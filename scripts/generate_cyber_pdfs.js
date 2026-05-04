const fs = require("fs");
const path = require("path");

const ROOT = path.join(__dirname, "..");
const SUBMISSIONS_DIR = path.join(ROOT, "data", "submissions");

const pdfSpecs = [
  {
    file_name: "company-description.pdf",
    file_type: "pdf",
    category: "company_description",
    description: "Company description and cyber exposure overview",
    title: "Company Description"
  },
  {
    file_name: "overall-status.pdf",
    file_type: "pdf",
    category: "overall_status",
    description: "Overall cyber underwriting status summary",
    title: "Overall Status"
  }
];

for (const folderName of fs.readdirSync(SUBMISSIONS_DIR).sort()) {
  const folderPath = path.join(SUBMISSIONS_DIR, folderName);
  const metadataPath = path.join(folderPath, "metadata.json");

  if (!fs.existsSync(metadataPath)) {
    continue;
  }

  const metadata = JSON.parse(fs.readFileSync(metadataPath, "utf8"));

  for (const spec of pdfSpecs) {
    const createdAt = metadata.updated_at || metadata.file_created_at;
    const lines =
      spec.category === "company_description"
        ? buildCompanyDescription(metadata)
        : buildOverallStatus(metadata);

    fs.writeFileSync(path.join(folderPath, spec.file_name), createPdf(spec.title, lines));

    const existing = metadata.documents.find((document) => document.file_name === spec.file_name);
    const documentMetadata = {
      file_name: spec.file_name,
      file_type: spec.file_type,
      category: spec.category,
      file_created_at: createdAt,
      received_at: metadata.received_at,
      description: spec.description
    };

    if (existing) {
      Object.assign(existing, documentMetadata);
    } else {
      metadata.documents.push(documentMetadata);
    }
  }

  fs.writeFileSync(metadataPath, `${JSON.stringify(metadata, null, 2)}\n`);
}

function buildCompanyDescription(metadata) {
  const applicant = metadata.applicant || {};
  const coverage = metadata.coverage || {};

  return [
    metadata.title,
    "",
    `Insured: ${applicant.insured_name}`,
    `Industry: ${applicant.industry}`,
    `Location: ${applicant.location}`,
    `Annual Revenue: ${formatCurrency(applicant.annual_revenue)}`,
    `Employees: ${applicant.employee_count}`,
    `Records: ${formatNumber(applicant.records_count)}`,
    "",
    "Technology Profile",
    applicant.technology_profile,
    "",
    "Cyber Coverage Requested",
    ...(coverage.lines_requested || []).map((line) => `- ${line}`),
    `Effective Date: ${coverage.requested_effective_date}`,
    `Retention Requested: ${coverage.retention_requested}`
  ];
}

function buildOverallStatus(metadata) {
  const controls = metadata.security_controls || {};

  return [
    metadata.title,
    "",
    `Submission ID: ${metadata.id}`,
    `Line of Business: ${metadata.line_of_business}`,
    `Status: ${metadata.status}`,
    `File Created At: ${metadata.file_created_at}`,
    `Received At: ${metadata.received_at}`,
    `Updated At: ${metadata.updated_at}`,
    "",
    "Security Controls",
    ...Object.entries(controls).map(([key, value]) => `- ${labelize(key)}: ${value}`),
    "",
    "Risk Flags",
    ...(metadata.risk_flags || []).map((flag) => `- ${flag}`),
    "",
    "Open Questions",
    ...(metadata.open_questions || []).map((question) => `- ${question}`)
  ];
}

function createPdf(title, lines) {
  const escapedLines = lines.flatMap((line) => wrapLine(String(line || ""), 92));
  const textCommands = [
    "BT",
    "/F1 18 Tf",
    "72 740 Td",
    `(${escapePdfText(title)}) Tj`,
    "/F1 10 Tf",
    "0 -28 Td",
    ...escapedLines.map((line) => `(${escapePdfText(line)}) Tj 0 -15 Td`),
    "ET"
  ].join("\n");

  const objects = [
    "<< /Type /Catalog /Pages 2 0 R >>",
    "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
    "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
    "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    `<< /Length ${Buffer.byteLength(textCommands)} >>\nstream\n${textCommands}\nendstream`
  ];

  let pdf = "%PDF-1.4\n";
  const offsets = [0];

  objects.forEach((object, index) => {
    offsets.push(Buffer.byteLength(pdf));
    pdf += `${index + 1} 0 obj\n${object}\nendobj\n`;
  });

  const xrefOffset = Buffer.byteLength(pdf);
  pdf += `xref\n0 ${objects.length + 1}\n`;
  pdf += "0000000000 65535 f \n";
  offsets.slice(1).forEach((offset) => {
    pdf += `${String(offset).padStart(10, "0")} 00000 n \n`;
  });
  pdf += `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xrefOffset}\n%%EOF\n`;

  return Buffer.from(pdf, "utf8");
}

function wrapLine(line, maxLength) {
  if (line.length <= maxLength) {
    return [line];
  }

  const words = line.split(" ");
  const wrapped = [];
  let current = "";

  for (const word of words) {
    if (`${current} ${word}`.trim().length > maxLength) {
      wrapped.push(current);
      current = word;
    } else {
      current = `${current} ${word}`.trim();
    }
  }

  if (current) {
    wrapped.push(current);
  }

  return wrapped;
}

function escapePdfText(value) {
  return value.replace(/\\/g, "\\\\").replace(/\(/g, "\\(").replace(/\)/g, "\\)");
}

function labelize(value) {
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function formatCurrency(value) {
  return typeof value === "number" ? `$${value.toLocaleString("en-US")}` : "TBD";
}

function formatNumber(value) {
  return typeof value === "number" ? value.toLocaleString("en-US") : "TBD";
}
