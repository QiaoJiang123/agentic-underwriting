import shutil
from datetime import datetime, timedelta, timezone

from backend.config import INTAKE_UPLOAD_DIR


def cleanup_intake_uploads(max_age_hours=24, dry_run=True, now=None):
    max_age_hours = max(0, int(max_age_hours or 0))
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=max_age_hours)
    INTAKE_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    candidates = []

    for path in sorted(INTAKE_UPLOAD_DIR.iterdir()):
        if path.name.startswith("."):
            continue
        modified_at = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
        if modified_at > cutoff:
            continue
        size = path_size(path)
        candidates.append(
            {
                "path": str(path.relative_to(INTAKE_UPLOAD_DIR.parent)),
                "name": path.name,
                "modified_at": modified_at.isoformat().replace("+00:00", "Z"),
                "bytes": size,
                "is_dir": path.is_dir(),
            }
        )
        if not dry_run:
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()

    return {
        "dry_run": bool(dry_run),
        "max_age_hours": max_age_hours,
        "cutoff": cutoff.isoformat().replace("+00:00", "Z"),
        "candidate_count": len(candidates),
        "deleted_count": 0 if dry_run else len(candidates),
        "candidate_bytes": sum(item["bytes"] for item in candidates),
        "candidates": candidates,
    }


def path_size(path):
    if path.is_file():
        return path.stat().st_size
    total = 0
    for child in path.rglob("*"):
        if child.is_file():
            total += child.stat().st_size
    return total
