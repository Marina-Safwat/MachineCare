# Manual acceptance scenarios

Use sample accounts and sample inventory. Start as Administrator. Lead A should have B01 whole-building access; create Technician A assigned to it.

| Scenario | Action | Expected |
|---|---|---|
| Existing rights | Upgrade and sign in as an existing employee | Previous whole-building equipment remains visible |
| Single line | Edit Technician A; uncheck B01 whole building; check only B01 L01 | After signing in again, only L01 appears; L02 does not appear in line filters |
| Parent visibility | Inspect equipment hierarchy as Technician A | B01 appears as the parent; this does not grant L02 access |
| Whole building | Grant Technician A B01 whole building | After signing in again, all B01 lines appear |
| Future line | As admin add B01 L03 | A whole-building employee sees L03 in line choices; a L01-only employee does not |
| Mixed scope | Grant B01 whole building and one B03 line | Only that B03 line plus every B01 line is accessible; assigned lead must cover both |
| Lead mismatch | Narrow lead to L01, try granting its technician L02 | Edit is blocked; previous settings remain |
| Future coverage | Lead gets explicit L01/L02; try granting technician whole B01 | Edit is blocked, since the lead lacks whole-building/future-line coverage |
| Pending work | Create early pending request on L01; try removing technician's L01 access | Save is blocked until work is reviewed/completed or cancelled appropriately |
| Lead access removal | Lead supervises L01 technician; try removing lead's L01 access | Save is blocked until technician is reassigned or restricted |
| History visibility | Complete work on L02, then restrict employee to L01 | Employee no longer sees L02 history; administrator still sees it |
| Session revocation | Keep employee signed in; admin changes line selection | Employee's next Refresh/action requires sign-in; new sign-in uses new scope |
| Create account | Create employee with only L02, complete first-password change | Only L02 equipment is available |
| No access | Create unassigned technician with no scopes | No machines/lines appear; no direct machine actions allowed |
| Cancel edit | Change line selections, then Cancel | Previous scope persists |
| Restart | Save L01-only access, restart services | Scope remains L01-only |
| Prior regression | Search/filter machines and open/cancel/reopen replacement form | Filters and dialog fix continue working |

Document unexpected results with scenario name, role, selected building/line, error text and expected/actual behavior. Do not send passwords.
