BEGIN IMMEDIATE;
CREATE TABLE IF NOT EXISTS part_provenance(
 part_id INTEGER PRIMARY KEY REFERENCES parts(id),
 source_key TEXT UNIQUE NOT NULL,
 manufacturer TEXT,
 manufacturer_part_number TEXT,
 reference_serial TEXT,
 quantity_per_machine INTEGER NOT NULL CHECK(quantity_per_machine>0),
 machine_family TEXT NOT NULL,
 demo_notice TEXT NOT NULL
);
PRAGMA user_version=7;
COMMIT;
