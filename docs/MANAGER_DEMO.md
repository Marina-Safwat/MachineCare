# MachineCare manager walkthrough

## Updated package for 19 October 2026

Open `manager-presentation-2026-10-19/MachineCare_Manager_Review_2026-10-19.pptx`.
The matching PDF is the offline fallback; SPEAKER_NOTES.md contains the narration.
See PRODUCTION_READINESS.md for release gates and proposed owners.

Double-click `Start-Manager-Demo.cmd` in the project root after restarting the
laptop. It checks ports, creates a fresh session-cleared database copy, starts
loopback-only API/web servers and verifies they respond. Sign in with your current
Marina password. No passwords are embedded in the launcher or presentation.
If ports are occupied, it stops with a message rather than killing unknown servers.
The currently launched demo uses a copy; installed maintenance history is untouched.
Do not run the normal installed-database server at the same time as this demo.

### AOI and line layout

Each of the three configured lines (B01/L01, B01/L02, B03/L02) now has two DIMM
presses and one AOI: six DIMMs plus three AOIs. Existing ACOS and conveyor assets
were retained, for eleven total equipment records. New asset tags/stations and
Operating statuses are demo placeholders, not confirmed physical asset surveys.
No additional lines were invented for buildings that have no configured lines.

| AOI component | Manufacturer | Supplied model / identifier | Per AOI |
|---|---|---|---:|
| TM robot | TM, as supplied | Model unknown | 1 |
| Small light curtain | PILZ | PSEN op113H-s-30-030 | 4 |
| Large light curtain | PILZ | PESN op113H-s-30-075 | 2 |
| PLC PNOZ m bo.1 | PILZ | Ident-772104 | 1 |
| Tower light | Unknown | ASTLF-110-4-5FT-CM | 2 |
| Switching power supply | Unknown | s-120-24 | 1 |
| Control box | VEVOR | Serial 240108586510146 | 1 |

The user confirmed quantities of one for robot, PLC, power supply and control box.
Each AOI entry has two illustrative opening spare units (14 total), not a physical
count. Shared stock is not multiplied by the number of lines. Supplied identifiers
remain verbatim pending nameplate confirmation; the control-box serial is not
assigned to every AOI. Safety component entries are not inspection certifications
or maintenance recommendations. There are now 20 total catalog entries.

### Before the meeting

1. Open the PPTX once in PowerPoint; use the PDF if needed. Desktop PowerPoint
   rendering could not be verified here, although package structure was checked.
2. Sign in to the demo, review Equipment and Inventory, then rehearse one DIMM
   replacement. The diagram and parts also appear in the slides if login fails.
3. Download a CSV and open it in Excel. This manual acceptance check remains open.
4. State that this is a supervised local pilot with sample stock/planning values.
5. Ask for a maintenance data owner, an IT reviewer and a one-line validation pilot.

Present as a local pilot with real part references and illustrative inventory.
Allow 10–15 minutes for the presentation. Before scheduling, complete one signed-in
browser rehearsal on this laptop, including a downloaded CSV opened in Excel.
The backend workflow has been rehearsed on a disposable copy; this does not replace
that final browser check. Use a separate database copy for any demonstration that
records completion or receives stock, so the installed history stays unchanged.

## What is real and what is illustrative

The ten part names, supplied manufacturers, part numbers/serial and quantities
used per machine came from the user. The user confirmed Old Auto DIMM means the
existing DIMM Press type. The tray clamp manufacturer is unknown. Load-cell
2511231 is a supplied serial reference, not a model or part number; it does not
identify every spare load cell. Manufacturer is separate from purchasing supplier.

The user authorized illustrative spare counts. All imported SKUs begin DEMO-AD-.
Their cost is $0 as an unknown-price placeholder, their bin is unassigned, and
their 365-day interval and zero-day lead time are placeholders. Threshold is one
machine's installed quantity; target is three machines' quantities. These are demo
settings, not verified maintenance or purchasing recommendations. Financial
reports for these parts are not actual cost estimates. Inventory displays these
limitations and preserves the supplied references separately.

| Part | Manufacturer | Part number / serial | Used per machine | Initial demo spares |
|---|---|---|---:|---:|
| Load cell | Delta Transducers | Serial 2511231 | 5 | 10 |
| Finger cylinder | Airtac | HFD12X50 | 4 | 8 |
| Vertical cylinder | Airtac | HLQ12X50S | 5 | 10 |
| Solenoid valve | Airtac | 7V110-6 | 10 | 6 |
| Tray cylinder | Airtac | TCL25X20S | 2 | 4 |
| Tray clamp cylinder | Unknown | HLS16X20SAS | 4 | 8 |
| Finger reed switch sensor | Airtac | DMSH A11DW | 8 | 16 |
| Vertical reed switch sensor | Airtac | D-M98W | 10 | 20 |
| Flag sensor | Panasonic | PM-T45 | 8 | 16 |
| Photoelectric sensor | Panasonic | CX-441 | 12 | 24 |

## Presentation sequence

1. Overview: explain equipment visibility, low stock and upcoming maintenance.
2. Inventory: search HFD12X50, explain four installed per machine versus eight
   illustrative spares; show manufacturer and compatibility.
3. Equipment: select an existing DIMM Press and request one finger cylinder.
4. Approvals: show reservation without physical deduction, then record completion
   on the demonstration copy. Available stock and maintenance history update.
5. Purchasing: show the solenoid example, six spares against a threshold of ten.
   Explain request, approval/order status, and partial receipts. Supplier ordering
   and real email are not activated.
6. History/Reports: show traceability and a CSV export. Explain that prices remain
   unknown, so cost totals are illustrative/incomplete.
7. Close with the pilot proposal: validate stock, bins, prices and intervals with
   maintenance, then agree users, deployment and acceptance criteria.

## Next milestones

- Final signed-in Chrome rehearsal and CSV opening: budget 30–60 minutes if no
  issues arise. This is an estimate, not an already-completed check.
- Manager presentation: ready to schedule after that rehearsal passes; it does
  not need to wait for production hosting.
- Operational release: verified inventory/planning data, supported runtime,
  hosting/identity decisions, backup policy and security acceptance remain open.

## Repeat import

Stop the backend before upgrading. The explicit local command creates a verified
backup first and imports in one transaction; it never creates accounts or resets
existing balances. Re-running skips imported source keys. Conflicting SKUs abort.

```powershell
python backend/import_auto_dimm.py --db backend/machinecare.db --backup-dir backend/backups/pre-auto-dimm
```
