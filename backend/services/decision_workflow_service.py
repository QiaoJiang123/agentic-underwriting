import json
from datetime import datetime, timezone

from backend.config import DECISION_WORKFLOW_DIR
from backend.services.model_service import get_model
from backend.services.schema_service import validate_named_schema
from backend.services.stage_state_service import get_stage_state_record
from backend.services.submission_service import is_valid_submission_id, submission_exists
from backend.services.task_service import get_task_record
from backend.services.underwriting_service import get_underwriting_system_record


DECISION_STATUSES = {"pending", "approved", "referred", "held", "declined"}


def get_decision_workflow_record(submission_id):
    validate_submission(submission_id)
    system = get_underwriting_system_record(submission_id)
    stored = read_stored_workflow(submission_id)
    decisions = normalize_decisions(stored.get("decisions", []))
    gates = build_decision_gates(submission_id, system, decisions)
    record = {
        "submission_id": submission_id,
        "generated_at": utc_now(),
        "updated_at": stored.get("updated_at"),
        "gates": gates,
        "decision_policy": {
            "name": "commercial_cyber_demo_decision_workflow",
            "version": "0.1",
            "description": "Demo workflow for quote readiness, referral, approval, and bind readiness.",
        },
    }
    validate_named_schema("decision_workflow_record", record)
    return record


def save_decision_workflow_record(submission_id, decisions):
    validate_submission(submission_id)
    now = utc_now()
    record = {
        "submission_id": submission_id,
        "updated_at": now,
        "decisions": normalize_decisions(decisions, now),
    }
    DECISION_WORKFLOW_DIR.mkdir(parents=True, exist_ok=True)
    get_workflow_path(submission_id).write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return get_decision_workflow_record(submission_id)


def build_decision_gates(submission_id, system, decisions):
    evidence = system.get("evidence_status") or []
    appetite = system.get("appetite") or {}
    signals = system.get("signals") or []
    claims = system.get("claim_snapshot") or {}
    tasks = get_task_record(submission_id).get("tasks", [])
    stages = get_stage_state_record(submission_id).get("stages", [])
    scores = score_quote_bind_models(system)
    evidence_score = calculate_evidence_score(evidence)
    open_tasks = [task for task in tasks if task.get("status") != "done"]
    referral_required = is_referral_required(appetite, signals, claims)
    checked_stage_keys = {stage.get("key") for stage in stages if stage.get("checked")}
    decision_by_key = {decision.get("gate_key"): decision for decision in decisions}

    gates = [
        make_gate(
            key="quote_readiness",
            label="Quote Readiness",
            status="ready" if evidence_score >= 0.8 and scores["quote"] >= 0.45 and not referral_required else "needs_work",
            score=round((evidence_score * 0.55 + scores["quote"] * 0.45), 3),
            rationale=(
                "Core evidence and quote model support quote preparation."
                if evidence_score >= 0.8 and scores["quote"] >= 0.45
                else "Quote should wait for stronger evidence or model support."
            ),
            blockers=[
                *[item.get("label") for item in evidence if item.get("status") == "missing"][:5],
                *([] if scores["quote"] >= 0.45 else ["Quote model support below readiness threshold"]),
            ],
            actions=[
                "Confirm required evidence and document source quality.",
                "Review quote model drivers before preparing terms.",
            ],
            sources=[
                f"data/submissions/{submission_id}/metadata.json",
                "model/quote_prob.json",
                f"data/underwriting/{submission_id}.json",
            ],
            decision=decision_by_key.get("quote_readiness"),
        ),
        make_gate(
            key="referral",
            label="Referral",
            status="required" if referral_required else "not_required",
            score=round(referral_score(appetite, signals, claims), 3),
            rationale=(
                "Referral is triggered by authority, claims, or high-severity signals."
                if referral_required
                else "No senior referral trigger is active from the current evidence."
            ),
            blockers=build_referral_triggers(appetite, signals, claims),
            actions=[
                "Prepare referral memo with claim summary, controls posture, and proposed terms.",
                "Attach source evidence used for authority review.",
            ],
            sources=[
                f"data/claims/{submission_id}.json",
                f"data/underwriting/{submission_id}.json",
            ],
            decision=decision_by_key.get("referral"),
        ),
        make_gate(
            key="quote_approval",
            label="Quote Approval",
            status="ready_for_approval" if evidence_score >= 0.8 and not referral_required else "pending",
            score=round(min(evidence_score, scores["quote"]), 3),
            rationale=(
                "Underwriter can approve quote terms after final review."
                if evidence_score >= 0.8 and not referral_required
                else "Approval is pending evidence completion or referral disposition."
            ),
            blockers=[
                *([] if evidence_score >= 0.8 else ["Evidence readiness below approval threshold"]),
                *([] if not referral_required else ["Referral disposition required"]),
            ],
            actions=[
                "Review pricing, subjectivities, exclusions, and limit/retention fit.",
                "Record underwriter approval before quote release.",
            ],
            sources=[
                f"data/states/{submission_id}.json",
                "model/quote_prob.json",
            ],
            decision=decision_by_key.get("quote_approval"),
        ),
        make_gate(
            key="bind_readiness",
            label="Bind Readiness",
            status="ready" if scores["bind"] >= 0.4 and not open_tasks and "quote" in checked_stage_keys else "not_ready",
            score=round(scores["bind"], 3),
            rationale=(
                "Bind support is adequate and no open scheduled tasks remain."
                if scores["bind"] >= 0.4 and not open_tasks
                else "Bind should wait for task closure, quote-stage completion, or stronger bind support."
            ),
            blockers=[
                *[f"Open task: {task.get('title')}" for task in open_tasks[:5]],
                *([] if "quote" in checked_stage_keys else ["Quote stage is not checked"]),
                *([] if scores["bind"] >= 0.4 else ["Bind probability below readiness threshold"]),
            ],
            actions=[
                "Confirm signed subjectivities and final broker instructions.",
                "Lock bind package and update submission status after approval.",
            ],
            sources=[
                f"data/task/{submission_id}.json",
                f"data/states/{submission_id}.json",
                "model/bind_prob.json",
            ],
            decision=decision_by_key.get("bind_readiness"),
        ),
    ]
    return gates


def score_quote_bind_models(system):
    try:
        from backend.services.data_retrieval_service import build_feature_lookup, score_model

        submission = system.get("submission") or {}
        if not submission:
            # get_underwriting_system_record intentionally does not echo the full submission.
            from backend.services.submission_service import get_submission_detail

            submission = get_submission_detail(system["submission_id"])["submission"]
        feature_lookup = build_feature_lookup(submission, system)
        quote = score_model(get_model("quote_prob"), feature_lookup)
        bind = score_model(get_model("bind_prob"), feature_lookup)
        return {
            "quote": quote.get("probability", 0.5),
            "bind": bind.get("probability", 0.5),
        }
    except Exception:
        return {"quote": 0.5, "bind": 0.5}


def make_gate(key, label, status, score, rationale, blockers, actions, sources, decision=None):
    return {
        "key": key,
        "label": label,
        "status": status,
        "score": max(0, min(float(score or 0), 1)),
        "rationale": rationale,
        "blockers": [str(item) for item in blockers if item],
        "required_actions": [str(item) for item in actions if item],
        "sources": [str(item) for item in sources if item],
        "decision": decision or {},
    }


def normalize_decisions(decisions, fallback_time=None):
    if isinstance(decisions, dict):
        decisions = decisions.get("decisions", [])
    if not isinstance(decisions, list):
        return []

    normalized = []
    for item in decisions:
        item = item or {}
        gate_key = str(item.get("gate_key") or item.get("key") or "").strip()
        status = str(item.get("status") or "pending").strip().lower()
        if not gate_key or status not in DECISION_STATUSES:
            continue
        normalized.append(
            {
                "gate_key": gate_key,
                "status": status,
                "note": str(item.get("note") or "").strip(),
                "decided_by": str(item.get("decided_by") or "demo_underwriter").strip(),
                "decided_at": item.get("decided_at") or fallback_time or utc_now(),
            }
        )
    return normalized


def calculate_evidence_score(evidence):
    if not evidence:
        return 0
    available = len([item for item in evidence if item.get("status") == "available"])
    return available / len(evidence)


def is_referral_required(appetite, signals, claims):
    authority = str(appetite.get("recommended_authority") or "").lower()
    status = str(appetite.get("status") or "").lower()
    total_incurred = float(claims.get("total_incurred") or 0)
    open_claims = int(claims.get("open_claims") or 0)
    return (
        "senior" in authority
        or "referral" in status
        or open_claims > 0
        or total_incurred >= 100000
        or any(signal.get("severity") == "high" for signal in signals)
    )


def referral_score(appetite, signals, claims):
    score = 0.2
    if "senior" in str(appetite.get("recommended_authority") or "").lower():
        score += 0.3
    if int(claims.get("open_claims") or 0):
        score += 0.25
    if float(claims.get("total_incurred") or 0) >= 100000:
        score += 0.2
    if any(signal.get("severity") == "high" for signal in signals):
        score += 0.25
    return min(score, 1)


def build_referral_triggers(appetite, signals, claims):
    triggers = []
    if "senior" in str(appetite.get("recommended_authority") or "").lower():
        triggers.append("Senior authority recommended")
    if int(claims.get("open_claims") or 0):
        triggers.append("Open claim activity")
    if float(claims.get("total_incurred") or 0) >= 100000:
        triggers.append("High historical incurred losses")
    triggers.extend(
        f"High signal: {signal.get('label')}"
        for signal in signals
        if signal.get("severity") == "high"
    )
    return triggers


def read_stored_workflow(submission_id):
    path = get_workflow_path(submission_id)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def get_workflow_path(submission_id):
    return DECISION_WORKFLOW_DIR / f"{submission_id}.json"


def validate_submission(submission_id):
    if not is_valid_submission_id(submission_id):
        raise ValueError("Invalid submission id.")
    if not submission_exists(submission_id):
        raise FileNotFoundError("Submission not found.")


def utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
