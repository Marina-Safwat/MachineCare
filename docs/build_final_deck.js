// Final manager deck: editable pptxgenjs build with real screenshots captured from
// a disposable demo database (never the installed database).
// Run from the project root: node docs/build_final_deck.js
const path = require("path");
const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");
const fa = require("react-icons/fa");

const OUT = path.join(__dirname, "manager-presentation-2026-10-19", "final");
const SHOT = (n) => path.join(OUT, "screenshots", n + ".png");
const APPLY_THEME = process.env.PPTX_APPLY_THEME;

const THEME = {
  name: "MachineCare",
  headFontFace: "Calibri",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "17232E", lt1: "FFFFFF", dk2: "0F2A3A", lt2: "EEF4F5",
    accent1: "00695C", accent2: "4DB6AC", accent3: "E0A030", accent4: "C2410C",
    accent5: "5B7083", accent6: "B2DFDB", hlink: "00695C", folHlink: "5B7083",
  },
};
const HEX = THEME.colors;

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.333 x 7.5
pres.title = "MachineCare - Manager Review";
pres.author = "MachineCare project";
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
const C = pres.SchemeColor;

const FOOT = "MachineCare  ·  Manager review  ·  19 October 2026";
pres.defineSlideMaster({
  title: "CONTENT",
  background: { color: HEX.lt2 },
  objects: [
    { placeholder: { options: { name: "kicker", type: "body", x: 0.6, y: 0.32, w: 12.1, h: 0.3, fontSize: 12, bold: true, color: C.accent1, charSpacing: 2, margin: 0 }, text: "" } },
    { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.6, w: 12.1, h: 0.75, fontSize: 32, bold: true, color: C.text2, margin: 0, valign: "top", align: "left" }, text: "" } },
    { text: { text: FOOT, options: { x: 0.6, y: 7.05, w: 8, h: 0.25, fontSize: 10, color: C.accent5, margin: 0 } } },
  ],
  slideNumber: { x: 12.2, y: 7.05, w: 0.5, h: 0.25, fontSize: 10, color: C.accent5, align: "right" },
});
pres.defineSlideMaster({
  title: "DARK",
  background: { color: HEX.dk2 },
  objects: [
    { placeholder: { options: { name: "kicker", type: "body", x: 0.6, y: 0.5, w: 12.1, h: 0.3, fontSize: 12, bold: true, color: C.accent2, charSpacing: 2, margin: 0 }, text: "" } },
    { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.85, w: 12.1, h: 1.0, fontSize: 36, bold: true, color: C.background1, margin: 0, valign: "top", align: "left" }, text: "" } },
  ],
  slideNumber: { x: 12.2, y: 7.05, w: 0.5, h: 0.25, fontSize: 10, color: C.accent2, align: "right" },
});

async function icon(Comp, color, size = 256) {
  const svg = ReactDOMServer.renderToStaticMarkup(React.createElement(Comp, { color: "#" + color, size: String(size) }));
  const buf = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + buf.toString("base64");
}

const shadow = () => ({ type: "outer", color: "0F2A3A", blur: 8, offset: 2, angle: 90, opacity: 0.18 });

function content(kicker, title, section) {
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: section });
  s.addText(kicker.toUpperCase(), { placeholder: "kicker" });
  s.addText(title, { placeholder: "title" });
  return s;
}
// Screenshot framed as a white card with soft shadow: the deck's recurring motif.
function screenshot(s, name, x, y, w, ratio = 1440 / 900) {
  const h = w / ratio;
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: x - 0.08, y: y - 0.08, w: w + 0.16, h: h + 0.16, rectRadius: 0.08, fill: { color: C.background1 }, line: { color: "D5E0E3", width: 0.75 }, shadow: shadow(), objectName: "Frame " + name });
  s.addImage({ path: SHOT(name), x, y, w, h, altText: "MachineCare " + name.replace(/_/g, " ") + " screen (demo data)", objectName: "Screenshot " + name });
  return h;
}
function card(s, x, y, w, h, fill = C.background1) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.1, fill: { color: fill }, line: { color: "D5E0E3", width: 0.75 }, shadow: shadow() });
}
// Numbered callouts beside a screenshot.
function callouts(s, x, y, w, heading, items) {
  s.addText(heading, { x, y, w, h: 0.5, fontSize: 20, bold: true, color: C.accent1, margin: 0, isTextBox: true });
  items.forEach(([head, body], i) => {
    const yy = y + 0.75 + i * 1.3;
    s.addShape(pres.shapes.OVAL, { x, y: yy, w: 0.42, h: 0.42, fill: { color: C.accent1 }, line: { type: "none" } });
    s.addText(String(i + 1), { x, y: yy, w: 0.42, h: 0.42, fontSize: 14, bold: true, color: C.background1, align: "center", valign: "middle", margin: 0, isTextBox: true });
    s.addText([{ text: head, options: { bold: true, color: C.text2, breakLine: true } }, { text: body, options: { color: C.accent5 } }],
      { x: x + 0.6, y: yy - 0.05, w: w - 0.6, h: 1.15, fontSize: 14, valign: "top", margin: 0, paraSpaceAfter: 2, isTextBox: true });
  });
}
function demoTag(s, x, y, text = "Demo database · illustrative values") {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w: 3.3, h: 0.32, rectRadius: 0.16, fill: { color: "FFF4DC" }, line: { color: HEX.accent3, width: 0.75 } });
  s.addText(text, { x, y, w: 3.3, h: 0.32, fontSize: 10, bold: true, color: "8A5A00", align: "center", valign: "middle", margin: 0, isTextBox: true });
}

(async () => {
  const I = {};
  for (const [k, comp, col] of [
    ["machine", fa.FaIndustry, HEX.accent1], ["box", fa.FaBoxes, HEX.accent1], ["history", fa.FaHistory, HEX.accent1],
    ["lock", fa.FaLock, HEX.accent1], ["shield", fa.FaShieldAlt, HEX.accent1], ["db", fa.FaDatabase, HEX.accent1],
    ["users", fa.FaUserShield, HEX.accent1], ["file", fa.FaFileCsv, HEX.accent1], ["key", fa.FaKey, HEX.accent1],
    ["check", fa.FaCheckCircle, HEX.accent1], ["half", fa.FaAdjust, HEX.accent3], ["x", fa.FaTimesCircle, HEX.accent4],
    ["server", fa.FaServer, HEX.accent1], ["clip", fa.FaClipboardCheck, HEX.accent1], ["cloud", fa.FaCloudUploadAlt, HEX.accent1],
    ["cog", fa.FaCogs, HEX.accent1], ["mail", fa.FaEnvelope, HEX.accent1], ["user", fa.FaUserCheck, HEX.accent1],
    ["wcheck", fa.FaCheck, "FFFFFF"],
  ]) I[k] = await icon(comp, col);

  // ---------- 1. Title ----------
  pres.addSection({ title: "Opening" });
  let s = pres.addSlide({ masterName: "DARK", sectionTitle: "Opening" });
  s.addText("MANAGER REVIEW  ·  19 OCTOBER 2026", { placeholder: "kicker" });
  s.addText("MachineCare", { placeholder: "title" });
  s.addText("Equipment, spare parts and every replacement in one traceable record", { x: 0.6, y: 1.85, w: 5.6, h: 1.0, fontSize: 22, color: C.accent6, margin: 0, isTextBox: true });
  s.addText([
    { text: "Working local pilot for DIMM press and AOI lines", options: { bullet: true, breakLine: true } },
    { text: "Walkthrough of the app as it runs today", options: { bullet: true, breakLine: true } },
    { text: "What still stands between the pilot and production", options: { bullet: true } },
  ], { x: 0.6, y: 3.2, w: 5.4, h: 1.5, fontSize: 16, color: C.background1, paraSpaceAfter: 8, margin: 0, isTextBox: true });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.6, y: 5.3, w: 4.4, h: 0.6, rectRadius: 0.3, fill: { color: C.accent1 }, line: { type: "none" } });
  s.addText("Ask: approve a one-line validation pilot", { x: 0.6, y: 5.3, w: 4.4, h: 0.6, fontSize: 15, bold: true, color: C.background1, align: "center", valign: "middle", margin: 0, isTextBox: true });
  s.addImage({ path: SHOT("overview"), x: 6.6, y: 2.0, w: 6.2, h: 6.2 / 1.6, altText: "MachineCare overview screen", shadow: { type: "outer", color: "000000", blur: 12, offset: 4, angle: 90, opacity: 0.4 } });
  s.addNotes("Open with the purpose: MachineCare connects machines, shared spare parts and each replacement so we can answer what was replaced, where, by whom, with which part and at what cost. Today it is a working local pilot on this laptop, not a company-wide production system. The screenshots in this deck come from the real application running on a demonstration copy of the data. The ask at the end is a supervised one-line validation pilot.");

  // ---------- 2. Why ----------
  s = content("Why this matters", "Three questions maintenance must answer quickly", "Opening");
  [["machine", "Which machine?", "Building › line › station › machine, with the parts each machine type is compatible with."],
   ["box", "What do we have?", "Physical, reserved and available stock for shared spares, and low-stock alerts before a line waits on a part."],
   ["history", "What happened?", "Who replaced which part, when, where, why, and at what cost, recorded at the moment the work is completed."]]
    .forEach(([ic, h, b], i) => {
      const x = 0.6 + i * 4.15;
      card(s, x, 1.75, 3.85, 3.6);
      s.addShape(pres.shapes.OVAL, { x: x + 0.35, y: 2.1, w: 0.9, h: 0.9, fill: { color: "E0F2F1" }, line: { type: "none" } });
      s.addImage({ data: I[ic], x: x + 0.57, y: 2.32, w: 0.46, h: 0.46 });
      s.addText(h, { x: x + 0.35, y: 3.2, w: 3.2, h: 0.5, fontSize: 22, bold: true, color: C.text2, margin: 0, isTextBox: true });
      s.addText(b, { x: x + 0.35, y: 3.75, w: 3.2, h: 1.4, fontSize: 15, color: C.accent5, margin: 0, valign: "top", isTextBox: true });
    });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.6, y: 5.75, w: 12.1, h: 0.75, rectRadius: 0.1, fill: { color: C.text2 }, line: { type: "none" } });
  s.addText([{ text: "One workflow:  ", options: { bold: true, color: C.accent2 } }, { text: "Request  →  Review  →  Reserve stock  →  Complete  →  Traceable history", options: { color: C.background1 } }],
    { x: 0.9, y: 5.75, w: 11.5, h: 0.75, fontSize: 18, valign: "middle", margin: 0, isTextBox: true });
  s.addNotes("These are intended benefits, not measured savings. Today this information is spread across people, paper and spreadsheets. The pilot should measure three things: traceability of replacements, stock accuracy, and how easy the app is for operators.");

  // ---------- 3. At a glance ----------
  s = content("What exists today", "A complete working pilot, not a mock-up", "Opening");
  [["11", "screens", "Overview to Reports"], ["3", "roles", "Admin · Lead · Technician"], ["11", "machines", "6 DIMM + 3 AOI + 2 others"], ["20", "catalog parts", "with real DIMM/AOI references"]]
    .forEach(([n, l, sub], i) => {
      const x = 0.6 + i * 3.1;
      card(s, x, 1.7, 2.85, 2.2);
      s.addText(n, { x: x + 0.3, y: 1.85, w: 2.4, h: 1.0, fontSize: 54, bold: true, color: C.accent1, margin: 0, isTextBox: true });
      s.addText(l, { x: x + 0.3, y: 2.85, w: 2.4, h: 0.4, fontSize: 18, bold: true, color: C.text2, margin: 0, isTextBox: true });
      s.addText(sub, { x: x + 0.3, y: 3.25, w: 2.4, h: 0.4, fontSize: 13, color: C.accent5, margin: 0, isTextBox: true });
    });
  card(s, 0.6, 4.25, 6.0, 2.45);
  s.addText("Built with", { x: 0.9, y: 4.4, w: 5.4, h: 0.4, fontSize: 18, bold: true, color: C.text2, margin: 0, isTextBox: true });
  s.addText([
    { text: "Flutter web front end (works on desktop, tablet, phone)", options: { bullet: true, breakLine: true } },
    { text: "Python API using only the standard library", options: { bullet: true, breakLine: true } },
    { text: "SQLite database with 7 ordered schema migrations", options: { bullet: true, breakLine: true } },
    { text: "Optional background worker: checks, backups, email", options: { bullet: true } },
  ], { x: 0.9, y: 4.85, w: 5.5, h: 1.75, fontSize: 14, color: C.accent5, paraSpaceAfter: 4, margin: 0, isTextBox: true });
  card(s, 6.85, 4.25, 5.85, 2.45);
  s.addText("Verified by automated tests", { x: 7.15, y: 4.4, w: 5.3, h: 0.4, fontSize: 18, bold: true, color: C.text2, margin: 0, isTextBox: true });
  s.addText([
    { text: "140 backend tests: permissions, stock, workflows, security, backups", options: { bullet: true, breakLine: true } },
    { text: "45 Flutter widget tests: screens, roles, forms, layouts", options: { bullet: true, breakLine: true } },
    { text: "Static analysis: no issues found", options: { bullet: true } },
  ], { x: 7.15, y: 4.85, w: 5.35, h: 1.75, fontSize: 14, color: C.accent5, paraSpaceAfter: 4, margin: 0, isTextBox: true });
  s.addNotes("Everything shown in the walkthrough works end to end in the browser. Test counts are from a run on 19 October 2026 against disposable databases. Tests prove the rules behave; they do not replace a signed-in acceptance session with real users, which is still on the production list.");

  // ---------- 4. Plant model ----------
  s = content("Production model", "Every configured line: two DIMM presses and one AOI", "Opening");
  [["B01 / L01"], ["B01 / L02"], ["B03 / L02"]].forEach(([ln], r) => {
    const y = 1.75 + r * 1.2;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.6, y, w: 2.2, h: 0.95, rectRadius: 0.1, fill: { color: C.text2 }, line: { type: "none" } });
    s.addText(ln, { x: 0.6, y, w: 2.2, h: 0.95, fontSize: 18, bold: true, color: C.background1, align: "center", valign: "middle", margin: 0, isTextBox: true });
    [["DIMM press 1", C.accent1], ["DIMM press 2", C.accent1], ["AOI · TM robot cell", C.accent5]].forEach(([t, col], i) => {
      const x = 3.0 + i * 2.5;
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w: 2.3, h: 0.95, rectRadius: 0.1, fill: { color: col }, line: { type: "none" } });
      s.addText(t, { x, y, w: 2.3, h: 0.95, fontSize: 15, bold: true, color: C.background1, align: "center", valign: "middle", margin: 0, isTextBox: true });
    });
  });
  s.addText([{ text: "6 DIMM + 3 AOI", options: { bold: true, color: C.accent1, breakLine: true } }, { text: "+ existing ACOS station and conveyor = 11 equipment records", options: { color: C.accent5 } }],
    { x: 0.6, y: 5.5, w: 7.0, h: 0.9, fontSize: 18, margin: 0, isTextBox: true });
  card(s, 10.75, 1.75, 1.95, 3.35);
  s.addText([{ text: "10", options: { fontSize: 36, bold: true, color: C.accent1, breakLine: true } }, { text: "DIMM part references", options: { fontSize: 13, color: C.accent5, breakLine: true } },
    { text: " ", options: { fontSize: 8, breakLine: true } }, { text: "7", options: { fontSize: 36, bold: true, color: C.accent5, breakLine: true } }, { text: "AOI component references", options: { fontSize: 13, color: C.accent5 } }],
    { x: 10.95, y: 1.9, w: 1.6, h: 3.1, margin: 0, valign: "top", isTextBox: true });
  s.addText("Part names, manufacturers, model numbers and quantities per machine were supplied by maintenance (see appendix). New asset tags, stations and statuses are placeholders until a physical survey.",
    { x: 7.9, y: 5.45, w: 4.8, h: 1.1, fontSize: 12, italic: true, color: C.accent5, margin: 0, isTextBox: true });
  s.addNotes("Three lines are configured: B01/L01, B01/L02 and B03/L02. Each has two DIMM presses and one AOI, which gives six DIMMs and three AOIs. The existing ACOS station and conveyor were kept, giving 11 equipment records. Part references are real; asset tags and stations for the newly added machines are placeholders.");

  // ---------- 5. Roles ----------
  pres.addSection({ title: "App walkthrough" });
  s = content("Who does what", "Three roles, enforced on the server", "App walkthrough");
  const rows = [
    ["Capability", "Admin", "Lead", "Tech"],
    ["View assigned machines and history", "✓", "✓", "✓"],
    ["Request a replacement; complete own work", "✓", "✓", "✓"],
    ["Review early work, complete others' work", "✓", "✓", "–"],
    ["Catalog, stock receipts and adjustments", "✓", "✓", "–"],
    ["Purchasing, audit log, stock ledger, exports", "✓", "✓", "–"],
    ["Accounts, access, buildings and lines, backups", "✓", "–", "–"],
  ];
  s.addTable(rows.map((r, i) => r.map((c, j) => ({ text: c, options: {
    bold: i === 0 || (j > 0 && c === "✓"), color: i === 0 ? HEX.lt1 : (c === "✓" ? HEX.accent1 : (c === "–" ? "9AA9B5" : HEX.dk1)),
    fill: { color: i === 0 ? HEX.dk2 : (i % 2 ? "FFFFFF" : "F5F9FA") }, align: j ? "center" : "left", fontSize: 14, valign: "middle" } }))),
    { x: 0.6, y: 1.75, w: 7.2, colW: [4.5, 0.9, 0.9, 0.9], rowH: 0.55, border: { type: "solid", color: "D5E0E3", pt: 0.75 }, margin: [0.04, 0.1, 0.04, 0.1] });
  s.addText("Technicians see a shorter menu, and only the lines they are assigned to. Hiding buttons is not the protection: the server checks every action.",
    { x: 0.6, y: 5.85, w: 7.2, h: 0.8, fontSize: 13, italic: true, color: C.accent5, margin: 0, isTextBox: true });
  screenshot(s, "technician_equipment", 8.2, 1.85, 4.5);
  s.addText("Technician view: no Management, Reorders, Audit or Stock screens", { x: 8.2, y: 4.85, w: 4.5, h: 0.6, fontSize: 12, color: C.accent5, margin: 0, isTextBox: true });
  s.addNotes("Administrator: accounts, access, plant structure, system configuration and backups. Lead: runs operations, including the catalog, stock, purchasing, approvals and audit, but can never edit accounts. Technician: works on assigned machines and can complete or cancel only their own work. Machine access is scoped by building and line, and moves check both the source and the destination line.");

  // ---------- 6. Overview ----------
  s = content("Walkthrough 1 · Overview", "The overview puts today's exceptions first", "App walkthrough");
  screenshot(s, "overview", 0.7, 1.7, 7.6);
  demoTag(s, 8.85, 6.45);
  callouts(s, 8.85, 1.7, 3.85, "Start with what needs attention", [
    ["Attention cards", "Turn amber or red when action is needed; click one to jump to that page"],
    ["Production status", "Operating, maintenance, stopped and retired, each with colour and icon"],
    ["Stock needs attention", "Parts at or below their reorder level, with a stock bar"],
  ]);
  s.addNotes("This is the landing page after sign-in. Point at the counters, then the production status chips, then the low-stock list. In the demo, the solenoid valve shows 8 available against a threshold of 10. These numbers come from the demo copy, not from real stock.");

  // ---------- 7. Equipment ----------
  s = content("Walkthrough 2 · Equipment", "Find the line, then the machine", "App walkthrough");
  screenshot(s, "equipment", 0.7, 1.7, 7.6);
  demoTag(s, 8.85, 6.45);
  callouts(s, 8.85, 1.7, 3.85, "Navigate the plant", [
    ["Building › line › type", "Expandable tree; each machine shows station, asset tag and status"],
    ["Search and filters", "By asset tag, serial, building, line, type, station and status"],
    ["Scoped", "Each user only sees the buildings and lines they are assigned"],
  ]);
  s.addNotes("Expand B01, then L01: two DIMM presses and one AOI. Open a machine to see its compatible parts and request a replacement. Leads and administrators can register, edit, move or retire machines inside their scope.");

  // ---------- 8. Inventory ----------
  s = content("Walkthrough 3 · Inventory", "Shared spare parts with honest labels", "App walkthrough");
  screenshot(s, "inventory", 0.7, 1.7, 7.6);
  demoTag(s, 8.85, 6.45);
  callouts(s, 8.85, 1.7, 3.85, "Every part shows", [
    ["Physical · reserved · available", "Three clear tiles plus a bar marking the reorder level"],
    ["Supplier lead time", "Shown in weeks or months; long-lead parts are flagged and arrival is estimated"],
    ["Real references, honest labels", "Supplied model or serial kept; a blue tag marks demo stock and prices"],
  ]);
  s.addNotes("Example: the AOI control box shows VEVOR and the supplied serial number. The tag 'Demo stock / planning values' means the opening stock, $0 price, bin and 365-day interval are placeholders. Receive, adjust and reorder are available to leads and administrators; adjustments need a reason and cannot consume reserved stock.");

  // ---------- 9. Workflow ----------
  s = content("Walkthrough 4 · Maintenance flow", "From request to an auditable replacement", "App walkthrough");
  [["01", "Request", "Technician picks machine and compatible part"], ["02", "Review", "Early work needs an explanation and lead review"], ["03", "Reserve", "Approval holds stock without deducting it"],
   ["04", "Complete", "One atomic stock deduction, at completion"], ["05", "Record", "History and ledger keep who, where, cost"]]
    .forEach(([n, h, b], i) => {
      const x = 0.6 + i * 2.45;
      card(s, x, 1.8, 2.25, 2.85);
      s.addText(n, { x: x + 0.25, y: 1.95, w: 1.8, h: 0.7, fontSize: 32, bold: true, color: C.accent1, margin: 0, isTextBox: true });
      s.addText(h, { x: x + 0.25, y: 2.7, w: 1.85, h: 0.45, fontSize: 19, bold: true, color: C.text2, margin: 0, isTextBox: true });
      s.addText(b, { x: x + 0.25, y: 3.2, w: 1.85, h: 1.3, fontSize: 13, color: C.accent5, margin: 0, valign: "top", isTextBox: true });
    });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.6, y: 5.0, w: 12.1, h: 0.7, rectRadius: 0.1, fill: { color: C.text2 }, line: { type: "none" } });
  s.addText([{ text: "Approval reserves stock.  ", options: { color: C.accent2, bold: true } }, { text: "Only completion deducts physical inventory. Cancelling never deducts.", options: { color: C.background1 } }],
    { x: 0.9, y: 5.0, w: 11.5, h: 0.7, fontSize: 17, valign: "middle", margin: 0, isTextBox: true });
  s.addText("If someone else completes or cancels your request, you are notified. The history keeps both the original requester and the person who did the work.",
    { x: 0.6, y: 5.95, w: 12.1, h: 0.6, fontSize: 13, italic: true, color: C.accent5, margin: 0, isTextBox: true });
  s.addNotes("This is the heart of the system. A normal request is approved immediately and reserves stock. If the same part on the same machine is replaced before its expected life, the technician must explain why and a lead reviews it. A pending early request reserves nothing. Completion deducts stock exactly once, creates the history record and releases the reservation. If completion fails, the reservation stays.");

  // ---------- 10. Approvals ----------
  s = content("Walkthrough 5 · Approvals", "Review early work before anyone records completion", "App walkthrough");
  screenshot(s, "approvals", 0.7, 1.7, 7.6);
  demoTag(s, 8.85, 6.45);
  callouts(s, 8.85, 1.7, 3.85, "Grouped by what to do next", [
    ["#6 Pending · early", "Finger cylinder: the technician's explanation is shown for the lead"],
    ["#5 Approved", "2 reed switches reserved; ready to record physical completion"],
    ["#4 Completed", "Locked; it now appears in History and Stock movements"],
  ]);
  s.addNotes("Request 6 is an early replacement: the leak came back after three days. A lead can approve or reject it with a comment, but cannot approve their own request. Request 5 is approved and holds two units in reserve. Record physical completion only after the work is actually done.");

  // ---------- 11. History + stock ----------
  s = content("Walkthrough 6 · Traceability", "History and stock movements explain every change", "App walkthrough");
  const hh = screenshot(s, "history", 0.7, 1.7, 5.85);
  screenshot(s, "stock_movements", 6.85, 1.7, 5.85);
  s.addText([{ text: "History  ", options: { bold: true, color: C.text2 } }, { text: "Part, machine location, who, when, quantity and cost, kept as a snapshot even if the machine later moves or the price changes", options: { color: C.accent5 } }],
    { x: 0.7, y: 1.7 + hh + 0.25, w: 5.85, h: 1.1, fontSize: 13, margin: 0, valign: "top", isTextBox: true });
  s.addText([{ text: "Stock movements  ", options: { bold: true, color: C.text2 } }, { text: "Every receipt, adjustment and deduction with actor, reason and running balance. Filters and CSV export", options: { color: C.accent5 } }],
    { x: 6.85, y: 1.7 + hh + 0.25, w: 5.85, h: 1.1, fontSize: 13, margin: 0, valign: "top", isTextBox: true });
  s.addNotes("History shows completed work only. Because location and cost are snapshots, older records stay correct when things change later. The stock ledger is append-only: nothing is overwritten, and corrections are new, explained entries. Recorded costs of $0 are the unknown-price placeholders.");

  // ---------- 12. Reorders ----------
  s = content("Walkthrough 7 · Purchasing", "Ordering is tracked, but only receipts add stock", "App walkthrough");
  screenshot(s, "reorders", 0.7, 1.7, 7.6);
  demoTag(s, 8.85, 6.45);
  callouts(s, 8.85, 1.7, 3.85, "Request › order › receive", [
    ["Approval policy", "Lead requests start approved; Admin requests need another manager"],
    ["Partial deliveries", "#1 solenoid: 10 ordered, 4 received on DN-DEMO-77, 6 still open"],
    ["Expected arrival", "Order date + supplier lead time; late deliveries turn red. Duplicates and over-receipts are rejected"],
  ]);
  s.addNotes("Supplier ordering itself is still manual: the app records the PO reference but does not send anything to a supplier or ERP. Cancelling an open balance keeps what was already received.");

  // ---------- 13. Alerts, reports, audit ----------
  s = content("Walkthrough 8 · Oversight", "Alerts, reports and a full audit trail", "App walkthrough");
  const h3 = screenshot(s, "alerts", 0.6, 2.0, 3.85);
  screenshot(s, "reports", 4.74, 2.0, 3.85);
  screenshot(s, "audit", 8.88, 2.0, 3.85);
  [["Persistent alerts", "Low stock, shortfalls and overdue intervals stay open until the condition clears"], ["Reports and CSV", "Maintenance outlook, early-replacement counts, exports protected against spreadsheet formulas"], ["Audit log", "Logins, account changes, approvals and orders. Passwords are never recorded"]]
    .forEach(([h, b], i) => s.addText([{ text: h, options: { bold: true, color: C.text2, breakLine: true } }, { text: b, options: { color: C.accent5 } }],
      { x: 0.6 + i * 4.14, y: 2.0 + h3 + 0.35, w: 3.85, h: 1.6, fontSize: 15, margin: 0, valign: "top", isTextBox: true }));
  s.addNotes("Alerts are re-evaluated whenever someone uses the app, or continuously if the optional background worker is running. Email notification is built in but switched off: it needs an approved mail server and explicit authorization. Administrators also have a system-status view for background jobs.");

  // ---------- 14. Safeguards ----------
  s = content("Built in from day one", "Safeguards that are already working", "App walkthrough");
  [["lock", "Secure sign-in", "Hashed passwords, 8-hour sessions, forced first change, lockout after repeated failures"],
   ["users", "Server-side permissions", "Every action checks role and building/line scope"],
   ["db", "No double counting", "Atomic transactions, duplicate-submit keys, edit-conflict detection"],
   ["file", "Safe exports", "Permission checked, passwords redacted, formula injection blocked"],
   ["cloud", "Verified backups", "Integrity-checked copies; recovery always uses a new file"],
   ["shield", "Local only", "Bound to this laptop (loopback); not exposed to the company network"]]
    .forEach(([ic, h, b], i) => {
      const x = 0.6 + (i % 3) * 4.15, y = 1.75 + Math.floor(i / 3) * 2.45;
      card(s, x, y, 3.85, 2.2);
      s.addShape(pres.shapes.OVAL, { x: x + 0.3, y: y + 0.3, w: 0.7, h: 0.7, fill: { color: "E0F2F1" }, line: { type: "none" } });
      s.addImage({ data: I[ic], x: x + 0.47, y: y + 0.47, w: 0.36, h: 0.36 });
      s.addText(h, { x: x + 1.2, y: y + 0.33, w: 2.5, h: 0.65, fontSize: 17, bold: true, color: C.text2, margin: 0, valign: "middle", isTextBox: true });
      s.addText(b, { x: x + 0.3, y: y + 1.1, w: 3.3, h: 0.95, fontSize: 13, color: C.accent5, margin: 0, valign: "top", isTextBox: true });
    });
  s.addNotes("These protections are tested automatically. They are a strong base, but an engineering review is not an independent security assessment, which is still a production gate.");

  // ---------- 15. Readiness scorecard ----------
  pres.addSection({ title: "Path to production" });
  s = content("Production readiness", "Features are done; operations and data are not", "Path to production");
  const score = [
    ["check", "Done", "Core workflows: equipment, inventory, approvals, history, purchasing, alerts, reports, audit"],
    ["check", "Done", "Role permissions, data integrity, backups and recovery tooling, automated tests"],
    ["half", "Partial", "Background worker and email: built and tested, not switched on or configured"],
    ["half", "Partial", "Operational data: part references real; stock, prices, bins, intervals, asset tags are demo"],
    ["x", "Missing", "Production hosting: HTTPS server, company sign-in, monitoring, supported runtime"],
    ["x", "Missing", "Independent security review and signed-in user acceptance for all roles"],
    ["x", "Missing", "Four business rules not yet decided (multi-bin, backdating, emergency work, corrections)"],
  ];
  score.forEach(([ic, st, t], i) => {
    const y = 1.7 + i * 0.72;
    card(s, 0.6, y, 12.1, 0.6);
    s.addImage({ data: I[ic], x: 0.8, y: y + 0.13, w: 0.34, h: 0.34 });
    s.addText(st, { x: 1.3, y, w: 1.3, h: 0.6, fontSize: 15, bold: true, color: ic === "check" ? C.accent1 : ic === "half" ? "8A5A00" : C.accent4, valign: "middle", margin: 0, isTextBox: true });
    s.addText(t, { x: 2.6, y, w: 9.9, h: 0.6, fontSize: 15, color: C.text1, valign: "middle", margin: 0, isTextBox: true });
  });
  s.addNotes("This is the honest summary. The software features a maintenance team needs are built and tested. What is missing is mostly not code: verified data, an approved hosting setup, company identity and security sign-off, operations ownership, and four business-rule decisions only management can make.");

  // ---------- 16. Gates ----------
  s = content("What's missing", "Release gates, owners and evidence", "Path to production");
  const gates = [
    ["Gate", "Still missing", "Owner", "Evidence of done"],
    ["Operational data", "Real stock counts, bins, prices, suppliers, intervals, asset tags", "Maintenance lead", "Signed inventory and equipment review"],
    ["AOI identification", "TM robot model, unknown makers, nameplate check", "Maintenance lead", "Verified component list"],
    ["Hosting", "Production web server, HTTPS, upgrade and rollback plan", "IT + engineering", "Reviewed staging deployment"],
    ["Runtime", "Python 3.10 out of support since 1 Oct 2026; Flutter SDK review", "Engineering", "Approved versions, tests re-run"],
    ["Identity and security", "SSO/MFA decision, service account, file permissions, secrets", "IT / security", "Independent security assessment"],
    ["Backups", "Scheduled, encrypted, off-host; recovery targets", "IT / operations", "Restore drill on a separate host"],
    ["Operations", "Auto-start, monitoring, logs, patching, support", "IT / operations", "Runbook and restart tests"],
    ["User acceptance", "All roles in Chrome, CSV in Excel, accessibility, load", "Maintenance + eng.", "Signed acceptance, no critical defects"],
    ["Email (optional)", "Mail server, recipients, send authorization", "IT + business", "Monitored test sends"],
  ];
  s.addTable(gates.map((r, i) => r.map((c, j) => ({ text: c, options: {
    bold: i === 0 || j === 0, color: i === 0 ? HEX.lt1 : (j === 0 ? HEX.dk2 : HEX.dk1), fill: { color: i === 0 ? HEX.dk2 : (i % 2 ? "FFFFFF" : "F5F9FA") }, fontSize: 12, valign: "middle" } }))),
    { x: 0.6, y: 1.6, w: 12.1, colW: [2.1, 4.7, 2.0, 3.3], rowH: 0.5, border: { type: "solid", color: "D5E0E3", pt: 0.75 }, margin: [0.03, 0.08, 0.03, 0.08] });
  s.addNotes("These are acceptance gates, not a delivery date. Each needs an owner and evidence. The most urgent technical item is the Python runtime: version 3.10 reached end of support on 1 October 2026, so production must use a supported version and the tests must be re-run on it. The current built-in Python web server is fine for a local pilot but is documented as unsuitable for production.");

  // ---------- 17. Decisions ----------
  s = content("Decisions needed", "Four business rules to agree before building", "Path to production");
  [["Multi-bin stock", "If one part sits in several bins, which bin is reserved and used, and how are transfers recorded?"],
   ["Backdated work", "Can completion be recorded for an earlier date? How far back, in which time zone, and who approves?"],
   ["Emergency work", "Who can override stock or approval checks in a breakdown, and what is the deadline for review afterwards?"],
   ["Corrections", "How is a wrong record reversed, and what happens to stock, history and orders? Today nothing is ever deleted."]]
    .forEach(([h, b], i) => {
      const x = 0.6 + (i % 2) * 6.15, y = 1.75 + Math.floor(i / 2) * 2.45;
      card(s, x, y, 5.95, 2.2);
      s.addText(h, { x: x + 0.35, y: y + 0.3, w: 5.3, h: 0.5, fontSize: 20, bold: true, color: C.accent1, margin: 0, isTextBox: true });
      s.addText(b, { x: x + 0.35, y: y + 0.9, w: 5.3, h: 1.1, fontSize: 15, color: C.accent5, margin: 0, valign: "top", isTextBox: true });
    });
  s.addNotes("These were deliberately not built on guesswork, because each one changes stock, history and approvals. Options: agree the rules and build them, or explicitly leave them out of the first release.");

  // ---------- 18. Roadmap ----------
  s = content("Proposed rollout", "A staged path from demo to adoption", "Path to production");
  [["NOW", "Manager review", "Walkthrough on the demo copy; agree owners and success measures"],
   ["NEXT", "One-line pilot", "Count real stock for one line; replace demo values; train users"],
   ["THEN", "Harden", "Supported runtime, hosting design, security review, backup policy"],
   ["RELEASE", "Go live", "User acceptance sign-off, monitored service, support owner"]]
    .forEach(([k, h, b], i) => {
      const x = 0.6 + i * 3.08;
      s.addShape(pres.shapes.OVAL, { x: x + 0.05, y: 1.9, w: 0.7, h: 0.7, fill: { color: i === 0 ? C.accent1 : C.background1 }, line: { color: HEX.accent1, width: 2 } });
      s.addText(String(i + 1), { x: x + 0.05, y: 1.9, w: 0.7, h: 0.7, fontSize: 20, bold: true, color: i === 0 ? C.background1 : C.accent1, align: "center", valign: "middle", margin: 0, isTextBox: true });
      if (i < 3) s.addShape(pres.shapes.LINE, { x: x + 0.85, y: 2.25, w: 2.13, h: 0, line: { color: HEX.accent2, width: 2, dashType: "dash" } });
      card(s, x, 2.9, 2.85, 2.9);
      s.addText(k, { x: x + 0.25, y: 3.05, w: 2.4, h: 0.35, fontSize: 12, bold: true, color: C.accent1, charSpacing: 2, margin: 0, isTextBox: true });
      s.addText(h, { x: x + 0.25, y: 3.45, w: 2.4, h: 0.5, fontSize: 20, bold: true, color: C.text2, margin: 0, isTextBox: true });
      s.addText(b, { x: x + 0.25, y: 4.0, w: 2.4, h: 1.6, fontSize: 14, color: C.accent5, margin: 0, valign: "top", isTextBox: true });
    });
  s.addText("Move to the next stage when the current one meets its agreed acceptance criteria. No calendar dates are promised here.", { x: 0.6, y: 6.15, w: 12.1, h: 0.5, fontSize: 13, italic: true, color: C.accent5, margin: 0, isTextBox: true });
  s.addNotes("Suggested pilot measures: share of replacements recorded with full traceability, stock-count accuracy against a physical count for the pilot line, and operator feedback on usability. Agree these before promising savings or a launch date.");


  // ---------- Cost comparison (inputs mirror docs/budget/MachineCare_Cost_Comparison.xlsx) ----------
  const B = { licence: 50, users: 62, install: 10000, rate: 40, dataHrs: 80, trainHrs: 1, hardHrs: 160, secReview: 8000, hosting: 1200, supportHrs: 4 };
  const shared = B.rate * (B.dataHrs + B.trainHrs * B.users);
  const vendorYear = (y) => B.licence * B.users * 12 + (y === 1 ? B.install + shared : 0);
  const inHouseOnce = B.rate * B.hardHrs + B.secReview;
  const inHouseYear = (y) => B.hosting + B.supportHrs * 52 * B.rate + (y === 1 ? inHouseOnce + shared : 0);
  const cum = (f) => [1, 2, 3, 4, 5].map((y) => [1, 2, 3, 4, 5].slice(0, y).reduce((a, k) => a + f(k), 0));
  const vCum = cum(vendorYear), mCum = cum(inHouseYear);
  const usd = (n) => "$" + Math.round(n).toLocaleString("en-US");
  const perUser = (B.hosting + B.supportHrs * 52 * B.rate) / B.users / 12;

  s = content("Budget · 5-year view", "MachineCare costs about a third of the outside system", "Path to production");
  s.addChart(pres.charts.BAR, [
    { name: "Outside vendor", labels: ["Year 1", "Year 2", "Year 3", "Year 4", "Year 5"], values: vCum },
    { name: "MachineCare (in-house)", labels: ["Year 1", "Year 2", "Year 3", "Year 4", "Year 5"], values: mCum },
  ], { x: 0.6, y: 1.65, w: 7.5, h: 4.95, barDir: "col", barGrouping: "clustered", barGapWidthPct: 60,
    chartColors: [HEX.accent4, HEX.accent1], showLegend: true, legendPos: "b", legendFontSize: 12, legendFontFace: "+mn-lt",
    showTitle: true, title: "Cumulative cost (US$)", titleFontSize: 14, titleColor: HEX.dk2, titleFontFace: "+mn-lt",
    showValue: true, dataLabelPosition: "outEnd", dataLabelFontSize: 10, dataLabelColor: HEX.dk2, dataLabelFormatCode: "$#,##0,\"k\"", dataLabelFontFace: "+mn-lt",
    valAxisLabelFormatCode: "$#,##0,\"k\"", valAxisLabelColor: HEX.accent5, catAxisLabelColor: HEX.dk2, valAxisLabelFontSize: 11, catAxisLabelFontSize: 12,
    catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt",
    valGridLine: { color: "E3EAED", size: 0.75 }, catGridLine: { style: "none" } });
  [["Outside vendor · 5 years", usd(vCum[4]), `$${B.licence}/user/month × ${B.users} users + ${usd(B.install)} installation`, C.accent4],
   ["MachineCare · 5 years", usd(mCum[4]), "No licences: hosting, support time, one-time hardening and security review", C.accent1],
   ["Saving over 5 years", usd(vCum[4] - mCum[4]), `Running cost ≈ $${perUser.toFixed(0)} vs $${B.licence} per user per month`, C.text2]]
    .forEach(([h, v, sub, col], i) => {
      const y = 1.65 + i * 1.68;
      card(s, 8.5, y, 4.2, 1.5);
      s.addText(h, { x: 8.75, y: y + 0.12, w: 3.8, h: 0.3, fontSize: 13, bold: true, color: C.accent5, margin: 0, isTextBox: true });
      s.addText(v, { x: 8.75, y: y + 0.42, w: 3.8, h: 0.55, fontSize: 28, bold: true, color: col, margin: 0, isTextBox: true });
      s.addText(sub, { x: 8.75, y: y + 0.97, w: 3.8, h: 0.45, fontSize: 11, color: C.accent5, margin: 0, isTextBox: true });
    });
  s.addText("Vendor figures: the quote received. MachineCare figures: planning assumptions (next slide), editable in docs/budget/MachineCare_Cost_Comparison.xlsx.",
    { x: 0.6, y: 6.68, w: 12.1, h: 0.3, fontSize: 10, italic: true, color: C.accent5, margin: 0, isTextBox: true });
  s.addNotes(`Outside vendor: ${B.users} licences at $${B.licence} per user per month is ${usd(B.licence * B.users * 12)} a year, plus the ${usd(B.install)} one-time installation. Year 1 is ${usd(vendorYear(1))} including ${usd(shared)} of our own time for stock counts and training, which we need with either option. Five-year total ${usd(vCum[4])}. MachineCare: no licence fees. Year 1 is ${usd(inHouseYear(1))} (hardening, deployment and an independent security review, plus the same data and training effort); then about ${usd(inHouseYear(2))} a year for hosting and an internal owner's support time. Five-year total ${usd(mCum[4])}, a saving of about ${usd(vCum[4] - mCum[4])}. The vendor price includes their support and updates; with MachineCare we carry that responsibility ourselves, which is why support hours are budgeted every year. Replace the yellow assumptions in the spreadsheet with our real labour rate and quotes before approval.`);

  s = content("Budget · what MachineCare needs", "Budget plan to run MachineCare here", "Path to production");
  const brow = (a, b, c, d) => [a, b, c, d];
  const budget = [
    brow("Item", "Basis (assumption)", "Year 1", "Each later year"),
    brow("Production hardening & deployment", `${B.hardHrs} h × $${B.rate}/h`, usd(B.rate * B.hardHrs), "—"),
    brow("Independent security review", "External quote needed", usd(B.secReview), "—"),
    brow("Stock count & data validation", `${B.dataHrs} h × $${B.rate}/h (needed with either option)`, usd(B.rate * B.dataHrs), "—"),
    brow("Training", `${B.users} people × ${B.trainHrs} h × $${B.rate}/h (either option)`, usd(B.rate * B.trainHrs * B.users), "—"),
    brow("Server / VM hosting & backup storage", "Small internal VM + off-host backups", usd(B.hosting), usd(B.hosting)),
    brow("Support, patching & small changes", `${B.supportHrs} h/week × 52 × $${B.rate}/h`, usd(B.supportHrs * 52 * B.rate), usd(B.supportHrs * 52 * B.rate)),
    brow("Licences", `0 × ${B.users} users`, "$0", "$0"),
    brow("Total", "", usd(inHouseYear(1)), usd(inHouseYear(2))),
  ];
  s.addTable(budget.map((r, i) => r.map((c, j) => ({ text: c, options: {
    bold: i === 0 || i === budget.length - 1 || j === 0, color: i === 0 ? HEX.lt1 : HEX.dk1,
    fill: { color: i === 0 ? HEX.dk2 : i === budget.length - 1 ? "E1F2EF" : (i % 2 ? "FFFFFF" : "F5F9FA") },
    align: j >= 2 ? "right" : "left", fontSize: 13, valign: "middle" } }))),
    { x: 0.6, y: 1.65, w: 8.1, colW: [2.9, 2.9, 1.15, 1.15], rowH: 0.5, border: { type: "solid", color: "D5E0E3", pt: 0.75 }, margin: [0.03, 0.08, 0.03, 0.08] });
  card(s, 9.0, 1.65, 3.7, 4.5);
  s.addText("Before approval", { x: 9.25, y: 1.85, w: 3.3, h: 0.4, fontSize: 17, bold: true, color: C.accent1, margin: 0, isTextBox: true });
  s.addText([
    { text: "Replace the $40/h rate with our real loaded labour cost", options: { bullet: true, breakLine: true } },
    { text: "Get a real quote for the security review and hosting", options: { bullet: true, breakLine: true } },
    { text: "Name one internal owner for support (the vendor price includes theirs)", options: { bullet: true, breakLine: true } },
    { text: "Confirm the vendor quote covers updates, support and data migration", options: { bullet: true } },
  ], { x: 9.25, y: 2.35, w: 3.3, h: 3.6, fontSize: 13, color: C.accent5, paraSpaceAfter: 8, margin: 0, valign: "top", isTextBox: true });
  s.addText("All MachineCare amounts are planning assumptions, not quotes. Editable model: docs/budget/MachineCare_Cost_Comparison.xlsx.",
    { x: 0.6, y: 6.68, w: 12.1, h: 0.3, fontSize: 10, italic: true, color: C.accent5, margin: 0, isTextBox: true });
  s.addNotes(`Year 1 for MachineCare is ${usd(inHouseYear(1))}; each later year about ${usd(inHouseYear(2))}. The biggest unknowns are our internal hourly rate and the security review quote. Stock counting and training are needed whichever system we choose, so they appear in both totals. The main trade-off: a vendor provides support and updates; with MachineCare an internal owner does, which is budgeted at ${B.supportHrs} hours a week.`);

  // ---------- 19. Ask ----------
  s = pres.addSlide({ masterName: "DARK", sectionTitle: "Path to production" });
  s.addText("THE DECISION", { placeholder: "kicker" });
  s.addText("Approve a focused validation pilot", { placeholder: "title" });
  [["Choose one validated line", "Where we count real stock and run the full workflow"], ["Name a data owner and an IT reviewer", "Maintenance and IT/security owners for the production gates"], ["Agree acceptance measures", "Traceability, stock accuracy and operator usability"]]
    .forEach(([h, b], i) => {
      const y = 2.3 + i * 1.3;
      s.addShape(pres.shapes.OVAL, { x: 0.6, y, w: 0.8, h: 0.8, fill: { color: C.accent1 }, line: { type: "none" } });
      s.addText(String(i + 1), { x: 0.6, y, w: 0.8, h: 0.8, fontSize: 24, bold: true, color: C.background1, align: "center", valign: "middle", margin: 0, isTextBox: true });
      s.addText([{ text: h, options: { bold: true, color: C.background1, fontSize: 22, breakLine: true } }, { text: b, options: { color: C.accent6, fontSize: 15 } }],
        { x: 1.7, y: y - 0.05, w: 7.5, h: 1.0, margin: 0, valign: "middle", isTextBox: true });
    });
  s.addImage({ path: SHOT("technician_mobile"), x: 10.2, y: 1.4, w: 1.9, h: 1.9 * 900 / 430, altText: "MachineCare on a phone-sized screen" });
  s.addText("Also works on a phone", { x: 9.9, y: 5.5, w: 2.5, h: 0.4, fontSize: 12, color: C.accent6, align: "center", margin: 0, isTextBox: true });
  s.addText("A working local pilot today. A controlled release after validation.", { x: 0.6, y: 6.4, w: 9, h: 0.5, fontSize: 16, italic: true, color: C.accent2, margin: 0, isTextBox: true });
  s.addNotes("Close with three concrete requests. Do not commit to a production date until the gates have owners and scope.");

  // ---------- 20-21. Appendix ----------
  pres.addSection({ title: "Appendix" });
  const tbl = (title, kicker, data, notes) => {
    const a = content(kicker, title, "Appendix");
    a.addTable(data.map((r, i) => r.map((c, j) => ({ text: c, options: { bold: i === 0, color: i === 0 ? HEX.lt1 : HEX.dk1, fill: { color: i === 0 ? HEX.dk2 : (i % 2 ? "FFFFFF" : "F5F9FA") }, fontSize: 12, align: j === 3 ? "center" : "left", valign: "middle" } }))),
      { x: 0.6, y: 1.6, w: 12.1, colW: [3.6, 2.8, 4.3, 1.4], rowH: 0.42, border: { type: "solid", color: "D5E0E3", pt: 0.75 }, margin: [0.03, 0.08, 0.03, 0.08] });
    a.addNotes(notes);
  };
  tbl("DIMM press component reference", "Appendix A", [["Component", "Manufacturer", "Supplied identifier", "Per DIMM"],
    ["Load cell", "Delta Transducers", "Serial 2511231 (not a part number)", "5"], ["Finger cylinder", "Airtac", "HFD12X50", "4"], ["Vertical cylinder", "Airtac", "HLQ12X50S", "5"],
    ["Solenoid valve", "Airtac", "7V110-6", "10"], ["Tray cylinder", "Airtac", "TCL25X20S", "2"], ["Tray clamp cylinder", "Unknown", "HLS16X20SAS", "4"],
    ["Finger reed switch sensor", "Airtac", "DMSH A11DW", "8"], ["Vertical reed switch sensor", "Airtac", "D-M98W", "10"], ["Flag sensor", "Panasonic", "PM-T45", "8"], ["Photoelectric sensor", "Panasonic", "CX-441", "12"]],
    "References exactly as supplied by maintenance. Spare quantities in the demo are illustrative and separate from installed quantities.");
  tbl("AOI component reference", "Appendix B", [["Component", "Manufacturer", "Supplied identifier", "Per AOI"],
    ["TM robot", "TM (as supplied)", "Model not supplied", "1"], ["Small light curtain", "PILZ", "PSEN op113H-s-30-030", "4"], ["Large light curtain", "PILZ", "PESN op113H-s-30-075", "2"],
    ["PLC PNOZ m bo.1", "PILZ", "Ident-772104", "1"], ["Tower light", "Unknown", "ASTLF-110-4-5FT-CM", "2"], ["Switching power supply", "Unknown", "s-120-24", "1"], ["Control box", "VEVOR", "Serial 240108586510146", "1"]],
    "Identifiers kept verbatim pending nameplate confirmation. Catalog entries for safety components are not an inspection or certification.");

  const file = path.join(OUT, "MachineCare_Manager_Review_Final.pptx");
  await pres.writeFile({ fileName: file });
  if (APPLY_THEME) await require(APPLY_THEME).applyTheme(file, THEME);
  console.log("wrote", file);
})();
