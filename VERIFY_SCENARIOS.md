# Local verification scenarios

Use a disposable copy of your database. Do not record fictional maintenance or receipts against real inventory. For the numeric examples, use a test part with stock 12, threshold 5, target 20, no active reorders or maintenance requests and no recent replacement on the selected machines.

## Lead reorder rule

| Check | Steps | Expected |
|---|---|---|
| Lead bypass | As Lead, request 10 units with a reason. | Approved immediately; bypass explanation shown. No review required and stock unchanged. |
| Ordering | As Administrator, open that order and Mark ordered with a PO reference. | Ordered; physical stock unchanged. Lead cannot perform ordering/receiving. |
| Partial delivery | Receive 4 with SLIP-A, then 6 with SLIP-B. | Partially received -> Received. Physical stock increases by exactly 10. |
| Duplicate/over-receipt | Before the final receipt, try the same reference in lowercase; try more than the remaining amount. | Both fail without adding stock or delivery rows. |
| Administrator request | Submit as Administrator. Try to review it using the same account, then another Administrator. | Own review blocked; another Administrator can approve/reject. |
| Existing Lead request | On a disposable pre-update database, leave a Lead reorder Requested, then install/restart. | It becomes Approved once with upgrade explanation; other existing decisions and physical stock stay unchanged. |

## Stock reservations

| Check | Steps | Expected |
|---|---|---|
| Reserve | Request normal maintenance for 7 units. | Physical 12, reserved 7, available 5; request Approved. Suggested reorder quantity 15 with no active reorders. |
| Competing work | Another technician tries to request 6 units from the same SKU. | Insufficient available stock; no new reservation. |
| Cancel | Cancel the 7-unit request. | Physical 12, reserved 0, available 12. |
| Complete | Request 7 again and record physical completion. | Physical 5, reserved 0, available 5; one history record and deduction. Duplicate completion blocked. |
| Pending early work | After a recent replacement, submit an early request with explanation. | Pending; no reservation. When approved by assigned Lead, quantity becomes reserved. |
| Approval recheck | While early work waits, reserve the remaining stock on another eligible machine. Then approve the early request. | Approval fails; request stays Pending. Release reservations/receive stock, refresh and approve again. |
| Stock adjustment | With 10 units reserved out of 12, try reducing physical stock by 3, then by 2. | -3 blocked; -2 allowed, leaving physical/reserved 10 and available 0. |
| Receipt | With reservations in place, receive new stock through a placed reorder. | Physical and available increase by delivered quantity; reservations unchanged. |
| Concurrent approvals | Two Lead sessions approve different Pending requests that compete for the final available unit. | Only one succeeds. |
| Completion/cancel race | Two sessions try completion and cancellation of the same approved request. | Exactly one transition succeeds; reservation released once; stock deducted only if completion wins. |
| Failed completion | Create competing normal requests for the same machine/part; complete the first, then try the second. | Second is blocked by the new early interval; its reservation remains until cancellation. |

## Persistent alerts

| Check | Steps | Expected |
|---|---|---|
| Low available | Reserve enough stock to reach the threshold. Open Notifications. | One active Low stock episode for that SKU. |
| Deduplication | Refresh several times. | Same alert ID/episode; no duplicate active alert. |
| Acknowledge | Acknowledge as Technician, then inspect as Lead. | Technician sees Seen; condition still Active; Lead still has their own acknowledgement button. |
| Resolve | Cancel work or receive enough stock to raise available above the threshold. | Alert moves to Resolved; visible in Resolved/All. |
| Recurrence | Reserve/consume again until availability is low. | New active episode, unacknowledged even if the old one was seen. |
| Overdue | Use a disposable test record whose last replacement is older than its configured interval; refresh. | One Overdue maintenance alert for that machine/part. Unknown dates never automatically count as overdue. |
| Fix overdue | Record a new physical replacement. | Overdue alert resolves; maintenance history updates. |
| Permission | Restrict a technician to one line; create overdue work on a different line. | Its machine alert is absent for that technician; direct acknowledgement is rejected. Shared low-stock alerts remain visible. |
| Interval/retirement | Increase the interval beyond elapsed time, or retire an overdue machine. | Its overdue condition resolves. Reverting interval can create a new episode. |
| Persistence | Acknowledge an alert, leave work approved, restart both services. | Reservations, acknowledgement and alert history remain. |
| Idle timing | Leave the app idle as a due date passes, then refresh. | The condition is detected at refresh; no unattended email is expected. |
| Legacy shortage | In a disposable older database with approved quantities greater than physical stock, upgrade. | Work retained, available zero, shortfall shown. Receive stock/cancel work to clear it. |

Run `flutter analyze` and `flutter test`. Also recheck account edits, line permissions, catalog edits, equipment filters and dialog cancellation/reopening. Send the exact terminal error and action/role if any check fails.
