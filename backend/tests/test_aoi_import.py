import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import Store
from import_aoi import import_data, PARTS

class AoiImportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name) / 'test.db')
        self.store.seed()
    def tearDown(self):
        self.tmp.cleanup()
    def test_layout_source_and_idempotence_preserve_existing(self):
        with self.store.tx() as db:
            before = [tuple(r) for r in db.execute('SELECT * FROM machines')]
        result = import_data(self.store)
        self.assertEqual(result['parts_added'], 7)
        with self.store.tx() as db:
            after = [tuple(r) for r in db.execute('SELECT * FROM machines')]
            self.assertTrue(all(r in after for r in before))
            for line in db.execute('SELECT id FROM lines').fetchall():
                for name, count in [('DIMM Press',2),('AOI',1)]:
                    self.assertEqual(db.execute('SELECT COUNT(*) FROM machines m JOIN types t ON t.id=m.type_id WHERE m.line_id=? AND t.name=?', (line['id'],name)).fetchone()[0], count)
            profiles = db.execute("SELECT p.name,v.* FROM parts p JOIN part_provenance v ON p.id=v.part_id WHERE source_key LIKE 'aoi-user-%' ORDER BY p.id").fetchall()
            for row, source in zip(profiles, PARTS):
                self.assertEqual((row['name'],row['manufacturer'],row['manufacturer_part_number'],row['reference_serial'],row['quantity_per_machine']),source[:5])
                self.assertEqual('UNVERIFIED' in row['demo_notice'], not source[5])
            db.execute("UPDATE parts SET stock=1 WHERE sku='DEMO-AOI-001'")
        self.assertEqual(import_data(self.store), {'parts_added':0,'machines_added':0})
        with self.store.tx() as db:
            self.assertEqual(db.execute("SELECT stock FROM parts WHERE sku='DEMO-AOI-001'").fetchone()[0],1)
    def test_conflict_rolls_back_new_type_machines_and_parts(self):
        with self.store.tx() as db:
            before = db.execute('SELECT COUNT(*) FROM machines').fetchone()[0]
            db.execute("INSERT INTO parts(sku,name,bin,cost,stock,threshold,target,interval_days) VALUES('DEMO-AOI-004','Existing','A',0,1,0,1,365)")
        with self.assertRaises(ValueError): import_data(self.store)
        with self.store.tx() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM machines').fetchone()[0],before)
            self.assertIsNone(db.execute("SELECT id FROM types WHERE name='AOI'").fetchone())
            self.assertEqual(db.execute('SELECT COUNT(*) FROM part_provenance').fetchone()[0],0)

if __name__ == '__main__': unittest.main()
