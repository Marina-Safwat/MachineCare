# Update 5: Lead reorder policy, reservations and persistent alerts

This is a cumulative update for your existing Flutter/Python MachineCare pilot. It includes the previous purchasing, catalog, account, line-access, filter and dialog updates. You can install it directly over the existing pilot without installing each earlier ZIP first.

## Install

1. Stop Flutter (`q`) and the backend (Ctrl+C).
2. Back up your complete project and `backend/machinecare.db` while stopped. Keep backups outside `app/lib`.
3. Copy every included file from this package's `backend` and `app` folders into the matching folders under `F:\work\machinecare_flutter`, replacing matching files. Include all migration files and the new `backend/inventory_status.py`. Keep your existing database, server.py, main.dart, api.dart, pubspec.yaml and login test.
4. Run the checks below. Backend tests use temporary test databases, not your live database.

```powershell
cd F:\work\machinecare_flutter
python -m unittest discover -s backend/tests -v
cd app
flutter analyze
flutter test
```

If temporary space on C: is low, run this in the Flutter terminal first:

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

Startup upgrades the database to schema version 5. It adds alert tables and approves existing Requested reorders whose requester currently has the Lead role. Those existing orders receive a policy-upgrade audit record and a new revision. Existing physical stock, accounts, maintenance history and deliveries are retained. Do not run init or seed; do not delete the database.

6. Restart Flutter in a second terminal:

```powershell
cd F:\work\machinecare_flutter\app
flutter run -d chrome --web-hostname localhost --web-port 18080 --dart-define=API_URL=http://127.0.0.1:8000
```

## Your updated reorder rule

Lead-submitted reorders are Approved immediately. No separate approval is needed. The authenticated Lead is recorded as the approval actor, with a bypass explanation and audit entry. Administrator-submitted reorders still start Requested and require another Administrator's review. Changing a user's role later does not retroactively change an order's recorded decision.

Administrators still place orders through the existing purchasing process, record Mark ordered and receive physical deliveries. Leads can cancel their own pre-order requests. Supplier ordering/email remains manual. Duplicate references, partial receiving and over-receipt protection remain in place.

## Reservations

- Inventory and equipment show physical stock, reserved quantity and available quantity.
- Every Approved maintenance request reserves its quantity. Available = max(0, physical - approved reservations).
- Normal maintenance requests are approved/reserved on submission. Early Pending requests reserve nothing until their Lead approves; approval checks current availability again.
- Completion deducts physical stock and releases that request's reservation together. Cancellation releases the reservation without changing physical stock. Rejected/Pending/Completed/Cancelled work reserves nothing.
- Reservations derive from persisted Approved requests, so there is no second balance table that can drift out of sync.
- Receipts increase availability; stock adjustments cannot reduce physical stock below reserved quantities. Cancel work before making a reduction that would consume its reservation.
- Existing Approved work is retained on upgrade. If earlier work already exceeds physical stock, available is zero and a Reservation shortfall alert appears. Receive stock or cancel unnecessary work. Nothing is silently deleted, cancelled or deducted during upgrade.
- Failed completion leaves the request and reservation intact; cancel it if it must be resubmitted for early review.
- Requests do not queue for insufficient stock. Request submission/approval must succeed with sufficient current availability.
- Reorder suggestion now uses available stock: max(0, target - available - outstanding approved/ordered balance - pending reorder requests). Reorders do not reserve stock; approved maintenance does.

## Persistent alerts

Open Notifications -> Persistent alerts. Filter Active, Unacknowledged, Resolved or All. Overview includes an active-alert count.

- Low stock: available quantity is at or below the threshold. Shared inventory alerts are visible to all signed-in staff.
- Reservation shortfall: legacy approved maintenance exceeds physical stock.
- Overdue maintenance: a known last replacement plus the part's current interval has elapsed. No history means the due date is unknown. Retired machines do not generate active overdue alerts.
- Machine alerts follow current building/line permissions, including acknowledgement authorization.
- Repeated checks update the same active alert instead of creating duplicates. When the condition clears, the episode is marked Resolved and retained. A recurrence creates a fresh unacknowledged episode.
- Acknowledge marks seen for your account only. It does not resolve the condition or hide it from other users.
- Conditions are evaluated on state refresh and successful backend transactions. There is no unattended scheduler, push service or automatic email. If the app is idle, a new time-based overdue alert appears at the next refresh/activity; opened time is detection time, not necessarily the instant the threshold was crossed.
- Catalog interval/threshold changes can resolve or reopen alerts based on the new settings. Alert history is retained; it is not an immutable snapshot of every intermediate message.

## Verification

82 backend tests passed in 67.437 seconds, including 16 new checks for Lead bypass, reservations, persistent alerts, migration and concurrency. Python syntax compilation passed. See TEST_RESULTS.txt for the actual backend run and VERIFY_SCENARIOS.md for manual checks. Flutter is not installed in the delivery environment, so Flutter analysis and supplied widget tests are NOT executed here. Run both locally before relying on the update.

## Rollback

Stop both services and restore the complete previous code with its matching stopped-database backup. Restoring that backup loses subsequent changes. Do not downgrade just the code or overwrite a live database.
