import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from backend.config import AGENT_TRACE_DIR
from backend.services.schema_service import validate_named_schema
from backend.services.submission_service import is_safe_child, is_valid_submission_id


def new_trace_id():
    return f"trace-{int(time.time() * 1000)}-{uuid.uuid4().hex[:8]}"


def save_agent_trace(record):
    submission_id = str(record.get("submission_id") or "").strip()
    trace_id = str(record.get("trace_id") or "").strip()
    if not is_valid_submission_id(submission_id):
        raise ValueError("Invalid submission id.")
    if not trace_id:
        raise ValueError("Trace id is required.")

    now = utc_now()
    record["updated_at"] = now
    record.setdefault("created_at", now)
    validate_named_schema("agent_trace_record", record)

    folder = (AGENT_TRACE_DIR / submission_id).resolve()
    safe_parent = AGENT_TRACE_DIR.resolve()
    folder.mkdir(parents=True, exist_ok=True)
    if not is_safe_child(folder, safe_parent):
        raise ValueError("Invalid trace path.")

    trace_path = (folder / f"{trace_id}.json").resolve()
    if not is_safe_child(trace_path, folder):
        raise ValueError("Invalid trace path.")

    trace_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return record


def list_agent_traces(submission_id):
    if not is_valid_submission_id(submission_id):
        raise ValueError("Invalid submission id.")

    folder = AGENT_TRACE_DIR / submission_id
    if not folder.exists():
        return []

    traces = []
    for path in sorted(folder.glob("*.json"), reverse=True):
        record = read_json(path)
        traces.append(
            {
                "trace_id": record.get("trace_id"),
                "submission_id": record.get("submission_id"),
                "created_at": record.get("created_at"),
                "updated_at": record.get("updated_at"),
                "status": record.get("status"),
                "agent": record.get("agent"),
                "prompt_preview": record.get("prompt_preview"),
                "attempt_count": record.get("attempt_count", 0),
                "confidence": record.get("confidence", {}),
            }
        )
    return traces


def list_all_agent_traces(limit=75):
    if not AGENT_TRACE_DIR.exists():
        return []

    traces = []
    for path in AGENT_TRACE_DIR.glob("*/*.json"):
        try:
            record = read_json(path)
        except (OSError, json.JSONDecodeError):
            continue

        traces.append(
            {
                "trace_id": record.get("trace_id"),
                "submission_id": record.get("submission_id"),
                "created_at": record.get("created_at"),
                "updated_at": record.get("updated_at"),
                "status": record.get("status"),
                "agent": record.get("agent"),
                "prompt_preview": record.get("prompt_preview"),
                "attempt_count": record.get("attempt_count", 0),
                "confidence": record.get("confidence", {}),
                "selected_skills": record.get("selected_skills", []),
                "source_count": record.get("source_count", 0),
                "step_count": len(record.get("steps", [])),
            }
        )

    traces.sort(key=lambda item: item.get("updated_at") or item.get("created_at") or "", reverse=True)
    return traces[: int(limit or 75)]


def get_agent_trace(submission_id, trace_id):
    if not is_valid_submission_id(submission_id):
        raise ValueError("Invalid submission id.")

    safe_trace_id = Path(str(trace_id or "")).stem
    folder = (AGENT_TRACE_DIR / submission_id).resolve()
    trace_path = (folder / f"{safe_trace_id}.json").resolve()
    if (
        not is_safe_child(folder, AGENT_TRACE_DIR.resolve())
        or not is_safe_child(trace_path, folder)
        or not trace_path.exists()
    ):
        raise FileNotFoundError("Agent trace not found.")
    return read_json(trace_path)


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
