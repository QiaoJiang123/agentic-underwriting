from datetime import datetime, timezone

from backend.services.claim_service import get_claim_record
from backend.services.decision_workflow_service import get_decision_workflow_record
from backend.services.model_governance_service import get_model_governance
from backend.services.portfolio_workbench_service import (
    get_clearance_review,
    get_external_research,
    get_rating_quote,
)
from backend.services.schema_service import validate_named_schema
from backend.services.submission_service import get_submission_detail
from backend.services.underwriting_service import get_underwriting_system_record


CORE_MODEL_NAMES = [
    "quote_prob",
    "bind_prob",
    "cyber_attack_prob",
    "ransomware_prob",
    "data_breach_prob",
    "business_interruption_prob",
    "claim_severity_prob",
    "industry_propensity",
]


def get_decision_package(submission_id, package_type="review"):
    submission = get_submission_detail(submission_id)["submission"]
    underwriting = get_underwriting_system_record(submission_id)
    claims = get_claim_record(submission_id)
    workflow = get_decision_workflow_record(submission_id)
    rating = get_rating_quote(submission_id)
    clearance = get_clearance_review(submission_id)
    external_research = get_external_research(submission_id)
    evidence = summarize_evidence(underwriting.get("evidence_status", []))
    package = {
        "submission_id": submission_id,
        "package_type": normalize_package_type(package_type),
        "generated_at": utc_now(),
        "package_name": "commercial_cyber_underwriting_decision_package",
        "account": build_account_section(submission),
        "broker": underwriting.get("broker") or {},
        "evidence": evidence,
        "claims": {
            "aggregate": claims.get("aggregate", {}),
            "claim_ids": [claim.get("claim_id") for claim in claims.get("claims", [])],
            "claims": claims.get("claims", []),
        },
        "underwriting": {
            "appetite": underwriting.get("appetite", {}),
            "signals": underwriting.get("signals", []),
            "recommended_actions": underwriting.get("recommended_actions", []),
            "sop_guidance": underwriting.get("sop_guidance", {}),
        },
        "workflow": {
            "gates": workflow.get("gates", []),
            "decision_policy": workflow.get("decision_policy", {}),
        },
        "rating_quote": {
            "rating_engine": rating.get("rating_engine"),
            "status": rating.get("status"),
            "authority_path": rating.get("authority_path"),
            "quote_readiness": rating.get("quote_readiness"),
            "indicated_premium": rating.get("indicated_premium"),
            "premium_range": rating.get("premium_range"),
            "recommended_limit": rating.get("recommended_limit"),
            "recommended_retention": rating.get("recommended_retention"),
            "subjectivities": rating.get("subjectivities", []),
            "referral_reasons": rating.get("referral_reasons", []),
            "calculation": rating.get("calculation", {}),
            "modifiers": rating.get("modifiers", []),
        },
        "clearance": {
            "status": clearance.get("status"),
            "summary": clearance.get("summary"),
            "checks": clearance.get("checks", []),
        },
        "external_research": {
            "research_status": external_research.get("research_status"),
            "research_tasks": external_research.get("research_tasks", []),
        },
        "model_governance": build_model_governance_section(),
        "underwriter_controls": build_underwriter_controls(workflow, evidence, rating),
        "citations": collect_citations(submission_id, underwriting, workflow, rating, clearance, external_research),
    }
    validate_named_schema("decision_package_record", package)
    return package


def build_account_section(submission):
    applicant = submission.get("applicant") or {}
    coverage = submission.get("coverage") or {}
    return {
        "title": submission.get("title"),
        "insured_name": applicant.get("insured_name"),
        "status": submission.get("status"),
        "industry": applicant.get("industry"),
        "industry_bucket": applicant.get("industry_bucket") or applicant.get("industry_group"),
        "location": applicant.get("location"),
        "annual_revenue": applicant.get("annual_revenue"),
        "employee_count": applicant.get("employee_count"),
        "records_count": applicant.get("records_count"),
        "requested_effective_date": coverage.get("requested_effective_date"),
        "requested_limits": coverage.get("requested_limits", {}),
        "retention_requested": coverage.get("retention_requested"),
    }


def summarize_evidence(evidence_status):
    received = [item for item in evidence_status or [] if item.get("status") == "available"]
    missing = [item for item in evidence_status or [] if item.get("status") == "missing"]
    total = len(evidence_status or [])
    return {
        "required_count": total,
        "received_count": len(received),
        "missing_count": len(missing),
        "received": received,
        "missing": missing,
        "readiness_ratio": round(len(received) / total, 4) if total else 0,
    }


def build_model_governance_section():
    models = []
    for model_name in CORE_MODEL_NAMES:
        try:
            record = get_model_governance(model_name)["model"]
        except FileNotFoundError:
            continue
        models.append(
            {
                "model_name": record.get("model_name", model_name),
                "display_name": record.get("display_name"),
                "model_family": record.get("model_family"),
                "version": record.get("version"),
                "approval_status": record.get("approval_status"),
                "allowed_use": record.get("allowed_use"),
                "decision_owner": record.get("decision_owner"),
                "override_required_reason": record.get("override_required_reason"),
                "monitoring_metrics": record.get("monitoring_metrics", []),
            }
        )
    return {
        "source": "model/governance.json",
        "models": models,
    }


def build_underwriter_controls(workflow, evidence, rating):
    controls = [
        "Review citations and source documents before relying on the package.",
        "Confirm missing evidence and open subjectivities before quote or bind.",
        "Document reason for any model override or workflow gate override.",
    ]
    if evidence.get("missing_count"):
        controls.append("Do not bind until required evidence gaps are resolved or explicitly waived.")
    if rating.get("referral_reasons"):
        controls.append("Route referral package for authority review before releasing terms.")
    if any(gate.get("decision") for gate in workflow.get("gates", [])):
        controls.append("Confirm stored gate decisions still match the latest evidence and claims.")
    return controls


def collect_citations(submission_id, *records):
    citations = [
        {"source": f"data/submissions/{submission_id}/metadata.json", "section": "submission"},
        {"source": f"data/claims/{submission_id}.json", "section": "claims"},
        {"source": f"data/underwriting/{submission_id}.json", "section": "underwriting"},
        {"source": "model/governance.json", "section": "model_governance"},
    ]
    seen = {item["source"] for item in citations}
    for record in records:
        for source in extract_sources(record):
            if source not in seen:
                citations.append({"source": source, "section": "supporting_record"})
                seen.add(source)
    return citations


def extract_sources(value):
    if isinstance(value, dict):
        sources = []
        if isinstance(value.get("sources"), list):
            sources.extend(str(source) for source in value["sources"] if source)
        for child in value.values():
            sources.extend(extract_sources(child))
        return sources
    if isinstance(value, list):
        sources = []
        for item in value:
            sources.extend(extract_sources(item))
        return sources
    return []


def normalize_package_type(package_type):
    value = str(package_type or "review").strip().lower()
    return value if value in {"quote", "referral", "bind", "review"} else "review"


def utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
