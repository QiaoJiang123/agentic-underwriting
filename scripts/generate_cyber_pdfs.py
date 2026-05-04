import json
from pathlib import Path
from textwrap import wrap


ROOT = Path(__file__).resolve().parent.parent
SUBMISSIONS_DIR = ROOT / "data" / "submissions"

PDF_SPECS = [
    {
        "file_name": "company-description.pdf",
        "file_type": "pdf",
        "category": "company_description",
        "description": "Company description and cyber exposure overview",
        "title": "Company Description",
    },
    {
        "file_name": "overall-status.pdf",
        "file_type": "pdf",
        "category": "overall_status",
        "description": "Overall cyber underwriting status summary",
        "title": "Overall Status",
    },
]


def main():
    for folder_path in sorted(SUBMISSIONS_DIR.iterdir()):
        metadata_path = folder_path / "metadata.json"
        if not metadata_path.exists():
            continue

        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

        for spec in PDF_SPECS:
            created_at = metadata.get("updated_at") or metadata.get("file_created_at")
            lines = (
                build_company_description(metadata)
                if spec["category"] == "company_description"
                else build_overall_status(metadata)
            )
            (folder_path / spec["file_name"]).write_bytes(create_pdf(spec["title"], lines))

            document_metadata = {
                "file_name": spec["file_name"],
                "file_type": spec["file_type"],
                "category": spec["category"],
                "file_created_at": created_at,
                "received_at": metadata.get("received_at"),
                "description": spec["description"],
            }

            existing = next(
                (
                    document
                    for document in metadata.get("documents", [])
                    if document.get("file_name") == spec["file_name"]
                ),
                None,
            )
            if existing:
                existing.update(document_metadata)
            else:
                metadata.setdefault("documents", []).append(document_metadata)

        metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")


def build_company_description(metadata):
    applicant = metadata.get("applicant", {})
    coverage = metadata.get("coverage", {})

    return [
        metadata.get("title"),
        "",
        f"Insured: {applicant.get('insured_name')}",
        f"Industry: {applicant.get('industry')}",
        f"Location: {applicant.get('location')}",
        f"Annual Revenue: {format_currency(applicant.get('annual_revenue'))}",
        f"Employees: {applicant.get('employee_count')}",
        f"Records: {format_number(applicant.get('records_count'))}",
        "",
        "Technology Profile",
        applicant.get("technology_profile"),
        "",
        "Cyber Coverage Requested",
        *[f"- {line}" for line in coverage.get("lines_requested", [])],
        f"Effective Date: {coverage.get('requested_effective_date')}",
        f"Retention Requested: {coverage.get('retention_requested')}",
    ]


def build_overall_status(metadata):
    controls = metadata.get("security_controls", {})

    return [
        metadata.get("title"),
        "",
        f"Submission ID: {metadata.get('id')}",
        f"Line of Business: {metadata.get('line_of_business')}",
        f"Status: {metadata.get('status')}",
        f"File Created At: {metadata.get('file_created_at')}",
        f"Received At: {metadata.get('received_at')}",
        f"Updated At: {metadata.get('updated_at')}",
        "",
        "Security Controls",
        *[f"- {labelize(key)}: {value}" for key, value in controls.items()],
        "",
        "Risk Flags",
        *[f"- {flag}" for flag in metadata.get("risk_flags", [])],
        "",
        "Open Questions",
        *[f"- {question}" for question in metadata.get("open_questions", [])],
    ]


def create_pdf(title, lines):
    escaped_lines = []
    for line in lines:
        escaped_lines.extend(wrap(str(line or ""), width=92) or [""])

    text_commands = "\n".join(
        [
            "BT",
            "/F1 18 Tf",
            "72 740 Td",
            f"({escape_pdf_text(title)}) Tj",
            "/F1 10 Tf",
            "0 -28 Td",
            *[f"({escape_pdf_text(line)}) Tj 0 -15 Td" for line in escaped_lines],
            "ET",
        ]
    )

    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        f"<< /Length {len(text_commands.encode('utf-8'))} >>\nstream\n{text_commands}\nendstream",
    ]

    pdf = "%PDF-1.4\n"
    offsets = [0]
    for index, pdf_object in enumerate(objects, start=1):
        offsets.append(len(pdf.encode("utf-8")))
        pdf += f"{index} 0 obj\n{pdf_object}\nendobj\n"

    xref_offset = len(pdf.encode("utf-8"))
    pdf += f"xref\n0 {len(objects) + 1}\n"
    pdf += "0000000000 65535 f \n"
    for offset in offsets[1:]:
        pdf += f"{offset:010d} 00000 n \n"
    pdf += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n"

    return pdf.encode("utf-8")


def escape_pdf_text(value):
    return str(value).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def labelize(value):
    return " ".join(part.capitalize() for part in str(value).split("_"))


def format_currency(value):
    return f"${value:,.0f}" if isinstance(value, (int, float)) else "TBD"


def format_number(value):
    return f"{value:,}" if isinstance(value, (int, float)) else "TBD"


if __name__ == "__main__":
    main()

