# Update 6: Full Lead reorder access and record viewers

This cumulative update includes all earlier pilot updates: accounts, line access, catalog editing, filters/dialog fixes, purchasing, stock reservations and persistent alerts. Install it over your existing MachineCare project; this is an update package, not a standalone Flutter project.

## Install step by step

1. Stop Flutter with `q` and stop the backend with Ctrl+C.
2. Back up the complete project and `backend/machinecare.db` while stopped. Keep backup Dart files outside `app/lib`.
3. Copy every included file from this package's `backend` and `app` folders into the matching folders under `F:\work\machinecare_flutter`, replacing matching files. Include the new `backend/records.py`, all other Python modules and all migrations. Keep your existing database, server.py, main.dart, api.dart, pubspec.yaml and login test.
4. Run the checks:

```powershell
cd F:\work\machinecare_flutter
python -m unittest discover -s backend/tests -v
cd app
flutter analyze
flutter test
```

If C: is still short of temporary space, run this in the Flutter terminal first:

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

This update keeps schema version 5. Older databases upgrade automatically using included migrations. Existing stock, accounts, reservations, deliveries and history are retained. Upgrades from versions below 5 also apply the earlier Lead-request approval policy. Do not run init or seed and do not delete the database.

6. Start Flutter in another terminal:

```powershell
cd F:\work\machinecare_flutter\app
flutter run -d chrome --web-hostname localhost --web-port 18080 --dart-define=API_URL=http://127.0.0.1:8000
```

## Lead reorder permissions

| Action | Lead | Administrator | Technician |
|---|---|---|---|
| Request reorder | Immediately Approved | Requested, needs another manager's review | No |
| Review another request | Yes | Yes | No |
| Review own Requested order | No | No | No |
| Record placed order/PO | Yes | Yes | No |
| Record partial/final physical delivery | Yes | Yes | No |
| Cancel any active remaining balance | Yes | Yes | No |
| View all facility purchasing records | Yes | Yes | No |

Lead requests require no separate approval. Administrator requests can now be reviewed by another Lead or Administrator. Lead/Administrator can act on orders submitted by other employees; purchasing is facility-wide. Machine building/line permissions still govern maintenance work.

The actual signed-in user's identity is recorded for ordering, review, receiving and cancellation. Reorder notifications now reach active Leads and Administrators. Closed Received/Rejected/Cancelled orders cannot be received or cancelled again. Duplicate reference, duplicate-operation, remaining-quantity and stale-revision checks remain enforced.

Supplier orders and supplier cancellations still happen through your purchasing process. Mark ordered records a placed order; it does not send an order. Receive delivery records physical arrivals. For purchased orders, use Reorders -> Receive delivery, rather than the generic Inventory receipt action, to keep ordered balances correct. The generic receipt action and stock adjustments remain Administrator-only because they are separate inventory operations.

## Stock movements

Lead or Administrator -> Stock movements:

- Inspect opening balances, purchased deliveries, unlinked receipts, adjustments and completed replacement deductions.
- Each record shows the current part name/SKU, signed quantity, reason, authenticated actor, time and balance after the movement.
- Balance after is calculated from the complete ledger for that SKU before filtering. An Out-only filter does not recalculate balances using only deductions.
- Reservations change available quantities, not physical stock, so they appear in Inventory/Approvals rather than as movement rows.
- Filters: search part/SKU/reason/actor, select a part, In/Out/All and inclusive UTC date range. Click Apply / refresh records. Timestamps display in the browser's local time; date filters use UTC dates.
- Load more fetches older rows in descending ID order, 50 per page. New arrivals do not shift already loaded pages. Apply / refresh records returns to the newest page. Changing filters disables Load more until applied, preventing mixed result sets.
- Names/SKUs and actor usernames shown beside historical records come from the current catalog/account. Movement quantity, reason and timestamp remain the recorded values.
- Balance after represents recorded ledger movements. Direct database edits or pre-existing unrecorded changes can make it differ from physical stock; the viewer does not invent missing movements or repair inventory automatically.

## Audit log

Administrator -> Audit log:

- Browse recorded account/scope changes, catalog edits, maintenance actions and purchasing actions.
- Search action or actor; optionally enter an exact action such as `reorder_receive`, `edit_part`, `edit_user`, `complete` or `reorder_cancel`; filter inclusive UTC dates.
- Expand a record to inspect its recorded detail, including before/after metadata where those actions already capture it.
- Credential-related fields are recursively redacted before delivery to the client. Unstructured legacy details are withheld instead of displayed as arbitrary text.
- This is a read-only viewer of existing audit records. It does not claim to log every event: login attempts, every password change, alert acknowledgement and background condition evaluations are not all captured by the existing audit writers. Database-local manual changes are not automatically audited. This pilot is not a tamper-proof audit system.
- Leads and Technicians are denied audit browsing by the server, even if they call the API directly. Stock movement history is available to Leads/Administrators and is facility-wide.

## Actual verification

96 backend tests passed in 71.853 seconds, including 14 new checks for Lead ordering/receiving/cancellation, role enforcement, concurrent deliveries, record filtering/pagination, balance calculations, redaction, restart persistence and a real HTTP flow. Python syntax compilation passed. See TEST_RESULTS.txt.

Flutter is not installed in the delivery environment. Supplied widget tests and Flutter analysis are NOT executed here. Run them locally and follow VERIFY_SCENARIOS.md before relying on this version.

## Rollback

Stop both services and restore the complete previous code with its matching stopped-database backup. Restoring a backup loses changes recorded since it was taken. Never overwrite a live database or downgrade just the code.
