import json
import time
from datetime import datetime, timezone

from backend.config import TASK_DIR
from backend.services.schema_service import validate_named_schema
from backend.services.submission_service import is_valid_submission_id, submission_exists


VALID_STATUSES = {"open", "done"}


def get_task_record(submission_id):
    validate_submission(submission_id)
    path = get_task_path(submission_id)

    if not path.exists():
        return {
            "submission_id": submission_id,
            "updated_at": None,
            "tasks": [],
        }

    record = json.loads(path.read_text(encoding="utf-8"))
    raw_tasks = record.get("tasks", record.get("follow_ups", []))
    return {
        "submission_id": record.get("submission_id", submission_id),
        "updated_at": record.get("updated_at"),
        "tasks": sanitize_tasks(raw_tasks, [], utc_now(), False),
    }


def save_task_record(submission_id, tasks):
    validate_submission(submission_id)
    previous_record = get_task_record(submission_id)
    now = utc_now()
    record = {
        "submission_id": submission_id,
        "updated_at": now,
        "tasks": sanitize_tasks(tasks, previous_record.get("tasks", []), now),
    }
    validate_named_schema("task_record", record)

    TASK_DIR.mkdir(parents=True, exist_ok=True)
    get_task_path(submission_id).write_text(
        json.dumps(record, indent=2) + "\n",
        encoding="utf-8",
    )
    return record


def validate_submission(submission_id):
    if not is_valid_submission_id(submission_id):
        raise ValueError("Invalid submission id.")
    if not submission_exists(submission_id):
        raise FileNotFoundError("Submission not found.")


def sanitize_tasks(tasks, previous_tasks, now, refresh_updated_at=True):
    if not isinstance(tasks, list):
        return []

    previous_by_id = {
        item.get("id"): item
        for item in previous_tasks
        if isinstance(item, dict) and item.get("id")
    }
    sanitized = []

    for index, item in enumerate(tasks):
        item = item or {}
        title = str(item.get("title", "")).strip()
        due_date = str(item.get("due_date", "")).strip()
        if not title or not is_iso_date(due_date):
            continue

        raw_id = str(item.get("id", "")).strip()
        task_id = raw_id if is_safe_id(raw_id) else f"task-{int(time.time() * 1000)}-{index}"
        previous = previous_by_id.get(task_id, {})
        status = str(item.get("status", "open")).strip().lower()
        if status not in VALID_STATUSES:
            status = "open"

        sanitized.append(
            {
                "id": task_id,
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


def get_task_path(submission_id):
    return TASK_DIR / f"{submission_id}.json"


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
