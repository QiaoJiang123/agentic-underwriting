from pathlib import Path

from backend.config import (
    AGENT_SKILLS_PATH,
    BROKER_DB_PATH,
    CHAT_HISTORY_DIR,
    CLAIMS_DIR,
    DATA_DIR,
    DECISION_WORKFLOW_DIR,
    DOCUMENT_REQUIREMENTS_PATH,
    GUIDE_DIR,
    INTAKE_STATUS_DIR,
    MODEL_DIR,
    NOTE_DIR,
    SCHEMA_DIR,
    SEARCH_METADATA_PATH,
    SOP_METADATA_PATH,
    SOP_PATH,
    STATES_DIR,
    TASK_DIR,
    UNDERWRITING_DIR,
)
from backend.services.agent_skill_service import get_agent_skills_record
from backend.services.broker_service import get_broker_database
from backend.services.claim_service import get_claim_record
from backend.services.submission_service import get_search_metadata


def get_dev_console_catalog():
    submissions = get_search_metadata().get("submissions", [])
    brokers = get_broker_database().get("brokers", [])
    agent_skills = get_agent_skills_record()
    claim_records = build_claim_records(submissions)
    data_sources = build_data_sources(submissions, brokers, agent_skills, claim_records)
    overview = build_overview(submissions, brokers, agent_skills, claim_records, data_sources)

    return {
        "overview": overview,
        "submissions": submissions,
        "brokers": brokers,
        "claims": {
            "records": claim_records,
            "totals": summarize_claim_records(claim_records),
        },
        "agent_skills": agent_skills,
        "workflow": build_agent_workflow(agent_skills),
        "data_sources": data_sources,
    }


def build_claim_records(submissions):
    records = []
    for submission in submissions:
        submission_id = submission.get("id")
        if not submission_id:
            continue

        try:
            claim_record = get_claim_record(submission_id)
        except (FileNotFoundError, ValueError):
            claim_record = {
                "submission_id": submission_id,
                "claim_system": "dummy_claims_core",
                "updated_at": None,
                "claims": [],
                "aggregate": summarize_empty_claims(),
            }

        aggregate = claim_record.get("aggregate") or summarize_empty_claims()
        records.append(
            {
                "submission_id": submission_id,
                "title": submission.get("title"),
                "insured_name": submission.get("insured_name"),
                "industry": submission.get("industry"),
                "industry_bucket": submission.get("industry_bucket"),
                "status": submission.get("status"),
                "broker_name": submission.get("broker_name"),
                "claim_system": claim_record.get("claim_system"),
                "updated_at": claim_record.get("updated_at"),
                "aggregate": aggregate,
                "claims": claim_record.get("claims", []),
            }
        )

    return sorted(
        records,
        key=lambda item: (
            item.get("aggregate", {}).get("total_claims", 0),
            item.get("aggregate", {}).get("total_incurred", 0),
        ),
        reverse=True,
    )


def summarize_empty_claims():
    return {
        "total_claims": 0,
        "open_claims": 0,
        "closed_claims": 0,
        "total_paid": 0,
        "total_reserved": 0,
        "total_incurred": 0,
        "latest_loss_date": None,
        "severity_mix": {},
        "as_of": None,
    }


def summarize_claim_records(claim_records):
    return {
        "claim_record_count": len(claim_records),
        "companies_with_claims": sum(1 for record in claim_records if record.get("aggregate", {}).get("total_claims", 0)),
        "total_claims": sum(record.get("aggregate", {}).get("total_claims", 0) for record in claim_records),
        "open_claims": sum(record.get("aggregate", {}).get("open_claims", 0) for record in claim_records),
        "total_paid": sum(record.get("aggregate", {}).get("total_paid", 0) for record in claim_records),
        "total_reserved": sum(record.get("aggregate", {}).get("total_reserved", 0) for record in claim_records),
        "total_incurred": sum(record.get("aggregate", {}).get("total_incurred", 0) for record in claim_records),
    }


def build_overview(submissions, brokers, agent_skills, claim_records, data_sources):
    claim_totals = summarize_claim_records(claim_records)
    return {
        "submission_count": len(submissions),
        "broker_count": len(brokers),
        "companies_with_claims": claim_totals["companies_with_claims"],
        "total_claims": claim_totals["total_claims"],
        "total_incurred": claim_totals["total_incurred"],
        "agent_skill_count": len(agent_skills.get("skills", [])),
        "data_source_count": len(data_sources),
    }


def build_data_sources(submissions, brokers, agent_skills, claim_records):
    return [
        source_item(
            "submissions",
            "Submission Documents",
            "data/submissions/<submission_id>",
            len(submissions),
            "Submission folders, document files, and per-submission metadata used by chat, analytics, and underwriting workbench views.",
            "/api/submissions",
        ),
        source_item(
            "search_index",
            "Search Index",
            path_label(SEARCH_METADATA_PATH),
            len(submissions),
            "Global submission index used by search, Dev maintenance, and intake lookup.",
            "/api/search-metadata",
        ),
        source_item(
            "brokers",
            "Broker Database",
            path_label(BROKER_DB_PATH),
            len(brokers),
            "Reusable broker firm, contact, service, relationship, and placement metrics.",
            "/api/brokers",
        ),
        source_item(
            "claims",
            "Claim System Records",
            path_label(CLAIMS_DIR),
            len(claim_records),
            "Dummy linked claim records with paid, reserved, severity, status, and cause fields.",
            "/api/submissions/<submission_id>/claims",
        ),
        source_item(
            "agent_skills",
            "Agent Skills",
            path_label(AGENT_SKILLS_PATH),
            len(agent_skills.get("skills", [])),
            "Local retrieval and navigation skills used by the centralized information agent.",
            "/api/agent-skills",
        ),
        source_item(
            "sop",
            "Underwriting SOP",
            path_label(SOP_PATH),
            count_json_list(SOP_PATH, "steps"),
            "Commercial cyber underwriting procedure steps, goals, and suggestion templates.",
            "/api/sop",
        ),
        source_item(
            "sop_metadata",
            "SOP Metadata",
            path_label(SOP_METADATA_PATH),
            count_json_list(SOP_METADATA_PATH, "steps"),
            "Searchable SOP keywords and intents used when prompts need procedural guidance.",
            "/api/sop",
        ),
        source_item(
            "document_requirements",
            "Document Requirements",
            path_label(DOCUMENT_REQUIREMENTS_PATH),
            count_required_documents(DOCUMENT_REQUIREMENTS_PATH),
            "Cyber required evidence checklist used for missing-document analysis.",
            "/api/chat",
        ),
        source_item(
            "models",
            "Analytics Models",
            path_label(MODEL_DIR),
            count_files(MODEL_DIR, "*.json"),
            "Quote, bind, supplemental GLM, feature metadata, and industry benchmark model files.",
            "/api/models/<model_name>",
        ),
        source_item(
            "underwriting",
            "Underwriting Workbench",
            path_label(UNDERWRITING_DIR),
            count_files(UNDERWRITING_DIR, "*.json"),
            "Per-submission underwriting components, broker context, claim review, and recommended actions.",
            "/api/submissions/<submission_id>/underwriting",
        ),
        source_item(
            "tasks",
            "Tasks",
            path_label(TASK_DIR),
            count_files(TASK_DIR, "*.json"),
            "Scheduled task records and calendar inputs for each submission.",
            "/api/submissions/<submission_id>/tasks",
        ),
        source_item(
            "states",
            "Stage State",
            path_label(STATES_DIR),
            count_files(STATES_DIR, "*.json"),
            "Underwriting stage checklist state and locked stage submissions.",
            "/api/submissions/<submission_id>/states",
        ),
        source_item(
            "notes",
            "Underwriter Notes",
            path_label(NOTE_DIR),
            count_files(NOTE_DIR, "*.json"),
            "Ground-truth underwriter notes sent as context during chat retrieval.",
            "/api/submissions/<submission_id>/notes",
        ),
        source_item(
            "guides",
            "Prompt Guides",
            path_label(GUIDE_DIR),
            count_files(GUIDE_DIR, "*.json"),
            "Per-submission prompt guide instructions injected into the system prompt.",
            "/api/submissions/<submission_id>/guides",
        ),
        source_item(
            "decision_workflow",
            "Decision Workflow",
            path_label(DECISION_WORKFLOW_DIR),
            count_files(DECISION_WORKFLOW_DIR, "*.json"),
            "Quote readiness, referral, approval, and bind readiness gate decisions.",
            "/api/submissions/<submission_id>/decision-workflow",
        ),
        source_item(
            "intake_status",
            "Intake Status",
            path_label(INTAKE_STATUS_DIR),
            count_files(INTAKE_STATUS_DIR, "*.json"),
            "Saved add-submission checklist and intake staging status.",
            "/api/intake/status",
        ),
        source_item(
            "chat_history",
            "Chat History",
            path_label(CHAT_HISTORY_DIR),
            count_files(CHAT_HISTORY_DIR, "*.json"),
            "Saved chat threads grouped by submission.",
            "/api/submissions/<submission_id>/chat-history",
        ),
        source_item(
            "schemas",
            "Schemas",
            path_label(SCHEMA_DIR),
            count_files(SCHEMA_DIR, "*.json") + count_files(SCHEMA_DIR, "*.md"),
            "Formal data schema references and validation documentation.",
            "/api/schemas",
        ),
    ]


def source_item(key, label, path, record_count, description, api):
    return {
        "key": key,
        "label": label,
        "path": path,
        "record_count": record_count,
        "description": description,
        "api": api,
    }


def build_agent_workflow(agent_skills):
    return {
        "title": "Centralized Underwriting Information Agent",
        "summary": "Routes each prompt to the data needed for the answer, assembles cited context, then sends the compact working set to the model and UI action layer.",
        "nodes": [
            {
                "id": "prompt",
                "label": "Prompt Intake",
                "phase": "Input",
                "description": "Receives the underwriter question, current submission, selected files, notes, guides, and panel state.",
            },
            {
                "id": "central_agent",
                "label": "Information Agent",
                "phase": "Plan",
                "description": "Classifies the request and chooses whether to pull documents, SOP, broker data, claims, analytics, workflow state, or account metadata.",
            },
            {
                "id": "skill_router",
                "label": "Skill Router",
                "phase": "Route",
                "description": "Maps intent to retrieval skills and local actions before the GPT response is built.",
            },
            {
                "id": "retrieval",
                "label": "Retrieval Layer",
                "phase": "Retrieve",
                "description": "Reads selected JSON stores and submission files. Auto mode can check documents in the left panel based on the selected evidence.",
            },
            {
                "id": "context",
                "label": "Context Assembly",
                "phase": "Assemble",
                "description": "Combines sources into a compact context block with citations, excluding full document text from saved chat history.",
            },
            {
                "id": "model",
                "label": "LangGraph / GPT",
                "phase": "Reason",
                "description": "Runs the Python graph flow, applies system guides, and asks the configured GPT model to produce the answer.",
            },
            {
                "id": "response",
                "label": "Answer + UI Actions",
                "phase": "Act",
                "description": "Returns the answer, citations, selected surfaces, document selections, and workflow actions to the browser.",
            },
        ],
        "retrieval_groups": build_retrieval_groups(agent_skills),
        "edges": [
            {"from": "prompt", "to": "central_agent", "label": "question + workspace state"},
            {"from": "central_agent", "to": "skill_router", "label": "intent plan"},
            {"from": "skill_router", "to": "retrieval", "label": "selected skills"},
            {"from": "retrieval", "to": "context", "label": "source records"},
            {"from": "context", "to": "model", "label": "cited context"},
            {"from": "model", "to": "response", "label": "answer + actions"},
        ],
        "cycles": [
            {
                "from": "response",
                "to": "prompt",
                "label": "Underwriter follow-up loop",
                "description": "The answer, citations, selected documents, visible panel state, and underwriter edits inform the next prompt.",
            },
            {
                "from": "response",
                "to": "retrieval",
                "label": "Workspace update loop",
                "description": "Chat actions can save notes, guides, tasks, stages, or metadata updates. Future retrieval reads those updated JSON records.",
            },
            {
                "from": "retrieval",
                "to": "skill_router",
                "label": "Selection correction loop",
                "description": "If Auto document selection or data retrieval is revised by the user, the next request routes with the corrected fixed or auto state.",
            },
        ],
    }


def build_retrieval_groups(agent_skills):
    skills = agent_skills.get("skills", [])
    groups = [
        ("documents", "Documents + Evidence", ["document", "evidence", "loss", "application"]),
        ("sop", "SOP Guidance", ["sop", "procedure"]),
        ("broker", "Broker Intelligence", ["broker"]),
        ("claims", "Claims", ["claim", "loss"]),
        ("analytics", "Analytics + Models", ["analytics", "model", "quote", "bind"]),
        ("workflow", "Tasks + Stages", ["task", "stage", "workflow", "status"]),
        ("navigation", "Workspace Navigation", ["navigate", "open"]),
    ]
    return [
        {
            "key": key,
            "label": label,
            "skill_ids": [
                skill.get("skill_id")
                for skill in skills
                if any(term in " ".join([skill.get("skill_id", ""), skill.get("label", ""), skill.get("output", "")]).lower() for term in terms)
            ],
        }
        for key, label, terms in groups
    ]


def count_files(path, pattern):
    path = Path(path)
    if not path.exists():
        return 0
    return sum(1 for item in path.rglob(pattern) if item.is_file())


def count_json_list(path, list_key):
    data = read_json_if_exists(path)
    value = data.get(list_key, []) if isinstance(data, dict) else []
    return len(value) if isinstance(value, list) else 0


def count_required_documents(path):
    data = read_json_if_exists(path)
    if not isinstance(data, dict):
        return 0
    for key in ["required_documents", "documents", "requirements"]:
        value = data.get(key)
        if isinstance(value, list):
            return len(value)
    return 0


def read_json_if_exists(path):
    path = Path(path)
    if not path.exists():
        return {}
    try:
        import json

        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def path_label(path):
    try:
        return str(Path(path).relative_to(Path.cwd()))
    except ValueError:
        return str(path)
