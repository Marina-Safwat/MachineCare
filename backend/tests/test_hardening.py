import hashlib
import json
import sqlite3
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.request import Request, urlopen
from urllib.error import HTTPError
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core import Store, Error, password_hash
from server import serve
from worker import Worker, RetryableMailError, UncertainMailError, load_config, exclusive, retry_email
import backup

class HardeningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.digest=password_hash('Disposable-test-only-2026')
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.store=Store(self.root/'test.db');self.store.seed()
        with self.store.tx() as db:
            for uid,role in [(1,'Administrator'),(2,'Lead'),(3,'Technician')]:
                db.execute('INSERT INTO users(id,username,password,role,must_change) VALUES(?,?,?,?,0)',(uid,f'user{uid}',self.digest,role))
                db.execute('INSERT INTO sessions VALUES(?,?,?,0)',(hashlib.sha256(f'test-{uid}'.encode()).hexdigest(),uid,time.time()+3600))
            db.execute('INSERT INTO line_access VALUES(2,1)')
        self.config={'email':{'enabled':True,'recipients':{'1':'admin@example.test','2':'lead@example.test','3':'tech@example.test'}},'backup_seconds':60}
    def tearDown(self):self.tmp.cleanup()
    def test_auth_audit_never_contains_credentials_and_failure_commits(self):
        with self.assertRaises(Error):self.store.login('unknown','private-value')
        result=self.store.login('user1','Disposable-test-only-2026')
        self.store.execute(result['token'],'logout',{})
        with self.store.tx() as db:
            events=[dict(r) for r in db.execute('SELECT * FROM audit')]
        self.assertTrue({'login_failed','login_success','logout'} <= {r['action'] for r in events})
        self.assertNotIn('private-value',json.dumps(events));self.assertNotIn(result['token'],json.dumps(events))
    def test_malformed_inputs_rejected_without_mutation(self):
        for data in [{'notes':[]},{'reason':{}},{'quantity':2**63},{'cost':float('nan')},{'early_explanation':False}]:
            with self.assertRaises(Error):self.store.execute('test-1','request',data)
        with self.store.tx() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM requests').fetchone()[0],0)
    def test_system_status_admin_only(self):
        self.assertIn('jobs',self.store.execute('test-1','system_status',{}))
        for token in ('test-2','test-3'):
            with self.assertRaises(Error):self.store.execute(token,'system_status',{})
        with self.store.tx() as db:self.assertEqual(db.execute("SELECT COUNT(*) FROM audit WHERE action='permission_denied'").fetchone()[0],2)
    def test_password_failure_audit_preserves_password_and_session(self):
        with self.assertRaises(Error):self.store.execute('test-1','password',{'current_password':'wrong-private-value','new_password':'New-private-value-123'})
        with self.store.tx() as db:
            self.assertEqual(db.execute('SELECT password FROM users WHERE id=1').fetchone()[0],self.digest)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM audit WHERE action='password_change_failed'").fetchone()[0],1)
            self.assertNotIn('private-value',str([dict(r) for r in db.execute('SELECT * FROM audit')]))
        self.assertIn('user',self.store.state('test-1'))
    def test_worker_disabled_delivery_dedup_and_restart(self):
        sent=[];worker=Worker(self.store,self.config,sender=lambda *a:sent.append(a))
        worker.tick();worker.tick()
        with self.store.tx() as db:
            count=db.execute('SELECT COUNT(*) FROM email_outbox').fetchone()[0]
            self.assertGreater(count,0)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM email_outbox WHERE user_id=3').fetchone()[0],0)
        self.assertEqual(sent,[])
        worker=Worker(self.store,self.config,True,sender=lambda *a:sent.append(a));worker.tick();worker.tick()
        self.assertEqual(len(sent),count)
    def test_retry_and_ambiguous_delivery(self):
        clock=[1000]
        def fail(*args):raise RetryableMailError()
        worker=Worker(self.store,self.config,True,sender=fail,clock=lambda:clock[0]);worker.tick()
        with self.store.tx() as db:self.assertEqual(db.execute('SELECT MIN(attempts) FROM email_outbox').fetchone()[0],1)
        worker.tick()
        with self.store.tx() as db:self.assertEqual(db.execute('SELECT MAX(attempts) FROM email_outbox').fetchone()[0],1)
        clock[0]+=61
        def uncertain(*args):raise UncertainMailError()
        worker.sender=uncertain;worker.tick();clock[0]+=10000;worker.tick()
        with self.store.tx() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM email_outbox WHERE state!='Uncertain'").fetchone()[0],0)
            self.assertEqual(db.execute('SELECT MAX(attempts) FROM email_outbox').fetchone()[0],2)
    def test_crashed_delivery_and_revoked_access_are_not_resent(self):
        worker=Worker(self.store,self.config);worker.tick()
        with self.store.tx() as db:
            db.execute("UPDATE email_outbox SET state='Sending' WHERE user_id=1")
            db.execute('UPDATE users SET active=0 WHERE id=2')
        worker.recover();worker.allow_email=True;worker.sender=lambda *a:self.fail('Must not send');worker.tick()
        with self.store.tx() as db:
            self.assertEqual({r[0] for r in db.execute('SELECT state FROM email_outbox')},{'Uncertain','Cancelled'})
    def test_backup_schedule_success_and_failure_are_visible(self):
        self.config['backup_directory']=str(self.root/'backups');clock=[1000]
        worker=Worker(self.store,self.config,clock=lambda:clock[0]);worker.tick();worker.tick()
        copies=list((self.root/'backups').glob('*.db'));self.assertEqual(len(copies),1)
        self.assertEqual(backup.verify(copies[0])['schema_version'],7)
        clock[0]+=61
        with patch('worker.backup.create',side_effect=OSError('sensitive path')):worker.tick()
        self.assertNotIn('sensitive path',json.dumps(worker.status()))
        self.assertTrue(next(r for r in worker.status()['jobs'] if r['name']=='backup')['last_error'])
    def test_config_rejects_plaintext_password_and_injection(self):
        for email in [{'password':'do-not-store'},{'recipients':{'1':'a@example.test\r\nBcc: x@y.test'}},{'enabled':True,'host':'smtp','from':'a@b.test','tls':'none'}]:
            path=self.root/'config.json';path.write_text(json.dumps({'email':email}))
            with self.assertRaises(ValueError):load_config(path)
    def test_single_worker_lock(self):
        with exclusive(self.store.path):
            with self.assertRaises(OSError):
                with exclusive(self.store.path):pass
    def test_manual_retry_requires_reconciliation_and_rejects_sent(self):
        Worker(self.store,self.config).tick()
        with self.store.tx() as db:
            event_id=db.execute('SELECT MIN(id) FROM email_outbox').fetchone()[0]
            db.execute("UPDATE email_outbox SET state='Uncertain' WHERE id=?",(event_id,))
        with self.assertRaises(ValueError):retry_email(self.store,event_id,'Provider confirms non-delivery')
        retry_email(self.store,event_id,'Provider confirms non-delivery',True)
        with self.store.tx() as db:
            self.assertEqual(db.execute('SELECT state FROM email_outbox WHERE id=?',(event_id,)).fetchone()[0],'Pending')
            db.execute("UPDATE email_outbox SET state='Sent' WHERE id=?",(event_id,))
        with self.assertRaises(ValueError):retry_email(self.store,event_id,'Not allowed',True)
    def test_http_headers_json_types_origin_and_rate_limit(self):
        server=serve(self.store,0);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        base=f'http://127.0.0.1:{server.server_port}'
        def call(path='/login',body=b'{}',headers=None):
            request=Request(base+path,data=body,headers={'Content-Type':'application/json',**(headers or {})})
            try:response=urlopen(request)
            except HTTPError as error:response=error
            response.read();response.close()
            return response
        try:
            response=call(body=b'{"username":[],"password":{}}');self.assertEqual(response.code,400)
            self.assertEqual(response.headers['X-Frame-Options'],'DENY')
            self.assertNotIn('Python',response.headers['Server'])
            self.assertEqual(call(body=b'{"x":1,"x":2}').code,400)
            self.assertEqual(call(headers={'Origin':'https://evil.example'}).code,403)
            self.assertEqual(call(headers={'Host':'evil.example'}).code,403)
            self.assertEqual(call(headers={'Content-Type':'text/plain'}).code,415)
            with patch.object(self.store,'login',side_effect=Error('Invalid username or password.',401)):
                for _ in range(15):self.assertEqual(call().code,401)
                limited=call();self.assertEqual(limited.code,429);self.assertEqual(limited.headers['Retry-After'],'300')
        finally:server.shutdown();server.server_close();thread.join()

if __name__=='__main__':unittest.main()
