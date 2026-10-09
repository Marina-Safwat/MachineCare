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
            db.execute('DROP TABLE reorder_deliveries');db.execute('DROP TABLE reorders');db.execute('DROP TABLE line_access');db.execute('ALTER TABLE parts DROP COLUMN revision');db.execute('ALTER TABLE types DROP COLUMN revision');db.execute('PRAGMA user_version=1')
        reopened=Store(self.store.path)
        after=reopened.state(self.tokens['admin'])
        self.assertEqual(after['history'],before['history'])
        self.assertEqual(after['parts'],before['parts'])
        self.assertEqual(after['users'],before['users'])
        self.assertEqual(len(reopened.state(self.tokens['tech'])['machines']),4)
        with reopened.tx() as db:self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],4)
    def test_migration_rerun_keeps_line_grants_and_version(self):
        self.line_only()
        reopened=Store(self.store.path)
        self.assertEqual(reopened.state(self.tokens['tech'])['user']['line_ids'],[1])
        with reopened.tx() as db:self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],4)
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
    def test_part_edit_blocked_for_technician_and_lead(self):
        for user in ['tech','lead']:
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

    def reorder(self,user='lead',quantity=10,key='purchase-first',part_id=1,**extra):
        return self.act(user,'reorder_request',part_id=part_id,quantity=quantity,reason='Replenish spare parts',operation_key=key,**extra)
    def order_ready(self,quantity=10,key='purchase-first',part_id=1):
        r=self.reorder(quantity=quantity,key=key,part_id=part_id)
        self.act('admin','reorder_review',reorder_id=r['id'],revision=0,decision='Approved',comment='Approved replenishment')
        self.act('admin','reorder_order',reorder_id=r['id'],revision=1,po_reference='PO-001')
        return r['id']
    def receive(self,rid,quantity=4,reference='SLIP-1',key='delivery-first',user='admin',**extra):
        return self.act(user,'reorder_receive',reorder_id=rid,quantity=quantity,delivery_reference=reference,operation_key=key,notes='Inspected delivery',**extra)
    def test_reorder_approval_and_ordering_do_not_change_stock(self):
        before=self.store.state(self.tokens['admin'])['parts']
        r=self.reorder()
        self.assertEqual(self.store.state(self.tokens['admin'])['reorders'][0]['state'],'Requested')
        self.act('admin','reorder_review',reorder_id=r['id'],revision=0,decision='Approved',comment='Yes')
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
        with self.assertRaises(Error):self.act('lead','reorder_review',reorder_id=r['id'],revision=0,decision='Approved',comment='Lead')
        rid=self.order_ready(key='lead-order')
        for user in ['lead','tech']:
            with self.assertRaises(Error):self.receive(rid,user=user,key='not-admin-'+user)
        self.assertEqual(self.store.state(self.tokens['tech'])['reorders'],[])
        self.assertEqual(self.store.state(self.tokens['tech'])['deliveries'],[])
    def test_rejected_and_unordered_reorders_cannot_receive(self):
        r=self.reorder()
        with self.assertRaises(Error):self.receive(r['id'])
        self.act('admin','reorder_review',reorder_id=r['id'],revision=0,decision='Rejected',comment='Not needed')
        with self.assertRaises(Error):self.receive(r['id'])
        with self.assertRaises(Error):self.act('admin','reorder_order',reorder_id=r['id'],revision=1,po_reference='PO')
        approved=self.reorder(key='approved')
        self.act('admin','reorder_review',reorder_id=approved['id'],revision=0,decision='Approved',comment='Yes')
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
    def test_lead_cancellation_limited_to_own_preorder_requests(self):
        r=self.reorder()
        self.act('lead','reorder_cancel',reorder_id=r['id'],revision=0,reason='No longer needed')
        r=self.reorder(user='admin',key='another-requester')
        with self.assertRaises(Error):self.act('lead','reorder_cancel',reorder_id=r['id'],revision=0,reason='Not mine')
        rid=self.order_ready(key='ordered-lead')
        with self.assertRaises(Error):self.act('lead','reorder_cancel',reorder_id=rid,revision=2,reason='Already ordered')
    def test_purchase_revision_blocks_stale_approval_and_ordering(self):
        r=self.reorder()
        self.act('admin','reorder_review',reorder_id=r['id'],revision=0,decision='Approved',comment='First')
        with self.assertRaises(Error) as caught:self.act('admin','reorder_review',reorder_id=r['id'],revision=0,decision='Rejected',comment='Stale')
        self.assertEqual(caught.exception.status,409)
        with self.assertRaises(Error):self.act('admin','reorder_order',reorder_id=r['id'],revision=0,po_reference='PO-stale')
    def test_reorder_suggestion_accounts_for_pending_and_outstanding(self):
        def part():return next(p for p in self.store.state(self.tokens['admin'])['parts'] if p['id']==1)
        self.assertEqual(part()['suggested_order_quantity'],8)
        r=self.reorder(quantity=5)
        self.assertEqual(part()['pending_reorder_quantity'],5);self.assertEqual(part()['suggested_order_quantity'],3)
        self.act('admin','reorder_review',reorder_id=r['id'],revision=0,decision='Approved',comment='Yes')
        self.assertEqual(part()['pending_reorder_quantity'],0);self.assertEqual(part()['outstanding_order_quantity'],5)
        self.act('admin','reorder_order',reorder_id=r['id'],revision=1,po_reference='PO')
        self.receive(r['id'],quantity=2)
        self.assertEqual(part()['outstanding_order_quantity'],3);self.assertEqual(part()['stock'],14);self.assertEqual(part()['suggested_order_quantity'],3)
    def test_purchase_snapshots_survive_part_edits_and_ignore_spoofed_identity(self):
        r=self.reorder(requested_by=4,unit_cost_snapshot=0,supplier_snapshot='Spoof')
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
        with reopened.tx() as db:self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],4)
    def test_purchase_notifications_and_audit_not_duplicated_by_retry(self):
        r=self.reorder()
        admins=self.store.state(self.tokens['admin'])['notifications']
        with self.assertRaises(Error):self.reorder()
        self.assertEqual(self.store.state(self.tokens['admin'])['notifications'],admins)
        self.act('admin','reorder_review',reorder_id=r['id'],revision=0,decision='Approved',comment='Yes')
        self.assertTrue(any('Approved' in n['message'] for n in self.store.state(self.tokens['lead'])['notifications']))
        with self.store.tx() as db:self.assertEqual(db.execute("SELECT COUNT(*) FROM audit WHERE action='reorder_request'").fetchone()[0],1)
    def test_http_purchase_flow_through_partial_and_complete_receiving(self):
        server=serve(self.store,0);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        def api(action,data,user):
            req=Request(f'http://127.0.0.1:{server.server_port}/actions/{action}',data=json.dumps(data).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+self.tokens[user]})
            with urlopen(req) as response:return json.load(response)
        try:
            r=api('reorder_request',{'part_id':1,'quantity':5,'reason':'HTTP replenish','operation_key':'http-order'},'lead')
            api('reorder_review',{'reorder_id':r['id'],'revision':0,'decision':'Approved','comment':'Approved'},'admin')
            api('reorder_order',{'reorder_id':r['id'],'revision':1,'po_reference':'HTTP-PO'},'admin')
            result=api('reorder_receive',{'reorder_id':r['id'],'quantity':2,'delivery_reference':'HTTP-SLIP1','operation_key':'http-delivery1'},'admin')
            self.assertEqual(result['state'],'Partially received')
            result=api('reorder_receive',{'reorder_id':r['id'],'quantity':3,'delivery_reference':'HTTP-SLIP2','operation_key':'http-delivery2'},'admin')
            self.assertEqual(result['state'],'Received')
        finally:server.shutdown();server.server_close();thread.join()

if __name__=='__main__': unittest.main()
