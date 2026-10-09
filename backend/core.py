"""MachineCare local pilot domain service. Every mutation owns one SQLite transaction."""
import base64, hashlib, hmac, json, os, secrets, sqlite3, time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import access_policy as scopes
import catalog

class Error(Exception):
    def __init__(self, message, status=400):
        self.message, self.status = message, status
        super().__init__(message)

def now(): return datetime.now(timezone.utc).isoformat()
def password_hash(password):
    if not isinstance(password,str) or len(password)<12: raise Error('Use a password of at least 12 characters.')
    salt=secrets.token_bytes(16)
    digest=hashlib.pbkdf2_hmac('sha256',password.encode(),salt,600000)
    return 'pbkdf2_sha256$600000$'+base64.b64encode(salt).decode()+'$'+base64.b64encode(digest).decode()
def password_ok(password, encoded):
    _, rounds, salt, expected=encoded.split('$')
    actual=hashlib.pbkdf2_hmac('sha256',password.encode(),base64.b64decode(salt),int(rounds))
    return hmac.compare_digest(actual,base64.b64decode(expected))
def required(data,key):
    value=data.get(key)
    if not isinstance(value,str) or not value.strip(): raise Error(f'{key} is required.')
    return value.strip()
def integer(data,key,minimum=1):
    value=data.get(key)
    if isinstance(value,bool) or not isinstance(value,int) or value<minimum: raise Error(f'{key} must be an integer of at least {minimum}.')
    return value

class Store:
    def __init__(self,path):
        self.path=str(path)
        db=sqlite3.connect(self.path,timeout=20,isolation_level=None)
        try:
            db.execute('PRAGMA foreign_keys=ON')
            version=db.execute('PRAGMA user_version').fetchone()[0]
            if version>3: raise Error('Database is newer than this application. Upgrade the app; do not downgrade.')
            db.executescript(Path(__file__).with_name('schema.sql').read_text())
            if version<1: db.execute('PRAGMA user_version=1')
            if version<2:
                db.executescript((Path(__file__).parent/'migrations'/'002_line_access.sql').read_text())
            if version<3:
                db.executescript((Path(__file__).parent/'migrations'/'003_catalog_revision.sql').read_text())
        except Exception:
            if db.in_transaction: db.rollback()
            raise
        finally: db.close()
    @contextmanager
    def tx(self):
        db=sqlite3.connect(self.path,timeout=20,isolation_level=None)
        db.row_factory=sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        try:
            db.execute('BEGIN IMMEDIATE')
            yield db
            db.commit()
        except sqlite3.IntegrityError as e:
            db.rollback()
            raise Error('Conflict: duplicate identifier or invalid relationship.') from e
        except Exception:
            db.rollback(); raise
        finally: db.close()
    def audit(self,db,user,action,detail):
        db.execute('INSERT INTO audit(actor_id,action,detail,created) VALUES(?,?,?,?)',(user,action,json.dumps(detail),now()))
    def bootstrap(self,username,password):
        with self.tx() as db:
            if db.execute('SELECT 1 FROM users').fetchone(): raise Error('First administrator already exists.')
            db.execute("INSERT INTO users(username,password,role,must_change) VALUES(?,?,'Administrator',0)",(username,password_hash(password)))
    def login(self,username,password):
        with self.tx() as db:
            u=db.execute('SELECT * FROM users WHERE username=?',(username,)).fetchone()
            if not u or not u['active'] or not password_ok(password,u['password']): raise Error('Invalid username or password.',401)
            raw=secrets.token_urlsafe(32); token=hashlib.sha256(raw.encode()).hexdigest()
            db.execute('INSERT INTO sessions VALUES(?,?,?,?)',(token,u['id'],time.time()+8*3600,u['version']))
            return {'token':raw,'user':self.public_user(u)}
    @staticmethod
    def public_user(u): return {k:u[k] for k in ('id','username','role','lead_id','active','must_change')}
    def user(self,db,raw,allow_change=False):
        token=hashlib.sha256(raw.encode()).hexdigest()
        u=db.execute('SELECT u.* FROM users u JOIN sessions s ON s.user_id=u.id WHERE s.token=? AND s.expires>? AND s.version=u.version AND u.active=1',(token,time.time())).fetchone()
        if not u: raise Error('Session expired. Sign in again.',401)
        if u['must_change'] and not allow_change: raise Error('Change your temporary password first.',403)
        return u
    def admin(self,u):
        if u['role']!='Administrator': raise Error('Administrator permission required.',403)
    def machine(self,db,u,machine_id):
        m=db.execute('SELECT m.*,b.id building_id,b.code building,l.code line,t.name type FROM machines m JOIN lines l ON l.id=m.line_id JOIN buildings b ON b.id=l.building_id JOIN types t ON t.id=m.type_id WHERE m.id=?',(machine_id,)).fetchone()
        if not m: raise Error('Machine not found.',404)
        if u['role']!='Administrator' and not scopes.allows(scopes.grants(db,u['id']),m['building_id'],m['line_id']): raise Error('Machine outside your assigned buildings or production lines.',403)
        return m
    @staticmethod
    def name(m): return f"{m['building']} · {m['line']} · Station {m['station']} · {m['type']}"
    def public_scope(self,db,u):
        buildings,lines=scopes.grants(db,u['id'])
        return {**self.public_user(u),'building_ids':sorted(buildings),'line_ids':sorted(lines)}
    def validate_scope(self,db,buildings,lines):
        try: return scopes.validate(db,buildings,lines)
        except ValueError as e: raise Error(str(e)) from e
    def check_lead_coverage(self,db):
        for tech in db.execute('SELECT id,lead_id FROM users WHERE lead_id IS NOT NULL').fetchall():
            if not scopes.covers(db,scopes.grants(db,tech['lead_id']),scopes.grants(db,tech['id'])):
                raise Error('Moving this line would leave a lead without access to assigned technician lines. Update assignments first.')
    def public_part(self,db,p):
        return {**dict(p),'type_ids':[r[0] for r in db.execute('SELECT type_id FROM compatibility WHERE part_id=? ORDER BY type_id',(p['id'],))]}
    def catalog_validation(self,fn,*args):
        try: return fn(*args)
        except catalog.CatalogError as e: raise Error(str(e)) from e
    def state(self,raw):
        with self.tx() as db:
            u=self.user(db,raw)
            machines=[]
            for row in db.execute('SELECT id FROM machines').fetchall():
                try: m=self.machine(db,u,row['id'])
                except Error: continue
                item=dict(m); item['name']=self.name(m); item['parts']=[]
                for p in db.execute('SELECT p.* FROM parts p JOIN compatibility c ON c.part_id=p.id WHERE c.type_id=?',(m['type_id'],)).fetchall():
                    part=self.public_part(db,p)
                    last=db.execute('SELECT MAX(replaced) FROM maintenance WHERE machine_id=? AND part_id=?',(m['id'],p['id'])).fetchone()[0]
                    part['last_replacement']=last
                    item['parts'].append(part)
                machines.append(item)
            visible={m['id'] for m in machines}
            requests=[dict(r) for r in db.execute('SELECT r.*,u.username technician,p.name part FROM requests r JOIN users u ON u.id=r.technician_id JOIN parts p ON p.id=r.part_id ORDER BY r.id DESC') if r['machine_id'] in visible and (u['role']=='Administrator' or r['technician_id']==u['id'] or r['lead_id']==u['id'])]
            history=[dict(r) for r in db.execute('SELECT m.*,p.name part,u.username technician FROM maintenance m JOIN parts p ON p.id=m.part_id JOIN users u ON u.id=m.technician_id ORDER BY m.id DESC') if r['machine_id'] in visible]
            scope=scopes.grants(db,u['id'])
            accessible_lines=[dict(l) for l in db.execute('SELECT * FROM lines') if u['role']=='Administrator' or scopes.allows(scope,l['building_id'],l['id'])]
            building_ids=scope[0]|{l['building_id'] for l in accessible_lines}
            return {'user':self.public_scope(db,u),'machines':machines,'parts':[self.public_part(db,r) for r in db.execute('SELECT * FROM parts ORDER BY name')], 'requests':requests,'history':history,'buildings':[dict(r) for r in db.execute('SELECT * FROM buildings') if u['role']=='Administrator' or r['id'] in building_ids], 'lines':accessible_lines, 'types':[dict(r) for r in db.execute('SELECT * FROM types')],'users':[self.public_scope(db,r) for r in db.execute('SELECT * FROM users')] if u['role']=='Administrator' else [],'notifications':[dict(r) for r in db.execute('SELECT * FROM notifications WHERE user_id=? ORDER BY id DESC',(u['id'],))], 'email_available':False}
    def execute(self,raw,action,d):
        with self.tx() as db:
            u=self.user(db,raw,action in ('password','logout'))
            uid=u['id']
            if action=='logout':
                db.execute('DELETE FROM sessions WHERE token=?',(hashlib.sha256(raw.encode()).hexdigest(),)); return {}
            if action=='password':
                if not password_ok(required(d,'current_password'),u['password']): raise Error('Current password is incorrect.')
                db.execute('UPDATE users SET password=?,must_change=0,version=version+1 WHERE id=?',(password_hash(required(d,'new_password')),uid))
                db.execute('DELETE FROM sessions WHERE user_id=?',(uid,)); return {'message':'Password changed. Sign in again.'}
            if action in ('building','line','type','machine','part','edit_part','user','edit_user','reset','disable','receipt','adjust'):
                self.admin(u)
                if action=='building':
                    values=(required(d,'code'),required(d,'name'))
                    if d.get('id'): db.execute('UPDATE buildings SET code=?,name=? WHERE id=?',(*values,integer(d,'id')))
                    else: db.execute('INSERT INTO buildings(code,name) VALUES(?,?)',values)
                elif action=='line':
                    values=(integer(d,'building_id'),required(d,'code'),d.get('description',''))
                    if d.get('id'): db.execute('UPDATE lines SET building_id=?,code=?,description=? WHERE id=?',(*values,integer(d,'id')))
                    else: db.execute('INSERT INTO lines(building_id,code,description) VALUES(?,?,?)',values)
                    self.check_lead_coverage(db)
                elif action=='type':
                    name=self.catalog_validation(catalog.text,d,'name')
                    type_id=integer(d,'id') if 'id' in d else None
                    self.catalog_validation(catalog.unique_type_name,db,name,type_id)
                    if type_id is None:
                        db.execute('INSERT INTO types(name) VALUES(?)',(name,))
                    else:
                        old=db.execute('SELECT * FROM types WHERE id=?',(type_id,)).fetchone()
                        if not old: raise Error('Machine type not found.',404)
                        revision=integer(d,'revision',0)
                        if revision!=old['revision']: raise Error('This machine type changed in another session. Reopen its editor before saving.',409)
                        if name!=old['name']:
                            db.execute('UPDATE types SET name=?,revision=revision+1 WHERE id=? AND revision=?',(name,type_id,revision))
                        self.audit(db,uid,'edit_type',{'type_id':type_id,'before':dict(old),'after':dict(db.execute('SELECT * FROM types WHERE id=?',(type_id,)).fetchone())})
                        return {'message':'Machine type saved.'}
                elif action=='machine':
                    values=(integer(d,'line_id'),integer(d,'type_id'),required(d,'station'),required(d,'asset_tag'),d.get('serial',''),d.get('status','Operating'))
                    if d.get('id'): db.execute('UPDATE machines SET line_id=?,type_id=?,station=?,asset_tag=?,serial=?,status=? WHERE id=?',(*values,integer(d,'id')))
                    else: db.execute('INSERT INTO machines(line_id,type_id,station,asset_tag,serial,status) VALUES(?,?,?,?,?,?)',values)
                elif action in ('part','edit_part'):
                    if action=='edit_part' and any(k in d for k in ('stock','quantity','delta')): raise Error('Edit details cannot change stock. Use a receipt or inventory adjustment.')
                    details=self.catalog_validation(catalog.part_details,db,d)
                    pid=integer(d,'part_id') if action=='edit_part' else None
                    self.catalog_validation(catalog.unique_sku,db,details['sku'],pid)
                    columns=('sku','name','bin','supplier','supplier_number','cost','threshold','target','lead_days','interval_days')
                    values=tuple(details[k] for k in columns)
                    if action=='part':
                        stock=integer(d,'stock',0)
                        cur=db.execute('INSERT INTO parts(sku,name,bin,supplier,supplier_number,cost,threshold,target,lead_days,interval_days,stock) VALUES(?,?,?,?,?,?,?,?,?,?,?)',(*values,stock))
                        pid=cur.lastrowid
                        for t in details['type_ids']: db.execute('INSERT INTO compatibility VALUES(?,?)',(pid,t))
                        db.execute('INSERT INTO ledger(part_id,delta,reason,actor_id,created,operation_key) VALUES(?,?,?,?,?,?)',(pid,stock,'Opening balance',uid,now(),secrets.token_hex(16)))
                    else:
                        old=db.execute('SELECT * FROM parts WHERE id=?',(pid,)).fetchone()
                        if not old: raise Error('Part not found.',404)
                        before=self.public_part(db,old)
                        revision=integer(d,'revision',0)
                        if revision!=old['revision']: raise Error('This part changed in another session. Reopen its editor before saving.',409)
                        reason=required(d,'change_reason')
                        incompatible=[r['id'] for r in db.execute("SELECT r.id,m.type_id FROM requests r JOIN machines m ON m.id=r.machine_id WHERE r.part_id=? AND r.state IN ('Pending','Approved')",(pid,)) if r['type_id'] not in details['type_ids']]
                        if incompatible: raise Error('Cannot remove compatibility used by active requests '+', '.join('#'+str(r) for r in incompatible)+'. Finish or cancel them first.')
                        cur=db.execute('UPDATE parts SET sku=?,name=?,bin=?,supplier=?,supplier_number=?,cost=?,threshold=?,target=?,lead_days=?,interval_days=?,revision=revision+1 WHERE id=? AND revision=?',(*values,pid,revision))
                        if cur.rowcount!=1: raise Error('Part changed in another session. Reopen its editor.',409)
                        db.execute('DELETE FROM compatibility WHERE part_id=?',(pid,))
                        for t in details['type_ids']: db.execute('INSERT INTO compatibility VALUES(?,?)',(pid,t))
                        self.audit(db,uid,'edit_part',{'part_id':pid,'reason':reason,'before':before,'after':self.public_part(db,db.execute('SELECT * FROM parts WHERE id=?',(pid,)).fetchone())})
                        return {'message':'Part details saved. Stock and completed maintenance were not changed.'}
                elif action=='user':
                    role=required(d,'role'); lead=d.get('lead_id')
                    if role not in ('Administrator','Lead','Technician'): raise Error('Invalid role.')
                    if lead is not None and (type(lead)!=int or lead<1): raise Error('Select a valid lead ID.')
                    if role!='Technician' and lead is not None: raise Error('Lead assignments apply to Technician accounts.')
                    scope=self.validate_scope(db,d.get('building_ids',[]),d.get('line_ids',[]))
                    if lead is not None:
                        if not db.execute("SELECT 1 FROM users WHERE id=? AND role='Lead' AND active=1",(lead,)).fetchone(): raise Error('Select an active Lead account.')
                        if not scopes.covers(db,scopes.grants(db,lead),scope): raise Error('The assigned lead needs access to all selected buildings and lines.')
                    cur=db.execute('INSERT INTO users(username,password,role,lead_id) VALUES(?,?,?,?)',(required(d,'username'),password_hash(required(d,'password')),role,lead))
                    scopes.write(db,cur.lastrowid,scope)
                elif action=='edit_user':
                    target=integer(d,'user_id')
                    if target==uid: raise Error('Another administrator must edit your own role or access.')
                    previous=db.execute('SELECT * FROM users WHERE id=?',(target,)).fetchone()
                    if not previous: raise Error('Account not found.',404)
                    role=required(d,'role')
                    if role not in ('Administrator','Lead','Technician'): raise Error('Invalid role.')
                    old_buildings,old_lines=scopes.grants(db,target)
                    buildings,lines=self.validate_scope(db,d.get('building_ids'),d.get('line_ids',sorted(old_lines)))
                    lead=d.get('lead_id')
                    if lead is not None and (type(lead)!=int or lead<1): raise Error('Select a valid lead ID.')
                    if lead==target: raise Error('An account cannot be its own assigned lead.')
                    if role!='Technician' and lead is not None: raise Error('Lead assignments apply to Technician accounts.')
                    if lead is not None:
                        if not db.execute("SELECT 1 FROM users WHERE id=? AND role='Lead' AND active=1",(lead,)).fetchone(): raise Error('Select an active Lead account.')
                        if not scopes.covers(db,scopes.grants(db,lead),(buildings,lines)): raise Error('The assigned lead needs access to all selected technician buildings and lines.')
                    assigned=db.execute('SELECT id FROM users WHERE lead_id=?',(target,)).fetchall()
                    if assigned and role!='Lead': raise Error('Reassign this lead’s technicians before changing the lead’s role.')
                    for technician in assigned:
                        if not scopes.covers(db,(buildings,lines),scopes.grants(db,technician['id'])): raise Error('This lead still supervises technicians in removed buildings or lines. Reassign them first.')
                    if role!='Lead' and db.execute("SELECT 1 FROM requests WHERE lead_id=? AND state='Pending'",(target,)).fetchone(): raise Error('Review or reassign pending approvals before changing this lead’s role.')
                    pending=db.execute("SELECT r.id,l.building_id,m.line_id FROM requests r JOIN machines m ON m.id=r.machine_id JOIN lines l ON l.id=m.line_id WHERE r.technician_id=? AND r.state='Pending'",(target,)).fetchall()
                    if pending and role!='Technician': raise Error('Finish or cancel this account’s pending early requests before changing its role.')
                    if pending and (lead is None or any(not scopes.allows((buildings,lines),r['building_id'],r['line_id']) for r in pending)): raise Error('Pending early requests need a lead and access to their machine buildings. Finish or cancel them first.')
                    changed=previous['role']!=role or previous['lead_id']!=lead or old_buildings!=buildings or old_lines!=lines
                    if changed:
                        db.execute('UPDATE users SET role=?,lead_id=?,version=version+1 WHERE id=?',(role,lead,target))
                        scopes.write(db,target,(buildings,lines))
                        db.execute('DELETE FROM sessions WHERE user_id=?',(target,))
                        if previous['lead_id']!=lead:
                            for r in pending:
                                db.execute('UPDATE requests SET lead_id=? WHERE id=?',(lead,r['id']))
                                db.execute('INSERT INTO notifications(user_id,message,created) VALUES(?,?,?)',(lead,f"Early replacement #{r['id']} reassigned to you for review.",now()))
                                if previous['lead_id']:
                                    db.execute('INSERT INTO notifications(user_id,message,created) VALUES(?,?,?)',(previous['lead_id'],f"Early replacement #{r['id']} reassigned to another lead.",now()))
                    self.audit(db,uid,'edit_user',{'user_id':target,'before':{'role':previous['role'],'lead_id':previous['lead_id'],'building_ids':sorted(old_buildings),'line_ids':sorted(old_lines)},'after':{'role':role,'lead_id':lead,'building_ids':sorted(buildings),'line_ids':sorted(lines)},'pending_reassigned':[r['id'] for r in pending] if previous['lead_id']!=lead else []})
                    return {'message':'Account updated. Changed permissions revoke existing sessions.' if changed else 'No changes.'}
                elif action in ('reset','disable'):
                    target=integer(d,'user_id')
                    if target==uid: raise Error('Use your own password change; do not disable your current account.')
                    if action=='reset': db.execute('UPDATE users SET password=?,must_change=1,version=version+1 WHERE id=?',(password_hash(required(d,'password')),target))
                    else:
                        active=integer(d,'active',0)
                        if active not in (0,1): raise Error('active must be 0 or 1.')
                        db.execute('UPDATE users SET active=?,version=version+1 WHERE id=?',(active,target))
                    db.execute('DELETE FROM sessions WHERE user_id=?',(target,))
                else:
                    pid=integer(d,'part_id'); delta=integer(d,'quantity') if action=='receipt' else 0
                    if action=='adjust':
                        delta=d.get('delta')
                        if type(delta)!=int or delta==0: raise Error('delta must be a nonzero integer.')
                    key=required(d,'operation_key'); reason=required(d,'reason')
                    if db.execute('SELECT 1 FROM ledger WHERE operation_key=?',(key,)).fetchone(): raise Error('This stock operation was already recorded.',409)
                    cur=db.execute('UPDATE parts SET stock=stock+? WHERE id=? AND stock+?>=0',(delta,pid,delta))
                    if cur.rowcount!=1: raise Error('Part missing or insufficient stock.')
                    db.execute('INSERT INTO ledger(part_id,delta,reason,actor_id,created,operation_key) VALUES(?,?,?,?,?,?)',(pid,delta,reason,uid,now(),key))
                self.audit(db,uid,action,{k:v for k,v in d.items() if 'password' not in k})
                return {'message':'Saved.'}
            if action=='request':
                mid=integer(d,'machine_id'); pid=integer(d,'part_id'); qty=integer(d,'quantity'); m=self.machine(db,u,mid)
                if m['status']=='Retired': raise Error('Retired machines cannot receive replacement work.')
                p=db.execute('SELECT p.* FROM parts p JOIN compatibility c ON c.part_id=p.id WHERE p.id=? AND c.type_id=?',(pid,m['type_id'])).fetchone()
                if not p: raise Error('This part is incompatible with this machine.')
                if qty>p['stock']: raise Error('Insufficient shared stock.')
                reason=required(d,'reason'); key=required(d,'operation_key')
                last=db.execute('SELECT MAX(replaced) FROM maintenance WHERE machine_id=? AND part_id=?',(mid,pid)).fetchone()[0]
                early=bool(last and (datetime.now(timezone.utc)-datetime.fromisoformat(last)).total_seconds()<p['interval_days']*86400)
                lead=u['lead_id']
                if early:
                    if not d.get('early_explanation','').strip(): raise Error('Early replacement requires an explanation.')
                    if not lead or lead==uid or not db.execute("SELECT 1 FROM users WHERE id=? AND active=1 AND role='Lead'",(lead,)).fetchone(): raise Error('No active assigned lead. Ask an administrator to assign one; request blocked.')
                    lead_user=db.execute('SELECT * FROM users WHERE id=?',(lead,)).fetchone(); self.machine(db,lead_user,mid)
                cur=db.execute('INSERT INTO requests(machine_id,part_id,quantity,technician_id,lead_id,early,state,reason,notes,created,operation_key) VALUES(?,?,?,?,?,?,?,?,?,?,?)',(mid,pid,qty,uid,lead,int(early),'Pending' if early else 'Approved',reason,d.get('notes','')+ ('\nEarly explanation: '+d['early_explanation'] if early else ''),now(),key))
                if early: db.execute('INSERT INTO notifications(user_id,message,created) VALUES(?,?,?)',(lead,f'Early replacement #{cur.lastrowid} requires review.',now()))
                self.audit(db,uid,'request',{'request_id':cur.lastrowid})
                return {'id':cur.lastrowid,'state':'Pending' if early else 'Approved','early':early}
            if action in ('review','complete','cancel'):
                rid=integer(d,'request_id'); r=db.execute('SELECT * FROM requests WHERE id=?',(rid,)).fetchone()
                if not r: raise Error('Request not found.',404)
                m=self.machine(db,u,r['machine_id'])
                if action=='review':
                    if uid==r['technician_id']: raise Error('You cannot approve your own request.',403)
                    if u['role']!='Lead' or uid!=r['lead_id']: raise Error('Only the assigned lead can review.',403)
                    if r['state']!='Pending': raise Error('Request is no longer pending.',409)
                    decision=required(d,'decision')
                    if decision not in ('Approved','Rejected'): raise Error('Invalid decision.')
                    db.execute('UPDATE requests SET state=?,reviewer_id=?,review_comment=?,reviewed=? WHERE id=?',(decision,uid,required(d,'comment'),now(),rid))
                    db.execute('INSERT INTO notifications(user_id,message,created) VALUES(?,?,?)',(r['technician_id'],f'Request #{rid}: {decision}',now()))
                elif action=='cancel':
                    if uid!=r['technician_id'] and u['role']!='Administrator': raise Error('Only the requester or administrator can cancel.',403)
                    if r['state'] not in ('Pending','Approved'): raise Error('Cannot cancel this request.')
                    db.execute("UPDATE requests SET state='Cancelled' WHERE id=?",(rid,))
                else:
                    if uid!=r['technician_id']: raise Error('Only the authenticated requester can record completion.',403)
                    if r['state']!='Approved': raise Error('Only approved work can be completed.',409)
                    if m['status']=='Retired': raise Error('Retired machine; cancel the request.')
                    if not db.execute('SELECT 1 FROM compatibility WHERE part_id=? AND type_id=?',(r['part_id'],m['type_id'])).fetchone(): raise Error('Machine type changed; part is no longer compatible. Cancel this request.')
                    # Prevent a second normal request bypassing an interval established by concurrent completion.
                    p=db.execute('SELECT * FROM parts WHERE id=?',(r['part_id'],)).fetchone()
                    last=db.execute('SELECT MAX(replaced) FROM maintenance WHERE machine_id=? AND part_id=?',(m['id'],p['id'])).fetchone()[0]
                    if not r['early'] and last and (datetime.now(timezone.utc)-datetime.fromisoformat(last)).total_seconds()<p['interval_days']*86400: raise Error('A recent replacement now makes this early. Cancel and submit for lead review.')
                    cur=db.execute('UPDATE parts SET stock=stock-? WHERE id=? AND stock>=?',(r['quantity'],r['part_id'],r['quantity']))
                    if cur.rowcount!=1: raise Error('Insufficient stock at completion; no stock was deducted.')
                    stamp=now()
                    db.execute('INSERT INTO maintenance(request_id,machine_id,part_id,technician_id,quantity,unit_cost,replaced,location_snapshot,reason,early) VALUES(?,?,?,?,?,?,?,?,?,?)',(rid,m['id'],r['part_id'],uid,r['quantity'],p['cost'],stamp,self.name(m),r['reason'],r['early']))
                    db.execute('INSERT INTO ledger(part_id,delta,reason,actor_id,created,operation_key) VALUES(?,?,?,?,?,?)',(r['part_id'],-r['quantity'],f'Replacement #{rid}',uid,stamp,f'complete:{rid}'))
                    db.execute("UPDATE requests SET state='Completed' WHERE id=?",(rid,))
                self.audit(db,uid,action,{'request_id':rid}); return {'message':'Saved.'}
            raise Error('Unknown action.',404)
    def seed(self):
        with self.tx() as db:
            if db.execute('SELECT 1 FROM buildings').fetchone(): raise Error('Seed only an empty equipment database.')
            for i in range(1,10): db.execute('INSERT INTO buildings(code,name) VALUES(?,?)',(f'B{i:02}',f'Building {i}'))
            db.execute("INSERT INTO lines(building_id,code) VALUES(1,'L01'),(1,'L02'),(3,'L02')")
            db.execute("INSERT INTO types(name) VALUES('DIMM Press'),('ACOS Station'),('Conveyor')")
            db.execute("INSERT INTO machines(line_id,type_id,station,asset_tag,serial,status) VALUES(1,1,'01','DEMO-001','SAMPLE-001','Operating'),(2,2,'04','DEMO-002','SAMPLE-002','Maintenance'),(3,1,'04','DEMO-003','SAMPLE-003','Operating'),(3,3,'05','DEMO-004','SAMPLE-004','Stopped')")
            db.execute("INSERT INTO parts(sku,name,bin,cost,stock,threshold,target,interval_days) VALUES('DEMO-SEAL','Pneumatic seal kit','B01 / A-12',24.50,12,5,20,90),('DEMO-FILTER','Air filter','B01 / A-13',18,3,4,12,30),('DEMO-BELT','Drive belt','B03 / C-02',82,6,2,10,180)")
            db.execute('INSERT INTO compatibility VALUES(1,1),(1,2),(2,1),(2,2),(3,3)')
            for p in db.execute('SELECT id,stock FROM parts').fetchall(): db.execute('INSERT INTO ledger(part_id,delta,reason,created,operation_key) VALUES(?,?,?,?,?)',(p['id'],p['stock'],'Sample opening balance',now(),f"seed:{p['id']}"))
