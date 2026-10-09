# Step 1: Edit existing employee accounts

Adds role, lead and building-access editing under Administration -> Accounts -> pencil icon.
This update includes the equipment filters and previous dialog controller fix.
No database schema change or reseeding is required. Existing passwords and maintenance history remain intact.
Line-level access remains a separate upcoming feature.

## Apply on Windows

1. Stop the Flutter process with `q`. Stop the Python backend with Ctrl+C.
2. Make backup copies of your current `backend/core.py` and `app/lib/workspace.dart` outside the `app/lib` folder. With the backend stopped, also copy `backend/machinecare.db` to a protected backup location.
3. Copy this package's `backend/core.py` over `F:\work\machinecare_flutter\backend\core.py`.
4. Copy this package's `app/lib/workspace.dart` over `F:\work\machinecare_flutter\app\lib\workspace.dart`.
5. Copy `backend/tests/test_core.py` into your backend/tests folder and the two new `app/test` files into your app/test folder. Keep your existing login test.
6. Run backend checks from `F:\work\machinecare_flutter`:

```powershell
python -m unittest discover -s backend/tests -v
```

7. From the app folder run `flutter analyze` and `flutter test`. If your C: disk is still short of space, use the same temporary-folder setup in that terminal:

```powershell
New-Item -ItemType Directory -Force -Path F:\FlutterTemp
$env:TEMP = 'F:\FlutterTemp'
$env:TMP = 'F:\FlutterTemp'
```

8. Restart the backend in its terminal:

```powershell
cd F:\work\machinecare_flutter\backend
$env:MACHINECARE_ORIGIN = 'http://localhost:18080'
python server.py run
```

9. Restart Flutter in the other terminal:

```powershell
cd F:\work\machinecare_flutter\app
flutter run -d chrome --web-hostname localhost --web-port 18080 --dart-define=API_URL=http://127.0.0.1:8000
```

## How to use

Sign in as Administrator -> Administration -> Accounts. Click the pencil beside an employee. Select role, choose an active assigned lead for Technician accounts, and check the permitted buildings. Click Save account.

A changed role/lead/access revokes that employee's sessions. They must sign in again. A no-change save does not revoke sessions. Only administrators can edit, and another administrator must edit your own role/access. Usernames and passwords are not changed by this editor.

Pending early requests are transferred when their technician gets a new lead, with in-app notifications to the new and old lead. Approved/completed records retain existing review information. A lead must cover all selected technician buildings. Leads with assigned technicians cannot be demoted or lose required building access until those technicians are reassigned. Pending work cannot be left without a lead or the technician's required access. Validation failures leave all records unchanged and keep entered selections in the dialog.

Access removal can make previously approved work inaccessible; restore the access or have an administrator cancel the obsolete request. This update does not add an approved-work reassignment workflow.

## Actual verification

23 Python backend tests passed in 11.079 seconds, including seven new account-edit tests. Test databases were temporary and separate. Python syntax compilation passed. See TEST_RESULTS.txt.
Flutter runtime is not available in the delivery environment. The two AccountEditor widget tests and previous lifecycle tests are supplied but not executed here; run them on your laptop before use. Existing frontend source still requires local analyze/runtime verification.

## Remaining sequence

1. Account editing: delivered in this update, local UI verification pending.
2. Line-level permissions.
3. Machine-type/part editing.
4. Reorder and partial-receipt workflow.
5. Reservations and persistent low-stock alerts.
6. Email/background jobs.
7. Emergency replacement and corrections.
8. Reporting and exports.
9. Production deployment, backup and security review.
