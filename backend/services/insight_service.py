import json
from datetime import datetime, timezone

from backend.config import DATA_DIR
from backend.services.openai_service import extract_output_text, post_json
from backend.services.submission_service import get_submission_detail, is_safe_child, is_valid_submission_id, read_json, submission_exists


INSIGHT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["summary", "timeline"],
    "properties": {
        "summary": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "account_overview",
                "appetite_fit",
                "key_considerations",
                "recommended_next_action",
            ],
            "properties": {
                "account_overview": {"type": "string"},
                "appetite_fit": {"type": "string"},
                "key_considerations": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 1,
                    "maxItems": 6,
                },
                "recommended_next_action": {"type": "string"},
            },
        },
        "timeline": {
            "type": "array",
            "minItems": 1,
            "maxItems": 10,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["date", "event", "description"],
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "ISO date or datetime for the event.",
                    },
                    "event": {"type": "string"},
                    "description": {"type": "string"},
                },
            },
        },
    },
}


def refresh_submission_insights(submission_id, api_key="", model=""):
    if not is_valid_submission_id(submission_id) or not submission_exists(submission_id):
        raise FileNotFoundError("Submission not found.")

    folder_path = (DATA_DIR / submission_id).resolve()
    if not is_safe_child(folder_path, DATA_DIR.resolve()):
        raise ValueError("Invalid submission path.")

    metadata_path = folder_path / "metadata.json"
    submission = get_submission_detail(submission_id)["submission"]
    insights = generate_insights_with_llm(submission, api_key, model) if api_key and model else None
    if not insights:
        insights = generate_local_insights(submission)

    saved_submission = read_json(metadata_path)
    saved_submission["summary"] = insights["summary"]
    saved_submission["timeline"] = insights["timeline"]
    saved_submission["updated_at"] = utc_now()
    metadata_path.write_text(json.dumps(saved_submission, indent=2) + "\n", encoding="utf-8")

    return {
        "insights": insights,
        "submission": get_submission_detail(submission_id)["submission"],
    }


def generate_insights_with_llm(submission, api_key, model):
    prompt = build_insight_prompt(submission)
    structured_payload = {
        "model": model,
        "instructions": build_insight_instructions(),
        "input": prompt,
        "text": {
            "format": {
                "type": "json_schema",
                "name": "submission_summary_timeline",
                "schema": INSIGHT_SCHEMA,
                "strict": True,
            }
        },
        "max_output_tokens": 1200,
    }

    try:
        response = post_json("https://api.openai.com/v1/responses", structured_payload, api_key)
        return sanitize_insights(json.loads(extract_output_text(response)))
    except Exception:
        pass

    fallback_payload = {
        "model": model,
        "instructions": build_insight_instructions() + "\nReturn only JSON that matches the provided schema.",
        "input": prompt,
        "max_output_tokens": 1200,
    }
    try:
        response = post_json("https://api.openai.com/v1/responses", fallback_payload, api_key)
        return sanitize_insights(json.loads(extract_json_object(extract_output_text(response))))
    except Exception:
        return None


def build_insight_instructions():
    return (
        "You create cyber insurance underwriting submission summaries and timelines. "
        "Use only the provided submission metadata and document text excerpts. "
        "Do not invent facts. If information is missing, state what is missing in the summary. "
        "The response must match the JSON schema exactly."
    )


def build_insight_prompt(submission):
    documents = []
    for document in submission.get("documents", []):
        documents.append(
            {
                "file_name": document.get("file_name"),
                "file_type": document.get("file_type"),
                "description": document.get("description"),
                "document_types": document.get("document_types", []),
                "major_categories": document.get("major_categories", []),
                "received_at": document.get("received_at"),
                "content_excerpt": str(document.get("content") or "")[:3000],
            }
        )

    payload = {
        "task": "Refresh this submission's underwriter-facing summary and event timeline.",
        "schema": INSIGHT_SCHEMA,
        "submission": {
            "id": submission.get("id"),
            "title": submission.get("title"),
            "status": submission.get("status"),
            "received_at": submission.get("received_at"),
            "file_created_at": submission.get("file_created_at"),
            "applicant": submission.get("applicant", {}),
            "coverage": submission.get("coverage", {}),
            "security_controls": submission.get("security_controls", {}),
            "existing_timeline": submission.get("timeline", []),
            "documents": documents,
        },
        "timeline_rules": [
            "Include material underwriting events only.",
            "Use dates from metadata or document text when available.",
            "Include uploaded or received document events when they affect underwriting chronology.",
            "Keep each event and description concise.",
        ],
        "summary_rules": [
            "Account overview should identify insured, industry, revenue scale, and cyber exposure.",
            "Appetite fit should be a short underwriting view based on controls, claims, and requested coverage.",
            "Key considerations should be concrete bullets for review.",
            "Recommended next action should be the next practical underwriting action.",
        ],
    }
    return json.dumps(payload, indent=2)


def generate_local_insights(submission):
    applicant = submission.get("applicant", {})
    coverage = submission.get("coverage", {})
    controls = submission.get("security_controls", {})
    documents = submission.get("documents", [])
    insured = applicant.get("insured_name") or submission.get("title") or submission.get("id")
    industry = applicant.get("industry") or "industry not provided"
    revenue = applicant.get("annual_revenue")
    revenue_text = f"${revenue:,.0f}" if isinstance(revenue, (int, float)) else "revenue not provided"
    control_items = [
        label
        for key, label in [
            ("mfa", "MFA"),
            ("edr", "EDR"),
            ("backups", "tested backups"),
            ("incident_response_plan", "incident response plan"),
        ]
        if controls.get(key)
    ]
    coverage_lines = coverage.get("lines_requested") if isinstance(coverage.get("lines_requested"), list) else []

    timeline = sanitize_timeline(submission.get("timeline", []))
    for document in documents:
        received_at = document.get("received_at") or document.get("file_created_at")
        if not received_at:
            continue
        timeline.append(
            {
                "date": received_at,
                "event": f"Received {document.get('file_type', 'document').replace('_', ' ')}",
                "description": document.get("description") or document.get("file_name") or "Document added to submission.",
            }
        )

    timeline = sorted(timeline, key=lambda item: item.get("date") or "")[-10:]

    summary = {
        "account_overview": f"{insured} is a {industry} account with {revenue_text} in annual revenue and requested cyber coverage across {', '.join(coverage_lines) or 'coverage lines not provided'}.",
        "appetite_fit": f"Initial fit depends on validation of {', '.join(control_items) if control_items else 'core cyber controls'} and review of claims, compliance, and vendor exposure documents.",
        "key_considerations": [
            f"{len(documents)} underwriting documents are currently attached.",
            "Confirm all required cyber application, ransomware, loss, financial, control, and compliance evidence is current.",
            "Resolve any document gaps or conflicting representations before quote terms are finalized.",
        ],
        "recommended_next_action": "Review recently added documents, refresh control evidence, and ask for missing clarifications before moving to final terms.",
    }
    return {"summary": summary, "timeline": timeline or fallback_timeline(submission)}


def sanitize_insights(value):
    if not isinstance(value, dict):
        raise ValueError("Insight response must be a JSON object.")
    summary = value.get("summary") if isinstance(value.get("summary"), dict) else {}
    timeline = sanitize_timeline(value.get("timeline"))
    key_considerations = summary.get("key_considerations")
    if not isinstance(key_considerations, list):
        key_considerations = [str(key_considerations or "Review submission documents for missing information.")]

    return {
        "summary": {
            "account_overview": str(summary.get("account_overview") or "").strip(),
            "appetite_fit": str(summary.get("appetite_fit") or "").strip(),
            "key_considerations": [str(item).strip() for item in key_considerations if str(item or "").strip()][:6]
            or ["Review submission documents for missing information."],
            "recommended_next_action": str(summary.get("recommended_next_action") or "").strip(),
        },
        "timeline": timeline,
    }


def sanitize_timeline(value):
    if not isinstance(value, list):
        return []
    items = []
    for item in value:
        if not isinstance(item, dict):
            continue
        date = str(item.get("date") or "").strip()
        event = str(item.get("event") or "").strip()
        description = str(item.get("description") or "").strip()
        if date and event:
            items.append({"date": date, "event": event, "description": description})
    return items[:10]


def fallback_timeline(submission):
    date = submission.get("received_at") or submission.get("file_created_at") or utc_now()
    return [
        {
            "date": date,
            "event": "Submission received",
            "description": "Initial submission metadata is available for underwriting review.",
        }
    ]


def extract_json_object(text):
    value = str(text or "")
    start = value.find("{")
    end = value.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("No JSON object found.")
    return value[start : end + 1]


def utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
