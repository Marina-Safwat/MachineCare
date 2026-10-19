"""Opt-in local worker: durable alert/email episodes and verified scheduled backups.

No mail is sent without both enabled configuration and --allow-email. One worker
per database is enforced by an OS file lock. SMTP ambiguous outcomes are held
for operator review, never blindly retried.
"""
import argparse
import json
import os
import re
import smtplib
import ssl
import time
from contextlib import contextmanager
from email.message import EmailMessage
from pathlib import Path
import backup
import inventory_status
from core import Store, now

class RetryableMailError(Exception):pass
class UncertainMailError(Exception):pass

def retry_email(store,event_id,reason,confirm_uncertain=False):
    if type(event_id)!=int or event_id<1 or not isinstance(reason,str) or not reason.strip() or len(reason)>1000:
        raise ValueError('A valid delivery ID and reconciliation reason are required.')
    with store.tx() as db:
        row=db.execute('SELECT state FROM email_outbox WHERE id=?',(event_id,)).fetchone()
        if not row or row['state'] not in ('Failed','Uncertain'):raise ValueError('Only failed or uncertain deliveries can be retried.')
        if row['state']=='Uncertain' and not confirm_uncertain:raise ValueError('Reconcile SMTP logs and explicitly confirm an uncertain retry.')
        db.execute("UPDATE email_outbox SET state='Pending',attempts=0,next_attempt=0,last_error=NULL WHERE id=?",(event_id,))
        store.audit(db,None,'email_retry_authorized',{'delivery_id':event_id,'previous_state':row['state'],'reason':reason.strip()})

def load_config(path):
    config=json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(config,dict):raise ValueError('Configuration must be an object.')
    for name,default,minimum in [('check_seconds',60,10),('backup_seconds',86400,60)]:
        value=config.get(name,default)
        if type(value)!=int or not minimum<=value<=31536000:raise ValueError('Invalid worker interval.')
        config[name]=value
    email=config.get('email',{})
    if not isinstance(email,dict) or type(email.get('enabled',False))!=bool:raise ValueError('Invalid email configuration.')
    recipients=email.get('recipients',{})
    if not isinstance(recipients,dict):raise ValueError('Recipients must map user IDs to email addresses.')
    addresses=list(recipients.values())+([email.get('from','')] if email.get('enabled') else [])
    if any(not isinstance(v,str) or not re.fullmatch(r'[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+',v) for v in addresses):raise ValueError('Invalid email address.')
    if any(not key.isdigit() or int(key)<1 for key in recipients):raise ValueError('Invalid recipient user ID.')
    if email.get('enabled'):
        if not isinstance(email.get('host'),str) or not email['host']:raise ValueError('SMTP host required.')
        if type(email.get('port',587))!=int or not 1<=email.get('port',587)<=65535:raise ValueError('Invalid SMTP port.')
        if email.get('tls','starttls') not in ('starttls','ssl'):raise ValueError('SMTP TLS is required.')
    if 'password' in email:raise ValueError('Use password_env, never a password in the configuration file.')
    config['email']=email
    return config

@contextmanager
def exclusive(database):
    path=Path(str(Path(database).resolve())+'.worker.lock')
    with path.open('a+b') as handle:
        handle.seek(0);handle.write(b'0');handle.flush();handle.seek(0)
        if os.name=='nt':
            import msvcrt
            msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1)
        else:
            import fcntl
            fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
        try:yield
        finally:
            handle.seek(0)
            if os.name=='nt':msvcrt.locking(handle.fileno(),msvcrt.LK_UNLCK,1)
            else:fcntl.flock(handle,fcntl.LOCK_UN)

def smtp_send(email,address,event_id):
    message=EmailMessage()
    message['From']=email['from'];message['To']=address
    message['Subject']='MachineCare: attention required'
    message['Message-ID']=f'<machinecare-{event_id}@{email["from"].split("@")[1]}>'
    # No machine, stock, account or free-text data can escape scope through email.
    message.set_content('You have a MachineCare notification. Open your usual MachineCare application and sign in to view current information available to your account.')
    client=None
    try:
        context=ssl.create_default_context()
        if email.get('tls','starttls')=='ssl':client=smtplib.SMTP_SSL(email['host'],email.get('port',465),timeout=20,context=context)
        else:
            client=smtplib.SMTP(email['host'],email.get('port',587),timeout=20)
            client.ehlo();client.starttls(context=context);client.ehlo()
        if email.get('username'):
            secret=os.environ.get(email.get('password_env','MACHINECARE_SMTP_PASSWORD'))
            if not secret:raise RetryableMailError()
            client.login(email['username'],secret)
    except Exception as exc:
        if client:
            try:client.close()
            except Exception:pass
        raise RetryableMailError() from exc
    try:
        client.send_message(message)
    except smtplib.SMTPResponseException as exc:
        raise RetryableMailError() from exc
    except Exception as exc:
        raise UncertainMailError() from exc
    finally:
        # QUIT failure after successful DATA must not turn delivery into a retry.
        try:client.close()
        except Exception:pass

class Worker:
    def __init__(self,store,config,allow_email=False,sender=smtp_send,clock=time.time):
        self.store=store;self.config=config;self.allow_email=allow_email;self.sender=sender;self.clock=clock

    def recover(self):
        with self.store.tx() as db:
            db.execute("UPDATE email_outbox SET state='Uncertain',last_error='Worker interrupted during delivery; reconcile before retry.' WHERE state='Sending'")

    def tick(self):
        stamp=self.clock();email=self.config.get('email',{})
        with self.store.tx() as db:
            inventory_status.sync(db)
            if email.get('enabled'):
                for key in email.get('recipients',{}):
                    user=db.execute('SELECT * FROM users WHERE id=? AND active=1',(int(key),)).fetchone()
                    if not user:continue
                    events=[f'notification:{r[0]}' for r in db.execute('SELECT id FROM notifications WHERE user_id=?',(user['id'],))]
                    if user['role'] in ('Administrator','Lead'):
                        events += [f'alert:{r["id"]}' for r in db.execute('SELECT * FROM alerts WHERE resolved IS NULL') if inventory_status.visible(db,user,r)]
                    for event in events:
                        db.execute('INSERT OR IGNORE INTO email_outbox(event_key,user_id,created) VALUES(?,?,?)',(event,user['id'],now()))
            db.execute("INSERT INTO job_state(name,last_success,last_error) VALUES('checks',?,NULL) ON CONFLICT(name) DO UPDATE SET last_success=excluded.last_success,last_error=NULL",(stamp,))
        if email.get('enabled') and self.allow_email:self.deliver()
        directory=self.config.get('backup_directory')
        if directory:
            with self.store.tx() as db:
                last=db.execute("SELECT last_success FROM job_state WHERE name='backup'").fetchone()
            if not last or last[0] is None or stamp-last[0]>=self.config.get('backup_seconds',86400):
                try:
                    backup.create(self.store.path,directory)
                    with self.store.tx() as db:
                        db.execute("INSERT INTO job_state VALUES('backup',?,NULL) ON CONFLICT(name) DO UPDATE SET last_success=excluded.last_success,last_error=NULL",(stamp,))
                        self.store.audit(db,None,'scheduled_backup_success',{})
                except Exception:
                    with self.store.tx() as db:
                        db.execute("INSERT INTO job_state VALUES('backup',NULL,'Backup failed; check disk capacity and protected destination.') ON CONFLICT(name) DO UPDATE SET last_error=excluded.last_error")
                    # No exception text: filesystem paths and service secrets stay private.
        return self.status()

    def deliver(self):
        email=self.config['email']
        with self.store.tx() as db:
            pending=[dict(r) for r in db.execute("SELECT * FROM email_outbox WHERE state='Pending' AND next_attempt<=? ORDER BY id LIMIT 50",(self.clock(),))]
        for item in pending:
            with self.store.tx() as db:
                user=db.execute('SELECT * FROM users WHERE id=? AND active=1',(item['user_id'],)).fetchone()
                address=email.get('recipients',{}).get(str(item['user_id']))
                allowed=bool(user and address)
                if allowed and item['event_key'].startswith('alert:'):
                    alert=db.execute('SELECT * FROM alerts WHERE id=? AND resolved IS NULL',(int(item['event_key'].split(':')[1]),)).fetchone()
                    allowed=bool(alert and user['role'] in ('Administrator','Lead') and inventory_status.visible(db,user,alert))
                if not allowed:
                    db.execute("UPDATE email_outbox SET state='Cancelled' WHERE id=?",(item['id'],));continue
                claimed=db.execute("UPDATE email_outbox SET state='Sending',attempts=attempts+1 WHERE id=? AND state='Pending'",(item['id'],)).rowcount
            if not claimed:continue
            try:
                self.sender(email,address,f'{item["id"]}-{item["created"].replace(":", "")}')
                state='Sent';error=None
            except RetryableMailError:
                state='Failed' if item['attempts']>=4 else 'Pending';error='Delivery rejected or connection unavailable.'
            except Exception:
                state='Uncertain';error='Delivery outcome uncertain; reconcile with mail service before retry.'
            with self.store.tx() as db:
                db.execute('UPDATE email_outbox SET state=?,last_error=?,next_attempt=?,sent=? WHERE id=?',(state,error,self.clock()+min(3600,60*2**item['attempts']),now() if state=='Sent' else None,item['id']))

    def status(self):
        with self.store.tx() as db:
            return {'jobs':[dict(r) for r in db.execute('SELECT * FROM job_state')], 'queue':[dict(r) for r in db.execute('SELECT state,COUNT(*) count FROM email_outbox GROUP BY state')], 'email_delivery_enabled':bool(self.allow_email and self.config.get('email',{}).get('enabled'))}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db',required=True);parser.add_argument('--config',required=True)
    parser.add_argument('--once',action='store_true');parser.add_argument('--allow-email',action='store_true')
    parser.add_argument('--retry-email',type=int);parser.add_argument('--reason',default='')
    parser.add_argument('--confirm-uncertain',action='store_true')
    args=parser.parse_args()
    try:
        if not Path(args.db).is_file():raise ValueError('Existing database required.')
        config=load_config(args.config)
        with exclusive(args.db):
            store=Store(args.db)
            if args.retry_email is not None:
                retry_email(store,args.retry_email,args.reason,args.confirm_uncertain)
                print('Delivery queued for a future authorized worker run. No email sent.');return
            worker=Worker(store,config,args.allow_email);worker.recover()
            while True:
                print(json.dumps(worker.tick()),flush=True)
                if args.once:break
                time.sleep(config['check_seconds'])
    except KeyboardInterrupt:pass
    except Exception:parser.exit(1,'Worker stopped. Check configuration, database version, disk space and single-worker ownership. No email or secret details are logged.\n')

if __name__=='__main__':main()
