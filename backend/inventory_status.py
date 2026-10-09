"""Reservations derive from approved work; alerts persist observed condition episodes."""
from datetime import datetime, timezone, timedelta
import access_policy as scopes

def balance(db, part):
    reserved = db.execute("SELECT COALESCE(SUM(quantity),0) FROM requests WHERE part_id=? AND state='Approved'", (part['id'],)).fetchone()[0]
    return {'reserved_quantity': reserved, 'available_quantity': max(0, part['stock']-reserved),
            'reservation_shortfall': max(0, reserved-part['stock'])}

def sync(db):
    stamp = datetime.now(timezone.utc).isoformat()
    conditions = {}
    for p in db.execute('SELECT * FROM parts').fetchall():
        b = balance(db, p)
        if b['available_quantity'] <= p['threshold']:
            conditions[f'low:{p["id"]}'] = ('Low stock', p['id'], None, f'{p["name"]}: {b["available_quantity"]} available, {b["reserved_quantity"]} reserved; threshold {p["threshold"]}.')
        if b['reservation_shortfall']:
            conditions[f'short:{p["id"]}'] = ('Reservation shortfall', p['id'], None, f'{p["name"]}: approved work exceeds physical stock by {b["reservation_shortfall"]}. Receive stock or cancel work.')
    for r in db.execute("SELECT m.id machine_id,p.id part_id,p.name,p.interval_days,MAX(h.replaced) last FROM machines m JOIN compatibility c ON c.type_id=m.type_id JOIN parts p ON p.id=c.part_id JOIN maintenance h ON h.machine_id=m.id AND h.part_id=p.id WHERE m.status!='Retired' GROUP BY m.id,p.id").fetchall():
        due = datetime.fromisoformat(r['last']) + timedelta(days=r['interval_days'])
        if due <= datetime.now(timezone.utc):
            conditions[f'overdue:{r["machine_id"]}:{r["part_id"]}'] = ('Overdue maintenance', r['part_id'], r['machine_id'], f'{r["name"]} on machine #{r["machine_id"]}: replacement due {due.date().isoformat()}.')
    active = {r['condition_key']: r for r in db.execute('SELECT * FROM alerts WHERE resolved IS NULL').fetchall()}
    for key, (kind, pid, mid, message) in conditions.items():
        if key in active:
            db.execute('UPDATE alerts SET message=? WHERE id=?', (message, active[key]['id']))
        else:
            db.execute('INSERT INTO alerts(condition_key,kind,part_id,machine_id,message,opened) VALUES(?,?,?,?,?,?)', (key,kind,pid,mid,message,stamp))
    for key, row in active.items():
        if key not in conditions:
            db.execute('UPDATE alerts SET resolved=? WHERE id=?', (stamp,row['id']))

def visible(db,u,row):
    if row['machine_id'] is None or u['role']=='Administrator': return True
    m=db.execute('SELECT l.building_id,m.line_id FROM machines m JOIN lines l ON l.id=m.line_id WHERE m.id=?',(row['machine_id'],)).fetchone()
    return bool(m and scopes.allows(scopes.grants(db,u['id']),m['building_id'],m['line_id']))

def snapshot(db,u):
    return [dict(r) for r in db.execute('SELECT a.*,CASE WHEN k.user_id IS NULL THEN 0 ELSE 1 END acknowledged FROM alerts a LEFT JOIN alert_acknowledgements k ON k.alert_id=a.id AND k.user_id=? ORDER BY a.id DESC',(u['id'],)).fetchall() if visible(db,u,r)]
