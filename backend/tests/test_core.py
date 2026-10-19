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
            for name,role,lead in [('admin','Administrator',None),('lead','Lead',None),('tech','Technician',2),('other','Technician',2),('reviewer','Administrator',None)]: db.execute('INSERT INTO users(username,password,role,lead_id,must_change) VALUES(?,?,?,?,0)',(name,self.hashed,role,lead))
            for uid in (2,3,4):
                for bid in (1,3): db.execute('INSERT INTO access VALUES(?,?)',(uid,bid))
        self.tokens={u:self.store.login(u,'Example-long-password-2026')['token'] for u in ('admin','lead','tech','other','reviewer')}
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
        def reserve(user):
            try: return self.request(user=user,mid=1 if user=='tech' else 3)
            except Error: return None
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool: outcomes=list(pool.map(reserve,['tech','other']))
        self.assertEqual(sum(r is not None for r in outcomes),1)
        for user,r in zip(['tech','other'],outcomes):
            if r: self.act(user,'complete',request_id=r['id'])
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
        self.assertEqual(next(r for r in self.store.state(self.tokens['lead'])['requests'] if r['id']==early['id'])['state'],'Pending')
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
            db.execute('DROP TABLE reorder_deliveries');db.execute('DROP TABLE reorders');db.execute('DROP TABLE line_access');db.execute('ALTER TABLE parts DROP COLUMN revision');db.execute('ALTER TABLE types DROP COLUMN revision');db.execute('PRAGMA user_version=1')
        reopened=Store(self.store.path)
        after=reopened.state(self.tokens['admin'])
        self.assertEqual(after['history'],before['history'])
        self.assertEqual(after['parts'],before['parts'])
        self.assertEqual(after['users'],before['users'])
        self.assertEqual(len(reopened.state(self.tokens['tech'])['machines']),4)
        with reopened.tx() as db:self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],7)
    def test_migration_rerun_keeps_line_grants_and_version(self):
        self.line_only()
        reopened=Store(self.store.path)
        self.assertEqual(reopened.state(self.tokens['tech'])['user']['line_ids'],[1])
        with reopened.tx() as db:self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],7)
    def test_http_forbidden_line_request_is_rejected(self):
        self.line_only()
        server=serve(self.store,0);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            req=Request(f'http://127.0.0.1:{server.server_port}/actions/request',data=json.dumps({'machine_id':2,'part_id':1,'quantity':1,'reason':'Forbidden sibling','operation_key':'http-forbidden'}).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+self.tokens['tech']})
            with self.assertRaises(HTTPError) as result:urlopen(req)
            self.assertEqual(result.exception.code,403)
            self.assertEqual(self.store.state(self.tokens['admin'])['requests'],[])
        finally:server.shutdown();server.server_close();thread.join()

    def edit_part_data(self,part_id=1,**changes):
        p=next(p for p in self.store.state(self.tokens['admin'])['parts'] if p['id']==part_id)
        keys=('sku','name','bin','supplier','supplier_number','cost','threshold','target','lead_days','interval_days','type_ids','revision')
        return {**{k:p[k] for k in keys},'part_id':part_id,'change_reason':'Catalog corrected',**changes}
    def test_type_rename_preserves_links_and_historical_location(self):
        r=self.request();self.act('tech','complete',request_id=r['id'])
        old=self.store.state(self.tokens['admin'])['history'][0]['location_snapshot']
        self.act('admin','type',id=1,revision=0,name='Precision DIMM Press')
        state=self.store.state(self.tokens['admin'])
        self.assertEqual(next(m for m in state['machines'] if m['id']==1)['type'],'Precision DIMM Press')
        self.assertEqual(next(p for p in state['parts'] if p['id']==1)['type_ids'],[1,2])
        self.assertEqual(state['history'][0]['location_snapshot'],old)
        self.assertEqual(next(t for t in state['types'] if t['id']==1)['revision'],1)
    def test_type_rename_checks_permission_duplicate_name_and_revision(self):
        with self.assertRaises(Error):self.act('tech','type',id=1,revision=0,name='Forbidden')
        with self.assertRaises(Error):self.act('admin','type',id=1,revision=0,name='acos station')
        with self.assertRaises(Error):self.act('admin','type',id=1,revision=0,name='  ')
        self.act('admin','type',id=1,revision=0,name='Press V2')
        with self.assertRaises(Error) as caught:self.act('admin','type',id=1,revision=0,name='Press V3')
        self.assertEqual(caught.exception.status,409)
    def test_part_edit_preserves_stock_ledger_and_completed_records(self):
        r=self.request();self.act('tech','complete',request_id=r['id'])
        with self.store.tx() as db:
            history=[dict(x) for x in db.execute('SELECT * FROM maintenance')]
            ledger=[dict(x) for x in db.execute('SELECT * FROM ledger')]
            stock=db.execute('SELECT stock FROM parts WHERE id=1').fetchone()[0]
        self.act('admin','edit_part',**self.edit_part_data(name='Updated seal kit',sku='new-seal',bin='B01 / A-20',supplier='Supplier Co',supplier_number='S-001',cost=55.25,threshold=3,target=25,lead_days=7,interval_days=60,type_ids=[1,2]))
        state=self.store.state(self.tokens['admin']);p=next(p for p in state['parts'] if p['id']==1)
        self.assertEqual(p['stock'],stock);self.assertEqual(p['sku'],'NEW-SEAL');self.assertEqual(p['supplier'],'Supplier Co');self.assertEqual(p['revision'],1)
        with self.store.tx() as db:
            self.assertEqual([dict(x) for x in db.execute('SELECT * FROM maintenance')],history)
            self.assertEqual([dict(x) for x in db.execute('SELECT * FROM ledger')],ledger)
            audit=db.execute("SELECT detail FROM audit WHERE action='edit_part'").fetchone()
            self.assertEqual(json.loads(audit['detail'])['reason'],'Catalog corrected')
        early=self.request(key='new-cost',early_explanation='Defect')
        self.act('lead','review',request_id=early['id'],decision='Approved',comment='Verified')
        self.act('tech','complete',request_id=early['id'])
        costs=[h['unit_cost'] for h in self.store.state(self.tokens['admin'])['history']]
        self.assertEqual(costs,[55.25,24.5])
    def test_part_edit_rejects_duplicate_sku_and_invalid_metadata_atomically(self):
        original=self.store.state(self.tokens['admin'])['parts']
        for change in [dict(sku='demo-filter'),dict(name=''),dict(bin=''),dict(cost=-1),dict(cost=True),dict(cost=float('nan')),dict(cost=1.234),dict(target=0),dict(interval_days=0),dict(lead_days=-1),dict(type_ids=[]),dict(type_ids=[True]),dict(type_ids=[999]),dict(change_reason='')]:
            with self.assertRaises(Error):self.act('admin','edit_part',**self.edit_part_data(**change))
        self.assertEqual(self.store.state(self.tokens['admin'])['parts'],original)
    def test_part_edit_cannot_change_stock(self):
        for change in [dict(stock=500),dict(quantity=500),dict(delta=500)]:
            with self.assertRaises(Error):self.act('admin','edit_part',**self.edit_part_data(**change))
        self.assertEqual(next(p for p in self.store.state(self.tokens['admin'])['parts'] if p['id']==1)['stock'],12)
    def test_part_edit_blocked_for_technician(self):
        for user in ['tech']:
            with self.assertRaises(Error):self.act(user,'edit_part',**self.edit_part_data(name='Unauthorized'))
    def test_part_compatibility_removal_checks_approved_and_pending_work(self):
        approved=self.request()
        with self.assertRaises(Error):self.act('admin','edit_part',**self.edit_part_data(type_ids=[2]))
        self.act('tech','complete',request_id=approved['id'])
        pending=self.request(key='pending-compatibility',early_explanation='Failure')
        with self.assertRaises(Error):self.act('admin','edit_part',**self.edit_part_data(type_ids=[2]))
        self.act('tech','cancel',request_id=pending['id'])
        self.act('admin','edit_part',**self.edit_part_data(type_ids=[2]))
        self.assertNotIn(1,[p['id'] for p in next(m for m in self.store.state(self.tokens['admin'])['machines'] if m['id']==1)['parts']])
        self.assertEqual(len(self.store.state(self.tokens['admin'])['history']),1)
    def test_part_compatibility_addition_uses_same_shared_balance(self):
        self.act('admin','edit_part',**self.edit_part_data(type_ids=[1,2,3]))
        machines=self.store.state(self.tokens['admin'])['machines']
        self.assertIn(1,[p['id'] for p in next(m for m in machines if m['id']==4)['parts']])
        self.assertEqual(len(self.store.state(self.tokens['admin'])['parts']),3)
        r=self.request(mid=4);self.act('tech','complete',request_id=r['id'])
        machines=self.store.state(self.tokens['admin'])['machines']
        for machine in [1,4]:
            self.assertEqual(next(p for p in next(m for m in machines if m['id']==machine)['parts'] if p['id']==1)['stock'],11)
    def test_part_concurrent_metadata_edit_rejects_stale_writer(self):
        data=self.edit_part_data()
        def edit(name):
            try:self.act('admin','edit_part',**{**data,'name':name});return True
            except Error as e:self.assertEqual(e.status,409);return False
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:result=list(pool.map(edit,['First edit','Second edit']))
        self.assertEqual(sum(result),1)
        self.assertEqual(next(p for p in self.store.state(self.tokens['admin'])['parts'] if p['id']==1)['revision'],1)
    def test_receipts_during_catalog_edit_are_not_overwritten(self):
        data=self.edit_part_data()
        self.act('admin','receipt',part_id=1,quantity=5,reason='delivery',operation_key='catalog-receipt')
        self.act('admin','edit_part',**{**data,'name':'Edited after receipt'})
        self.assertEqual(next(p for p in self.store.state(self.tokens['admin'])['parts'] if p['id']==1)['stock'],17)
    def test_changed_interval_rechecked_at_completion(self):
        first=self.request();self.act('tech','complete',request_id=first['id'])
        # Set historical time to 100 days ago to exercise a normal request at 90 days.
        with self.store.tx() as db:db.execute('UPDATE maintenance SET replaced=? WHERE request_id=?',((datetime.now(timezone.utc)-timedelta(days=100)).isoformat(),first['id']))
        normal=self.request(key='normal-100-days')
        self.act('admin','edit_part',**self.edit_part_data(interval_days=180))
        with self.assertRaises(Error):self.act('tech','complete',request_id=normal['id'])
        self.assertEqual(next(r for r in self.store.state(self.tokens['admin'])['requests'] if r['id']==normal['id'])['state'],'Approved')
    def test_catalog_v2_upgrade_preserves_data_and_line_grants(self):
        self.line_only()
        before=self.store.state(self.tokens['admin'])
        with self.store.tx() as db:
            db.execute('DROP TABLE reorder_deliveries');db.execute('DROP TABLE reorders');db.execute('ALTER TABLE parts DROP COLUMN revision');db.execute('ALTER TABLE types DROP COLUMN revision');db.execute('PRAGMA user_version=2')
        upgraded=Store(self.store.path)
        self.assertEqual(upgraded.state(self.tokens['admin']),before)
        self.assertEqual(upgraded.state(self.tokens['tech'])['user']['line_ids'],[1])
    def test_catalog_v3_restart_preserves_revisions(self):
        self.act('admin','edit_part',**self.edit_part_data(name='Renamed'))
        self.act('admin','type',id=1,revision=0,name='Type renamed')
        restarted=Store(self.store.path)
        state=restarted.state(self.tokens['admin'])
        self.assertEqual(next(p for p in state['parts'] if p['id']==1)['revision'],1)
        self.assertEqual(next(t for t in state['types'] if t['id']==1)['revision'],1)
    def test_http_part_update_and_permission_enforcement(self):
        server=serve(self.store,0);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        def update(token,data):
            req=Request(f'http://127.0.0.1:{server.server_port}/actions/edit_part',data=json.dumps(data).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+token})
            with urlopen(req) as response:return json.load(response)
        try:
            data=self.edit_part_data(name='HTTP updated part')
            with self.assertRaises(HTTPError) as caught:update(self.tokens['tech'],data)
            self.assertEqual(caught.exception.code,403)
            update(self.tokens['admin'],data)
            self.assertEqual(next(p for p in self.store.state(self.tokens['admin'])['parts'] if p['id']==1)['name'],'HTTP updated part')
        finally:server.shutdown();server.server_close();thread.join()

    def reorder(self,user='admin',quantity=10,key='purchase-first',part_id=1,**extra):
        return self.act(user,'reorder_request',part_id=part_id,quantity=quantity,reason='Replenish spare parts',operation_key=key,**extra)
    def order_ready(self,quantity=10,key='purchase-first',part_id=1):
        r=self.reorder(quantity=quantity,key=key,part_id=part_id)
        self.act('reviewer','reorder_review',reorder_id=r['id'],revision=0,decision='Approved',comment='Approved replenishment')
        self.act('admin','reorder_order',reorder_id=r['id'],revision=1,po_reference='PO-001')
        return r['id']
    def receive(self,rid,quantity=4,reference='SLIP-1',key='delivery-first',user='admin',**extra):
        return self.act(user,'reorder_receive',reorder_id=rid,quantity=quantity,delivery_reference=reference,operation_key=key,notes='Inspected delivery',**extra)
    def test_reorder_approval_and_ordering_do_not_change_stock(self):
        before=self.store.state(self.tokens['admin'])['parts']
        r=self.reorder()
        self.assertEqual(self.store.state(self.tokens['admin'])['reorders'][0]['state'],'Requested')
        self.act('reviewer','reorder_review',reorder_id=r['id'],revision=0,decision='Approved',comment='Yes')
        self.act('admin','reorder_order',reorder_id=r['id'],revision=1,po_reference='PO-123')
        after=self.store.state(self.tokens['admin'])['parts']
        self.assertEqual([p['stock'] for p in after],[p['stock'] for p in before])
        self.assertEqual(self.store.state(self.tokens['admin'])['history'],[])
    def test_partial_and_final_deliveries_record_atomic_stock_and_identity(self):
        rid=self.order_ready()
        result=self.receive(rid,quantity=4,received_by=4)
        self.assertEqual(result['state'],'Partially received');self.assertEqual(result['remaining_quantity'],6)
        result=self.receive(rid,quantity=6,reference='SLIP-2',key='delivery-second')
        self.assertEqual(result['state'],'Received')
        state=self.store.state(self.tokens['admin']);part=next(p for p in state['parts'] if p['id']==1)
        self.assertEqual(part['stock'],22);self.assertEqual(len(state['deliveries']),2)
        self.assertTrue(all(d['received_by']==1 for d in state['deliveries']))
        with self.store.tx() as db:self.assertEqual(db.execute("SELECT SUM(delta) FROM ledger WHERE operation_key LIKE 'reorder-receipt:%'").fetchone()[0],10)
        self.assertEqual(state['history'],[])
    def test_duplicate_reorder_and_receipt_keys_and_references(self):
        rid=self.order_ready()
        with self.assertRaises(Error):self.reorder()
        self.receive(rid)
        with self.assertRaises(Error):self.receive(rid,reference='SLIP-NEW')
        with self.assertRaises(Error):self.receive(rid,reference='slip-1',key='delivery-new')
        state=self.store.state(self.tokens['admin'])
        self.assertEqual(next(p for p in state['parts'] if p['id']==1)['stock'],16)
        self.assertEqual(len(state['deliveries']),1)
    def test_over_receiving_and_concurrent_final_deliveries(self):
        rid=self.order_ready(quantity=5)
        with self.assertRaises(Error):self.receive(rid,quantity=6)
        self.assertEqual(self.store.state(self.tokens['admin'])['deliveries'],[])
        def receiving(n):
            try:self.receive(rid,quantity=5,reference=f'SLIP-{n}',key=f'CONCURRENT-{n}');return True
            except Error:return False
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(receiving,[1,2]))
        self.assertEqual(sum(results),1)
        state=self.store.state(self.tokens['admin'])
        self.assertEqual(next(p for p in state['parts'] if p['id']==1)['stock'],17)
        self.assertEqual(state['reorders'][0]['received_quantity'],5)
        self.assertEqual(len(state['deliveries']),1)
    def test_purchasing_roles_and_self_approval(self):
        with self.assertRaises(Error):self.reorder(user='tech')
        r=self.reorder(user='admin')
        with self.assertRaises(Error):self.act('admin','reorder_review',reorder_id=r['id'],revision=0,decision='Approved',comment='Self')
        self.act('lead','reorder_review',reorder_id=r['id'],revision=0,decision='Approved',comment='Lead review')
        rid=self.order_ready(key='lead-order')
        for user in ['tech']:
            with self.assertRaises(Error):self.receive(rid,user=user,key='not-admin-'+user)
        self.assertEqual(self.store.state(self.tokens['tech'])['reorders'],[])
        self.assertEqual(self.store.state(self.tokens['tech'])['deliveries'],[])
    def test_rejected_and_unordered_reorders_cannot_receive(self):
        r=self.reorder()
        with self.assertRaises(Error):self.receive(r['id'])
        self.act('reviewer','reorder_review',reorder_id=r['id'],revision=0,decision='Rejected',comment='Not needed')
        with self.assertRaises(Error):self.receive(r['id'])
        with self.assertRaises(Error):self.act('admin','reorder_order',reorder_id=r['id'],revision=1,po_reference='PO')
        approved=self.reorder(key='approved')
        self.act('reviewer','reorder_review',reorder_id=approved['id'],revision=0,decision='Approved',comment='Yes')
        with self.assertRaises(Error):self.receive(approved['id'],key='approved-delivery')
    def test_cancel_partial_order_keeps_received_stock_and_history(self):
        rid=self.order_ready()
        self.receive(rid,quantity=3)
        self.act('admin','reorder_cancel',reorder_id=rid,revision=3,reason='Supplier cannot deliver remainder')
        state=self.store.state(self.tokens['admin'])
        self.assertEqual(state['reorders'][0]['state'],'Cancelled');self.assertEqual(state['reorders'][0]['received_quantity'],3)
        part=next(p for p in state['parts'] if p['id']==1)
        self.assertEqual(part['stock'],15);self.assertEqual(part['outstanding_order_quantity'],0);self.assertEqual(part['suggested_order_quantity'],5)
        self.assertEqual(len(state['deliveries']),1)
        with self.assertRaises(Error):self.receive(rid,quantity=7,reference='SLIP-2',key='late')
    def test_lead_can_cancel_any_active_reorder(self):
        r=self.reorder(user='lead')
        self.act('lead','reorder_cancel',reorder_id=r['id'],revision=0,reason='No longer needed')
        r=self.reorder(user='admin',key='another-requester')
        self.act('lead','reorder_cancel',reorder_id=r['id'],revision=0,reason='Purchasing cancelled')
        rid=self.order_ready(key='ordered-lead')
        self.act('lead','reorder_cancel',reorder_id=rid,revision=2,reason='Supplier cancellation')
    def test_purchase_revision_blocks_stale_approval_and_ordering(self):
        r=self.reorder()
        self.act('reviewer','reorder_review',reorder_id=r['id'],revision=0,decision='Approved',comment='First')
        with self.assertRaises(Error) as caught:self.act('reviewer','reorder_review',reorder_id=r['id'],revision=0,decision='Rejected',comment='Stale')
        self.assertEqual(caught.exception.status,409)
        with self.assertRaises(Error):self.act('admin','reorder_order',reorder_id=r['id'],revision=0,po_reference='PO-stale')
    def test_reorder_suggestion_accounts_for_pending_and_outstanding(self):
        def part():return next(p for p in self.store.state(self.tokens['admin'])['parts'] if p['id']==1)
        self.assertEqual(part()['suggested_order_quantity'],8)
        r=self.reorder(quantity=5)
        self.assertEqual(part()['pending_reorder_quantity'],5);self.assertEqual(part()['suggested_order_quantity'],3)
        self.act('reviewer','reorder_review',reorder_id=r['id'],revision=0,decision='Approved',comment='Yes')
        self.assertEqual(part()['pending_reorder_quantity'],0);self.assertEqual(part()['outstanding_order_quantity'],5)
        self.act('admin','reorder_order',reorder_id=r['id'],revision=1,po_reference='PO')
        self.receive(r['id'],quantity=2)
        self.assertEqual(part()['outstanding_order_quantity'],3);self.assertEqual(part()['stock'],14);self.assertEqual(part()['suggested_order_quantity'],3)
    def test_purchase_snapshots_survive_part_edits_and_ignore_spoofed_identity(self):
        r=self.reorder(user='lead',requested_by=4,unit_cost_snapshot=0,supplier_snapshot='Spoof')
        self.act('admin','edit_part',**self.edit_part_data(supplier='New supplier',cost=99))
        saved=self.store.state(self.tokens['admin'])['reorders'][0]
        self.assertEqual(saved['requested_by'],2);self.assertEqual(saved['unit_cost_snapshot'],24.5);self.assertEqual(saved['supplier_snapshot'],'')
    def test_invalid_purchase_inputs_and_cancel_reasons(self):
        for quantity in [0,-1,True,'2']:
            with self.assertRaises(Error):self.reorder(quantity=quantity)
        r=self.reorder()
        with self.assertRaises(Error):self.act('lead','reorder_cancel',reorder_id=r['id'],revision=0,reason='')
        rid=self.order_ready(key='valid')
        for q in [0,-1,True,'2']:
            with self.assertRaises(Error):self.receive(rid,quantity=q)
        self.assertEqual(self.store.state(self.tokens['admin'])['deliveries'],[])
    def test_v3_migration_and_v4_restarts_preserve_orders(self):
        before=self.store.state(self.tokens['admin'])
        with self.store.tx() as db:
            db.execute('DROP TABLE reorder_deliveries');db.execute('DROP TABLE reorders');db.execute('PRAGMA user_version=3')
        self.store=Store(self.store.path)
        self.assertEqual(self.store.state(self.tokens['admin']),before)
        rid=self.order_ready();self.receive(rid)
        before=self.store.state(self.tokens['admin'])
        reopened=Store(self.store.path)
        self.assertEqual(reopened.state(self.tokens['admin']),before)
        with reopened.tx() as db:self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],7)
    def test_purchase_notifications_and_audit_not_duplicated_by_retry(self):
        r=self.reorder()
        admins=self.store.state(self.tokens['admin'])['notifications']
        with self.assertRaises(Error):self.reorder()
        self.assertEqual(self.store.state(self.tokens['admin'])['notifications'],admins)
        self.act('reviewer','reorder_review',reorder_id=r['id'],revision=0,decision='Approved',comment='Yes')
        self.assertTrue(any('Approved' in n['message'] for n in self.store.state(self.tokens['admin'])['notifications']))
        with self.store.tx() as db:self.assertEqual(db.execute("SELECT COUNT(*) FROM audit WHERE action='reorder_request'").fetchone()[0],1)
    def test_http_purchase_flow_through_partial_and_complete_receiving(self):
        server=serve(self.store,0);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        def api(action,data,user):
            req=Request(f'http://127.0.0.1:{server.server_port}/actions/{action}',data=json.dumps(data).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+self.tokens[user]})
            with urlopen(req) as response:return json.load(response)
        try:
            r=api('reorder_request',{'part_id':1,'quantity':5,'reason':'HTTP replenish','operation_key':'http-order'},'lead')
            self.assertEqual(r['state'],'Approved')
            api('reorder_order',{'reorder_id':r['id'],'revision':0,'po_reference':'HTTP-PO'},'admin')
            result=api('reorder_receive',{'reorder_id':r['id'],'quantity':2,'delivery_reference':'HTTP-SLIP1','operation_key':'http-delivery1'},'admin')
            self.assertEqual(result['state'],'Partially received')
            result=api('reorder_receive',{'reorder_id':r['id'],'quantity':3,'delivery_reference':'HTTP-SLIP2','operation_key':'http-delivery2'},'admin')
            self.assertEqual(result['state'],'Received')
        finally:server.shutdown();server.server_close();thread.join()

    def part_balance(self,pid=1):
        return next(p for p in self.store.state(self.tokens['admin'])['parts'] if p['id']==pid)
    def active_alerts(self,user='admin',kind=None):
        return [a for a in self.store.state(self.tokens[user])['alerts'] if a['resolved'] is None and (kind is None or a['kind']==kind)]
    def test_lead_reorder_bypass_is_audited_without_stock_or_ordering(self):
        r=self.reorder(user='lead',requested_by=1,state='Requested')
        self.assertEqual(r['state'],'Approved')
        saved=self.store.state(self.tokens['admin'])['reorders'][0]
        self.assertEqual(saved['reviewed_by'],2);self.assertEqual(saved['revision'],0)
        self.assertEqual(self.part_balance()['stock'],12)
        self.assertTrue(any('ready for ordering' in n['message'] for n in self.store.state(self.tokens['admin'])['notifications']))
        with self.assertRaises(Error): self.act('admin','reorder_review',reorder_id=r['id'],revision=0,decision='Rejected',comment='Review no longer needed')
        self.act('lead','reorder_order',reorder_id=r['id'],revision=0,po_reference='LEAD-PO')
        self.receive(r['id'],quantity=10)
        self.assertEqual(self.part_balance()['stock'],22)
        with self.store.tx() as db:
            detail=json.loads(db.execute("SELECT detail FROM audit WHERE action='reorder_request'").fetchone()[0])
            self.assertEqual(detail['approval_policy'],'Lead bypass')
    def test_approved_work_reserves_cancel_releases_without_changing_stock(self):
        r=self.act('tech','request',machine_id=1,part_id=1,quantity=7,reason='Service',operation_key='reserve-seven')
        p=self.part_balance();self.assertEqual((p['stock'],p['reserved_quantity'],p['available_quantity']),(12,7,5))
        self.assertEqual(p['suggested_order_quantity'],15)
        self.act('tech','cancel',request_id=r['id'])
        p=self.part_balance();self.assertEqual((p['stock'],p['reserved_quantity'],p['available_quantity']),(12,0,12))
    def test_completion_consumes_own_reservation_and_keeps_others(self):
        one=self.request();two=self.request(user='other',mid=3)
        self.act('tech','complete',request_id=one['id'])
        p=self.part_balance();self.assertEqual((p['stock'],p['reserved_quantity'],p['available_quantity']),(11,1,10))
        self.act('other','complete',request_id=two['id'])
        self.assertEqual(self.part_balance()['reserved_quantity'],0)
    def test_pending_work_reserves_only_at_approval_and_rechecks_capacity(self):
        done=self.request();self.act('tech','complete',request_id=done['id'])
        early=self.act('tech','request',machine_id=1,part_id=1,quantity=11,reason='Failure',early_explanation='Broken seal',operation_key='early-eleven')
        self.assertEqual(self.part_balance()['reserved_quantity'],0)
        other=self.act('other','request',machine_id=3,part_id=1,quantity=11,reason='Service',operation_key='other-eleven')
        with self.assertRaises(Error):self.act('lead','review',request_id=early['id'],decision='Approved',comment='Repair')
        self.act('other','cancel',request_id=other['id'])
        self.act('lead','review',request_id=early['id'],decision='Approved',comment='Repair')
        self.assertEqual(self.part_balance()['reserved_quantity'],11)
        self.act('tech','cancel',request_id=early['id'])
        self.assertEqual(self.part_balance()['reserved_quantity'],0)
    def test_adjustment_cannot_consume_reserved_stock_but_receipt_adds_available(self):
        self.act('tech','request',machine_id=1,part_id=1,quantity=10,reason='Service',operation_key='reserve-ten')
        with self.assertRaises(Error):self.act('admin','adjust',part_id=1,delta=-3,reason='Count',operation_key='bad-adjust')
        self.act('admin','adjust',part_id=1,delta=-2,reason='Count',operation_key='good-adjust')
        self.act('admin','receipt',part_id=1,quantity=3,reason='Delivery',operation_key='after-reserve')
        p=self.part_balance();self.assertEqual((p['stock'],p['reserved_quantity'],p['available_quantity']),(13,10,3))
    def test_failed_completion_preserves_reservation(self):
        one=self.request(key='first');two=self.request(key='second')
        self.act('tech','complete',request_id=one['id'])
        with self.assertRaises(Error):self.act('tech','complete',request_id=two['id'])
        self.assertEqual(self.part_balance()['reserved_quantity'],1)
    def test_low_alert_deduplicates_acknowledges_per_user_and_recurs(self):
        r=self.act('tech','request',machine_id=1,part_id=1,quantity=7,reason='Service',operation_key='low')
        alert=next(a for a in self.active_alerts(kind='Low stock') if a['part_id']==1)
        for _ in range(3):
            self.assertEqual(len([a for a in self.active_alerts(kind='Low stock') if a['part_id']==1]),1)
        self.act('tech','alert_ack',alert_id=alert['id']);self.act('tech','alert_ack',alert_id=alert['id'])
        self.assertEqual(next(a for a in self.active_alerts('tech') if a['id']==alert['id'])['acknowledged'],1)
        self.assertEqual(next(a for a in self.active_alerts('lead') if a['id']==alert['id'])['acknowledged'],0)
        self.act('tech','cancel',request_id=r['id'])
        old=next(a for a in self.store.state(self.tokens['tech'])['alerts'] if a['id']==alert['id'])
        self.assertIsNotNone(old['resolved'])
        with self.assertRaises(Error):self.act('tech','alert_ack',alert_id=alert['id'])
        self.act('tech','request',machine_id=1,part_id=1,quantity=7,reason='Service',operation_key='low-again')
        new=next(a for a in self.active_alerts('tech',kind='Low stock') if a['part_id']==1)
        self.assertNotEqual(new['id'],alert['id']);self.assertEqual(new['acknowledged'],0)
    def make_overdue(self,mid=1):
        r=self.request(mid=mid,key='overdue-'+str(mid));self.act('tech','complete',request_id=r['id'])
        old=(datetime.now(timezone.utc)-timedelta(days=100)).isoformat()
        with self.store.tx() as db: db.execute('UPDATE maintenance SET replaced=? WHERE request_id=?',(old,r['id']))
        return r
    def test_overdue_alert_requires_known_history_and_resolves_after_completion(self):
        self.assertEqual(self.active_alerts(kind='Overdue maintenance'),[])
        self.make_overdue()
        alerts=self.active_alerts(kind='Overdue maintenance');self.assertEqual(len(alerts),1)
        self.act('tech','alert_ack',alert_id=alerts[0]['id'])
        r=self.request(key='fix-overdue');self.act('tech','complete',request_id=r['id'])
        self.assertEqual(self.active_alerts(kind='Overdue maintenance'),[])
    def test_alert_machine_scope_and_ack_are_enforced(self):
        self.make_overdue(mid=3)
        alert=self.active_alerts(kind='Overdue maintenance')[0]
        with self.store.tx() as db:db.execute('DELETE FROM access WHERE user_id=3 AND building_id=3')
        self.assertFalse(any(a['id']==alert['id'] for a in self.store.state(self.tokens['tech'])['alerts']))
        with self.assertRaises(Error) as e:self.act('tech','alert_ack',alert_id=alert['id'])
        self.assertEqual(e.exception.status,404)
        self.assertTrue(any(a['id']==alert['id'] for a in self.store.state(self.tokens['admin'])['alerts']))
    def test_retirement_and_catalog_interval_resolve_overdue_alert(self):
        self.make_overdue()
        self.assertEqual(len(self.active_alerts(kind='Overdue maintenance')),1)
        self.act('admin','edit_part',**self.edit_part_data(interval_days=200))
        self.assertEqual(self.active_alerts(kind='Overdue maintenance'),[])
        self.act('admin','edit_part',**self.edit_part_data(interval_days=90,revision=1))
        self.assertEqual(len(self.active_alerts(kind='Overdue maintenance')),1)
        self.act('admin','machine',id=1,line_id=1,type_id=1,station='01',asset_tag='DEMO-001',serial='SAMPLE',status='Retired')
        self.assertEqual(self.active_alerts(kind='Overdue maintenance'),[])
    def test_existing_overcommitted_work_is_visible_and_can_recover(self):
        self.act('tech','request',machine_id=1,part_id=1,quantity=12,reason='Service',operation_key='legacy')
        with self.store.tx() as db:db.execute('UPDATE parts SET stock=5 WHERE id=1')
        self.assertEqual(self.part_balance()['reservation_shortfall'],7)
        self.assertEqual(len(self.active_alerts(kind='Reservation shortfall')),1)
        with self.assertRaises(Error):self.request(user='other',mid=3)
        self.act('admin','receipt',part_id=1,quantity=7,reason='Recover legacy balance',operation_key='recover')
        self.assertEqual(self.part_balance()['reservation_shortfall'],0)
        self.assertEqual(self.active_alerts(kind='Reservation shortfall'),[])
    def test_alerts_reservations_and_acknowledgement_survive_restart(self):
        self.act('tech','request',machine_id=1,part_id=1,quantity=7,reason='Service',operation_key='restart')
        a=next(a for a in self.active_alerts(kind='Low stock') if a['part_id']==1)
        self.act('admin','alert_ack',alert_id=a['id'])
        before=self.store.state(self.tokens['admin']);reopened=Store(self.store.path)
        self.assertEqual(reopened.state(self.tokens['admin']),before)
    def test_v4_upgrade_approves_existing_lead_requests_once_and_preserves_stock(self):
        import sqlite3
        r=self.reorder(user='lead')
        db=sqlite3.connect(self.store.path)
        try:
            db.execute('DROP TABLE alert_acknowledgements');db.execute('DROP TABLE alerts')
            db.execute("UPDATE reorders SET state='Requested',reviewed_by=NULL,reviewed=NULL,review_comment=NULL WHERE id=?",(r['id'],))
            db.execute('PRAGMA user_version=4');db.commit()
        finally:db.close()
        self.store=Store(self.store.path)
        self.assertEqual(self.part_balance()['stock'],12)
        order=self.store.state(self.tokens['admin'])['reorders'][0]
        self.assertEqual(order['state'],'Approved');self.assertEqual(order['revision'],1)
        self.store=Store(self.store.path)
        with self.store.tx() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM audit WHERE action='lead_reorder_policy_upgrade'").fetchone()[0],1)
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],7)
    def test_receiving_purchase_resolves_available_stock_alert(self):
        self.act('tech','request',machine_id=1,part_id=1,quantity=7,reason='Service',operation_key='reserve-for-receipt')
        rid=self.order_ready(quantity=2,key='supply')
        self.receive(rid,quantity=2)
        p=self.part_balance();self.assertEqual((p['stock'],p['reserved_quantity'],p['available_quantity']),(14,7,7))
        self.assertFalse(any(a['part_id']==1 for a in self.active_alerts(kind='Low stock')))

    def test_concurrent_pending_approvals_cannot_reserve_last_unit_twice(self):
        done=self.request();self.act('tech','complete',request_id=done['id'])
        with self.store.tx() as db:db.execute('UPDATE parts SET stock=1 WHERE id=1')
        pending=[self.request(user=user,key='early-'+user,early_explanation='Failed seal') for user in ['tech','other']]
        def approve(r):
            try:self.act('lead','review',request_id=r['id'],decision='Approved',comment='Repair');return True
            except Error:return False
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(approve,pending))
        self.assertEqual(sum(results),1)
        p=self.part_balance();self.assertEqual((p['stock'],p['reserved_quantity'],p['available_quantity']),(1,1,0))
    def test_concurrent_cancel_and_complete_release_reservation_once(self):
        r=self.request()
        def transition(action):
            try:self.act('tech',action,request_id=r['id']);return True
            except Error:return False
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(transition,['complete','cancel']))
        self.assertEqual(sum(results),1)
        state=self.store.state(self.tokens['admin']);row=next(x for x in state['requests'] if x['id']==r['id'])
        p=self.part_balance();self.assertEqual(p['reserved_quantity'],0)
        self.assertEqual(p['stock'],11 if row['state']=='Completed' else 12)
        self.assertEqual(len(state['history']),1 if row['state']=='Completed' else 0)

    def test_lead_full_reorder_flow_records_authenticated_actor(self):
        r=self.reorder(user='lead')
        self.act('lead','reorder_order',reorder_id=r['id'],revision=0,po_reference='LEAD-PO',ordered_by=1)
        self.receive(r['id'],user='lead',quantity=4,received_by=1)
        self.receive(r['id'],user='lead',quantity=6,reference='LEAD-SECOND',key='lead-second')
        state=self.store.state(self.tokens['lead']);order=state['reorders'][0]
        self.assertEqual(order['state'],'Received');self.assertEqual(order['ordered_by'],2)
        self.assertTrue(all(d['received_by']==2 for d in state['deliveries']))
        movements=self.act('lead','ledger_list',part_id=1)['records']
        self.assertEqual(movements[0]['actor'],'lead');self.assertEqual(movements[0]['balance_after'],22)
        events=self.act('admin','audit_list',event='reorder_receive')['records']
        self.assertEqual(len(events),2);self.assertTrue(all(r['actor_id']==2 for r in events))
    def test_lead_cancel_partial_other_requester_and_terminal_guards(self):
        rid=self.order_ready()
        self.receive(rid,user='lead',quantity=3)
        self.act('lead','reorder_cancel',reorder_id=rid,revision=3,reason='Supplier failed')
        self.assertEqual(self.part_balance()['stock'],15)
        self.assertEqual(self.store.state(self.tokens['lead'])['reorders'][0]['cancelled_by'],2)
        with self.assertRaises(Error):self.receive(rid,user='lead',quantity=1,reference='late',key='late')
        with self.assertRaises(Error):self.act('lead','reorder_cancel',reorder_id=rid,revision=4,reason='Again')
    def test_lead_can_reject_admin_request_and_tech_cannot_purchase(self):
        r=self.reorder()
        self.act('lead','reorder_review',reorder_id=r['id'],revision=0,decision='Rejected',comment='Not needed')
        self.assertEqual(self.store.state(self.tokens['lead'])['reorders'][0]['reviewed_by'],2)
        for action in ['reorder_review','reorder_order','reorder_receive','reorder_cancel']:
            with self.assertRaises(Error) as e:self.act('tech',action,reorder_id=r['id'])
            self.assertEqual(e.exception.status,403)
    def test_lead_and_admin_concurrent_receipts_cannot_overfill(self):
        rid=self.order_ready(quantity=5)
        def receipt(user):
            try:self.receive(rid,user=user,quantity=5,reference=user,key='race-'+user);return True
            except Error:return False
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(receipt,['lead','admin']))
        self.assertEqual(sum(results),1);self.assertEqual(self.part_balance()['stock'],17)
    def test_record_view_permissions_are_server_side(self):
        for user,action in [('tech','audit_list'),('tech','ledger_list')]:
            with self.assertRaises(Error) as e:self.act(user,action)
            self.assertEqual(e.exception.status,403)
        self.assertTrue(self.act('lead','ledger_list')['records'])
        self.act('admin','audit_list')
    def test_record_views_do_not_mutate_ledger_or_audit(self):
        self.request()
        with self.store.tx() as db:
            before={t:[tuple(r) for r in db.execute('SELECT * FROM '+t)] for t in ['ledger','audit','requests','parts']}
        for _ in range(2):self.act('admin','audit_list');self.act('lead','ledger_list')
        with self.store.tx() as db:
            after={t:[tuple(r) for r in db.execute('SELECT * FROM '+t)] for t in before}
        self.assertEqual(before,after)
    def test_movement_balances_use_all_rows_despite_direction_filter(self):
        self.act('admin','receipt',part_id=1,quantity=3,reason='Arrived',operation_key='plus-three')
        self.act('admin','adjust',part_id=1,delta=-2,reason='Count correction',operation_key='minus-two')
        r=self.request();self.act('tech','complete',request_id=r['id'])
        out=self.act('lead','ledger_list',part_id=1,direction='Out')['records']
        self.assertEqual([(r['delta'],r['balance_after']) for r in out],[(-1,12),(-2,13)])
        self.assertEqual(out[0]['actor'],'tech')
        self.assertTrue(all(r['part_id']==1 for r in out))
        self.assertNotIn('operation_key',out[0])
    def test_cursor_pagination_has_no_duplicates_when_new_records_arrive(self):
        for n in range(6):self.act('admin','receipt',part_id=1,quantity=1,reason=f'Batch {n}',operation_key=f'page-{n}')
        first=self.act('lead','ledger_list',part_id=1,limit=2)
        self.assertTrue(first['has_more'])
        self.act('admin','receipt',part_id=1,quantity=1,reason='New arrival',operation_key='new-arrival')
        second=self.act('lead','ledger_list',part_id=1,limit=2,cursor=first['next_cursor'])
        self.assertTrue(all(r['id']<first['next_cursor'] for r in second['records']))
        ids=[r['id'] for r in first['records']+second['records']];self.assertEqual(len(ids),len(set(ids)))
        newest=self.act('lead','ledger_list',part_id=1,limit=2)['records'][0]
        self.assertEqual(newest['reason'],'New arrival')
    def test_audit_pagination_event_and_actor_search(self):
        for n in range(5):self.reorder(user='lead',key=f'audit-{n}')
        first=self.act('admin','audit_list',event='reorder_request',search='lead',limit=2)
        second=self.act('admin','audit_list',event='reorder_request',search='lead',limit=2,cursor=first['next_cursor'])
        final=self.act('admin','audit_list',event='reorder_request',search='lead',limit=2,cursor=second['next_cursor'])
        self.assertEqual([len(x['records']) for x in [first,second,final]],[2,2,1]);self.assertFalse(final['has_more'])
        self.assertEqual(final['next_cursor'],None)
        self.assertTrue(all(r['action']=='reorder_request' and r['actor']=='lead' for x in [first,second,final] for r in x['records']))
    def test_record_filters_literal_search_dates_and_zero_matches(self):
        self.act('admin','receipt',part_id=1,quantity=2,reason='50%_test',operation_key='literal')
        self.assertEqual(len(self.act('lead','ledger_list',search='%_')['records']),1)
        self.assertEqual(self.act('lead','ledger_list',search="' OR 1=1 --")['records'],[])
        self.assertEqual(self.act('admin','audit_list',event='missing')['records'],[])
        today=datetime.now(timezone.utc).date().isoformat()
        rows=self.act('lead','ledger_list',from_date=today,to_date=today,direction='In')['records']
        self.assertTrue(rows);self.assertTrue(all(r['delta']>0 and r['created'][:10]==today for r in rows))
        self.assertEqual(self.act('lead','ledger_list',to_date='2000-01-01')['records'],[])
    def test_record_input_validation(self):
        cases=[{'limit':True},{'limit':0},{'limit':101},{'cursor':-1},{'cursor':'2'},{'search':None},{'search':'x'*201},{'from_date':'2026-1-01'},{'from_date':'2026-02-30'},{'from_date':'2026-10-10','to_date':'2026-10-09'},{'direction':'Other'},{'part_id':False},{'part_id':999}]
        for d in cases:
            with self.subTest(d=d):
                with self.assertRaises(Error):self.act('lead','ledger_list',**d)
        with self.assertRaises(Error):self.act('admin','audit_list',event='x'*81)
    def test_audit_detail_redacts_nested_credentials_and_hides_legacy_text(self):
        with self.store.tx() as db:
            self.store.audit(db,1,'sensitive_test',{'password':'BAD1','before':{'session_token':'BAD2','role':'Lead'},'items':[{'apiKey':'BAD3','secret':'BAD4','reason':'Safe'}]})
            db.execute("INSERT INTO audit(actor_id,action,detail,created) VALUES(1,'legacy_test','bad plaintext',?)",(datetime.now(timezone.utc).isoformat(),))
        detail=self.act('admin','audit_list',event='sensitive_test')['records'][0]['detail']
        self.assertEqual(detail['password'],'[redacted]');self.assertEqual(detail['before']['session_token'],'[redacted]')
        self.assertEqual(detail['items'][0]['apiKey'],'[redacted]');self.assertEqual(detail['before']['role'],'Lead')
        legacy=self.act('admin','audit_list',event='legacy_test')['records'][0]['detail']
        self.assertNotIn('bad plaintext',json.dumps(legacy))
    def test_historical_balances_survive_catalog_rename_and_restart(self):
        self.act('admin','receipt',part_id=1,quantity=2,reason='Receipt',operation_key='rename-ledger')
        self.act('admin','edit_part',**self.edit_part_data(name='New name',sku='NEW-SEAL'))
        rows=self.act('lead','ledger_list',part_id=1)['records']
        self.assertEqual(rows[0]['balance_after'],14);self.assertEqual(rows[0]['part'],'New name');self.assertEqual(rows[0]['sku'],'NEW-SEAL')
        self.store=Store(self.store.path)
        self.assertEqual(self.act('lead','ledger_list',part_id=1)['records'],rows)
    def test_http_lead_reorders_and_record_view_authorization(self):
        server=serve(self.store,0);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        def api(action,data,user='lead'):
            req=Request(f'http://127.0.0.1:{server.server_port}/actions/{action}',data=json.dumps(data).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+self.tokens[user]})
            with urlopen(req) as response:return json.load(response)
        try:
            r=api('reorder_request',{'part_id':1,'quantity':2,'reason':'Supply','operation_key':'http-lead'})
            api('reorder_order',{'reorder_id':r['id'],'revision':0,'po_reference':'PO'})
            api('reorder_receive',{'reorder_id':r['id'],'quantity':2,'delivery_reference':'SLIP','operation_key':'http-slip'})
            self.assertEqual(api('ledger_list',{'part_id':1})['records'][0]['actor'],'lead')
            with self.assertRaises(HTTPError) as e:api('audit_list',{},'tech')
            self.assertEqual(e.exception.code,403)
            self.assertEqual(api('audit_list',{'event':'reorder_receive'},'admin')['records'][0]['actor'],'lead')
        finally:server.shutdown();server.server_close();thread.join()

    def csv_rows(self,result):
        import csv,io
        return list(csv.DictReader(io.StringIO(result['csv'].lstrip('\ufeff'))))
    def test_maintenance_export_matches_scope_and_captured_cost(self):
        one=self.request();self.act('tech','complete',request_id=one['id'])
        two=self.request(mid=3,key='other-line');self.act('tech','complete',request_id=two['id'])
        self.act('admin','edit_part',**self.edit_part_data(cost=99,name='New part'))
        with self.store.tx() as db:db.execute('DELETE FROM access WHERE user_id=3 AND building_id=3')
        result=self.act('tech','report_export',report='maintenance')
        rows=self.csv_rows(result);self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['machine_id'],'1');self.assertEqual(rows[0]['unit_cost'],'24.5');self.assertEqual(rows[0]['total_cost'],'24.5')
        self.assertEqual(rows[0]['part'],'New part');self.assertEqual(self.act('admin','report_export',report='maintenance')['row_count'],2)
    def test_inventory_export_contains_reservations_and_planning(self):
        self.act('tech','request',machine_id=1,part_id=1,quantity=7,reason='Reserve',operation_key='export-reserve')
        rows=self.csv_rows(self.act('tech','report_export',report='inventory',part_id=1))
        self.assertEqual(len(rows),1)
        self.assertEqual((rows[0]['stock'],rows[0]['reserved_quantity'],rows[0]['available_quantity']),('12','7','5'))
        self.assertEqual(rows[0]['suggested_order_quantity'],'15')
        self.assertIn('supplier_number',rows[0]);self.assertIn('interval_days',rows[0]);self.assertIn('lead_days',rows[0])
    def test_export_all_pages_and_ledger_balance_filter(self):
        for n in range(105):self.act('admin','receipt',part_id=1,quantity=1,reason='Bulk',operation_key=f'export-{n}')
        result=self.act('lead','report_export',report='stock_movements',part_id=1,direction='In',limit=1,cursor=999)
        rows=self.csv_rows(result);self.assertEqual(len(rows),106);self.assertEqual(result['row_count'],106)
        self.assertEqual(rows[0]['balance_after'],'117');self.assertEqual(rows[-1]['balance_after'],'12')
    def test_export_permissions_and_unknown_report(self):
        for user,kind in [('tech','audit'),('tech','reorders'),('tech','stock_movements')]:
            with self.assertRaises(Error) as e:self.act(user,'report_export',report=kind)
            self.assertEqual(e.exception.status,403)
        with self.assertRaises(Error):self.act('admin','report_export',report='users')
        self.assertNotIn('password',self.act('tech','report_export',report='inventory')['csv'])
    def test_audit_export_redaction_and_export_audit_entry(self):
        with self.store.tx() as db:self.store.audit(db,1,'redaction_test',{'password':'PRIVATE','nested':{'token':'PRIVATE2','reason':'OK'}})
        result=self.act('admin','report_export',report='audit',event='redaction_test')
        self.assertEqual(result['row_count'],1);self.assertNotIn('PRIVATE',result['csv']);self.assertIn('[redacted]',result['csv'])
        record=self.act('admin','audit_list',event='report_export')['records'][0]
        self.assertEqual(record['detail'],{'report':'audit','row_count':1})
    def test_csv_escaping_unicode_and_formula_injection(self):
        self.act('admin','receipt',part_id=1,quantity=1,reason='  =SUM(1,2)',operation_key='formula')
        self.act('admin','receipt',part_id=1,quantity=1,reason='Seal, "special"\nمرحبا',operation_key='unicode')
        result=self.act('lead','report_export',report='stock_movements',part_id=1)
        rows=self.csv_rows(result)
        self.assertEqual(rows[0]['reason'],'Seal, "special"\nمرحبا');self.assertEqual(rows[1]['reason'],"'=SUM(1,2)")
        self.assertTrue(result['csv'].startswith('\ufeff'));self.assertTrue(result['filename'].endswith('.csv'))
        from reports import cell
        for value in ['+cmd','-cmd','@cmd','\tcmd','\rdata','\nformula']:
            self.assertTrue(cell(value).startswith("'"))
        self.assertEqual(cell(-1),-1);self.assertEqual(cell('  =SUM(1,2)'),"'  =SUM(1,2)")
    def test_export_filters_and_header_only_no_matches(self):
        r=self.request();self.act('tech','complete',request_id=r['id'])
        today=datetime.now(timezone.utc).date().isoformat()
        result=self.act('tech','report_export',report='maintenance',from_date=today,to_date=today,search='Worn')
        self.assertEqual(result['row_count'],1)
        result=self.act('tech','report_export',report='maintenance',search='Nothing matches')
        self.assertEqual(result['row_count'],0);self.assertEqual(self.csv_rows(result),[]);self.assertIn('unit_cost',result['csv'])
        for data in [{'from_date':'2026-02-30'},{'from_date':'2026-10-10','to_date':'2026-10-09'},{'part_id':False}]:
            with self.assertRaises(Error):self.act('tech','report_export',report='maintenance',**data)
        with self.assertRaises(Error):self.act('tech','report_export',report='inventory',from_date=today)
    def test_export_row_limit_is_error_not_partial_file(self):
        from unittest.mock import patch
        self.request();self.request(user='other',mid=3)
        with patch('reports.MAX_ROWS',1):
            with self.assertRaises(Error) as e:self.act('tech','report_export',report='inventory')
            self.assertEqual(e.exception.status,413)
        with self.store.tx() as db:self.assertEqual(db.execute("SELECT COUNT(*) FROM audit WHERE action='report_export'").fetchone()[0],0)
    def test_reorder_export_contains_partial_delivery_and_cancelled_remainder(self):
        r=self.reorder(user='lead',quantity=10)
        self.act('lead','reorder_order',reorder_id=r['id'],revision=0,po_reference='PO-EXPORT')
        self.receive(r['id'],user='lead',quantity=3)
        self.act('lead','reorder_cancel',reorder_id=r['id'],revision=2,reason='No more supply')
        row=self.csv_rows(self.act('lead','report_export',report='reorders',search='PO-EXPORT'))[0]
        self.assertEqual((row['state'],row['received_quantity'],row['remaining_quantity']),('Cancelled','3','7'))
        self.assertEqual(row['estimated_total'],'245.0');self.assertEqual(row['requester'],'lead')
    def test_backup_validates_snapshot_clears_only_copy_sessions_and_preserves_history(self):
        import backup,sqlite3
        r=self.request();self.act('tech','complete',request_id=r['id'])
        source_before=self.store.state(self.tokens['admin'])
        path,summary=backup.create(self.store.path,Path(self.tmp.name)/'backups')
        self.assertEqual(summary['schema_version'],7);self.assertEqual(summary['maintenance'],1)
        with sqlite3.connect(path) as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM sessions').fetchone()[0],0)
        self.assertEqual(self.store.state(self.tokens['admin']),source_before)
        recovered=Store(path);token=recovered.login('admin','Example-long-password-2026')['token']
        self.assertEqual(recovered.state(token)['history'],source_before['history'])
        self.assertEqual(recovered.state(token)['parts'],source_before['parts'])
    def test_backup_missing_source_and_invalid_file_never_create_source(self):
        import backup
        missing=Path(self.tmp.name)/'missing.db'
        with self.assertRaises(backup.BackupError):backup.create(missing,Path(self.tmp.name)/'backups')
        self.assertFalse(missing.exists())
        broken=Path(self.tmp.name)/'broken.db';broken.write_text('not a database')
        with self.assertRaises(backup.BackupError):backup.verify(broken)
        with self.assertRaises(backup.BackupError):backup.create(broken,Path(self.tmp.name)/'backups')
        self.assertEqual(list((Path(self.tmp.name)/'backups').glob('*.db')),[])
    def test_backup_duplicate_name_does_not_overwrite_and_failed_copy_is_removed(self):
        import backup
        from unittest.mock import patch
        directory=Path(self.tmp.name)/'backups'
        with patch('backup.secrets.token_hex',return_value='constant'),patch('backup.datetime') as clock:
            clock.now.return_value.strftime.return_value='SAME-TIME'
            first,_=backup.create(self.store.path,directory);before=first.read_bytes()
            with self.assertRaises(FileExistsError):backup.create(self.store.path,directory)
            self.assertEqual(first.read_bytes(),before)
        with patch('shutil.copyfileobj',side_effect=OSError('disk full')):
            with self.assertRaises(OSError):backup.create(self.store.path,directory)
        self.assertEqual(list(directory.glob('*.db')),[first]);self.assertEqual(list(directory.glob('.machinecare-backup-*')),[])
    def test_backup_verify_rejects_missing_tables_newer_schema_and_broken_relationships(self):
        import backup,sqlite3
        path,_=backup.create(self.store.path,Path(self.tmp.name)/'backups')
        db=sqlite3.connect(path);db.execute('UPDATE ledger SET part_id=999 WHERE id=1');db.commit();db.close()
        with self.assertRaises(backup.BackupError):backup.verify(path)
        path,_=backup.create(self.store.path,Path(self.tmp.name)/'backups')
        db=sqlite3.connect(path);db.execute('PRAGMA user_version=8');db.commit();db.close()
        with self.assertRaises(backup.BackupError):backup.verify(path)
        path,_=backup.create(self.store.path,Path(self.tmp.name)/'backups')
        db=sqlite3.connect(path);db.execute('DROP TABLE sessions');db.commit();db.close()
        with self.assertRaises(backup.BackupError):backup.verify(path)
    def test_backup_wal_snapshot_matches_ledger_during_writes(self):
        import backup,sqlite3
        keeper=sqlite3.connect(self.store.path);keeper.execute('PRAGMA journal_mode=WAL')
        def writing():
            for n in range(5):self.act('admin','receipt',part_id=1,quantity=1,reason='Concurrent',operation_key=f'backup-{n}')
        try:
            thread=threading.Thread(target=writing);thread.start()
            path,_=backup.create(self.store.path,Path(self.tmp.name)/'backups');thread.join()
            with sqlite3.connect(path) as db:
                stock=db.execute('SELECT stock FROM parts WHERE id=1').fetchone()[0]
                total=db.execute('SELECT SUM(delta) FROM ledger WHERE part_id=1').fetchone()[0]
                self.assertEqual(stock,total);self.assertTrue(12<=stock<=17)
            self.assertEqual(self.part_balance()['stock'],17)
        finally:keeper.close()
    def test_http_csv_export_permissions_and_payload(self):
        server=serve(self.store,0);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        def api(kind,user):
            req=Request(f'http://127.0.0.1:{server.server_port}/actions/report_export',data=json.dumps({'report':kind}).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+self.tokens[user]})
            with urlopen(req) as response:return json.load(response)
        try:
            result=api('inventory','tech');self.assertEqual(result['row_count'],3);self.assertEqual(len(self.csv_rows(result)),3)
            with self.assertRaises(HTTPError) as e:api('audit','tech')
            self.assertEqual(e.exception.code,403)
        finally:server.shutdown();server.server_close();thread.join()

    def test_lead_cannot_edit_accounts_or_structure_even_by_api(self):
        actions={'building':{'code':'B10','name':'Extra'},'line':{'building_id':1,'code':'L99'},'user':{'username':'new'},'edit_user':{'user_id':3,'role':'Administrator'},'reset':{'user_id':3,'password':'Very-long-new-password'},'disable':{'user_id':3,'active':0}}
        before=self.store.state(self.tokens['admin'])
        for action,data in actions.items():
            with self.subTest(action=action):
                with self.assertRaises(Error) as e:self.act('lead',action,**data)
                self.assertEqual(e.exception.status,403)
        self.assertEqual(self.store.state(self.tokens['admin']),before)
        self.assertEqual(self.store.state(self.tokens['lead'])['users'],[])
    def test_lead_edits_shared_catalog_and_inventory(self):
        self.act('lead','type',id=1,revision=0,name='Lead renamed type')
        self.act('lead','edit_part',**self.edit_part_data(name='Lead renamed part',cost=30))
        self.act('lead','receipt',part_id=1,quantity=2,reason='Unlinked receipt',operation_key='lead-receipt')
        self.act('lead','adjust',part_id=1,delta=-1,reason='Count correction',operation_key='lead-adjust')
        self.assertEqual(self.part_balance()['stock'],13);self.assertEqual(self.part_balance()['name'],'Lead renamed part')
        self.assertEqual(self.act('lead','ledger_list',part_id=1)['records'][0]['actor'],'lead')
    def test_lead_machine_create_edit_and_move_check_both_scopes(self):
        with self.store.tx() as db:
            db.execute('DELETE FROM access WHERE user_id=2');db.execute('DELETE FROM access WHERE user_id IN (3,4)')
            db.execute('INSERT INTO line_access VALUES(2,1)')
        self.act('lead','machine',line_id=1,type_id=1,station='99',asset_tag='LEAD-NEW',serial='NEW',status='Operating')
        self.act('lead','machine',id=1,line_id=1,type_id=1,station='02',asset_tag='DEMO-001',serial='CHANGED',status='Maintenance')
        for mid,line in [(1,2),(2,1)]:
            with self.assertRaises(Error) as e:self.act('lead','machine',id=mid,line_id=line,type_id=1,station='08',asset_tag='BLOCKED',status='Operating')
            self.assertEqual(e.exception.status,403)
        with self.assertRaises(Error):self.act('lead','machine',line_id=2,type_id=1,station='99',asset_tag='OUTSIDE',status='Operating')
        with self.store.tx() as db:self.assertEqual(db.execute("SELECT COUNT(*) FROM machines WHERE asset_tag='BLOCKED'").fetchone()[0],0)
    def test_lead_completes_technician_work_with_actual_actor(self):
        r=self.request()
        self.act('lead','complete',request_id=r['id'],technician_id=3)
        state=self.store.state(self.tokens['admin']);history=state['history'][0]
        self.assertEqual(history['technician_id'],2);self.assertEqual(history['technician'],'lead')
        self.assertEqual(state['requests'][0]['technician_id'],3)
        self.assertEqual(self.part_balance()['stock'],11);self.assertEqual(self.part_balance()['reserved_quantity'],0)
        event=self.act('lead','audit_list',event='complete')['records'][0]
        self.assertEqual(event['actor_id'],2);self.assertEqual(event['detail']['requester_id'],3)
        self.assertTrue(any('recorded by lead' in n['message'] for n in self.store.state(self.tokens['tech'])['notifications']))
        with self.assertRaises(Error):self.act('lead','complete',request_id=r['id'])
    def test_lead_cancels_other_approved_work_and_tech_cannot(self):
        r=self.request()
        with self.assertRaises(Error):self.act('other','cancel',request_id=r['id'])
        with self.assertRaises(Error):self.act('other','complete',request_id=r['id'])
        self.act('lead','cancel',request_id=r['id'])
        self.assertEqual(self.part_balance()['stock'],12);self.assertEqual(self.part_balance()['reserved_quantity'],0)
    def test_lead_sees_all_requests_in_scope_without_assignment(self):
        with self.store.tx() as db:db.execute('UPDATE users SET lead_id=NULL WHERE id=3')
        r=self.request()
        self.assertTrue(any(x['id']==r['id'] for x in self.store.state(self.tokens['lead'])['requests']))
    def test_manager_initiated_early_request_requires_explanation_and_is_recorded(self):
        r=self.request();self.act('tech','complete',request_id=r['id'])
        with self.assertRaises(Error):self.request(user='lead',key='no-explanation')
        early=self.request(user='lead',key='manager-early',early_explanation='Confirmed failed seal')
        self.assertEqual(early['state'],'Approved')
        row=next(r for r in self.store.state(self.tokens['lead'])['requests'] if r['id']==early['id'])
        self.assertEqual(row['reviewer_id'],2);self.assertIn('Manager initiated',row['review_comment'])
        self.act('lead','complete',request_id=early['id'])
        self.assertEqual(self.store.state(self.tokens['lead'])['history'][0]['technician_id'],2)
    def test_lead_review_and_completion_cannot_escape_machine_scope(self):
        r=self.request(mid=3)
        with self.store.tx() as db:db.execute('DELETE FROM access WHERE user_id=2 AND building_id=3')
        for action in ['complete','cancel','review']:
            with self.assertRaises(Error) as e:self.act('lead',action,request_id=r['id'],decision='Approved',comment='Outside')
            self.assertEqual(e.exception.status,403)
        self.assertEqual(self.part_balance()['reserved_quantity'],1)
    def test_lead_audit_export_is_redacted_and_technician_denied(self):
        with self.store.tx() as db:self.store.audit(db,1,'account_event',{'password':'HIDDEN','role':'Technician'})
        result=self.act('lead','report_export',report='audit',event='account_event')
        self.assertEqual(result['row_count'],1);self.assertNotIn('HIDDEN',result['csv']);self.assertIn('[redacted]',result['csv'])
        with self.assertRaises(Error):self.act('tech','report_export',report='audit')
    def test_lead_inventory_adjustment_still_preserves_reservations(self):
        self.act('tech','request',machine_id=1,part_id=1,quantity=10,reason='Reserve',operation_key='manager-reserve')
        with self.assertRaises(Error):self.act('lead','adjust',part_id=1,delta=-3,reason='Count',operation_key='lead-reserved-adjust')
        self.assertEqual(self.part_balance()['stock'],12)
    def test_lead_can_review_other_technician_pending_early_work(self):
        r=self.request();self.act('tech','complete',request_id=r['id'])
        early=self.request(key='pending-review',early_explanation='Failure')
        self.act('admin','edit_user',user_id=4,role='Lead',lead_id=None,building_ids=[1,3])
        self.tokens['other']=self.store.login('other','Example-long-password-2026')['token']
        self.act('other','review',request_id=early['id'],decision='Approved',comment='Confirmed within scope')
        self.assertEqual(next(r for r in self.store.state(self.tokens['other'])['requests'] if r['id']==early['id'])['reviewer_id'],4)
    def test_http_lead_operations_and_admin_boundary(self):
        server=serve(self.store,0);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        def api(action,data):
            req=Request(f'http://127.0.0.1:{server.server_port}/actions/{action}',data=json.dumps(data).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+self.tokens['lead']})
            with urlopen(req) as response:return json.load(response)
        try:
            r=self.request();api('complete',{'request_id':r['id']})
            self.assertEqual(api('audit_list',{'event':'complete'})['records'][0]['actor'],'lead')
            with self.assertRaises(HTTPError) as e:api('disable',{'user_id':3,'active':0})
            self.assertEqual(e.exception.code,403)
        finally:server.shutdown();server.server_close();thread.join()

if __name__=='__main__': unittest.main()
