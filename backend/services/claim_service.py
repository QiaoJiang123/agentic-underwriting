import json
from datetime import datetime, timezone

from backend.config import CLAIMS_DIR
from backend.services.submission_service import is_valid_submission_id, submission_exists


def get_claim_record(submission_id):
    validate_submission(submission_id)
    path = CLAIMS_DIR / f"{submission_id}.json"

    if not path.exists():
        claims = []
        return {
            "submission_id": submission_id,
            "claim_system": "dummy_claims_core",
            "updated_at": None,
            "claims": claims,
            "aggregate": summarize_claims(claims),
        }

    record = json.loads(path.read_text(encoding="utf-8"))
    claims = sanitize_claims(record.get("claims", []))
    return {
        "submission_id": record.get("submission_id", submission_id),
        "claim_system": record.get("claim_system", "dummy_claims_core"),
        "updated_at": record.get("updated_at"),
        "claims": claims,
        "aggregate": summarize_claims(claims),
    }


def sanitize_claims(claims):
    if not isinstance(claims, list):
        return []

    sanitized = []
    for index, claim in enumerate(claims):
        if not isinstance(claim, dict):
            continue

        claim_id = str(claim.get("claim_id") or f"CLM-DUMMY-{index + 1:03d}").strip()
        sanitized.append(
            {
                "claim_id": claim_id,
                "loss_date": str(claim.get("loss_date") or "").strip(),
                "reported_date": str(claim.get("reported_date") or "").strip(),
                "status": normalize_status(claim.get("status")),
                "claim_type": normalize_label(claim.get("claim_type") or "unknown"),
                "coverage_area": normalize_label(claim.get("coverage_area") or "cyber"),
                "severity": normalize_severity(claim.get("severity")),
                "amount_paid": make_number(claim.get("amount_paid")),
                "amount_reserved": make_number(claim.get("amount_reserved")),
                "cause": str(claim.get("cause") or "").strip(),
                "description": str(claim.get("description") or "").strip(),
                "recovery_status": normalize_label(claim.get("recovery_status") or "unknown"),
            }
        )

    return sorted(sanitized, key=lambda item: item.get("loss_date") or "", reverse=True)


def summarize_claims(claims):
    total_paid = sum(claim["amount_paid"] for claim in claims)
    total_reserved = sum(claim["amount_reserved"] for claim in claims)
    open_claims = [claim for claim in claims if claim["status"] == "open"]
    severity_mix = {}
    for claim in claims:
        severity_mix[claim["severity"]] = severity_mix.get(claim["severity"], 0) + 1

    latest_loss_date = claims[0]["loss_date"] if claims else None
    return {
        "total_claims": len(claims),
        "open_claims": len(open_claims),
        "closed_claims": len(claims) - len(open_claims),
        "total_paid": total_paid,
        "total_reserved": total_reserved,
        "total_incurred": total_paid + total_reserved,
        "latest_loss_date": latest_loss_date,
        "severity_mix": severity_mix,
        "as_of": utc_now(),
    }


def validate_submission(submission_id):
    if not is_valid_submission_id(submission_id):
        raise ValueError("Invalid submission id.")
    if not submission_exists(submission_id):
        raise FileNotFoundError("Submission not found.")


def normalize_status(value):
    text = normalize_label(value)
    return text if text in {"open", "closed"} else "closed"


def normalize_severity(value):
    text = normalize_label(value)
    return text if text in {"low", "moderate", "high"} else "moderate"


def normalize_label(value):
    return str(value or "").strip().lower().replace(" ", "_").replace("-", "_")


def make_number(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
