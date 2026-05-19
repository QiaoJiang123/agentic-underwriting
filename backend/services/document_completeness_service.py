import json
import re
from collections import Counter
from pathlib import Path

from backend.config import DATA_DIR, DOCUMENT_REQUIREMENTS_PATH
from backend.services.intake_status_service import REQUIRED_INTAKE_DOCUMENTS
from backend.services.submission_service import get_submission_detail


DEFAULT_ALIASES = {
    "cyber_application": ["cyber_application", "submission_form", "cyber application", "cyber-application"],
    "ransomware_supplemental_application": [
        "ransomware_supplemental_application",
        "ransomware supplement",
        "ransomware-supplemental-application",
    ],
    "prior_cyber_insurance_policy": [
        "prior_cyber_insurance_policy",
        "prior policy",
        "expiring policy",
        "policy_form",
        "prior-cyber-insurance-policy",
    ],
    "loss_runs_claims_history": [
        "loss_runs",
        "claims_history",
        "loss run",
        "loss runs",
        "claims history",
        "loss-runs-claims-history",
    ],
    "financial_information_revenue_breakdown": [
        "financial_information",
        "revenue_breakdown",
        "financial information",
        "revenue breakdown",
        "financial-information-revenue-breakdown",
    ],
    "it_security_controls_questionnaire": [
        "it_security_controls_questionnaire",
        "security_questionnaire",
        "controls questionnaire",
        "security questionnaire",
        "it-security-controls-questionnaire",
    ],
    "mfa_edr_backup_documentation": [
        "mfa_documentation",
        "edr_documentation",
        "backup_documentation",
        "mfa edr backup",
        "mfa-edr-backup-documentation",
    ],
    "incident_response_plan": ["incident_response_plan", "incident response", "ir plan", "incident-response-plan"],
    "vendor_security_assessment": [
        "vendor_security_assessment",
        "third_party_risk_assessment",
        "vendor assessment",
        "security assessment",
        "vendor-security-assessment",
    ],
    "compliance_documents": ["compliance_documentation", "compliance documents", "soc 2", "hipaa", "pci", "compliance-documents"],
}


def get_document_completeness_record(submission_id):
    requirement_record = get_required_document_record()
    detail = get_submission_detail(submission_id)
    submission = detail["submission"]
    submitted_documents = summarize_submitted_documents(submission.get("documents") or [])
    required_documents = requirement_record.get("required_documents") or []

    matches_by_key = {item["key"]: [] for item in required_documents if item.get("key")}
    for document in submitted_documents:
        matched_keys = match_document_to_requirements(document, required_documents)
        document["matched_required_keys"] = matched_keys
        for key in matched_keys:
            matches_by_key.setdefault(key, []).append(document)

    required_status = []
    for item in required_documents:
        key = item.get("key")
        matches = matches_by_key.get(key, [])
        required_status.append(
            {
                "key": key,
                "label": item.get("label") or format_label(key),
                "status": "received" if matches else "missing",
                "source_files": [document.get("file_name") for document in matches if document.get("file_name")],
                "matched_document_types": sorted(
                    {
                        document_type
                        for document in matches
                        for document_type in document.get("document_types", [])
                        if document_type
                    }
                ),
            }
        )

    missing = [item for item in required_status if item["status"] == "missing"]
    received = [item for item in required_status if item["status"] == "received"]
    extras = [document for document in submitted_documents if not document.get("matched_required_keys")]

    return {
        "submission_id": submission_id,
        "requirement_set_id": requirement_record.get("requirement_set_id"),
        "requirement_version": requirement_record.get("version"),
        "requirement_source": requirement_record.get("source"),
        "requirement_path": requirement_record.get("path"),
        "required_count": len(required_status),
        "received_count": len(received),
        "missing_count": len(missing),
        "submitted_count": len(submitted_documents),
        "required_status": required_status,
        "missing_required_documents": missing,
        "received_required_documents": received,
        "submitted_documents": submitted_documents,
        "extra_documents": extras,
    }


def get_required_document_record():
    if DOCUMENT_REQUIREMENTS_PATH.exists():
        record = json.loads(DOCUMENT_REQUIREMENTS_PATH.read_text(encoding="utf-8"))
        record["required_documents"] = sanitize_required_documents(record.get("required_documents"))
        record["path"] = f"data/document_requirements/{DOCUMENT_REQUIREMENTS_PATH.name}"
        return record

    inferred = infer_required_documents_from_portfolio()
    return {
        "requirement_set_id": "commercial_cyber_required_documents_inferred",
        "version": "inferred",
        "line_of_business": "Cyber liability",
        "source": "Inferred from the sample submission portfolio because no stored requirement file was found.",
        "path": "inferred_from_data/submissions",
        "required_documents": inferred,
    }


def sanitize_required_documents(value):
    documents = []
    source = value if isinstance(value, list) else []
    fallback_labels = dict(REQUIRED_INTAKE_DOCUMENTS)
    for item in source:
        if not isinstance(item, dict):
            continue
        key = make_snake(item.get("key"))
        if not key:
            continue
        aliases = item.get("aliases") if isinstance(item.get("aliases"), list) else []
        aliases = [str(alias).strip() for alias in aliases if str(alias).strip()]
        documents.append(
            {
                "key": key,
                "label": str(item.get("label") or fallback_labels.get(key) or format_label(key)).strip(),
                "aliases": unique_list([key, *aliases, *(DEFAULT_ALIASES.get(key) or [])]),
            }
        )

    if documents:
        return documents

    return [
        {
            "key": key,
            "label": label,
            "aliases": unique_list([key, *(DEFAULT_ALIASES.get(key) or [])]),
        }
        for key, label in REQUIRED_INTAKE_DOCUMENTS
    ]


def infer_required_documents_from_portfolio():
    document_type_counts = Counter()
    if DATA_DIR.exists():
        for metadata_path in DATA_DIR.glob("*/metadata.json"):
            try:
                submission = json.loads(metadata_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            for document in submission.get("documents") or []:
                for document_type in document.get("document_types") or []:
                    document_type_counts[make_snake(document_type)] += 1
                document_type_counts[make_snake(document.get("file_type"))] += 1

    documents = []
    for key, label in REQUIRED_INTAKE_DOCUMENTS:
        aliases = DEFAULT_ALIASES.get(key) or []
        common_aliases = [
            document_type
            for document_type, _count in document_type_counts.most_common()
            if key in document_type or any(alias.replace("-", "_") in document_type for alias in aliases)
        ]
        documents.append(
            {
                "key": key,
                "label": label,
                "aliases": unique_list([key, *aliases, *common_aliases[:8]]),
            }
        )
    return documents


def summarize_submitted_documents(documents):
    summarized = []
    for document in documents:
        if not isinstance(document, dict):
            continue
        summarized.append(
            {
                "file_name": document.get("file_name", ""),
                "file_type": document.get("file_type", ""),
                "category": document.get("category", ""),
                "description": document.get("description", ""),
                "document_types": document.get("document_types") or [],
                "major_categories": document.get("major_categories") or [],
                "received_at": document.get("received_at") or document.get("file_created_at"),
            }
        )
    return summarized


def match_document_to_requirements(document, required_documents):
    values = searchable_document_values(document)
    blob = " ".join(values)
    matched = []
    for requirement in required_documents:
        aliases = requirement.get("aliases") or []
        if any(alias_matches_document(alias, values, blob) for alias in aliases):
            matched.append(requirement["key"])
    return sorted(set(matched))


def searchable_document_values(document):
    values = [
        document.get("file_name", ""),
        Path(str(document.get("file_name") or "")).stem,
        document.get("file_type", ""),
        document.get("category", ""),
        document.get("description", ""),
        *(document.get("document_types") or []),
        *(document.get("major_categories") or []),
    ]
    return [normalize_match_text(value) for value in values if normalize_match_text(value)]


def alias_matches_document(alias, values, blob):
    normalized = normalize_match_text(alias)
    if not normalized:
        return False
    if normalized in values:
        return True
    return len(normalized) >= 6 and normalized in blob


def normalize_match_text(value):
    return re.sub(r"\s+", " ", str(value or "").replace("_", " ").replace("-", " ")).strip().lower()


def make_snake(value):
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", str(value or "").lower())).strip("_")


def format_label(value):
    return " ".join(word.capitalize() for word in str(value or "").replace("_", " ").split())


def unique_list(items):
    result = []
    for item in items:
        text = str(item or "").strip()
        if text and text not in result:
            result.append(text)
    return result
