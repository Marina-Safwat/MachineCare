"""Read-only, permission-checked record browsing with stable descending ID cursors."""
import json
from datetime import date

class RecordError(ValueError):
    def __init__(self,message,status=400): self.status=status;super().__init__(message)

def text(d,key,maximum=200):
    value=d.get(key,'')
    if not isinstance(value,str) or len(value)>maximum:raise RecordError(f'{key} must be text of at most {maximum} characters.')
    return value.strip()

def positive(d,key,default=None):
    v=d.get(key,default)
    if v is None:return None
    if type(v)!=int or v<1:raise RecordError(f'{key} must be a positive integer.')
    return v

def redact(value):
    if isinstance(value,dict):
        return {k:('[redacted]' if any(word in k.lower() for word in ('password','token','secret','credential','authorization','api_key','apikey')) else redact(v)) for k,v in value.items()}
    if isinstance(value,list):return [redact(v) for v in value]
    return value

def browse(db,u,action,d):
    audit=action=='audit_list'
    if audit and u['role']!='Administrator':raise RecordError('Administrator permission required for audit records.',403)
    if not audit and u['role'] not in ('Lead','Administrator'):raise RecordError('Lead or Administrator permission required for stock movements.',403)
    limit=positive(d,'limit',50)
    if limit>100:raise RecordError('limit must be at most 100.')
    cursor=positive(d,'cursor')
    start=text(d,'from_date',10);end=text(d,'to_date',10)
    for v in (start,end):
        if v:
            try:parsed=date.fromisoformat(v)
            except ValueError:raise RecordError('Dates must use YYYY-MM-DD.')
            if parsed.isoformat()!=v:raise RecordError('Dates must use YYYY-MM-DD.')
    if start and end and start>end:raise RecordError('Start date must not follow end date.')
    where=[];args=[]
    if cursor:where.append('r.id<?');args.append(cursor)
    if start:where.append('substr(r.created,1,10)>=?');args.append(start)
    if end:where.append('substr(r.created,1,10)<=?');args.append(end)
    search=text(d,'search')
    if search:
        pattern='%'+search.replace('\\','\\\\').replace('%','\\%').replace('_','\\_')+'%'
        columns=['r.action',"COALESCE(u.username,'System')"] if audit else ['p.name','p.sku','r.reason',"COALESCE(u.username,'System')"]
        where.append('('+' OR '.join(c+" LIKE ? ESCAPE '\\'" for c in columns)+')');args.extend([pattern]*len(columns))
    if audit:
        event=text(d,'event',80)
        if event:where.append('r.action=?');args.append(event)
        query="SELECT r.id,r.actor_id,r.action,r.detail,r.created,COALESCE(u.username,'System') actor FROM audit r LEFT JOIN users u ON u.id=r.actor_id"
    else:
        pid=positive(d,'part_id')
        if pid:
            if not db.execute('SELECT 1 FROM parts WHERE id=?',(pid,)).fetchone():raise RecordError('Part not found.',404)
            where.append('r.part_id=?');args.append(pid)
        direction=text(d,'direction',10) or 'All'
        if direction not in ('All','In','Out'):raise RecordError('Choose All, In or Out.')
        if direction!='All':where.append('r.delta>0' if direction=='In' else 'r.delta<0')
        query="SELECT r.id,r.part_id,r.delta,r.reason,r.actor_id,r.created,r.balance_after,p.name part,p.sku,COALESCE(u.username,'System') actor FROM (SELECT l.*,SUM(delta) OVER(PARTITION BY part_id ORDER BY id ROWS UNBOUNDED PRECEDING) balance_after FROM ledger l) r JOIN parts p ON p.id=r.part_id LEFT JOIN users u ON u.id=r.actor_id"
    query+=(' WHERE '+' AND '.join(where) if where else '')+' ORDER BY r.id DESC LIMIT ?'
    rows=[dict(r) for r in db.execute(query,(*args,limit+1)).fetchall()]
    more=len(rows)>limit;rows=rows[:limit]
    if audit:
        for r in rows:
            try:
                parsed=json.loads(r['detail'])
                r['detail']=redact(parsed) if isinstance(parsed,(dict,list)) else {'note':'Unstructured legacy detail is unavailable.'}
            except (ValueError,TypeError):r['detail']={'note':'Unstructured legacy detail is unavailable.'}
    return {'records':rows,'has_more':more,'next_cursor':rows[-1]['id'] if more else None}
