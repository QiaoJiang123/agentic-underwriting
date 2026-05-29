import json
from copy import deepcopy

from backend.config import MODEL_DIR


MODEL_GOVERNANCE_PATH = MODEL_DIR / "governance.json"


def get_model_governance_registry():
    if not MODEL_GOVERNANCE_PATH.exists():
        return default_governance_registry()
    registry = json.loads(MODEL_GOVERNANCE_PATH.read_text(encoding="utf-8"))
    return normalize_registry(registry)


def get_model_governance(model_name=None):
    registry = get_model_governance_registry()
    models = registry.get("models", {})
    if model_name:
        record = models.get(model_name)
        if not record:
            raise FileNotFoundError(f"Model governance not found: {model_name}")
        return {
            "source": registry.get("source", "model/governance.json"),
            "registry_version": registry.get("registry_version"),
            "default_policy": registry.get("default_policy", {}),
            "model": record,
        }
    return registry


def attach_governance(model_name, model_record):
    package = get_model_governance(model_name)
    return {
        **deepcopy(model_record),
        "governance": package["model"],
    }


def normalize_registry(registry):
    normalized = deepcopy(registry or {})
    normalized.setdefault("registry_version", "0.1.0")
    normalized.setdefault("source", "model/governance.json")
    normalized.setdefault("default_policy", default_policy())
    models = normalized.setdefault("models", {})
    for model_name, record in list(models.items()):
        models[model_name] = normalize_model_governance(model_name, record, normalized["default_policy"])
    return normalized


def normalize_model_governance(model_name, record, default):
    record = deepcopy(record or {})
    record.setdefault("model_name", model_name)
    record.setdefault("display_name", model_name.replace("_", " ").title())
    record.setdefault("approval_status", default.get("approval_status", "demo_only_not_approved"))
    record.setdefault("decision_owner", default.get("decision_owner", "human_underwriter"))
    record.setdefault("allowed_use", default.get("allowed_use", "decision_support_only"))
    record.setdefault("limitations", default.get("limitations", []))
    record.setdefault("required_controls", default.get("required_controls", []))
    record.setdefault("override_required_reason", default.get("override_required_reason", True))
    record.setdefault("monitoring_metrics", [])
    return record


def default_governance_registry():
    return {
        "registry_version": "0.1.0",
        "source": "generated_default",
        "default_policy": default_policy(),
        "models": {},
    }


def default_policy():
    return {
        "approval_status": "demo_only_not_approved",
        "decision_owner": "human_underwriter",
        "allowed_use": "decision_support_only",
        "override_required_reason": True,
        "limitations": [
            "Uses synthetic demo data.",
            "Requires human underwriting review before any final decision.",
        ],
        "required_controls": [
            "Show source data and model version.",
            "Capture override reason when model guidance is not followed.",
        ],
    }
