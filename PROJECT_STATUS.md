# MachineCare project status

## Current checkpoint: readability / UI refresh — 2026-10-19

Visual refresh of the existing Flutter UI. There is no framework, API, permission or backend change.

- `app/lib/design.dart`:
  - Stronger type scale (15–16 px body) and a higher-contrast palette.
  - Semantic status colours, always paired with an icon or word.
  - Shared widgets: `StatusPill`, `Fact`/`FactGrid`, `Notice`, `EmptyState`, `SectionLabel`, `CountBadge`, `StockBar`.
- `app/lib/workspace.dart`:
  - Navigation is grouped (Daily work / Records & purchasing / Setup), with pending-approval and alert badges and a user card.
  - Content width is capped at 1180 px.
  - Overview cards are clickable and tinted by attention level, with stock bars.
  - Inventory shows physical/reserved/available tiles, a stock bar, labelled facts, a low-stock filter and a highlighted demo/source reference.
  - Approvals are grouped into Needs review / Ready to complete / Closed.
  - Reorders show a received-progress bar and labelled facts. History uses labelled facts.
  - Alerts show icons, the machine-details dialog uses readable part cards, and Reports sits in a card.
- `app/lib/main.dart`: login errors are shown as a notice.
- One test changed. `reservations_alerts_test.dart` now asserts the new physical/reserved/available tiles and the low-stock notice instead of the old single text line. All other test strings were preserved.
- Actual checks: `flutter analyze` no issues; `flutter test` **45 passed**, including 390/768/1440 width layout checks for all roles. Two overflows found by those checks during the work (stock-attention row, alert dropdown) were fixed.
- Visual check: release web build against a disposable demo database. Before/after captures are in `docs/ui-refresh-2026-10-19/`. Signed-in rehearsal on the laptop is still recommended. The installed database was not used.

## Current checkpoint: final manager deck with real screenshots — 2026-10-19

Added `docs/manager-presentation-2026-10-19/final/`. It contains a 21-slide editable PPTX with speaker notes, a PDF fallback, 14 real app screenshots and `WALKTHROUGH.md`, which has the slide-by-slide script and the production gap list. Generator: `docs/build_final_deck.js`. This replaces the graphical deck's "Screenshot capture pending" placeholders. Earlier decks are left unchanged.

- Screenshots were taken in a cloud workspace from a release web build served on loopback. The backend ran against a disposable scratch database: repository sample structure, the DIMM/AOI importers, throwaway demo accounts and fictional workflow rows. The installed database was not present or used. No application code changed.
- Actual checks (Linux, Python 3, Flutter 3.24.5): backend discovery **140 tests OK** (120 s); `flutter test` **45 passed**; `flutter analyze` **no issues**. `flutter build web --release --no-web-resources-cdn` passed, with the existing Cupertino-font warning.
- Deck: package validation passed; every slide rendered with LibreOffice and visually inspected.
- Still unverified: opening the deck in desktop PowerPoint, and signed-in Chrome/Excel CSV download on the laptop. Production gates are unchanged (see `docs/PRODUCTION_READINESS.md`).

## Current checkpoint: AOI / manager package — 2026-10-18 (Chicago)

Prepared the 19 October manager deck. User supplied AOI references and confirmed
one robot, PLC, power supply and control box per AOI. Added seven AOI catalog
entries and seven missing machines. Each of the three existing lines now has
two DIMM presses and one AOI: six DIMMs, three AOIs, plus the retained ACOS and
conveyor (11 total machines). Catalog: 20 entries. Schema remains 7.

- Pre-import verified backup:
  `backend/backups/pre-aoi/machinecare_20261019T041158Z_7558fb64.db` (UTC filename).
- Existing business rows compared with backup and preserved, including accounts,
  inventory, equipment, maintenance, orders and grants. Integrity check passed.
  Added stock is illustrative: two per AOI catalog item, 14 total. Unknown prices,
  bins, intervals and new asset identifiers/status remain explicitly demo values.
- `backend/import_aoi.py`: transactional/idempotent import, missing type creation,
  line count reconciliation without deleting other equipment, conflict rollback,
  exact supplied identifiers, separate serial references and provenance notices.
- Five importer tests passed (AOI and DIMM); no unrelated core/UI code changed.
  Separate-copy import and repeat verified. No full-suite rerun claimed this turn.
- Created 12-slide editable PPTX, embedded notes, PDF fallback, speaker notes and
  image previews in `docs/manager-presentation-2026-10-19`. All XML/relationship
  targets checked; overview visually inspected. Previews/PDF are generated from
  slide content, not a PowerPoint rendering. Actual desktop PPTX opening unverified.
- Automatic approval review rejected library installation and desktop Office
  access because its selected model was at capacity. Used local standard-library
  OOXML generation plus already-installed PDF/image libraries. No install required.
- `Start-Manager-Demo.cmd` / `.ps1` launch `backend/start_manager_demo.py`:
  fresh session-cleared snapshot, hidden loopback servers, duplicate-port guard,
  health checks and logs. Started successfully against
  `.verification/manager-demo/machinecare_20261019T041512Z_adb9fa45.db`.
  App URL: http://localhost:18080; API: 127.0.0.1:8000. Fictional work affects the
  demo copy, not the installed database. Sign in with current credentials.
- Updated `docs/MANAGER_DEMO.md`; added `docs/PRODUCTION_READINESS.md` with owners
  and acceptance evidence. Final signed-in browser/Excel and desktop PPTX checks
  remain user rehearsal items; production remains gated on the documented work.

## Current checkpoint: Auto DIMM presentation data — 2026-10-16

This checkpoint supersedes the installed-state statements below. The installed
database is now schema **7**, with **13 parts** (3 existing + 10 imported), 4 users,
and the same 2 existing maintenance records. User confirmed Old Auto DIMM means
DIMM Press and explicitly authorized illustrative spare stock. Ten provenance
records retain manufacturer, part number versus serial, quantities per machine,
and the demo assumptions. Tray clamp manufacturer remains unknown. Load-cell
2511231 remains a serial reference. Total illustrative opening stock: 122 units.

- Verified pre-import backup:
  `backend/backups/pre-auto-dimm/machinecare_20261016T175542Z_4a8defca.db` (schema 4).
- Stopped the identified old backend before upgrade; restarted current backend
  on 127.0.0.1:8000; `/health` returned local-pilot/ok.
- Existing accounts, equipment, part rows, stock ledger, maintenance, requests,
  deliveries, compatibility and access grants compared with backup and preserved.
  Existing migration 5 changed Lead reorder #1 Requested -> Approved, revision
  0 -> 1, with its policy audit. No supplier order or receipt was executed.
- Schema 7 adds part_provenance. Explicit `backend/import_auto_dimm.py` backs up
  before import, rejects SKU collisions transactionally, and skips previously
  imported source keys without resetting balances. No credentials were changed.
- Inventory shows manufacturer, supplied identifier, installed quantity and demo
  notice. Manufacturer is not silently treated as supplier. Demo cost $0 means
  unknown; bin/365-day interval/zero-day lead and planning levels are placeholders.
- Three importer tests passed (source fidelity, repeat safety/recovery, atomic
  collision and absent-type handling). Full existing Flutter suite: 44 passed;
  additional imported-part mobile/search/serial-label test: 1 passed. Flutter
  analysis: no issues. Web release build passed in 70.1s, with the existing
  Cupertino-font-family warning.
- Backend discovery: 138 tests in 370.990s, 137 passed and one migration-repeat
  error from the initial non-idempotent table creation. Fixed migration 7 to use
  CREATE TABLE IF NOT EXISTS; that failing test then passed in a targeted rerun
  (4.411s). Three additional migration regressions passed in 8.807s. No second full-suite run is claimed.
- Separate current-data copy rehearsal passed: imported finger cylinder + existing
  compatible machine, request approval, reservation without stock deduction,
  completion and single stock deduction. Recovery backup verified at schema 7.
  This rehearsal did not add maintenance records to the installed database.
- Replaced the old frontend configured for backend port 18001 with the current
  release build served locally at http://localhost:18080. Opened MachineCare in
  the app browser. Backend uses port 8000. Both temporary server processes must
  be restarted after this session/laptop restart; no startup service installed.

Next: signed-in browser rehearsal including CSV opened in Excel (budget 30–60
minutes if no issues), then a 10–15 minute manager walkthrough. See
`docs/MANAGER_DEMO.md` for source/sample values and presentation sequence. No
production-readiness claim; hosting, supported runtime, verified operational
data and security acceptance remain open. Older checkpoint test counts below
remain historical.

## Current checkpoint: background services, UI and security — 2026-10-12

The sections below the historical checkpoint heading are the previous session's record. This section is current.

### Installed state and data safety

- Architecture preserved: Flutter web, Python standard-library HTTP, SQLite. New code supports schema **6**. Live backend/machinecare.db was inspected read-only and remains schema **4**; the previously installed update had not yet migrated this database.
- Before data-affecting work, created and verified `backend/backups/pre-hardening/machinecare_20261012T142203Z_0b54ff77.db`. Existing backup code had refused v4, so it now validates supported legacy schemas before upgrade. Source sessions were not cleared; backup sessions were.
- A separate `.verification/upgrade-copy.db` upgraded 4 -> 6, reopened without changing data, and produced a verified recovery backup with matching business rows and no sessions. Accounts, equipment, stock, maintenance, orders, deliveries and grants were preserved. No live database migration, reseed, account creation/reset, real email, publishing or company-infrastructure change occurred.
- All previous uncommitted changes remain. No application dependency or SDK upgrade was made. Bandit was installed only under ignored .verification/security_tools for scanning.

### Implemented

- `backend/worker.py`: optional continuous checks; persistent job success/failure; scheduled verified backups; single-worker OS lock; TLS SMTP with backend recipient mapping, deduplicated outbox, bounded retries, Uncertain outcome hold, send-time recipient/scope recheck and audited manual requeue. Delivery requires configuration AND --allow-email. Live worker/email not activated.
- `006_jobs.sql`: job_state and email_outbox. `validation.py`: bounded typed/nested payload validation and duplicate-JSON-key rejection.
- Authentication audit: login success/failure/throttle, logout, password success/failure, permission denial. No submitted credential fields in these events. Unknown users perform equivalent password-hash work.
- HTTP hardening: correct 18080 default origin, exact loopback Host checks, JSON/framing validation, timeouts, restrictive API headers, generic errors, hidden runtime version. Existing scoped roles and Lead capabilities retained.
- UI: shared design theme, more readable warning/error text, password visibility/required-field validation, labeled line/building/type/status selectors, better numeric errors, cancellation/account/adjustment confirmations, duplicate-action guard, inventory search, mobile app bar/padding, status styling, Administrator service status and maintenance outlook/repeated-early counts. Existing dialog-owned controller disposal retained.
- API client: friendly connection/timeout/unexpected-response errors and clearing expired tokens. A timeout instructs refresh before retry, because server completion may be uncertain.
- `app/tool/visual_preview.dart`: explicitly labeled, read-only disposable UI fixture for browser/layout/export checks. Never deploy this target. It contains sample public state only, no credentials; mutation requests fail explicitly.

### Actual checks

| Check | Actual result |
|---|---|
| Full backend discovery after authentication/HTTP changes | **134 tests passed**, 256.228s (123 legacy + 11 new) |
| Subsequent hardening suite after manual email-requeue addition and response cleanup | **12 tests passed**, 3.769s; includes the extra retry reconciliation regression |
| Full Flutter suite | **44 tests passed**, about 14s |
| Subsequent account/part/reorder editor checks after immediate duplicate-submit guards | **10 tests passed**, about 2s |
| Final Flutter analysis | **No issues**, 1.5s; generated build/** excluded |
| Flutter web release build | Passed; Material icon tree-shaking/Cupertino font-family warning recorded, no compile errors |
| Legacy-data upgrade/recovery | Passed on separate copy; live DB remains v4 |
| Bandit 1.9.4 | Three findings reviewed: fixed-table SQL identifier (B608) and two SMTP-close cleanup handlers (B110); see docs/SECURITY_REVIEW.md |
| OSV dependency query | 27 hosted locked Dart packages checked, no reported advisories; SDK/runtime/OS not covered |
| Browser | Actual login rendered at narrow/desktop widths; required validation and accessibility labels observed. Read-only real Workspace fixture inspected for dashboard/inventory/machine selectors/reports, including phone layout. |

The full backend run was initially blocked by C: disk-full errors; the successful run used TEMP/TMP on F:. Only our own identified failed Flutter-run directory `C:\Users\VTM\AppData\Local\Temp\flutter_tools.1e89f4bf` was removed. Other user files were untouched. Use F: temporary storage for Python and Flutter checks. Browser-debug temporary entrypoints caused an analysis false positive; app/analysis_options.yaml now excludes generated build files rather than suppressing application diagnostics.

### Remaining blockers and release gates

- SMTP endpoint/approved recipients/secret provisioning and explicit real-send authorization; worker/service auto-start and backup destination/ACL/encryption/retention policy. Integration code is not a configured operational service.
- Four prior scope items have undefined business rules: multi-bin allocation, completion backdating, emergency override/review and historical correction/reversal. Clarification requested; not implemented speculatively. See docs/FEATURE_INVENTORY.md for every feature's status and the separation from new suggestions.
- Intended multi-user hosting/identity model is unconfirmed. Python is **3.10.8** (3.10 support ended 2026-10-01); a supported patched runtime and Flutter SDK assessment/testing are release gates. Global runtime untouched. http.server remains explicitly local-only, not production-ready.
- Actual Chrome CSV file completion/bytes/Excel opening remains unverified: fixture action displayed "Download requested", but the available in-app browser download event timed out. Debug browser logs contained a service-worker registration warning. No completed download is claimed.
- Browser operational checks used read-only fixtures, not authenticated end-to-end live workflows. Full real-browser acceptance, screen-reader review, infrastructure/ACL checks and **independent security review** are still required. No claim of guaranteed security.

### Continue / verify

Read docs/FEATURE_INVENTORY.md, docs/BACKGROUND_SERVICES.md and docs/SECURITY_REVIEW.md. From root set TEMP/TMP to an existing F: directory, then run `python -m unittest discover -s backend/tests -v`; from app run `flutter analyze`, `flutter test` and `flutter build web`. Startup still uses backend `MACHINECARE_ORIGIN=http://localhost:18080`, `python server.py run` and frontend `flutter run -d chrome --web-hostname localhost --web-port 18080 --dart-define=API_URL=http://127.0.0.1:8000`.

Back up again immediately before upgrading the live DB; stop older server/worker processes and use matching code. Do not run init/seed. BACKUP_RECOVERY.md remains the separate-filename recovery guide; leave email disabled after recovery until deliveries are reconciled.

## Historical checkpoint: initial update verification

Verified on this laptop on 2026-10-12. This document supersedes the older environment's verification claims in TEST_RESULTS.txt.

## Installed update and local state

Found `F:\work\MachineCare_Lead_Operations_Update.zip`. Compared all 31 archive files byte-for-byte after removing the archive's enclosing directory: every file matched the installed project before this session's edits. The cumulative Lead Operations update is fully applied; no required update files are missing. Existing main.dart, api.dart, pubspec.yaml and login test remain present.

The repository already contained uncommitted cumulative-update changes and untracked export/backup files. They were preserved. No archive extraction, reset, dependency upgrade, backend change, account change or live-database operation was performed. Tests create and clean up their own disposable SQLite databases.

## Changes in this session

- app/lib/workspace.dart: set the reorder status dropdown's `isExpanded` to true so its contents fit its 240-pixel field. Three widget tests had reported a 75-pixel horizontal overflow before the fix.
- app/test/record_browser_test.dart: added braces around the audit fixture conditional to satisfy Flutter analysis; behavior unchanged.
- Added AGENTS.md and this continuation record; refreshed the current verification notes in INSTALL.md and VERIFY_SCENARIOS.md.

## Actual verification

Environment: Python 3.10; installed Flutter SDK version file reports 3.24.5. No SDK/dependency upgrades were requested or performed.

| Check | Result |
|---|---|
| `python -m unittest discover -s backend/tests -v` from root | PASS: 123 tests, 392.120 seconds, exit 0 |
| `flutter analyze` from app, after fixes and test cleanup | PASS: no issues, 2.0 seconds, exit 0 |
| `flutter test` from app, after dropdown fix | PASS: 33 tests, about 9 seconds, exit 0 |
| `flutter test test/record_browser_test.dart` after the subsequent lint-only edit | PASS: all 4 tests, exit 0 |

The first widget run failed because C: lacked temporary space (OS error 112). Rerunning with TEMP/TMP on F: exposed the three genuine dropdown failures; those are fixed. An analysis run during tests saw generated temporary listener files; final analysis after cleanup is clean. The Flutter launcher also required SDK-cache access outside the workspace sandbox.

For repeat widget runs without using C: temporary space, from app:
```powershell
New-Item -ItemType Directory -Force -Path .\build\test_temp | Out-Null
$env:TEMP = 'F:\work\machinecare_flutter\app\build\test_temp'
$env:TMP = $env:TEMP
flutter test
```
Finish tests before running analysis when temporary files live inside app. Alternatively use the external F:\FlutterTemp location described in INSTALL.md, with appropriate filesystem access.

## Policy and lifecycle review

Backend authorization and Flutter visibility match the supplied policy: accounts and building/line structure are Administrator-only; Leads have operational catalog, inventory, purchasing, records/export and scoped machine tools. Backend tests cover both source/destination machine scope, cross-technician completion/cancellation, authenticated actor recording, scoped early review, Lead immediate reorder approval, separate review for Administrator reorders, Technician restrictions, revisions, duplicate deliveries, reservations and atomic stock/history behavior.

Flutter tests verify Lead tools and hidden account/structure controls, operational request controls, exports, alerts, account/line editors and reorder workflows. EntryDialog owns controller disposal in State.dispose; its save/cancel/reopen transition regressions both passed. No lifecycle rewrite was needed.

## Architecture and startup

Flutter web frontend; Python standard-library HTTP server; SQLite schema version 5 with ordered migrations. No FastAPI/Django. See AGENTS.md for permission/inventory invariants and module map.

Backend, from backend:
```powershell
$env:MACHINECARE_ORIGIN = 'http://localhost:18080'
python server.py run
```
Frontend, from app:
```powershell
flutter run -d chrome --web-hostname localhost --web-port 18080 --dart-define=API_URL=http://127.0.0.1:8000
```
Do not run init/seed or recreate the Administrator. Never overwrite a live database. Preserve credentials outside logs/Git. BACKUP_RECOVERY.md describes verified backups and recovery with a separate filename.

## Remaining manual verification and limitations

- Actual Chrome CSV downloads: check filename, downloaded bytes/UTF-8, opening in a spreadsheet, formula protection and filtered results. Widget tests verify the downloader handoff; backend tests verify CSV generation/authorization, not Chrome download behavior.
- Exercise VERIFY_SCENARIOS.md in a disposable copy using each role, including dialog transitions and complete ordering/maintenance flows in Chrome. No interactive authenticated browser session or web release build was run in this session.
- Perform the documented backup/recovery drill with a separate database and compare representative counts/history/stock to the snapshot. Automated backup tests passed, but no live-data recovery drill was performed.
- C: temporary space remains limited; use F: as above. This session did not delete unrelated files to reclaim space.
- Local loopback pilot only. Alerts evaluate on refresh/backend activity. Unattended scheduling, automatic email and supplier integrations are absent; ordering/email remain manual.

## Suggested next two features (not implemented)

1. A scoped maintenance planning calendar/work queue with due-soon filters and assignment visibility, built on existing intervals/history and machine access.
2. A purchasing planning view combining available/reserved stock, outstanding deliveries and supplier lead times, with an editable draft reorder batch and existing approval/receipt safeguards.

Agree on scope before implementing either. Retain the same permission, concurrency and UI regression coverage.
