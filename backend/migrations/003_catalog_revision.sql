-- Add optimistic concurrency versions without changing stock or past maintenance.
BEGIN IMMEDIATE;
ALTER TABLE types ADD COLUMN revision INTEGER NOT NULL DEFAULT 0 CHECK(revision>=0);
ALTER TABLE parts ADD COLUMN revision INTEGER NOT NULL DEFAULT 0 CHECK(revision>=0);
PRAGMA user_version=3;
COMMIT;
