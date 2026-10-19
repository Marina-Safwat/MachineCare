import sqlite3
import tempfile
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import backup
from core import Store
from import_auto_dimm import import_parts, PARTS

class AutoDimmImportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'test.db'
        self.store = Store(self.path)
        with self.store.tx() as db:
            db.execute("INSERT INTO types(name) VALUES('DIMM Press')")

    def tearDown(self):
        self.tmp.cleanup()

    def test_exact_source_and_demo_stock_with_idempotence_and_recovery(self):
        self.assertEqual(import_parts(self.store), 10)
        with self.store.tx() as db:
            parts = db.execute('SELECT * FROM parts ORDER BY id').fetchall()
            for part, source in zip(parts, PARTS):
                public = self.store.public_part(db, part)
                profile = public['provenance']
                self.assertEqual((part['name'], profile['manufacturer'], profile['manufacturer_part_number'],
                    profile['reference_serial'], profile['quantity_per_machine'], part['stock']), source)
                self.assertEqual(public['type_ids'], [1])
                self.assertIn('DEMO', profile['demo_notice'])
            self.assertIsNone(self.store.public_part(db, parts[5])['provenance']['manufacturer'])
            db.execute('UPDATE parts SET stock=9 WHERE id=1')
        self.assertEqual(import_parts(self.store), 0)
        with self.store.tx() as db:
            self.assertEqual(db.execute('SELECT stock FROM parts WHERE id=1').fetchone()[0], 9)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM ledger').fetchone()[0], 10)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM maintenance').fetchone()[0], 0)
        snapshot, summary = backup.create(self.path, Path(self.tmp.name) / 'backups')
        self.assertEqual(summary['schema_version'], 7)
        with sqlite3.connect(snapshot) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM part_provenance').fetchone()[0], 10)

    def test_conflicting_sku_rolls_back_every_part(self):
        with self.store.tx() as db:
            db.execute("INSERT INTO parts(sku,name,bin,cost,stock,threshold,target,interval_days) VALUES('DEMO-AD-005','Existing','A',0,1,0,1,365)")
        with self.assertRaises(ValueError):
            import_parts(self.store)
        with self.store.tx() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM parts').fetchone()[0], 1)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM part_provenance').fetchone()[0], 0)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM ledger').fetchone()[0], 0)

    def test_missing_machine_type_does_not_guess(self):
        with self.store.tx() as db:
            db.execute('DELETE FROM types')
        with self.assertRaises(ValueError):
            import_parts(self.store)

if __name__ == '__main__':
    unittest.main()
