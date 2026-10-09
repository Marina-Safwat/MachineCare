# Update 4: Reorder approvals and partial deliveries

This cumulative update includes account editing, line access, catalog editing, equipment filters and the dialog fix. Install over your existing MachineCare pilot; this ZIP is an update, not a standalone project.

## Install step by step

1. Stop Flutter with `q` and the backend with Ctrl+C.
2. Back up your project and `backend/machinecare.db` while both are stopped. Keep backup Dart files outside `app/lib`.
3. Extract the ZIP. Copy the contents of its `backend` and `app` folders into the matching folders in `F:\work\machinecare_flutter`, replacing matching files. Copy ALL included files, particularly the new `backend/purchasing.py` and `backend/migrations/004_purchasing.sql`. Keep your existing `server.py`, `main.dart`, `api.dart`, `pubspec.yaml`, login test and database.
4. Run checks:

```powershell
cd F:\work\machinecare_flutter
python -m unittest discover -s backend/tests -v
cd app
flutter analyze
flutter test
```

If C: is still short of temporary space, set these in the Flutter terminal before testing:

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

Startup automatically adds purchasing tables and upgrades existing schemas to version 4. Existing accounts, stock, equipment and history are retained. Do not run `init` or `seed` and do not delete the database.

6. Start Flutter in a separate terminal:

```powershell
cd F:\work\machinecare_flutter\app
flutter run -d chrome --web-hostname localhost --web-port 18080 --dart-define=API_URL=http://127.0.0.1:8000
```

## Use the new features

Lead or Administrator: Inventory -> Request reorder, or Reorders -> Request reorder. Enter quantity and reason. A different Administrator approves or rejects it with a comment. For a simple demo, submit as a Lead, then approve as your Administrator.

Administrator: place the actual supplier order using your purchasing process, then click Mark ordered and enter its PO/reference. Click Receive delivery for each physical arrival. Enter the arrived quantity and a unique delivery reference, for example `SLIP-100-SEAL-1`. The order moves to Partially received, then Received when its full quantity arrives. Expand Delivery history to see each receipt.

| Action | Allowed role | Stock effect |
|---|---|---|
| Request | Lead or Administrator | None |
| Approve/reject | Another Administrator | None |
| Mark ordered | Administrator | None |
| Receive delivery | Administrator | Adds only received quantity |
| Cancel remaining | Administrator; Lead can cancel their own Requested/Approved request | Received stock retained |

Purchasing and inventory are facility-wide in this pilot. Machine building/line access still governs maintenance work; it does not restrict purchasing by building. Technicians cannot access purchasing actions or records.

## Rules and current limits

- Approval cannot be performed by the requester. If an Administrator submits a request, another Administrator must review it.
- Supplier, supplier part number and unit cost are captured at request time. Estimated value excludes freight/tax; it is not an invoice or paid amount.
- Stock, delivery, inventory ledger, order status, notification and audit changes commit together. Failed or duplicate receipts do not add stock.
- Each order/reference pair is unique without case sensitivity. Repeated operation keys are also blocked. Refresh after an uncertain network response to see whether it committed before resubmitting.
- Use Reorders -> Receive delivery for purchased orders. The existing Inventory -> Receive action is for unlinked receipts and does not update an order. Recording the same physical delivery through both paths can double-count stock; cross-path physical receipt matching is not implemented.
- Requested quantities count as pending planning. Approved/Ordered/Partially received balances count as outstanding. Suggested quantity is max(0, target - stock - outstanding - pending). These quantities do not reserve inventory or guarantee delivery.
- Approval, ordering and cancellation check record revisions to block stale edits. Refresh before retrying conflicts. Concurrent deliveries check the current remaining balance inside the transaction.
- Cancelling a partial order cancels only its remaining quantity; prior deliveries and stock remain. Arrange supplier cancellation separately for placed orders.
- Supplier ordering and email are manual. In-app purchasing notifications are provided; automatic email, supplier integration, reservations and scheduled alerts remain future work.

## Verification and rollback

66 backend tests passed in 45.070 seconds, including 15 new purchasing tests and a real HTTP end-to-end purchasing flow. See TEST_RESULTS.txt. Flutter is unavailable in the build environment, so supplied widget tests and Flutter analysis have NOT run here. Run the local checks and VERIFY_SCENARIOS.md before relying on the update.

To roll back, stop both services and restore the entire previous code plus its matching stopped-database backup together. A restored backup loses changes since the backup. Do not overwrite a live database or downgrade only the code.
