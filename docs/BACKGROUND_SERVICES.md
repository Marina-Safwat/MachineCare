# Background checks, email and scheduled backups

Implementation is available; activation is a separate administrative step. No real email has been sent and no Windows startup task has been installed. The worker must remain running for unattended checks; sleep/shutdown pauses it. Use a reviewed service/scheduler with restart-on-failure for deployment.

1. Back up the existing DB with `python backend/backup.py create --db backend/machinecare.db --out backend/backups/pre-upgrade`. Protect this directory. Stop old server/worker processes before starting new code. New code upgrades existing schema 1–5 to 6 through ordered migrations. Do not downgrade upgraded data.
2. Copy backend/worker.example.json to backend/worker.local.json (ignored by Git). Set check_seconds, backup_seconds, a protected backup_directory, and optional SMTP configuration. Use an absolute existing DB path when launching. Directory creation is automatic; disk-full/permission failures appear in job status. Backups are not automatically deleted; set a reviewed retention process outside this worker.
3. Start checks/backups without email, from root:

```powershell
python backend/worker.py --db F:\work\machinecare_flutter\backend\machinecare.db --config backend/worker.local.json
```

Use `--once` for one cycle. First run checks immediately; backup runs if there is no successful prior run or the configured interval elapsed. Last success/error persists in job_state. Administrator -> Management -> Background services -> Check service status shows timestamps and queue counts. Absence of activity does not mean a service is healthy or configured.

Email requires BOTH `email.enabled: true` and the explicit CLI flag `--allow-email`. Do not activate without authorization. SMTP requires certificate-verified SSL or STARTTLS; no plaintext/insecure-TLS option exists. `password_env` names an environment variable supplied by the service's secret manager. Never put the password in JSON, command arguments, source control or frontend defines. `recipients` maps existing user IDs (strings) to approved email addresses. This is local administrator configuration; Leads cannot change it through the API.

Existing in-app notifications and current active alert episodes are queued when recipients are enabled; this may send a backlog. Review counts before enabling delivery. Low-stock/shortfall alerts go to configured active managers; maintenance alerts require machine access. Generic notification emails contain no business detail. Confirm recipient identity through company procedures before mapping it.

Queue states:

- Pending: waits for delivery; connection/rejection failures back off from 60 seconds, with at most five attempts.
- Sending: claimed atomically before contacting SMTP.
- Sent: SMTP accepted the message; this does not prove inbox arrival/read receipt.
- Failed: retry limit reached. Correct infrastructure/configuration and review with an administrator before a controlled retry.
- Uncertain: disconnected during delivery or worker interrupted after claiming; consult SMTP delivery logs before any retry. Automatic retry is deliberately stopped to avoid duplicate mail. There is no general exactly-once SMTP guarantee.
- Cancelled: user disabled/removed from mapping or alert resolved/access revoked before delivery.

One worker per DB is enforced by an OS lock released automatically when its process exits. A lock filename alone is not evidence of a running worker. Restart converts leftover Sending records to Uncertain. Queue and schedule state are included in schema-6 backups. After recovery, leave email disabled until queue/history are reconciled against the mail service; restoring an older snapshot can otherwise replay events already sent after that snapshot.

After stopping the worker and reconciling the provider's logs, a local administrator can requeue a Failed delivery using `--retry-email ID --reason "Reconciliation reason"` with the usual --db/--config arguments. An Uncertain delivery additionally requires `--confirm-uncertain`. This operation audits the decision and queues only; it sends no email. Sent deliveries cannot be requeued by this command. Never retry an uncertain outcome merely because the recipient has not read the email.

No email provider/inbox test, service auto-start test, ACL validation, encrypted off-host backup or retention policy has been completed. Use BACKUP_RECOVERY.md for a separate-filename recovery drill and SECURITY_REVIEW.md for deployment gates.
