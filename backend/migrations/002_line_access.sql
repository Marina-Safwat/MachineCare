-- Additive v1 -> v2 upgrade. Existing building grants are preserved.
BEGIN IMMEDIATE;
CREATE TABLE IF NOT EXISTS line_access (
 user_id INTEGER NOT NULL REFERENCES users(id),
 line_id INTEGER NOT NULL REFERENCES lines(id),
 PRIMARY KEY(user_id,line_id)
);
PRAGMA user_version=2;
COMMIT;
