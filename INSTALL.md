# Update 3: Machine-type and part-detail editing

This is a cumulative update: it includes account editing, building/line access, equipment filters and the dialog controller fix.

## New actions

- Administrator -> Administration -> Machine types -> pencil: rename a type.
- Administrator -> Inventory -> Edit details: change a part's name, SKU, supplier, supplier part number, bin, cost, expected replacement interval, reorder threshold/target, supplier lead time and compatible machine types.
- Inventory -> Add part now uses labeled fields and compatibility checkboxes instead of typing type IDs.

Part edits require a reason and are recorded with before/after details in the audit database. This update does not add an audit-log viewer.

## Install

1. Stop Flutter with `q`; stop the backend with Ctrl+C.
2. Back up your code and backend/machinecare.db while the backend is stopped. Keep backups outside app/lib.
3. Copy this package's files to the matching folders under F:\work\machinecare_flutter:

| File | Purpose |
|---|---|
| backend/core.py | Updated domain actions and migration runner |
| backend/access_policy.py | Building/line permission rules |
| backend/catalog.py | New catalog validation module |
| backend/schema.sql | Baseline schema |
| backend/migrations/002_line_access.sql | Earlier additive line-access upgrade |
| backend/migrations/003_catalog_revision.sql | New catalog-version upgrade |
| backend/tests/test_core.py | Updated full backend suite |
| app/lib/workspace.dart | Both editors plus previous frontend updates |
| app/test/*.dart | Updated/new widget tests; keep your existing login test |

Copy every required backend file, including the migrations folder. Do not delete the database, reinitialize the administrator or reseed.

4. Run checks:

```powershell
cd F:\work\machinecare_flutter
python -m unittest discover -s backend/tests -v
cd app
flutter analyze
flutter test
```

If the C: drive is still short of space, set these in the Flutter terminal before testing/running:

```powershell
New-Item -ItemType Directory -Force -Path F:\FlutterTemp
$env:TEMP = 'F:\FlutterTemp'
$env:TMP = 'F:\FlutterTemp'
```

5. Restart the backend:

```powershell
cd F:\work\machinecare_flutter\backend
$env:MACHINECARE_ORIGIN = 'http://localhost:18080'
python server.py run
```

The backend upgrades schema version 1 or 2 to version 3 automatically, preserving existing accounts, line grants, equipment, stock and maintenance. Version 3 adds revision counters for machine types and parts; no inventory balances are modified.

6. Restart Flutter in another terminal:

```powershell
cd F:\work\machinecare_flutter\app
flutter run -d chrome --web-hostname localhost --web-port 18080 --dart-define=API_URL=http://127.0.0.1:8000
```

## Important rules

- Editing part metadata cannot set stock. Use Receive or Adjust for inventory quantities.
- SKU edits keep the same part ID, compatibility links, inventory and maintenance references. New/edit SKUs are trimmed and stored uppercase; duplicates are checked without case sensitivity.
- Machine-type names are unique without case sensitivity. Renaming preserves IDs and machine/part relationships.
- Unit cost is nonnegative and supports at most two decimal places. Target stock must be at least the reorder threshold. Expected interval must be positive.
- Every part must have at least one compatible machine type.
- Compatibility required by Pending or Approved requests cannot be removed. Finish or cancel those requests first. Completed history never blocks a compatibility update and is never deleted.
- Historical maintenance stores quantity, unit cost, replacement time, technician and location. Metadata edits do not rewrite these records. Part names shown beside old history are the current catalog names; historical machine-location labels remain the captured labels.
- Future completed work captures the price configured at completion, not necessarily at request submission. Existing completed costs do not change.
- Increasing expected life can make already-approved normal work early. The backend checks again at completion and may require cancellation/resubmission for lead approval. Reducing expected life does not auto-approve existing pending requests. Overdue metrics use the currently configured interval.
- One shared balance/bin per SKU remains the pilot inventory model. Changing the bin changes the catalog location label; no stock movement, receipt or physical relocation is automatically performed.
- Catalog edits include a revision number. If another admin saves first, stale saves are blocked instead of overwriting their changes. Close/reopen the editor to reload; note your intended changes before doing so.
- Permission checks remain server-side. Leads and technicians cannot edit catalog details even by calling the API directly.

## Actual verification

51 backend tests passed in 34.004 seconds on Python 3.12.14. This includes 37 existing tests and 14 new catalog tests. Python syntax compilation passed. Raw final output is TEST_RESULTS.txt.

New tests cover renamed type relationships/history, permission checks, duplicates, stale/conflicting metadata updates, stock/ledger/history preservation, future versus historical costs, active compatibility safeguards, shared stock after new compatibility, receipts during metadata edits, changed expected intervals, v2->v3 migration and repeated starts.

Flutter is not installed in the delivery environment. Supplied widget tests are NOT executed here. Run flutter analyze/flutter test and VERIFY_SCENARIOS.md locally. Backend coverage does not substitute for frontend verification or production security review.

## Rollback

Stop both services and restore the complete pre-update code and matching stopped-database backup together. Restoring only old code can remove line permission enforcement. Restoring a backup reverts changes recorded since the backup. Never overwrite a live database.

## Next pair

Reorder requests/approvals and partial deliveries, with atomic receiving and duplicate prevention.
