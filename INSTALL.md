# Step 2: Building and production-line permissions

This cumulative update includes account editing, equipment filters and the dialog-lifecycle fix.

## What is new

Create/edit an account with access to whole buildings, individual production lines, or a mixture. Line checkboxes appear under each building. Do not select a whole-building checkbox when you intend to restrict that user to selected lines in that building.

Examples:

- B01 whole building -> all B01 lines, including lines created later.
- B01 L01 only -> L01 machines; no access to B01 L02 or future sibling lines.
- B01 whole building + B03 L02 -> all B01 lines and only B03 L02.
- Administrator -> all equipment, regardless of stored selections.
- Nothing selected -> no equipment access (shared parts metadata remains visible).

A selected line does not imply a whole-building grant. Its parent building is displayed only so the equipment explorer can show the hierarchy. Individual line grants follow stable line IDs if a line is renamed. They follow that line if moved between buildings, but a move that breaks lead/technician coverage is blocked.

Lead coverage must match technicians' scopes. A lead with only today's individual lines cannot supervise a technician granted the whole building: whole-building access also includes future lines. Grant the lead that whole building or narrow the technician to explicit lines.

## Install on your Windows laptop

1. Stop Flutter with `q` and the backend with Ctrl+C.
2. Back up your app and `backend/machinecare.db` while the backend is stopped. Keep backups outside app/lib.
3. Copy these package files to the matching locations under `F:\work\machinecare_flutter`:

| Package file | Destination |
|---|---|
| backend/core.py | backend/core.py |
| backend/access_policy.py | backend/access_policy.py (new) |
| backend/schema.sql | backend/schema.sql |
| backend/migrations/002_line_access.sql | backend/migrations/002_line_access.sql (new folder/file) |
| app/lib/workspace.dart | app/lib/workspace.dart |
| backend/tests/test_core.py | backend/tests/test_core.py |
| app/test/*.dart | app/test/ (keep your existing login test) |

Copy every backend file above before restarting. The migration is required; do not copy only core.py. Do NOT delete your database or run init/seed again.

4. Run checks:

```powershell
cd F:\work\machinecare_flutter
python -m unittest discover -s backend/tests -v
cd app
flutter analyze
flutter test
```

If your C: drive remains short of space, set the temporary folder in this Flutter terminal before those Flutter commands:

```powershell
New-Item -ItemType Directory -Force -Path F:\FlutterTemp
$env:TEMP = 'F:\FlutterTemp'
$env:TMP = 'F:\FlutterTemp'
```

5. Start the backend in one terminal:

```powershell
cd F:\work\machinecare_flutter\backend
$env:MACHINECARE_ORIGIN = 'http://localhost:18080'
python server.py run
```

Its first start upgrades database version 1 to 2 by adding the line_access table. Existing accounts, passwords, stock, history and whole-building grants are preserved. Repeated starts do not erase line grants or reset the schema version.

6. Start Flutter in another terminal:

```powershell
cd F:\work\machinecare_flutter\app
flutter run -d chrome --web-hostname localhost --web-port 18080 --dart-define=API_URL=http://127.0.0.1:8000
```

## Use

Administrator -> Administration -> Accounts -> pencil icon -> Building and production-line access. Uncheck the whole building, then check only the intended lines. Save. The employee must sign in again after permission changes. New accounts use the same checkboxes plus a temporary password and role/lead dropdowns.

Pending early requests must retain technician access and an assigned lead with matching coverage; contradictory edits fail atomically. Lead assignment changes still transfer pending requests to the new lead. Completed history is retained. Requests, equipment and history are filtered by the user's current equipment access; machine moves can change who can see that machine's old history.

Previously approved work can become inaccessible when permissions are narrowed or equipment moves. Restore access to complete it, or have an administrator cancel obsolete work. The update does not introduce approved-work reassignment or reservation features.

## Verification results

37 backend tests passed in 25.647 seconds on Python 3.12.14. This includes the prior 23 tests and 14 new line-access tests. Python syntax compilation passed for core.py and access_policy.py. See TEST_RESULTS.txt.

Tests cover v1 migration preserving data/permissions, migration reruns preserving line grants, forbidden sibling-line API calls, whole-building access to future lines, explicit-line isolation, lead scope coverage, account creation, revocation, invalid scopes, pending request safeguards, historical visibility and line/machine moves.

Flutter is unavailable in the delivery environment. The supplied widget tests for account selection/creation and dialog lifecycles are NOT executed here. Run flutter analyze/flutter test and the manual scenarios below on your laptop.

## Rollback

If required, stop both services and restore the complete pre-update code AND its database backup together. Do not downgrade only the code: old versions do not enforce individual-line permissions. Restoration also reverts work recorded since that backup. Never restore over a running database.

## Next feature

Machine-type and part-detail editing. Reordering/partial receipts follow that step.
