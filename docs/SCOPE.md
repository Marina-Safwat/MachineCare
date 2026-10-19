# Requirement coverage and remaining work

Historical checklist retained for provenance. See FEATURE_INVENTORY.md and PROJECT_STATUS.md at the project root for current implementation and verification; the pending statuses below are outdated.

This is a local proposal pilot. Major requirements below are explicitly tracked; absent functionality is not claimed as implemented.

| Requirement | Status and limits |
|---|---|
| Flutter responsive UI | Source delivered; compilation, widget tests and browser QA pending |
| Nine buildings and equipment hierarchy | Implemented with optional sample seed; expandable building/line/type/machine explorer |
| Station-based names, separate asset tags | Implemented; no redundant machine number |
| Buildings/lines create/edit, optional descriptions | Implemented |
| Machine types create/edit | Create implemented; edit pending |
| Register/edit/move/retire machines | Implemented; historical replacement location retained |
| Own username/password login, no registration | Implemented local pilot |
| Admin creates accounts and initial roles/lead/building access | Implemented at creation; editing role/lead/access later pending |
| Line-level access and assigned-equipment permissions | Pending; pilot enforces building-level access |
| Password changes/resets, disabled accounts and revocation | Implemented; sessions expire in eight hours |
| Established auth library, secure session cookies, production hardening | Pending; pilot uses salted PBKDF2 and hashed, in-memory bearer session tokens over loopback HTTP |
| Login rate limiting | In-memory per-IP limit in HTTP adapter; restart resets it; production distributed limiter pending |
| Machine compatible parts, exact replacement dates | Implemented |
| Multi-type compatibility with shared SKU stock | Implemented; one bin per SKU in pilot; multi-bin inventory pending |
| Part metadata and opening balances | Implemented on creation; part editing pending |
| Receipts/adjustments, audit ledger, no negative balances | Implemented; adjustment reasons required |
| Atomic completion, duplicate deductions, competing last-item requests | Implemented and tested |
| Reservations | Not implemented; approved requests do not guarantee stock |
| Early warning, mandatory explanation and assigned-lead review | Implemented; no valid assigned lead blocks request |
| Approval/rejection/completion/cancellation | Implemented; completion records server UTC time (user-entered actual time pending) |
| Self-approval prevention, authenticated technician identity | Implemented |
| Emergency override and retrospective lead review | Pending; do not use ordinary requests to claim emergency functionality |
| In-app request/review notifications | Implemented synchronously; refresh required |
| Background jobs, retry, delivery tracking and automatic email | Pending; app explicitly says email unavailable |
| Low-stock dashboard | Implemented as computed state; persistent alert lifecycle, inventory-lead notification and duplicate suppression pending |
| Reorder workflow, outstanding orders and partial deliveries | Pending; generic receipts are not order receiving |
| Upcoming/overdue maintenance | Overdue count for parts with history implemented; upcoming schedule pending |
| Spending, recent work, status and approval metrics | Implemented for visible history; excludes labor/freight/tax |
| Frequent early replacements/repeated-failure analytics | Pending |
| History filters and protected CSV export | Pending; machine detail shows its history |
| Audit preservation and corrections/reversals | Audit events and immutable completed-work API implemented; formal correction/reversal workflow pending |
| Accessibility, keyboard, errors and entered values | Standard labeled Material fields, loading/errors, preserved dialog values; full accessibility audit pending |
| Modular production architecture | API/core/SQL and Flutter API/login/workspace separated; finer domain modules required as project grows |
| Migrations and schema versioning | Initial schema with user_version=1; ordered upgrade migrations pending |
| Docker Compose and production deployment | Pending; architectural instructions only; local HTTP adapter must not be publicly deployed |
| Backups and restore | Stop-and-copy pilot instructions; encrypted automated backup/restore testing pending |
| Tests | Backend domain + HTTP integration tests delivered; Flutter widget/browser E2E, purchasing, job retry and reservation tests pending |

## Assumptions

- All available inventory is one shared balance per SKU/bin; no reservations.
- Request quantity is a positive integer.
- “Early” compares exact elapsed UTC seconds against expected days; no history means no early warning and unknown due date.
- A normal request enters Approved as work authorization; a separate completion event still records physical work.
- Actual replacement time is server time at recording; only record immediately after physical work in this pilot.
- Building-level access governs equipment; inventory metadata is visible to authenticated staff across the facility.
- The first administrator is created interactively. No credentials are shipped.
- Sample seed data does not represent measured production inventory.

## Security limits

The HTTP server is a loopback development adapter with custom session handling. It is not a security-reviewed production service. Production requires HTTPS, maintained framework/auth components, an explicit cookie/token and CSRF strategy, least-privilege hosting, centralized rate limiting, durable audit controls, secrets management and browser security headers. Server-side authorization and parameterized SQL are already used, but are not evidence of complete security compliance.
