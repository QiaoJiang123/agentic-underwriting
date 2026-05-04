import json
import re
from pathlib import Path

from backend.config import DATA_DIR, SEARCH_METADATA_PATH


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

