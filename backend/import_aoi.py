"""Add the user-supplied AOI catalog and complete the stated per-line layout.

Explicit local import only. Existing assets, accounts and balances are preserved.
Unknown counts/operational values are labeled demo assumptions.
"""
import argparse
from pathlib import Path
import backup
from core import Store, now

PARTS = [
    ('TM robot', 'TM (as supplied)', None, None, 1, True),
    ('Small light curtain', 'PILZ', 'PSEN op113H-s-30-030', None, 4, True),
    ('Large light curtain', 'PILZ', 'PESN op113H-s-30-075', None, 2, True),
    ('PLC PNOZ m bo.1', 'PILZ', 'Ident-772104', None, 1, True),
    ('Tower light', None, 'ASTLF-110-4-5FT-CM', None, 2, True),
    ('Switching power supply', None, 's-120-24', None, 1, True),
    ('Control box', 'VEVOR', None, '240108586510146', 1, True),
]

def import_data(store):
    added_parts = added_machines = 0
    with store.tx() as db:
        types = {}
        for name in ('DIMM Press', 'AOI'):
            matches = db.execute('SELECT id FROM types WHERE lower(trim(name))=lower(?)', (name,)).fetchall()
            if len(matches) > 1:
                raise ValueError('Ambiguous machine type: ' + name)
            if matches:
                types[name] = matches[0]['id']
            elif name == 'AOI':
                types[name] = db.execute('INSERT INTO types(name) VALUES(?)', (name,)).lastrowid
            else:
                raise ValueError('DIMM Press type is missing; do not guess existing assignments.')
        for line in db.execute('SELECT id FROM lines ORDER BY id').fetchall():
            for name, desired, prefix in [('DIMM Press', 2, 'DIMM'), ('AOI', 1, 'AOI')]:
                count = db.execute("SELECT COUNT(*) FROM machines WHERE line_id=? AND type_id=? AND status!='Retired'", (line['id'], types[name])).fetchone()[0]
                if count > desired:
                    raise ValueError(f"Line {line['id']} already exceeds stated {name} count; no assets changed.")
                for number in range(count + 1, desired + 1):
                    tag = f"DEMO-L{line['id']:03d}-{prefix}-{number:02d}"
                    if db.execute('SELECT 1 FROM machines WHERE upper(asset_tag)=?', (tag,)).fetchone():
                        raise ValueError('Conflicting asset tag: ' + tag)
                    mid = db.execute('INSERT INTO machines(line_id,type_id,station,asset_tag,serial,status) VALUES(?,?,?,?,?,?)',
                        (line['id'], types[name], f'DEMO-{prefix}-{number:02d}', tag, '', 'Operating')).lastrowid
                    store.audit(db, None, 'demo_equipment_import', {'machine_id':mid, 'line_id':line['id'],
                        'source':'User confirmed two DIMM presses and one AOI per line.',
                        'assumptions':'Asset tag, station and Operating status are demo placeholders; serial unknown.'})
                    added_machines += 1
        for index, (name, manufacturer, number, serial, usage, confirmed) in enumerate(PARTS, 1):
            key = f'aoi-user-2026-10-18:{index}'
            if db.execute('SELECT 1 FROM part_provenance WHERE source_key=?', (key,)).fetchone():
                continue
            sku = f'DEMO-AOI-{index:03d}'
            if db.execute('SELECT 1 FROM parts WHERE upper(trim(sku))=?', (sku,)).fetchone():
                raise ValueError('Conflicting SKU: ' + sku)
            notice = ('DEMO: opening spare stock is illustrative (2 per catalog item); cost $0 means unknown. '
                      'Bin unassigned; 365-day interval, 0-day lead and reorder levels are placeholders. '
                      'Not a safety inspection or maintenance recommendation. ' +
                      ('Quantity per AOI supplied by user. ' if confirmed else 'Quantity of 1 per AOI is an UNVERIFIED demo assumption. ') +
                      'Identifiers preserved as supplied; verify against nameplates. Serial references do not identify every machine/spare.')
            pid = db.execute('INSERT INTO parts(sku,name,bin,cost,stock,threshold,target,lead_days,interval_days) VALUES(?,?,?,0,2,1,4,0,365)',
                             (sku, name, 'DEMO - unassigned')).lastrowid
            db.execute('INSERT INTO compatibility VALUES(?,?)', (pid, types['AOI']))
            db.execute('INSERT INTO part_provenance VALUES(?,?,?,?,?,?,?,?)',
                       (pid, key, manufacturer, number, serial, usage, 'AOI / TM robot cell', notice))
            db.execute('INSERT INTO ledger(part_id,delta,reason,actor_id,created,operation_key) VALUES(?,2,?,NULL,?,?)',
                       (pid, 'Illustrative manager-demo opening stock; not a physical count.', now(), key))
            store.audit(db, None, 'demo_part_import', {'part_id':pid, 'source_key':key, 'notice':notice})
            added_parts += 1
    return {'parts_added':added_parts, 'machines_added':added_machines}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', required=True)
    parser.add_argument('--backup-dir', required=True)
    args = parser.parse_args()
    path = Path(args.db).resolve()
    snapshot, summary = backup.create(path, args.backup_dir)
    print('Verified backup:', snapshot, summary, flush=True)
    print(import_data(Store(path)))
    print('Integrity:', backup.verify(path))

if __name__ == '__main__':
    main()
