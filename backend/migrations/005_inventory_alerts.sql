BEGIN IMMEDIATE;
CREATE TABLE IF NOT EXISTS alerts(
 id INTEGER PRIMARY KEY,
 condition_key TEXT NOT NULL,
 kind TEXT NOT NULL,
 part_id INTEGER NOT NULL REFERENCES parts(id),
 machine_id INTEGER REFERENCES machines(id),
 message TEXT NOT NULL,
 opened TEXT NOT NULL,
 resolved TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS alert_active_condition ON alerts(condition_key) WHERE resolved IS NULL;
CREATE TABLE IF NOT EXISTS alert_acknowledgements(
 alert_id INTEGER NOT NULL REFERENCES alerts(id),
 user_id INTEGER NOT NULL REFERENCES users(id),
 acknowledged TEXT NOT NULL,
 PRIMARY KEY(alert_id,user_id)
);
CREATE INDEX IF NOT EXISTS request_reservation_balance ON requests(part_id,state);
INSERT INTO audit(actor_id,action,detail,created)
 SELECT requested_by,'lead_reorder_policy_upgrade','{"reorder_id":' || id || ',"policy":"Lead bypass"}',strftime('%Y-%m-%dT%H:%M:%f+00:00','now')
 FROM reorders WHERE state='Requested' AND requested_by IN (SELECT id FROM users WHERE role='Lead');
UPDATE reorders SET state='Approved',reviewed_by=requested_by,
 reviewed=strftime('%Y-%m-%dT%H:%M:%f+00:00','now'),
 review_comment='Lead request: approval not required (policy upgrade)',revision=revision+1
 WHERE state='Requested' AND requested_by IN (SELECT id FROM users WHERE role='Lead');
PRAGMA user_version=5;
COMMIT;
