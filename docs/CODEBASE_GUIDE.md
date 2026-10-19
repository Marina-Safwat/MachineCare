# MachineCare: the complete codebase guide

This guide is for owning the app: understanding every file, changing anything, and rebuilding it from an empty folder. Read it top to bottom once. After that, use the **Recipes** section (part 8) as a reference.

The project is small:

- about **1,500 lines of Python** (backend)
- about **1,100 lines of Dart** (frontend)
- about **1,400 lines of tests**

Everything else is documentation, scripts and generated files.

---

## Part 1. The big picture

MachineCare is three things talking to each other:

```
┌─────────────────────────┐   HTTP + JSON    ┌──────────────────────────┐   SQL    ┌────────────────┐
│  FRONTEND (Flutter web) │ ───────────────▶ │  BACKEND (Python)        │ ───────▶ │  DATABASE      │
│  app/lib/*.dart         │                  │  backend/*.py            │          │  SQLite file   │
│  runs in Chrome         │ ◀─────────────── │  server.py + core.py     │ ◀─────── │ machinecare.db │
│  port 18080             │   {"error": …}   │  port 8000               │          │                │
└─────────────────────────┘                  └──────────────────────────┘          └────────────────┘
```

- **Frontend** = what people see and click. It is written in **Dart** using **Flutter**, compiled to a web page and opened in Chrome. It holds **no rules**: it only draws screens and sends requests.
- **Backend** = the brain. It is written in **Python**, using **only the standard library**, so nothing needs `pip install`. Every rule lives here: who can do what, how stock changes, and what counts as early.
- **Database** = one file, `backend/machinecare.db`, in **SQLite** format. All data lives in it. It is git-ignored, so it is never in the repository.

### The only three ways the frontend talks to the backend

| Request | What it does | Code that answers it |
|---|---|---|
| `POST /login` with `{username, password}` | Returns a session **token** and the user | `Store.login` in `core.py` |
| `GET /state` (token in header) | Returns **everything this user may see**: machines, parts, requests, history, alerts, reorders… in one JSON object | `Store.state` in `core.py` |
| `POST /actions/<name>` with a JSON body | Performs **one change**, e.g. `/actions/request`, `/actions/complete`, `/actions/reorder_receive` | `Store.execute` → `Store._execute` in `core.py` |

The pattern behind the whole app:

1. The screen loads `/state`.
2. The user clicks something, and the screen sends `/actions/<name>`.
3. The screen loads `/state` again and redraws.

If you understand that loop, you understand the architecture.

---

## Part 2. Running it from zero

You need **Python 3** and the **Flutter SDK**. Your laptop has Flutter 3.24.5. Use a **supported Python** for production, because 3.10 is past end of support.

```powershell
# Terminal 1: backend
cd backend
python server.py init      # ONLY on a brand-new empty database: asks for your admin username/password
python server.py seed      # OPTIONAL, ONLY on an empty database: sample buildings/lines/machines/parts
$env:MACHINECARE_ORIGIN = 'http://localhost:18080'
python server.py run       # starts the API on http://127.0.0.1:8000

# Terminal 2: frontend
cd app
flutter pub get
flutter run -d chrome --web-hostname localhost --web-port 18080 --dart-define=API_URL=http://127.0.0.1:8000
```

> ⚠️ **Never run `init` or `seed` on your real installed database.** They are for a fresh, empty file only. To experiment safely, copy the database first (Part 9) and point the server at the copy with `--db`.

What each piece of the commands means:

- `server.py run --db <file> --port <n>` chooses which database file and port to use.
- `MACHINECARE_ORIGIN` is the exact web address the browser page comes from. The backend refuses requests from any other origin, so this must match the Flutter port.
- `--dart-define=API_URL=...` tells the Flutter app where the backend is. It is read in `api.dart`.

---

## Part 3. Follow one click through the whole app

Example: a technician requests a new **finger cylinder** for a DIMM press. Follow it file by file.

**1. Screen (`app/lib/workspace.dart`)**
- The Equipment page is drawn by `equipment()`.
- Clicking a machine calls `machineDetails(m)`, which opens a dialog listing that machine's compatible parts.
- Clicking **Replace this part** calls `request(m, p)`.
- `request` works out whether this replacement is "early". It then calls `form(...)` to open a dialog with fields Quantity, Reason, Notes, and Early explanation (only if early).

**2. Dialog (`EntryDialog` in `workspace.dart`)**
- Checks each field: required, whole number, and so on.
- Then runs `onSave`, which calls `widget.api.action('request', {...})`.

**3. Network (`app/lib/api.dart`)**
- `action('request', data)` sends `POST http://127.0.0.1:8000/actions/request`.
- The JSON body goes with an `Authorization: Bearer <token>` header.

**4. HTTP layer (`backend/server.py`)**
- Checks the Origin and Host headers, body size and content type.
- Rejects duplicate JSON keys and runs `validation.payload(...)`.
- Calls `store.execute(token, 'request', data)`.

**5. Rules (`backend/core.py`, `Store._execute`, the `if action=='request':` block)**
- `self.user(db, token)` finds who you are from the token.
- `self.machine(db, u, machine_id)` checks you have access to that machine's building or line.
- It checks the part is **compatible** with the machine's type.
- It checks enough **available** stock exists (physical minus reserved).
- It looks up the last replacement of this part on this machine. If that was sooner than `interval_days`, the request is **early**.
- Early work requires an explanation. A technician's early request becomes **Pending** for their lead. Everything else is **Approved** straight away, which **reserves** stock.
- It inserts a row in `requests`, notifies the lead if needed, and writes an `audit` row.

**6. Transaction (`Store.tx()` in `core.py`)**
- Everything above ran inside one `BEGIN IMMEDIATE` transaction.
- Before committing, `inventory_status.sync(db)` re-checks the alert conditions.
- If anything raised an error, the whole change is rolled back. Nothing half-happens.

**7. Back to the screen**
- The backend replies `{"id": 7, "state": "Approved", ...}`.
- `form()` calls `refresh()`, which gets `/state` again. The new request appears under **Approvals → Ready to complete**.

**8. Completion**
- Later, someone clicks **Record physical completion**. That calls `confirmComplete` → `act('complete', ...)`.
- The backend's `complete` branch:
  - deducts the stock **once**
  - writes a `maintenance` (history) row with a **snapshot** of location and cost
  - writes a `ledger` row
  - sets the request to Completed
  - notifies the requester if someone else completed it.

Every feature in the app follows this same path. Only the action name and the rules block change.

---

## Part 4. Every file in the repository

Legend: ✏️ = you will edit this to change behaviour · 📄 = documentation · 🔧 = tooling/script · 🤖 = generated, don't hand-edit · 🧪 = test

### Root folder

| File | What it is |
|---|---|
| `AGENTS.md` 📄 | Rules for AI assistants working on the project: permissions, data-safety and how to run things. It is also a good one-page summary of the business rules. |
| `README.md` 📄 | Original setup instructions (first-time `init`/`seed`). Older, but still correct for a brand-new install. |
| `INSTALL.md` 📄 | How updates were installed on your laptop, plus the permission table. |
| `PROJECT_STATUS.md` 📄 | **Running diary** of every work session: what changed, which tests ran, and what is still open. The newest entry is at the top. |
| `VERIFY_SCENARIOS.md` 📄 | Manual test checklist to click through for each role. |
| `BACKUP_RECOVERY.md` 📄 | How to make and verify backups, and how to recover into a **new** file. |
| `TEST_RESULTS.txt` 📄 | Old test output from an earlier environment. Historical only. |
| `.gitignore` 🔧 | Keeps the database (`*.db`), backups, `.env` and caches out of git. |
| `Setup-Flutter.ps1` 🔧 | One-time helper: generates Flutter's web scaffolding and runs `pub get` + `analyze`. |
| `Start-Manager-Demo.cmd` / `.ps1` 🔧 | Double-click demo launcher. It calls `backend/start_manager_demo.py`. |

### `backend/`: the Python brain

| File | Lines | What it does | Edit it when… |
|---|---|---|---|
| `server.py` ✏️ | 95 | The **HTTP adapter**: opens port 8000 and turns HTTP requests into calls on `Store`. Also handles the CLI commands `init`/`seed`/`run`, the login rate limit (15 attempts per 5 minutes), security headers and the CORS origin check. | …you add a new URL path (rare: almost everything is an `/actions/<name>`), or change headers or the rate limit. |
| `core.py` ✏️ | 412 | **The heart.** Holds the `Store` class. It runs migrations, opens transactions, handles login and sessions, builds `/state`, and contains the big `_execute` dispatcher with every action's rules. It also has `seed()`. | …you change almost any business rule. |
| `access_policy.py` ✏️ | 37 | **Who can see which machines.** A user's scope is "whole buildings" plus "individual lines". Functions: `grants`, `allows`, `covers` (does the lead cover the technician?), `validate`, `write`. | …you change how building/line access works. |
| `validation.py` | 33 | **First-line input checks**: limits on size, nesting and text length, and duplicate JSON keys. Lists which fields must be text. | …you add a new text field name that must be a string. |
| `catalog.py` ✏️ | 47 | Validates **part and machine-type details**: SKU, cost (max 2 decimals), threshold ≤ target, compatible types. Also checks for unique SKU and unique type name. | …you add or change a part field. |
| `inventory_status.py` ✏️ | 39 | **Reservations and alerts.** `balance()` computes reserved, available and shortfall. `sync()` opens and closes alerts for Low stock, Reservation shortfall and Overdue maintenance. `snapshot()` lists alerts for a user. | …you change what counts as low stock or overdue, or add a new alert type. |
| `purchasing.py` ✏️ | 98 | **Reorders.** Request → (review) → Approved → Ordered → Partially received / Received, or Rejected / Cancelled. `planning()` computes the suggested order quantity. | …you change the purchasing workflow. |
| `records.py` | 70 | Read-only **audit log and stock ledger browsing**, with filters and paging. `redact()` hides password-like fields. | …you add a filter to the Audit log or Stock movements screens. |
| `reports.py` | 75 | **CSV exports**: maintenance, inventory, reorders, stock movements, audit. `cell()` blocks spreadsheet formula injection. | …you add a CSV column or a new report. |
| `backup.py` 🔧 | 87 | Makes a **verified copy** of the database. Clears sessions in the copy, never overwrites, and runs integrity checks. CLI: `python backup.py create --db machinecare.db --out backups` and `python backup.py verify <file>`. | Rarely. |
| `worker.py` 🔧 | 199 | **Optional background service**: re-checks alerts regularly, makes scheduled backups and can send email over TLS SMTP. Email is off unless the config enables it **and** you pass `--allow-email`. | …you turn on scheduled jobs or email. |
| `worker.example.json` 🔧 | 15 | Example worker config. It holds no secrets: the SMTP password comes from an environment variable. | Copy it to `worker.local.json` (git-ignored) to use it. |
| `schema.sql` ✏️ | 16 | **The original tables** (version 1): users, access, sessions, buildings, lines, types, machines, parts, compatibility, requests, maintenance, ledger, notifications, audit. | Never edit for existing installs. Add a migration instead (Recipe 8.6). |
| `migrations/002…007_*.sql` ✏️ | — | **Ordered upgrades**:<br>002 line access<br>003 revision numbers<br>004 purchasing tables<br>005 alerts<br>006 worker job state and email outbox<br>007 part provenance (real reference vs demo values).<br>Each ends with `PRAGMA user_version=N`. | Add `008_…sql` for any new table or column. |
| `import_auto_dimm.py`, `import_aoi.py` 🔧 | 68/85 | One-off **data importers** for your DIMM and AOI part lists. They back up first, run in one transaction and are safe to re-run. | Copy one as a template for importing new machine families. |
| `reset_admin.py` 🔧 | 23 | **Emergency** local admin password reset (you type the new password). | Only if you're locked out. |
| `start_manager_demo.py` 🔧 | 45 | Copies the database to `.verification/manager-demo/`, then starts the API and web servers on the **copy**. | Rarely. |
| `.env.example` 📄 | 5 | Example only. `server.py` reads real environment variables, not this file. | — |
| `tests/` 🧪 | ~1,300 | `test_core.py` covers workflows and permissions. `test_hardening.py` covers HTTP/security and the worker. `test_auto_dimm_import.py` and `test_aoi_import.py` cover the importers. 140 tests in total. | Add a test whenever you change a rule. |

### `app/`: the Flutter frontend

| File | Lines | What it does |
|---|---|---|
| `pubspec.yaml` ✏️ | 16 | Project manifest: name, Dart SDK range and dependencies. The only package dependency is `http`. |
| `pubspec.lock` 🤖 | — | Exact resolved package versions. Updated by `flutter pub get`. |
| `analysis_options.yaml` | 33 | Lint rules used by `flutter analyze`. |
| `lib/main.dart` ✏️ | 57 | **App entry point.** `main()` → `MachineCareApp` (applies the theme) → `LoginPage`. The login form, error notice and forced password change. After login it opens `Workspace`. |
| `lib/api.dart` ✏️ | 32 | **The only network code.** Class `Api` with `call()`, `login()` and `action()`. Keeps the token **in memory only**. Turns HTTP errors into readable messages. |
| `lib/design.dart` ✏️ | 163 | **The design system.** Contains:<br>• `Palette` (every colour)<br>• `Tone`, `toneFor()` (which status gets which colour)<br>• `machineCareTheme()` (fonts, buttons, inputs, cards)<br>• reusable widgets `StatusPill`, `Fact`/`FactGrid`, `Notice`, `EmptyState`, `SectionLabel`, `CountBadge`, `StockBar`<br>• `confirmAction()` |
| `lib/workspace.dart` ✏️ | 898 | **Every screen after login.** See the map below. |
| `lib/file_export.dart`, `file_export_web.dart`, `file_export_stub.dart` | 18 | CSV download. On web it creates a Blob and clicks a hidden link. On other platforms it throws "not supported". `file_export.dart` picks the right one. |
| `test/*.dart` 🧪 | ~640 | Widget tests with a fake API (`FakeApi` in `reservations_alerts_test.dart`), no real server. `responsive_workspace_test.dart` opens every page for every role at 390, 768 and 1440 px and fails on any overflow. |
| `tool/visual_preview.dart` 🧪 | 21 | Read-only demo with built-in sample data (`PreviewApi`). Used by tests and for layout checks. **Never deploy this.** |
| `web/index.html`, `manifest.json`, icons 🤖 | — | The HTML shell Flutter loads into, plus the browser tab icon and title. Change the title or icon here. |
| `build/` 🤖 | — | Output of `flutter build web`. Git-ignored. |

#### Map of `workspace.dart`

The page list is at the top of `_WorkspaceState`. Each page is one method.

```
pages = ['Overview','Equipment','Inventory','Approvals','History','Management',
         'Notifications','Reorders','Audit log','Stock movements','Reports']
index:     0          1           2           3          4          5
           6               7          8            9                 10
```

| Page (index) | Method that draws it | Helpers it uses |
|---|---|---|
| Overview (0) | `overview()` | `metric()`, `panel()`, `StockBar` |
| Equipment (1) | `equipment()` | `equipmentFilter()`, `machineDetails()`, `request()` |
| Inventory (2) | `inventory()` | `partCard()`, `stockStat()`, `editPart()` → `PartEditor`, `requestReorder()` → `ReorderRequestEditor` |
| Approvals (3) | `approvals()` | `requestCard()`, `review()`, `confirmComplete()` |
| History (4) | `history()` | `labelled()`, `Fact` |
| Management (5) | `administration()` | `editMachine()`, `createUser()`/`editUser()` → `AccountEditor`, `SystemStatus` |
| Notifications (6) | `notifications()` | `alertsPanel()`, `acknowledgeAlert()` |
| Reorders (7) | `reorders()` | `reviewReorder()`, `receiveReorder()` |
| Audit log (8) | `auditLog()` | `RecordBrowser(audit: true)` |
| Stock movements (9) | `stockMovements()` | `RecordBrowser(audit: false)` |
| Reports (10) | `reportsPage()` | `maintenancePlan()`, `ReportExporter` |

Shared machinery in `_WorkspaceState`:

- `state`: the last `/state` JSON. Every page reads from it with `rows(state, 'parts')` and similar.
- `refresh()` re-downloads `/state`. `act(name, data)` sends one action, then refreshes and shows a snackbar.
- `form(title, action, specs, extra:, intro:)` builds a dialog from a short spec list. `['quantity','Quantity','int','1']` means key, label, type, default. The types are `int`, `decimal`, `optional` and `text`.
- `panel(title, children)` is the white card used on every page.
- `build()` draws the scaffold, the grouped side menu (`navGroups`), badges (`badgeFor`), the user card and the page body. `visiblePage(i)` hides pages 5, 7, 8 and 9 from Technicians.

Separate dialog classes at the bottom of the file: `EntryDialog`, `SystemStatus`, `AccountEditor`, `PartEditor`, `ReorderRequestEditor`, `RecordBrowser`, `ReportExporter`.

### `docs/`

| File | Status |
|---|---|
| `CODEBASE_GUIDE.md` | This file. |
| `FEATURE_INVENTORY.md`, `SECURITY_REVIEW.md`, `BACKGROUND_SERVICES.md`, `PRODUCTION_READINESS.md` | **Current** references. |
| `MANAGER_DEMO.md`, `manager-presentation-2026-10-19/` | Presentation material. `final/` is the latest deck. `build_final_deck.js` regenerates it. |
| `ui-refresh-2026-10-19/` | Before/after screenshots of the UI refresh. |
| `SCOPE.md`, `ARCHITECTURE.md`, `PROPOSAL.md`, `VERIFICATION.md` | Older proposal text. Keep for history, **not** current authority. |
| `build_manager_deck.py/.ps1`, `build_graphical_deck.py` | Older deck generators. |
| `BANDIT_REPORT.json`, `DEPENDENCY_AUDIT.json`, `test-output.txt` | Saved scan and test outputs. |

---

## Part 5. The data model (database tables)

```
buildings 1─* lines 1─* machines *─1 types *─* parts   (through compatibility)
                              │                    │
                              ├── requests ────────┤   (machine + part + quantity + state)
                              └── maintenance ─────┘   (history: one row per completed request)
parts 1─* ledger              (every stock change: +receipt, −completion, ±adjustment)
parts 1─* reorders 1─* reorder_deliveries
users ─ access (building grants), line_access (line grants), sessions, notifications, audit
alerts ─ alert_acknowledgements
part_provenance (1 per imported part: real manufacturer/model vs demo values)
job_state, email_outbox (worker)
```

The important columns and rules:

- **parts.stock** is the *physical* count. **Reserved** is not stored. It is calculated live as the sum of quantities on `Approved` requests (`inventory_status.balance`). Available = max(0, stock − reserved).
- **requests.state**: Pending → Approved/Rejected → Completed/Cancelled. Only Approved reserves stock. Only Completed deducts it.
- **maintenance** copies `unit_cost` and `location_snapshot` at completion, so history never changes if a price or machine location changes later.
- **ledger** is append-only. Stock is never edited directly: every change is a ledger row plus an update to `parts.stock` in the same transaction.
- **operation_key** columns are unique. If the same button press arrives twice (double-click, retry), the second one is rejected, which prevents double counting.
- **revision** columns (parts, types, reorders) catch two people editing the same thing at once ("changed in another session").
- **users.version** increases on password, role or disable changes, which instantly invalidates old sessions.
- `PRAGMA user_version` is the schema version (currently **7**).

---

## Part 6. Backend concepts you must know

1. **One action = one transaction.** `with self.tx() as db:` opens `BEGIN IMMEDIATE`. If any line raises an error, everything rolls back. Never commit halfway.
2. **Errors are messages.** `raise Error('Text the user sees.', 403)` becomes HTTP 403 with `{"error": "Text the user sees."}`. The Flutter app shows it as-is. To change an error message, find its text in `core.py` or `purchasing.py`.
3. **Permission checks come first.**
   - `self.admin(u)` means Administrator only.
   - `u['role'] in ('Lead','Administrator')` means managers.
   - `self.machine(db, u, id)` means the user must have access to that machine's building or line.

   Hiding a button in Flutter is **not** security. The backend check is.
4. **Audit everything.** `self.audit(db, uid, 'action_name', {...details})` records who did what. Password-like keys are redacted automatically.
5. **Notifications** are just rows in `notifications`, and the user sees them on the Notifications page.
6. **Time** is always UTC ISO strings (`now()`).
7. **Passwords**: PBKDF2-SHA256 with 600,000 rounds and a random salt, 12–1,024 characters. Tokens are random; only their SHA-256 hash is stored. Sessions expire after **8 hours** (`time.time()+8*3600` in `login`).

## Part 7. Frontend concepts you must know

1. **Everything is a widget.** A screen is a tree of widgets such as `Column`, `Row`, `Card`, `Text` and `FilledButton`. To move something, move it in the tree.
2. **`setState(() { ... })`** changes a variable and redraws. Example: `setState(() => page = 2)` switches to Inventory.
3. **Data comes from `state`.** Pages never fetch on their own. They read the one `/state` snapshot, so `refresh()` updates everything at once.
4. **Responsive rules:**
   - Under 900 px wide, the side menu becomes a drawer (hamburger button).
   - Under 600 px, `compact` is true, so padding shrinks and facts get narrower.
   - Use `Wrap` instead of `Row` when items might not fit. `Row` + long text = overflow error.
5. **Style lives in `design.dart`.** Use `Palette.*` colours and the shared widgets so every screen stays consistent.
6. **Dialogs own their text controllers** and dispose them when they close. That is the "controller lifecycle" rule in `AGENTS.md`. Follow how `EntryDialog` does it.

---

## Part 8. Recipes: how to change things

Always:

1. Make the change.
2. Run the tests (Part 9).
3. Try it on a **copy** of the database.
4. Commit.

### 8.1 Change wording on a screen
- Search for the exact text in `app/lib/` (VS Code: Ctrl+Shift+F) and edit the string.
- If a test fails because it searched for the old text, update that test's `find.text('...')`.

### 8.2 Change colours, fonts or spacing
- Colours: edit `Palette` in `design.dart`. For example, `brand` is the teal used everywhere.
- Which status gets which colour: edit `toneFor()`.
- Font sizes: edit the `TextTheme` in `machineCareTheme()`.
- Card corners and borders: edit `cardTheme`.

### 8.3 Change a business number
| Want to change | Where |
|---|---|
| Session length (8 h) | `core.py` → `login` → `8*3600` |
| Minimum password length (12) | `core.py` → `password_hash` → `12<=len(password)` (also the UI hint text and tests) |
| Login rate limit (15 per 5 min) | `server.py` → `len(q)>=15` and `300` |
| "Due soon" window on Reports (30 days) | `workspace.dart` → `maintenancePlan()` → `Duration(days: 30)` |
| Low-stock rule (available ≤ threshold) | `inventory_status.py` → `sync()` and `workspace.dart` (`isLow`, overview `low`) |
| CSV row limit (10,000) | `reports.py` → `MAX_ROWS` |

### 8.4 Add a new field to parts (example: "location note")
1. **Database**: create `backend/migrations/008_part_location_note.sql`:
   ```sql
   BEGIN IMMEDIATE;
   ALTER TABLE parts ADD COLUMN location_note TEXT NOT NULL DEFAULT '';
   PRAGMA user_version=8;
   COMMIT;
   ```
2. **Run the migration**: in `core.py` → `Store.__init__`, change `if version>7` to `>8` and add:
   ```python
   if version<8:
       db.executescript((Path(__file__).parent/'migrations'/'008_part_location_note.sql').read_text())
   ```
   Also allow version 8 in `backup.py` → `verify` (`1 <= version <= 8`).
3. **Validation**: in `catalog.py` → `part_details`, add `'location_note': text(data,'location_note',True)`.
4. **Save it**: in `core.py`, add `'location_note'` to the `columns` tuple in the `part`/`edit_part` block, and to the INSERT and UPDATE column lists.
5. **Send it**: `public_part` already returns every column of `parts`, so `/state` includes it automatically.
6. **Edit it**: in `workspace.dart` → `_PartEditorState.labels`, add `'location_note': 'Location note (optional)'`.
7. **Show it**: in `partCard()`, add `Fact('Location note', '${p['location_note']}', width: factWidth)` to the `FactGrid`.
8. **Text field list**: add `'location_note'` to `TEXT_FIELDS` in `validation.py`.
9. **Test**: add a test to `backend/tests/test_core.py` that creates and edits a part with the field.

That is the full stack: database → validation → rule → JSON → UI → test.

### 8.5 Add a brand-new action (example: "mark machine inspected")
1. In `core.py` → `_execute`, add a block before the final fallthrough:
   ```python
   if action=='inspect':
       m=self.machine(db,u,integer(d,'machine_id'))          # scope check
       self.audit(db,uid,'inspect',{'machine_id':m['id'],'note':d.get('note','')})
       return {'message':'Inspection recorded.'}
   ```
2. In Flutter, add a button somewhere that calls `act('inspect', {'machine_id': m['id'], 'note': '...'})`, or uses `form('Record inspection', 'inspect', [['note','Note','optional']], extra: {'machine_id': m['id']})`.
3. Add `'note'` to `TEXT_FIELDS` in `validation.py` if it is new.
4. Add a backend test for allowed and denied roles.

### 8.6 Add a new database table
Same as 8.4: write a numbered migration, register it in `Store.__init__`, bump the max version in `__init__` and `backup.verify`, and add the table to `required` in `backup.verify`. **Never** edit `schema.sql` for existing installs.

### 8.7 Change who can do something
- Find the action's block in `core.py` (or `purchasing.py` for reorders) and change the role check.
- Then mirror it in Flutter so the button only shows for those roles: `purchasingAllowed` (Lead/Admin) or `admin` (Admin only).
- Update the permission table in `INSTALL.md` and `AGENTS.md`, and the role tests in `test_core.py` and `reservations_alerts_test.dart`.

### 8.8 Add a new page to the menu
1. In `workspace.dart`, add a name to `pages` and an icon to `icons` (same position).
2. Add the method name to the page list in `build()`: `[overview, equipment, …][page]()`.
3. Add its index to a group in `navGroups`. If only managers should see it, add it to the list in `visiblePage`.
4. Write the method, e.g. `Widget myPage() => panel('Title', [...]);`.
5. If it should be tested at all widths, add the page name to the list in `responsive_workspace_test.dart`.

### 8.9 Add a new alert type
In `inventory_status.sync()`, add an entry to `conditions[...]` with a unique key, kind, part and machine. It opens and closes automatically: it opens when the condition first appears and resolves when it disappears.

### 8.10 Add a column to a CSV report
In `reports.py`, add the column name to the right `fields=[...]` list. If it is a computed value, set `row['your_col']=...` in the loop.

### 8.11 Import a new machine family's parts
Copy `backend/import_aoi.py`. Change the `PARTS` list and the machine type name, and keep the backup + single transaction + skip-if-imported pattern. Copy `tests/test_aoi_import.py` too.

### 8.12 Change the app title or tab icon
`app/web/index.html` (`<title>`), `app/web/manifest.json`, the icons in `app/web/icons/`, and `title:` in `main.dart`.

---

## Part 9. Testing and working safely

```powershell
# from project root
python -m unittest discover -s backend/tests -v        # 140 backend tests (~2–6 min)
python -m unittest backend.tests.test_core.WorkflowTests.test_early_approval_consumes_only_at_completion   # just one
# from app/
flutter analyze                                        # static checks: must say "No issues found"
flutter test                                           # 45 widget tests
flutter test test/responsive_workspace_test.dart       # just one file
flutter build web --release --dart-define=API_URL=http://127.0.0.1:8000   # production web build
```

How the tests are built:

- **Backend tests** create a temporary database (`tempfile.TemporaryDirectory()`), seed it and create five users in `setUp`. Each test calls `self.act('lead','review', request_id=…, …)` and checks the result or `assertRaises(Error)`. Copy an existing test to write a new one.
- **Flutter tests** use `FakeApi`, which returns a fixed `/state`. They pump `Workspace(api: FakeApi(role: 'Lead'))`, tap with `find.text('Inventory')` and assert with `expect(find.text('Add part'), findsOneWidget)`.

Working safely with data:

- Experiment on a copy: `python backend/backup.py create --db backend/machinecare.db --out backend/backups`, then run `python server.py run --db backups/<that file>`.
- Before upgrading the real database, stop the server and make a verified backup.
- Recovering always uses a **new filename** (see `BACKUP_RECOVERY.md`).

---

## Part 10. Rebuild it from scratch: the order to do it in

If you deleted everything and started over, this is the order that reproduces this app. Each step is small and testable.

1. **Database schema**: write `schema.sql` (Part 5 tables). Make `Store.__init__` run it and set `user_version`.
2. **Transaction helper**: `Store.tx()` with `BEGIN IMMEDIATE`, commit or rollback.
3. **Accounts**:
   - `password_hash` / `password_ok`
   - `bootstrap` (first admin)
   - `login` (token + session row)
   - `user()` (token → user)
   - the `server.py init` command.
4. **HTTP server**: `server.py` with `/login`, `/state` and `/actions/<name>`, the JSON error format, and the origin check.
5. **Structure**: buildings, lines, types and machines actions (admin), plus `state()` returning them. Then `access_policy.py` scoping.
6. **Parts and stock**: the `part` action with an opening-balance ledger row, plus `receipt` and `adjust` with ledger rows and the stock ≥ 0 rule.
7. **Maintenance**: `request` (compatibility, availability, early rule) → `review` → `complete` (deduct, maintenance snapshot, ledger) → `cancel`.
8. **Reservations and alerts**: `inventory_status.balance` and `sync`.
9. **Purchasing**: the `reorders` tables and the `purchasing.py` state machine.
10. **Records and exports**: `records.py` and `reports.py`.
11. **Flutter shell**: `api.dart` → `main.dart` login → `Workspace` with `/state` and one page.
12. **Pages one by one**: Overview, Equipment, Inventory, Approvals, History, Management, Notifications, Reorders, Audit, Stock, Reports.
13. **Design system**: `design.dart`.
14. **Hardening**: `validation.py`, security headers, rate limit, auth audit events.
15. **Operations**: `backup.py`, `worker.py`, importers.

Write tests at every step. The existing tests are a ready-made checklist of what each step must do.

---

## Part 11. Practice exercises (do these on a database copy)

1. Change the overview headline "Keep production moving." to your own words. Run `flutter test`.
2. Change the brand colour in `Palette.brand` and rebuild. Watch it change everywhere.
3. Change the session length to 4 hours and find which test, if any, mentions 8 hours.
4. Add a CSV column `bin` to the maintenance report (hint: join `parts` in the query).
5. Follow Recipe 8.4 completely with "location note". This one exercise touches every layer, so once it works, you know the whole stack.
6. Write a backend test proving a Technician cannot call `adjust`.

When all six work, you can confidently change anything in MachineCare.
