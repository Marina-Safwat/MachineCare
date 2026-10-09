BEGIN IMMEDIATE;
CREATE TABLE reorders (
 id INTEGER PRIMARY KEY,
 part_id INTEGER NOT NULL REFERENCES parts(id),
 requested_by INTEGER NOT NULL REFERENCES users(id),
 quantity INTEGER NOT NULL CHECK(quantity>0),
 received_quantity INTEGER NOT NULL DEFAULT 0 CHECK(received_quantity>=0 AND received_quantity<=quantity),
 state TEXT NOT NULL DEFAULT 'Requested' CHECK(state IN ('Requested','Approved','Ordered','Partially received','Received','Rejected','Cancelled')),
 reason TEXT NOT NULL,
 supplier_snapshot TEXT NOT NULL,
 supplier_number_snapshot TEXT NOT NULL,
 unit_cost_snapshot REAL NOT NULL CHECK(unit_cost_snapshot>=0),
 created TEXT NOT NULL,
 reviewed_by INTEGER REFERENCES users(id),
 reviewed TEXT,
 review_comment TEXT,
 po_reference TEXT,
 ordered_by INTEGER REFERENCES users(id),
 ordered TEXT,
 cancelled_by INTEGER REFERENCES users(id),
 cancelled TEXT,
 cancellation_reason TEXT,
 operation_key TEXT UNIQUE NOT NULL,
 revision INTEGER NOT NULL DEFAULT 0 CHECK(revision>=0)
);
CREATE TABLE reorder_deliveries (
 id INTEGER PRIMARY KEY,
 reorder_id INTEGER NOT NULL REFERENCES reorders(id),
 quantity INTEGER NOT NULL CHECK(quantity>0),
 delivery_reference TEXT NOT NULL,
 notes TEXT NOT NULL DEFAULT '',
 received_by INTEGER NOT NULL REFERENCES users(id),
 received TEXT NOT NULL,
 operation_key TEXT UNIQUE NOT NULL,
 UNIQUE(reorder_id,delivery_reference)
);
CREATE INDEX reorder_part_state ON reorders(part_id,state);
PRAGMA user_version=4;
COMMIT;
