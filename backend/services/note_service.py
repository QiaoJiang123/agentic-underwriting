import json
import time
from datetime import datetime, timezone

from backend.config import NOTE_DIR
from backend.services.schema_service import validate_named_schema
from backend.services.submission_service import is_valid_submission_id, submission_exists


def get_note_record(submission_id):
    validate_submission(submission_id)
    path = get_note_path(submission_id)

    if not path.exists():
        return {
            "submission_id": submission_id,
            "updated_at": None,
            "notes": [],
        }

    record = json.loads(path.read_text(encoding="utf-8"))
    return {
        "submission_id": record.get("submission_id", submission_id),
        "updated_at": record.get("updated_at"),
        "notes": sanitize_notes(record.get("notes", []), [], utc_now(), False),
    }


def save_note_record(submission_id, notes):
    validate_submission(submission_id)
    previous_record = get_note_record(submission_id)
    now = utc_now()
    record = {
        "submission_id": submission_id,
        "updated_at": now,
        "notes": sanitize_notes(notes, previous_record.get("notes", []), now),
    }
    validate_named_schema("note_record", record)

    NOTE_DIR.mkdir(parents=True, exist_ok=True)
    get_note_path(submission_id).write_text(
        json.dumps(record, indent=2) + "\n",
        encoding="utf-8",
    )
    return record


def validate_submission(submission_id):
    if not is_valid_submission_id(submission_id):
        raise ValueError("Invalid submission id.")
    if not submission_exists(submission_id):
        raise FileNotFoundError("Submission not found.")


def sanitize_notes(notes, previous_notes, now, refresh_updated_at=True):
    if not isinstance(notes, list):
        return []

    previous_by_id = {
        note.get("id"): note
        for note in previous_notes
        if isinstance(note, dict) and note.get("id")
    }
    sanitized = []

    for index, note in enumerate(notes):
        note_object = {"text": note} if isinstance(note, str) else note or {}
        text = str(note_object.get("text", "")).strip()
        if not text:
            continue

        raw_id = str(note_object.get("id", "")).strip()
        note_id = raw_id if is_safe_id(raw_id) else f"note-{int(time.time() * 1000)}-{index}"
        previous = previous_by_id.get(note_id, {})

        sanitized.append(
            {
                "id": note_id,
                "text": text,
                "created_at": note_object.get("created_at") or previous.get("created_at") or now,
                "updated_at": now
                if refresh_updated_at
                else note_object.get("updated_at") or previous.get("updated_at") or now,
            }
        )

    return sanitized


def get_note_path(submission_id):
    return NOTE_DIR / f"{submission_id}.json"


def is_safe_id(value):
    return bool(value) and all(char.isalnum() or char in "._-" for char in value)


def utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
