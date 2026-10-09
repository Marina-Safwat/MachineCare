# Check this update

Use a disposable database copy. Fictional deliveries and completed maintenance change real stock. For the numeric examples, use a part starting with physical stock 12, no existing reservations and no recent replacement on your test machine.

## Full Lead reorder process

| Check | Steps | Expected |
|---|---|---|
| Lead request | As Lead, request 10 units with a reason. | Approved immediately; stock still 12. |
| Lead ordering | Stay signed in as Lead; Mark ordered with PO-LEAD-1. | Ordered, Lead recorded as ordering actor; stock still 12. |
| Lead partial delivery | Receive 4 with SLIP-1. | Partially received, remaining 6, stock 16. Delivery history identifies the Lead. |
| Duplicate/over-receipt | Try slip-1 with a new operation, then try 7 with a different slip. | Both rejected; stock stays 16. |
| Lead final delivery | Receive 6 with SLIP-2. | Received, remaining 0, stock 22. |
| Lead review | Submit a new request as Administrator; review it as Lead with a comment. | Approved or Rejected; reviewer is the Lead. The submitting Administrator cannot self-review. |
| Lead cancellation | On another placed order, receive 3, then cancel the remainder as Lead. Also cancel another employee's unreceived active order. | Allowed; received stock/history retained. Outstanding remainder removed from planning. |
| Closed order | Try to receive/cancel Received, Rejected or Cancelled orders. | Buttons unavailable; direct API attempts rejected. |
| Technician restriction | Sign in as Technician. | No purchasing/stock movement/audit navigation; direct purchasing and record APIs denied. |
| Concurrent receipts | In Lead and Administrator sessions, both try to receive the entire remaining balance with distinct slips. | Only one succeeds; stock increases once. |

## Stock movement history

| Check | Steps | Expected |
|---|---|---|
| Actor/quantity | Open Stock movements after the two Lead deliveries above. | +4 and +6 rows show the Lead, references, times and balances after 16/22. |
| Maintenance deduction | Complete a normal replacement of 1 unit. | One -1 row, authenticated requester, balance after 21. Duplicate completion adds nothing. |
| Reservations | Approve/request normal maintenance but do not complete it. | Inventory reserved/available changes; no physical movement row appears until completion. Cancellation adds no movement. |
| Part/direction | Select the SKU, choose Out and Apply. | Only that SKU's deductions; balance after includes earlier receipts, not merely filtered deductions. |
| Search | Search a delivery reference or actor; Apply. Search a string with no matches. | Matching reasons/actors found; no-match message shown. |
| Date range | Choose From and To dates; Apply. Try From later than To. | Inclusive UTC-date filtering; reversed range rejected, existing rows preserved. |
| Clear filters | Apply several filters, then Clear filters. | Defaults restored; newest records shown. |
| Paging | With more than 50 matching rows, Load more. Add a new receipt in another session before the next page. | Older records appended without duplicates; newest arrival appears after Apply / refresh records. |
| Changed filters | With Load more visible, edit search/direction/date/part. | Load more disabled until Apply; result sets never mixed. |
| Rename/restart | Rename a catalog part, then restart the services. | Movement quantities/balances persist; names/SKUs show current catalog values. |

## Audit log

| Check | Steps | Expected |
|---|---|---|
| Administrator view | Open Audit log as Administrator; search Lead username or `reorder_receive`. Expand an entry. | Actual actor, time, action and recorded quantities/references shown. |
| Before/after | Edit a part with a reason; filter exact action `edit_part`, then expand. | Recorded reason and before/after detail visible; no stock deduction from metadata editing. |
| Account changes | Edit employee access; filter `edit_user`. | Recorded access changes visible to Administrator. |
| Privacy/permissions | As Lead/Technician, inspect navigation and attempt `audit_list` through the API. | Audit navigation absent; server returns permission error. No audit data returned. |
| Pagination | With over 50 records, Load more, then Apply / refresh records. | Older records append; refresh returns to newest page. |
| Read-only | Note stock and order status; browse/filter both viewers. | Browsing creates no ledger/audit entries and changes no stock, reservations or order states. Alert evaluation may still occur during backend activity. |

Also verify existing equipment filters, replacement completion/history, account/line access, catalog edits, reservations, persistent alerts and dialog cancel/reopen. Run `flutter analyze` and `flutter test`; record exact terminal errors and action/role if something fails.
