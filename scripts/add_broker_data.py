import json
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.config import AGENT_SKILLS_DIR, AGENT_SKILLS_PATH, BROKER_DB_PATH, BROKERS_DIR, DATA_DIR, SEARCH_METADATA_PATH


BROKERS = [
    {
        "broker_id": "brk-atlantic-risk-partners",
        "firm_name": "Atlantic Risk Partners",
        "broker_type": "Retail broker",
        "branch": "New York Metro",
        "primary_region": "Northeast",
        "service_tier": "Strategic",
        "market_focus": ["Food distribution", "Hospitality", "Cyber and technology E&O"],
        "contacts": {
            "producer": {
                "name": "Maya Chen",
                "email": "maya.chen@atlanticrisk.example",
                "phone": "212-555-0184",
            },
            "account_manager": {
                "name": "Jordan Patel",
                "email": "jordan.patel@atlanticrisk.example",
                "phone": "212-555-0149",
            },
        },
        "relationship_metrics": {
            "years_active": 7,
            "submissions_ytd": 18,
            "quote_ratio_12m": 0.74,
            "bind_ratio_12m": 0.41,
            "avg_response_hours": 9,
            "data_quality_score": 88,
        },
        "placement_notes": "Strong market access and clean submission packaging; often asks for quick quote turnaround.",
        "communication_preferences": ["Email", "Shared secure portal"],
    },
    {
        "broker_id": "brk-midwest-commercial-risk",
        "firm_name": "Midwest Commercial Risk",
        "broker_type": "Retail broker",
        "branch": "Columbus",
        "primary_region": "Midwest",
        "service_tier": "Core",
        "market_focus": ["Construction", "Manufacturing", "Funds transfer fraud"],
        "contacts": {
            "producer": {
                "name": "Evan Brooks",
                "email": "evan.brooks@midwestcommercial.example",
                "phone": "614-555-0177",
            },
            "account_manager": {
                "name": "Priya Raman",
                "email": "priya.raman@midwestcommercial.example",
                "phone": "614-555-0191",
            },
        },
        "relationship_metrics": {
            "years_active": 4,
            "submissions_ytd": 12,
            "quote_ratio_12m": 0.68,
            "bind_ratio_12m": 0.36,
            "avg_response_hours": 14,
            "data_quality_score": 79,
        },
        "placement_notes": "Construction accounts usually need invoice manipulation and social engineering clarity.",
        "communication_preferences": ["Email", "Phone follow-up for subjectivities"],
    },
    {
        "broker_id": "brk-harbor-specialty",
        "firm_name": "Harbor Specialty Brokerage",
        "broker_type": "Wholesale broker",
        "branch": "Boston",
        "primary_region": "National",
        "service_tier": "Core",
        "market_focus": ["Healthcare", "Education", "Public entity", "Marina and recreation"],
        "contacts": {
            "producer": {
                "name": "Nora Walsh",
                "email": "nora.walsh@harborspecialty.example",
                "phone": "617-555-0116",
            },
            "account_manager": {
                "name": "Leo Martinez",
                "email": "leo.martinez@harborspecialty.example",
                "phone": "617-555-0130",
            },
        },
        "relationship_metrics": {
            "years_active": 6,
            "submissions_ytd": 22,
            "quote_ratio_12m": 0.61,
            "bind_ratio_12m": 0.29,
            "avg_response_hours": 18,
            "data_quality_score": 73,
        },
        "placement_notes": "Complex accounts frequently need second-round evidence and authority explanation.",
        "communication_preferences": ["Email", "Broker portal"],
    },
    {
        "broker_id": "brk-pacific-tech-risk",
        "firm_name": "Pacific Technology Risk Advisors",
        "broker_type": "Retail broker",
        "branch": "San Francisco",
        "primary_region": "West",
        "service_tier": "Strategic",
        "market_focus": ["SaaS", "Fintech", "Technology E&O", "API platforms"],
        "contacts": {
            "producer": {
                "name": "Sofia Nguyen",
                "email": "sofia.nguyen@pacifictechrisk.example",
                "phone": "415-555-0108",
            },
            "account_manager": {
                "name": "Caleb Ortiz",
                "email": "caleb.ortiz@pacifictechrisk.example",
                "phone": "415-555-0152",
            },
        },
        "relationship_metrics": {
            "years_active": 5,
            "submissions_ytd": 16,
            "quote_ratio_12m": 0.82,
            "bind_ratio_12m": 0.47,
            "avg_response_hours": 7,
            "data_quality_score": 91,
        },
        "placement_notes": "Strong technical detail and SOC evidence; expects clear model rationale on technology accounts.",
        "communication_preferences": ["Email", "Technical data room"],
    },
    {
        "broker_id": "brk-crestline-specialty",
        "firm_name": "Crestline Specialty Partners",
        "broker_type": "Wholesale broker",
        "branch": "Chicago",
        "primary_region": "National",
        "service_tier": "Development",
        "market_focus": ["Retail pharmacy", "Manufacturing", "Hospitality", "Privacy exposed accounts"],
        "contacts": {
            "producer": {
                "name": "Amelia Ross",
                "email": "amelia.ross@crestlinespecialty.example",
                "phone": "312-555-0126",
            },
            "account_manager": {
                "name": "Marcus Lee",
                "email": "marcus.lee@crestlinespecialty.example",
                "phone": "312-555-0164",
            },
        },
        "relationship_metrics": {
            "years_active": 2,
            "submissions_ytd": 9,
            "quote_ratio_12m": 0.56,
            "bind_ratio_12m": 0.24,
            "avg_response_hours": 22,
            "data_quality_score": 68,
        },
        "placement_notes": "Submissions can need follow-up on controls, but broker is responsive once requirements are specific.",
        "communication_preferences": ["Email", "Weekly pipeline call"],
    },
]


ASSIGNMENTS = {
    "001-acme-foods": ("brk-atlantic-risk-partners", "Maya Chen", "Jordan Patel", "Retail submission", "Strategic renewal opportunity; broker wants fast feedback on MFA subjectivity."),
    "002-northstar-contracting": ("brk-midwest-commercial-risk", "Evan Brooks", "Priya Raman", "Retail submission", "Broker is focused on funds transfer fraud wording and subcontractor portal exposure."),
    "003-evergreen-senior-living": ("brk-harbor-specialty", "Nora Walsh", "Leo Martinez", "Wholesale submission", "Broker expects referral explanation because PHI exposure and medical device controls are sensitive."),
    "004-harborview-marina": ("brk-harbor-specialty", "Nora Walsh", "Leo Martinez", "Wholesale submission", "Broker is comparing options for PCI, customer Wi-Fi, and reservation platform dependencies."),
    "005-pixelwave-software": ("brk-pacific-tech-risk", "Sofia Nguyen", "Caleb Ortiz", "Retail submission", "Broker wants a technical quote story around API exposure and SOC 2 evidence."),
    "006-quantum-retail-pharmacy": ("brk-crestline-specialty", "Amelia Ross", "Marcus Lee", "Wholesale submission", "Broker needs clear HIPAA and pharmacy system follow-up items."),
    "007-lakeview-university": ("brk-harbor-specialty", "Nora Walsh", "Leo Martinez", "Wholesale submission", "Broker expects staged remediation requirements for MFA rollout and research network segmentation."),
    "008-summit-fintech-payments": ("brk-pacific-tech-risk", "Sofia Nguyen", "Caleb Ortiz", "Retail submission", "Broker wants quote rationale tied to API aggregation, PCI posture, and transaction dependency."),
    "009-cascade-industrial-manufacturing": ("brk-midwest-commercial-risk", "Evan Brooks", "Priya Raman", "Retail submission", "Broker needs practical OT and vendor remote access subjectivities."),
    "010-sunrise-hospitality-group": ("brk-atlantic-risk-partners", "Maya Chen", "Jordan Patel", "Retail submission", "Broker wants clean next steps for PCI, guest Wi-Fi, and property management controls."),
}


AGENT_SKILLS = {
    "version": "0.1-demo",
    "description": "Local chat skills for extraction and navigation inside the underwriting workspace.",
    "skills": [
        {
            "skill_id": "extract_broker_profile",
            "label": "Extract Broker Profile",
            "trigger_examples": ["show broker", "who is the broker", "extract broker information"],
            "action_type": "extract",
            "output": "Broker firm, contacts, service tier, response metrics, data quality, and submission-specific notes.",
        },
        {
            "skill_id": "extract_account_snapshot",
            "label": "Extract Account Snapshot",
            "trigger_examples": ["extract account summary", "show account snapshot", "summarize this submission"],
            "action_type": "extract",
            "output": "Applicant, coverage request, broker, claim summary, evidence readiness, and next action.",
        },
        {
            "skill_id": "extract_claim_history",
            "label": "Extract Claim History",
            "trigger_examples": ["show claims", "extract claim history", "summarize loss runs"],
            "action_type": "extract",
            "output": "Claim count, open claim count, incurred loss, severity mix, and claim details.",
        },
        {
            "skill_id": "extract_missing_evidence",
            "label": "Extract Missing Evidence",
            "trigger_examples": ["what is missing", "extract missing evidence", "draft broker follow up"],
            "action_type": "extract",
            "output": "Required evidence status, missing items, and broker-ready follow-up wording.",
        },
        {
            "skill_id": "retrieve_relevant_documents",
            "label": "Retrieve Relevant Documents",
            "trigger_examples": ["what does the application say about MFA", "review the loss runs", "pull documents for backup evidence"],
            "action_type": "retrieve",
            "output": "Selects and reads relevant submission files based on prompt intent and current file selection.",
        },
        {
            "skill_id": "retrieve_analytics_models",
            "label": "Retrieve Analytics And Models",
            "trigger_examples": ["why is quote probability high", "show model drivers", "what is the industry propensity benchmark"],
            "action_type": "retrieve",
            "output": "Pulls quote, bind, supplemental GLM, and industry propensity model results with top drivers.",
        },
        {
            "skill_id": "retrieve_operating_context",
            "label": "Retrieve Operating Context",
            "trigger_examples": ["what are the open tasks", "what notes exist", "what stage are we in"],
            "action_type": "retrieve",
            "output": "Pulls notes, guide instructions, scheduled tasks, and underwriting stage state as needed.",
        },
        {
            "skill_id": "retrieve_submission_current_status",
            "label": "Retrieve Submission Current Status",
            "trigger_examples": ["what is the current status", "where are we on this submission", "give me a status update"],
            "action_type": "retrieve",
            "output": "Pulls metadata status, appetite, evidence readiness, claims, open tasks, stage progress, and locked-stage state.",
        },
        {
            "skill_id": "retrieve_workflow_stage_status",
            "label": "Retrieve Workflow Stage Status",
            "trigger_examples": ["what stage are we in", "what is the next stage", "which stages are locked"],
            "action_type": "retrieve",
            "output": "Pulls underwriting stage checks, current or next stage, and submitted locked-stage information.",
        },
        {
            "skill_id": "retrieve_submission_update_history",
            "label": "Retrieve Submission Update History",
            "trigger_examples": ["what changed recently", "show status update history", "what submission updates were made"],
            "action_type": "retrieve",
            "output": "Pulls submission timeline and metadata update events from the submission record.",
        },
        {
            "skill_id": "navigate_workspace",
            "label": "Navigate Workspace",
            "trigger_examples": ["open analytics", "go to tasks", "show note", "open underwriting system"],
            "action_type": "navigate",
            "output": "Switches the visible workspace panel and expands the correct view where useful.",
        },
    ],
}


def main():
    BROKERS_DIR.mkdir(parents=True, exist_ok=True)
    AGENT_SKILLS_DIR.mkdir(parents=True, exist_ok=True)

    broker_lookup = {broker["broker_id"]: broker for broker in BROKERS}
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    BROKER_DB_PATH.write_text(
        json.dumps({"updated_at": now, "brokers": BROKERS}, indent=2) + "\n",
        encoding="utf-8",
    )
    AGENT_SKILLS_PATH.write_text(json.dumps(AGENT_SKILLS, indent=2) + "\n", encoding="utf-8")

    for metadata_path in sorted(DATA_DIR.glob("*/metadata.json")):
        submission = json.loads(metadata_path.read_text(encoding="utf-8"))
        assignment = ASSIGNMENTS.get(submission["id"])
        if not assignment:
            continue

        broker_id, producer_name, account_manager_name, relationship_type, broker_notes = assignment
        broker = broker_lookup[broker_id]
        producer = broker["contacts"]["producer"]
        account_manager = broker["contacts"]["account_manager"]
        submission["broker"] = {
            "broker_id": broker_id,
            "firm_name": broker["firm_name"],
            "producer_name": producer_name,
            "producer_email": producer["email"],
            "producer_phone": producer["phone"],
            "account_manager_name": account_manager_name,
            "account_manager_email": account_manager["email"],
            "account_manager_phone": account_manager["phone"],
            "relationship_type": relationship_type,
            "submission_channel": "Broker portal",
            "target_quote_date": submission.get("coverage", {}).get("requested_effective_date"),
            "broker_priority": broker["service_tier"],
            "broker_notes": broker_notes,
        }
        metadata_path.write_text(json.dumps(submission, indent=2) + "\n", encoding="utf-8")

    if SEARCH_METADATA_PATH.exists():
        search_metadata = json.loads(SEARCH_METADATA_PATH.read_text(encoding="utf-8"))
        for item in search_metadata.get("submissions", []):
            assignment = ASSIGNMENTS.get(item.get("id"))
            if not assignment:
                continue
            broker = broker_lookup[assignment[0]]
            item["broker_id"] = broker["broker_id"]
            item["broker_name"] = broker["firm_name"]
            keywords = item.setdefault("keywords", [])
            for keyword in [broker["firm_name"], broker["broker_type"], broker["service_tier"]]:
                if keyword not in keywords:
                    keywords.append(keyword)
        SEARCH_METADATA_PATH.write_text(json.dumps(search_metadata, indent=2) + "\n", encoding="utf-8")

    print(f"wrote {BROKER_DB_PATH.relative_to(ROOT)}")
    print(f"wrote {AGENT_SKILLS_PATH.relative_to(ROOT)}")
    print("updated broker references on submissions")


if __name__ == "__main__":
    main()
