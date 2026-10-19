$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$output = Join-Path $PSScriptRoot 'manager-presentation-2026-10-19'
New-Item -ItemType Directory -Force -Path $output | Out-Null
$slides = @(
 @{Title='MachineCare'; Eyebrow='MANAGER REVIEW / 19 OCTOBER 2026'; Body="Maintenance visibility for DIMM and AOI lines`n`nWorking local pilot | Representative equipment and component data`n`nDecision requested: approve a scoped validation pilot and IT review."; Notes='Introduce this as a working local pilot, not a production deployment. The component references come from maintenance; inventory, cost and planning assumptions are clearly marked.'},
 @{Title='One record from request to replacement'; Eyebrow='THE OPERATIONAL VALUE'; Body="Equipment context  >  Part request  >  Review / reservation`n`nPhysical completion  >  Stock deduction  >  Traceable history`n`nShared inventory and purchasing give maintenance leads a common view.`nNo downtime, savings or ROI claim has been measured yet."; Notes='Explain that approving work reserves parts; only physical completion deducts stock. The pilot is intended to validate usefulness, not claim quantified savings.'},
 @{Title='The line model now reflects your layout'; Eyebrow='EQUIPMENT STRUCTURE'; Body="EACH LINE:     DIMM PRESS 1   +   DIMM PRESS 2   +   AOI`n`nB01 / L01       2 DIMM presses       1 AOI`nB01 / L02       2 DIMM presses       1 AOI`nB03 / L02       2 DIMM presses       1 AOI`n`n6 DIMM + 3 AOI across 3 configured lines. Existing ACOS and conveyor retained: 11 total assets."; Notes='These are the three configured lines, not a claim that all nine building records have complete equipment. New tags, positions and operating statuses are demo placeholders; asset serials still need confirmation.'},
 @{Title='DIMM catalog: ten supplied references'; Eyebrow='REAL COMPONENT INFORMATION'; Body="Load cell / cylinders / solenoid / reed switches / optical sensors`nManufacturers supplied: Delta Transducers, Airtac and Panasonic`n`nExample: Finger cylinder | HFD12X50 | 4 used per DIMM`nLoad cell: serial reference 2511231, not a general part number`n`n122 illustrative opening spare units across the ten DIMM entries.`nInstalled quantities and shared spare balances are separate."; Notes='Show HFD12X50 in Inventory. Two DIMMs imply eight finger cylinders installed per line; that is not the spare inventory. Tray clamp manufacturer remains unknown.'},
 @{Title='AOI: robot cell and safety components'; Eyebrow='USER-SUPPLIED REFERENCES / 1 OF 2'; Body="TM robot                         Model not supplied | 1 per AOI confirmed`nPILZ small light curtain       PSEN op113H-s-30-030 | 4 per AOI`nPILZ large light curtain       PESN op113H-s-30-075 | 2 per AOI`nPILZ PLC PNOZ m bo.1         Ident-772104 | 1 per AOI confirmed`n`nIdentifiers preserved exactly as supplied. Validate against nameplates.`nCatalog entries do not validate safety functions or inspection intervals."; Notes='PESN and PNOZ m bo.1 are retained exactly as received, without guessing a corrected model. Counts of four and two were supplied. The user confirmed one robot and one PLC per AOI.'},
 @{Title='AOI: signaling, power and enclosure'; Eyebrow='USER-SUPPLIED REFERENCES / 2 OF 2'; Body="Tower light                 ASTLF-110-4-5FT-CM | 2 per AOI`nSwitching supply          s-120-24 | 1 per AOI confirmed`nVEVOR control box        Serial 240108586510146 | 1 per AOI confirmed`n`nTower-light and power-supply manufacturers remain unknown.`nControl-box serial is a reference, not every AOI's asset serial.`nSeven AOI catalog entries; 14 illustrative opening spare units."; Notes='Include the robot as one of the seven catalog entries. All seven have two illustrative spare units for the demo; no physical spare count was supplied. Do not describe a robot as actually in stores.'},
 @{Title='Known information versus demo assumptions'; Eyebrow='DATA CONFIDENCE'; Body="SUPPLIED: component names, stated manufacturers, identifiers and explicit counts`nCONFIRMED: two DIMM presses and one AOI on each line`n`nILLUSTRATIVE: spare stock, reorder levels, new asset tags / station / status`nUNKNOWN: actual prices, bins, supplier details, lead times and service intervals`n`n`$0 = unknown-price placeholder. 365 days = demo interval, not an instruction.`n20 catalog entries total: 17 supplied component references + 3 earlier samples."; Notes='Financial totals are incomplete and must not be used for procurement approval. Serial references must not be replicated as unique asset serials. The application shows demo notices.'},
 @{Title='Ten-minute live walkthrough'; Eyebrow='DEMO SCRIPT'; Body="1   Equipment: show a line with two DIMMs and one AOI`n2   Inventory: search HFD12X50 and PSEN; distinguish installed from spare counts`n3   Demo copy only: request one finger cylinder and show reservation`n4   Demo copy only: record completion, stock change and history`n5   Show low-stock planning, order stages and a CSV report`n`nUse the PDF fallback if the browser is unavailable."; Notes='Never rehearse fictional completion in the installed database. Sign in before the meeting, check all screens and verify a CSV in Excel. Supplier ordering remains manual; email is disabled. The disposable backend test is not a signed-in browser acceptance test.'},
 @{Title='What works today'; Eyebrow='IMPLEMENTED LOCAL PILOT'; Body="Scoped Administrator / Lead / Technician permissions`nEquipment registry, shared catalog and compatibility`nRequests, review, reservations, completion and historical snapshots`nStock receipts / adjustments, purchasing and partial deliveries`nIn-app alerts, audit / stock viewers and CSV generation`n`nBackup and email-worker code exists; unattended services are not activated."; Notes='Administrator manages accounts and structure. Leads run operations within scope; technicians operate within assigned access. Distinguish code implementation from infrastructure activation.'},
 @{Title='Production gates: platform and assurance'; Eyebrow='NOT READY FOR COMPANY-WIDE DEPLOYMENT'; Body="IT: approved hosting, HTTPS, service identity, access controls and secrets`nEngineering: supported patched runtime / SDK and deployment testing`nSecurity: identity / SSO-MFA decision, abuse controls and independent review`nOperations: monitored startup services and protected off-host backups`nAcceptance: authenticated browser workflows, concurrency and recovery tests`n`nCurrent server is loopback-only. Production date depends on these gates."; Notes='Keep the current architecture for the pilot. A production server adapter requires agreement; a database migration or framework rewrite is not automatically required. Define backup recovery objectives and test them.'},
 @{Title='Production gates: maintenance decisions'; Eyebrow='DATA AND WORKFLOW OWNERSHIP'; Body="Validate physical stock, actual assets, bins, prices and replacement intervals`nConfirm AOI model spellings and counts; obtain missing robot details`nDecide multi-bin rules, backdating, emergency review and corrections`nApprove email recipients / SMTP and supplier-ordering process if required`nAgree support ownership, pilot scope and measurable acceptance criteria`n`nRecommended owners: maintenance lead + IT/security + application owner."; Notes='These business rules are unresolved scope decisions. They may be deferred explicitly for a limited pilot; do not describe them as completed or set a production date before the decision.'},
 @{Title='The decision for tomorrow'; Eyebrow='PROPOSED NEXT STEP'; Body="Approve a limited, supervised pilot on one validated line.`n`nName a maintenance data owner and an IT/security reviewer.`nAgree success measures: traceability, stock accuracy and operator usability.`nReview findings before expanding access or committing a production date.`n`nToday: working local pilot. Next: verified data and user acceptance."; Notes='Ask for permission to validate the process and assign owners, not immediate company-wide deployment. Capture feedback and prioritize production gaps. Use the detailed readiness checklist in the handoff package.'}
)
$slides | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $output 'slide-content.json') -Encoding UTF8
$app = New-Object -ComObject PowerPoint.Application
$deck = $app.Presentations.Add(0)
try {
 $deck.PageSetup.SlideWidth = 960
 $deck.PageSetup.SlideHeight = 540
 $index = 0
 foreach ($item in $slides) {
  $index++
  $slide = $deck.Slides.Add($index, 12)
  $slide.FollowMasterBackground = 0
  $slide.Background.Fill.ForeColor.RGB = 2235152
  $accent = $slide.Shapes.AddShape(1, 0, 0, 12, 540)
  $accent.Fill.ForeColor.RGB = 12566288
  $accent.Line.Visible = 0
  foreach ($spec in @(
   @{Text=$item.Eyebrow; X=48; Y=28; W=864; H=28; Size=12; Color=12566288; Bold=-1},
   @{Text=$item.Title; X=48; Y=69; W=864; H=90; Size=32; Color=16777215; Bold=-1},
   @{Text=$item.Body; X=48; Y=177; W=864; H=302; Size=20; Color=15723743; Bold=0},
   @{Text="MACHINECARE  /  LOCAL PILOT  /  19 OCT 2026                                      $index / $($slides.Count)"; X=48; Y=507; W=864; H=18; Size=10; Color=11908533; Bold=0}
  )) {
   $shape = $slide.Shapes.AddTextbox(1,$spec.X,$spec.Y,$spec.W,$spec.H)
   $shape.TextFrame.MarginLeft=0; $shape.TextFrame.MarginRight=0
   $shape.TextFrame.MarginTop=0; $shape.TextFrame.MarginBottom=0
   $shape.TextFrame.WordWrap=-1
   $range=$shape.TextFrame.TextRange
   $range.Text=$spec.Text
   $range.Font.Name='Aptos'
   $range.Font.Size=$spec.Size
   $range.Font.Color.RGB=$spec.Color
   $range.Font.Bold=$spec.Bold
   if ($range.BoundHeight -gt ($spec.H + 3)) { throw "Text overflow on slide $index" }
  }
  $slide.NotesPage.Shapes.Placeholders.Item(2).TextFrame.TextRange.Text=$item.Notes
 }
 $pptx=Join-Path $output 'MachineCare_Manager_Review_2026-10-19.pptx'
 $pdf=Join-Path $output 'MachineCare_Manager_Review_2026-10-19.pdf'
 $deck.SaveAs($pptx,24)
 $deck.SaveAs($pdf,32)
 $deck.Slides.Item(3).Export((Join-Path $output 'line-layout-preview.png'),'PNG',1600,900)
 Write-Output "Created $($deck.Slides.Count) slides with speaker notes; checked text bounds."
 Write-Output $pptx
 Write-Output $pdf
} finally {
 $deck.Close()
 [void][Runtime.InteropServices.Marshal]::ReleaseComObject($deck)
 [void][Runtime.InteropServices.Marshal]::ReleaseComObject($app)
}
