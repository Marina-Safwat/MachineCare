BEGIN IMMEDIATE;
CREATE TABLE IF NOT EXISTS job_state(name TEXT PRIMARY KEY, last_success REAL, last_error TEXT);
CREATE TABLE IF NOT EXISTS email_outbox(
 id INTEGER PRIMARY KEY, event_key TEXT NOT NULL, user_id INTEGER NOT NULL REFERENCES users(id),
 state TEXT NOT NULL DEFAULT 'Pending' CHECK(state IN ('Pending','Sending','Sent','Failed','Uncertain','Cancelled')),
 attempts INTEGER NOT NULL DEFAULT 0, next_attempt REAL NOT NULL DEFAULT 0,
 last_error TEXT, created TEXT NOT NULL, sent TEXT,
 UNIQUE(event_key,user_id));
PRAGMA user_version=6;
COMMIT;
