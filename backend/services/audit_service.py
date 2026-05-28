import json
from datetime import datetime, timezone

from backend.config import ACCESS_AUDIT_PATH, AUDIT_DIR


def record_access_audit(record):
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": utc_now(),
        **{key: value for key, value in record.items() if value is not None},
    }
    with ACCESS_AUDIT_PATH.open("a", encoding="utf-8") as file:
        file.write(json.dumps(entry, sort_keys=True) + "\n")
    return entry


def read_recent_access_audit(limit=100):
    if not ACCESS_AUDIT_PATH.exists():
        return []

    lines = ACCESS_AUDIT_PATH.read_text(encoding="utf-8").splitlines()
    records = []
    for line in lines[-int(limit or 100) :]:
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return list(reversed(records))


def utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
