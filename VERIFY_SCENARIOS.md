# Verify the new role policy

Current results and remaining blockers are in PROJECT_STATUS.md. Additional checks: phone/tablet/desktop layouts, labeled machine selectors, failed-form value preservation, cancellation/adjustment/account confirmation, Administrator-only Background services, worker deduplication/retry/Uncertain handling, and schema-6 upgrade on a disposable copy. Run email tests with substitutes until actual sending is explicitly authorized. See docs/BACKGROUND_SERVICES.md and docs/SECURITY_REVIEW.md.

Use a disposable project/database copy for fictional work. Physical completion, receipts and adjustments change stock.

| Check | Steps | Expected |
|---|---|---|
| Your Administrator tools | Sign in as your Administrator and open Management. | Account and building/line tools available alongside equipment tools. |
| Lead management | Sign in as Lead; open Management. | Register/edit machines and add/rename machine types available. Account and building/line tools absent. |
| API boundary | As Lead, try user/edit_user/reset/disable/building/line actions directly. | Server rejects each with permission error; accounts/access/structure unchanged. |
| Lead catalog | As Lead, edit part name, price, supplier/interval/compatibility with reason; rename a machine type. | Saves allowed; stale revisions, duplicate SKUs/names and active-compatibility removal still blocked. |
| Lead inventory | As Lead, receive unlinked stock and make a justified adjustment. Try reducing below reserved quantity. | Valid actions recorded as Lead; consuming reserved stock rejected. For purchased orders use Reorders -> Receive delivery. |
| Machine scope | Give a Lead only one line; register/edit a machine there. Try moving it to another line and editing an outside machine into the assigned line. | Own-line operations succeed; both cross-scope attempts rejected. |
| Request visibility | Leave approved work on an accessible machine submitted by a technician assigned to a different Lead. | This Lead can see it and complete/cancel it. Outside machines remain hidden. |
| Lead completion | Technician submits normal work; Lead records physical completion. | One stock deduction/history record; actual Lead identified in history/ledger/audit. Request retains original technician; notification sent to requester. |
| Duplicate completion | Try completion again. | Rejected; no second deduction/history record. |
| Lead cancellation | Lead cancels another technician's Approved request. | Physical stock unchanged; reservation released; requester notified. |
| Technician ownership | A different Technician tries completing/cancelling another technician's work. | Denied. Own approved work still works. |
| Technician early work | Complete a part, then submit an early replacement as Technician with explanation. | Pending, no reservation; authorized scoped Lead can approve/reject with comment. |
| Lead early work | Submit early replacement as Lead, first without explanation, then with explanation. | Blank explanation blocked; valid explained request Approved with recorded manager confirmation. |
| Review scope | Attempt reviewing/completing/cancelling a request on an outside line via API. | Denied before stock/history mutation. |
| Full logs | Lead opens Audit log and Stock movements; exports both. | Read/export allowed; audit credential fields redacted. Technician still denied. |
| System records read-only | As Lead, inspect an account-change audit record. | Readable but no account-editing tools or permissions granted. |
| Lead orders | Lead requests, marks ordered, receives batches and cancels outstanding remainder. | All allowed; duplicates/over-deliveries/stale edits still blocked. |
| Regression | Check filters, account editing as Administrator, line access, alerts, reservations, CSV downloads and backup/recovery drill. | Prior features remain usable under the updated role table. |

Laptop verification on 2026-10-12: 123 backend tests and 33 Flutter widget tests passed; final `flutter analyze` found no issues. See PROJECT_STATUS.md for the F: temporary-storage workaround and actual results. The interactive scenarios above, actual Chrome downloads and a separate-database recovery drill still need manual checks. Report the exact error, signed-in role and action if a check fails.
