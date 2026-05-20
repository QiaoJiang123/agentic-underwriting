import json
import re
from datetime import datetime, timezone

from backend.config import DATA_DIR
from backend.services.broker_service import get_submission_broker
from backend.services.claim_service import get_claim_record
from backend.services.submission_service import (
    get_search_metadata,
    is_valid_submission_id,
    submission_exists,
)
from backend.services.underwriting_service import build_evidence_status


INDUSTRY_RATE_FACTORS = {
    "Fintech / Payments": 1.38,
    "Healthcare / Pharmacy": 1.32,
    "Education": 1.2,
    "Manufacturing / OT": 1.18,
    "SaaS / Software": 1.12,
    "Food Distribution / Logistics": 1.05,
    "Hospitality / Retail": 1.02,
    "Marina / Recreation": 0.96,
    "Construction": 0.93,
    "Professional Services": 0.9,
}


def get_portfolio_queue():
    rows = [build_queue_row(record) for record in list_submission_metadata()]
    rows.sort(key=lambda row: (priority_rank(row.get("priority")), -row.get("age_days", 0), row.get("id", "")))
    industry_mix = build_industry_mix(rows)
    broker_mix = build_broker_mix(rows)
    overview = build_portfolio_overview(rows)

    return {
        "generated_at": utc_now(),
        "overview": overview,
        "queue": rows,
        "dashboard": {
            "pipeline": build_pipeline_breakdown(rows),
            "industry_mix": industry_mix,
            "broker_mix": broker_mix,
            "severity_bands": build_severity_bands(rows),
            "decision_readiness": build_readiness_metrics(rows),
        },
    }


def get_clearance_review(submission_id):
    submission = read_submission_metadata(submission_id)
    broker = get_submission_broker(submission)
    evidence = build_evidence_status(submission)
    claims = get_claim_record(submission_id)
    matches = find_clearance_matches(submission_id, submission)
    applicant = submission.get("applicant", {})
    coverage = submission.get("coverage", {})
    missing = [item for item in evidence if item.get("status") == "missing"]
    claim_snapshot = claims.get("aggregate") or {}
    checks = [
        make_check(
            "named_insured",
            "Named insured",
            "pass" if applicant.get("insured_name") else "hold",
            applicant.get("insured_name") or "Named insured is missing.",
        ),
        make_check(
            "broker_link",
            "Broker appointment",
            "pass" if broker else "warn",
            broker.get("firm_name") if broker else "No broker database record is linked.",
        ),
        make_check(
            "duplicate_scan",
            "Duplicate submission scan",
            "warn" if matches else "pass",
            f"{len(matches)} possible related account(s)." if matches else "No strong duplicate signal in the demo portfolio.",
        ),
        make_check(
            "effective_date",
            "Effective date",
            "pass" if coverage.get("requested_effective_date") else "warn",
            coverage.get("requested_effective_date") or "Requested effective date is missing.",
        ),
        make_check(
            "required_evidence",
            "Required evidence",
            "hold" if len(missing) >= 3 else "warn" if missing else "pass",
            f"{len(missing)} required evidence categories missing.",
        ),
        make_check(
            "claim_clearance",
            "Claim clearance",
            "warn" if claim_snapshot.get("open_claims") else "pass",
            f"{claim_snapshot.get('total_claims', 0)} linked claims, {claim_snapshot.get('open_claims', 0)} open.",
        ),
    ]
    status = "clear"
    if any(check["status"] == "hold" for check in checks):
        status = "hold"
    elif any(check["status"] == "warn" for check in checks):
        status = "review"

    return {
        "submission_id": submission_id,
        "generated_at": utc_now(),
        "status": status,
        "summary": clearance_summary(status, matches, missing, claim_snapshot),
        "checks": checks,
        "possible_matches": matches,
        "sources": [
            f"data/submissions/{submission_id}/metadata.json",
            "data/metadata.json",
            f"data/claims/{submission_id}.json",
            "data/brokers/brokers.json",
        ],
    }


def get_external_research(submission_id):
    submission = read_submission_metadata(submission_id)
    applicant = submission.get("applicant", {})
    controls = submission.get("security_controls", {})
    broker = get_submission_broker(submission)
    technology = str(applicant.get("technology_profile") or "")
    vendor_signal = bool(re.search(r"edi|portal|payment|api|cloud|vendor|provider|msp", technology, re.I))

    tasks = [
        research_task("business_registry", "Business registry verification", "not_connected", "Confirm legal entity, state registration, and trade names."),
        research_task("sanctions", "Sanctions and watchlist screen", "not_connected", "Check OFAC and commercial watchlists before quote release."),
        research_task("domain_security", "Domain and email security", "not_connected", "Review SPF, DKIM, DMARC, exposed login portals, and domain age."),
        research_task("security_rating", "External security rating", "not_connected", "Pull security scorecard or ASM rating when a connector is added."),
        research_task("breach_news", "Breach and incident news", "not_connected", "Search for public breach, ransomware, lawsuit, and regulatory events."),
        research_task("vendor_dependency", "Critical vendor dependency", "derived", "Material dependency noted in submission." if vendor_signal else "No material dependency signal in metadata."),
    ]

    return {
        "submission_id": submission_id,
        "generated_at": utc_now(),
        "profile": {
            "insured_name": applicant.get("insured_name"),
            "industry": applicant.get("industry"),
            "industry_bucket": get_industry_bucket(applicant),
            "location": applicant.get("location"),
            "technology_profile": technology,
            "broker": broker.get("firm_name") if broker else None,
        },
        "research_status": "connector_ready",
        "research_note": "This demo prepares the external research surface, but live enrichment connectors are not attached.",
        "signals_from_submission": [
            f"MFA: {controls.get('mfa', 'TBD')}",
            f"EDR: {controls.get('edr', 'TBD')}",
            f"Backups: {controls.get('backup', 'TBD')}",
            f"Technology: {technology or 'TBD'}",
        ],
        "research_tasks": tasks,
        "sources": [f"data/submissions/{submission_id}/metadata.json", "future_external_connectors"],
    }


def get_rating_quote(submission_id):
    submission = read_submission_metadata(submission_id)
    broker = get_submission_broker(submission)
    claims = get_claim_record(submission_id)
    evidence = build_evidence_status(submission)
    metrics = compute_workbench_metrics(submission, claims, evidence, broker)
    applicant = submission.get("applicant", {})
    coverage = submission.get("coverage", {})
    controls = submission.get("security_controls", {})
    revenue = make_number(applicant.get("annual_revenue"))
    records = make_number(applicant.get("records_count"))
    requested_limit = max([parse_money(value) for value in (coverage.get("requested_limits") or {}).values()] or [1_000_000])
    requested_retention = coverage.get("retention_requested") or "$10,000"
    industry_bucket = get_industry_bucket(applicant)
    industry_factor = INDUSTRY_RATE_FACTORS.get(industry_bucket, 1.0)
    control_factor = build_control_factor(controls)
    claim_factor = 1 + min(make_number((claims.get("aggregate") or {}).get("total_incurred")) / 250_000, 0.8)
    if make_number((claims.get("aggregate") or {}).get("open_claims")):
        claim_factor += 0.25
    evidence_factor = 1 + (1 - metrics["evidence_ratio"]) * 0.22
    broker_quality = make_number((broker or {}).get("relationship_metrics", {}).get("data_quality_score") or 70)
    broker_factor = 0.96 if broker_quality >= 85 else 1.04 if broker_quality < 70 else 1.0
    limit_factor = max(0.75, min(1.55, requested_limit / 2_000_000))
    base_premium = max(3_500, revenue * 0.00055 + records * 0.012)
    modifier_product = industry_factor * control_factor * claim_factor * evidence_factor * broker_factor * limit_factor
    indicated_premium = round_to_hundreds(base_premium * modifier_product)
    premium_low = round_to_hundreds(indicated_premium * 0.9)
    premium_high = round_to_hundreds(indicated_premium * 1.15)
    subjectivities = build_quote_subjectivities(evidence, controls, claims)
    referral_reasons = build_referral_reasons(submission, claims, evidence, metrics)
    status = "underwriter_review"
    if metrics["quote_readiness"] >= 78 and len(subjectivities) <= 1 and not referral_reasons:
        status = "ready_for_underwriter_terms"
    elif referral_reasons:
        status = "senior_referral_review"

    return {
        "submission_id": submission_id,
        "generated_at": utc_now(),
        "rating_engine": "demo_cyber_rating_v0",
        "status": status,
        "authority_path": "Senior referral" if referral_reasons else "Underwriter delegated review",
        "referral_reasons": referral_reasons,
        "quote_readiness": metrics["quote_readiness"],
        "requested_limit": requested_limit,
        "recommended_limit": recommended_limit(requested_limit, metrics),
        "requested_retention": requested_retention,
        "recommended_retention": recommended_retention(requested_retention, metrics),
        "indicated_premium": indicated_premium,
        "premium_range": {"low": premium_low, "high": premium_high},
        "calculation": {
            "formula": "max(3500, annual_revenue * 0.00055 + records_count * 0.012) * industry * controls * claims * evidence * broker * limit",
            "base_premium": round_to_hundreds(base_premium),
            "modifier_product": round(modifier_product, 4),
            "range_low_factor": 0.9,
            "range_high_factor": 1.15,
            "inputs": {
                "annual_revenue": revenue,
                "records_count": records,
                "requested_limit": requested_limit,
                "industry_bucket": industry_bucket,
                "evidence_ratio": metrics["evidence_ratio"],
                "broker_data_quality_score": broker_quality,
                "claims_total_incurred": make_number((claims.get("aggregate") or {}).get("total_incurred")),
                "claims_open_count": make_number((claims.get("aggregate") or {}).get("open_claims")),
            },
        },
        "modifiers": [
            modifier("Industry", industry_factor, f"{industry_bucket} benchmark factor."),
            modifier("Controls", control_factor, "MFA, EDR, backup, patching, and training posture."),
            modifier("Claims", claim_factor, "Linked claim count, incurred value, and open claim signal."),
            modifier("Evidence", evidence_factor, "Required underwriting evidence completeness."),
            modifier("Broker", broker_factor, "Broker data quality and relationship signal."),
            modifier("Limit", limit_factor, "Requested limit relativity."),
        ],
        "coverage_terms": [
            term("Cyber Liability", requested_limit, "Included"),
            term("Privacy Liability", min(requested_limit, 2_000_000), "Included"),
            term("Business Interruption", min(requested_limit, 1_000_000), "Subject to waiting period"),
            term("Cyber Crime", min(requested_limit, 500_000), "Sublimited"),
            term("Incident Response", min(requested_limit, 250_000), "Included"),
        ],
        "subjectivities": subjectivities,
        "sources": [
            f"data/submissions/{submission_id}/metadata.json",
            f"data/claims/{submission_id}.json",
            "data/brokers/brokers.json",
            "model/quote_prob.json",
            "model/bind_prob.json",
        ],
    }


def build_queue_row(submission):
    submission_id = submission.get("id")
    claims = get_claim_record(submission_id)
    evidence = build_evidence_status(submission)
    broker = get_submission_broker(submission)
    metrics = compute_workbench_metrics(submission, claims, evidence, broker)
    applicant = submission.get("applicant", {})
    claim_snapshot = claims.get("aggregate") or {}
    priority = "Ready"
    status = submission.get("status", "New")
    referral_reasons = build_referral_reasons(submission, claims, evidence, metrics)
    if "declin" in status.lower():
        priority = "Closed"
    elif referral_reasons:
        priority = "Referral"
    elif metrics["quote_readiness"] < 78 or "referral" in status.lower() or metrics["risk_signal_count"] >= 3:
        priority = "Review"
    return {
        "id": submission_id,
        "title": submission.get("title"),
        "insured_name": applicant.get("insured_name"),
        "industry": applicant.get("industry"),
        "industry_bucket": get_industry_bucket(applicant),
        "status": status,
        "priority": priority,
        "received_at": submission.get("received_at"),
        "age_days": age_days(submission.get("received_at") or submission.get("file_created_at")),
        "broker_name": broker.get("firm_name") if broker else None,
        "broker_id": (broker or {}).get("broker_id"),
        "quote_readiness": metrics["quote_readiness"],
        "evidence_ratio": metrics["evidence_ratio"],
        "risk_signal_count": metrics["risk_signal_count"],
        "open_claims": claim_snapshot.get("open_claims", 0),
        "total_claims": claim_snapshot.get("total_claims", 0),
        "total_incurred": claim_snapshot.get("total_incurred", 0),
        "referral_reasons": referral_reasons,
        "next_action": queue_next_action(priority, metrics, evidence, claim_snapshot, referral_reasons),
    }


def compute_workbench_metrics(submission, claims, evidence, broker):
    available = len([item for item in evidence if item.get("status") == "available"])
    evidence_ratio = available / len(evidence) if evidence else 0.0
    risk_flags = submission.get("risk_flags") or []
    applicant = submission.get("applicant") or {}
    coverage = submission.get("coverage") or {}
    controls = submission.get("security_controls") or {}
    claim_snapshot = claims.get("aggregate") or {}
    broker_quality = make_number((broker or {}).get("relationship_metrics", {}).get("data_quality_score") or 70)
    control_gaps = count_control_gaps(controls)
    risk_signal_count = len(risk_flags) + control_gaps + int(make_number(claim_snapshot.get("open_claims")) > 0)
    revenue = make_number(applicant.get("annual_revenue"))
    records = make_number(applicant.get("records_count"))
    requested_limit = max([parse_money(value) for value in (coverage.get("requested_limits") or {}).values()] or [0])
    total_claims = make_number(claim_snapshot.get("total_claims"))
    open_claims = make_number(claim_snapshot.get("open_claims"))
    total_incurred = make_number(claim_snapshot.get("total_incurred"))
    industry_factor = INDUSTRY_RATE_FACTORS.get(get_industry_bucket(applicant), 1.0)
    exposure_drag = min(revenue / 50_000_000, 6) + min(records / 250_000, 5) + min(requested_limit / 5_000_000, 4)
    claims_drag = min(total_incurred / 12_000, 18) + open_claims * 7 + max(total_claims - 1, 0) * 1.4
    industry_drag = max((industry_factor - 1) * 9, -1.5)
    demo_variance = stable_demo_variance(submission.get("id"))
    readiness = (
        54
        + evidence_ratio * 27
        + min(broker_quality, 100) * 0.13
        + demo_variance
        - claims_drag
        - control_gaps * 3.6
        - len(risk_flags) * 2.2
        - exposure_drag
        - industry_drag
    )
    return {
        "evidence_ratio": round(evidence_ratio, 4),
        "quote_readiness": round(clamp(readiness, 0, 100), 1),
        "risk_signal_count": int(risk_signal_count),
    }


def build_portfolio_overview(rows):
    count = len(rows)
    return {
        "submission_count": count,
        "ready_count": sum(1 for row in rows if row.get("priority") == "Ready"),
        "review_count": sum(1 for row in rows if row.get("priority") == "Review"),
        "referral_count": sum(1 for row in rows if row.get("priority") == "Referral"),
        "avg_quote_readiness": round(sum(row.get("quote_readiness", 0) for row in rows) / count, 1) if count else 0,
        "open_claims": sum(row.get("open_claims", 0) for row in rows),
        "total_incurred": round(sum(row.get("total_incurred", 0) for row in rows), 2),
    }


def build_pipeline_breakdown(rows):
    labels = ["Ready", "Review", "Referral", "Closed"]
    return [
        {"label": label, "count": sum(1 for row in rows if row.get("priority") == label)}
        for label in labels
    ]


def build_industry_mix(rows):
    groups = {}
    for row in rows:
        bucket = row.get("industry_bucket") or "Unknown"
        group = groups.setdefault(
            bucket,
            {"industry": bucket, "submission_count": 0, "claims": 0, "open_claims": 0, "total_incurred": 0, "readiness_total": 0},
        )
        group["submission_count"] += 1
        group["claims"] += row.get("total_claims", 0)
        group["open_claims"] += row.get("open_claims", 0)
        group["total_incurred"] += row.get("total_incurred", 0)
        group["readiness_total"] += row.get("quote_readiness", 0)
    result = []
    for group in groups.values():
        count = group["submission_count"] or 1
        result.append(
            {
                "industry": group["industry"],
                "submission_count": group["submission_count"],
                "claim_count": group["claims"],
                "open_claims": group["open_claims"],
                "total_incurred": round(group["total_incurred"], 2),
                "avg_readiness": round(group["readiness_total"] / count, 1),
                "claim_rate": round(group["claims"] / count, 4),
            }
        )
    return sorted(result, key=lambda item: (item["total_incurred"], item["claim_count"]), reverse=True)


def build_broker_mix(rows):
    groups = {}
    for row in rows:
        broker = row.get("broker_name") or "Unassigned"
        group = groups.setdefault(broker, {"broker_name": broker, "submission_count": 0, "ready": 0, "referral": 0, "readiness_total": 0})
        group["submission_count"] += 1
        group["ready"] += int(row.get("priority") == "Ready")
        group["referral"] += int(row.get("priority") == "Referral")
        group["readiness_total"] += row.get("quote_readiness", 0)
    result = []
    for group in groups.values():
        count = group["submission_count"] or 1
        result.append({**group, "avg_readiness": round(group["readiness_total"] / count, 1)})
    return sorted(result, key=lambda item: (item["submission_count"], item["avg_readiness"]), reverse=True)


def build_severity_bands(rows):
    counts = {"Low": 0, "Moderate": 0, "High": 0}
    for row in rows:
        if row.get("total_incurred", 0) >= 75_000 or row.get("open_claims", 0) > 0:
            counts["High"] += 1
        elif row.get("total_incurred", 0) >= 25_000 or row.get("risk_signal_count", 0) >= 3:
            counts["Moderate"] += 1
        else:
            counts["Low"] += 1
    return [{"label": label, "count": counts[label]} for label in ["Low", "Moderate", "High"]]


def build_readiness_metrics(rows):
    count = len(rows) or 1
    return {
        "evidence_complete": sum(1 for row in rows if row.get("evidence_ratio", 0) >= 1),
        "model_ready": sum(1 for row in rows if row.get("quote_readiness", 0) >= 70),
        "referral_needed": sum(1 for row in rows if row.get("priority") == "Referral"),
        "evidence_complete_ratio": round(sum(1 for row in rows if row.get("evidence_ratio", 0) >= 1) / count, 4),
        "model_ready_ratio": round(sum(1 for row in rows if row.get("quote_readiness", 0) >= 70) / count, 4),
    }


def find_clearance_matches(submission_id, submission):
    target_name = normalize_name((submission.get("applicant") or {}).get("insured_name") or submission.get("title"))
    target_bucket = get_industry_bucket(submission.get("applicant") or {})
    matches = []
    for candidate in list_submission_metadata():
        if candidate.get("id") == submission_id:
            continue
        candidate_name = normalize_name((candidate.get("applicant") or {}).get("insured_name") or candidate.get("title"))
        score = token_similarity(target_name, candidate_name)
        same_bucket = get_industry_bucket(candidate.get("applicant") or {}) == target_bucket
        if score >= 0.45 or (score >= 0.3 and same_bucket):
            matches.append(
                {
                    "id": candidate.get("id"),
                    "title": candidate.get("title"),
                    "insured_name": (candidate.get("applicant") or {}).get("insured_name"),
                    "status": candidate.get("status"),
                    "industry_bucket": get_industry_bucket(candidate.get("applicant") or {}),
                    "similarity": round(score, 3),
                    "reason": "Name similarity and same industry bucket." if same_bucket else "Name similarity.",
                }
            )
    return sorted(matches, key=lambda item: item["similarity"], reverse=True)[:6]


def list_submission_metadata():
    records = []
    for item in get_search_metadata().get("submissions", []):
        submission_id = item.get("id")
        if not submission_id:
            continue
        try:
            records.append(read_submission_metadata(submission_id))
        except (FileNotFoundError, ValueError, json.JSONDecodeError):
            continue
    return records


def read_submission_metadata(submission_id):
    if not is_valid_submission_id(submission_id) or not submission_exists(submission_id):
        raise FileNotFoundError("Submission not found.")
    path = DATA_DIR / submission_id / "metadata.json"
    return json.loads(path.read_text(encoding="utf-8"))


def count_control_gaps(controls):
    text = " ".join(str(controls.get(key) or "") for key in ["mfa", "edr", "backup", "patching", "security_training"]).lower()
    gaps = 0
    if "partial" in text or "pending" in text or "not documented" in text:
        gaps += 1
    for key in ["mfa", "edr", "backup", "patching", "security_training"]:
        if not str(controls.get(key) or "").strip():
            gaps += 1
    return gaps


def build_control_factor(controls):
    factor = 1.0
    text = {key: str(value or "").lower() for key, value in (controls or {}).items()}
    factor -= 0.06 if text.get("mfa") and "partial" not in text.get("mfa", "") else 0
    factor -= 0.05 if "deployed" in text.get("edr", "") or "crowdstrike" in text.get("edr", "") else 0
    factor -= 0.04 if "restore" in text.get("backup", "") or "immutable" in text.get("backup", "") else 0
    factor += 0.08 if "partial" in text.get("mfa", "") or "pending" in text.get("mfa", "") else 0
    factor += 0.06 if not text.get("edr") else 0
    factor += 0.05 if not text.get("patching") or "not documented" in text.get("patching", "") else 0
    factor += 0.04 if not text.get("security_training") or "not documented" in text.get("security_training", "") else 0
    return round(clamp(factor, 0.82, 1.3), 3)


def build_quote_subjectivities(evidence, controls, claims):
    subjectivities = []
    missing = [item.get("label") for item in evidence if item.get("status") == "missing"]
    if missing:
        subjectivities.append(f"Receive and review missing evidence: {', '.join(missing[:4])}.")
    if "partial" in str((controls or {}).get("mfa", "")).lower():
        subjectivities.append("Confirm full MFA rollout for email, remote access, and privileged accounts.")
    if not str((controls or {}).get("patching", "")).strip() or "not documented" in str((controls or {}).get("patching", "")).lower():
        subjectivities.append("Document critical patching SLA and remediation ownership.")
    if not str((controls or {}).get("security_training", "")).strip() or "not documented" in str((controls or {}).get("security_training", "")).lower():
        subjectivities.append("Confirm annual security awareness training and phishing simulation cadence.")
    if (claims.get("aggregate") or {}).get("open_claims"):
        subjectivities.append("Resolve open claim status and reserve adequacy before bind.")
    return subjectivities[:6]


def build_referral_reasons(submission, claims, evidence, metrics):
    claim_snapshot = claims.get("aggregate") or {}
    coverage = submission.get("coverage") or {}
    requested_limit = max([parse_money(value) for value in (coverage.get("requested_limits") or {}).values()] or [0])
    missing_count = len([item for item in evidence if item.get("status") == "missing"])
    reasons = []
    if make_number(claim_snapshot.get("open_claims")) > 0:
        reasons.append("Open cyber claim requires authority review")
    if make_number(claim_snapshot.get("total_incurred")) >= 150_000:
        reasons.append("Historical incurred losses exceed $150,000")
    if metrics["quote_readiness"] < 50:
        reasons.append("Quote readiness is below 50%")
    if missing_count >= 5:
        reasons.append(f"{missing_count} required evidence categories are missing")
    if requested_limit >= 5_000_000 and metrics["quote_readiness"] < 55:
        reasons.append("Requested limit is high relative to current readiness")
    return reasons


def queue_next_action(priority, metrics, evidence, claim_snapshot, referral_reasons=None):
    missing = [item.get("label") for item in evidence if item.get("status") == "missing"]
    if priority == "Referral" and referral_reasons:
        return f"Send to senior referral for: {', '.join(referral_reasons[:2])}."
    if priority == "Review":
        return "Underwriter review: confirm evidence, claims, controls, and quote authority."
    if priority == "Referral":
        return "Prepare referral note with claims, controls, and evidence gaps."
    if missing:
        return f"Request missing evidence: {', '.join(missing[:2])}."
    if claim_snapshot.get("total_claims"):
        return "Review loss history and confirm remediation before terms."
    if metrics["quote_readiness"] >= 82:
        return "Move to rating and quote package review."
    return "Complete underwriting review and SOP checks."


def clearance_summary(status, matches, missing, claim_snapshot):
    if status == "hold":
        return f"Hold clearance until required evidence is resolved. {len(missing)} categories are missing."
    if status == "review":
        return f"Clearance review needed. {len(matches)} duplicate signals and {claim_snapshot.get('open_claims', 0)} open claims found."
    return "Clearance is clean in the demo portfolio. No strong duplicate, broker, evidence, or claim blockers were found."


def make_check(key, label, status, detail):
    return {"key": key, "label": label, "status": status, "detail": detail}


def research_task(key, label, status, detail):
    return {"key": key, "label": label, "status": status, "detail": detail}


def modifier(label, factor, rationale):
    return {"label": label, "factor": round(make_number(factor), 3), "rationale": rationale}


def term(label, limit, condition):
    return {"coverage": label, "limit": round_to_hundreds(limit), "condition": condition}


def recommended_limit(requested_limit, metrics):
    if metrics["quote_readiness"] >= 82:
        return requested_limit
    if metrics["quote_readiness"] >= 65:
        return min(requested_limit, 2_000_000)
    return min(requested_limit, 1_000_000)


def recommended_retention(requested_retention, metrics):
    parsed = parse_money(requested_retention)
    floor = 25_000 if metrics["quote_readiness"] < 65 else 10_000
    return money(max(parsed or floor, floor))


def get_industry_bucket(applicant):
    return (
        applicant.get("industry_bucket")
        or applicant.get("industry_group")
        or resolve_industry_bucket(applicant.get("industry", ""), applicant.get("technology_profile", ""))
    )


def resolve_industry_bucket(industry, technology):
    combined = f"{industry} {technology}".lower()
    if re.search(r"fintech|payment|wallet|merchant", combined):
        return "Fintech / Payments"
    if re.search(r"saas|software|api|technology", combined):
        return "SaaS / Software"
    if re.search(r"health|senior|pharmacy|dental|clinic|patient|hipaa", combined):
        return "Healthcare / Pharmacy"
    if re.search(r"university|college|school|education|student", combined):
        return "Education"
    if re.search(r"manufacturing|industrial|robotics|ot|fabrication", combined):
        return "Manufacturing / OT"
    if re.search(r"food|logistics|freight|warehouse|cold chain", combined):
        return "Food Distribution / Logistics"
    if re.search(r"hospitality|hotel|retail|restaurant|cafe|ecommerce", combined):
        return "Hospitality / Retail"
    if re.search(r"marina|recreation|sailing|yacht", combined):
        return "Marina / Recreation"
    if re.search(r"construction|contracting|siteworks|builders", combined):
        return "Construction"
    return "Professional Services"


def priority_rank(priority):
    return {"Referral": 0, "Review": 1, "Ready": 2, "Closed": 3}.get(priority, 4)


def normalize_name(value):
    return re.sub(r"[^a-z0-9 ]+", " ", str(value or "").lower())


def token_similarity(left, right):
    left_tokens = set(left.split())
    right_tokens = set(right.split())
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def stable_demo_variance(value):
    seed = str(value or "")
    if not seed:
        return 0
    weighted = sum((index + 1) * ord(character) for index, character in enumerate(seed))
    return ((weighted % 141) / 10) - 7


def parse_money(value):
    try:
        return float(re.sub(r"[^0-9.]", "", str(value or "")) or 0)
    except (TypeError, ValueError):
        return 0.0


def make_number(value):
    try:
        if isinstance(value, str):
            return float(value.replace(",", "").replace("$", ""))
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def round_to_hundreds(value):
    return int(round(make_number(value) / 100) * 100)


def money(value):
    return f"${round_to_hundreds(value):,}"


def clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))


def age_days(value):
    if not value:
        return 0
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return 0
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return max((datetime.now(timezone.utc) - parsed).days, 0)


def utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
