# MachineCare production readiness — 18 October 2026

Current status: working local pilot; not approved for company-wide production.
The manager presentation is dated 19 October 2026. No production completion date
is committed. The following gates need owners and evidence, not merely a UI demo.

| Gate | Still missing | Proposed owner | Acceptance evidence |
|---|---|---|---|
| Operational data | Verified stock, bins, prices, suppliers, intervals, asset tags, stations, serials and operating status | Maintenance lead | Signed inventory/equipment review; remove demo assumptions through a controlled conversion |
| AOI identification | TM model; unknown manufacturers; nameplate confirmation of exact supplied model strings | Maintenance lead | Verified component list and asset-specific serial records |
| Hosting | Approved production service adapter, HTTPS, certificates, deployment and upgrade/rollback plan | IT + engineering | Reviewed staging deployment; retain loopback-only pilot until approved |
| Runtime | Supported patched Python/Flutter/Dart baseline and rerun dependency/security checks | Engineering | Approved versions, reproducible build and regression results |
| Identity/security | SSO/MFA decision, account lifecycle, durable abuse controls, service identity, file ACLs and secrets | IT/security | Independent security assessment and remediation acceptance |
| Backups/recovery | Scheduled monitored backups, encrypted off-host storage, retention, recovery time/data-loss objectives | IT/operations | Successful restore drill on separate host, documented ownership and alerts |
| Operations | Service startup/restart, monitoring, logs, patching and incident/support ownership | IT/operations | Restart/failure tests and operational runbook |
| User acceptance | Signed-in browser workflows for all roles, Chrome/Excel downloads, accessibility and concurrency/load checks | Maintenance + engineering | Documented acceptance results; no unresolved critical defects |
| Business rules | Multi-bin allocation, backdating, emergency review, historical correction/reversal | Maintenance manager | Implement approved rules or explicitly defer them from the approved release scope |
| Optional integrations | SMTP/recipients/secrets, real-send authorization and delivery tests if email is required | IT + business owner | Approved configuration; monitored sending; uncertain-delivery reconciliation |

Supplier ordering is currently manual. There is no approved ERP integration.
SQLite need not be replaced solely for the presentation; assess concurrency and
deployment requirements before choosing a different database. A framework rewrite,
container deployment or company network exposure is not part of this update.

## Manager decision requested

Approve a supervised pilot on one validated line, appoint maintenance and IT owners,
and agree acceptance measures (traceability, inventory accuracy and operator
usability). Set a production target only after these gates are scoped and assigned.

## Presentation versus acceptance evidence

The application has automated workflow and permission tests. This update adds
transactional AOI/line-layout import tests and a separate-copy verification. These
do not substitute for a signed-in browser acceptance session or security review.
The PowerPoint package is generated locally and XML/relationship validated; its
PDF and image previews are generated from the same content. A desktop PowerPoint
open/render check was unavailable because automatic approval review was at capacity.
Open the deck once before the meeting; the PDF is the fallback.
