# Two-feature acceptance scenarios

Use sample equipment and temporary accounts. Record your starting stock and history before editing. Perform catalog edits as Administrator.

## Machine-type editing

| Scenario | Action | Expected |
|---|---|---|
| Rename a used type | Rename DIMM Press to Precision DIMM Press | Equipment names and type filters use new name; machines keep their type ID |
| Compatibility | Open the same machine after renaming | Existing compatible parts remain attached |
| History | Complete work before renaming; then inspect History | Saved location snapshot retains original type name and the replacement date/cost |
| Duplicate name | Rename to another existing type, including different letter case | Specific error; original type unchanged; entered text preserved |
| Blank name | Clear type name and Save | Required-field error; original type unchanged |
| Cancel | Change type name then Cancel | No rename |
| Concurrent admins | Two admins open same type; admin A saves; admin B saves stale form | B gets conflict message; A's rename remains |
| Restricted roles | Sign in as Lead/Technician | No catalog-edit controls; backend rejects unauthorized actions |

## Part-detail editing

| Scenario | Action | Expected |
|---|---|---|
| Metadata | Change supplier, supplier part number, bin and lead time with a reason | Updated details appear after saving and reopening |
| Stock unchanged | Change name/SKU/cost; compare quantity and ledger | Same stock; metadata change does not create a stock transaction |
| Historical cost | Complete work at 24.50; edit current price to 55.25 | Old replacement remains 24.50 per unit; future completion records 55.25 |
| Stable part identity | Rename name/SKU and open machine history | Same part ID; replacement dates/history remain linked |
| Duplicate SKU | Enter another part's SKU, including different letter case | Specific duplicate error; data unchanged; form values preserved |
| Invalid fields | Negative cost, 3-decimal cost, blank name/bin, 0-day expected life, or target below threshold | Save blocked with explanatory error |
| Missing reason | Edit details and omit change reason | Save blocked; input retained |
| Compatibility add | Add another compatible machine type | Same SKU/shared stock appears on its machines; no duplicated physical balance |
| Compatibility remove | Remove a type with no active replacement requests | Part stops appearing on that type's machines; completed history persists |
| Active work safeguard | Create Approved or Pending request; remove its machine type from the part | Edit blocked, listing request IDs; finish/cancel work first |
| Concurrent edits | Two admins open same part; A saves then B attempts stale save | B gets conflict; A's changes are not overwritten |
| Stock received during edit | Open part editor; receive stock from another session; then save metadata | Receipt quantity remains; old displayed stock is not written back |
| Interval change | Normal request is approved at old lifetime; increase lifetime so it becomes early | Completion blocked; cancel and submit with explanation for lead review |
| Cancel/reopen | Type changes, Cancel, open editor again | Saved original values load; no controller-disposal error |
| Persistence | Save edits, restart both services, sign in again | Edited details, history and line permissions remain |

Also verify previous account editing, whole-building vs individual-line access, equipment filters, first-password changes and replacement approvals/completion. Report failed scenario, role, expected/actual result and exact error text. Never send passwords.
