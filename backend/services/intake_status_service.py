import json
from datetime import datetime, timezone

from backend.config import INTAKE_STATUS_DIR, INTAKE_STATUS_PATH


REQUIRED_INTAKE_DOCUMENTS = [
    ("cyber_application", "Cyber application"),
    ("ransomware_supplemental_application", "Ransomware supplemental application"),
    ("prior_cyber_insurance_policy", "Prior cyber insurance policy"),
    ("loss_runs_claims_history", "Loss runs / claims history"),
    ("financial_information_revenue_breakdown", "Financial information or revenue breakdown"),
    ("it_security_controls_questionnaire", "IT/security controls questionnaire"),
    ("mfa_edr_backup_documentation", "MFA/EDR/backup documentation"),
    ("incident_response_plan", "Incident response plan"),
    ("vendor_security_assessment", "Vendor/security assessment"),
    ("compliance_documents", "Compliance documents"),
]

ALLOWED_DOCUMENT_STATUSES = {"needed", "received", "waived", "not_applicable"}
ALLOWED_INTAKE_MODES = {"manual", "submission_form"}


def get_intake_status_record():
    if not INTAKE_STATUS_PATH.exists():
        return build_default_intake_status()

    record = json.loads(INTAKE_STATUS_PATH.read_text(encoding="utf-8"))
    return sanitize_intake_status(record)


def save_intake_status_record(payload):
    record = sanitize_intake_status(payload)
    record["updated_at"] = utc_now()
    INTAKE_STATUS_DIR.mkdir(parents=True, exist_ok=True)
    INTAKE_STATUS_PATH.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return record


def build_default_intake_status():
    return {
        "status_id": "add_submission_status",
        "updated_at": None,
        "intake_mode": "manual",
        "overall_status": "draft",
        "documents": [
            {
                "key": key,
                "label": label,
                "status": "needed",
                "note": "",
            }
            for key, label in REQUIRED_INTAKE_DOCUMENTS
        ],
        "draft": {},
    }


def sanitize_intake_status(payload):
    payload = payload if isinstance(payload, dict) else {}
    existing_docs = {
        str(item.get("key", "")): item
        for item in payload.get("documents", [])
        if isinstance(item, dict)
    }
    documents = []
    for key, label in REQUIRED_INTAKE_DOCUMENTS:
        item = existing_docs.get(key, {})
        status = str(item.get("status") or "needed").strip()
        documents.append(
            {
                "key": key,
                "label": label,
                "status": status if status in ALLOWED_DOCUMENT_STATUSES else "needed",
                "note": str(item.get("note") or "").strip(),
            }
        )

    mode = str(payload.get("intake_mode") or "manual").strip()
    return {
        "status_id": "add_submission_status",
        "updated_at": payload.get("updated_at"),
        "intake_mode": mode if mode in ALLOWED_INTAKE_MODES else "manual",
        "overall_status": str(payload.get("overall_status") or "draft").strip() or "draft",
        "documents": documents,
        "draft": payload.get("draft") if isinstance(payload.get("draft"), dict) else {},
    }


def utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
