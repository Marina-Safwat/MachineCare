# MachineCare working instructions

Continue the existing local pilot; do not rebuild it or change frameworks without agreement. Read PROJECT_STATUS.md, INSTALL.md, VERIFY_SCENARIOS.md and BACKUP_RECOVERY.md first. Preserve existing uncommitted changes.

## Architecture

- Current inventory/security/operations: docs/FEATURE_INVENTORY.md, docs/SECURITY_REVIEW.md, docs/BACKGROUND_SERVICES.md. docs/SCOPE.md and docs/ARCHITECTURE.md retain older proposal text and are not current permission/feature authorities.
- worker.py owns optional background checks, backups and generic TLS email. validation.py rejects malformed inputs. Schema 6 adds job_state/email_outbox; schema 7 adds part_provenance for imported identifiers and demo assumptions. system_status is Administrator-only. Live integrations require configuration/authorization; never claim them active from passing fake-transport tests.

- Flutter/Dart web frontend in app/lib (main.dart, api.dart, workspace.dart, file_export*.dart).
- Python standard-library HTTP server and SQLite in backend. Core modules: core.py, server.py, access_policy.py, catalog.py, purchasing.py, inventory_status.py, records.py, reports.py, backup.py.
- Schema version 7; upgrades use ordered backend/migrations. Buildings contain lines, lines contain machines; machine types link compatible shared parts. Station means position within a line; line description is optional.

## Permissions and invariants

- Administrator only: accounts, roles, supervisor/access assignments, resets/activation, building/line structure, system configuration and local backup administration.
- Lead and Administrator: shared catalogs/types, inventory receipts/justified adjustments, purchasing, audit/stock viewers and exports; machine operations and maintenance require machine access. Machine moves check both source and destination. Leads never gain account/access editing.
- Technicians retain machine access and own-request completion/cancellation only; no catalog, purchasing, adjustment or audit administration.
- Approved requests reserve stock; Pending early requests reserve nothing. Technician early work requires explanation and scoped manager review. Manager early work requires explanation and records immediate confirmation.
- Completion atomically deducts stock once, creates history/ledger, releases the reservation, records authenticated completer and preserves requester. Another actor's completion/cancellation notifies requester. Cancellation never deducts stock. Failed completion preserves reservation. Adjustments cannot consume reserved stock; shortages stay visible; availability is bounded at zero.
- Historical cost/location remain snapshots. Shared inventory/catalogs/purchasing/audit are facility-wide; maintenance history follows machine access.
- Lead reorders start Approved; Administrator reorders require another manager's review. Ordering adds no stock; receipts add only received quantities. Preserve revision, operation-key, case-insensitive delivery-reference and over-receipt protections. Cancelling a partial balance preserves receipts.
- CSV exports enforce permissions, redact credentials and protect against spreadsheet formulas.

## Data safety

Never delete/reseed the existing database, recreate the Administrator, add default passwords, overwrite a live database or expose credentials. Tests use disposable databases. Backups clear sessions in the copy only; recovery uses a new filename. Do not run init/seed/reset tooling on the installed database. Avoid unrelated dependency upgrades and large refactors.

## Checks and startup (PowerShell)

From project root: `python -m unittest discover -s backend/tests -v`.
From app: `flutter analyze` and `flutter test`.
Use F: TEMP/TMP for Python tests as well as Flutter if C: is full. app/tool/visual_preview.dart is a read-only test fixture, never the production build target. Test all roles at small and large widths and keep entered form values on error.
If C: is full, create an F: temporary directory and set TEMP/TMP in that terminal. When using app/build/test_temp, finish tests before analysis so generated listener files are not analyzed. Flutter needs write access to its SDK cache outside the workspace.

Backend, from backend:
```powershell
$env:MACHINECARE_ORIGIN = 'http://localhost:18080'
python server.py run
```
Frontend, from app:
```powershell
flutter run -d chrome --web-hostname localhost --web-port 18080 --dart-define=API_URL=http://127.0.0.1:8000
```
Use port 18080 (8080 previously failed). Keep local loopback deployment.

## Flutter lifecycle and handoff

Dialog controllers must live through the exit transition and be disposed by their owning State, not immediately after awaiting showDialog. EntryDialog owns its supplied controllers. Retain lifecycle regressions for save/cancel/reopen.

Report actual checks, not historical handoff claims. Record results, limitations and remaining manual checks in PROJECT_STATUS.md. Alerts evaluate on refresh/backend activity and via the optional worker. Read docs/BACKGROUND_SERVICES.md and docs/SECURITY_REVIEW.md. Email requires configured TLS SMTP plus explicit --allow-email; do not send real email or install startup jobs without authorization. Supplier ordering remains manual.

Manager presentation: docs/manager-presentation-2026-10-19 contains PPTX/PDF/notes. Start-Manager-Demo.cmd launches a fresh snapshot, not the installed DB. Source includes user-confirmed AOI counts and per-line 2 DIMM + 1 AOI layout. Never conflate sample stock/planning or asset tags with verified operational data.
