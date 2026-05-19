import json
import random
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DATA_ROOT = ROOT / "data"
SUBMISSIONS_DIR = DATA_ROOT / "submissions"
CLAIMS_DIR = DATA_ROOT / "claims"
SEARCH_METADATA_PATH = DATA_ROOT / "metadata.json"
BROKER_DB_PATH = DATA_ROOT / "brokers" / "brokers.json"

UPDATED_AT = "2026-05-19T12:00:00-04:00"


INDUSTRY_BUCKETS = {
    "Food Distribution / Logistics": {
        "keywords": ["food distribution", "logistics", "cold storage", "warehouse", "edi"],
        "base_claim": 52000,
    },
    "Construction": {
        "keywords": ["construction", "contracting", "subcontractor", "funds transfer"],
        "base_claim": 41000,
    },
    "Healthcare / Pharmacy": {
        "keywords": ["healthcare", "pharmacy", "phi", "hipaa", "patient records"],
        "base_claim": 85000,
    },
    "Marina / Recreation": {
        "keywords": ["marina", "recreation", "reservation platform", "customer wifi"],
        "base_claim": 38000,
    },
    "SaaS / Software": {
        "keywords": ["saas", "software", "api", "technology e&o", "soc 2"],
        "base_claim": 76000,
    },
    "Fintech / Payments": {
        "keywords": ["fintech", "payments", "pci", "api", "transaction dependency"],
        "base_claim": 96000,
    },
    "Education": {
        "keywords": ["education", "student records", "research network", "university"],
        "base_claim": 72000,
    },
    "Manufacturing / OT": {
        "keywords": ["manufacturing", "ot", "industrial", "remote access", "edi"],
        "base_claim": 69000,
    },
    "Hospitality / Retail": {
        "keywords": ["hospitality", "retail", "hotel", "ecommerce", "pos"],
        "base_claim": 49000,
    },
    "Professional Services": {
        "keywords": ["professional services", "law firm", "consulting", "managed service"],
        "base_claim": 57000,
    },
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


BROKER_ASSIGNMENTS = {
    "Food Distribution / Logistics": "brk-atlantic-risk-partners",
    "Hospitality / Retail": "brk-atlantic-risk-partners",
    "Construction": "brk-midwest-commercial-risk",
    "Manufacturing / OT": "brk-midwest-commercial-risk",
    "Healthcare / Pharmacy": "brk-harbor-specialty",
    "Education": "brk-harbor-specialty",
    "Marina / Recreation": "brk-harbor-specialty",
    "SaaS / Software": "brk-pacific-tech-risk",
    "Fintech / Payments": "brk-pacific-tech-risk",
    "Professional Services": "brk-crestline-specialty",
}


EXISTING_BUCKETS = {
    "001-acme-foods": "Food Distribution / Logistics",
    "002-northstar-contracting": "Construction",
    "003-evergreen-senior-living": "Healthcare / Pharmacy",
    "004-harborview-marina": "Marina / Recreation",
    "005-pixelwave-software": "SaaS / Software",
    "006-quantum-retail-pharmacy": "Healthcare / Pharmacy",
    "007-lakeview-university": "Education",
    "008-summit-fintech-payments": "Fintech / Payments",
    "009-cascade-industrial-manufacturing": "Manufacturing / OT",
    "010-sunrise-hospitality-group": "Hospitality / Retail",
}


NEW_COMPANIES = [
    ("011-brightpath-dental-network", "BrightPath Dental Network", "BrightPath Dental Network LLC", "Multi-site dental services organization", "Healthcare / Pharmacy", "Nashville, TN", 36400000, 420, 390000, "Practice management platform, imaging systems, patient portal, payment terminals, Microsoft 365"),
    ("012-blue-ridge-cold-chain", "Blue Ridge Cold Chain", "Blue Ridge Cold Chain Inc.", "Refrigerated logistics and cold storage", "Food Distribution / Logistics", "Roanoke, VA", 51200000, 260, 96000, "Warehouse management system, EDI ordering, fleet telematics, customer portal, Microsoft 365"),
    ("013-copperline-electrical-contractors", "Copperline Electrical Contractors", "Copperline Electrical Contractors LLC", "Commercial electrical contracting", "Construction", "Phoenix, AZ", 28700000, 118, 42000, "Project management suite, subcontractor portal, payroll system, email, mobile field devices"),
    ("014-novus-cloud-analytics", "Novus Cloud Analytics", "Novus Cloud Analytics Inc.", "B2B SaaS analytics platform", "SaaS / Software", "Austin, TX", 69000000, 305, 1250000, "Multi-tenant analytics platform, AWS, Kubernetes, API integrations, customer support portal"),
    ("015-riverbend-community-college", "Riverbend Community College", "Riverbend Community College", "Public community college", "Education", "Albany, NY", 92000000, 780, 250000, "Student information system, LMS, donor CRM, research labs, Microsoft 365"),
    ("016-sterling-machined-components", "Sterling Machined Components", "Sterling Machined Components Co.", "Precision component manufacturer", "Manufacturing / OT", "Cleveland, OH", 118000000, 540, 83000, "ERP, plant floor OT network, EDI, remote vendor maintenance, Microsoft 365"),
    ("017-pierpoint-resort-group", "Pierpoint Resort Group", "Pierpoint Resort Group LLC", "Regional resort and hotel operator", "Hospitality / Retail", "Charleston, SC", 74200000, 630, 410000, "Property management system, booking engine, guest Wi-Fi, POS terminals, loyalty platform"),
    ("018-civicpay-solutions", "CivicPay Solutions", "CivicPay Solutions Inc.", "Municipal payment processing platform", "Fintech / Payments", "Denver, CO", 84500000, 355, 1850000, "Payment gateway, ACH processing, API platform, fraud analytics, AWS"),
    ("019-harborline-yacht-services", "Harborline Yacht Services", "Harborline Yacht Services LLC", "Marina services and boat storage", "Marina / Recreation", "Annapolis, MD", 19400000, 95, 36000, "Reservation platform, POS terminals, customer Wi-Fi, maintenance scheduling, Microsoft 365"),
    ("020-evergreen-legal-advisors", "Evergreen Legal Advisors", "Evergreen Legal Advisors LLP", "Regional law firm", "Professional Services", "Seattle, WA", 62800000, 240, 580000, "Document management system, client portal, e-discovery platform, Microsoft 365, VPN"),
    ("021-meridian-specialty-clinics", "Meridian Specialty Clinics", "Meridian Specialty Clinics Inc.", "Specialty medical clinic network", "Healthcare / Pharmacy", "Minneapolis, MN", 103000000, 715, 880000, "EHR, patient portal, imaging systems, claims clearinghouse, Microsoft 365"),
    ("022-summit-grocery-distributors", "Summit Grocery Distributors", "Summit Grocery Distributors LLC", "Regional grocery distribution", "Food Distribution / Logistics", "Kansas City, MO", 67500000, 340, 120000, "Warehouse management system, EDI, fleet routing, vendor portal, Microsoft 365"),
    ("023-foundation-builders", "Foundation Builders", "Foundation Builders Inc.", "Commercial general contractor", "Construction", "Charlotte, NC", 144000000, 410, 76000, "ERP, bid management, subcontractor portal, payroll, field tablets"),
    ("024-signalforge-devops", "SignalForge DevOps", "SignalForge DevOps Inc.", "DevOps tooling SaaS", "SaaS / Software", "Raleigh, NC", 45500000, 190, 720000, "SaaS platform, CI/CD orchestration, API integrations, AWS, customer support portal"),
    ("025-northshore-prep-academy", "Northshore Prep Academy", "Northshore Prep Academy", "Private K-12 school network", "Education", "Evanston, IL", 33600000, 265, 94000, "Student information system, LMS, parent portal, donor CRM, Microsoft 365"),
    ("026-pinnacle-packaging-systems", "Pinnacle Packaging Systems", "Pinnacle Packaging Systems Co.", "Packaging equipment manufacturer", "Manufacturing / OT", "Grand Rapids, MI", 156000000, 720, 118000, "ERP, OT line controls, EDI, remote vendor support, quality management system"),
    ("027-coastline-inns", "Coastline Inns", "Coastline Inns LLC", "Limited-service hotel group", "Hospitality / Retail", "Savannah, GA", 38800000, 315, 230000, "Property management system, booking engine, guest Wi-Fi, POS, loyalty data"),
    ("028-ledgerlane-capital", "LedgerLane Capital", "LedgerLane Capital LLC", "Digital lending and payments platform", "Fintech / Payments", "Salt Lake City, UT", 126000000, 465, 2400000, "Loan origination system, payment APIs, fraud analytics, cloud data lake, customer portal"),
    ("029-cascade-adventure-parks", "Cascade Adventure Parks", "Cascade Adventure Parks Inc.", "Outdoor recreation and ticketing operator", "Marina / Recreation", "Bend, OR", 24600000, 180, 112000, "Ticketing platform, waiver system, POS terminals, customer Wi-Fi, Microsoft 365"),
    ("030-horizon-consulting-group", "Horizon Consulting Group", "Horizon Consulting Group LLC", "Management consulting firm", "Professional Services", "Chicago, IL", 91000000, 510, 330000, "Client portal, project management system, data room, Microsoft 365, SSO"),
    ("031-clearwater-pediatrics", "Clearwater Pediatrics", "Clearwater Pediatrics PA", "Pediatric clinic group", "Healthcare / Pharmacy", "Tampa, FL", 22900000, 185, 270000, "EHR, patient portal, e-prescribing, payment terminals, Microsoft 365"),
    ("032-metroline-freight", "Metroline Freight", "Metroline Freight Inc.", "Regional freight brokerage and logistics", "Food Distribution / Logistics", "Memphis, TN", 132000000, 520, 150000, "Transportation management system, EDI, carrier portal, fleet telematics, Microsoft 365"),
    ("033-ironwood-construction-services", "Ironwood Construction Services", "Ironwood Construction Services LLC", "Industrial construction services", "Construction", "Pittsburgh, PA", 98500000, 355, 62000, "ERP, estimating software, subcontractor portal, payroll, mobile field devices"),
    ("034-cloudnest-hr-platform", "CloudNest HR Platform", "CloudNest HR Platform Inc.", "Human resources SaaS", "SaaS / Software", "San Diego, CA", 58500000, 260, 1550000, "HR SaaS platform, payroll integrations, API gateway, SOC 2 control environment"),
    ("035-westfield-technical-institute", "Westfield Technical Institute", "Westfield Technical Institute", "Technical college", "Education", "Worcester, MA", 71000000, 490, 180000, "Student information system, LMS, lab networks, alumni CRM, Microsoft 365"),
    ("036-apex-robotics-fabrication", "Apex Robotics Fabrication", "Apex Robotics Fabrication Inc.", "Robotics and fabrication manufacturer", "Manufacturing / OT", "Detroit, MI", 213000000, 920, 142000, "ERP, robotic cell controllers, OT network, EDI, remote vendor maintenance"),
    ("037-urban-market-collective", "Urban Market Collective", "Urban Market Collective LLC", "Specialty retail and ecommerce", "Hospitality / Retail", "Brooklyn, NY", 44700000, 285, 620000, "Ecommerce platform, POS terminals, loyalty platform, customer support portal, Microsoft 365"),
    ("038-paystream-merchant-services", "PayStream Merchant Services", "PayStream Merchant Services Inc.", "Merchant services provider", "Fintech / Payments", "Atlanta, GA", 99000000, 390, 3100000, "Payment gateway, merchant portal, API platform, PCI environment, fraud analytics"),
    ("039-lakeside-recreation-centers", "Lakeside Recreation Centers", "Lakeside Recreation Centers LLC", "Family recreation centers", "Marina / Recreation", "Madison, WI", 28400000, 220, 85000, "Membership platform, online booking, POS terminals, guest Wi-Fi, Microsoft 365"),
    ("040-courtney-architecture-studio", "Courtney Architecture Studio", "Courtney Architecture Studio PC", "Architecture and design services", "Professional Services", "Dallas, TX", 41500000, 160, 122000, "Design file platform, client portal, project management system, Microsoft 365"),
    ("041-vitalcare-home-health", "VitalCare Home Health", "VitalCare Home Health Inc.", "Home health services provider", "Healthcare / Pharmacy", "Louisville, KY", 78000000, 980, 740000, "EHR, mobile caregiver app, patient portal, claims clearinghouse, Microsoft 365"),
    ("042-northern-produce-network", "Northern Produce Network", "Northern Produce Network LLC", "Produce distribution and cold storage", "Food Distribution / Logistics", "Boise, ID", 53800000, 290, 102000, "Warehouse management system, EDI, cold chain monitoring, fleet telematics"),
    ("043-keystone-siteworks", "Keystone Siteworks", "Keystone Siteworks Inc.", "Civil construction contractor", "Construction", "Harrisburg, PA", 76500000, 330, 53000, "ERP, project management, subcontractor portal, payroll, mobile equipment telemetry"),
    ("044-quantumledger-tax", "QuantumLedger Tax", "QuantumLedger Tax LLC", "Tax and accounting platform", "SaaS / Software", "Boston, MA", 72000000, 340, 1850000, "Tax workflow SaaS, customer portal, API integrations, cloud data lake, SOC 2 program"),
    ("045-redwood-online-university", "Redwood Online University", "Redwood Online University", "Online higher education", "Education", "Sacramento, CA", 164000000, 840, 530000, "Student information system, LMS, proctoring platform, research network, Microsoft 365"),
    ("046-union-gearworks", "Union Gearworks", "Union Gearworks Co.", "Industrial gear manufacturer", "Manufacturing / OT", "Milwaukee, WI", 88500000, 510, 78000, "ERP, OT production network, EDI, vendor remote access, Microsoft 365"),
    ("047-silverline-cafes", "Silverline Cafes", "Silverline Cafes LLC", "Cafe and quick-service restaurant group", "Hospitality / Retail", "Portland, ME", 31600000, 470, 215000, "POS terminals, loyalty app, online ordering, guest Wi-Fi, Microsoft 365"),
    ("048-cardinal-wallet", "Cardinal Wallet", "Cardinal Wallet Inc.", "Digital wallet and prepaid card platform", "Fintech / Payments", "New York, NY", 188000000, 620, 4200000, "Digital wallet platform, card processor APIs, fraud analytics, customer portal, AWS"),
    ("049-breakwater-sailing-club", "Breakwater Sailing Club", "Breakwater Sailing Club Inc.", "Sailing club and marina operator", "Marina / Recreation", "San Diego, CA", 18200000, 84, 47000, "Member portal, reservation system, POS terminals, customer Wi-Fi, Microsoft 365"),
    ("050-nova-managed-services", "Nova Managed Services", "Nova Managed Services LLC", "Managed IT services provider", "Professional Services", "Columbus, OH", 68200000, 295, 410000, "RMM platform, client ticketing, privileged access tooling, backup management portal, Microsoft 365"),
]


def main():
    rng = random.Random(20260519)
    broker_lookup = load_broker_lookup()

    update_existing_submission_industries(broker_lookup)
    claim_submission_ids = choose_new_claim_accounts(rng)

    for company in NEW_COMPANIES:
        item = build_submission(company, broker_lookup)
        item["claims"] = build_claims(item, rng) if item["id"] in claim_submission_ids else []
        write_submission(item)
        ensure_context_records(item["id"])

    update_search_metadata(broker_lookup)
    update_industry_model_note()
    print("Portfolio now contains 50 submissions.")
    print(f"Generated claims for {count_companies_with_claims()} of 50 companies.")


def load_broker_lookup():
    if not BROKER_DB_PATH.exists():
        return {}
    brokers = json.loads(BROKER_DB_PATH.read_text(encoding="utf-8")).get("brokers", [])
    return {broker["broker_id"]: broker for broker in brokers}


def update_existing_submission_industries(broker_lookup):
    for metadata_path in sorted(SUBMISSIONS_DIR.glob("*/metadata.json")):
        submission_id = metadata_path.parent.name
        if submission_id not in EXISTING_BUCKETS:
            continue
        metadata = read_json(metadata_path)
        bucket = EXISTING_BUCKETS[submission_id]
        applicant = metadata.setdefault("applicant", {})
        applicant["industry_bucket"] = bucket
        applicant["industry_group"] = bucket
        metadata["updated_at"] = UPDATED_AT
        apply_broker(metadata, bucket, broker_lookup)
        write_json(metadata_path, metadata)


def choose_new_claim_accounts(rng):
    existing_claim_accounts = count_companies_with_claims(EXISTING_BUCKETS)
    needed_claim_accounts = 30 - existing_claim_accounts
    new_ids = [company[0] for company in NEW_COMPANIES]
    return set(rng.sample(new_ids, needed_claim_accounts))


def build_submission(company, broker_lookup):
    (
        submission_id,
        title,
        insured_name,
        industry,
        bucket,
        location,
        revenue,
        employees,
        records,
        technology,
    ) = company
    index = int(submission_id.split("-", 1)[0])
    received_at = datetime(2026, 4, 8, 9, 0, tzinfo=timezone(timedelta(hours=-4))) + timedelta(days=index - 11, hours=index % 7)
    file_created_at = received_at - timedelta(hours=3, minutes=15)
    effective = (received_at + timedelta(days=45 + index % 20)).date().isoformat()
    status = ["New", "In Review", "Referral Needed", "New", "In Review"][index % 5]
    controls = build_controls(bucket, index)
    risk_flags = build_risk_flags(bucket, technology, records, index)
    open_questions = build_open_questions(bucket, index)
    coverage = build_coverage(bucket)
    broker_id = BROKER_ASSIGNMENTS[bucket]

    item = {
        "id": submission_id,
        "title": title,
        "insured_name": insured_name,
        "industry": industry,
        "industry_bucket": bucket,
        "location": location,
        "revenue": revenue,
        "employees": employees,
        "records": records,
        "technology": technology,
        "status": status,
        "received_at": iso(received_at),
        "file_created_at": iso(file_created_at),
        "effective": effective,
        "coverage": coverage["lines_requested"],
        "limits": coverage["requested_limits"],
        "retention": coverage["retention_requested"],
        "controls": controls,
        "risk_flags": risk_flags,
        "open_questions": open_questions,
        "keywords": list(dict.fromkeys(INDUSTRY_BUCKETS[bucket]["keywords"] + [industry.lower(), bucket.lower()])),
        "broker_id": broker_id,
        "claims": [],
    }

    metadata = build_metadata(item)
    apply_broker(metadata, bucket, broker_lookup)
    item["metadata"] = metadata
    return item


def build_coverage(bucket):
    base_limits = {
        "Food Distribution / Logistics": ("$5,000,000", "$3,000,000"),
        "Construction": ("$3,000,000", "$1,000,000"),
        "Healthcare / Pharmacy": ("$5,000,000", "$3,000,000"),
        "Marina / Recreation": ("$2,000,000", "$1,000,000"),
        "SaaS / Software": ("$10,000,000", "$5,000,000"),
        "Fintech / Payments": ("$10,000,000", "$5,000,000"),
        "Education": ("$5,000,000", "$3,000,000"),
        "Manufacturing / OT": ("$5,000,000", "$3,000,000"),
        "Hospitality / Retail": ("$3,000,000", "$2,000,000"),
        "Professional Services": ("$5,000,000", "$2,000,000"),
    }
    cyber_limit, bi_or_eo_limit = base_limits[bucket]
    lines = ["Cyber liability", "Privacy breach response"]
    limits = {"cyber_liability": cyber_limit, "privacy_breach_response": "$2,000,000"}

    if bucket in {"SaaS / Software", "Fintech / Payments", "Professional Services"}:
        lines.append("Technology E&O")
        limits["technology_eo"] = bi_or_eo_limit
    else:
        lines.append("Business interruption")
        limits["business_interruption"] = bi_or_eo_limit

    if bucket in {"Fintech / Payments", "Hospitality / Retail", "Healthcare / Pharmacy"}:
        lines.append("PCI fines and assessments")
        limits["pci"] = "$1,000,000"

    return {
        "lines_requested": lines,
        "requested_limits": limits,
        "retention_requested": "$100,000" if cyber_limit == "$10,000,000" else "$50,000",
    }


def build_controls(bucket, index):
    mfa = "Enabled for email, VPN, and privileged users"
    if index % 6 == 0:
        mfa = "Partial; enabled for email and VPN with rollout pending for privileged application admins"
    elif bucket in {"Fintech / Payments", "SaaS / Software"}:
        mfa = "Phishing-resistant MFA for privileged users and SSO MFA for all employees"

    edr = "Microsoft Defender for Endpoint deployed on managed endpoints"
    if bucket in {"Fintech / Payments", "SaaS / Software"}:
        edr = "CrowdStrike with 24/7 MDR coverage"
    elif index % 8 == 0:
        edr = "EDR deployed on corporate endpoints; server coverage in progress"

    backup = "Daily backups with quarterly restore testing"
    if index % 7 == 0:
        backup = "Daily backups; last restore test was more than six months ago"
    elif bucket in {"Fintech / Payments", "SaaS / Software", "Manufacturing / OT"}:
        backup = "Immutable backups with monthly restore testing"

    patching = "Critical patches within 14 days"
    if bucket in {"Fintech / Payments", "SaaS / Software"}:
        patching = "Critical patches within 7 days"
    elif index % 5 == 0:
        patching = "Critical patches within 30 days with exception tracking"

    training = "Annual employee training plus phishing simulations"
    if index % 4 == 0:
        training = "Annual employee training"

    return {
        "mfa": mfa,
        "edr": edr,
        "backup": backup,
        "patching": patching,
        "security_training": training,
    }


def build_risk_flags(bucket, technology, records, index):
    flags = []
    if records >= 500000:
        flags.append("Large privacy record count")
    if "EDI" in technology or "portal" in technology.lower() or "API" in technology:
        flags.append("Material third-party or portal dependency")
    if bucket == "Manufacturing / OT":
        flags.append("Operational technology dependency")
    if bucket in {"Fintech / Payments", "Hospitality / Retail"}:
        flags.append("PCI and payment card exposure")
    if bucket in {"Healthcare / Pharmacy", "Education"}:
        flags.append("Sensitive regulated data exposure")
    if index % 6 == 0:
        flags.append("MFA rollout gap")
    return flags[:4]


def build_open_questions(bucket, index):
    questions = [
        "Confirm most recent backup restore test date.",
        "Provide latest vulnerability scan executive summary.",
    ]
    if bucket == "Manufacturing / OT":
        questions.append("Clarify OT segmentation and vendor remote access controls.")
    elif bucket == "Fintech / Payments":
        questions.append("Request PCI ROC or most recent attestation summary.")
    elif bucket == "Healthcare / Pharmacy":
        questions.append("Request latest HIPAA security risk assessment summary.")
    elif bucket == "Education":
        questions.append("Clarify student MFA and research network segmentation.")
    elif bucket == "SaaS / Software":
        questions.append("Request SOC 2 bridge letter and customer incident SLA.")
    else:
        questions.append("Clarify critical vendor incident notification obligations.")

    if index % 6 == 0:
        questions.append("Confirm privileged application MFA completion timeline.")
    return questions


def build_metadata(item):
    documents = []
    for definition in DOCUMENT_DEFINITIONS:
        file_name, file_type, category, document_types, major_categories, description = definition
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

    return {
        "id": item["id"],
        "title": item["title"],
        "line_of_business": "Cyber liability",
        "file_created_at": item["file_created_at"],
        "received_at": item["received_at"],
        "updated_at": UPDATED_AT,
        "status": item["status"],
        "applicant": {
            "insured_name": item["insured_name"],
            "industry": item["industry"],
            "industry_bucket": item["industry_bucket"],
            "industry_group": item["industry_bucket"],
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
            "date": UPDATED_AT,
            "event": "Portfolio benchmark data linked",
            "description": "Submission connected to demo claims and industry propensity benchmark population.",
        },
    ]


def apply_broker(metadata, bucket, broker_lookup):
    broker_id = BROKER_ASSIGNMENTS.get(bucket)
    broker = broker_lookup.get(broker_id)
    if not broker:
        return

    producer = broker["contacts"]["producer"]
    account_manager = broker["contacts"]["account_manager"]
    metadata["broker"] = {
        "broker_id": broker_id,
        "firm_name": broker["firm_name"],
        "producer_name": producer["name"],
        "producer_email": producer["email"],
        "producer_phone": producer["phone"],
        "account_manager_name": account_manager["name"],
        "account_manager_email": account_manager["email"],
        "account_manager_phone": account_manager["phone"],
        "relationship_type": "Broker submission",
        "submission_channel": "Broker portal",
        "target_quote_date": metadata.get("coverage", {}).get("requested_effective_date"),
        "broker_priority": broker["service_tier"],
        "broker_notes": f"{broker['firm_name']} assigned based on {bucket} appetite and market focus.",
    }


def write_submission(item):
    folder = SUBMISSIONS_DIR / item["id"]
    folder.mkdir(parents=True, exist_ok=True)

    for document in DOCUMENT_DEFINITIONS:
        file_name = document[0]
        description = document[5]
        (folder / file_name).write_text(build_document_text(item, file_name, description), encoding="utf-8")

    write_json(folder / "metadata.json", item["metadata"])
    write_json(
        CLAIMS_DIR / f"{item['id']}.json",
        {
            "submission_id": item["id"],
            "claim_system": "dummy_claims_core",
            "updated_at": UPDATED_AT,
            "claims": item["claims"],
        },
    )


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
        f"Industry benchmark bucket: {item['industry_bucket']}",
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
        base.extend(["", "Revenue breakdown:", "- Core operations are the primary revenue source unless otherwise stated.", f"- Annual revenue: ${item['revenue']:,}"])
    elif file_name == "prior-cyber-insurance-policy.txt":
        base.extend(["", f"Expiring retention: {item['retention']}", "Prior carrier terms are provided for comparison only."])
    elif file_name == "compliance-documents.txt":
        base.extend(["", "Compliance evidence should be reviewed for applicable regulatory or contractual control frameworks."])
    elif file_name == "vendor-security-assessment.txt":
        base.extend(["", "Critical vendors should be reviewed for incident notification, recovery time, and data access controls."])

    return "\n".join(base) + "\n"


def build_claims(item, rng):
    count = rng.choice([1, 1, 1, 2, 2, 3, 4])
    claims = []
    for index in range(count):
        loss_date = datetime(2022 + rng.randint(0, 3), rng.randint(1, 12), rng.randint(1, 25)).date()
        reported_date = loss_date + timedelta(days=rng.randint(1, 4))
        claim_type, coverage_area, cause = choose_claim_type(item["industry_bucket"], rng)
        severity = rng.choice(["low", "moderate", "moderate", "high"])
        amount_paid, amount_reserved = claim_amounts(item["industry_bucket"], severity, rng, index)
        status = "open" if index == 0 and rng.random() < 0.25 else "closed"
        if status == "closed":
            amount_reserved = 0
        claims.append(
            {
                "claim_id": f"CLM-{claim_prefix(item['title'])}-{loss_date.year}-{index + 1:03d}",
                "loss_date": loss_date.isoformat(),
                "reported_date": reported_date.isoformat(),
                "status": status,
                "claim_type": claim_type,
                "coverage_area": coverage_area,
                "severity": severity,
                "amount_paid": amount_paid,
                "amount_reserved": amount_reserved,
                "cause": cause,
                "description": build_claim_description(claim_type, status),
                "recovery_status": "active_review" if status == "open" else rng.choice(["resolved", "remediated", "partial_recovery", "not_applicable"]),
            }
        )
    return claims


def choose_claim_type(bucket, rng):
    by_bucket = {
        "Fintech / Payments": [
            ("service_outage", "technology_errors_omissions", "Payment gateway routing issue caused customer transaction disruption."),
            ("payment_card_incident", "pci_assessment", "PCI forensic review triggered by suspicious payment environment activity."),
            ("api_security_event", "incident_response", "API credential exposure required forensic review and customer notification assessment."),
        ],
        "Healthcare / Pharmacy": [
            ("privacy_incident", "privacy_liability", "Misdirected file or portal access exposed limited patient information."),
            ("credential_compromise", "incident_response", "Compromised account accessed clinical or patient portal data."),
            ("ransomware_attempt", "incident_response", "Endpoint malware activity required forensic containment and legal review."),
        ],
        "Education": [
            ("credential_compromise", "incident_response", "Compromised student or faculty account accessed cloud storage."),
            ("privacy_incident", "privacy_liability", "Student record file was shared with an incorrect recipient."),
            ("ransomware_attempt", "incident_response", "Malware activity affected academic network endpoints before containment."),
        ],
        "Manufacturing / OT": [
            ("business_interruption", "network_business_interruption", "Plant system outage disrupted production scheduling."),
            ("vendor_remote_access_event", "incident_response", "Remote support credential misuse required forensic review."),
            ("invoice_manipulation", "social_engineering", "Vendor banking instructions were changed through compromised email."),
        ],
    }
    default = [
        ("business_email_compromise", "cyber_crime", "Compromised mailbox used in a fraudulent payment attempt."),
        ("service_outage", "business_interruption", "Core business platform outage caused customer service disruption."),
        ("payment_card_incident", "pci_assessment", "Suspicious POS activity required PCI forensic review."),
        ("privacy_incident", "privacy_liability", "Limited customer information was disclosed to an unauthorized recipient."),
    ]
    return rng.choice(by_bucket.get(bucket, default))


def claim_amounts(bucket, severity, rng, index):
    base = INDUSTRY_BUCKETS[bucket]["base_claim"]
    multiplier = {"low": 0.35, "moderate": 0.85, "high": 1.75}[severity]
    paid = int(round(base * multiplier * rng.uniform(0.65, 1.35), -2))
    reserve = 0
    if severity == "high" or index % 3 == 0:
        reserve = int(round(base * rng.uniform(0.25, 1.1), -2))
    return paid, reserve


def build_claim_description(claim_type, status):
    disposition = "remains under review" if status == "open" else "was closed after remediation was documented"
    return f"{claim_type.replace('_', ' ').title()} {disposition}; costs include forensic, legal, notification, recovery, or customer credit expenses as applicable."


def claim_prefix(title):
    letters = re.sub(r"[^A-Za-z]", "", title).upper()
    return (letters[:8] or "DUMMY")


def ensure_context_records(submission_id):
    for folder_name, key in [("guide", "guides"), ("note", "notes"), ("task", "tasks")]:
        path = DATA_ROOT / folder_name / f"{submission_id}.json"
        if not path.exists():
            write_json(path, {"submission_id": submission_id, "updated_at": None, key: []})

    state_path = DATA_ROOT / "states" / f"{submission_id}.json"
    if not state_path.exists():
        write_json(state_path, {"submission_id": submission_id, "updated_at": None, "submitted_at": None, "stages": []})

    underwriting_path = DATA_ROOT / "underwriting" / f"{submission_id}.json"
    if not underwriting_path.exists():
        write_json(
            underwriting_path,
            {
                "submission_id": submission_id,
                "updated_at": UPDATED_AT,
                "source": "demo_underwriting_workbench",
                "components": [],
                "claim_review": None,
            },
        )


def update_search_metadata(broker_lookup):
    entries = []
    for metadata_path in sorted(SUBMISSIONS_DIR.glob("*/metadata.json")):
        metadata = read_json(metadata_path)
        applicant = metadata.get("applicant", {})
        bucket = applicant.get("industry_bucket") or applicant.get("industry_group") or "Professional Services"
        broker_id = metadata.get("broker", {}).get("broker_id") or BROKER_ASSIGNMENTS.get(bucket)
        broker = broker_lookup.get(broker_id, {})
        keywords = list(dict.fromkeys(
            [
                *(INDUSTRY_BUCKETS.get(bucket, {}).get("keywords", [])),
                metadata.get("title", ""),
                applicant.get("insured_name", ""),
                applicant.get("industry", ""),
                bucket,
                broker.get("firm_name", ""),
                broker.get("broker_type", ""),
                broker.get("service_tier", ""),
            ]
        ))
        entries.append(
            {
                "id": metadata["id"],
                "title": metadata.get("title", metadata["id"]),
                "insured_name": applicant.get("insured_name", "Unknown insured"),
                "industry": applicant.get("industry", "Industry TBD"),
                "industry_bucket": bucket,
                "status": metadata.get("status", "New"),
                "received_at": metadata.get("received_at"),
                "folder": f"data/submissions/{metadata['id']}",
                "keywords": [keyword for keyword in keywords if keyword],
                "broker_id": broker_id,
                "broker_name": broker.get("firm_name"),
            }
        )

    write_json(
        SEARCH_METADATA_PATH,
        {
            "generated_at": UPDATED_AT,
            "description": "Search index for cyber underwriting dummy submissions.",
            "submissions": sorted(entries, key=lambda item: item["id"]),
        },
    )


def update_industry_model_note():
    path = ROOT / "model" / "industry_propensity.json"
    write_json(
        path,
        {
            "model_name": "industry_propensity",
            "model_type": "calculated_benchmark_table",
            "target": "industry_cyber_propensity_score",
            "version": "0.2.0-demo",
            "description": "Calculated by backend from data/submissions and data/claims. The stored file documents the demo formula; the API response contains current industry_history.",
            "source_data": {
                "submissions": "data/submissions/*/metadata.json",
                "claims": "data/claims/*.json",
            },
            "score_formula": "0.25 + 0.50 * company_claim_rate + 0.25 * normalized_average_claim_severity",
        },
    )


def count_companies_with_claims(submission_ids=None):
    allowed_ids = set(submission_ids) if submission_ids else None
    count = 0
    for path in CLAIMS_DIR.glob("*.json"):
        if allowed_ids is not None and path.stem not in allowed_ids:
            continue
        try:
            claims = read_json(path).get("claims", [])
        except json.JSONDecodeError:
            claims = []
        if claims:
            count += 1
    return count


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def iso(value):
    return value.isoformat(timespec="seconds")


if __name__ == "__main__":
    main()
