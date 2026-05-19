import json

from backend.config import CLAIMS_DIR, DATA_DIR, MODEL_DIR


ALLOWED_MODELS = {
    "quote_prob",
    "bind_prob",
    "cyber_attack_prob",
    "ransomware_prob",
    "data_breach_prob",
    "business_interruption_prob",
    "claim_severity_prob",
    "industry_propensity",
    "feature_metadata",
}


def get_model(model_name):
    if model_name not in ALLOWED_MODELS:
        raise FileNotFoundError(f"Model not found: {model_name}")

    if model_name == "industry_propensity":
        return build_industry_propensity_model()

    model_path = MODEL_DIR / f"{model_name}.json"
    if not model_path.exists():
        raise FileNotFoundError(f"Model not found: {model_name}")

    return json.loads(model_path.read_text(encoding="utf-8"))


def build_industry_propensity_model():
    model_path = MODEL_DIR / "industry_propensity.json"
    model = json.loads(model_path.read_text(encoding="utf-8")) if model_path.exists() else {}
    buckets = {}

    for metadata_path in sorted(DATA_DIR.glob("*/metadata.json")):
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        submission_id = metadata.get("id") or metadata_path.parent.name
        applicant = metadata.get("applicant", {})
        bucket = applicant.get("industry_bucket") or applicant.get("industry_group") or resolve_industry_bucket(
            applicant.get("industry", ""),
            applicant.get("technology_profile", ""),
        )
        claims = read_claims(submission_id)
        total_incurred = sum(make_number(claim.get("amount_paid")) + make_number(claim.get("amount_reserved")) for claim in claims)

        item = buckets.setdefault(
            bucket,
            {
                "industry": bucket,
                "submission_count": 0,
                "claim_company_count": 0,
                "total_claim_count": 0,
                "total_incurred": 0.0,
            },
        )
        item["submission_count"] += 1
        item["total_claim_count"] += len(claims)
        item["total_incurred"] += total_incurred
        if claims:
            item["claim_company_count"] += 1

    max_average_severity = max(
        (
            item["total_incurred"] / item["total_claim_count"]
            for item in buckets.values()
            if item["total_claim_count"]
        ),
        default=1,
    )
    industry_history = []
    for item in buckets.values():
        submission_count = item["submission_count"] or 1
        total_claim_count = item["total_claim_count"]
        average_claim_severity = item["total_incurred"] / total_claim_count if total_claim_count else 0
        company_claim_rate = item["claim_company_count"] / submission_count
        normalized_severity = average_claim_severity / max_average_severity if max_average_severity else 0
        score = clamp(0.25 + 0.5 * company_claim_rate + 0.25 * normalized_severity, 0, 1)
        industry_history.append(
            {
                "industry": item["industry"],
                "score": round(score, 4),
                "submission_count": item["submission_count"],
                "claim_company_count": item["claim_company_count"],
                "total_claim_count": total_claim_count,
                "attack_frequency": round(company_claim_rate, 4),
                "average_claim_severity": round(average_claim_severity, 2),
                "total_incurred": round(item["total_incurred"], 2),
            }
        )

    industry_history.sort(key=lambda item: (item["score"], item["submission_count"]), reverse=True)
    return {
        "model_name": model.get("model_name", "industry_propensity"),
        "model_type": model.get("model_type", "calculated_benchmark_table"),
        "target": model.get("target", "industry_cyber_propensity_score"),
        "version": model.get("version", "0.2.0-demo"),
        "description": model.get(
            "description",
            "Calculated from dummy submissions and linked claims.",
        ),
        "source_data": model.get(
            "source_data",
            {
                "submissions": "data/submissions/*/metadata.json",
                "claims": "data/claims/*.json",
            },
        ),
        "score_formula": model.get(
            "score_formula",
            "0.25 + 0.50 * company_claim_rate + 0.25 * normalized_average_claim_severity",
        ),
        "portfolio": {
            "submission_count": sum(item["submission_count"] for item in industry_history),
            "claim_company_count": sum(item["claim_company_count"] for item in industry_history),
            "total_claim_count": sum(item["total_claim_count"] for item in industry_history),
        },
        "industry_history": industry_history,
    }


def read_claims(submission_id):
    path = CLAIMS_DIR / f"{submission_id}.json"
    if not path.exists():
        return []

    try:
        claims = json.loads(path.read_text(encoding="utf-8")).get("claims", [])
    except json.JSONDecodeError:
        return []

    return claims if isinstance(claims, list) else []


def resolve_industry_bucket(industry, technology):
    combined = f"{industry} {technology}".lower()
    if any(term in combined for term in ["fintech", "payment", "wallet", "merchant"]):
        return "Fintech / Payments"
    if any(term in combined for term in ["saas", "software", "api", "technology"]):
        return "SaaS / Software"
    if any(term in combined for term in ["health", "senior", "pharmacy", "dental", "clinic", "patient", "hipaa"]):
        return "Healthcare / Pharmacy"
    if any(term in combined for term in ["university", "college", "school", "education", "student"]):
        return "Education"
    if any(term in combined for term in ["manufacturing", "industrial", "robotics", "ot", "fabrication"]):
        return "Manufacturing / OT"
    if any(term in combined for term in ["food", "logistics", "freight", "warehouse", "cold chain"]):
        return "Food Distribution / Logistics"
    if any(term in combined for term in ["hospitality", "hotel", "retail", "restaurant", "cafe", "ecommerce"]):
        return "Hospitality / Retail"
    if any(term in combined for term in ["marina", "recreation", "sailing", "yacht"]):
        return "Marina / Recreation"
    if any(term in combined for term in ["construction", "contracting", "siteworks", "builders"]):
        return "Construction"
    return "Professional Services"


def make_number(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))
