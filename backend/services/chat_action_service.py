import re
import time
from datetime import datetime, timedelta

from backend.services.broker_service import list_brokers
from backend.services.document_completeness_service import get_document_completeness_record
from backend.services.underwriting_service import get_underwriting_system_record
from backend.services.guide_service import get_guide_record, save_guide_record
from backend.services.mcp_client_service import call_mcp_tool
from backend.services.note_service import get_note_record, save_note_record
from backend.services.submission_service import update_submission_metadata_cells
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
        record, transport = add_note_with_agent_tool(submission_id, action["text"])
        return {
            "type": "note",
            "reply": "Added that as an underwriter note.",
            "record": record,
            "transport": transport,
            "mcp_tool": "add_underwriter_note" if transport == "mcp" else None,
            "ui_action": {"panel": "note", "expand": False},
        }

    if action_type == "guide":
        record, transport = add_guide_with_agent_tool(submission_id, action["text"])
        return {
            "type": "guide",
            "reply": "Added that as a guide instruction.",
            "record": record,
            "transport": transport,
            "mcp_tool": "add_guide_instruction" if transport == "mcp" else None,
            "ui_action": {"panel": "guide", "expand": False},
        }

    if action_type == "task":
        due_date = action.get("due_date") or parse_due_date(action["text"])
        if not due_date:
            return {
                "type": "task",
                "reply": "I can add that task, but I need a due date. Try: add task: Request MFA evidence due 2026-05-20.",
                "record": None,
            }

        title = action.get("title") or clean_task_title(action["text"], due_date)
        if not title:
            return {
                "type": "task",
                "reply": "I can add that task, but I need a task description before the due date.",
                "record": None,
            }

        record, created_task, transport = add_task_with_agent_tool(submission_id, title, due_date)
        return {
            "type": "task",
            "reply": f"Added task due {due_date}: {title}",
            "record": record,
            "created_task": created_task,
            "transport": transport,
            "mcp_tool": "add_scheduled_task" if transport == "mcp" else None,
            "ui_action": {"panel": "tasks", "expand": False},
        }

    if action_type == "navigate":
        return {
            "type": "navigate",
            "reply": action["reply"],
            "ui_action": action["ui_action"],
        }

    if action_type == "update_submission_status":
        record = update_submission_metadata_cells(submission_id, {"status": action["status"]})
        return {
            "type": "submission_update",
            "reply": f"Updated submission status to {record.get('status', action['status'])}.",
            "record": record,
            "ui_action": {"panel": "details", "expand": False},
        }

    if action_type == "extract_broker":
        system = get_underwriting_system_record(submission_id)
        return {
            "type": "extract",
            "reply": format_broker_profile(system),
            "ui_action": {"panel": "details", "expand": True},
        }

    if action_type == "extract_broker_table":
        return {
            "type": "broker_table",
            "reply": format_broker_table_query(action.get("prompt", "")),
            "ui_action": {"panel": "details", "expand": True},
        }

    if action_type == "extract_claims":
        system = get_underwriting_system_record(submission_id)
        return {
            "type": "extract",
            "reply": format_claim_summary(system),
            "ui_action": {"panel": "details", "expand": True},
        }

    if action_type == "extract_evidence":
        completeness = get_document_completeness_record(submission_id)
        return {
            "type": "document_completeness",
            "reply": format_document_completeness_summary(completeness),
            "ui_action": {"panel": "details", "expand": True},
        }

    if action_type == "extract_account":
        system = get_underwriting_system_record(submission_id)
        return {
            "type": "extract",
            "reply": format_account_snapshot(system),
            "ui_action": {"panel": "details", "expand": True},
        }

    return None


def parse_chat_action(prompt):
    text = str(prompt or "").strip()
    normalized = re.sub(r"\s+", " ", text).strip()
    lowered = normalized.lower()

    direct_match = re.match(
        r"^(?:please\s+)?add\s+(?:(?:an?|one\s+more|new|scheduled)\s+)?(note|guide|task)s?\b\s*[:,-]?\s*(.+)$",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if direct_match:
        action_type = direct_match.group(1).lower()
        if action_type == "task":
            return build_task_action(text, direct_match.group(2), direct_match.start(2))
        value = clean_action_value(direct_match.group(2))
        return {"type": action_type, "text": value} if value else None

    skill_action = parse_skill_action(normalized, lowered)
    if skill_action:
        return skill_action

    intent_match = re.search(
        r"\b(?:add|create|save|record)\s+(?:(?:an?|one\s+more|new|scheduled)\s+)?(note|guide|task)\b",
        lowered,
        re.IGNORECASE,
    )
    if not intent_match:
        return None

    action_type = intent_match.group(1).lower()
    if action_type == "task":
        return build_task_action(text, text[intent_match.end():], intent_match.end())

    value = extract_action_text(text, action_type, intent_match.end())
    if not value:
        return None

    return {"type": action_type, "text": value}


def build_task_action(full_text, action_text, fallback_start):
    raw_text = clean_action_value(action_text)
    due_date = parse_due_date(raw_text) or parse_due_date(full_text)
    title = extract_task_title(full_text, raw_text, due_date, fallback_start)

    if not raw_text and not title:
        return None

    action = {"type": "task", "text": raw_text or title}
    if due_date:
        action["due_date"] = due_date
    if title:
        action["title"] = title
    return action


def parse_skill_action(text, lowered):
    status_update_match = re.search(
        r"\b(?:set|update|change)\s+(?:the\s+)?(?:submission\s+)?status\s+(?:to|as)\s+(.+)$",
        text,
        re.IGNORECASE,
    )
    if status_update_match:
        status = clean_action_value(status_update_match.group(1))
        if status:
            return {"type": "update_submission_status", "status": status}

    if is_broker_table_prompt(lowered):
        return {"type": "extract_broker_table", "prompt": text}

    if re.search(r"\b(?:show|extract|summarize|who\s+is|what\s+is).*\bbroker\b", lowered):
        return {"type": "extract_broker"}

    if re.search(r"\b(?:show|extract|summarize|review).*\b(claim|claims|loss|losses|loss runs)\b", lowered):
        return {"type": "extract_claims"}

    if is_document_completeness_prompt(lowered):
        return {"type": "extract_evidence"}

    if re.search(r"\b(?:missing evidence|required evidence|what is missing|draft broker follow[- ]?up)\b", lowered):
        return {"type": "extract_evidence"}

    if re.search(r"\b(?:extract|show|summarize).*\b(account|submission|snapshot|overview)\b", lowered):
        return {"type": "extract_account"}

    navigate_match = re.search(r"\b(?:open|go to|show|navigate to)\s+(analytics|quote|bind|what if|what-if|tasks?|notes?|details|underwriting system)\b", lowered)
    if navigate_match:
        destination = navigate_match.group(1)
        panel = "details"
        analytics_tab = None
        expand = True

        if destination in {"analytics", "quote", "bind", "what if", "what-if"}:
            panel = "analytics"
            analytics_tab = "what-if" if "what" in destination else destination if destination in {"quote", "bind"} else None
        elif destination.startswith("task"):
            panel = "tasks"
            expand = False
        elif destination.startswith("note"):
            panel = "note"
            expand = False
        elif destination in {"details", "underwriting system"}:
            panel = "details"

        label = "Analytics" if panel == "analytics" else "Tasks" if panel == "tasks" else "Note" if panel == "note" else "Underwriting System"
        return {
            "type": "navigate",
            "reply": f"Opening {label}.",
            "ui_action": {
                "panel": panel,
                "expand": expand,
                "analytics_tab": analytics_tab,
            },
        }

    return None


def is_broker_table_prompt(lowered):
    if "broker" not in lowered and "producer" not in lowered and "account manager" not in lowered:
        return False

    table_terms = [
        "broker table",
        "broker database",
        "broker db",
        "broker list",
        "all broker",
        "all brokers",
        "compare broker",
        "compare brokers",
        "rank broker",
        "rank brokers",
        "which broker",
        "best broker",
        "worst broker",
        "top broker",
        "highest",
        "lowest",
        "quote ratio",
        "bind ratio",
        "data quality",
        "response",
        "fastest",
        "slowest",
        "market focus",
        "service tier",
        "strategic",
        "wholesale",
        "retail",
        "submissions ytd",
    ]
    return any(term in lowered for term in table_terms)


def is_document_completeness_prompt(lowered):
    document_pattern = r"\b(?:documents?|documnts?|documnt|docs?|files?|evidence|filings?)\b"
    completeness_pattern = r"\b(?:missing|required|requirements?|needed|outstanding|available|submitted|received|provided|checklist|gaps?|complete|completeness)\b"
    return bool(re.search(document_pattern, lowered) and re.search(completeness_pattern, lowered))


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


def add_note_with_agent_tool(submission_id, text):
    try:
        return call_mcp_tool(
            "add_underwriter_note",
            {"submission_id": submission_id, "text": text},
        ), "mcp"
    except Exception:
        return add_note(submission_id, text), "internal_python_fallback"


def add_guide_with_agent_tool(submission_id, text):
    try:
        return call_mcp_tool(
            "add_guide_instruction",
            {"submission_id": submission_id, "text": text},
        ), "mcp"
    except Exception:
        return add_guide(submission_id, text), "internal_python_fallback"


def add_task_with_agent_tool(submission_id, title, due_date):
    try:
        result = call_mcp_tool(
            "add_scheduled_task",
            {"submission_id": submission_id, "title": title, "due_date": due_date},
        )
        return result.get("record", {}), result.get("created_task", {}), "mcp"
    except Exception:
        record, created_task = add_task(submission_id, title, due_date)
        return record, created_task, "internal_python_fallback"


def add_task(submission_id, title, due_date):
    record = get_task_record(submission_id)
    tasks = record.get("tasks", [])
    now = utc_now()
    task = {
        "id": f"task-{int(time.time() * 1000)}",
        "title": str(title).strip(),
        "due_date": due_date,
        "status": "open",
        "created_at": now,
        "updated_at": now,
    }
    tasks.append(task)
    saved_record = save_task_record(submission_id, tasks)
    saved_task = next(
        (item for item in saved_record.get("tasks", []) if item.get("id") == task["id"]),
        task,
    )
    return saved_record, saved_task


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


def extract_task_title(full_text, action_text, due_date, fallback_start):
    candidates = []
    combined_text = str(full_text or "")
    raw_action_text = str(action_text or "")

    quoted = re.findall(r'"([^"]+)"|\'([^\']+)\'', combined_text, re.DOTALL)
    candidates.extend(first or second for first, second in quoted if (first or second).strip())

    label_patterns = [
        r"\b(?:the\s+)?task(?:\s+(?:content|text|description|title|name))?\s*(?:should\s+be|is|=|:|called|named)\s*(.+)$",
        r"\b(?:content|text|description|title|name)\s*(?:should\s+be|is|=|:)\s*(.+)$",
        r"\b(?:task|todo|to\s+do)\s+(?:to|for)\s+(.+?)\s+(?:due|on|by|for)\s+",
    ]
    for source in (combined_text, raw_action_text):
        for pattern in label_patterns:
            match = re.search(pattern, source, re.IGNORECASE | re.DOTALL)
            if match:
                candidates.append(match.group(1))

    if raw_action_text:
        candidates.append(raw_action_text)

    fallback = combined_text[fallback_start:] if isinstance(fallback_start, int) else ""
    if fallback:
        candidates.append(fallback)

    for candidate in candidates:
        title = clean_task_title(candidate, due_date)
        if is_meaningful_task_title(title):
            return title

    return ""


def is_meaningful_task_title(title):
    normalized = re.sub(r"[^a-z0-9 ]+", " ", str(title or "").lower())
    words = [word for word in normalized.split() if word]
    filler = {"for", "on", "by", "due", "task", "the", "a", "an", "to", "please"}
    return bool(words) and any(word not in filler for word in words)


def clean_task_title(text, due_date):
    title = str(text or "")
    title = re.split(r"\s+(?:and|then)\s+(?:add|create|save|record)\s+(?:a\s+|an\s+)?(?:note|guide|task)\b", title, maxsplit=1, flags=re.IGNORECASE)[0]
    title = re.sub(
        r"\b(?:due|on|by|for)\s+20\d{2}-\d{2}-\d{2}\b",
        "",
        title,
        flags=re.IGNORECASE,
    )
    title = re.sub(r"\b(?:due|on|by|for)\s+today\b", "", title, flags=re.IGNORECASE)
    title = re.sub(r"\b(?:due|on|by|for)\s+tomorrow\b", "", title, flags=re.IGNORECASE)
    title = re.sub(r"\b(?:due|on|by|for)?\s*in\s+\d{1,3}\s+days?\b", "", title, flags=re.IGNORECASE)
    title = re.sub(
        r"\b(?:due|on|by|for)?\s*(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t|tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+\d{1,2}(?:,)?\s+20\d{2}\b",
        "",
        title,
        flags=re.IGNORECASE,
    )
    if due_date:
        title = title.replace(due_date, "")
    title = re.sub(
        r"^(?:please\s+)?(?:add|create|save|record)\s+(?:(?:an?|one\s+more|new|scheduled)\s+)?tasks?\b\s*[:,-]?\s*",
        "",
        title,
        flags=re.IGNORECASE,
    )
    title = re.sub(
        r"^(?:the\s+)?task(?:\s+(?:content|text|description|title|name))?\s*(?:should\s+be|is|=|:|called|named)\s*",
        "",
        title,
        flags=re.IGNORECASE,
    )
    title = clean_action_value(title)
    title = re.sub(r"\s+", " ", title).strip(" -:,.")
    return title[:1].upper() + title[1:] if title else ""


def format_broker_profile(system):
    broker = system.get("broker") or {}
    contact = broker.get("submission_contact") or {}
    metrics = broker.get("relationship_metrics") or {}
    contacts = broker.get("contacts") or {}
    producer = contacts.get("producer") or {}
    account_manager = contacts.get("account_manager") or {}

    if not broker:
        return "No broker profile is linked to this submission."

    return "\n".join(
        [
            f"**Broker:** {broker.get('firm_name', 'TBD')} ({broker.get('broker_type', 'TBD')})",
            f"- **Service tier:** {broker.get('service_tier', 'TBD')} | **Region:** {broker.get('primary_region', 'TBD')}",
            f"- **Producer:** {contact.get('producer_name') or producer.get('name', 'TBD')} | {contact.get('producer_email') or producer.get('email', 'TBD')} | {contact.get('producer_phone') or producer.get('phone', 'TBD')}",
            f"- **Account manager:** {contact.get('account_manager_name') or account_manager.get('name', 'TBD')} | {contact.get('account_manager_email') or account_manager.get('email', 'TBD')}",
            f"- **Quote ratio:** {format_percent(metrics.get('quote_ratio_12m'))} | **Bind ratio:** {format_percent(metrics.get('bind_ratio_12m'))} | **Data quality:** {metrics.get('data_quality_score', 'TBD')}/100",
            f"- **Avg response:** {metrics.get('avg_response_hours', 'TBD')} hours | **YTD submissions:** {metrics.get('submissions_ytd', 'TBD')}",
            f"- **Placement notes:** {broker.get('placement_notes', 'TBD')}",
            f"- **Submission note:** {contact.get('broker_notes', 'TBD')}",
        ]
    )


def format_broker_table_query(prompt):
    brokers = list_brokers()
    if not brokers:
        return "**Broker Database**\n- No broker rows are available."

    prompt_text = str(prompt or "").lower()
    metric_key, metric_label, ascending = resolve_broker_metric(prompt_text)
    matched = filter_brokers_for_prompt(brokers, prompt_text)
    ranked = sorted(
        matched,
        key=lambda broker: broker_metric_value(broker, metric_key),
        reverse=not ascending,
    )

    lines = [
        "**Broker Database Query**",
        f"- **Source:** `data/brokers/brokers.json`",
        f"- **Rows matched:** {len(ranked)} of {len(brokers)}",
        f"- **Sorted by:** {metric_label} ({'lower is better' if ascending else 'higher is better'})",
        "",
        f"**Broker Ranking By {metric_label}**",
    ]

    for index, broker in enumerate(ranked, start=1):
        metrics = broker.get("relationship_metrics") or {}
        contacts = broker.get("contacts") or {}
        producer = contacts.get("producer") or {}
        account_manager = contacts.get("account_manager") or {}
        lines.extend(
            [
                f"{index}. **{broker.get('firm_name', 'TBD')}** - {metric_label}: {format_broker_metric(metric_key, metrics.get(metric_key))}",
                f"- Tier: {broker.get('service_tier', 'TBD')} | Type: {broker.get('broker_type', 'TBD')} | Region: {broker.get('primary_region', 'TBD')}",
                f"- Quote ratio: {format_percent(metrics.get('quote_ratio_12m'))} | Bind ratio: {format_percent(metrics.get('bind_ratio_12m'))} | Data quality: {metrics.get('data_quality_score', 'TBD')}/100 | Avg response: {metrics.get('avg_response_hours', 'TBD')}h | YTD submissions: {metrics.get('submissions_ytd', 'TBD')}",
                f"- Producer: {producer.get('name', 'TBD')} | {producer.get('email', 'TBD')}",
                f"- Account manager: {account_manager.get('name', 'TBD')} | {account_manager.get('email', 'TBD')}",
                f"- Market focus: {', '.join(broker.get('market_focus') or []) or 'TBD'}",
                f"- Notes: {broker.get('placement_notes', 'TBD')}",
            ]
        )

    if len(ranked) < len(brokers):
        lines.append("")
        lines.append("Filtered rows came from service tier, broker type, region, or market-focus terms in the prompt.")

    return "\n".join(lines)


def filter_brokers_for_prompt(brokers, prompt_text):
    filtered = []
    for broker in brokers:
        searchable = " ".join(
            [
                broker.get("firm_name", ""),
                broker.get("broker_type", ""),
                broker.get("branch", ""),
                broker.get("primary_region", ""),
                broker.get("service_tier", ""),
                " ".join(broker.get("market_focus") or []),
                " ".join(broker.get("communication_preferences") or []),
            ]
        ).lower()
        if any(term in searchable for term in broker_filter_terms(prompt_text)):
            filtered.append(broker)

    return filtered or brokers


def broker_filter_terms(prompt_text):
    terms = []
    for candidate in [
        "strategic",
        "core",
        "development",
        "retail",
        "wholesale",
        "northeast",
        "midwest",
        "national",
        "west",
        "food",
        "hospitality",
        "cyber",
        "technology",
        "construction",
        "manufacturing",
        "healthcare",
        "education",
        "public entity",
        "marina",
        "recreation",
        "saas",
        "fintech",
        "api",
        "privacy",
        "pharmacy",
    ]:
        if candidate in prompt_text:
            terms.append(candidate)
    return terms


def resolve_broker_metric(prompt_text):
    if "bind" in prompt_text or "bound" in prompt_text:
        return "bind_ratio_12m", "Bind ratio", False
    if "quote" in prompt_text or "quoted" in prompt_text:
        return "quote_ratio_12m", "Quote ratio", False
    if "response" in prompt_text or "fastest" in prompt_text or "slowest" in prompt_text or "turnaround" in prompt_text:
        return "avg_response_hours", "Average response hours", True
    if "submission" in prompt_text or "volume" in prompt_text or "pipeline" in prompt_text:
        return "submissions_ytd", "YTD submissions", False
    if "year" in prompt_text or "tenure" in prompt_text or "relationship age" in prompt_text:
        return "years_active", "Years active", False
    return "data_quality_score", "Data quality score", False


def broker_metric_value(broker, metric_key):
    metrics = broker.get("relationship_metrics") or {}
    try:
        return float(metrics.get(metric_key) or 0)
    except (TypeError, ValueError):
        return 0


def format_broker_metric(metric_key, value):
    if metric_key in {"quote_ratio_12m", "bind_ratio_12m"}:
        return format_percent(value)
    if metric_key == "avg_response_hours":
        return f"{format_int(value)}h"
    if metric_key == "data_quality_score":
        return f"{format_int(value)}/100"
    return format_int(value)


def format_claim_summary(system):
    snapshot = system.get("claim_snapshot") or {}
    claims = system.get("claims") or []
    lines = [
        "**Historical Claim Information**",
        f"- **Total claims:** {snapshot.get('total_claims', 0)} | **Open:** {snapshot.get('open_claims', 0)} | **Incurred:** {format_currency(snapshot.get('total_incurred', 0))}",
        f"- **Latest loss date:** {snapshot.get('latest_loss_date') or 'TBD'}",
    ]
    for claim in claims[:5]:
        lines.append(
            f"- **{claim.get('claim_id', 'Claim')}:** {claim.get('loss_date', 'TBD')} | "
            f"{format_label(claim.get('claim_type'))} | {format_label(claim.get('status'))} | "
            f"{format_currency(claim.get('amount_paid', 0))} paid, {format_currency(claim.get('amount_reserved', 0))} reserved"
        )
    return "\n".join(lines)


def format_document_completeness_summary(record):
    missing = record.get("missing_required_documents") or []
    received = record.get("received_required_documents") or []
    submitted = record.get("submitted_documents") or []
    lines = [
        "**Document Completeness Review**",
        f"- **Required source:** {record.get('requirement_source', 'Stored cyber requirement map')}",
        f"- **Required categories received:** {record.get('received_count', len(received))}/{record.get('required_count', len(received) + len(missing))}",
        f"- **Submitted files reviewed:** {record.get('submitted_count', len(submitted))}",
    ]
    if missing:
        lines.append("")
        lines.append("**Missing required documents**")
        lines.extend(f"- {item.get('label', 'Evidence')}" for item in missing)
        lines.append("")
        lines.append("**Broker follow-up**")
        lines.append("Please provide " + ", ".join(item.get("label", "evidence") for item in missing[:6]) + ".")
    else:
        lines.append("- **Missing required documents:** None based on the current required document map.")

    if received:
        lines.append("")
        lines.append("**Received required documents**")
        for item in received:
            files = ", ".join(item.get("source_files") or [])
            lines.append(f"- {item.get('label', 'Evidence')}: {files or 'matched in metadata'}")

    if submitted:
        lines.append("")
        lines.append("**Submitted file metadata reviewed**")
        for document in submitted[:12]:
            lines.append(f"- `{document.get('file_name', 'document')}`: {document.get('description') or document.get('file_type') or 'document'}")

    return "\n".join(lines)


def format_account_snapshot(system):
    submission_id = system.get("submission_id", "")
    broker = system.get("broker") or {}
    appetite = system.get("appetite") or {}
    claim_snapshot = system.get("claim_snapshot") or {}
    evidence = system.get("evidence_status") or []
    available = len([item for item in evidence if item.get("status") == "available"])
    actions = system.get("recommended_actions") or []

    return "\n".join(
        [
            f"**Account Snapshot:** {submission_id}",
            f"- **Appetite:** {appetite.get('status', 'TBD')} - {appetite.get('rationale', 'TBD')}",
            f"- **Broker:** {broker.get('firm_name', 'TBD')} | {broker.get('service_tier', 'TBD')}",
            f"- **Claims:** {claim_snapshot.get('total_claims', 0)} total, {claim_snapshot.get('open_claims', 0)} open, {format_currency(claim_snapshot.get('total_incurred', 0))} incurred",
            f"- **Evidence:** {available}/{len(evidence)} required categories available",
            f"- **Next action:** {actions[0] if actions else 'Prepare terms after document review.'}",
        ]
    )


def format_currency(value):
    try:
        return f"${float(value or 0):,.0f}"
    except (TypeError, ValueError):
        return "$0"


def format_percent(value):
    try:
        return f"{float(value or 0) * 100:.0f}%"
    except (TypeError, ValueError):
        return "TBD"


def format_int(value):
    try:
        return f"{int(float(value or 0)):,}"
    except (TypeError, ValueError):
        return "0"


def format_label(value):
    words = str(value or "TBD").replace("_", " ").replace("-", " ").split()
    return " ".join(word[:1].upper() + word[1:] for word in words)


def utc_now():
    return datetime.utcnow().isoformat() + "Z"
