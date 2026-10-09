# MachineCare: Manufacturing Maintenance & Spare Parts Management

Prepared by Marina Gerges • Automation Software Engineer
Proposal date: October 8, 2026

## Requested decision

Approve a controlled MachineCare pilot for one production line, with an assigned maintenance lead and inventory owner. Authorize requirements review with technicians, PE, Quality and IT/security before company deployment.

## Problem and proposed outcome

Equipment spans nine buildings and multiple lines. Spare-part stock, replacement history and early replacement decisions need a consistent, traceable workflow. MachineCare brings those records together so technicians can find equipment quickly, see the exact last replacement date for each part, and consume shared stock only when work is physically completed.

## Proposed solution

Use a Flutter interface designed for desktop browsers and tablets, backed by an application API and relational database. Equipment is organized as Building → Line → Machine Type → Station. A readable name such as “B03 · L02 · Station 04 · DIMM Press” identifies the production location; asset tags remain separate identifiers.

Administrators issue employee accounts and control permissions. Technicians request replacements and record authorized work. Assigned leads review early replacement requests, with mandatory explanations and recorded comments. A shared stock ledger connects replacement consumption to inventory availability.

## Demonstrable pilot

The delivered implementation contains the Flutter client source and an executable local API with SQLite persistence. It includes administrator setup without default credentials, account creation/reset/disable, forced temporary-password changes, building access checks, equipment registration/moves/retirement, multi-type part compatibility, receipts/adjustments, exact machine/part replacement dates, lead approvals and transactional completion. The backend is tested. Flutter compilation and browser demonstration must be verified on the presentation laptop.

The dashboard displays operating status, low stock, pending decisions and recorded maintenance cost. Cost means completed quantity × unit cost captured when the replacement is recorded; it excludes labor, freight and tax.

## Production architecture

Flutter → HTTPS API → PostgreSQL

The API owns authentication, permissions, equipment, inventory, maintenance and purchasing rules. A background worker will deliver email and maintain retryable notification records. Employee devices never connect directly to the database. The local pilot intentionally uses SQLite and loopback HTTP to simplify presentation setup; this is not the final deployment configuration.

## Delivery stages and acceptance gates

| Stage | Deliverable | Acceptance gate |
|---|---|---|
| Local demonstration | Main technician/lead workflow and sample equipment | Flutter build passes; demo runs on laptop |
| Requirements validation | One-line equipment/parts list, roles and expected lifetimes | Maintenance, PE and Quality agree on rules |
| Production foundation | Framework API, PostgreSQL migrations, HTTPS/session controls | IT/security approve deployment design |
| Inventory & purchasing | Reservations, reorder approvals, partial receipts and deduplication | Inventory owner verifies balances and concurrent operations |
| Operational readiness | Notifications, emergency review, corrections, exports, E2E tests and backups | Operators accept workflows and restore drill passes |
| Controlled rollout | Limited approved production deployment | Pilot results accepted before all nine buildings |

Timing and cost estimates should follow inventory size, hosting approval and workflow review. No delivery date or ROI is guaranteed by this proposal.

## Success measures

Measure time to locate a compatible part, percentage of completed replacements with accurate history, inventory discrepancies, unreviewed early replacements and time to resolve stock alerts. Establish the baseline before deployment and compare during the controlled pilot.

## Support needed

An inventory owner; a maintenance lead; approved sample equipment/part data; IT hosting and security review; Quality/PE agreement on expected replacement intervals and emergency rules.

## Suggested presentation opening

“MachineCare will give technicians one place to find machines, check compatible spare parts and record replacements. It will also give leads control over early replacements and keep shared inventory accurate. Today I’m proposing a controlled pilot and showing the main workflow; production deployment will follow IT and security review.”
