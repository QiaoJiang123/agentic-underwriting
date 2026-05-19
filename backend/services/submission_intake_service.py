import json
import re
import shutil
import time
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

from backend.config import (
    CHAT_HISTORY_DIR,
    CLAIMS_DIR,
    DATA_DIR,
    GUIDE_DIR,
    INTAKE_STATUS_DIR,
    INTAKE_UPLOAD_DIR,
    NOTE_DIR,
    STATES_DIR,
    TASK_DIR,
    UNDERWRITING_DIR,
)
from backend.services.intake_status_service import REQUIRED_INTAKE_DOCUMENTS, sanitize_intake_status
from backend.services.broker_service import get_broker, list_brokers
from backend.services.openai_service import extract_output_text, post_json
from backend.services.schema_service import validate_named_schema
from backend.services.submission_service import (
    extract_simple_pdf_text,
    get_submission_detail,
    is_valid_submission_id,
    submission_exists,
    update_search_metadata_entry,
    write_json,
)
from backend.services.upload_service import infer_document_metadata


INTAKE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "title",
        "insured_name",
        "industry",
        "location",
        "annual_revenue",
        "employee_count",
        "records_count",
        "technology_profile",
        "requested_effective_date",
        "retention_requested",
        "coverage_limit",
        "broker_name",
        "producer_email",
        "mfa",
        "edr",
        "backup",
        "patching",
        "security_training",
        "risk_flags",
        "open_questions",
    ],
    "properties": {
        "title": {"type": "string"},
        "insured_name": {"type": "string"},
        "industry": {"type": "string"},
        "location": {"type": "string"},
        "annual_revenue": {"type": "number"},
        "employee_count": {"type": "number"},
        "records_count": {"type": "number"},
        "technology_profile": {"type": "string"},
        "requested_effective_date": {"type": "string"},
        "retention_requested": {"type": "string"},
        "coverage_limit": {"type": "string"},
        "broker_name": {"type": "string"},
        "producer_email": {"type": "string"},
        "mfa": {"type": "string"},
        "edr": {"type": "string"},
        "backup": {"type": "string"},
        "patching": {"type": "string"},
        "security_training": {"type": "string"},
        "risk_flags": {"type": "array", "items": {"type": "string"}},
        "open_questions": {"type": "array", "items": {"type": "string"}},
    },
}

DEFAULT_STAGES = [
    ("intake", "Intake"),
    ("document_collection", "Document Collection"),
    ("data_extraction", "Data Extraction"),
    ("initial_review", "Initial Review"),
    ("risk_assessment", "Risk Assessment"),
    ("clarification", "Clarification"),
    ("referral_approval", "Referral / Approval"),
    ("terms_conditions", "Terms & Conditions"),
    ("quote", "Quote"),
    ("bind_close", "Bind / Close"),
]


def draft_submission_from_text(intake_text, api_key="", model=""):
    text = str(intake_text or "").strip()
    llm_draft = draft_submission_with_llm(text, api_key, model) if text else None
    local_draft = infer_submission_draft(text)
    return sanitize_draft({**local_draft, **(llm_draft or {})})


def draft_submission_from_application_file(file_name, file_bytes, api_key="", model=""):
    safe_file_name = Path(str(file_name or "application-form")).name
    suffix = Path(safe_file_name).suffix.lower()
    if suffix not in {".txt", ".pdf"}:
        raise ValueError("Only .txt and .pdf intake documents can be uploaded.")
    if not file_bytes:
        raise ValueError("Uploaded intake document is empty.")

    extracted_text = extract_application_form_text(safe_file_name, file_bytes)
    upload_id = stage_intake_upload(safe_file_name, file_bytes, extracted_text)
    return {
        "upload_id": upload_id,
        "file_name": safe_file_name,
        "extracted_text": extracted_text,
        "draft": draft_submission_from_text(extracted_text, api_key, model),
    }


def build_intake_review(payload):
    draft = sanitize_draft(payload.get("draft") if isinstance(payload.get("draft"), dict) else payload)
    intake_text = str(payload.get("intake_text") or draft.get("intake_text") or "").strip()
    uploaded_documents = sanitize_uploaded_documents(payload.get("uploaded_documents"))
    intake_status = sanitize_intake_status(payload.get("intake_status") if isinstance(payload.get("intake_status"), dict) else {})
    broker = resolve_broker(draft.get("broker_id"), draft.get("broker_name"))
    missing_fields = find_missing_intake_fields(draft, broker)
    evidence_gaps = find_missing_evidence(intake_status, uploaded_documents, intake_text)
    control_gaps = find_control_gaps(draft)
    open_questions = draft.get("open_questions") or []

    steps = [
        {
            "key": "intake_validation",
            "heading": "Complete intake fields",
            "status": "needs_attention" if missing_fields else "complete",
            "action": "Validate intake fields before moving deeper into risk review.",
            "detail": f"Missing: {', '.join(missing_fields)}." if missing_fields else "Core intake fields are present.",
            "items": missing_fields,
            "source": "Submitted intake form",
        },
        {
            "key": "required_evidence_review",
            "heading": "Required Evidence Review",
            "status": "needs_attention" if evidence_gaps else "complete",
            "action": "Request missing required evidence" if evidence_gaps else "Evidence checklist is ready",
            "detail": (
                "Ask the broker for " + ", ".join(item["label"] for item in evidence_gaps[:5]) + "."
                if evidence_gaps
                else "No required evidence category is currently marked as missing."
            ),
            "items": [item["label"] for item in evidence_gaps],
            "source": "Documents checklist and uploaded document metadata",
            "summary": f"{len(evidence_gaps)} required evidence categories are missing.",
        },
        {
            "key": "control_baseline",
            "heading": "Control Baseline",
            "status": "needs_attention" if control_gaps else "complete",
            "action": "Review control baseline gaps" if control_gaps else "Control baseline is documented",
            "detail": "; ".join(control_gaps) if control_gaps else "MFA, EDR, backups, patching, and security training are documented.",
            "items": control_gaps,
            "source": "Cyber control fields",
            "recommendation": "Tie any quote subjectivities to the control gap and request remediation timing.",
        },
        {
            "key": "broker_follow_up",
            "heading": "Broker Follow-Up",
            "status": "ready" if open_questions or evidence_gaps else "complete",
            "action": "Draft broker follow-up" if open_questions or evidence_gaps else "No follow-up draft needed yet",
            "detail": f"{len(open_questions)} open questions and {len(evidence_gaps)} evidence gaps are available for follow-up.",
            "items": open_questions[:8],
            "source": "Open questions and evidence review",
            "recommendation": "Send a focused broker request using the missing evidence and open question list.",
        },
        {
            "key": "analytics_initialization",
            "heading": "Analytics Initialization",
            "status": "pending_confirmation",
            "action": "Prepare model inputs after confirmation",
            "detail": "Quote, bind, cyber attack, ransomware, breach, interruption, and severity models use stored demo coefficients and the confirmed intake metadata.",
            "items": [
                "No random runtime values are accepted here.",
                "The demo portfolio contains seed analytics data; this new submission is created only after underwriter confirmation.",
            ],
            "source": "Model folder coefficients and confirmed submission metadata",
        },
    ]

    return {
        "status": "awaiting_underwriter_confirmation",
        "generated_at": utc_now(),
        "title": draft.get("title"),
        "insured_name": draft.get("insured_name"),
        "industry": draft.get("industry"),
        "broker": broker.get("firm_name") if broker else draft.get("broker_name", ""),
        "data_policy": "This review uses deterministic extraction, uploaded document metadata, SOP checklist rules, and stored demo model configuration. It does not write the final submission until the underwriter confirms.",
        "steps": steps,
        "actions": [
            {
                "key": "move_to_underwriting_agent",
                "label": "Move to Underwriting Agent",
                "description": "Create the submission record, starter workflow folders, and model-ready metadata, then open the underwriting workspace.",
            },
            {
                "key": "revise_submission_intake_form",
                "label": "Revise the Submission Intake Form",
                "description": "Return to the intake form before creating the final submission record.",
            },
        ],
    }


def create_submission_from_intake(payload):
    draft = sanitize_draft(payload.get("draft") if isinstance(payload.get("draft"), dict) else payload)
    intake_text = str(payload.get("intake_text") or draft.get("intake_text") or "").strip()
    uploaded_documents = sanitize_uploaded_documents(payload.get("uploaded_documents"))
    intake_status = sanitize_intake_status(payload.get("intake_status") if isinstance(payload.get("intake_status"), dict) else {})
    broker = resolve_broker(draft.get("broker_id"), draft.get("broker_name"))
    submission_id = clean_submission_id(draft.get("submission_id")) or make_submission_id(draft)
    if not is_valid_submission_id(submission_id):
        raise ValueError("Invalid submission id.")
    if submission_exists(submission_id):
        raise ValueError("Submission id already exists.")

    now = utc_now()
    folder_path = DATA_DIR / submission_id
    folder_path.mkdir(parents=True, exist_ok=False)

    documents = []
    if intake_text and not uploaded_documents:
        intake_file_name = "intake-form.txt"
        (folder_path / intake_file_name).write_text(intake_text + "\n", encoding="utf-8")
        documents.append(
            {
                "file_name": intake_file_name,
                "file_type": "submission_form",
                "category": "submission",
                "document_types": ["submission_form", "broker_email"],
                "major_categories": ["submission", "communication"],
                "file_created_at": now,
                "received_at": now,
                "description": "Submitted intake form text used to create the submission record",
            }
        )

    documents.extend(write_uploaded_intake_documents(folder_path, uploaded_documents, now))

    applicant = {
        "insured_name": draft["insured_name"],
        "industry": draft["industry"],
        "location": draft["location"],
        "annual_revenue": make_int(draft.get("annual_revenue")),
        "employee_count": make_int(draft.get("employee_count")),
        "records_count": make_int(draft.get("records_count")),
        "technology_profile": draft["technology_profile"],
        "industry_bucket": draft["industry_bucket"],
        "industry_group": draft["industry_bucket"],
    }
    coverage_limit = draft.get("coverage_limit") or "$1,000,000"
    submission = {
        "id": submission_id,
        "title": draft["title"],
        "line_of_business": "Cyber liability",
        "file_created_at": now,
        "received_at": now,
        "updated_at": now,
        "status": draft.get("status") or "New",
        "applicant": applicant,
        "coverage": {
            "lines_requested": draft.get("lines_requested") or ["Cyber liability"],
            "requested_effective_date": draft.get("requested_effective_date") or "",
            "requested_limits": {
                "cyber_liability": coverage_limit,
            },
            "retention_requested": draft.get("retention_requested") or "",
        },
        "broker": build_submission_broker(draft, broker),
        "documents": documents,
        "security_controls": {
            "mfa": draft.get("mfa") or "",
            "edr": draft.get("edr") or "",
            "backup": draft.get("backup") or "",
            "patching": draft.get("patching") or "",
            "security_training": draft.get("security_training") or "",
        },
        "risk_flags": draft.get("risk_flags") or [],
        "open_questions": draft.get("open_questions") or [],
        "intake_status": {
            "intake_mode": intake_status.get("intake_mode"),
            "overall_status": intake_status.get("overall_status"),
            "documents": intake_status.get("documents", []),
        },
        "summary": build_initial_summary(draft),
        "timeline": [
            {
                "date": now,
                "event": "Submission created",
                "description": "Submission created from the Add Submission intake form.",
            }
        ],
    }

    validate_named_schema("submission_metadata", submission)
    write_json(folder_path / "metadata.json", submission)
    create_starter_records(submission_id, now)
    save_submission_intake_status(submission_id, intake_status, draft, now)
    update_search_metadata_entry(submission)
    return get_submission_detail(submission_id)


def find_missing_intake_fields(draft, broker):
    field_checks = [
        ("submission title", draft.get("title")),
        ("insured name", draft.get("insured_name")),
        ("industry", None if draft.get("industry") == "Industry TBD" else draft.get("industry")),
        ("location", draft.get("location")),
        ("annual revenue", draft.get("annual_revenue")),
        ("records count", draft.get("records_count")),
        ("coverage effective date", draft.get("requested_effective_date")),
        ("broker", (broker or {}).get("firm_name") or draft.get("broker_name") or draft.get("broker_id")),
    ]
    return [label for label, value in field_checks if is_missing_value(value)]


def find_missing_evidence(intake_status, uploaded_documents, intake_text):
    received_keys = {
        item["key"]
        for item in intake_status.get("documents", [])
        if item.get("status") in {"received", "waived", "not_applicable"}
    }
    received_keys.update(infer_required_document_keys_from_uploads(uploaded_documents))
    received_keys.update(infer_required_document_keys_from_text("intake-form.txt", intake_text))

    missing = []
    for key, label in REQUIRED_INTAKE_DOCUMENTS:
        checklist_item = next((item for item in intake_status.get("documents", []) if item.get("key") == key), {})
        if checklist_item.get("status") == "needed" and key not in received_keys:
            missing.append({"key": key, "label": label})
    return missing


def infer_required_document_keys_from_uploads(uploaded_documents):
    keys = set()
    for document in uploaded_documents:
        keys.update(infer_required_document_keys_from_text(document.get("file_name"), document.get("extracted_text")))
    return keys


def infer_required_document_keys_from_text(file_name, text):
    if not text:
        return set()
    metadata = infer_document_metadata(file_name or "uploaded-document.txt", text)
    haystack = " ".join(
        [
            str(file_name or ""),
            *(metadata.get("document_types") or []),
            *(metadata.get("major_categories") or []),
            metadata.get("description", ""),
            str(text or "")[:1000],
        ]
    ).lower()
    rules = [
        ("ransomware_supplemental_application", ["ransomware", "supplement"]),
        ("prior_cyber_insurance_policy", ["prior_cyber_insurance_policy", "prior policy", "expiring policy"]),
        ("loss_runs_claims_history", ["loss_runs", "claims_history", "loss run", "claim history", "loss history"]),
        ("financial_information_revenue_breakdown", ["financial_information", "revenue_breakdown", "financial", "revenue"]),
        ("it_security_controls_questionnaire", ["controls questionnaire", "security questionnaire", "it controls"]),
        ("mfa_edr_backup_documentation", ["mfa_documentation", "edr_documentation", "backup_documentation"]),
        ("incident_response_plan", ["incident_response_plan", "incident response", "ir plan"]),
        ("vendor_security_assessment", ["vendor_security_assessment", "third_party_risk_assessment", "security assessment"]),
        ("compliance_documents", ["compliance_documentation", "soc 2", "hipaa", "pci"]),
        ("cyber_application", ["cyber_application", "submission_form", "application"]),
    ]
    return {key for key, keywords in rules if any(keyword in haystack for keyword in keywords)}


def find_control_gaps(draft):
    findings = []
    for field, label in [
        ("mfa", "MFA"),
        ("edr", "EDR"),
        ("backup", "Backup"),
        ("patching", "Patching"),
        ("security_training", "Security training"),
    ]:
        value = str(draft.get(field) or "").strip()
        lowered = value.lower()
        if not value:
            findings.append(f"{label} is not documented")
        elif re.search(r"\b(no|none|partial|pending|weak|annual only|not enabled)\b", lowered):
            findings.append(f"{label}: {value}")
    return findings[:5]


def is_missing_value(value):
    if value in {None, ""}:
        return True
    if isinstance(value, (int, float)) and value <= 0:
        return True
    return False


def draft_submission_with_llm(text, api_key, model):
    if not api_key or not model:
        return None

    prompt = json.dumps(
        {
            "task": "Extract cyber insurance submission intake fields from the provided text.",
            "rules": [
                "Use only the provided text.",
                "If a value is missing, return an empty string, zero, or an empty list.",
                "Risk flags should be concise cyber underwriting concerns.",
                "Open questions should be broker-ready missing-information questions.",
            ],
            "intake_text": text[:6000],
        },
        indent=2,
    )
    payload = {
        "model": model,
        "instructions": "You extract commercial cyber insurance intake fields. Return strict JSON only.",
        "input": prompt,
        "text": {
            "format": {
                "type": "json_schema",
                "name": "cyber_submission_intake",
                "schema": INTAKE_SCHEMA,
                "strict": True,
            }
        },
        "max_output_tokens": 800,
    }

    try:
        response = post_json("https://api.openai.com/v1/responses", payload, api_key)
        return json.loads(extract_json_object(extract_output_text(response)))
    except Exception:
        return None


def extract_application_form_text(file_name, file_bytes):
    suffix = Path(file_name).suffix.lower()
    if suffix == ".txt":
        return file_bytes.decode("utf-8", errors="replace").strip()

    with tempfile.NamedTemporaryFile(suffix=".pdf") as temp_file:
        temp_file.write(file_bytes)
        temp_file.flush()
        return extract_simple_pdf_text(Path(temp_file.name)).strip()


def infer_submission_draft(text):
    lines = parse_key_value_lines(text)
    lower_text = text.lower()
    insured_name = pick(lines, ["insured", "insured name", "applicant", "company", "company name"])
    title = pick(lines, ["title", "submission title"]) or strip_entity_suffix(insured_name)
    industry = pick(lines, ["industry", "business", "operations", "description"])
    location = pick(lines, ["location", "address", "headquarters", "hq"])
    technology_profile = pick(lines, ["technology", "technology profile", "systems", "it environment", "platforms"])
    annual_revenue = pick_number(lines, ["annual revenue", "revenue", "sales"])
    employee_count = pick_number(lines, ["employees", "employee count", "staff"])
    records_count = pick_number(lines, ["records", "records count", "customer records", "patient records"])
    effective_date = pick(lines, ["effective date", "requested effective date"])
    retention = pick(lines, ["retention", "deductible", "self insured retention"])
    limit = pick(lines, ["limit", "requested limit", "cyber limit", "coverage limit"])
    broker_name = pick(lines, ["broker", "broker name", "firm", "broker firm"])
    producer_email = pick_email(text)

    return {
        "title": title or insured_name,
        "insured_name": insured_name,
        "industry": industry or infer_industry(lower_text),
        "location": location,
        "annual_revenue": annual_revenue,
        "employee_count": employee_count,
        "records_count": records_count,
        "technology_profile": technology_profile or infer_technology_profile(lower_text),
        "requested_effective_date": effective_date,
        "retention_requested": retention,
        "coverage_limit": limit,
        "broker_name": broker_name,
        "producer_email": producer_email,
        "mfa": pick(lines, ["mfa", "multi factor authentication", "multi-factor authentication"]),
        "edr": pick(lines, ["edr", "endpoint detection", "endpoint protection"]),
        "backup": pick(lines, ["backup", "backups"]),
        "patching": pick(lines, ["patching", "patch cadence", "critical patches"]),
        "security_training": pick(lines, ["security training", "training", "phishing"]),
        "risk_flags": infer_risk_flags(lower_text),
        "open_questions": infer_open_questions(lower_text),
    }


def sanitize_draft(draft):
    draft = draft if isinstance(draft, dict) else {}
    insured_name = clean_text(draft.get("insured_name")) or "New Cyber Applicant"
    title = clean_text(draft.get("title")) or strip_entity_suffix(insured_name) or insured_name
    industry = clean_text(draft.get("industry")) or "Industry TBD"
    industry_bucket = clean_text(draft.get("industry_bucket")) or resolve_industry_bucket(industry, draft.get("technology_profile"))
    lines_requested = normalize_lines_requested(draft.get("lines_requested"))

    return {
        "submission_id": clean_submission_id(draft.get("submission_id")),
        "title": title,
        "insured_name": insured_name,
        "industry": industry,
        "industry_bucket": industry_bucket,
        "location": clean_text(draft.get("location")),
        "annual_revenue": make_int(draft.get("annual_revenue")),
        "employee_count": make_int(draft.get("employee_count")),
        "records_count": make_int(draft.get("records_count")),
        "technology_profile": clean_text(draft.get("technology_profile")),
        "requested_effective_date": clean_text(draft.get("requested_effective_date")),
        "retention_requested": clean_text(draft.get("retention_requested")),
        "coverage_limit": clean_text(draft.get("coverage_limit")),
        "lines_requested": lines_requested,
        "broker_id": clean_text(draft.get("broker_id")),
        "broker_name": clean_text(draft.get("broker_name")),
        "producer_name": clean_text(draft.get("producer_name")),
        "producer_email": clean_text(draft.get("producer_email")),
        "account_manager_name": clean_text(draft.get("account_manager_name")),
        "account_manager_email": clean_text(draft.get("account_manager_email")),
        "mfa": clean_text(draft.get("mfa")),
        "edr": clean_text(draft.get("edr")),
        "backup": clean_text(draft.get("backup")),
        "patching": clean_text(draft.get("patching")),
        "security_training": clean_text(draft.get("security_training")),
        "risk_flags": normalize_text_list(draft.get("risk_flags")),
        "open_questions": normalize_text_list(draft.get("open_questions")),
        "status": clean_text(draft.get("status")) or "New",
    }


def create_starter_records(submission_id, now):
    for folder in [CHAT_HISTORY_DIR, CLAIMS_DIR, GUIDE_DIR, INTAKE_STATUS_DIR, NOTE_DIR, TASK_DIR, STATES_DIR, UNDERWRITING_DIR]:
        folder.mkdir(parents=True, exist_ok=True)

    (CHAT_HISTORY_DIR / submission_id).mkdir(parents=True, exist_ok=True)
    write_json(
        CLAIMS_DIR / f"{submission_id}.json",
        {
            "submission_id": submission_id,
            "claim_system": "dummy_claims_core",
            "updated_at": now,
            "claims": [],
        },
    )
    write_json(GUIDE_DIR / f"{submission_id}.json", {"submission_id": submission_id, "updated_at": now, "guides": []})
    write_json(NOTE_DIR / f"{submission_id}.json", {"submission_id": submission_id, "updated_at": now, "notes": []})
    write_json(TASK_DIR / f"{submission_id}.json", {"submission_id": submission_id, "updated_at": now, "tasks": []})
    write_json(
        STATES_DIR / f"{submission_id}.json",
        {
            "submission_id": submission_id,
            "updated_at": now,
            "submitted_at": None,
            "stages": [
                {"key": key, "label": label, "checked": False, "locked": False}
                for key, label in DEFAULT_STAGES
            ],
        },
    )
    write_json(
        UNDERWRITING_DIR / f"{submission_id}.json",
        {
            "submission_id": submission_id,
            "updated_at": now,
            "source": "add_submission_intake",
            "maintenance_note": "Starter underwriting record. The backend calculates appetite, evidence, SOP suggestions, broker, and claim context from current data.",
            "components": [],
        },
    )


def save_submission_intake_status(submission_id, intake_status, draft, now):
    record = {
        **intake_status,
        "status_id": submission_id,
        "submission_id": submission_id,
        "updated_at": now,
        "draft": draft,
    }
    INTAKE_STATUS_DIR.mkdir(parents=True, exist_ok=True)
    write_json(INTAKE_STATUS_DIR / f"{submission_id}.json", record)


def sanitize_uploaded_documents(value):
    if not isinstance(value, list):
        return []

    documents = []
    for item in value:
        if not isinstance(item, dict):
            continue
        file_name = Path(str(item.get("file_name") or "uploaded-document.txt")).name
        extracted_text = str(item.get("extracted_text") or "").strip()
        if not file_name or not extracted_text:
            continue
        documents.append(
            {
                "file_name": file_name,
                "extracted_text": extracted_text,
                "upload_id": clean_text(item.get("upload_id")),
            }
        )
    return documents[:20]


def write_uploaded_intake_documents(folder_path, uploaded_documents, now):
    written = []
    for item in uploaded_documents:
        original_name = item["file_name"]
        extracted_text = item["extracted_text"]
        staged_file = get_staged_upload_file(item.get("upload_id"), original_name)
        if staged_file:
            file_name = make_unique_file_name(folder_path, Path(original_name).name)
            shutil.copyfile(staged_file, folder_path / file_name)
            cleanup_staged_upload(item.get("upload_id"))
        else:
            file_name = make_unique_file_name(folder_path, make_text_document_name(original_name))
            (folder_path / file_name).write_text(extracted_text + "\n", encoding="utf-8")

        metadata = infer_document_metadata(original_name, extracted_text)
        written.append(
            {
                "file_name": file_name,
                "file_type": metadata["file_type"],
                "category": metadata["category"],
                "document_types": metadata["document_types"],
                "major_categories": metadata["major_categories"],
                "file_created_at": now,
                "received_at": now,
                "description": metadata["description"],
                "source_file_name": original_name,
            }
        )
    return written


def stage_intake_upload(file_name, file_bytes, extracted_text):
    upload_id = uuid.uuid4().hex
    upload_dir = INTAKE_UPLOAD_DIR / upload_id
    upload_dir.mkdir(parents=True, exist_ok=False)
    safe_file_name = Path(file_name).name
    (upload_dir / safe_file_name).write_bytes(file_bytes)
    write_json(
        upload_dir / "record.json",
        {
            "upload_id": upload_id,
            "file_name": safe_file_name,
            "created_at": utc_now(),
            "text_length": len(extracted_text or ""),
        },
    )
    return upload_id


def get_staged_upload_file(upload_id, file_name):
    upload_key = clean_upload_id(upload_id)
    if not upload_key:
        return None

    candidate = INTAKE_UPLOAD_DIR / upload_key / Path(file_name).name
    if candidate.exists() and candidate.is_file():
        return candidate
    return None


def cleanup_staged_upload(upload_id):
    upload_key = clean_upload_id(upload_id)
    if not upload_key:
        return
    shutil.rmtree(INTAKE_UPLOAD_DIR / upload_key, ignore_errors=True)


def clean_upload_id(value):
    text = str(value or "").strip()
    return text if re.fullmatch(r"[a-f0-9]{32}", text) else ""


def make_text_document_name(file_name):
    stem = Path(file_name).stem.lower()
    safe_stem = re.sub(r"[^a-z0-9._-]+", "-", stem).strip(".-_")
    return f"{safe_stem or 'uploaded-document'}.txt"


def make_unique_file_name(folder_path, file_name):
    candidate = file_name
    stem = Path(file_name).stem
    suffix = Path(file_name).suffix
    counter = 2
    while (folder_path / candidate).exists():
        candidate = f"{stem}-{counter}{suffix}"
        counter += 1
    return candidate


def build_submission_broker(draft, broker):
    broker_id = broker.get("broker_id") if broker else draft.get("broker_id")
    return {
        "broker_id": broker_id or "",
        "firm_name": broker.get("firm_name") if broker else draft.get("broker_name", ""),
        "producer_name": draft.get("producer_name") or ((broker.get("contacts", {}).get("producer") or {}).get("name") if broker else ""),
        "producer_email": draft.get("producer_email") or ((broker.get("contacts", {}).get("producer") or {}).get("email") if broker else ""),
        "account_manager_name": draft.get("account_manager_name") or ((broker.get("contacts", {}).get("account_manager") or {}).get("name") if broker else ""),
        "account_manager_email": draft.get("account_manager_email") or ((broker.get("contacts", {}).get("account_manager") or {}).get("email") if broker else ""),
        "broker_notes": "Linked during Add Submission intake.",
    }


def build_initial_summary(draft):
    insured = draft.get("insured_name") or draft.get("title") or "New applicant"
    industry = draft.get("industry") or "industry TBD"
    risk_flags = draft.get("risk_flags") or []
    return {
        "account_overview": f"{insured} is a cyber liability submission in {industry}.",
        "appetite_fit": "Initial appetite fit requires SOP-based evidence review and cyber control validation.",
        "key_considerations": risk_flags[:4] or ["Complete required cyber evidence checklist."],
        "recommended_next_action": "Follow SOP intake validation, confirm required evidence, and review baseline controls.",
    }


def resolve_broker(broker_id, broker_name):
    if broker_id:
        broker = get_broker(broker_id)
        if broker:
            return broker

    name = str(broker_name or "").strip().lower()
    if not name:
        return None

    return next((broker for broker in list_brokers() if broker.get("firm_name", "").lower() == name), None)


def make_submission_id(draft):
    prefix = next_submission_number()
    slug_source = draft.get("title") or draft.get("insured_name") or f"submission-{prefix}"
    slug = slugify(slug_source)[:48].strip("-") or "new-submission"
    candidate = f"{prefix}-{slug}"
    counter = 2
    while submission_exists(candidate):
        candidate = f"{prefix}-{slug}-{counter}"
        counter += 1
    return candidate


def next_submission_number():
    max_number = 0
    if DATA_DIR.exists():
        for folder in DATA_DIR.iterdir():
            match = re.match(r"^(\d+)-", folder.name)
            if match:
                max_number = max(max_number, int(match.group(1)))
    return f"{max_number + 1:03d}"


def parse_key_value_lines(text):
    values = {}
    for raw_line in str(text or "").splitlines():
        if ":" not in raw_line:
            continue
        key, value = raw_line.split(":", 1)
        key = normalize_key(key)
        value = value.strip()
        if key and value:
            values[key] = value
    return values


def pick(lines, labels):
    for label in labels:
        value = lines.get(normalize_key(label))
        if value:
            return value
    return ""


def pick_number(lines, labels):
    value = pick(lines, labels)
    if value:
        return make_int(value)
    return 0


def pick_email(text):
    match = re.search(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", str(text or ""), re.IGNORECASE)
    return match.group(0) if match else ""


def infer_industry(text):
    if "pharmacy" in text or "health" in text or "hipaa" in text:
        return "Healthcare / pharmacy"
    if "construction" in text or "contractor" in text:
        return "Construction"
    if "payment" in text or "fintech" in text or "pci" in text:
        return "Payment processing and fintech services"
    if "saas" in text or "software" in text or "api" in text:
        return "SaaS software"
    if "manufacturing" in text or "ot" in text:
        return "Manufacturing"
    if "education" in text or "university" in text:
        return "Education"
    if "food" in text or "warehouse" in text or "logistics" in text:
        return "Food distribution and logistics"
    return ""


def infer_technology_profile(text):
    signals = []
    for term in ["Microsoft 365", "EDI", "customer portal", "payment platform", "API", "warehouse system", "OT", "remote access", "cloud"]:
        if term.lower() in text:
            signals.append(term)
    return ", ".join(signals)


def infer_risk_flags(text):
    flags = []
    if "partial mfa" in text or "no mfa" in text or "mfa pending" in text:
        flags.append("MFA gap")
    if "ransomware" in text:
        flags.append("Ransomware exposure")
    if "open claim" in text or "prior claim" in text or "loss" in text:
        flags.append("Prior claim activity")
    if "edi" in text or "warehouse" in text or "ot" in text:
        flags.append("Operational dependency")
    if "pci" in text or "hipaa" in text or "patient" in text or "records" in text:
        flags.append("Sensitive records exposure")
    return flags


def infer_open_questions(text):
    questions = []
    if "mfa" not in text:
        questions.append("Confirm MFA coverage for email, VPN, privileged access, and critical applications.")
    if "backup" not in text:
        questions.append("Provide backup frequency, segmentation, and restore testing evidence.")
    if "loss" not in text and "claim" not in text:
        questions.append("Provide five-year cyber loss runs or no-loss letter.")
    if "edr" not in text:
        questions.append("Confirm EDR deployment scope across servers and endpoints.")
    return questions


def resolve_industry_bucket(industry, technology_profile=""):
    text = f"{industry or ''} {technology_profile or ''}".lower()
    if "health" in text or "pharmacy" in text or "patient" in text or "hipaa" in text:
        return "Healthcare / Pharmacy"
    if "payment" in text or "fintech" in text or "pci" in text:
        return "Fintech / Payments"
    if "education" in text or "school" in text or "university" in text:
        return "Education"
    if "manufacturing" in text or "industrial" in text or "ot" in text:
        return "Manufacturing / OT"
    if "food" in text or "warehouse" in text or "logistics" in text or "cold storage" in text:
        return "Food Distribution / Logistics"
    if "retail" in text or "hospitality" in text or "hotel" in text:
        return "Hospitality / Retail"
    if "marina" in text or "recreation" in text:
        return "Marina / Recreation"
    if "construction" in text or "contractor" in text:
        return "Construction"
    if "saas" in text or "software" in text or "api" in text:
        return "SaaS / Software"
    return "Other"


def normalize_lines_requested(value):
    if isinstance(value, list):
        lines = [clean_text(item) for item in value]
    else:
        lines = re.split(r"[,;\n]+", str(value or "Cyber liability"))
        lines = [clean_text(item) for item in lines]
    lines = [line for line in lines if line]
    return lines or ["Cyber liability"]


def normalize_text_list(value):
    if isinstance(value, list):
        items = value
    else:
        items = re.split(r"[\n;]+", str(value or ""))
    return [clean_text(item.strip(" -\t\r\n")) for item in items if clean_text(item.strip(" -\t\r\n"))]


def extract_json_object(text):
    match = re.search(r"\{.*\}", str(text or ""), re.DOTALL)
    if not match:
        raise ValueError("No JSON object found.")
    return match.group(0)


def clean_submission_id(value):
    text = slugify(value)
    return text[:80].strip("-")


def normalize_key(value):
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


def clean_text(value):
    return str(value or "").strip()


def strip_entity_suffix(value):
    return re.sub(r"\b(inc|inc\.|llc|l\.l\.c\.|corp|co\.|company|ltd|lp)\b\.?", "", str(value or ""), flags=re.I).strip(" ,.-")


def slugify(value):
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", str(value or "").lower())).strip("-")


def make_int(value):
    try:
        return int(float(str(value or "0").replace("$", "").replace(",", "")))
    except (TypeError, ValueError):
        return 0


def utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
