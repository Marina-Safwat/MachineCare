import concurrent.futures, json, tempfile, threading, unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core import Store, Error, password_hash
from server import serve
from urllib.request import Request, urlopen
from urllib.error import HTTPError

class WorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.hashed=password_hash('Example-long-password-2026')
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.store=Store(Path(self.tmp.name)/'test.db'); self.store.seed()
        with self.store.tx() as db:
            for name,role,lead in [('admin','Administrator',None),('lead','Lead',None),('tech','Technician',2),('other','Technician',2)]: db.execute('INSERT INTO users(username,password,role,lead_id,must_change) VALUES(?,?,?,?,0)',(name,self.hashed,role,lead))
            for uid in (2,3,4):
                for bid in (1,3): db.execute('INSERT INTO access VALUES(?,?)',(uid,bid))
        self.tokens={u:self.store.login(u,'Example-long-password-2026')['token'] for u in ('admin','lead','tech','other')}
    def tearDown(self): self.tmp.cleanup()
    def act(self,user,action,**d): return self.store.execute(self.tokens[user],action,d)
    def request(self,user='tech',mid=1,pid=1,**extra):
        return self.act(user,'request',machine_id=mid,part_id=pid,quantity=1,reason='Worn component',operation_key=extra.pop('key',f'{user}:{mid}:{pid}'),**extra)
    def test_logout_and_expiration(self):
        self.act('tech','logout')
        with self.assertRaises(Error): self.store.state(self.tokens['tech'])
        with self.store.tx() as db: db.execute('UPDATE sessions SET expires=0')
        with self.assertRaises(Error): self.store.state(self.tokens['admin'])
    def test_disable_revokes_sessions(self):
        self.act('admin','disable',user_id=3,active=0)
        with self.assertRaises(Error): self.store.state(self.tokens['tech'])
        with self.assertRaises(Error): self.store.login('tech','Example-long-password-2026')
    def test_reset_forces_change_and_revokes(self):
        self.act('admin','reset',user_id=3,password='New-temporary-password!')
        with self.assertRaises(Error): self.store.state(self.tokens['tech'])
        self.tokens['tech']=self.store.login('tech','New-temporary-password!')['token']
        with self.assertRaises(Error): self.store.state(self.tokens['tech'])
        self.act('tech','password',current_password='New-temporary-password!',new_password='New-personal-password!')
        with self.assertRaises(Error): self.store.state(self.tokens['tech'])
        token=self.store.login('tech','New-personal-password!')['token']; self.assertEqual(self.store.state(token)['user']['must_change'],0)
    def test_role_and_assignment_permissions(self):
        with self.assertRaises(Error): self.act('tech','building',code='B10',name='Hidden')
        with self.store.tx() as db: db.execute('DELETE FROM access WHERE user_id=3 AND building_id=3')
        with self.assertRaises(Error): self.request(mid=3)
    def test_incompatible_part(self):
        with self.assertRaises(Error): self.request(pid=3)
    def test_identity_last_date_and_duplicate_completion(self):
        r=self.request(technician_id=4); self.act('tech','complete',request_id=r['id'])
        state=self.store.state(self.tokens['tech'])
        self.assertEqual(state['history'][0]['technician_id'],3)
        dates={m['id']:{p['id']:p['last_replacement'] for p in m['parts']} for m in state['machines']}
        self.assertIsNotNone(dates[1][1]); self.assertIsNone(dates[3][1])
        self.act('admin','receipt',part_id=1,quantity=1,reason='New delivery',operation_key='receipt:1')
        self.assertEqual(self.store.state(self.tokens['tech'])['machines'][0]['parts'][0]['last_replacement'],dates[1][1])
        with self.assertRaises(Error): self.act('tech','complete',request_id=r['id'])
    def test_early_approval_consumes_only_at_completion(self):
        first=self.request(); self.act('tech','complete',request_id=first['id'])
        with self.assertRaises(Error): self.request(key='early-bad')
        early=self.request(key='early',early_explanation='Seal failed prematurely')
        self.assertTrue(early['early']); self.assertEqual(early['state'],'Pending')
        before=next(p for p in self.store.state(self.tokens['admin'])['parts'] if p['id']==1)['stock']
        with self.assertRaises(Error): self.act('tech','complete',request_id=early['id'])
        with self.assertRaises(Error): self.act('tech','review',request_id=early['id'],decision='Approved',comment='Self approval')
        self.act('lead','review',request_id=early['id'],decision='Approved',comment='Verified defect')
        self.assertEqual(next(p for p in self.store.state(self.tokens['admin'])['parts'] if p['id']==1)['stock'],before)
        self.act('tech','complete',request_id=early['id'])
        self.assertEqual(next(p for p in self.store.state(self.tokens['admin'])['parts'] if p['id']==1)['stock'],before-1)
    def test_rejection_blocks_completion(self):
        r=self.request(); self.act('tech','complete',request_id=r['id'])
        r=self.request(key='early',early_explanation='Test failure')
        self.act('lead','review',request_id=r['id'],decision='Rejected',comment='Investigate first')
        with self.assertRaises(Error): self.act('tech','complete',request_id=r['id'])
    def test_missing_lead_blocked(self):
        r=self.request(); self.act('tech','complete',request_id=r['id'])
        with self.store.tx() as db: db.execute('UPDATE users SET lead_id=NULL WHERE id=3')
        with self.assertRaises(Error): self.request(key='early',early_explanation='Failure')
    def test_duplicate_request_and_receipt(self):
        self.request(key='same')
        with self.assertRaises(Error): self.request(key='same')
        self.act('admin','receipt',part_id=1,quantity=2,reason='delivery',operation_key='delivery')
        with self.assertRaises(Error): self.act('admin','receipt',part_id=1,quantity=2,reason='delivery',operation_key='delivery')
    def test_last_item_concurrency(self):
        with self.store.tx() as db: db.execute('UPDATE parts SET stock=1 WHERE id=1')
        one=self.request(); two=self.request(user='other',mid=3)
        def finish(pair):
            try: self.act(pair[0],'complete',request_id=pair[1]['id']); return True
            except Error: return False
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool: outcomes=list(pool.map(finish,[('tech',one),('other',two)]))
        self.assertEqual(sum(outcomes),1)
        with self.store.tx() as db:
            self.assertEqual(db.execute('SELECT stock FROM parts WHERE id=1').fetchone()[0],0)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM maintenance').fetchone()[0],1)
    def test_move_preserves_location_snapshot(self):
        r=self.request(); self.act('tech','complete',request_id=r['id'])
        old=self.store.state(self.tokens['admin'])['history'][0]['location_snapshot']
        self.act('admin','machine',id=1,line_id=3,type_id=1,station='09',asset_tag='DEMO-001',serial='SAMPLE',status='Operating')
        state=self.store.state(self.tokens['admin'])
        self.assertEqual(state['history'][0]['location_snapshot'],old)
        self.assertIsNotNone(next(m for m in state['machines'] if m['id']==1)['parts'][0]['last_replacement'])
    def test_competing_normal_requests_cannot_bypass_early_review(self):
        one=self.request(key='one'); two=self.request(key='two')
        self.act('tech','complete',request_id=one['id'])
        with self.assertRaises(Error): self.act('tech','complete',request_id=two['id'])
    def test_no_negative_adjustments(self):
        with self.assertRaises(Error): self.act('admin','adjust',part_id=1,quantity=1,delta=-100,reason='count correction',operation_key='adjust')
    def test_optional_line_and_duplicate_sku(self):
        self.act('admin','line',building_id=2,code='L01')
        with self.assertRaises(Error): self.act('admin','part',sku='DEMO-SEAL',name='Duplicate',bin='A1',cost=1,stock=1,threshold=0,target=1,lead_days=0,interval_days=90,type_ids=[1])
    def test_http_technician_and_lead_flow(self):
        server=serve(self.store,0); thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
        def api(path,data=None,token=None):
            req=Request(f'http://127.0.0.1:{server.server_port}{path}',data=None if data is None else json.dumps(data).encode(),headers={'Content-Type':'application/json',**({'Authorization':'Bearer '+token} if token else {})})
            with urlopen(req) as response: return json.load(response)
        try:
            with self.assertRaises(HTTPError): api('/state')
            tech=api('/login',{'username':'tech','password':'Example-long-password-2026'})['token']
            r=api('/actions/request',{'machine_id':1,'part_id':1,'quantity':1,'reason':'Normal replacement','operation_key':'http-first'},tech)
            api('/actions/complete',{'request_id':r['id']},tech)
            r=api('/actions/request',{'machine_id':1,'part_id':1,'quantity':1,'reason':'Premature failure','early_explanation':'Verified seal defect','operation_key':'http-second'},tech)
            lead=api('/login',{'username':'lead','password':'Example-long-password-2026'})['token']
            api('/actions/review',{'request_id':r['id'],'decision':'Approved','comment':'Inspected'},lead)
            api('/actions/complete',{'request_id':r['id']},tech)
            self.assertEqual(len(api('/state',token=tech)['history']),2)
        finally: server.shutdown(); server.server_close(); thread.join()

    def test_edit_account_updates_access_revokes_session_and_preserves_password(self):
        self.act('admin','edit_user',user_id=3,role='Technician',lead_id=2,building_ids=[1])
        with self.assertRaises(Error): self.store.state(self.tokens['tech'])
        self.tokens['tech']=self.store.login('tech','Example-long-password-2026')['token']
        state=self.store.state(self.tokens['tech'])
        self.assertEqual({m['building_id'] for m in state['machines']},{1})
        with self.assertRaises(Error): self.request(mid=3)
        account=next(u for u in self.store.state(self.tokens['admin'])['users'] if u['id']==3)
        self.assertEqual(account['building_ids'],[1])
    def test_edit_account_rejects_nonadmin_and_self_changes(self):
        with self.assertRaises(Error): self.act('tech','edit_user',user_id=4,role='Administrator',lead_id=None,building_ids=[])
        with self.assertRaises(Error): self.act('admin','edit_user',user_id=1,role='Technician',lead_id=2,building_ids=[1])
    def test_edit_account_validates_lead_and_building_ids_atomically(self):
        for data in [dict(lead_id=3,building_ids=[1]),dict(lead_id=4,building_ids=[1]),dict(lead_id=True,building_ids=[1]),dict(lead_id=2,building_ids=[999]),dict(lead_id=2,building_ids=[True]),dict(lead_id=2,building_ids=[2])]:
            with self.assertRaises(Error): self.act('admin','edit_user',user_id=3,role='Technician',**data)
        self.assertEqual(self.store.state(self.tokens['tech'])['user']['lead_id'],2)
    def test_edit_lead_cannot_orphan_assigned_technicians(self):
        with self.assertRaises(Error): self.act('admin','edit_user',user_id=2,role='Administrator',lead_id=None,building_ids=[1,3])
        with self.assertRaises(Error): self.act('admin','edit_user',user_id=2,role='Lead',lead_id=None,building_ids=[1])
    def test_edit_account_noop_keeps_session(self):
        self.act('admin','edit_user',user_id=3,role='Technician',lead_id=2,building_ids=[3,1,1])
        self.assertEqual(self.store.state(self.tokens['tech'])['user']['id'],3)
    def test_edit_account_reassigns_pending_early_work_preserves_history(self):
        self.act('admin','edit_user',user_id=4,role='Lead',lead_id=None,building_ids=[1,3])
        first=self.request(); self.act('tech','complete',request_id=first['id'])
        early=self.request(key='reassignment',early_explanation='Failed seal')
        self.act('admin','edit_user',user_id=3,role='Technician',lead_id=4,building_ids=[1,3])
        with self.assertRaises(Error): self.act('lead','review',request_id=early['id'],decision='Approved',comment='Old lead')
        self.tokens['other']=self.store.login('other','Example-long-password-2026')['token']
        state=self.store.state(self.tokens['other'])
        self.assertEqual(next(r for r in state['requests'] if r['id']==early['id'])['lead_id'],4)
        self.assertTrue(any('reassigned' in n['message'] for n in state['notifications']))
        self.act('other','review',request_id=early['id'],decision='Approved',comment='New assigned lead')
        self.tokens['tech']=self.store.login('tech','Example-long-password-2026')['token']
        self.act('tech','complete',request_id=early['id'])
        self.assertEqual(len(self.store.state(self.tokens['tech'])['history']),2)
        with self.store.tx() as db:
            self.assertTrue(db.execute("SELECT 1 FROM audit WHERE action='edit_user'").fetchone())
    def test_edit_account_blocks_orphaning_pending_requests(self):
        first=self.request(); self.act('tech','complete',request_id=first['id'])
        self.request(key='pending',early_explanation='Premature wear')
        with self.assertRaises(Error): self.act('admin','edit_user',user_id=3,role='Technician',lead_id=None,building_ids=[1,3])
        with self.assertRaises(Error): self.act('admin','edit_user',user_id=3,role='Lead',lead_id=None,building_ids=[1,3])

    def line_only(self,user_id=3,line_ids=None,lead_id=2):
        self.act('admin','edit_user',user_id=user_id,role='Technician',lead_id=lead_id,building_ids=[],line_ids=[1] if line_ids is None else line_ids)
        name='tech' if user_id==3 else 'other'
        self.tokens[name]=self.store.login(name,'Example-long-password-2026')['token']
    def test_line_only_scope_hides_siblings_and_direct_requests(self):
        self.line_only()
        state=self.store.state(self.tokens['tech'])
        self.assertEqual([m['id'] for m in state['machines']],[1])
        self.assertEqual([l['id'] for l in state['lines']],[1])
        self.assertEqual([b['id'] for b in state['buildings']],[1])
        self.assertEqual(state['user']['line_ids'],[1])
        self.assertEqual(state['user']['building_ids'],[])
        with self.assertRaises(Error): self.request(mid=2)
        with self.assertRaises(Error): self.request(mid=3)
        self.request()
    def test_whole_building_grant_includes_new_lines(self):
        self.act('admin','edit_user',user_id=3,role='Technician',lead_id=2,building_ids=[1],line_ids=[])
        self.act('admin','line',building_id=1,code='L03')
        self.tokens['tech']=self.store.login('tech','Example-long-password-2026')['token']
        state=self.store.state(self.tokens['tech'])
        self.assertEqual({l['code'] for l in state['lines']},{'L01','L02','L03'})
    def test_line_grant_does_not_expand_to_new_sibling_lines(self):
        self.line_only()
        self.act('admin','line',building_id=1,code='L03')
        self.assertEqual([l['id'] for l in self.store.state(self.tokens['tech'])['lines']],[1])
    def test_invalid_line_grants_are_atomic(self):
        for values in [[999],[True],['1'],None]:
            with self.assertRaises(Error): self.act('admin','edit_user',user_id=3,role='Technician',lead_id=2,building_ids=[],line_ids=values)
        self.assertEqual(len(self.store.state(self.tokens['tech'])['machines']),4)
    def test_pending_early_work_blocks_line_access_removal(self):
        self.line_only()
        first=self.request();self.act('tech','complete',request_id=first['id'])
        self.request(key='early-line',early_explanation='Failed seal')
        with self.assertRaises(Error): self.act('admin','edit_user',user_id=3,role='Technician',lead_id=2,building_ids=[],line_ids=[])
        self.assertEqual(self.store.state(self.tokens['tech'])['user']['line_ids'],[1])
    def test_lead_line_coverage_and_future_building_semantics(self):
        self.line_only(user_id=3);self.line_only(user_id=4)
        self.act('admin','edit_user',user_id=2,role='Lead',lead_id=None,building_ids=[],line_ids=[1])
        with self.assertRaises(Error): self.act('admin','edit_user',user_id=3,role='Technician',lead_id=2,building_ids=[],line_ids=[2])
        self.act('admin','edit_user',user_id=2,role='Lead',lead_id=None,building_ids=[],line_ids=[1,2])
        with self.assertRaises(Error): self.act('admin','edit_user',user_id=3,role='Technician',lead_id=2,building_ids=[1],line_ids=[])
        with self.assertRaises(Error): self.act('admin','edit_user',user_id=2,role='Lead',lead_id=None,building_ids=[],line_ids=[2])
    def test_line_scope_hides_other_request_and_history_records(self):
        r=self.request(user='other',mid=2);self.act('other','complete',request_id=r['id'])
        self.line_only()
        state=self.store.state(self.tokens['tech'])
        self.assertEqual(state['history'],[])
        self.assertEqual(state['requests'],[])
        with self.assertRaises(Error): self.act('tech','complete',request_id=r['id'])
        self.assertEqual(len(self.store.state(self.tokens['admin'])['history']),1)
    def test_create_account_with_line_scope_and_lead_coverage(self):
        self.act('admin','user',username='line-user',password='Strong-temporary-password',role='Technician',lead_id=2,building_ids=[],line_ids=[2])
        token=self.store.login('line-user','Strong-temporary-password')['token']
        self.store.execute(token,'password',{'current_password':'Strong-temporary-password','new_password':'Strong-personal-password'})
        token=self.store.login('line-user','Strong-personal-password')['token']
        self.assertEqual([m['id'] for m in self.store.state(token)['machines']],[2])
        with self.assertRaises(Error): self.act('admin','user',username='bad-line',password='Strong-temporary-password',role='Technician',lead_id=2,building_ids=[],line_ids=[999])
        self.assertFalse(any(u['username']=='bad-line' for u in self.store.state(self.tokens['admin'])['users']))
    def test_legacy_account_edit_preserves_line_grants(self):
        self.line_only()
        self.act('admin','edit_user',user_id=3,role='Technician',lead_id=2,building_ids=[])
        self.assertEqual(self.store.state(self.tokens['tech'])['user']['line_ids'],[1])
    def test_machine_move_removes_line_visibility_preserves_history(self):
        self.line_only()
        r=self.request();self.act('tech','complete',request_id=r['id'])
        self.act('admin','machine',id=1,line_id=2,type_id=1,station='09',asset_tag='DEMO-001',serial='SAMPLE',status='Operating')
        self.assertEqual(self.store.state(self.tokens['tech'])['machines'],[])
        self.assertEqual(self.store.state(self.tokens['tech'])['history'],[])
        self.assertEqual(len(self.store.state(self.tokens['admin'])['history']),1)
    def test_line_move_cannot_break_assigned_lead_coverage(self):
        self.line_only()
        with self.assertRaises(Error): self.act('admin','line',id=1,building_id=2,code='L90')
        self.assertEqual(next(l for l in self.store.state(self.tokens['admin'])['lines'] if l['id']==1)['building_id'],1)
    def test_migration_preserves_v1_accounts_inventory_history_and_access(self):
        r=self.request();self.act('tech','complete',request_id=r['id'])
        before=self.store.state(self.tokens['admin'])
        with self.store.tx() as db:
            db.execute('DROP TABLE line_access');db.execute('PRAGMA user_version=1')
        reopened=Store(self.store.path)
        after=reopened.state(self.tokens['admin'])
        self.assertEqual(after['history'],before['history'])
        self.assertEqual(after['parts'],before['parts'])
        self.assertEqual(after['users'],before['users'])
        self.assertEqual(len(reopened.state(self.tokens['tech'])['machines']),4)
        with reopened.tx() as db:self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],2)
    def test_migration_rerun_keeps_line_grants_and_version(self):
        self.line_only()
        reopened=Store(self.store.path)
        self.assertEqual(reopened.state(self.tokens['tech'])['user']['line_ids'],[1])
        with reopened.tx() as db:self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],2)
    def test_http_forbidden_line_request_is_rejected(self):
        self.line_only()
        server=serve(self.store,0);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            req=Request(f'http://127.0.0.1:{server.server_port}/actions/request',data=json.dumps({'machine_id':2,'part_id':1,'quantity':1,'reason':'Forbidden sibling','operation_key':'http-forbidden'}).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+self.tokens['tech']})
            with self.assertRaises(HTTPError) as result:urlopen(req)
            self.assertEqual(result.exception.code,403)
            self.assertEqual(self.store.state(self.tokens['admin'])['requests'],[])
        finally:server.shutdown();server.server_close();thread.join()

if __name__=='__main__': unittest.main()
