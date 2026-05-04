import json
import re
import time
from datetime import datetime, timezone

from backend.config import CHAT_HISTORY_DIR
from backend.services.submission_service import is_valid_submission_id


def list_chat_history(submission_id):
    if not is_valid_submission_id(submission_id):
        raise ValueError("Invalid submission id.")

    history_path = CHAT_HISTORY_DIR / submission_id
    if not history_path.exists():
        return []

    history = []
    for path in sorted(history_path.glob("*.json")):
        record = read_json(path)
        messages = record.get("messages", [])
        history.append(
            {
                "id": record.get("id") or path.stem,
                "title": record.get("title") or path.name,
                "created_at": record.get("created_at"),
                "updated_at": record.get("updated_at"),
                "message_count": len(messages) if isinstance(messages, list) else 0,
            }
        )

    return history


def get_chat_history_detail(submission_id, history_id):
    if not is_valid_submission_id(submission_id) or not is_valid_history_id(history_id):
        raise ValueError("Invalid chat history request.")

    history_path = CHAT_HISTORY_DIR / submission_id
    if not history_path.exists():
        raise FileNotFoundError("Chat history not found.")

    match = find_chat_history_file(history_path, history_id)
    if not match:
        raise FileNotFoundError("Chat history not found.")

    return read_json(match)


def save_chat_history(submission_id, body):
    if not is_valid_submission_id(submission_id):
        raise ValueError("Invalid submission id.")

    messages = body.get("messages") if isinstance(body, dict) else []
    if not isinstance(messages, list) or not messages:
        raise ValueError("No chat messages were provided.")

    history_path = CHAT_HISTORY_DIR / submission_id
    history_path.mkdir(parents=True, exist_ok=True)

    now = utc_now()
    existing_id = body.get("history_id") if isinstance(body.get("history_id"), str) else ""
    existing_file = find_chat_history_file(history_path, existing_id) if existing_id else None
    first_user_message = next((message for message in messages if message.get("role") == "user"), None)
    title = body.get("title") or make_chat_title(
        first_user_message.get("content") if first_user_message else "New chat"
    )
    history_id = existing_id or f"{submission_id}-chat-{int(time.time() * 1000)}"
    file_path = existing_file or history_path / f"{slugify(history_id)}.json"
    existing_record = read_json(file_path) if file_path.exists() else {}

    record = {
        "id": existing_record.get("id") or history_id,
        "title": existing_record.get("title") or title,
        "created_at": existing_record.get("created_at") or now,
        "updated_at": now,
        "messages": [
            {
                "role": "assistant" if message.get("role") == "assistant" else "user",
                "content": str(message.get("content", "")),
            }
            for message in messages
        ],
    }

    file_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return record


def find_chat_history_file(history_path, history_id):
    if not history_id:
        return None

    for path in history_path.glob("*.json"):
        record = read_json(path)
        if record.get("id") == history_id or path.stem == history_id:
            return path

    return None


def make_chat_title(content):
    normalized = re.sub(r"\s+", " ", str(content or "New chat")).strip()
    return f"{normalized[:45]}..." if len(normalized) > 48 else normalized or "New chat"


def slugify(value):
    slug = re.sub(r"[^a-z0-9._-]+", "-", str(value).lower()).strip("-")
    return slug[:120] or "chat-history"


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def is_valid_history_id(history_id):
    return bool(re.fullmatch(r"^[a-zA-Z0-9._-]+$", history_id or ""))


def utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

