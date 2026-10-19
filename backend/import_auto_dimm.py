"""Explicit, backed-up import of user-supplied Auto DIMM parts for a local demo.

No accounts, passwords or existing parts are modified. Re-running skips imported
records, including balances changed since import; conflicting SKUs abort atomically.
"""
import argparse
from pathlib import Path

import backup
from core import Store, now

PARTS = [
    ('Load cell', 'Delta Transducers', None, '2511231', 5, 10),
    ('Finger cylinder', 'Airtac', 'HFD12X50', None, 4, 8),
    ('Vertical cylinder', 'Airtac', 'HLQ12X50S', None, 5, 10),
    ('Solenoid valve', 'Airtac', '7V110-6', None, 10, 6),
    ('Tray cylinder', 'Airtac', 'TCL25X20S', None, 2, 4),
    ('Tray clamp cylinder', None, 'HLS16X20SAS', None, 4, 8),
    ('Finger reed switch sensor', 'Airtac', 'DMSH A11DW', None, 8, 16),
    ('Vertical reed switch sensor', 'Airtac', 'D-M98W', None, 10, 20),
    ('Flag sensor', 'Panasonic', 'PM-T45', None, 8, 16),
    ('Photoelectric sensor', 'Panasonic', 'CX-441', None, 12, 24),
]
NOTICE = ('DEMO: spare stock and planning values are illustrative. Cost $0 is an unknown-price '
          'placeholder, not a quote. Bin is unassigned; 365-day life and 0-day lead time are '
          'placeholders, not maintenance recommendations. Verify before operational use.')

def import_parts(store):
    added = 0
    with store.tx() as db:
        types = db.execute("SELECT id FROM types WHERE lower(trim(name))='dimm press'").fetchall()
        if len(types) != 1:
            raise ValueError('Exactly one DIMM Press type is required; no type will be guessed or created.')
        for index, (name, manufacturer, number, serial, usage, stock) in enumerate(PARTS, 1):
            key = f'auto-dimm-user-2026-10-16:{index}'
            if db.execute('SELECT 1 FROM part_provenance WHERE source_key=?', (key,)).fetchone():
                continue
            sku = f'DEMO-AD-{index:03d}'
            if db.execute('SELECT 1 FROM parts WHERE upper(trim(sku))=?', (sku,)).fetchone():
                raise ValueError(f'Conflicting SKU {sku}; import rolled back.')
            pid = db.execute(
                'INSERT INTO parts(sku,name,bin,supplier,supplier_number,cost,stock,threshold,target,lead_days,interval_days) '
                'VALUES(?,?,?,?,?,0,?,?,?,0,365)',
                (sku, name, 'DEMO - unassigned', '', '', stock, usage, usage * 3)).lastrowid
            db.execute('INSERT INTO compatibility VALUES(?,?)', (pid, types[0]['id']))
            db.execute('INSERT INTO part_provenance VALUES(?,?,?,?,?,?,?,?)',
                       (pid, key, manufacturer, number, serial, usage, 'Old Auto DIMM / DIMM Press', NOTICE))
            db.execute('INSERT INTO ledger(part_id,delta,reason,actor_id,created,operation_key) VALUES(?,?,?,NULL,?,?)',
                       (pid, stock, 'User-authorized illustrative opening stock for manager demo; not a physical count.', now(), key))
            store.audit(db, None, 'demo_part_import', {'part_id':pid, 'source_key':key,
                'source':'User-supplied parts; user confirmed DIMM Press compatibility and authorized sample stock.',
                'sample_stock':stock, 'notice':NOTICE})
            added += 1
    return added

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', required=True)
    parser.add_argument('--backup-dir', required=True)
    args = parser.parse_args()
    path = Path(args.db).resolve()
    snapshot, summary = backup.create(path, args.backup_dir)
    print('Verified pre-import backup:', snapshot, summary, flush=True)
    print('Added parts:', import_parts(Store(path)))
    print('Verified database:', backup.verify(path))

if __name__ == '__main__':
    main()
