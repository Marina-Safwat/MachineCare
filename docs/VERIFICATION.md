# Actual verification results

Run in the delivery workspace on October 8, 2026 (UTC; evening October 7 in Tennessee).

- Runtime: Python 3.12.14.
- Command: `python3 -m unittest discover -s backend/tests -v`.
- Result: **16 tests passed**, 6.787 seconds in the final run.
- Python syntax compilation passed for core.py and server.py.
- Raw final test output: `test-output.txt`.

The tests use fresh temporary databases, never a production database. Coverage includes session expiration/logout, disabling, password reset/change and revocation, building/role permissions, incompatible parts, identity spoofing, exact machine/part dates, early approve/reject, prevention of self-approval, missing leads, duplicate submissions, duplicate receipt operations, atomic concurrent consumption of the last item, machine moves, competing normal requests, nonnegative adjustments, optional line descriptions, duplicate SKUs and a real HTTP technician→lead→completion flow.

An initial test incorrectly selected the second alphabetically sorted part rather than the part by ID. That test assertion was corrected to select by ID; the final full suite passed.

Flutter and Dart were not installed in this environment. **No Flutter compile, flutter analyze, widget tests, browser interaction tests, visual QA or Windows execution was performed.** The supplied frontend is editable source to verify locally. Setup-Flutter.ps1 was written but not run on Windows here.

Not tested/implemented: reservations, order receiving, notification retry/outbox, production migration/deployment, email provider, accessibility audit, security review, emergency overrides or correction/reversal workflows. See SCOPE.md.
