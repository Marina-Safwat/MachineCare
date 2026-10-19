# Feature inventory — 2026-10-12

This supersedes the stale SCOPE.md checklist after inspection of source, tests and handoffs. Implemented means working code exists; integration/release gates are stated separately. Current role policy overrides older proposal restrictions.

| Previously documented/requested feature | Status | Evidence / remaining work |
|---|---|---|
| Hierarchy, station names, optional line descriptions | Implemented | Explorer/search/filters, readable names, scoped API. |
| Machine register/edit/move/retire | Implemented | Lead source/destination scope; labeled line/type/status selectors. |
| Shared types/catalog/supplier/cost/interval/compatibility | Implemented | Revision and active-work safeguards; Lead/Administrator. |
| Accounts/roles/supervisor/building and line grants | Implemented | Administrator-only backend/UI; coverage and revocation tests. |
| Login/password/reset/disable/logout/expiry | Implemented local pilot | PBKDF2, hashed sessions, forced change, revocation, validation and auth audit. Production identity decision remains. |
| Shared inventory/receipts/adjustments | Implemented | Atomic ledger, nonnegative stock, reservation protection, confirmation/search. |
| Reservations and shortages | Implemented | Pending reserves nothing, availability bounded at zero, shortfalls visible. |
| Maintenance request/review/complete/cancel | Implemented | Early explanation/manager confirmation, scope/ownership, actor/requester separation, confirmation, atomic stock/history. |
| Historical cost/location and last replacement dates | Implemented | Captured snapshots and per-part last dates. |
| Reorders/ordering/partial receipts/cancel | Implemented | Lead immediate approval, separate Administrator review, deduplication and revisions. Supplier ordering manual by design. |
| Persistent alerts/acknowledgements | Implemented | Low stock/shortfall/overdue episodes, per-user acknowledgement, resolution/recurrence and scope. |
| Unattended checks | Implemented; live service inactive | Worker loop, durable timestamps, single-worker OS lock; running process/service required. No startup task installed. |
| Configurable email/retry/delivery tracking | Implemented integration; needs infrastructure verification | TLS SMTP, backend recipient mapping, unique outbox, bounded retries, uncertain-outcome hold, generic content and send-time access check. Disabled; fake transport tests. Approved SMTP/recipients/provider test/send authorization missing. |
| Scheduled backups/recovery | Implemented; live service inactive | Worker schedule/status, legacy backup, verified separate-copy upgrade/recovery. Destination ACLs, retention, encryption/off-host policy and service auto-start require IT decisions. |
| Authentication/account audit | Implemented | Login success/failure/throttle, logout, password success/failure, permission denial; existing account/reset/disable audit. Centralized tamper-resistant logging not deployed. |
| Stock/audit viewers and CSV | Implemented; browser delivery needs verification | Filters/pagination, backend/widget protections. Fixture browser requested export but download completion not observed; Chrome/Excel checks pending. |
| History filters | Implemented via Reports | Search/date-filtered maintenance export; History remains an unfiltered history view. |
| Upcoming/overdue and repeated early analytics | Implemented basic outlook | Reports: overdue/next 30 days, unknown dates, repeated early counts by captured location/part. Not a diagnostic or assignment calendar. |
| Responsive design/forms/accessibility | Implemented; acceptance needs verification | Shared theme, selectors, focus/keyboard fields, preserved failures, loading/confirmations. Responsive widget tests and representative screenshots. Full assistive-technology/user acceptance review pending. |
| Ordered migrations | Implemented | Schema 6; v1–5 path; actual v4-copy upgrade/reopen/recovery checked. Live DB unchanged. |
| Multi-bin inventory | Missing; decision required | No bin-transfer/reservation/allocation rules documented. |
| User-entered completion dates | Missing; decision required | Need backdating window/timezone/interval/approval rules; current completion uses server UTC. |
| Emergency override/retrospective review | Missing; decision required | Need roles, stock limits, review deadline/escalation. Ordinary requests are not emergency work. |
| Corrections/reversals | Missing; decision required | Need approval and stock/history/order effects. No destructive history edits introduced. |
| Auth library/cookies/framework/PostgreSQL/Docker | Not implemented; agreement required | Older proposal ideas, not authorization to replace the current architecture. No cookies introduced. |
| Multi-user deployment | Incomplete; hosting/security gates | Local-only. Supported runtime/SDK, HTTPS/service identity/ACL/secrets/SSO/monitoring and independent review required. |

## Manager demonstration update ? 2026-10-18

Seven AOI component references added; all three configured lines now have two DIMM presses and one AOI. New operational values are marked as demo assumptions. See MANAGER_DEMO.md and PRODUCTION_READINESS.md. The 12-slide PPTX/PDF and a separate-database demo launcher are available. Desktop PowerPoint and signed-in Chrome/Excel acceptance remain unverified.

## Suggestions rather than agreed requirements

The prior session suggested an assignment/calendar queue and a batch purchasing planning view. The basic outlook addresses the older upcoming-maintenance requirement. Calendar interaction, assignment and batch order creation are not implemented or represented as agreed requirements.

## Missing decisions

Multi-bin allocation, backdating, emergencies, reversals; hosting/identity model; SMTP recipients and send authorization; backup retention/encryption and restore objectives. Routine implementation continued; work dependent on these decisions remains incomplete.
