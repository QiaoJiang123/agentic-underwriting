import json
import time
from datetime import datetime, timezone

from backend.config import FOLLOW_UP_DIR
from backend.services.submission_service import is_valid_submission_id, submission_exists


VALID_STATUSES = {"open", "done"}


def get_follow_up_record(submission_id):
    validate_submission(submission_id)
    path = get_follow_up_path(submission_id)

    if not path.exists():
        return {
            "submission_id": submission_id,
            "updated_at": None,
            "follow_ups": [],
        }

    record = json.loads(path.read_text(encoding="utf-8"))
    return {
        "submission_id": record.get("submission_id", submission_id),
        "updated_at": record.get("updated_at"),
        "follow_ups": sanitize_follow_ups(record.get("follow_ups", []), [], utc_now(), False),
    }


def save_follow_up_record(submission_id, follow_ups):
    validate_submission(submission_id)
    previous_record = get_follow_up_record(submission_id)
    now = utc_now()
    record = {
        "submission_id": submission_id,
        "updated_at": now,
        "follow_ups": sanitize_follow_ups(follow_ups, previous_record.get("follow_ups", []), now),
    }

    FOLLOW_UP_DIR.mkdir(parents=True, exist_ok=True)
    get_follow_up_path(submission_id).write_text(
        json.dumps(record, indent=2) + "\n",
        encoding="utf-8",
    )
    return record


def validate_submission(submission_id):
    if not is_valid_submission_id(submission_id):
        raise ValueError("Invalid submission id.")
    if not submission_exists(submission_id):
        raise FileNotFoundError("Submission not found.")


def sanitize_follow_ups(follow_ups, previous_follow_ups, now, refresh_updated_at=True):
    if not isinstance(follow_ups, list):
        return []

    previous_by_id = {
        item.get("id"): item
        for item in previous_follow_ups
        if isinstance(item, dict) and item.get("id")
    }
    sanitized = []

    for index, item in enumerate(follow_ups):
        item = item or {}
        title = str(item.get("title", "")).strip()
        due_date = str(item.get("due_date", "")).strip()
        if not title or not is_iso_date(due_date):
            continue

        raw_id = str(item.get("id", "")).strip()
        follow_up_id = raw_id if is_safe_id(raw_id) else f"follow-up-{int(time.time() * 1000)}-{index}"
        previous = previous_by_id.get(follow_up_id, {})
        status = str(item.get("status", "open")).strip().lower()
        if status not in VALID_STATUSES:
            status = "open"

        sanitized.append(
            {
                "id": follow_up_id,
                "title": title,
                "due_date": due_date,
                "status": status,
                "created_at": item.get("created_at") or previous.get("created_at") or now,
                "updated_at": now
                if refresh_updated_at
                else item.get("updated_at") or previous.get("updated_at") or now,
            }
        )

    return sorted(sanitized, key=lambda item: (item["status"] == "done", item["due_date"], item["title"].lower()))


def get_follow_up_path(submission_id):
    return FOLLOW_UP_DIR / f"{submission_id}.json"


def is_iso_date(value):
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def is_safe_id(value):
    return bool(value) and all(char.isalnum() or char in "._-" for char in value)


def utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
