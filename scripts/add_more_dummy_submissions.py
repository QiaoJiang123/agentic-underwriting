import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
SUBMISSION_DIR = DATA_DIR / "submissions"
SEARCH_METADATA_PATH = DATA_DIR / "metadata.json"


TAXONOMY = {
    "major_categories": {
        "submission": "Submission",
        "company_profile": "Company Profile",
        "cyber_security": "Cyber Security",
        "loss_history": "Loss History",
        "financial": "Financial",
        "coverage_terms": "Coverage Terms",
        "vendor_risk": "Vendor Risk",
        "compliance": "Compliance",
        "communication": "Communication",
        "underwriting_review": "Underwriting Review",
    },
    "note": "document_types and major_categories are arrays because one document can support multiple underwriting uses.",
}


DOCUMENT_DEFINITIONS = [
    (
        "cyber-application.txt",
        "cyber_application",
        "submission",
        ["cyber_application", "submission_form"],
        ["submission", "cyber_security"],
        "Cyber application and submission form responses",
    ),
    (
        "ransomware-supplemental-application.txt",
        "ransomware_supplemental_application",
        "submission",
        ["ransomware_supplemental_application"],
        ["submission", "cyber_security"],
        "Ransomware supplemental application",
    ),
    (
        "prior-cyber-insurance-policy.txt",
        "prior_cyber_insurance_policy",
        "coverage_terms",
        ["prior_cyber_insurance_policy", "policy_form"],
        ["coverage_terms"],
        "Prior cyber insurance policy and expiring coverage terms",
    ),
    (
        "loss-runs-claims-history.txt",
        "loss_runs",
        "loss_history",
        ["loss_runs", "claims_history"],
        ["loss_history"],
        "Loss runs and cyber claims history",
    ),
    (
        "financial-information-revenue-breakdown.txt",
        "financial_information",
        "financial",
        ["financial_information", "revenue_breakdown"],
        ["financial", "company_profile"],
        "Financial information and revenue breakdown",
    ),
    (
        "it-security-controls-questionnaire.txt",
        "it_security_controls_questionnaire",
        "cyber_security",
        ["it_security_controls_questionnaire", "security_questionnaire"],
        ["cyber_security"],
        "IT and security controls questionnaire",
    ),
    (
        "mfa-edr-backup-documentation.txt",
        "mfa_documentation",
        "cyber_security",
        ["mfa_documentation", "edr_documentation", "backup_documentation"],
        ["cyber_security"],
        "MFA, EDR, and backup control documentation",
    ),
    (
        "incident-response-plan.txt",
        "incident_response_plan",
        "cyber_security",
        ["incident_response_plan"],
        ["cyber_security"],
        "Incident response plan and escalation workflow",
    ),
    (
        "vendor-security-assessment.txt",
        "vendor_security_assessment",
        "vendor_risk",
        ["vendor_security_assessment", "third_party_risk_assessment"],
        ["vendor_risk", "cyber_security"],
        "Vendor and third-party security assessment",
    ),
    (
        "compliance-documents.txt",
        "compliance_documentation",
        "compliance",
        ["compliance_documentation"],
        ["compliance", "cyber_security"],
        "Relevant compliance documentation such as SOC 2, HIPAA, PCI, or equivalent evidence",
    ),
]


SUBMISSIONS = [
    {
        "id": "006-quantum-retail-pharmacy",
        "title": "Quantum Retail Pharmacy",
        "insured_name": "Quantum Retail Pharmacy Inc.",
        "industry": "Regional retail pharmacy chain",
        "location": "Columbus, OH",
        "revenue": 41200000,
        "employees": 238,
        "records": 640000,
        "technology": "Pharmacy management system, e-prescribing, POS terminals, loyalty platform, Microsoft 365",
        "status": "In Review",
        "received_at": "2026-05-01T11:18:00-04:00",
        "file_created_at": "2026-05-01T09:47:00-04:00",
        "effective": "2026-06-15",
        "coverage": ["Cyber liability", "Privacy breach response", "PCI fines and assessments"],
        "limits": {"cyber_liability": "$5,000,000", "privacy_breach_response": "$3,000,000", "pci": "$1,000,000"},
        "retention": "$50,000",
        "controls": {
            "mfa": "Enabled for email, VPN, pharmacy system admins, and privileged users",
            "edr": "SentinelOne on corporate endpoints and pharmacy workstations",
            "backup": "Daily backups with monthly restore tests",
            "patching": "Critical patches within 10 days",
            "security_training": "Quarterly training for store managers and annual training for all employees",
        },
        "risk_flags": ["PHI and payment card exposure", "Distributed retail locations", "Vendor-hosted pharmacy platform"],
        "open_questions": ["Confirm PCI scan cadence.", "Request most recent HIPAA risk assessment.", "Clarify e-prescribing vendor incident notification obligations."],
        "claims": [
            {
                "claim_id": "CLM-QUANTUM-2024-001",
                "loss_date": "2024-03-14",
                "reported_date": "2024-03-15",
                "status": "closed",
                "claim_type": "privacy_incident",
                "coverage_area": "privacy_liability",
                "severity": "moderate",
                "amount_paid": 28500,
                "amount_reserved": 0,
                "cause": "Misdirected prescription delivery notification exposed limited patient information.",
                "description": "Notification and legal review expenses were paid.",
                "recovery_status": "resolved",
            }
        ],
        "keywords": ["pharmacy", "phi", "pci", "retail", "e-prescribing"],
    },
    {
        "id": "007-lakeview-university",
        "title": "Lakeview University",
        "insured_name": "Lakeview University",
        "industry": "Higher education",
        "location": "Madison, WI",
        "revenue": 186000000,
        "employees": 1120,
        "records": 420000,
        "technology": "Student information system, learning management system, research network, donor CRM, Microsoft 365",
        "status": "Referral Needed",
        "received_at": "2026-05-02T14:02:00-04:00",
        "file_created_at": "2026-05-02T10:28:00-04:00",
        "effective": "2026-07-01",
        "coverage": ["Cyber liability", "Privacy breach response", "Network business interruption"],
        "limits": {"cyber_liability": "$10,000,000", "privacy_breach_response": "$5,000,000", "business_interruption": "$5,000,000"},
        "retention": "$100,000",
        "controls": {
            "mfa": "Enabled for faculty, staff, and remote access; student MFA rollout in progress",
            "edr": "CrowdStrike on managed endpoints; research lab exceptions under review",
            "backup": "Daily backups with semiannual restore tests",
            "patching": "Critical patches within 20 days with research network exceptions",
            "security_training": "Annual employee training plus phishing simulations",
        },
        "risk_flags": ["Open research network", "Student MFA rollout in progress", "Large privacy record count"],
        "open_questions": ["Confirm research network segmentation.", "Request student MFA rollout timeline.", "Clarify ransomware tabletop testing."],
        "claims": [
            {
                "claim_id": "CLM-LAKE-2025-001",
                "loss_date": "2025-01-28",
                "reported_date": "2025-01-29",
                "status": "open",
                "claim_type": "credential_compromise",
                "coverage_area": "incident_response",
                "severity": "high",
                "amount_paid": 48000,
                "amount_reserved": 95000,
                "cause": "Compromised student account used to access cloud storage.",
                "description": "Forensic review and notification assessment remain open.",
                "recovery_status": "active_review",
            }
        ],
        "keywords": ["university", "student records", "research network", "mfa rollout", "education"],
    },
    {
        "id": "008-summit-fintech-payments",
        "title": "Summit Fintech Payments",
        "insured_name": "Summit Fintech Payments LLC",
        "industry": "Payment processing and fintech services",
        "location": "Charlotte, NC",
        "revenue": 73500000,
        "employees": 310,
        "records": 2100000,
        "technology": "Payment gateway, API platform, Kubernetes, AWS, fraud analytics, customer support portal",
        "status": "In Review",
        "received_at": "2026-05-03T09:35:00-04:00",
        "file_created_at": "2026-05-03T08:16:00-04:00",
        "effective": "2026-06-20",
        "coverage": ["Cyber liability", "Technology E&O", "PCI fines and assessments"],
        "limits": {"cyber_liability": "$10,000,000", "technology_eo": "$5,000,000", "pci": "$2,000,000"},
        "retention": "$150,000",
        "controls": {
            "mfa": "Phishing-resistant MFA for privileged users and SSO MFA for all employees",
            "edr": "CrowdStrike complete coverage with 24/7 MDR",
            "backup": "Immutable backups with monthly restore tests",
            "patching": "Critical patches within 7 days",
            "security_training": "Quarterly secure coding and phishing simulations",
        },
        "risk_flags": ["High transaction dependency", "API aggregation exposure", "Large records count"],
        "open_questions": ["Request PCI ROC summary.", "Confirm API rate limit monitoring.", "Clarify customer contract limitation of liability."],
        "claims": [
            {
                "claim_id": "CLM-SUMMIT-2025-001",
                "loss_date": "2025-06-03",
                "reported_date": "2025-06-04",
                "status": "closed",
                "claim_type": "service_outage",
                "coverage_area": "technology_errors_omissions",
                "severity": "moderate",
                "amount_paid": 56000,
                "amount_reserved": 0,
                "cause": "Gateway routing error caused intermittent transaction failures.",
                "description": "Customer credits and defense review were paid.",
                "recovery_status": "resolved",
            }
        ],
        "keywords": ["fintech", "payments", "pci", "api", "technology e&o"],
    },
    {
        "id": "009-cascade-industrial-manufacturing",
        "title": "Cascade Industrial Manufacturing",
        "insured_name": "Cascade Industrial Manufacturing Co.",
        "industry": "Industrial parts manufacturing",
        "location": "Portland, OR",
        "revenue": 128500000,
        "employees": 684,
        "records": 94000,
        "technology": "ERP, plant floor OT network, EDI with suppliers, remote vendor maintenance, Microsoft 365",
        "status": "New",
        "received_at": "2026-05-04T10:44:00-04:00",
        "file_created_at": "2026-05-04T09:05:00-04:00",
        "effective": "2026-07-10",
        "coverage": ["Cyber liability", "Dependent business interruption", "Contingent business interruption"],
        "limits": {"cyber_liability": "$5,000,000", "dependent_bi": "$3,000,000", "contingent_bi": "$2,000,000"},
        "retention": "$75,000",
        "controls": {
            "mfa": "Enabled for email, VPN, and ERP admins; vendor remote access MFA pending",
            "edr": "Microsoft Defender for Endpoint on corporate assets; OT monitoring pilot underway",
            "backup": "Daily backups with quarterly restore testing",
            "patching": "Critical corporate patches within 14 days; OT patch windows quarterly",
            "security_training": "Annual employee training",
        },
        "risk_flags": ["OT dependency", "Vendor remote access MFA pending", "EDI supplier concentration"],
        "open_questions": ["Confirm vendor remote access MFA date.", "Request OT network diagram.", "Clarify production downtime exposure."],
        "claims": [],
        "keywords": ["manufacturing", "ot", "edi", "business interruption", "vendor remote access"],
    },
    {
        "id": "010-sunrise-hospitality-group",
        "title": "Sunrise Hospitality Group",
        "insured_name": "Sunrise Hospitality Group LLC",
        "industry": "Hotel management and hospitality",
        "location": "Miami, FL",
        "revenue": 58200000,
        "employees": 412,
        "records": 310000,
        "technology": "Property management system, booking engine, guest Wi-Fi, POS terminals, loyalty data platform",
        "status": "New",
        "received_at": "2026-05-05T15:20:00-04:00",
        "file_created_at": "2026-05-05T13:48:00-04:00",
        "effective": "2026-07-15",
        "coverage": ["Cyber liability", "PCI fines and assessments", "Business interruption"],
        "limits": {"cyber_liability": "$3,000,000", "pci": "$1,000,000", "business_interruption": "$2,000,000"},
        "retention": "$50,000",
        "controls": {
            "mfa": "Enabled for corporate email and VPN; property management admin MFA scheduled",
            "edr": "Sophos on corporate endpoints and servers",
            "backup": "Daily backups with quarterly restore testing",
            "patching": "Critical patches within 15 days",
            "security_training": "Annual training plus seasonal phishing campaign",
        },
        "risk_flags": ["Guest Wi-Fi segmentation", "PCI exposure", "Property management vendor dependency"],
        "open_questions": ["Confirm guest Wi-Fi segmentation evidence.", "Request PCI SAQ.", "Clarify property management vendor incident SLA."],
        "claims": [
            {
                "claim_id": "CLM-SUNRISE-2024-001",
                "loss_date": "2024-12-11",
                "reported_date": "2024-12-12",
                "status": "closed",
                "claim_type": "payment_card_incident",
                "coverage_area": "pci_assessment",
                "severity": "moderate",
                "amount_paid": 39000,
                "amount_reserved": 0,
                "cause": "POS malware alert at one property required PCI forensic review.",
                "description": "No broad card compromise confirmed, but forensic and legal costs were paid.",
                "recovery_status": "remediated",
            }
        ],
        "keywords": ["hospitality", "hotel", "pci", "guest wifi", "property management"],
    },
]


def main():
    for item in SUBMISSIONS:
        create_submission(item)
        write_context_records(item)

    update_search_metadata()


def create_submission(item):
    folder = SUBMISSION_DIR / item["id"]
    folder.mkdir(parents=True, exist_ok=True)
    documents = []

    for definition in DOCUMENT_DEFINITIONS:
        file_name, file_type, category, document_types, major_categories, description = definition
        (folder / file_name).write_text(build_document_text(item, file_name, description), encoding="utf-8")
        documents.append(
            {
                "file_name": file_name,
                "file_type": file_type,
                "category": category,
                "document_types": document_types,
                "major_categories": major_categories,
                "file_created_at": item["file_created_at"],
                "received_at": item["received_at"],
                "description": description,
            }
        )

    metadata = {
        "id": item["id"],
        "title": item["title"],
        "line_of_business": "Cyber liability",
        "file_created_at": item["file_created_at"],
        "received_at": item["received_at"],
        "updated_at": "2026-05-19T09:00:00-04:00",
        "status": item["status"],
        "applicant": {
            "insured_name": item["insured_name"],
            "industry": item["industry"],
            "location": item["location"],
            "annual_revenue": item["revenue"],
            "employee_count": item["employees"],
            "records_count": item["records"],
            "technology_profile": item["technology"],
        },
        "coverage": {
            "lines_requested": item["coverage"],
            "requested_effective_date": item["effective"],
            "requested_limits": item["limits"],
            "retention_requested": item["retention"],
        },
        "documents": documents,
        "security_controls": item["controls"],
        "risk_flags": item["risk_flags"],
        "open_questions": item["open_questions"],
        "timeline": build_timeline(item),
        "document_taxonomy": TAXONOMY,
    }
    write_json(folder / "metadata.json", metadata)


def build_document_text(item, file_name, description):
    controls = "\n".join(f"- {label}: {value}" for label, value in item["controls"].items())
    claims = item["claims"]
    claims_text = "No cyber claims reported in the linked loss period."
    if claims:
        claims_text = "\n".join(
            f"{claim['loss_date']} | {claim['claim_type']} | {claim['status']} | paid ${claim['amount_paid']:,} | reserve ${claim['amount_reserved']:,}"
            for claim in claims
        )

    base = [
        description,
        "",
        f"Insured: {item['insured_name']}",
        f"Submission ID: {item['id']}",
        f"Industry: {item['industry']}",
        f"Revenue: ${item['revenue']:,}",
        f"Employees: {item['employees']}",
        f"Records: {item['records']:,}",
        f"Technology profile: {item['technology']}",
        "",
        "Security controls:",
        controls,
        "",
        "Claims history:",
        claims_text,
        "",
        "Risk flags:",
        *[f"- {flag}" for flag in item["risk_flags"]],
        "",
        "Open questions:",
        *[f"- {question}" for question in item["open_questions"]],
    ]

    if file_name == "financial-information-revenue-breakdown.txt":
        base.extend(["", "Revenue breakdown:", "- Core operations are the primary revenue source unless otherwise stated.", f"- Annual revenue: {item['revenue']}"])
    if file_name == "prior-cyber-insurance-policy.txt":
        base.extend(["", f"Expiring retention: {item['retention']}", "Prior carrier terms are provided for comparison only."])
    if file_name == "compliance-documents.txt":
        base.extend(["", "Compliance evidence should be reviewed for applicable regulatory or contractual control frameworks."])
    if file_name == "vendor-security-assessment.txt":
        base.extend(["", "Critical vendors should be reviewed for incident notification, recovery time, and data access controls."])

    return "\n".join(base) + "\n"


def build_timeline(item):
    return [
        {
            "date": item["file_created_at"],
            "event": "Submission file created",
            "description": "Broker prepared the cyber submission package.",
        },
        {
            "date": item["received_at"],
            "event": "Submission received",
            "description": "Cyber underwriting package received for review.",
        },
        {
            "date": "2026-05-19T09:00:00-04:00",
            "event": "Standardized evidence added",
            "description": "Cyber application, supplement, prior policy, loss runs, financials, controls, vendor, incident response, and compliance evidence added.",
        },
    ]


def write_context_records(item):
    for folder_name, key in [("guide", "guides"), ("note", "notes"), ("task", "tasks")]:
        path = DATA_DIR / folder_name / f"{item['id']}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        write_json(path, {"submission_id": item["id"], "updated_at": None, key: []})

    state_path = DATA_DIR / "states" / f"{item['id']}.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(state_path, {"submission_id": item["id"], "updated_at": None, "submitted_at": None, "stages": []})

    claims_path = DATA_DIR / "claims" / f"{item['id']}.json"
    claims_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(
        claims_path,
        {
            "submission_id": item["id"],
            "claim_system": "dummy_claims_core",
            "updated_at": "2026-05-19T09:00:00-04:00",
            "claims": item["claims"],
        },
    )


def update_search_metadata():
    metadata = json.loads(SEARCH_METADATA_PATH.read_text(encoding="utf-8"))
    existing = {
        submission["id"]: submission
        for submission in metadata.get("submissions", [])
    }
    for item in SUBMISSIONS:
        existing[item["id"]] = {
            "id": item["id"],
            "title": item["title"],
            "insured_name": item["insured_name"],
            "industry": item["industry"],
            "status": item["status"],
            "received_at": item["received_at"],
            "folder": f"data/submissions/{item['id']}",
            "keywords": item["keywords"],
        }
    metadata["generated_at"] = "2026-05-19T09:00:00-04:00"
    metadata["submissions"] = [existing[key] for key in sorted(existing)]
    write_json(SEARCH_METADATA_PATH, metadata)


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
