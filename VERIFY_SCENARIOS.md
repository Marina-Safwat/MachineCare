# Check the purchasing update

Use a disposable copy of your database for these scenarios. Purchases and deliveries really change stock; do not enter fictional deliveries in your live inventory. Record starting stock S for a test part. Refresh after switching accounts or browser sessions.

| Scenario | Steps | Expected result |
|---|---|---|
| Request and approval | As Lead, request 10 units with a reason. As Administrator, approve with a comment. | Requested -> Approved. Requester identified correctly. Stock stays S. |
| Self-review | Submit as Administrator, reopen it using that account. | Approve/reject buttons absent. Another Administrator must review. |
| Record placed order | After approval, Mark ordered with PO-DEMO-1. | Ordered, PO reference displayed; stock still S. No supplier email/order is sent. |
| First partial delivery | Receive 4 with reference SLIP-1-PART. | Stock S+4; received 4, remaining 6; Partially received; one delivery row. |
| Duplicate delivery | Try another 1 using slip-1-part on the same order. | Error, stock still S+4; no extra receipt. |
| Too many units | Try 7 using a new reference. | Error because only 6 remain; stock and delivery history unchanged. |
| Finish delivery | Receive 6 with SLIP-2-PART. | Stock S+10; Received; remaining 0; two delivery rows. |
| Closed order | View the completed order using All or Received filter. | Further receiving and cancellation unavailable. |
| Cancel remainder | Create/approve/order a second 10-unit request; receive 3; cancel with a reason. | Cancelled, received 3 retained; cancelled remainder 7; stock keeps the 3 delivered. |
| Rejection | Reject a new request with a comment. | Rejected; no ordering/receiving; stock unchanged. |
| Validation | Submit blank reason, zero, negative or fractional quantity; omit a PO or delivery reference. | Submission blocked; no stock or order mutation from invalid input. |
| Permissions | Sign in as Technician; as Lead inspect an Ordered request. | Technician has no Reorders access. Lead cannot approve, order or receive. |
| Planning | For stock 12, target 20 and no active orders, request 5. Approve/order it, then receive 2. | Suggestion initially 8; pending request makes it 3; after receipt stock 14/outstanding 3 still suggests 3. |
| Catalog snapshots | Request an order, then edit the part's supplier/cost in Inventory. | Order continues to show its original supplier/cost estimate; later requests use new details. |
| Notifications | Submit as Lead; inspect Administrator notifications. Review/receive, then inspect Lead notifications. | Relevant purchasing notifications appear. No automated email is expected. |
| Stale screen | Open the same Requested order in two Administrator sessions; review in one, then try in the other. | Second stale review rejected; first decision retained. Refresh shows current state. |
| Concurrent final receipt | Two Administrator sessions try to receive the entire remaining balance with different references. | Only one commits; stock increases by the remaining balance once. |
| Dialog lifecycle | Open Request reorder, edit, cancel and reopen; repeat Receive delivery cancellation. | No disposed-controller or _dependents assertion; fresh fields work. |
| Persistence | Restart backend and Flutter after a partial receipt. | Accounts, previous inventory/history, order quantities and delivery rows remain. |
| Regression | Verify equipment filters, replacement completion/history, account editing, line access and catalog editing. | Existing flows still work and scope restrictions remain enforced. |

Run `flutter analyze` and `flutter test` as well. Keep the terminal output if any scenario fails, and report the action, role and exact error. Backend tests passed here; the Flutter scenarios require your local verification.
