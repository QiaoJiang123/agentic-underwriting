import json
from datetime import datetime, timezone

from backend.config import STATES_DIR
from backend.services.submission_service import is_valid_submission_id, submission_exists


def get_stage_state_record(submission_id):
    validate_submission(submission_id)
    path = get_stage_state_path(submission_id)

    if not path.exists():
        return {
            "submission_id": submission_id,
            "updated_at": None,
            "submitted_at": None,
            "stages": [],
        }

    record = json.loads(path.read_text(encoding="utf-8"))
    return {
        "submission_id": record.get("submission_id", submission_id),
        "updated_at": record.get("updated_at"),
        "submitted_at": record.get("submitted_at"),
        "stages": sanitize_stages(record.get("stages", [])),
    }


def save_stage_state_record(submission_id, stages):
    validate_submission(submission_id)
    previous_record = get_stage_state_record(submission_id)
    merged_stages = merge_with_locked_stages(stages, previous_record.get("stages", []), lock_checked=False)

    record = {
        "submission_id": submission_id,
        "updated_at": utc_now(),
        "submitted_at": previous_record.get("submitted_at"),
        "stages": merged_stages,
    }

    STATES_DIR.mkdir(parents=True, exist_ok=True)
    get_stage_state_path(submission_id).write_text(
        json.dumps(record, indent=2) + "\n",
        encoding="utf-8",
    )
    return record


def submit_stage_state_record(submission_id, stages):
    validate_submission(submission_id)
    previous_record = get_stage_state_record(submission_id)
    now = utc_now()
    merged_stages = merge_with_locked_stages(stages, previous_record.get("stages", []), lock_checked=True)

    record = {
        "submission_id": submission_id,
        "updated_at": now,
        "submitted_at": now,
        "stages": merged_stages,
    }

    STATES_DIR.mkdir(parents=True, exist_ok=True)
    get_stage_state_path(submission_id).write_text(
        json.dumps(record, indent=2) + "\n",
        encoding="utf-8",
    )
    return record


def is_stage_state_submitted(submission_id):
    return bool(get_stage_state_record(submission_id).get("submitted_at"))


def merge_with_locked_stages(stages, previous_stages, lock_checked=False):
    sanitized = sanitize_stages(stages)
    previous_by_key = {
        stage.get("key"): stage
        for stage in previous_stages
        if isinstance(stage, dict) and stage.get("key")
    }

    merged = []
    for stage in sanitized:
        previous = previous_by_key.get(stage["key"], {})
        was_locked = bool(previous.get("locked"))
        is_checked = bool(stage.get("checked"))
        is_locked = was_locked or (lock_checked and is_checked)

        merged.append(
            {
                **stage,
                "checked": True if was_locked else is_checked,
                "locked": is_locked,
            }
        )

    return merged


def sanitize_stages(stages):
    if not isinstance(stages, list):
        return []

    sanitized = []
    seen = set()
    for item in stages:
        item = item or {}
        key = str(item.get("key", "")).strip()
        label = str(item.get("label", "")).strip()
        if not key or key in seen or not is_safe_key(key):
            continue

        seen.add(key)
        sanitized.append(
            {
                "key": key,
                "label": label or key.replace("_", " ").title(),
                "checked": bool(item.get("checked")),
                "locked": bool(item.get("locked")),
            }
        )

    return sanitized


def validate_submission(submission_id):
    if not is_valid_submission_id(submission_id):
        raise ValueError("Invalid submission id.")
    if not submission_exists(submission_id):
        raise FileNotFoundError("Submission not found.")


def get_stage_state_path(submission_id):
    return STATES_DIR / f"{submission_id}.json"


def is_safe_key(value):
    return bool(value) and all(char.isalnum() or char in "._-" for char in value)


def utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
