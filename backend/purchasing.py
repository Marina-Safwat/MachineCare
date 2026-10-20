"""Purchasing transitions run inside the caller's atomic database transaction."""
import json
import inventory_status
from datetime import datetime, timezone

class PurchaseError(ValueError):
    def __init__(self,message,status=400): self.message=message;self.status=status;super().__init__(message)

def now():return datetime.now(timezone.utc).isoformat()
def text(d,key,optional=False):
    value=d.get(key,'') if optional else d.get(key)
    if not isinstance(value,str) or (not optional and not value.strip()):raise PurchaseError(f'{key} is required.')
    value=value.strip()
    if len(value)>1000:raise PurchaseError(f'{key} is too long.')
    return value

def integer(d,key,minimum=1):
    value=d.get(key)
    if type(value)!=int or value<minimum:raise PurchaseError(f'{key} must be an integer of at least {minimum}.')
    return value

def planning(db,part):
    outstanding=db.execute("SELECT COALESCE(SUM(quantity-received_quantity),0) FROM reorders WHERE part_id=? AND state IN ('Approved','Ordered','Partially received')",(part['id'],)).fetchone()[0]
    pending=db.execute("SELECT COALESCE(SUM(quantity),0) FROM reorders WHERE part_id=? AND state='Requested'",(part['id'],)).fetchone()[0]
    return {'outstanding_order_quantity':outstanding,'pending_reorder_quantity':pending,'suggested_order_quantity':max(0,part['target']-inventory_status.balance(db,part)['available_quantity']-outstanding-pending)}

def snapshot(db,u):
    if u['role'] not in ('Lead','Administrator'):return {'reorders':[],'deliveries':[]}
    return {'reorders':[dict(r) for r in db.execute('SELECT r.*,p.name part,p.sku,p.lead_days,u.username requester FROM reorders r JOIN parts p ON p.id=r.part_id JOIN users u ON u.id=r.requested_by ORDER BY r.id DESC')],
            'deliveries':[dict(r) for r in db.execute('SELECT d.*,u.username receiver FROM reorder_deliveries d JOIN users u ON u.id=d.received_by ORDER BY d.id DESC')]}

def admins(db,message,exclude=None):
    for u in db.execute("SELECT id FROM users WHERE role IN ('Lead','Administrator') AND active=1 AND id!=?",(exclude or -1,)).fetchall():
        db.execute('INSERT INTO notifications(user_id,message,created) VALUES(?,?,?)',(u['id'],message,now()))

def notify(db,user_id,message):db.execute('INSERT INTO notifications(user_id,message,created) VALUES(?,?,?)',(user_id,message,now()))
def audit(db,uid,action,detail):db.execute('INSERT INTO audit(actor_id,action,detail,created) VALUES(?,?,?,?)',(uid,action,json.dumps(detail),now()))

def handle(db,u,action,d):
    uid=u['id']
    if u['role'] not in ('Lead','Administrator'):raise PurchaseError('Purchasing requires Lead or Administrator permission.',403)
    if action=='reorder_request':
        pid=integer(d,'part_id');quantity=integer(d,'quantity');key=text(d,'operation_key');reason=text(d,'reason')
        if db.execute('SELECT 1 FROM reorders WHERE operation_key=?',(key,)).fetchone():raise PurchaseError('This reorder request was already submitted. Refresh before submitting again.',409)
        part=db.execute('SELECT * FROM parts WHERE id=?',(pid,)).fetchone()
        if not part:raise PurchaseError('Part not found.',404)
        cur=db.execute('INSERT INTO reorders(part_id,requested_by,quantity,reason,supplier_snapshot,supplier_number_snapshot,unit_cost_snapshot,created,operation_key) VALUES(?,?,?,?,?,?,?,?,?)',(pid,uid,quantity,reason,part['supplier'],part['supplier_number'],part['cost'],now(),key))
        rid=cur.lastrowid;state='Approved' if u['role']=='Lead' else 'Requested'
        if state=='Approved':
            db.execute("UPDATE reorders SET state='Approved',reviewed_by=?,reviewed=?,review_comment='Lead request: approval not required' WHERE id=?",(uid,now(),rid))
        admins(db,f'Reorder #{rid}: Lead request approved; ready for ordering.' if state=='Approved' else f'Reorder #{rid} requires approval.',uid)
        audit(db,uid,action,{'reorder_id':rid,'part_id':pid,'quantity':quantity,'state':state,'approval_policy':'Lead bypass' if state=='Approved' else 'Separate Lead or Administrator'})
        return {'id':rid,'state':state}
    rid=integer(d,'reorder_id')
    r=db.execute('SELECT * FROM reorders WHERE id=?',(rid,)).fetchone()
    if not r:raise PurchaseError('Reorder not found.',404)
    if action=='reorder_receive':
        quantity=integer(d,'quantity');reference=text(d,'delivery_reference').upper();key=text(d,'operation_key');notes=text(d,'notes',True)
        if db.execute('SELECT 1 FROM reorder_deliveries WHERE operation_key=?',(key,)).fetchone() or db.execute('SELECT 1 FROM ledger WHERE operation_key=?',('reorder-receipt:'+key,)).fetchone():raise PurchaseError('This delivery operation was already recorded. Refresh to inspect its receipt.',409)
        if db.execute('SELECT 1 FROM reorder_deliveries WHERE reorder_id=? AND delivery_reference=?',(rid,reference)).fetchone():raise PurchaseError('That delivery reference was already received for this reorder.',409)
        if r['state'] not in ('Ordered','Partially received'):raise PurchaseError('Only Ordered or Partially received orders can receive deliveries.',409)
        remaining=r['quantity']-r['received_quantity']
        if quantity>remaining:raise PurchaseError(f'Delivery exceeds the remaining order balance of {remaining}.')
        received=r['received_quantity']+quantity;state='Received' if received==r['quantity'] else 'Partially received';stamp=now()
        db.execute('INSERT INTO reorder_deliveries(reorder_id,quantity,delivery_reference,notes,received_by,received,operation_key) VALUES(?,?,?,?,?,?,?)',(rid,quantity,reference,notes,uid,stamp,key))
        db.execute('UPDATE parts SET stock=stock+? WHERE id=?',(quantity,r['part_id']))
        db.execute('INSERT INTO ledger(part_id,delta,reason,actor_id,created,operation_key) VALUES(?,?,?,?,?,?)',(r['part_id'],quantity,f'Reorder #{rid} delivery {reference}',uid,stamp,'reorder-receipt:'+key))
        db.execute('UPDATE reorders SET received_quantity=?,state=?,revision=revision+1 WHERE id=?',(received,state,rid))
        notify(db,r['requested_by'],f'Reorder #{rid}: received {quantity}; {r["quantity"]-received} remaining.')
        audit(db,uid,action,{'reorder_id':rid,'quantity':quantity,'delivery_reference':reference,'state':state})
        return {'state':state,'received_quantity':received,'remaining_quantity':r['quantity']-received}
    revision=integer(d,'revision',0)
    if revision!=r['revision']:raise PurchaseError('This reorder changed in another session. Refresh before acting.',409)
    if action=='reorder_review':
        if uid==r['requested_by']:raise PurchaseError('You cannot approve or reject your own reorder. Use another Lead or Administrator.',403)
        if r['state']!='Requested':raise PurchaseError('Only Requested reorders can be reviewed.',409)
        decision=text(d,'decision')
        if decision not in ('Approved','Rejected'):raise PurchaseError('Choose Approved or Rejected.')
        comment=text(d,'comment')
        db.execute('UPDATE reorders SET state=?,reviewed_by=?,reviewed=?,review_comment=?,revision=revision+1 WHERE id=?',(decision,uid,now(),comment,rid))
        notify(db,r['requested_by'],f'Reorder #{rid}: {decision}.')
        audit(db,uid,action,{'reorder_id':rid,'decision':decision,'comment':comment})
        return {'state':decision}
    if action=='reorder_order':
        if r['state']!='Approved':raise PurchaseError('Only Approved reorders can be marked Ordered.',409)
        reference=text(d,'po_reference')
        db.execute("UPDATE reorders SET state='Ordered',po_reference=?,ordered_by=?,ordered=?,revision=revision+1 WHERE id=?",(reference,uid,now(),rid))
        notify(db,r['requested_by'],f'Reorder #{rid}: Ordered, reference {reference}.')
        audit(db,uid,action,{'reorder_id':rid,'po_reference':reference})
        return {'state':'Ordered'}
    if action=='reorder_cancel':
        if r['state'] not in ('Requested','Approved','Ordered','Partially received'):raise PurchaseError('This reorder cannot be cancelled.',409)
        reason=text(d,'reason')
        db.execute("UPDATE reorders SET state='Cancelled',cancelled_by=?,cancelled=?,cancellation_reason=?,revision=revision+1 WHERE id=?",(uid,now(),reason,rid))
        notify(db,r['requested_by'],f'Reorder #{rid}: cancelled remaining balance. Received stock is retained.')
        audit(db,uid,action,{'reorder_id':rid,'reason':reason,'received_quantity':r['received_quantity'],'cancelled_quantity':r['quantity']-r['received_quantity']})
        return {'state':'Cancelled'}
    raise PurchaseError('Unknown purchasing action.',404)
