import json

from backend.config import MODEL_DIR


ALLOWED_MODELS = {"quote_prob", "bind_prob", "feature_metadata"}


def get_model(model_name):
    if model_name not in ALLOWED_MODELS:
        raise FileNotFoundError(f"Model not found: {model_name}")

    model_path = MODEL_DIR / f"{model_name}.json"
    if not model_path.exists():
        raise FileNotFoundError(f"Model not found: {model_name}")

    return json.loads(model_path.read_text(encoding="utf-8"))
