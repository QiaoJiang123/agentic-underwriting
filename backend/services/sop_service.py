import json
import re

from backend.config import SOP_METADATA_PATH, SOP_PATH


def get_sop_record():
    if not SOP_PATH.exists():
        return {
            "sop_id": "cyber-commercial-underwriting-sop",
            "version": "missing",
            "name": "Commercial Cyber Underwriting SOP",
            "principles": [],
            "steps": [],
        }

    return json.loads(SOP_PATH.read_text(encoding="utf-8"))


def get_sop_metadata_record():
    if not SOP_METADATA_PATH.exists():
        return {
            "metadata_id": "cyber-commercial-underwriting-sop-metadata",
            "sop_id": "cyber-commercial-underwriting-sop",
            "source_file": "data/sop/cyber_underwriting_sop.json",
            "selection_rules": {
                "default_step_ids": ["required_evidence_review", "broker_follow_up"],
                "max_selected_steps": 4,
            },
            "steps": [],
        }

    return json.loads(SOP_METADATA_PATH.read_text(encoding="utf-8"))


def select_relevant_sop_steps(prompt_text, max_steps=None):
    metadata = get_sop_metadata_record()
    sop = get_sop_record()
    prompt = normalize_text(prompt_text)
    rules = metadata.get("selection_rules") or {}
    step_limit = max_steps or int(rules.get("max_selected_steps") or 4)
    sop_steps = {step.get("step_id"): step for step in sop.get("steps", []) if isinstance(step, dict)}

    scored_steps = []
    for step_metadata in metadata.get("steps") or []:
        if not isinstance(step_metadata, dict):
            continue
        score, reasons = score_sop_step(prompt, step_metadata)
        if score <= 0:
            continue
        step_id = step_metadata.get("step_id")
        step = sop_steps.get(step_id, {})
        scored_steps.append(
            {
                "score": score,
                "reasons": reasons,
                "metadata": step_metadata,
                "step": step,
            }
        )

    if not scored_steps and has_explicit_sop_request(prompt):
        default_ids = rules.get("default_step_ids") or []
        for step_id in default_ids:
            step_metadata = next((item for item in metadata.get("steps", []) if item.get("step_id") == step_id), {})
            step = sop_steps.get(step_id, {})
            if step:
                scored_steps.append(
                    {
                        "score": 1,
                        "reasons": ["Default SOP step for broad SOP request."],
                        "metadata": step_metadata,
                        "step": step,
                    }
                )

    selected = sorted(scored_steps, key=lambda item: item["score"], reverse=True)[:step_limit]
    return {
        "sop_id": sop.get("sop_id"),
        "name": sop.get("name"),
        "version": sop.get("version"),
        "metadata_source": "data/sop/metadata.json",
        "sop_source": "data/sop/cyber_underwriting_sop.json",
        "selected_steps": [format_selected_sop_step(item) for item in selected],
    }


def score_sop_step(prompt, step_metadata):
    score = 0
    reasons = []

    label = normalize_text(step_metadata.get("label"))
    if label and label in prompt:
        score += 5
        reasons.append(f"Matched label: {step_metadata.get('label')}")

    for keyword in step_metadata.get("keywords") or []:
        normalized = normalize_text(keyword)
        if normalized and normalized in prompt:
            score += 3
            reasons.append(f"Matched keyword: {keyword}")

    for intent in step_metadata.get("intents") or []:
        normalized = normalize_text(intent)
        if normalized and all(part in prompt for part in normalized.split()[:3]):
            score += 2
            reasons.append(f"Matched intent: {intent}")

    return score, reasons[:5]


def format_selected_sop_step(item):
    metadata = item["metadata"]
    step = item["step"]
    step_id = metadata.get("step_id") or step.get("step_id")
    return {
        "step_id": step_id,
        "label": step.get("label") or metadata.get("label") or str(step_id or "SOP step"),
        "priority": step.get("priority") or metadata.get("priority") or "medium",
        "goal": step.get("goal", ""),
        "suggestion_template": step.get("suggestion_template", ""),
        "keywords": metadata.get("keywords", [])[:10],
        "related_data": metadata.get("related_data", []),
        "score": item["score"],
        "reasons": item["reasons"],
    }


def has_explicit_sop_request(prompt):
    return any(term in prompt for term in ["sop", "procedure", "standard operating", "operating procedure"])


def normalize_text(value):
    return re.sub(r"\s+", " ", str(value or "").replace("_", " ").replace("-", " ")).strip().lower()


def build_sop_guidance(submission, claims, evidence, appetite, signals, broker=None):
    sop = get_sop_record()
    steps = {step.get("step_id"): step for step in sop.get("steps", []) if isinstance(step, dict)}
    suggestions = []

    applicant = submission.get("applicant") or {}
    coverage = submission.get("coverage") or {}
    controls = submission.get("security_controls") or {}
    risk_flags = submission.get("risk_flags") or []
    open_questions = submission.get("open_questions") or []
    missing_evidence = [item for item in evidence if item.get("status") == "missing"]
    claim_snapshot = claims.get("aggregate") or {}
    broker_metrics = (broker or {}).get("relationship_metrics") or {}
    revenue = make_number(applicant.get("annual_revenue"))
    records = make_number(applicant.get("records_count"))

    missing_intake = []
    for label, value in [
        ("insured name", applicant.get("insured_name")),
        ("industry", applicant.get("industry")),
        ("location", applicant.get("location")),
        ("annual revenue", applicant.get("annual_revenue")),
        ("records count", applicant.get("records_count")),
        ("coverage effective date", coverage.get("requested_effective_date")),
        ("broker", (submission.get("broker") or {}).get("firm_name") or (broker or {}).get("firm_name")),
    ]:
        if value in {None, "", 0}:
            missing_intake.append(label)

    if missing_intake:
        add_suggestion(
            suggestions,
            steps,
            "intake_validation",
            "Complete intake fields",
            f"Missing: {', '.join(missing_intake[:6])}.",
            "Validate intake fields before moving deeper into risk review.",
        )

    if missing_evidence:
        add_suggestion(
            suggestions,
            steps,
            "required_evidence_review",
            "Request missing required evidence",
            f"{len(missing_evidence)} required evidence categories are missing.",
            "Ask the broker for " + ", ".join(item.get("label", "evidence") for item in missing_evidence[:5]) + ".",
        )

    control_gap = describe_control_gap(controls)
    if control_gap:
        add_suggestion(
            suggestions,
            steps,
            "control_baseline",
            "Review control baseline gaps",
            control_gap,
            "Tie any quote subjectivities to the control gap and request remediation timing.",
        )

    if claim_snapshot.get("open_claims") or make_number(claim_snapshot.get("total_incurred")) >= 75000:
        add_suggestion(
            suggestions,
            steps,
            "claims_review",
            "Review prior claim severity",
            f"{claim_snapshot.get('open_claims', 0)} open claims and ${make_number(claim_snapshot.get('total_incurred')):,.0f} incurred.",
            "Confirm claim closure, remediation, current reserves, and whether terms need claim-related conditions.",
        )

    if open_questions or missing_evidence:
        add_suggestion(
            suggestions,
            steps,
            "broker_follow_up",
            "Draft broker follow-up",
            f"{len(open_questions)} open questions and {len(missing_evidence)} evidence gaps are available for follow-up.",
            "Send a focused broker request using the missing evidence and open question list.",
        )

    high_signals = [signal for signal in signals if signal.get("severity") == "high"]
    appetite_status = str(appetite.get("status") or "").lower()
    if high_signals or "referral" in appetite_status or records >= 1_000_000:
        add_suggestion(
            suggestions,
            steps,
            "referral_authority",
            "Check referral authority",
            "Referral trigger found from high signal, appetite status, or high records exposure.",
            "Prepare referral rationale before quote release.",
        )

    if not missing_evidence and not high_signals:
        add_suggestion(
            suggestions,
            steps,
            "pricing_terms",
            "Review pricing and terms",
            "Core evidence is available and no high-severity SOP blocker is present.",
            "Use quote/bind analytics with evidence quality, claims, and controls to prepare terms.",
        )

    if broker_metrics and make_number(broker_metrics.get("data_quality_score")) < 75:
        add_suggestion(
            suggestions,
            steps,
            "broker_follow_up",
            "Use structured broker request",
            "Broker data quality is below the SOP target.",
            "Ask for concise, field-level answers and attach the evidence checklist.",
        )

    return {
        "sop_id": sop.get("sop_id"),
        "version": sop.get("version"),
        "name": sop.get("name"),
        "principles": sop.get("principles", []),
        "suggestions": suggestions[:8],
    }


def add_suggestion(suggestions, steps, step_id, title, rationale, recommendation):
    step = steps.get(step_id, {})
    suggestions.append(
        {
            "step_id": step_id,
            "step_label": step.get("label", step_id.replace("_", " ").title()),
            "priority": step.get("priority", "medium"),
            "title": title,
            "rationale": rationale,
            "recommendation": recommendation,
        }
    )


def describe_control_gap(controls):
    findings = []
    for field, label in [
        ("mfa", "MFA"),
        ("edr", "EDR"),
        ("backup", "Backup"),
        ("patching", "Patching"),
        ("security_training", "Security training"),
    ]:
        value = str(controls.get(field) or "").strip()
        lowered = value.lower()
        if not value:
            findings.append(f"{label} is not documented")
        elif re.search(r"\b(no|none|partial|pending|weak|annual only|not enabled)\b", lowered):
            findings.append(f"{label}: {value}")

    return "; ".join(findings[:4])


def make_number(value):
    try:
        return float(str(value or "0").replace("$", "").replace(",", ""))
    except (TypeError, ValueError):
        return 0.0
