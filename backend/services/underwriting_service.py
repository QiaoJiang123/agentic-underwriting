import json
from datetime import datetime, timezone

from backend.config import UNDERWRITING_DIR
from backend.services.broker_service import get_submission_broker
from backend.services.claim_service import get_claim_record
from backend.services.sop_service import build_sop_guidance
from backend.services.submission_service import get_submission_detail


REQUIRED_EVIDENCE = [
    ("Cyber application", {"cyber_application", "submission_form"}),
    ("Ransomware supplement", {"ransomware_supplemental_application"}),
    ("Prior policy", {"prior_cyber_insurance_policy", "policy_form"}),
    ("Loss runs / claims history", {"loss_runs", "claims_history"}),
    ("Financials / revenue", {"financial_information", "revenue_breakdown"}),
    ("IT/security questionnaire", {"it_security_controls_questionnaire", "security_questionnaire"}),
    ("MFA/EDR/backup evidence", {"mfa_documentation", "edr_documentation", "backup_documentation"}),
    ("Incident response plan", {"incident_response_plan"}),
    ("Vendor assessment", {"vendor_security_assessment", "third_party_risk_assessment"}),
    ("Compliance evidence", {"compliance_documentation"}),
]


def get_underwriting_system_record(submission_id):
    submission = get_submission_detail(submission_id)["submission"]
    claims = get_claim_record(submission_id)
    broker = get_submission_broker(submission)
    evidence = build_evidence_status(submission)
    signals = build_underwriting_signals(submission, claims, evidence)
    appetite = build_appetite(submission, claims, evidence, signals)
    ingredients = build_ingredients(submission, claims, evidence, broker)
    sop_guidance = build_sop_guidance(submission, claims, evidence, appetite, signals, broker)
    actions = build_recommended_actions(submission, claims, evidence, appetite, sop_guidance)
    stored_data = get_underwriting_data(submission_id)
    default_components = build_underwriting_components(
        appetite=appetite,
        claim_snapshot=claims["aggregate"],
        ingredients=ingredients,
        signals=signals,
        evidence=evidence,
        actions=actions,
        broker=broker,
    )
    components = merge_underwriting_components(stored_data.get("components"), default_components)

    return {
        "submission_id": submission_id,
        "generated_at": utc_now(),
        "system_name": "underwriting_decision_workbench",
        "version": "0.1-demo",
        "data_source": {
            "underwriting": f"data/underwriting/{submission_id}.json",
            "claims": f"data/claims/{submission_id}.json",
        },
        "ingredients": ingredients,
        "appetite": appetite,
        "broker": broker,
        "sop_guidance": sop_guidance,
        "signals": signals,
        "evidence_status": evidence,
        "recommended_actions": actions,
        "components": components,
        "claim_review": stored_data.get("claim_review") or build_claim_review(claims),
        "claim_snapshot": claims["aggregate"],
        "claims": claims["claims"],
    }


def get_underwriting_data(submission_id):
    path = UNDERWRITING_DIR / f"{submission_id}.json"
    if not path.exists():
        return {}

    return json.loads(path.read_text(encoding="utf-8"))


def merge_underwriting_components(stored_components, default_components):
    if not stored_components:
        return default_components

    merged = list(stored_components)
    existing_names = {component.get("name") for component in merged if isinstance(component, dict)}
    for component in default_components:
        if component.get("name") not in existing_names:
            merged.append(component)
    return merged


def build_ingredients(submission, claims, evidence, broker=None):
    documents = submission.get("documents", [])
    missing_evidence = [item for item in evidence if item["status"] == "missing"]
    return [
        {
            "name": "Submission metadata",
            "status": "available",
            "detail": "Applicant, coverage request, controls, risk flags, and timeline.",
        },
        {
            "name": "Document evidence",
            "status": "partial" if missing_evidence else "available",
            "detail": f"{len(documents)} files loaded; {len(missing_evidence)} required evidence categories missing.",
        },
        {
            "name": "Claims system",
            "status": "available",
            "detail": f"{claims['aggregate']['total_claims']} claims linked from dummy_claims_core.",
        },
        {
            "name": "Broker database",
            "status": "available" if broker else "missing",
            "detail": (
                f"{broker.get('firm_name')} relationship and contact profile linked."
                if broker
                else "No broker profile is linked to this submission."
            ),
        },
        {
            "name": "Underwriter notes and guide",
            "status": "available",
            "detail": "Stored separately and sent to chat as operating context.",
        },
        {
            "name": "SOP guidance",
            "status": "available",
            "detail": "Commercial cyber SOP rules drive recommendations and next-step suggestions.",
        },
        {
            "name": "Quote/bind models",
            "status": "available",
            "detail": "Demo logistic models are available in the Analytics tab.",
        },
    ]


def build_evidence_status(submission):
    documents = submission.get("documents", [])
    document_lookup = []
    for document in documents:
        types = set(document.get("document_types", []) or [])
        types.add(document.get("file_type", ""))
        document_lookup.append((document, {item for item in types if item}))

    evidence = []
    for label, accepted_types in REQUIRED_EVIDENCE:
        matches = [
            document
            for document, document_types in document_lookup
            if document_types.intersection(accepted_types)
        ]
        evidence.append(
            {
                "label": label,
                "status": "available" if matches else "missing",
                "source_files": [document.get("file_name") for document in matches],
            }
        )

    return evidence


def build_underwriting_signals(submission, claims, evidence):
    controls = submission.get("security_controls", {})
    risk_flags = submission.get("risk_flags", [])
    aggregate = claims["aggregate"]
    missing_count = len([item for item in evidence if item["status"] == "missing"])
    signals = []

    claim_severity = "low"
    if aggregate["open_claims"] or aggregate["total_incurred"] >= 75000:
        claim_severity = "high"
    elif aggregate["total_claims"] or aggregate["total_incurred"] >= 25000:
        claim_severity = "moderate"
    signals.append(
        {
            "label": "Claim history",
            "severity": claim_severity,
            "detail": f"{aggregate['total_claims']} claims, {aggregate['open_claims']} open, ${aggregate['total_incurred']:,.0f} incurred.",
        }
    )

    mfa_value = str(controls.get("mfa", "")).lower()
    signals.append(
        {
            "label": "MFA maturity",
            "severity": "moderate" if "partial" in mfa_value or "pending" in mfa_value else "low",
            "detail": controls.get("mfa") or "MFA representation is not available.",
        }
    )

    signals.append(
        {
            "label": "Evidence readiness",
            "severity": "moderate" if missing_count else "low",
            "detail": f"{missing_count} required evidence categories missing.",
        }
    )

    if risk_flags:
        signals.append(
            {
                "label": "Submission risk flags",
                "severity": "moderate",
                "detail": "; ".join(risk_flags[:3]),
            }
        )

    return signals


def build_appetite(submission, claims, evidence, signals):
    aggregate = claims["aggregate"]
    missing_count = len([item for item in evidence if item["status"] == "missing"])
    has_high_signal = any(signal["severity"] == "high" for signal in signals)

    if has_high_signal:
        status = "Referral review"
        rationale = "Open or high-severity claim activity requires senior underwriting review."
    elif missing_count >= 3:
        status = "Hold for evidence"
        rationale = "The submission is missing several required underwriting evidence categories."
    elif aggregate["total_claims"] or any(signal["severity"] == "moderate" for signal in signals):
        status = "Proceed with conditions"
        rationale = "The account may be workable, but claims or control gaps should drive terms and subjectivities."
    else:
        status = "In appetite"
        rationale = "Core evidence and claim posture do not show a major blocker."

    return {
        "status": status,
        "rationale": rationale,
        "recommended_authority": "standard_underwriter" if status != "Referral review" else "senior_referral",
    }


def build_recommended_actions(submission, claims, evidence, appetite, sop_guidance=None):
    missing = [item["label"] for item in evidence if item["status"] == "missing"]
    sop_suggestions = (sop_guidance or {}).get("suggestions") or []
    actions = []

    for suggestion in sop_suggestions[:4]:
        recommendation = suggestion.get("recommendation")
        step_label = suggestion.get("step_label")
        if recommendation:
            actions.append(f"SOP - {step_label}: {recommendation}")

    if claims["aggregate"]["open_claims"]:
        actions.append("Review open claim notes and confirm current reserves before quote release.")
    if missing:
        actions.append(f"Request missing evidence: {', '.join(missing[:4])}.")
    if appetite["status"] == "Proceed with conditions":
        actions.append("Draft subjectivities tied to MFA, backups, and claim-control remediation.")
    if appetite["status"] == "Referral review":
        actions.append("Send claim summary, control posture, and recommended terms to senior referral.")
    if not actions:
        actions.append("Proceed to quote analytics and prepare terms subject to final document review.")

    return actions[:5]


def build_underwriting_components(appetite, claim_snapshot, ingredients, signals, evidence, actions, broker=None):
    missing_evidence = [item for item in evidence if item["status"] == "missing"]
    high_signals = [signal for signal in signals if signal["severity"] == "high"]
    moderate_signals = [signal for signal in signals if signal["severity"] == "moderate"]
    available_ingredients = len([item for item in ingredients if item["status"] == "available"])
    open_claims = int(claim_snapshot.get("open_claims", 0) or 0)
    total_incurred = float(claim_snapshot.get("total_incurred", 0) or 0)
    recommended_action = actions[0] if actions else "Prepare terms after document review."

    return [
        {
            "name": "Intake & Eligibility",
            "status": appetite.get("status") or "TBD",
            "tone": "alert" if high_signals else "watch",
            "owner": "Underwriting",
            "stage": "Intake",
            "data_sources": ["submission metadata", "coverage request", "appetite rules"],
            "detail": appetite.get("rationale")
            or "Review account appetite, authority path, and requested coverage fit.",
        },
        {
            "name": "Evidence Review",
            "status": f"{len(missing_evidence)} missing" if missing_evidence else "Complete",
            "tone": "watch" if missing_evidence else "good",
            "owner": "Underwriting Assistant",
            "stage": "Document Review",
            "data_sources": ["document metadata", "required evidence map"],
            "detail": (
                "Missing evidence includes "
                + ", ".join(item["label"] for item in missing_evidence[:3])
                + "."
                if missing_evidence
                else "Core cyber underwriting evidence is available for review."
            ),
        },
        {
            "name": "Controls Review",
            "status": "Review" if moderate_signals or high_signals else "Stable",
            "tone": "alert" if high_signals else "watch" if moderate_signals else "good",
            "owner": "Cyber Risk",
            "stage": "Risk Review",
            "data_sources": ["security controls", "risk flags", "questionnaires"],
            "detail": ", ".join(signal["label"] for signal in signals[:3]) or "No control signals available.",
        },
        {
            "name": "Claim Review",
            "status": f"{claim_snapshot.get('total_claims', 0)} claims",
            "tone": "alert" if open_claims or total_incurred >= 75000 else "watch" if total_incurred > 0 else "good",
            "owner": "Claims Liaison",
            "stage": "Loss Review",
            "data_sources": ["dummy_claims_core", "loss runs"],
            "detail": (
                f"{open_claims} open and {format_currency(total_incurred)} total incurred "
                "in linked historical claims."
            ),
        },
        {
            "name": "Broker Relationship",
            "status": broker.get("service_tier", "Linked") if broker else "Missing",
            "tone": "good" if broker and broker.get("relationship_metrics", {}).get("data_quality_score", 0) >= 80 else "watch",
            "owner": "Broker Management",
            "stage": "Broker Review",
            "data_sources": ["broker database", "submission broker notes"],
            "detail": (
                f"{broker.get('firm_name')} relationship profile linked; "
                f"producer {broker.get('submission_contact', {}).get('producer_name', 'TBD')}."
                if broker
                else "No broker profile is linked to this submission."
            ),
        },
        {
            "name": "Pricing & Terms",
            "status": "Model-ready",
            "tone": "good",
            "owner": "Pricing",
            "stage": "Terms",
            "data_sources": ["quote_prob", "bind_prob", "feature metadata"],
            "detail": "Quote and bind probability models are available in the Analytic Dashboard.",
        },
        {
            "name": "Authority & Next Action",
            "status": format_label(appetite.get("recommended_authority") or "TBD"),
            "tone": "alert" if high_signals else "watch",
            "owner": "Underwriting Manager",
            "stage": "Authority",
            "data_sources": ["appetite result", "recommended actions"],
            "detail": recommended_action,
        },
        {
            "name": "System Coverage",
            "status": f"{available_ingredients}/{len(ingredients) or 0} inputs",
            "tone": "good" if available_ingredients == len(ingredients) else "watch",
            "owner": "Platform",
            "stage": "System",
            "data_sources": ["submission documents", "notes", "guides", "models", "claims"],
            "detail": "Submission documents, metadata, notes, guides, models, and claims are connected for review.",
        },
    ]


def build_claim_review(claims):
    aggregate = claims.get("aggregate", {})
    return {
        "claim_system": claims.get("claim_system", "dummy_claims_core"),
        "review_focus": "Review open claims, incurred amounts, and claim causes before quote or referral decisions.",
        "summary": (
            f"{aggregate.get('total_claims', 0)} historical claims; "
            f"{aggregate.get('open_claims', 0)} open; "
            f"{format_currency(float(aggregate.get('total_incurred', 0) or 0))} incurred."
        ),
        "data_fields": [
            "claim_id",
            "loss_date",
            "reported_date",
            "claim_type",
            "status",
            "severity",
            "amount_paid",
            "amount_reserved",
            "cause",
            "description",
        ],
    }


def format_currency(value):
    return f"${value:,.0f}"


def format_label(value):
    words = str(value or "").replace("_", " ").replace("-", " ").split()
    return " ".join(word[:1].upper() + word[1:] for word in words) or "TBD"


def utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
