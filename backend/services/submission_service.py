import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

from backend.config import (
    CHAT_HISTORY_DIR,
    CLAIMS_DIR,
    DATA_DIR,
    DECISION_WORKFLOW_DIR,
    GUIDE_DIR,
    INTAKE_STATUS_DIR,
    NOTE_DIR,
    SEARCH_METADATA_PATH,
    STATES_DIR,
    TASK_DIR,
    UNDERWRITING_DIR,
)
from backend.services.schema_service import validate_named_schema


SUBMISSION_ID_RE = re.compile(r"^[a-zA-Z0-9._-]+$")
FILE_NAME_RE = re.compile(r"^[a-zA-Z0-9._-]+$")


def is_valid_submission_id(submission_id):
    return bool(SUBMISSION_ID_RE.fullmatch(submission_id or ""))


def is_valid_file_name(file_name):
    return bool(FILE_NAME_RE.fullmatch(file_name or ""))


def submission_exists(submission_id):
    return (DATA_DIR / submission_id / "metadata.json").exists()


def list_submissions():
    if not DATA_DIR.exists():
        return []

    submissions = []
    for folder in sorted(DATA_DIR.iterdir()):
        metadata_path = folder / "metadata.json"
        if not metadata_path.exists():
            continue

        submission = read_json(metadata_path)
        coverage = submission.get("coverage", {})
        applicant = submission.get("applicant", {})
        lines_requested = coverage.get("lines_requested")

        submissions.append(
            {
                "id": folder.name,
                "submission_id": submission.get("id", folder.name),
                "title": submission.get("title", folder.name),
                "insured": applicant.get("insured_name", "Unknown insured"),
                "coverage": ", ".join(lines_requested)
                if isinstance(lines_requested, list)
                else "Coverage TBD",
                "status": submission.get("status", "New"),
                "received_at": submission.get("received_at"),
                "file_created_at": submission.get("file_created_at"),
            }
        )

    return submissions


def get_search_metadata():
    if not SEARCH_METADATA_PATH.exists():
        return {"submissions": []}

    return read_json(SEARCH_METADATA_PATH)


def get_submission_detail(submission_id):
    if not is_valid_submission_id(submission_id):
        raise ValueError("Invalid submission id.")

    folder_path = (DATA_DIR / submission_id).resolve()
    metadata_path = folder_path / "metadata.json"

    if not is_safe_child(folder_path, DATA_DIR.resolve()) or not metadata_path.exists():
        raise FileNotFoundError("Submission not found.")

    submission = read_json(metadata_path)
    documents = []

    for document in submission.get("documents", []):
        file_name = document.get("file_name", "")
        document_path = (folder_path / file_name).resolve()
        content = ""

        if is_safe_child(document_path, folder_path) and document_path.exists():
            suffix = document_path.suffix.lower()
            if suffix in {".txt", ".md", ".csv"}:
                content = document_path.read_text(encoding="utf-8")
            elif suffix == ".pdf":
                content = extract_simple_pdf_text(document_path)

        documents.append(
            {
                **document,
                "url": f"/api/submissions/{submission_id}/files/{file_name}",
                "content": content,
            }
        )

    return {
        "id": submission_id,
        "submission": {
            **submission,
            "documents": documents,
        },
    }


def update_submission_metadata_cells(submission_id, updates):
    if not is_valid_submission_id(submission_id):
        raise ValueError("Invalid submission id.")

    folder_path = (DATA_DIR / submission_id).resolve()
    metadata_path = folder_path / "metadata.json"
    if not is_safe_child(folder_path, DATA_DIR.resolve()) or not metadata_path.exists():
        raise FileNotFoundError("Submission not found.")

    submission = read_json(metadata_path)
    changes = []

    status = clean_text(updates.get("status"))
    if status:
        set_value(submission, ["status"], status, "status", changes)

    applicant_updates = updates.get("applicant") if isinstance(updates.get("applicant"), dict) else {}
    applicant = submission.setdefault("applicant", {})
    text_fields = [
        "insured_name",
        "industry",
        "industry_bucket",
        "industry_group",
        "location",
        "technology_profile",
    ]
    for field in text_fields:
        value = clean_text(applicant_updates.get(field))
        if value:
            set_value(applicant, [field], value, f"applicant.{field}", changes)

    for field in ["annual_revenue", "employee_count", "records_count"]:
        if field in applicant_updates:
            set_value(applicant, [field], make_number(applicant_updates.get(field)), f"applicant.{field}", changes)

    coverage_updates = updates.get("coverage") if isinstance(updates.get("coverage"), dict) else {}
    coverage = submission.setdefault("coverage", {})
    for field in ["requested_effective_date", "retention_requested"]:
        value = clean_text(coverage_updates.get(field))
        if value:
            set_value(coverage, [field], value, f"coverage.{field}", changes)

    if "risk_flags" in updates:
        set_value(submission, ["risk_flags"], normalize_text_list(updates.get("risk_flags")), "risk_flags", changes)

    if "open_questions" in updates:
        set_value(submission, ["open_questions"], normalize_text_list(updates.get("open_questions")), "open_questions", changes)

    if changes:
        now = utc_now()
        submission["updated_at"] = now
        submission.setdefault("timeline", []).append(
            {
                "date": now,
                "event": "Submission cells updated",
                "description": f"Updated {', '.join(changes)}.",
            }
        )
        validate_named_schema("submission_metadata", submission)
        write_json(metadata_path, submission)
        update_search_metadata_entry(submission)

    return get_submission_detail(submission_id)["submission"]


def get_submission_file_path(submission_id, file_name):
    if not is_valid_submission_id(submission_id) or not is_valid_file_name(file_name):
        raise ValueError("Invalid file request")

    folder_path = (DATA_DIR / submission_id).resolve()
    file_path = (folder_path / file_name).resolve()

    if (
        not is_safe_child(folder_path, DATA_DIR.resolve())
        or not is_safe_child(file_path, folder_path)
        or not file_path.exists()
    ):
        raise FileNotFoundError("File not found")

    return file_path


def delete_submission_record(submission_id):
    if not is_valid_submission_id(submission_id):
        raise ValueError("Invalid submission id.")

    folder_path = (DATA_DIR / submission_id).resolve()
    if not is_safe_child(folder_path, DATA_DIR.resolve()) or not folder_path.exists():
        raise FileNotFoundError("Submission not found.")

    removed = []
    remove_tree(folder_path, DATA_DIR.resolve(), removed)
    remove_tree(CHAT_HISTORY_DIR / submission_id, CHAT_HISTORY_DIR.resolve(), removed)

    for directory in [
        CLAIMS_DIR,
        DECISION_WORKFLOW_DIR,
        GUIDE_DIR,
        INTAKE_STATUS_DIR,
        NOTE_DIR,
        STATES_DIR,
        TASK_DIR,
        UNDERWRITING_DIR,
    ]:
        remove_file(directory / f"{submission_id}.json", directory.resolve(), removed)

    search_removed = remove_search_metadata_entry(submission_id)
    return {
        "submission_id": submission_id,
        "removed_paths": removed,
        "search_metadata_removed": search_removed,
    }


def remove_tree(path, safe_parent, removed):
    path = Path(path).resolve()
    if not path.exists():
        return
    if not is_safe_child(path, safe_parent):
        raise ValueError("Refusing to delete unsafe path.")
    shutil.rmtree(path)
    removed.append(str(path))


def remove_file(path, safe_parent, removed):
    path = Path(path).resolve()
    if not path.exists():
        return
    if not is_safe_child(path, safe_parent):
        raise ValueError("Refusing to delete unsafe path.")
    if path.is_file():
        path.unlink()
        removed.append(str(path))


def remove_search_metadata_entry(submission_id):
    if not SEARCH_METADATA_PATH.exists():
        return False

    metadata = read_json(SEARCH_METADATA_PATH)
    submissions = metadata.get("submissions", [])
    remaining = [
        item
        for item in submissions
        if item.get("id") != submission_id
    ]
    removed = len(remaining) != len(submissions)
    if removed:
        metadata["submissions"] = remaining
        metadata["generated_at"] = utc_now()
        write_json(SEARCH_METADATA_PATH, metadata)
    return removed


def update_search_metadata_entry(submission):
    if SEARCH_METADATA_PATH.exists():
        metadata = read_json(SEARCH_METADATA_PATH)
    else:
        metadata = {
            "generated_at": utc_now(),
            "description": "Search index for cyber underwriting submissions.",
            "submissions": [],
        }

    applicant = submission.get("applicant", {})
    found = False
    for item in metadata.get("submissions", []):
        if item.get("id") != submission.get("id"):
            continue
        found = True
        item["title"] = submission.get("title", item.get("title"))
        item["insured_name"] = applicant.get("insured_name", item.get("insured_name"))
        item["industry"] = applicant.get("industry", item.get("industry"))
        item["industry_bucket"] = applicant.get("industry_bucket") or applicant.get("industry_group") or item.get("industry_bucket")
        item["status"] = submission.get("status", item.get("status"))
        item["received_at"] = submission.get("received_at", item.get("received_at"))
        keywords = item.setdefault("keywords", [])
        for keyword in [item.get("title"), item.get("insured_name"), item.get("industry"), item.get("industry_bucket"), item.get("status")]:
            if keyword and keyword not in keywords:
                keywords.append(keyword)
        break

    if not found:
        metadata.setdefault("submissions", []).append(build_search_metadata_entry(submission))

    metadata["generated_at"] = utc_now()
    write_json(SEARCH_METADATA_PATH, metadata)


def build_search_metadata_entry(submission):
    applicant = submission.get("applicant", {})
    broker = submission.get("broker") or {}
    industry_bucket = applicant.get("industry_bucket") or applicant.get("industry_group") or ""
    keywords = unique_values(
        [
            submission.get("title"),
            applicant.get("insured_name"),
            applicant.get("industry"),
            industry_bucket,
            applicant.get("technology_profile"),
            broker.get("firm_name"),
            broker.get("producer_name"),
            submission.get("status"),
        ]
    )
    return {
        "id": submission.get("id"),
        "title": submission.get("title"),
        "insured_name": applicant.get("insured_name"),
        "industry": applicant.get("industry"),
        "industry_bucket": industry_bucket,
        "status": submission.get("status", "New"),
        "received_at": submission.get("received_at"),
        "folder": f"data/submissions/{submission.get('id')}",
        "keywords": keywords,
        "broker_id": broker.get("broker_id"),
        "broker_name": broker.get("firm_name"),
    }


def set_value(target, path, value, label, changes):
    current = target
    for key in path[:-1]:
        current = current.setdefault(key, {})

    final_key = path[-1]
    if current.get(final_key) != value:
        current[final_key] = value
        changes.append(label)


def clean_text(value):
    return str(value or "").strip()


def normalize_text_list(value):
    if isinstance(value, list):
        values = value
    else:
        values = re.split(r"[\n;]+", str(value or ""))
    return [item.strip(" -\t\r\n") for item in values if item and item.strip(" -\t\r\n")]


def make_number(value):
    try:
        return int(float(str(value or "0").replace(",", "").replace("$", "")))
    except (TypeError, ValueError):
        return 0


def unique_values(values):
    result = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in result:
            result.append(text)
    return result


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def is_safe_child(path, parent):
    try:
        Path(path).resolve().relative_to(Path(parent).resolve())
        return True
    except ValueError:
        return False


def extract_simple_pdf_text(file_path):
    pdf = Path(file_path).read_text(encoding="latin1")
    matches = re.findall(r"\((.*?)\)\s*Tj", pdf)
    return "\n".join(unescape_pdf_text(match) for match in matches).strip()


def unescape_pdf_text(text):
    return (
        text.replace(r"\(", "(")
        .replace(r"\)", ")")
        .replace(r"\\", "\\")
    )
