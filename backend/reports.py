"""Bounded CSV exports; authorization and spreadsheet-safe cells are server-side."""
import csv
import io
import json
from datetime import date, datetime, timezone
import records

MAX_ROWS = 10000

def cell(value):
    if value is None:return ''
    if isinstance(value,(int,float)):return value
    value=str(value)
    if value.lstrip().startswith(('=','+','-','@')) or value.startswith(('\t','\r','\n')):return "'"+value
    return value

def export(db,u,d,visible_machines):
    kind=records.text(d,'report',40)
    if kind not in ('maintenance','inventory','reorders','stock_movements','audit'):raise records.RecordError('Choose a supported report.')
    if kind=='audit' and u['role'] not in ('Lead','Administrator'):raise records.RecordError('Lead or Administrator permission required for audit export.',403)
    if kind in ('stock_movements','reorders') and u['role'] not in ('Lead','Administrator'):raise records.RecordError('Lead or Administrator permission required for this report.',403)
    data=[]
    if kind in ('audit','stock_movements'):
        filters={k:v for k,v in d.items() if k not in ('cursor','limit','report')}
        while True:
            page=records.browse(db,u,'audit_list' if kind=='audit' else 'ledger_list',{**filters,'limit':100})
            data.extend(page['records'])
            if len(data)>MAX_ROWS:raise records.RecordError('Export exceeds 10,000 rows. Narrow the filters.',413)
            if not page['has_more']:break
            filters['cursor']=page['next_cursor']
        fields=['id','created','actor','action','detail'] if kind=='audit' else ['id','created','part_id','part','sku','delta','balance_after','reason','actor']
        if kind=='audit':
            for row in data:row['detail']=json.dumps(row['detail'],ensure_ascii=False)
    else:
        search=records.text(d,'search').casefold()
        start=records.text(d,'from_date',10);end=records.text(d,'to_date',10)
        for v in (start,end):
            if v:
                try:parsed=date.fromisoformat(v)
                except ValueError:raise records.RecordError('Dates must use YYYY-MM-DD.')
                if parsed.isoformat()!=v:raise records.RecordError('Dates must use YYYY-MM-DD.')
        if start and end and start>end:raise records.RecordError('Start date must not follow end date.')
        pid=records.positive(d,'part_id')
        if pid and not db.execute('SELECT 1 FROM parts WHERE id=?',(pid,)).fetchone():raise records.RecordError('Part not found.',404)
        if kind=='maintenance':
            query='SELECT h.*,p.name part,p.sku,u.username technician FROM maintenance h JOIN parts p ON p.id=h.part_id JOIN users u ON u.id=h.technician_id ORDER BY h.id DESC'
            fields=['id','request_id','replaced','machine_id','location_snapshot','part_id','part','sku','technician','quantity','unit_cost','total_cost','reason','early']
        elif kind=='reorders':
            query='SELECT r.*,p.name part,p.sku,u.username requester FROM reorders r JOIN parts p ON p.id=r.part_id JOIN users u ON u.id=r.requested_by ORDER BY r.id DESC'
            fields=['id','created','part_id','part','sku','requester','state','quantity','received_quantity','remaining_quantity','supplier_snapshot','supplier_number_snapshot','unit_cost_snapshot','estimated_total','po_reference','reason','review_comment','cancellation_reason']
        else:
            if start or end:raise records.RecordError('Inventory is a current snapshot; date filters do not apply.')
            query='SELECT id part_id,sku,name part,bin,supplier,supplier_number,cost,stock,threshold,target,lead_days,interval_days FROM parts ORDER BY id'
            fields=['part_id','sku','part','bin','supplier','supplier_number','lead_days','interval_days','cost','stock','reserved_quantity','available_quantity','reservation_shortfall','threshold','target','outstanding_order_quantity','pending_reorder_quantity','suggested_order_quantity']
        for row in db.execute(query):
            row=dict(row)
            if kind=='maintenance' and row['machine_id'] not in visible_machines:continue
            if pid and row['part_id']!=pid:continue
            stamp=row.get('replaced',row.get('created',''))[:10]
            if (start and stamp<start) or (end and stamp>end):continue
            keys=('part','sku','location_snapshot','technician','requester','reason','state','po_reference','bin','supplier')
            if search and not any(search in str(row.get(k,'')).casefold() for k in keys):continue
            if kind=='maintenance':row['total_cost']=round(row['quantity']*row['unit_cost'],2)
            elif kind=='reorders':
                row['remaining_quantity']=row['quantity']-row['received_quantity'];row['estimated_total']=round(row['quantity']*row['unit_cost_snapshot'],2)
            else:
                import inventory_status,purchasing
                part=db.execute('SELECT * FROM parts WHERE id=?',(row['part_id'],)).fetchone()
                row.update(inventory_status.balance(db,part));row.update(purchasing.planning(db,part))
            data.append(row)
            if len(data)>MAX_ROWS:raise records.RecordError('Export exceeds 10,000 rows. Narrow the filters.',413)
    out=io.StringIO(newline='');writer=csv.writer(out);writer.writerow(fields)
    writer.writerows([cell(row.get(k)) for k in fields] for row in data)
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    return {'filename':f'machinecare_{kind}_{stamp}.csv','csv':'\ufeff'+out.getvalue(),'row_count':len(data)}
