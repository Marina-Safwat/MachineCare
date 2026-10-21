# MachineCare — final manager deck and walkthrough (19 October 2026)

Files in this folder:

- `MachineCare_Manager_Review_Final.pptx`: 21 editable slides. Speaker notes are on every slide.
- `MachineCare_Manager_Review_Final.pdf`: offline fallback, rendered with LibreOffice.
- `screenshots/`: real captures of the running app.
- Rebuild the deck with `node docs/build_final_deck.js`. It needs pptxgenjs, react, react-dom, react-icons and sharp.

## Where the screenshots came from

The screenshots were recaptured on 19 October 2026 after the readability UI refresh (see `docs/ui-refresh-2026-10-19/`), so the deck shows the current design.

The screenshots come from a release web build of the current app, served on loopback. The backend ran against a **disposable database** built only for the captures:

- The repository's sample structure: 3 lines, DIMM/ACOS/conveyor.
- The repository's DIMM and AOI importers.
- Three throwaway accounts: `demo.admin`, `demo.lead` and `demo.tech`.
- A few fictional requests, completions and reorders.

The installed `backend/machinecare.db` was not used or touched. Every value you see on screen is illustrative: stock, costs, request numbers, PO and delivery references, and asset tags. Only the part references and the 2 DIMM + 1 AOI per line layout come from maintenance.

## Walkthrough: suggested order (10–15 minutes)

| # | Slide | What to say / show |
|---|---|---|
| 1 | Title | Working local pilot; screenshots are the real app on demo data. The ask is a one-line validation pilot. |
| 2 | Three questions | Which machine, what stock, what happened. One workflow: request → review → reserve → complete → history. |
| 3 | What exists today | 11 screens, 3 roles, 11 machines, 20 parts. 140 backend + 45 Flutter tests pass; analysis clean. |
| 4 | Production model | Three lines × (2 DIMM + 1 AOI), plus ACOS and conveyor. New tags and stations are placeholders. |
| 5 | Roles | Admin / Lead / Technician table. The Technician screenshot shows the shorter menu. The server enforces every rule. |
| 6 | Overview | Counters, production status, low-stock list. |
| 7 | Equipment | Building › line › type tree, filters, scoped access. |
| 8 | Inventory | Physical / reserved / available. Real references kept. Demo values flagged in the app. |
| 9 | Maintenance flow | Approval reserves; only completion deducts stock; cancel never deducts. |
| 10 | Approvals | Pending early request with explanation; approved work ready to complete. |
| 11 | History + stock | Snapshots of location and cost; append-only stock ledger. |
| 12 | Purchasing | Lead vs Admin approval; partial delivery 4 of 10; duplicates rejected. Supplier ordering stays manual. |
| 13 | Oversight | Persistent alerts, reports and CSV, audit log. Email is built but switched off. |
| 14 | Safeguards | Sign-in, permissions, transactions, safe exports, verified backups, loopback-only. |
| 15 | Readiness scorecard | Features done; data, hosting, security and acceptance not. |
| 16 | Release gates | Nine gates with owner and evidence (table). |
| 17 | Decisions | Multi-bin, backdating, emergency work, corrections. |
| 18 | Rollout | Now → one-line pilot → harden → go live. No dates. |
| 19 | The decision | One line, named owners, agreed measures. |
| 20–21 | Appendix | DIMM and AOI component references exactly as supplied. |

## What is still missing for production

Source: `docs/PRODUCTION_READINESS.md`, `docs/SECURITY_REVIEW.md` and `docs/FEATURE_INVENTORY.md`.

1. **Verified operational data.** Count real stock, assign bins, set prices, suppliers and lead times. Confirm intervals, asset tags, stations, serials and status. Today these are demo values.
2. **AOI identification.** Confirm the TM robot model and the unknown manufacturers (tower light, power supply). Check the supplied model strings against nameplates.
3. **Production hosting.** Python's `http.server` is documented as unsuitable for production. Needs an approved server or adapter, HTTPS with managed certificates, a reviewed origin, and an upgrade and rollback plan. Until then the app stays loopback-only.
4. **Supported runtime.** Python 3.10 reached end of support on 2026-10-01. Pick a supported Python, review the Flutter SDK (3.24.5), and re-run all tests on them.
5. **Identity and security.** Decide on SSO/MFA. Add durable per-account rate limits, a dedicated service account, file permissions on the database and backups, and secret management. An **independent security review** is required.
6. **Backups and recovery.** Scheduled, monitored, encrypted, off-host. Defined retention and RPO/RTO. A restore drill on a separate host.
7. **Operations.** Service auto-start and restart, monitoring of worker freshness, centralized redacted logs, patching, and a named support owner.
8. **User acceptance.** Signed-in browser sessions for every role, a CSV opened in Excel, a screen-reader and accessibility review, and concurrency/load checks.
9. **Business rules.** Agree on multi-bin allocation, backdating, emergency override, and corrections/reversals, or explicitly defer them from release 1.
10. **Optional email.** SMTP server, approved recipients, secrets, and explicit authorization to send real email.

Supplier ordering stays manual (no ERP integration). SQLite is fine for the pilot. Assess concurrency before deciding whether a different database is needed.

## Checks run for this deck (19 October 2026, cloud workspace)

- `python -m unittest discover -s backend/tests`: **140 tests, OK** (120 s).
- `flutter test`: **45 tests passed**. `flutter analyze`: **no issues**. Flutter 3.24.5.
- `flutter build web --release --no-web-resources-cdn`: passed. The existing Cupertino-font warning still appears.
- PPTX package validation passed. Every slide was rendered through LibreOffice and inspected.
- **Not verified:** opening the deck in desktop PowerPoint, and signed-in Chrome/Excel CSV download on the laptop. Rehearse both before the meeting.

## Added 2026-10-20: lead time and budget slides

- Inventory, Reorders and Overview screenshots now show supplier lead time. The demo lead times (100, 120, 90 and 45 days) are illustrative.
- Slide 19, "MachineCare costs about a third of the outside system", is a 5-year cumulative comparison.
- Slide 20, "Budget plan to run MachineCare here", lists the assumptions behind the MachineCare figures.
- Both slides are driven by the same inputs as `docs/budget/MachineCare_Cost_Comparison.xlsx`. If you change the spreadsheet, also update the `B = {...}` inputs in `docs/build_final_deck.js` and rebuild.

## Updated 2026-10-21: detailed budget from the revised spreadsheet

- The security review is done by the in-house security team: 20 h × $40 = $800, matching the user's sheet. It applies to both options.
- Slide 19 shows the 5-year comparison chart.
- Slide 20 shows the side-by-side budget by category: vendor vs MachineCare, Year 1, each later year and 5 years.
- Slide 21 shows the assumptions: values from the user's sheet vs lines added for a fair comparison. With the added lines set to 0, the reconciliation gives exactly the sheet's figures.
- Appendix C lists every cost line for both options.
- **Single source of truth:** `docs/budget/MachineCare_Cost_Comparison.xlsx`. To update the slides:
  1. Edit the blue cells and save in Excel.
  2. Run `python docs/budget/export_budget.py`.
  3. Run `node docs/build_final_deck.js`.
