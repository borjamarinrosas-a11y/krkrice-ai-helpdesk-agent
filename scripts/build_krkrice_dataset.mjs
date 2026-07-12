import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const root = process.cwd();
const outputDir = path.join(root, "outputs", "krkrice_it_dataset");
const csvDir = path.join(outputDir, "csv");
const previewDir = path.join(outputDir, "previews");
await fs.mkdir(csvDir, { recursive: true });
await fs.mkdir(previewDir, { recursive: true });

let seed = 20260710;
function rand() {
  seed = (seed * 1664525 + 1013904223) >>> 0;
  return seed / 4294967296;
}
const pick = (arr) => arr[Math.floor(rand() * arr.length)];
const pad = (n, w = 3) => String(n).padStart(w, "0");
const isoDate = (date) => date.toISOString().slice(0, 10);
const excelDate = (s) => new Date(`${s}T12:00:00Z`);

function csvEscape(value) {
  if (value === null || value === undefined) return "";
  const text = value instanceof Date ? isoDate(value) : String(value);
  return /[",\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
}
async function writeCsv(name, headers, rows) {
  const body = [headers, ...rows].map((r) => r.map(csvEscape).join(",")).join("\n") + "\n";
  await fs.writeFile(path.join(csvDir, `${name}.csv`), body, "utf8");
}

const departments = [
  ["Export Sales", 17], ["Logistics", 15], ["Warehouse", 23], ["Quality Control", 8],
  ["Finance", 10], ["Procurement", 7], ["Operations", 10], ["HR & Administration", 5], ["IT", 5],
];
const firstNames = ["Aleksandra", "Anna", "Aisha", "Carlos", "Daniel", "Ewa", "Fatima", "Hanna", "Jakub", "Jan", "Karolina", "Katarzyna", "Liam", "Lina", "Marek", "Marta", "Mateusz", "Maya", "Michał", "Nadia", "Noah", "Ola", "Piotr", "Sara", "Sofia", "Tomasz", "Yuki", "Zofia"];
const lastNames = ["Alvarez", "Bąk", "Chen", "Dąbrowski", "Garcia", "Jankowski", "Kaczmarek", "Kowalski", "Krawczyk", "Lewandowski", "Lis", "Mazur", "Nowak", "O'Connor", "Pawlak", "Rahman", "Sikora", "Szymański", "Tanaka", "Wójcik", "Zając", "Zieliński"];
const jobTitles = {
  "Export Sales": ["Export Sales Executive", "Account Manager", "Sales Operations Coordinator"],
  Logistics: ["Logistics Coordinator", "Shipment Planner", "Customs Documentation Specialist"],
  Warehouse: ["Warehouse Operator", "Inventory Controller", "Shift Supervisor"],
  "Quality Control": ["Quality Analyst", "Lab Technician", "Certification Specialist"],
  Finance: ["Financial Analyst", "Accounts Payable Specialist", "Controller"],
  Procurement: ["Procurement Specialist", "Supplier Manager", "Buyer"],
  Operations: ["Operations Planner", "Production Coordinator", "Process Analyst"],
  "HR & Administration": ["HR Specialist", "Office Administrator", "People Operations Coordinator"],
  IT: ["IT Support Specialist", "Systems Administrator", "Security Analyst"],
};
const managers = {};
const employees = [];
let employeeNumber = 1;
for (const [department, count] of departments) {
  for (let j = 0; j < count; j++) {
    const id = `EMP-${pad(employeeNumber)}`;
    let first = firstNames[(employeeNumber * 7 + j) % firstNames.length];
    let last = lastNames[(employeeNumber * 11 + j * 3) % lastNames.length];
    const name = `${first} ${last}`;
    if (j === 0) managers[department] = id;
    const location = department === "Warehouse" || department === "Operations" || department === "Quality Control" ? "Kraków Operations Centre" : (employeeNumber % 8 === 0 ? "Remote - Poland" : "Kraków Headquarters");
    const hireYear = 2017 + (employeeNumber % 9);
    const hireMonth = 1 + (employeeNumber % 12);
    const hireDay = 1 + (employeeNumber % 25);
    employees.push([
      id, name, `${first}.${last}`.toLowerCase().replaceAll("ą", "a").replaceAll("ć", "c").replaceAll("ę", "e").replaceAll("ł", "l").replaceAll("ń", "n").replaceAll("ó", "o").replaceAll("ś", "s").replaceAll("ź", "z").replaceAll("ż", "z").replaceAll("'", "") + "@krkrice.example",
      department, j === 0 ? `Head of ${department}` : pick(jobTitles[department]), location,
      j === 0 ? "" : managers[department], `202${employeeNumber % 10}`, "Active",
      `${hireYear}-${pad(hireMonth, 2)}-${pad(hireDay, 2)}`, employeeNumber % 9 === 0 ? "Polish, English" : "English",
    ]);
    employeeNumber++;
  }
}

const systemsSeed = [
  ["SYS-001", "Microsoft 365", "Productivity", "SaaS", "Critical", "IT", "Microsoft", "SSO + MFA", "99.9%", "Aisha Rahman"],
  ["SYS-002", "RiceFlow ERP", "ERP", "SaaS", "Critical", "Finance", "Fictional vendor", "SSO + MFA", "99.9%", "Aisha Rahman"],
  ["SYS-003", "GrainTrack WMS", "Warehouse", "Cloud", "Critical", "Warehouse", "Fictional vendor", "SSO", "99.9%", "Aisha Rahman"],
  ["SYS-004", "ExportHub CRM", "CRM", "SaaS", "High", "Export Sales", "Fictional vendor", "SSO", "99.5%", "Aisha Rahman"],
  ["SYS-005", "CertiRice", "Quality", "Web app", "High", "Quality Control", "Fictional vendor", "SSO", "99.5%", "Aisha Rahman"],
  ["SYS-006", "ShipLink", "Logistics", "SaaS", "High", "Logistics", "Fictional vendor", "Username + MFA", "99.5%", "Aisha Rahman"],
  ["SYS-007", "FortiClient VPN", "Network", "Hybrid", "Critical", "IT", "Fortinet", "SSO + MFA", "99.9%", "Mateusz Kowalski"],
  ["SYS-008", "Entra ID", "Identity", "SaaS", "Critical", "IT", "Microsoft", "MFA", "99.99%", "Sofia Alvarez"],
  ["SYS-009", "Jira Service Management", "Helpdesk", "SaaS", "High", "IT", "Atlassian", "SSO", "99.9%", "Sofia Alvarez"],
  ["SYS-010", "SharePoint Online", "Document Management", "SaaS", "High", "IT", "Microsoft", "SSO + MFA", "99.9%", "Aisha Rahman"],
  ["SYS-011", "Microsoft Teams", "Collaboration", "SaaS", "High", "IT", "Microsoft", "SSO + MFA", "99.9%", "Liam O'Connor"],
  ["SYS-012", "Power BI", "Analytics", "SaaS", "Medium", "Finance", "Microsoft", "SSO + MFA", "99.5%", "Aisha Rahman"],
  ["SYS-013", "Zebra Print Service", "Printing", "On-premises", "High", "Warehouse", "Zebra", "Service account", "99.5%", "Liam O'Connor"],
  ["SYS-014", "Warehouse Wi-Fi", "Network", "On-premises", "Critical", "IT", "Cisco", "Certificate", "99.9%", "Mateusz Kowalski"],
  ["SYS-015", "Endpoint Manager", "Device Management", "SaaS", "High", "IT", "Microsoft", "SSO + MFA", "99.9%", "Liam O'Connor"],
  ["SYS-016", "CrowdStrike Endpoint", "Security", "SaaS", "Critical", "IT", "CrowdStrike", "SSO + MFA", "99.9%", "Yuki Tanaka"],
  ["SYS-017", "DocuSign", "Electronic Signature", "SaaS", "Medium", "HR & Administration", "DocuSign", "SSO + MFA", "99.5%", "Aisha Rahman"],
  ["SYS-018", "HR People Portal", "HRIS", "SaaS", "High", "HR & Administration", "Fictional vendor", "SSO + MFA", "99.5%", "Aisha Rahman"],
  ["SYS-019", "Finance Banking Portal", "Finance", "SaaS", "Critical", "Finance", "Synthetic Bank", "Hardware token + MFA", "99.9%", "Yuki Tanaka"],
  ["SYS-020", "KRkRice Status Page", "Monitoring", "SaaS", "High", "IT", "Fictional vendor", "SSO", "99.9%", "Mateusz Kowalski"],
];

const assetTypes = ["Windows Laptop", "Windows Laptop", "Warehouse Tablet", "Barcode Scanner", "Label Printer", "Monitor", "Docking Station"];
const models = {
  "Windows Laptop": ["Dell Latitude 5450", "Lenovo ThinkPad T14", "HP EliteBook 840"],
  "Warehouse Tablet": ["Zebra ET45", "Samsung Tab Active4 Pro"],
  "Barcode Scanner": ["Zebra TC52", "Honeywell CT45"],
  "Label Printer": ["Zebra ZT411", "Zebra ZD421"], Monitor: ["Dell P2422H", "LG 27BN65Q"], "Docking Station": ["Dell WD19S", "Lenovo USB-C Dock Gen 2"],
};
const assets = [];
for (let i = 1; i <= 80; i++) {
  let type = assetTypes[(i * 5) % assetTypes.length];
  const employee = employees[(i * 13) % employees.length];
  if (["Warehouse Tablet", "Barcode Scanner", "Label Printer"].includes(type)) {
    const warehouseEmployees = employees.filter((e) => e[3] === "Warehouse");
    employee.splice(0, 0);
    const wh = warehouseEmployees[i % warehouseEmployees.length];
    assets.push([`AST-${pad(i)}`, type, pick(models[type]), `KRK${String(260000 + i * 73)}`, i % 9 === 0 ? "Shared" : wh[0], "Kraków Operations Centre", i % 17 === 0 ? "Repair" : "In service", `202${1 + (i % 5)}-${pad(1 + (i % 12), 2)}-${pad(1 + (i % 24), 2)}`, `202${4 + (i % 4)}-${pad(1 + (i % 12), 2)}-${pad(1 + (i % 24), 2)}`, type.includes("Scanner") || type.includes("Tablet") ? "Android 13" : "Firmware managed"]);
  } else {
    assets.push([`AST-${pad(i)}`, type, pick(models[type]), `KRK${String(260000 + i * 73)}`, i % 11 === 0 ? "Shared" : employee[0], employee[5], i % 19 === 0 ? "Repair" : "In service", `202${1 + (i % 5)}-${pad(1 + (i % 12), 2)}-${pad(1 + (i % 24), 2)}`, `202${4 + (i % 4)}-${pad(1 + (i % 12), 2)}-${pad(1 + (i % 24), 2)}`, type === "Windows Laptop" ? "Windows 11 Enterprise" : "Not applicable"]);
  }
}

const agents = [
  ["AGT-001", "Sofia Alvarez", "Senior IT Support Specialist", "Identity & Access", "Tier 2", "Madrid", "Spanish, English", "08:00-16:00 CET", "SUP-4", "Active"],
  ["AGT-002", "Liam O'Connor", "Workplace Technology Specialist", "Hardware & Devices", "Tier 1", "Dublin", "English", "09:00-17:00 GMT/BST", "SUP-2", "Active"],
  ["AGT-003", "Aisha Rahman", "Business Applications Support Analyst", "Business Applications", "Tier 2", "London", "English, Bengali", "09:00-17:00 GMT/BST", "SUP-3", "Active"],
  ["AGT-004", "Mateusz Kowalski", "Network and Cloud Support Engineer", "Network & Cloud", "Tier 3", "Warsaw", "Polish, English", "08:00-16:00 CET", "SUP-6", "Active"],
  ["AGT-005", "Yuki Tanaka", "Security Support Analyst", "Security", "Security", "Tokyo", "Japanese, English", "09:00-17:00 JST", "SUP-5", "Active"],
];

const kbTopics = [
  ["Reset an expired password", "Identity & Access", "SYS-008", "Sofia Alvarez", "Verify identity; use self-service reset; sign out and in; never share passwords."],
  ["Refresh VPN credentials after password change", "Network & VPN", "SYS-007", "Mateusz Kowalski", "Disconnect VPN; remove cached credentials; sign in with the new password; escalate lockouts."],
  ["Enroll a replacement MFA device", "Identity & Access", "SYS-008", "Sofia Alvarez", "Verify identity using an approved method; revoke old device; enroll replacement; confirm sign-in."],
  ["Unlock a user account", "Identity & Access", "SYS-008", "Sofia Alvarez", "Check lockout source; verify identity; unlock; require password reset if compromise is suspected."],
  ["Connect to warehouse Wi-Fi", "Network & VPN", "SYS-014", "Mateusz Kowalski", "Confirm managed device; renew certificate; forget and reconnect; check access-point health."],
  ["Troubleshoot slow office Wi-Fi", "Network & VPN", "SYS-014", "Mateusz Kowalski", "Check outage dashboard; capture location and time; test wired connection; escalate widespread impact."],
  ["Replace a damaged laptop", "Hardware", "SYS-015", "Liam O'Connor", "Record asset ID and damage; back up if safe; obtain approval; issue replacement; update inventory."],
  ["Fix a docking station display issue", "Hardware", "SYS-015", "Liam O'Connor", "Reseat cables; power-cycle dock; update firmware; test alternate cable and monitor."],
  ["Restore a Zebra label printer", "Hardware", "SYS-013", "Liam O'Connor", "Check media and queue; restart print service; calibrate; escalate hardware faults."],
  ["Re-enroll a barcode scanner", "Hardware", "SYS-003", "Liam O'Connor", "Confirm asset ID; connect to managed Wi-Fi; enroll in device manager; sync WMS profile."],
  ["Request RiceFlow ERP access", "Business Applications", "SYS-002", "Aisha Rahman", "Require manager and data-owner approval; apply least privilege; record approval in ticket."],
  ["Resolve RiceFlow invoice export errors", "Business Applications", "SYS-002", "Aisha Rahman", "Validate date and entity; retry export; capture error ID; escalate data-integrity issues."],
  ["Fix GrainTrack inventory sync", "Business Applications", "SYS-003", "Aisha Rahman", "Check service status; identify affected warehouse; preserve transaction IDs; avoid manual duplication."],
  ["Request ExportHub CRM access", "Business Applications", "SYS-004", "Aisha Rahman", "Obtain manager approval; assign role template; validate customer-data scope; confirm access."],
  ["Upload a CertiRice certificate", "Business Applications", "SYS-005", "Aisha Rahman", "Validate file type and shipment ID; check permissions; retry; preserve compliance record."],
  ["Troubleshoot ShipLink tracking", "Business Applications", "SYS-006", "Aisha Rahman", "Check carrier status; validate container reference; refresh integration; avoid duplicate bookings."],
  ["Restore a deleted SharePoint file", "Collaboration", "SYS-010", "Aisha Rahman", "Check recycle bin and retention; restore correct version; confirm permissions; escalate legal hold."],
  ["Fix Teams microphone problems", "Collaboration", "SYS-011", "Liam O'Connor", "Select correct input; check OS permission; test call; update driver; try browser client."],
  ["Report a phishing message", "Security", "SYS-016", "Yuki Tanaka", "Do not click; use report-phishing button; preserve message; reset credentials if entered; escalate immediately."],
  ["Respond to a suspicious login", "Security", "SYS-008", "Yuki Tanaka", "Revoke sessions; reset password; verify MFA; preserve logs; open security incident."],
  ["Handle a lost company device", "Security", "SYS-015", "Yuki Tanaka", "Record asset and last location; remote lock; notify Security and manager; assess data exposure."],
  ["Request software installation", "Service Request", "SYS-015", "Liam O'Connor", "Confirm business need and license; verify approved catalog; deploy through Endpoint Manager."],
  ["Onboard a new employee", "Service Request", "SYS-008", "Sofia Alvarez", "Require HR record and manager; create account; assign baseline access and device; verify MFA."],
  ["Offboard an employee", "Security", "SYS-008", "Yuki Tanaka", "Confirm HR request; disable access at effective time; revoke sessions; preserve data; recover assets."],
  ["Declare a major IT incident", "Incident Management", "SYS-020", "Mateusz Kowalski", "Confirm multi-user impact; appoint incident lead; publish status; track timeline; conduct review."],
];
const kb = kbTopics.map((x, i) => [`KB-${pad(i + 1)}`, x[0], x[1], x[2], "Published", "2026-06-30", x[3], x[4], `password|vpn|hardware|application|security|${x[1].toLowerCase().replaceAll(" ", "-")}`]);

const templates = [
  ["VPN authentication fails after password change", "Network & VPN", "SYS-007", "Medium", "AGT-004", "KB-002", "User cannot reach internal resources remotely.", "Clear cached VPN credentials and authenticate with the new password."],
  ["MFA prompt never arrives", "Identity & Access", "SYS-008", "High", "AGT-001", "KB-003", "User is blocked from all SSO applications.", "Verify identity and re-register the approved MFA method."],
  ["Account locked after repeated sign-in", "Identity & Access", "SYS-008", "Medium", "AGT-001", "KB-004", "User cannot sign in to company systems.", "Identify lockout source, verify identity, and unlock the account."],
  ["Warehouse scanner will not sync", "Hardware", "SYS-003", "High", "AGT-002", "KB-010", "Picking activity is delayed for one operator.", "Reconnect managed Wi-Fi, re-enroll the scanner, and sync its WMS profile."],
  ["Label printer produces blank labels", "Hardware", "SYS-013", "High", "AGT-002", "KB-009", "Outbound pallet labeling is delayed.", "Reload media, calibrate printer, and restart the managed print queue."],
  ["Laptop screen flickers through dock", "Hardware", "SYS-015", "Low", "AGT-002", "KB-008", "Employee can work using the laptop display.", "Update dock firmware and replace the display cable."],
  ["RiceFlow invoice export fails", "Business Applications", "SYS-002", "High", "AGT-003", "KB-012", "Finance cannot complete the daily invoice batch.", "Correct the entity filter and retry; preserve the error ID for escalation."],
  ["GrainTrack stock is not updating", "Business Applications", "SYS-003", "Critical", "AGT-003", "KB-013", "Multiple warehouse users see stale inventory.", "Pause manual adjustments and restore the inventory integration."],
  ["ExportHub access requested for new salesperson", "Service Request", "SYS-004", "Low", "AGT-003", "KB-014", "New employee needs CRM access.", "Obtain manager approval and assign the standard sales role."],
  ["CertiRice rejects quality certificate", "Business Applications", "SYS-005", "Medium", "AGT-003", "KB-015", "Certificate cannot be attached to a shipment.", "Convert to an approved PDF format and validate the shipment identifier."],
  ["ShipLink cannot find container", "Business Applications", "SYS-006", "Medium", "AGT-003", "KB-016", "Logistics cannot view carrier tracking.", "Validate the container reference and refresh the carrier integration."],
  ["Deleted pricing workbook in SharePoint", "Collaboration", "SYS-010", "High", "AGT-003", "KB-017", "Sales team needs a recently deleted file.", "Restore the correct retained version from the SharePoint recycle bin."],
  ["Teams microphone not detected", "Collaboration", "SYS-011", "Low", "AGT-002", "KB-018", "User cannot speak during calls.", "Select the correct device and restore OS microphone permission."],
  ["Suspicious invoice email received", "Security", "SYS-016", "Critical", "AGT-005", "KB-019", "Potential phishing attempt targeting Finance.", "Preserve and report the message; investigate links and affected credentials."],
  ["Unexpected sign-in from another country", "Security", "SYS-008", "Critical", "AGT-005", "KB-020", "Possible account compromise.", "Revoke sessions, reset credentials, and open a security incident."],
  ["Company laptop lost during travel", "Security", "SYS-015", "Critical", "AGT-005", "KB-021", "Managed device may be exposed.", "Remote lock the device and initiate the security response procedure."],
  ["Approved software installation request", "Service Request", "SYS-015", "Low", "AGT-002", "KB-022", "Employee requires an approved productivity tool.", "Validate the license and deploy through Endpoint Manager."],
  ["New employee IT onboarding", "Service Request", "SYS-008", "Medium", "AGT-001", "KB-023", "New starter requires baseline equipment and access.", "Provision baseline account, MFA, groups, and assigned device."],
  ["Employee offboarding request", "Security", "SYS-008", "High", "AGT-005", "KB-024", "Departing employee access must end on schedule.", "Disable access, revoke sessions, preserve data, and recover assets."],
  ["Warehouse Wi-Fi unavailable", "Network & VPN", "SYS-014", "Critical", "AGT-004", "KB-025", "Multiple warehouse devices are offline.", "Declare an incident, fail over connectivity, and publish status updates."],
];

const tickets = [];
const statuses = ["Resolved", "Resolved", "Resolved", "Resolved", "Resolved", "Closed", "Closed", "Waiting for customer", "In progress", "Open"];
for (let i = 1; i <= 100; i++) {
  const t = templates[(i * 7) % templates.length];
  const employee = employees[(i * 17) % employees.length];
  const relatedAssets = assets.filter((a) => a[4] === employee[0]);
  const assetId = ["Hardware", "Network & VPN", "Security"].includes(t[1]) && relatedAssets.length ? relatedAssets[0][0] : "";
  const created = new Date(Date.UTC(2025 + (i > 72 ? 1 : 0), (i * 3) % 12, 1 + (i * 11) % 27));
  const status = statuses[i % statuses.length];
  const resolved = ["Resolved", "Closed"].includes(status) ? new Date(created.getTime() + (4 + (i % 70)) * 3600000) : null;
  const confidence = Math.round((0.69 + (i % 29) / 100) * 100) / 100;
  const security = t[1] === "Security";
  const autoEligible = !security && !["Critical"].includes(t[3]) && confidence >= 0.8;
  const resolutionSource = ["Resolved", "Closed"].includes(status) ? (i % 4 === 0 ? "Human-edited AI draft" : i % 3 === 0 ? "AI draft approved" : "Human response") : "";
  const feedback = ["Resolved", "Closed"].includes(status) ? (i % 9 === 0 ? "Corrected" : "Approved") : "Pending";
  tickets.push([
    `TKT-${pad(i, 4)}`, `Historical: ${t[0]}`, t[1], t[2], t[3], status,
    isoDate(created), resolved ? isoDate(resolved) : "", employee[0], employee[1], employee[3], assetId,
    t[4], agents.find((a) => a[0] === t[4])[1], t[5], t[6],
    ["Resolved", "Closed"].includes(status) ? t[7] : "", confidence, autoEligible ? "Yes" : "No",
    security ? "Mandatory security escalation" : (t[3] === "Critical" ? "Major incident review" : confidence < 0.8 ? "Low confidence" : "None"),
    resolutionSource, feedback, `Synthetic ticket ${i}; no real customer or personal data.`,
  ]);
}

const headers = {
  employees: ["employee_id", "full_name", "email", "department", "job_title", "location", "manager_employee_id", "cost_centre", "employment_status", "hire_date", "languages"],
  assets: ["asset_id", "asset_type", "model", "serial_number", "assigned_employee_id", "location", "status", "purchase_date", "warranty_end", "operating_system"],
  systems: ["system_id", "system_name", "category", "hosting_model", "criticality", "business_owner", "vendor", "authentication", "availability_target", "support_owner"],
  agents: ["agent_id", "full_name", "role", "specialty", "support_tier", "location", "languages", "working_hours", "jira_profile_issue", "status"],
  knowledge: ["article_id", "title", "category", "system_id", "status", "last_reviewed", "owner", "resolution_summary", "tags"],
  tickets: ["ticket_id", "summary", "category", "system_id", "priority", "status", "created_date", "resolved_date", "requester_employee_id", "requester_name", "requester_department", "asset_id", "assigned_agent_id", "assigned_agent_name", "knowledge_article_id", "business_impact", "resolution", "ai_confidence", "auto_resolution_eligible", "escalation_reason", "resolution_source", "human_feedback", "data_classification_note"],
};

await writeCsv("employees", headers.employees, employees);
await writeCsv("assets", headers.assets, assets);
await writeCsv("systems", headers.systems, systemsSeed);
await writeCsv("agents", headers.agents, agents);
await writeCsv("knowledge_articles", headers.knowledge, kb);
await writeCsv("historical_tickets", headers.tickets, tickets);

const workbook = Workbook.create();
const sheetNames = ["Overview", "Employees", "Assets", "Systems", "Agents", "Knowledge Base", "Historical Tickets", "Data Dictionary"];
for (const name of sheetNames) workbook.worksheets.add(name);
const navy = "#17324D", green = "#2E7D5B", paleGreen = "#E7F3EC", gold = "#D5A021", paleGold = "#FFF4D6", light = "#F3F6F8", border = "#CBD5E1", red = "#B42318";

function colName(n) {
  let s = "";
  while (n > 0) { n--; s = String.fromCharCode(65 + n % 26) + s; n = Math.floor(n / 26); }
  return s;
}
function titleBlock(sheet, title, subtitle, cols) {
  sheet.showGridLines = false;
  const titleRange = sheet.getRange(`A1:${colName(cols)}1`);
  titleRange.merge();
  sheet.getRange("A1").values = [[title]];
  titleRange.format = { fill: navy, font: { bold: true, color: "#FFFFFF", size: 18 }, rowHeight: 30, verticalAlignment: "center" };
  const subtitleRange = sheet.getRange(`A2:${colName(cols)}2`);
  subtitleRange.merge();
  sheet.getRange("A2").values = [[subtitle]];
  subtitleRange.format = { fill: paleGreen, font: { italic: true, color: navy, size: 10 }, rowHeight: 24, verticalAlignment: "center" };
}
function dataSheet(name, title, subtitle, header, rows, dateCols = [], numberFormats = {}) {
  const sheet = workbook.worksheets.getItem(name);
  const cols = header.length;
  titleBlock(sheet, title, subtitle, cols);
  sheet.getRangeByIndexes(3, 0, 1, cols).values = [header];
  const converted = rows.map((row) => row.map((v, idx) => dateCols.includes(idx) && v ? excelDate(v) : v));
  sheet.getRangeByIndexes(4, 0, converted.length, cols).values = converted;
  const headerRange = sheet.getRangeByIndexes(3, 0, 1, cols);
  headerRange.format = { fill: green, font: { bold: true, color: "#FFFFFF" }, rowHeight: 24, wrapText: true, verticalAlignment: "center" };
  const body = sheet.getRangeByIndexes(4, 0, converted.length, cols);
  body.format = { font: { color: "#1F2937", size: 10 }, verticalAlignment: "top", borders: { insideHorizontal: { style: "thin", color: border } } };
  for (const c of dateCols) sheet.getRangeByIndexes(4, c, converted.length, 1).format.numberFormat = "yyyy-mm-dd";
  for (const [c, fmt] of Object.entries(numberFormats)) sheet.getRangeByIndexes(4, Number(c), converted.length, 1).format.numberFormat = fmt;
  const table = sheet.tables.add(`A4:${colName(cols)}${4 + converted.length}`, true, `${name.replaceAll(" ", "")}Table`);
  table.style = "TableStyleMedium4";
  sheet.freezePanes.freezeRows(4);
  headerRange.format.autofitColumns();
  body.format.autofitColumns();
  for (let c = 0; c < cols; c++) {
    const range = sheet.getRangeByIndexes(3, c, converted.length + 1, 1);
    const current = range.format.columnWidth;
    range.format.columnWidth = Math.min(Math.max(current || 12, 11), c === 1 || header[c].includes("summary") || header[c].includes("resolution") || header[c].includes("impact") || header[c].includes("note") ? 34 : 22);
  }
  return sheet;
}

dataSheet("Employees", "KRkRice Synthetic Employees", "100 invented employees for IT service-management testing. All addresses use the reserved .example domain.", headers.employees, employees, [9]);
dataSheet("Assets", "KRkRice Synthetic IT Assets", "80 invented devices linked to employees or shared operational locations.", headers.assets, assets, [7, 8]);
dataSheet("Systems", "KRkRice IT Systems", "20 applications and infrastructure services used in the fictional rice-export business.", headers.systems, systemsSeed);
dataSheet("Agents", "KRkRice Mock Helpdesk Agents", "Five routing personas corresponding to the mock Jira profile records SUP-2 through SUP-6.", headers.agents, agents);
dataSheet("Knowledge Base", "KRkRice Synthetic Knowledge Base", "25 approved troubleshooting and service-request articles for retrieval-augmented responses.", headers.knowledge, kb, [5]);
const ticketSheet = dataSheet("Historical Tickets", "KRkRice Historical IT Tickets", "100 synthetic tickets containing triage labels, routing targets, outcomes, confidence, and human feedback.", headers.tickets, tickets, [6, 7], {17: "0%"});
ticketSheet.getRange(`E5:E104`).conditionalFormats.add("containsText", { text: "Critical", format: { fill: "#FEE4E2", font: { color: red, bold: true } } });
ticketSheet.getRange(`F5:F104`).conditionalFormats.add("containsText", { text: "Resolved", format: { fill: paleGreen, font: { color: green } } });
ticketSheet.getRange(`R5:R104`).conditionalFormats.add("colorScale", { colors: ["#FEE4E2", paleGold, paleGreen], thresholds: ["min", "50%", "max"] });

const overview = workbook.worksheets.getItem("Overview");
titleBlock(overview, "KRkRice IT Service Dataset", "Synthetic showcase dataset — fictional company, people, devices, systems, tickets, and operational records.", 10);
overview.getRange("A4:B11").values = [
  ["Dataset", "Record count"], ["Employees", null], ["Assets", null], ["Systems", null], ["Helpdesk agents", null], ["Knowledge articles", null], ["Historical tickets", null], ["Resolved / closed tickets", null],
];
overview.getRange("B5").formulas = [["=COUNTA('Employees'!$A$5:$A$104)"]];
overview.getRange("B6").formulas = [["=COUNTA('Assets'!$A$5:$A$84)"]];
overview.getRange("B7").formulas = [["=COUNTA('Systems'!$A$5:$A$24)"]];
overview.getRange("B8").formulas = [["=COUNTA('Agents'!$A$5:$A$9)"]];
overview.getRange("B9").formulas = [["=COUNTA('Knowledge Base'!$A$5:$A$29)"]];
overview.getRange("B10").formulas = [["=COUNTA('Historical Tickets'!$A$5:$A$104)"]];
overview.getRange("B11").formulas = [["=COUNTIF('Historical Tickets'!$F$5:$F$104,\"Resolved\")+COUNTIF('Historical Tickets'!$F$5:$F$104,\"Closed\")"]];
overview.getRange("A4:B4").format = { fill: green, font: { bold: true, color: "#FFFFFF" } };
overview.getRange("A5:B11").format = { fill: "#FFFFFF", borders: { insideHorizontal: { style: "thin", color: border }, outside: { style: "thin", color: border } } };
overview.getRange("B5:B11").format = { font: { bold: true, color: navy }, numberFormat: "#,##0", horizontalAlignment: "right" };
const purposeHeader = overview.getRange("D4:J4"); purposeHeader.merge(); overview.getRange("D4").values = [["Purpose and safe-use notes"]];
purposeHeader.format = { fill: gold, font: { bold: true, color: "#FFFFFF" }, rowHeight: 24 };
const purposeBody = overview.getRange("D5:J11"); purposeBody.merge(); overview.getRange("D5").values = [["This dataset is designed for an AI helpdesk showcase: triage, retrieval, response drafting, routing, escalation, evaluation, and feedback learning. Every person, email, ticket, device, and business record is invented. Do not treat mock agent profiles as real Jira accounts. Security tickets are deliberately excluded from automatic resolution."]];
purposeBody.format = { fill: paleGold, font: { color: navy }, wrapText: true, verticalAlignment: "top", borders: { preset: "outside", style: "thin", color: gold } };
overview.getRange("A14:J14").merge(); overview.getRange("A14").values = [["Relational keys"]]; overview.getRange("A14").format = { fill: navy, font: { bold: true, color: "#FFFFFF" } };
overview.getRange("A15:J19").values = [
  ["Tickets.requester_employee_id", "→", "Employees.employee_id", "Tickets.asset_id", "→", "Assets.asset_id", "Tickets.system_id", "→", "Systems.system_id", ""],
  ["Tickets.assigned_agent_id", "→", "Agents.agent_id", "Tickets.knowledge_article_id", "→", "Knowledge Base.article_id", "Assets.assigned_employee_id", "→", "Employees.employee_id", ""],
  ["Knowledge Base.system_id", "→", "Systems.system_id", "Employees.manager_employee_id", "→", "Employees.employee_id", "Agents.jira_profile_issue", "→", "Jira SUP issues", ""],
  ["Reserved email domain", "", "krkrice.example", "Generation seed", "", "20260710", "Snapshot date", "", "2026-07-10", ""],
  ["CSV exports", "", "outputs/krkrice_it_dataset/csv", "Workbook", "", "krkrice_it_service_dataset.xlsx", "Classification", "", "Synthetic", ""],
];
overview.getRange("A15:J19").format = { fill: light, font: { size: 10, color: "#334155" }, borders: { insideHorizontal: { style: "thin", color: border } } };
overview.getRange("A:A").format.columnWidth = 31; overview.getRange("B:B").format.columnWidth = 15; overview.getRange("C:C").format.columnWidth = 28;
for (const c of ["D","E","F","G","H","I","J"]) overview.getRange(`${c}:${c}`).format.columnWidth = 18;
overview.getRange("A1:J1").format = { fill: navy, font: { bold: true, color: "#FFFFFF", size: 18 }, rowHeight: 30, verticalAlignment: "center" };
overview.getRange("A2:J2").format = { fill: paleGreen, font: { italic: true, color: navy, size: 10 }, rowHeight: 24, verticalAlignment: "center" };
purposeHeader.format = { fill: gold, font: { bold: true, color: "#FFFFFF" }, rowHeight: 24 };
purposeBody.format = { fill: paleGold, font: { color: navy }, wrapText: true, verticalAlignment: "top", borders: { preset: "outside", style: "thin", color: gold } };
overview.freezePanes.freezeRows(2);

const dict = workbook.worksheets.getItem("Data Dictionary");
const dictionary = [
  ["Table", "Primary key", "Important foreign keys", "Description"],
  ["Employees", "employee_id", "manager_employee_id → Employees", "Synthetic workforce used as ticket requesters and asset owners."],
  ["Assets", "asset_id", "assigned_employee_id → Employees", "Synthetic IT equipment inventory."],
  ["Systems", "system_id", "None", "Applications, platforms, and infrastructure services."],
  ["Agents", "agent_id", "jira_profile_issue → SUP project", "Fictional routing personas; not real Jira user accounts."],
  ["Knowledge Base", "article_id", "system_id → Systems", "Approved synthetic guidance used for grounded responses."],
  ["Historical Tickets", "ticket_id", "requester_employee_id, asset_id, system_id, assigned_agent_id, knowledge_article_id", "Labeled examples for evaluation, retrieval, and feedback workflows."],
];
titleBlock(dict, "Data Dictionary", "Table-level definitions and relationships for developers and reviewers.", 4);
dict.getRange(`A4:D${3 + dictionary.length}`).values = dictionary;
dict.getRange("A4:D4").format = { fill: green, font: { bold: true, color: "#FFFFFF" } };
dict.getRange(`A5:D${3 + dictionary.length}`).format = { borders: { insideHorizontal: { style: "thin", color: border } }, wrapText: true, verticalAlignment: "top" };
dict.getRange("A:D").format.autofitColumns(); dict.getRange("A:A").format.columnWidth = 23; dict.getRange("B:B").format.columnWidth = 23; dict.getRange("C:C").format.columnWidth = 48; dict.getRange("D:D").format.columnWidth = 52;
dict.freezePanes.freezeRows(4);

const inspect = await workbook.inspect({ kind: "table", range: "Overview!A1:J19", include: "values,formulas", tableMaxRows: 20, tableMaxCols: 10, maxChars: 8000 });
console.log(inspect.ndjson);
const errors = await workbook.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A", options: { useRegex: true, maxResults: 300 }, summary: "final formula error scan", maxChars: 4000 });
console.log(errors.ndjson);

for (const name of sheetNames) {
  const sheet = workbook.worksheets.getItem(name);
  const used = sheet.getUsedRange(true);
  const preview = await workbook.render({ sheetName: name, range: used.address, scale: name === "Historical Tickets" ? 0.55 : 0.8, format: "png" });
  await fs.writeFile(path.join(previewDir, `${name.replaceAll(" ", "_").toLowerCase()}.png`), new Uint8Array(await preview.arrayBuffer()));
}

const outputPath = path.join(outputDir, "krkrice_it_service_dataset.xlsx");
const xlsx = await SpreadsheetFile.exportXlsx(workbook);
await xlsx.save(outputPath);

const employeeIds = new Set(employees.map((r) => r[0]));
const assetIds = new Set(assets.map((r) => r[0]));
const systemIds = new Set(systemsSeed.map((r) => r[0]));
const agentIds = new Set(agents.map((r) => r[0]));
const kbIds = new Set(kb.map((r) => r[0]));
const broken = [];
for (const t of tickets) {
  if (!employeeIds.has(t[8])) broken.push(`${t[0]} requester`);
  if (t[11] && !assetIds.has(t[11])) broken.push(`${t[0]} asset`);
  if (!systemIds.has(t[3])) broken.push(`${t[0]} system`);
  if (!agentIds.has(t[12])) broken.push(`${t[0]} agent`);
  if (!kbIds.has(t[14])) broken.push(`${t[0]} knowledge`);
}
const summary = { outputPath, counts: { employees: employees.length, assets: assets.length, systems: systemsSeed.length, agents: agents.length, knowledge_articles: kb.length, historical_tickets: tickets.length }, broken_relationships: broken, csvDir, previewDir };
await fs.writeFile(path.join(outputDir, "validation_summary.json"), JSON.stringify(summary, null, 2));
console.log(JSON.stringify(summary, null, 2));
