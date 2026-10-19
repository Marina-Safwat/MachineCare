# Update 8: Administrator manages accounts/system; Leads manage operations

Current code supports schema 7: background-service state/outbox, UI hardening and imported-part provenance. See the 2026-10-16 checkpoint and docs/MANAGER_DEMO.md. Read PROJECT_STATUS.md, docs/FEATURE_INVENTORY.md, docs/BACKGROUND_SERVICES.md and docs/SECURITY_REVIEW.md before starting. Back up older databases before migration; backup.py now supports schemas 1–6. The installed database was upgraded from schema 4 to 7 after a verified backup on 2026-10-16; ten user-supplied Auto DIMM parts were imported with explicitly labeled illustrative stock. Email and scheduled service activation require configuration and authorization. The cumulative Update 8 instructions below are retained for history.

This cumulative update includes all earlier features: CSV exports, backup tooling, stock/audit viewers, full reorders, reservations, alerts, catalogs, account/line access, equipment filters and dialog fixes. It updates your existing local MachineCare pilot, rather than creating a separate app.

## Install

1. Stop Flutter (`q`) and the backend (Ctrl+C).
2. Back up your complete project and database while stopped. Keep backup Dart files outside app/lib.
3. Copy every included `backend` and `app` file into the matching folders under `F:\work\machinecare_flutter`, replacing matching files. Keep your existing database, server.py, main.dart, api.dart, pubspec.yaml and login test. Include all Python modules, migration files and file_export Dart helpers.
4. Run checks:

```powershell
cd F:\work\machinecare_flutter
python -m unittest discover -s backend/tests -v
cd app
flutter analyze
flutter test
```

If C: is short of temporary space, set these in the Flutter terminal first:

```powershell
New-Item -ItemType Directory -Force -Path F:\FlutterTemp
$env:TEMP = 'F:\FlutterTemp'
$env:TMP = 'F:\FlutterTemp'
```

5. Start the backend:

```powershell
cd F:\work\machinecare_flutter\backend
$env:MACHINECARE_ORIGIN = 'http://localhost:18080'
python server.py run
```

6. Start Flutter in a separate terminal:

```powershell
cd F:\work\machinecare_flutter\app
flutter run -d chrome --web-hostname localhost --web-port 18080 --dart-define=API_URL=http://127.0.0.1:8000
```

Schema is now version 7. Earlier schemas apply included migrations automatically. Existing accounts, stock, maintenance, orders, reservations and alerts remain. Do not run init/seed or delete the database. Assign other operational managers the Lead role; they do not need Administrator accounts for these new capabilities.

## Permission table

| Capability | Administrator (you) | Lead | Technician |
|---|---|---|---|
| Create/edit accounts, roles, assignments and access | Yes | No | No |
| Reset other users' passwords; enable/disable accounts | Yes | No | No |
| Change own password | Yes | Yes | Yes |
| Create/edit building and line structure | Yes | No | No |
| Register/edit/move/retire machines | All machines | Assigned machine access; both source/destination checked | No |
| Add/rename machine types and edit shared parts | Yes | Yes | No |
| Receive unlinked stock and adjust inventory | Yes | Yes | No |
| Complete/cancel approved maintenance requests | Yes | Within assigned machine access, including others' requests | Own requests only |
| Review pending early maintenance | Yes, excluding self-review | Within assigned machine access, excluding self-review | No |
| Initiate early maintenance | Approved with required explanation recorded | Approved with required explanation recorded | Pending Lead review |
| Manage entire reorder lifecycle | Yes | Yes | No |
| Read/export audit and stock logs | Yes | Yes | No |
| Maintenance history/export | All machines | Assigned machine access | Assigned machine access |
| Read shared inventory/export | Yes | Yes | Yes |
| Account and structural tools in Management | Visible | Hidden; server denies API attempts | Hidden; server denies API attempts |

Building/line hierarchy is treated as system structure. Machine registration, equipment status, machine types, part compatibility, supplier/cost settings and stock rules are operational and available to Leads. Shared catalogs, inventory, purchasing and audit logs are facility-wide; machine work and maintenance history remain limited by assigned building/line access. A Lead can rename a shared type or part even when it is used by machines outside their scope. Give access to all nine buildings only if that Lead should manage all machines.

## Operational changes

- Management replaces the Administration navigation label. Leads see machine-type and equipment registry tools; you also see account and building/line sections.
- Inventory shows Add part, Edit details, Receive and Adjust for Leads and Administrators. Reservation protection, required adjustment reasons, duplicate operation keys, catalog revisions and compatibility safeguards still apply.
- Leads see all requests for accessible machines, even when the original technician reports to a different Lead. The assigned Lead still receives the early-request notification, but another authorized Lead may review within their scope.
- Leads can complete or cancel another technician's request. Completion must represent physical work actually performed. Maintenance history, inventory ledger and audit actor use the signed-in completer. The request keeps the original requester ID, and the requester receives a notification when someone else completes/cancels it. Submitted identity fields cannot spoof the recorded person.
- A Lead/Administrator initiating an early replacement must provide an explanation; the request is immediately Approved and records that manager as the confirming actor. A technician's early request remains Pending until reviewed. Pending work reserves nothing; Approved work reserves stock.
- Completion still rechecks stock, status, compatibility and recent replacements. Duplicate completion remains blocked. Failed completion preserves its reservation until cancelled.
- Leads can view/export the full recorded audit log, including read-only account-change records. Credential fields remain redacted. Viewing a log does not grant account-editing permission.
- Full Lead reorder access remains: Lead requests approved immediately; ordering, partial/final delivery and cancellation allowed. Another Lead/Administrator reviews Administrator-submitted reorders. Supplier ordering/email remains manual.

## Exports and backups

Reports -> Download CSV exports maintenance, current inventory or reorder history. Stock movements and Audit log -> Export matching CSV export all matches, not merely loaded pages. Chrome downloads support UTF-8/Excel CSV, quoted text and formula-safe text cells. Row limit is 10,000; narrow filters if exceeded. Maintenance filters follow machine access; audit/stock/reorder exports are available to Leads/Administrators. Date filters use inclusive UTC dates; inventory is a current snapshot.

Backup remains local administrative tooling with no browser/API endpoint. Run from backend:

```powershell
python backup.py create --db .\machinecare.db --out F:\MachineCareBackups
python backup.py verify "F:\MachineCareBackups\YOUR_PRINTED_BACKUP_FILENAME.db"
```

Read BACKUP_RECOVERY.md for a drill using a separate database. Backup sessions are cleared in the copy only. Backup files are not encrypted or uploaded. Protect access to backend/database/backup files through Windows permissions; app roles do not restrict a person who has direct filesystem access to the SQLite files.

Alerts are evaluated on refresh/backend activity; no unattended scheduler or automated email is configured. The local HTTP pilot still binds loopback and is not a company-network deployment.

## Verification

Current laptop verification (2026-10-12): 123 backend tests passed; 33 Flutter widget tests passed after fixing the reorder status dropdown overflow; final Flutter analysis found no issues. Four record-browser tests also passed after a lint-only correction. Use F: temporary storage if C: is full. See PROJECT_STATUS.md for commands, details and remaining Chrome/download/recovery checks. The paragraph below is the original update author's historical result.

123 backend tests passed in 61.487 seconds, including 12 new permission/identity/scope checks and a real HTTP flow. See TEST_RESULTS.txt. Python syntax compilation passed. Flutter is unavailable here, so supplied widget tests, Flutter analysis and actual Chrome downloads require local verification. Follow VERIFY_SCENARIOS.md.

## Rollback

Stop both services and restore the complete previous code plus its matching stopped-database backup. Restoring a backup loses changes since that backup. Never overwrite a live database or downgrade only the code.
