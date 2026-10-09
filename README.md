# MachineCare — Flutter local pilot

A Flutter web client and a persistent Python/SQLite API for demonstrating the main maintenance workflow. This is a proposal pilot, not a production release or a claim that all uploaded requirements have been completed. Do not enter real company credentials or sensitive production data into the pilot.

## Start on your Windows laptop

Requirements: Python 3.12 or newer, Flutter stable with bundled Dart, Chrome or Edge. No PostgreSQL or Node.js required. Obtain Flutter from https://docs.flutter.dev/install/with-vs-code and confirm with `flutter doctor`. Python is available at https://www.python.org/downloads/windows/. If your Windows installation uses `python` instead of `py`, substitute it below.

1. Extract this ZIP into a normal writable folder, such as `Documents\MachineCare`.
2. Open PowerShell in that folder. In a first terminal:

```powershell
cd backend
py server.py init
py server.py seed
py server.py run
```

`init` prompts for your own administrator username and password (at least 12 characters). There is no default password. `seed` is optional and adds clearly named sample equipment, nine buildings, three types, and three parts. Run it only once on an empty equipment database. It does not create employees.

3. In another PowerShell terminal in the extracted root:

```powershell
.\Setup-Flutter.ps1
cd app
flutter run -d chrome --web-hostname localhost --web-port 8080 --dart-define=API_URL=http://127.0.0.1:8000
```

If PowerShell blocks the script, run these commands manually; do not change a company policy:

```powershell
cd app
flutter create --project-name machinecare --platforms web .
flutter pub get
flutter analyze
flutter run -d chrome --web-hostname localhost --web-port 8080 --dart-define=API_URL=http://127.0.0.1:8000
```

The generation command creates Flutter web platform scaffolding; keep the supplied `lib` files and supplied `pubspec.yaml`. The script explicitly preserves the manifest. If manual generation changes that manifest, copy it again from the ZIP before `flutter pub get`.

Use `-d edge` if you use Edge. Visit **http://localhost:8080**, not the API's port 8000. Log in with the administrator account you created. The allowed development origin is exactly `http://localhost:8080`; a different hostname or port requires matching `MACHINECARE_ORIGIN` before starting the API.

## Demo employee setup

Administration → Create employee account:

- First create a Lead. Give it building access `1,3`; leave Lead ID blank. Note its displayed account ID.
- Then create a Technician, set its Lead ID to that lead's ID, and give building access `1,3`.
- Choose temporary passwords of 12+ characters. Each employee must change its password on first login, then log in again.
- Account relationships and access are assigned at creation in this pilot. Editing them after creation requires a later management endpoint/UI; do not use direct database edits for production.

The app supports your own usernames and passwords. Employees do not need ChatGPT accounts. Refreshing the browser clears its in-memory token and requires signing in again. Restarting the API preserves equipment, accounts and history in `backend/machinecare.db`.

## Tomorrow's 5-minute demo

1. Show Overview: machines, low stock, approval counts and spending.
2. Open Equipment → B01 → L01 → DIMM Press → Station 01.
3. Show the separate asset tag, compatible shared stock/bin and “Not recorded” last replacement.
4. As Technician, request a pneumatic seal. Find it under Approvals, then record physical completion.
5. Reopen the machine: its last replacement is now recorded and shared stock decreased by one.
6. Request another seal immediately. The UI warns it is early and requires an explanation. Submit, but do not complete.
7. Sign in as Lead, approve with a comment. Explain that stock is unchanged by approval.
8. Sign back in as Technician and record completion. Show the history and lead notification.
9. As Administrator, edit a building/line, receive stock, and show account reset/disable controls.
10. End with `docs/PROPOSAL.md` and `docs/SCOPE.md` to explain the production roadmap.

For a short demo, complete employee first-login password changes before your meeting. Three separate browser tabs can hold different users, but every tab has its own in-memory session. Each screen needs Refresh to see another user's changes.

## Verification

```powershell
py -m unittest discover -s backend/tests -v
```

See `docs/VERIFICATION.md` for actual results and verification limitations. Flutter was unavailable in the delivery environment: its code has **not been compiled, analyzed or browser-tested there**. Run `flutter analyze` and the demo on your laptop before presenting. No screenshots are claimed to be Flutter runtime output.

## Folder structure

- `app/lib/main.dart`: application theme, login and first-password-change entry.
- `app/lib/api.dart`: HTTP API client, in-memory bearer token.
- `app/lib/workspace.dart`: responsive workspace, dashboard, explorer, forms and workflows.
- `backend/core.py`: domain rules, authorization, atomic inventory and audits.
- `backend/server.py`: loopback HTTP transport, input-size cap, fixed-origin CORS, login throttling.
- `backend/schema.sql`: relational schema and initial idempotent schema initialization.
- `backend/tests`: independent temporary-database unit and API integration tests.
- `docs`: proposal, architecture, scope, verification and operator notes.

## Troubleshooting

- API not reachable: keep the first terminal running; open `http://127.0.0.1:8000/health` to verify it.
- “Change temporary password first”: finish the password dialog, then log in again.
- “Outside assigned buildings”: administrator must create the user with the necessary building IDs.
- “No active assigned lead”: early replacement is deliberately blocked. Assign a lead in the account creation flow; account reassignment is a remaining requirement.
- Port occupied: stop the previous development process. Do not change the port without updating the frontend URL or allowed origin.
- Dependencies unavailable: the initial Flutter setup needs internet for its packages. Once installed, the pilot itself uses no external service.
- Windows asks for firewall/admin permission: the pilot API binds only to loopback. Follow your device's policy; do not bypass required approval.

## Backup and restore (pilot)

Stop the backend with Ctrl+C. Copy `backend/machinecare.db` into a protected backup location. Restore by stopping the API, keeping a safety copy of the current database and replacing it with the backup. Restart and check the demo records. Do not use a live file copy as your backup procedure. Production needs automated encrypted backups and tested restore drills.

## Company deployment

Do **not** expose `server.py` to a LAN or internet. See `docs/ARCHITECTURE.md`. An approved production server should use HTTPS, a maintained application server/framework, hardened sessions, PostgreSQL, migrations, backup jobs and notifications. Docker Compose and production deployment scripts are not included because this HTTP pilot is not a production service.
