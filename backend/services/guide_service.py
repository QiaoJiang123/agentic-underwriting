import json
import time
from datetime import datetime, timezone

from backend.config import GUIDE_DIR
from backend.services.submission_service import is_valid_submission_id, submission_exists


def get_guide_record(submission_id):
    validate_submission(submission_id)
    path = get_guide_path(submission_id)

    if not path.exists():
        return {
            "submission_id": submission_id,
            "updated_at": None,
            "guides": [],
        }

    record = json.loads(path.read_text(encoding="utf-8"))
    return {
        "submission_id": record.get("submission_id", submission_id),
        "updated_at": record.get("updated_at"),
        "guides": sanitize_guides(record.get("guides", []), [], utc_now(), False),
    }


def save_guide_record(submission_id, guides):
    validate_submission(submission_id)
    previous_record = get_guide_record(submission_id)
    now = utc_now()
    record = {
        "submission_id": submission_id,
        "updated_at": now,
        "guides": sanitize_guides(guides, previous_record.get("guides", []), now),
    }

    GUIDE_DIR.mkdir(parents=True, exist_ok=True)
    get_guide_path(submission_id).write_text(
        json.dumps(record, indent=2) + "\n",
        encoding="utf-8",
    )
    return record


def validate_submission(submission_id):
    if not is_valid_submission_id(submission_id):
        raise ValueError("Invalid submission id.")
    if not submission_exists(submission_id):
        raise FileNotFoundError("Submission not found.")


def sanitize_guides(guides, previous_guides, now, refresh_updated_at=True):
    if not isinstance(guides, list):
        return []

    previous_by_id = {
        guide.get("id"): guide
        for guide in previous_guides
        if isinstance(guide, dict) and guide.get("id")
    }
    sanitized = []

    for index, guide in enumerate(guides):
        guide_object = {"text": guide} if isinstance(guide, str) else guide or {}
        text = str(guide_object.get("text", "")).strip()
        if not text:
            continue

        raw_id = str(guide_object.get("id", "")).strip()
        guide_id = raw_id if is_safe_id(raw_id) else f"guide-{int(time.time() * 1000)}-{index}"
        previous = previous_by_id.get(guide_id, {})

        sanitized.append(
            {
                "id": guide_id,
                "text": text,
                "created_at": guide_object.get("created_at") or previous.get("created_at") or now,
                "updated_at": now
                if refresh_updated_at
                else guide_object.get("updated_at") or previous.get("updated_at") or now,
            }
        )

    return sanitized


def get_guide_path(submission_id):
    return GUIDE_DIR / f"{submission_id}.json"


def is_safe_id(value):
    return bool(value) and all(char.isalnum() or char in "._-" for char in value)


def utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

