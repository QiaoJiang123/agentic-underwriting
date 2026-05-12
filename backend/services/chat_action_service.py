import re
import time
from datetime import datetime, timedelta

from backend.services.guide_service import get_guide_record, save_guide_record
from backend.services.note_service import get_note_record, save_note_record
from backend.services.task_service import get_task_record, save_task_record


MONTHS = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}


def run_chat_action(submission_id, prompt):
    action = parse_chat_action(prompt)
    if not action:
        return None

    action_type = action["type"]
    if action_type == "note":
        record = add_note(submission_id, action["text"])
        return {
            "type": "note",
            "reply": "Added that as an underwriter note.",
            "record": record,
        }

    if action_type == "guide":
        record = add_guide(submission_id, action["text"])
        return {
            "type": "guide",
            "reply": "Added that as a guide instruction.",
            "record": record,
        }

    if action_type == "task":
        due_date = parse_due_date(action["text"])
        if not due_date:
            return {
                "type": "task",
                "reply": "I can add that task, but I need a due date. Try: add task: Request MFA evidence due 2026-05-20.",
                "record": None,
            }

        title = clean_task_title(action["text"], due_date)
        if not title:
            return {
                "type": "task",
                "reply": "I can add that task, but I need a task description before the due date.",
                "record": None,
            }

        record = add_task(submission_id, title, due_date)
        return {
            "type": "task",
            "reply": f"Added task due {due_date}: {title}",
            "record": record,
        }

    return None


def parse_chat_action(prompt):
    text = str(prompt or "").strip()
    normalized = re.sub(r"\s+", " ", text).strip()
    lowered = normalized.lower()

    direct_match = re.match(
        r"^(?:please\s+)?add\s+(note|guide|task)s?\b\s*[:,-]?\s*(.+)$",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if direct_match:
        action_type = direct_match.group(1).lower()
        value = clean_action_value(direct_match.group(2))
        return {"type": action_type, "text": value} if value else None

    intent_match = re.search(
        r"\b(?:add|create|save|record)\s+(?:(?:an?|one\s+more|new|scheduled)\s+)?(note|guide|task)\b",
        lowered,
        re.IGNORECASE,
    )
    if not intent_match:
        return None

    action_type = intent_match.group(1).lower()
    value = extract_action_text(text, action_type, intent_match.end())
    if not value:
        return None

    return {"type": action_type, "text": value}


def extract_action_text(text, action_type, fallback_start):
    quoted = re.findall(r'"([^"]+)"|\'([^\']+)\'', text, re.DOTALL)
    quoted_values = [first or second for first, second in quoted if (first or second).strip()]
    if quoted_values:
        return quoted_values[-1].strip()

    label_patterns = [
        rf"\b{action_type}\s+(?:content|text|instruction|description|title)\s*(?:should\s+be|is|=|:)\s*(.+)$",
        rf"\b(?:content|text|instruction|description|title)\s*(?:should\s+be|is|=|:)\s*(.+)$",
        rf"\b(?:that|as)\s*(.+)$",
    ]
    for pattern in label_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            value = clean_action_value(match.group(1))
            if value:
                return value

    return clean_action_value(text[fallback_start:])


def clean_action_value(value):
    cleaned = str(value or "").strip(" \n\t,.:;-?")
    cleaned = re.sub(r"^(?:for\s+me|please|to\s+the\s+submission)\b\s*[,.:-]?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^(?:to|that|as)\s+", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^(?:the\s+)?(?:note|guide|task)\s*(?:content|text|instruction|description|title)?\s*(?:should\s+be|is|=|:)?\s*", "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip(" \n\t,.:;-?\"'")


def add_note(submission_id, text):
    record = get_note_record(submission_id)
    notes = record.get("notes", [])
    notes.append(make_text_item("note", text))
    return save_note_record(submission_id, notes)


def add_guide(submission_id, text):
    record = get_guide_record(submission_id)
    guides = record.get("guides", [])
    guides.append(make_text_item("guide", text))
    return save_guide_record(submission_id, guides)


def add_task(submission_id, title, due_date):
    record = get_task_record(submission_id)
    tasks = record.get("tasks", [])
    now = utc_now()
    tasks.append(
        {
            "id": f"task-{int(time.time() * 1000)}",
            "title": str(title).strip(),
            "due_date": due_date,
            "status": "open",
            "created_at": now,
            "updated_at": now,
        }
    )
    return save_task_record(submission_id, tasks)


def make_text_item(prefix, text):
    now = utc_now()
    return {
        "id": f"{prefix}-{int(time.time() * 1000)}",
        "text": str(text).strip(),
        "created_at": now,
        "updated_at": now,
    }


def parse_due_date(text):
    value = str(text or "")
    iso_match = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", value)
    if iso_match:
        return iso_match.group(1)

    today = datetime.now().date()
    if re.search(r"\btoday\b", value, re.IGNORECASE):
        return today.isoformat()
    if re.search(r"\btomorrow\b", value, re.IGNORECASE):
        return (today + timedelta(days=1)).isoformat()

    days_match = re.search(r"\bin\s+(\d{1,3})\s+days?\b", value, re.IGNORECASE)
    if days_match:
        return (today + timedelta(days=int(days_match.group(1)))).isoformat()

    month_match = re.search(
        r"\b(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t|tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+(\d{1,2})(?:,)?\s+(20\d{2})\b",
        value,
        re.IGNORECASE,
    )
    if month_match:
        month = MONTHS[month_match.group(1).lower()]
        day = int(month_match.group(2))
        year = int(month_match.group(3))
        return datetime(year, month, day).date().isoformat()

    return None


def clean_task_title(text, due_date):
    title = str(text or "")
    title = re.sub(r"\b(?:due|on|by)\s+20\d{2}-\d{2}-\d{2}\b", "", title, flags=re.IGNORECASE)
    title = re.sub(r"\b(?:due|on|by)\s+today\b", "", title, flags=re.IGNORECASE)
    title = re.sub(r"\b(?:due|on|by)\s+tomorrow\b", "", title, flags=re.IGNORECASE)
    title = re.sub(r"\b(?:due|on|by)?\s*in\s+\d{1,3}\s+days?\b", "", title, flags=re.IGNORECASE)
    title = re.sub(
        r"\b(?:due|on|by)?\s*(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t|tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+\d{1,2}(?:,)?\s+20\d{2}\b",
        "",
        title,
        flags=re.IGNORECASE,
    )
    title = title.replace(due_date, "")
    return re.sub(r"\s+", " ", title).strip(" -:,.")


def utc_now():
    return datetime.utcnow().isoformat() + "Z"
