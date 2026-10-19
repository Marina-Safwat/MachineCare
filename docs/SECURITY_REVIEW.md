# Security review and release gates

Review date: 2026-10-12. This is an engineering review with automated tests, not an independent penetration test or a guarantee of security. Production release is blocked until the gates below are met.

## Threat model

Assets: password hashes, session hashes, account/scope assignments, equipment and maintenance history, shared physical/reserved stock, purchase/delivery records, audit trail, exports, backup copies and SMTP credentials.

Actors: unauthenticated browser/network clients; authenticated Technicians; operational Leads; Administrators; a compromised browser; a malicious or mistaken operator; a local user with filesystem access; an SMTP service; worker/service operators.

Boundaries: Flutter input -> HTTP adapter -> authenticated domain transaction -> SQLite; role and building/line scope boundaries; protected records -> CSV/browser download; SQLite -> backup files; worker -> SMTP over verified TLS. Browser labels/hidden buttons are not authorization. Client identity fields never establish an actor.

| Threat | Verified protection / remaining boundary |
|---|---|
| Credential guessing / account enumeration | Generic login failures, equivalent PBKDF2 work for unknown users, bounded passwords; HTTP rate limit 15 attempts per loopback address / 5 minutes. Limit is process-local and shared by local users; restart resets it. Production needs centralized/per-account controls and SSO/MFA decision. |
| Stolen/replayed session | Random bearer token, SHA256 hash in DB, eight-hour expiry, version and active checks, reset/password/disable revocation, logout deletion. Tokens only in browser memory. No cookies, so ambient-cookie CSRF is not introduced. XSS remains a bearer-token threat. |
| Role escalation / object access | Backend tests cover Lead account/structure denial, Technician manager-action denial, machine source and destination scope, maintenance/history scope and requester ownership. Shared catalogs/inventory/purchasing/audits deliberately remain facility-wide for authorized roles. |
| Injection / malformed requests | Bound SQL values; fixed identifiers only; duplicate JSON keys rejected; bounded payload size/depth/strings/integers, nonfinite values and incorrect text types rejected. Export formula escaping and audit credential redaction retained. |
| Replay / concurrency / integrity | BEGIN IMMEDIATE, operation keys, state/revision checks, delivery-reference deduplication, stock guards and atomic completion. Existing concurrency and failure-rollback tests pass. |
| Cross-origin / DNS rebinding | Exact configured origin, restricted preflight, exact localhost/127.0.0.1 Host and loopback binding; no wildcard origins. No company network exposure. |
| HTTP abuse / disclosure | 32 KiB request limit, JSON content type, duplicate framing/transfer encoding rejection, 10-second connection timeout, generic errors, no request-body logs; no Python version in response header. API headers include no-store, nosniff, DENY, no-referrer and restrictive CSP. Thread/resource quotas remain a production gate. |
| Audit leakage / missing auth events | Login success/failure, logout and password-change events added without submitted credentials/unknown usernames. Account change/reset/disable audit retained. Permission denials, failed password changes and throttling episodes are also recorded without payloads. Centralized security logging remains a release gate. |
| Email disclosure / duplicates | Recipient mapping is backend-only administrative configuration; messages contain only a generic sign-in reminder, no business data or URLs/tokens. Active user and alert access rechecked before send. Unique event/user outbox; bounded retry; interrupted/ambiguous delivery held Uncertain. SMTP cannot guarantee exactly-once delivery. No real email sent in verification. |
| Backup / restore | SQLite online backup API, integrity/FK/schema validation, exclusive filenames, source sessions untouched and backup sessions cleared. Legacy schemas can be backed up before upgrading. Tested schema-4 copy -> 6 -> recovered copy with preserved business data. Backups still contain password hashes and business data and require OS ACLs/encryption. |
| Local file access | Anyone who can read/write backend DB, configuration or backups can bypass app roles. Windows ACLs, encryption, separate service identity, protected logs and backup location are deployment responsibilities. Python mode 0600 alone is not a Windows ACL policy. |

## Changes and evidence

- Added validation.py, hardening HTTP tests and credential-free authentication events.
- Added schema 6 durable worker state/outbox with disabled-by-default external delivery and Administrator-only system_status.
- Existing 123 backend workflow/HTTP tests passed after these changes. New worker/security tests are recorded in PROJECT_STATUS.md.
- Bandit 1.9.4 scanned backend excluding tests. Raw report: BANDIT_REPORT.json. B608 in access_policy.py uses a table name taken only from a literal tuple (`buildings` or `lines`), with bound IDs; it is not caller-controlled SQL. Two B110 findings in worker.py suppress socket-close exceptions only, so a successful SMTP DATA acceptance is not retried due to a failed close. Operational send errors are recorded with redacted messages. These findings are reviewed, not hidden by broad suppressions.
- OSV querybatch checked all 27 hosted packages in app/pubspec.lock: no reported advisories at query time. DEPENDENCY_AUDIT.json records the result. This does not cover Flutter/Dart SDK, Python interpreter, browsers, OS or unreported vulnerabilities. Backend runtime uses standard library only; pip-audit of unrelated global packages is not an application dependency audit.
- Installed Python is 3.10.8. The 3.10 series reached end of support on 2026-10-01. Upgrade to a supported, patched runtime in an isolated environment and rerun the suite before deployment. The global interpreter was not replaced in this session.
- Flutter 3.24.5 is the existing SDK. No SDK vulnerability clearance is claimed; review and test an approved maintained SDK upgrade before release. Web build passed with a Cupertino font-family warning; Material icons used by this UI rendered in browser checks.

## Deployment design (not deployed)

Keep the pilot bound to 127.0.0.1. Python documents http.server as unsuitable for production. Do not expose it through firewall changes or port forwarding. Target hosting/identity requirements are awaiting user/IT confirmation; changing the API framework requires agreement.

Before multi-user release: approve a supported service adapter/runtime; terminate HTTPS with managed certificates; serve frontend/API on a reviewed origin; trust forwarding headers only from a fixed proxy; decide company SSO/MFA; implement appropriate persistent account/IP rate limits and bounded resources; establish secret management; run as a dedicated least-privilege identity; deny ordinary users DB/backup/config access; encrypt backup storage; define retention/RPO/RTO and test restore; monitor worker freshness/failure and uncertain email; review CSP against the Flutter release renderer and use locally served assets; define session expiry/idle policy and incident revocation; maintain dependency/OS/browser patching and centralized redacted audit retention.

No Docker/network configuration, Windows scheduled task, SMTP activation or infrastructure change was applied. Independent security review, authenticated end-to-end browser testing and deployment/ACL validation are mandatory release gates.

References: [Python HTTP-server security warning](https://docs.python.org/3/library/security_warnings.html), [OWASP authentication guidance](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html), [Python 3.10 release/support schedule](https://peps.python.org/pep-0619/), [OSV batch API](https://google.github.io/osv.dev/post-v1-querybatch/).
