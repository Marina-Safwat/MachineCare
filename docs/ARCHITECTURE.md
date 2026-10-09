# Architecture and operator guide

## Pilot topology

Flutter web in the laptop browser calls a loopback Python API. The API uses SQLite transactions for sessions, equipment, parts, requests, maintenance, ledger, notifications and audits. The schema uses foreign keys, unique identifiers, stock constraints and one completed maintenance record per request.

`core.py` owns decisions. `server.py` handles HTTP, a fixed allowed origin, an input-size limit and rate limiting. `api.dart` handles requests and keeps tokens only in memory. Material widgets present state returned by the API; permissions are enforced again by the API. The API never accepts a technician name as the maintenance author.

## Replacement transitions

Normal request → Approved → Completed or Cancelled.
Early request → Pending → Approved or Rejected; Pending/Approved can be Cancelled. Approved work can be Completed only by its requester.

Approval writes review metadata, but neither creates completed maintenance nor consumes stock. Completion checks permission, request state, active machine, current compatibility, latest replacement interval and stock inside one transaction. It captures cost, location, quantity and authenticated technician, deducts stock, inserts a ledger entry and marks completion. A repeated completion fails rather than deducting twice. Two normal requests for the same machine/part cannot bypass an interval established by the first completion.

SQLite BEGIN IMMEDIATE serializes writes for the local pilot. PostgreSQL production should use row locks/atomic conditional updates and unique idempotency constraints with explicit retry handling.

## Authentication

Passwords use salted PBKDF2-SHA256 with 600,000 iterations. Session secrets are random; only their SHA256 hashes are stored. Sessions expire after eight hours. User version changes and session deletion revoke sessions after reset/disable/password change. Temporary-password users can only change password or sign out. API clients use bearer Authorization headers, not ambient cookies. The browser origin is checked and CORS is limited to the configured local origin.

This is custom pilot auth, not an established-auth-library implementation. Production should move to a maintained framework and audited session strategy. The loopback API is not a production application server.

## API contract

`POST /login`: username/password → token/user.
`GET /state`: authenticated workspace snapshot.
`POST /actions/{action}`: authenticated domain operation.
`GET /health`: public liveness, no business data.

Admin actions: building, line, type, machine, part, user, reset, disable, receipt, adjust.
User actions: password, logout, request, review, complete, cancel.

Most mutation responses require a subsequent `/state` refresh. Action payload examples are in the Flutter forms and tests. Inventory receipt/request clients must retain one operation_key per form submission attempt; duplicate keys fail safely. Completion is idempotency-protected by request state and database uniqueness. This pilot rejects repeats instead of replaying prior success responses.

## Administrator guide

Create the first account from the CLI. Create Lead accounts before Technician accounts and enter the lead ID and permitted building IDs. Create/edit buildings and lines. Register machines with one station field; change a line ID to move, or status to Retired to retire. Use inventory receipts for deliveries and signed adjustments with reasons for count corrections. Resetting an employee password forces a new first-login change; disabling revokes its sessions.

## Lead guide

Open Approvals to find assigned early requests. Read the reason, notes and mandatory explanation. Approve or reject with a review comment. Do not use approval to represent physical work. Refresh notifications and request state as needed. Leads cannot approve their own work.

## Technician guide

Expand the equipment hierarchy or search. Open a machine to see compatible parts, shared bin stock and its exact part replacement dates. Submit a quantity/reason. Explain early replacements. Wait for assigned-lead approval where required. After performing the physical work, choose Record physical completion and confirm. If work is cancelled or approval becomes obsolete, cancel the request rather than recording a false completion.

## Proposed production deployment

Use a Flutter release web build behind the company HTTPS reverse proxy and a maintained API framework service on the same origin. Migrate the schema into versioned PostgreSQL migrations. Add a background worker and durable outbox for notifications/retry/deduplication. Store secrets in server environment or company secret management. Use separate runtime/database identities, least-privilege database access, private database networking, approved logging, encrypted backups and restore drills. Review CSRF if moving to cookies. Enforce scoped roles on every new endpoint and test access to individual records.

Docker Compose is an eventual deployment option, not included or verified here. Final deployment details depend on approved company infrastructure.
