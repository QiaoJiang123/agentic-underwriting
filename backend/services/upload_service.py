import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

from backend.config import DATA_DIR
from backend.services.document_tools import KEYWORD_RULES
from backend.services.openai_service import extract_output_text, post_json
from backend.services.submission_service import (
    extract_simple_pdf_text,
    get_submission_detail,
    is_safe_child,
    is_valid_submission_id,
    read_json,
    submission_exists,
)
from backend.services.schema_service import validate_named_schema


ALLOWED_UPLOAD_SUFFIXES = {".txt", ".pdf"}
ALLOWED_MAJOR_CATEGORIES = {
    "submission",
    "company_profile",
    "cyber_security",
    "loss_history",
    "financial",
    "coverage_terms",
    "vendor_risk",
    "compliance",
    "email_communication",
    "communication",
    "legal_contract",
    "underwriting_workflow",
    "underwriting_review",
    "other",
}

DOCUMENT_METADATA_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "file_type",
        "category",
        "description",
        "document_types",
        "major_categories",
    ],
    "properties": {
        "file_type": {
            "type": "string",
            "description": "Short snake_case document type.",
        },
        "category": {
            "type": "string",
            "description": "One primary major category.",
            "enum": sorted(ALLOWED_MAJOR_CATEGORIES),
        },
        "description": {
            "type": "string",
            "description": "One concise underwriter-facing description.",
        },
        "document_types": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
            "description": "One or more snake_case document type labels.",
        },
        "major_categories": {
            "type": "array",
            "items": {"type": "string", "enum": sorted(ALLOWED_MAJOR_CATEGORIES)},
            "minItems": 1,
            "description": "One or more allowed major categories.",
        },
    },
}


def upload_submission_file(submission_id, original_file_name, file_bytes, api_key="", model=""):
    if not is_valid_submission_id(submission_id) or not submission_exists(submission_id):
        raise FileNotFoundError("Submission not found.")

    if not file_bytes:
        raise ValueError("Uploaded file is empty.")

    folder_path = (DATA_DIR / submission_id).resolve()
    if not is_safe_child(folder_path, DATA_DIR.resolve()):
        raise ValueError("Invalid submission path.")

    file_name = make_safe_upload_name(original_file_name)
    suffix = Path(file_name).suffix.lower()
    if suffix not in ALLOWED_UPLOAD_SUFFIXES:
        raise ValueError("Only .txt and .pdf files can be uploaded.")

    file_name = make_unique_file_name(folder_path, file_name)
    file_path = folder_path / file_name
    file_path.write_bytes(file_bytes)

    extracted_text = extract_uploaded_text(file_path)
    metadata = generate_document_metadata(
        submission_id=submission_id,
        file_name=file_name,
        file_suffix=suffix,
        extracted_text=extracted_text,
        api_key=api_key,
        model=model,
    )
    append_document_metadata(folder_path, metadata)

    return {
        "document": metadata,
        "submission": get_submission_detail(submission_id)["submission"],
    }


def delete_submission_file(submission_id, file_name):
    if not is_valid_submission_id(submission_id) or not submission_exists(submission_id):
        raise FileNotFoundError("Submission not found.")

    safe_file_name = Path(str(file_name or "")).name
    if safe_file_name != file_name or safe_file_name == "metadata.json":
        raise ValueError("Invalid file request.")

    folder_path = (DATA_DIR / submission_id).resolve()
    file_path = (folder_path / safe_file_name).resolve()
    if not is_safe_child(folder_path, DATA_DIR.resolve()) or not is_safe_child(file_path, folder_path):
        raise ValueError("Invalid file request.")

    metadata_path = folder_path / "metadata.json"
    submission = read_json(metadata_path)
    original_documents = submission.get("documents", [])
    submission["documents"] = [
        document
        for document in original_documents
        if document.get("file_name") != safe_file_name
    ]
    submission["updated_at"] = utc_now()

    if file_path.exists() and file_path.is_file():
        file_path.unlink()
    elif len(submission["documents"]) == len(original_documents):
        raise FileNotFoundError("File not found.")

    metadata_path.write_text(json.dumps(submission, indent=2) + "\n", encoding="utf-8")

    return {
        "file_name": safe_file_name,
        "submission": get_submission_detail(submission_id)["submission"],
    }


def make_safe_upload_name(original_file_name):
    source = Path(str(original_file_name or "uploaded-document")).name
    stem = Path(source).stem.lower()
    suffix = Path(source).suffix.lower()
    safe_stem = re.sub(r"[^a-z0-9._-]+", "-", stem).strip(".-_")
    safe_suffix = suffix if suffix in ALLOWED_UPLOAD_SUFFIXES else ""
    return f"{safe_stem or 'uploaded-document'}{safe_suffix}"


def make_unique_file_name(folder_path, file_name):
    candidate = file_name
    stem = Path(file_name).stem
    suffix = Path(file_name).suffix
    counter = 2
    while (folder_path / candidate).exists():
        candidate = f"{stem}-{counter}{suffix}"
        counter += 1
    return candidate


def extract_uploaded_text(file_path):
    suffix = Path(file_path).suffix.lower()
    if suffix == ".txt":
        return Path(file_path).read_text(encoding="utf-8", errors="replace")
    if suffix == ".pdf":
        return extract_simple_pdf_text(file_path)
    return ""


def generate_document_metadata(submission_id, file_name, file_suffix, extracted_text, api_key, model):
    llm_metadata = generate_document_metadata_with_llm(
        submission_id=submission_id,
        file_name=file_name,
        extracted_text=extracted_text,
        api_key=api_key,
        model=model,
    )
    metadata = llm_metadata or infer_document_metadata(file_name, extracted_text)
    now = utc_now()

    return {
        "file_name": file_name,
        "file_type": metadata["file_type"],
        "category": metadata["category"],
        "document_types": metadata["document_types"],
        "major_categories": metadata["major_categories"],
        "file_created_at": now,
        "received_at": now,
        "description": metadata["description"] or f"Uploaded {file_suffix.removeprefix('.').upper()} document",
    }


def generate_document_metadata_with_llm(submission_id, file_name, extracted_text, api_key, model):
    if not api_key or not model:
        return None

    prompt = build_metadata_prompt(submission_id, file_name, extracted_text)
    payload = {
        "model": model,
        "instructions": (
            "You classify uploaded cyber insurance underwriting documents. "
            "Return strict JSON only. Do not include markdown."
        ),
        "input": prompt,
        "text": {
            "format": {
                "type": "json_schema",
                "name": "uploaded_document_metadata",
                "schema": DOCUMENT_METADATA_SCHEMA,
                "strict": True,
            }
        },
        "max_output_tokens": 500,
    }

    try:
        response = post_json("https://api.openai.com/v1/responses", payload, api_key)
        raw_text = extract_output_text(response)
        parsed = json.loads(extract_json_object(raw_text))
        return sanitize_generated_metadata(parsed)
    except Exception:
        return None


def build_metadata_prompt(submission_id, file_name, extracted_text):
    text_sample = (extracted_text or "")[:5000]
    return json.dumps(
        {
            "task": "Create document metadata for an uploaded cyber underwriting file.",
            "submission_id": submission_id,
            "file_name": file_name,
            "allowed_major_categories": sorted(ALLOWED_MAJOR_CATEGORIES),
            "required_json_fields": [
                "file_type",
                "category",
                "description",
                "document_types",
                "major_categories",
            ],
            "format_rules": {
                "file_type": "snake_case short document type",
                "category": "one primary major category",
                "description": "short underwriter-facing description",
                "document_types": "array of one or more snake_case document type labels",
                "major_categories": "array of one or more allowed major categories",
            },
            "document_text_sample": text_sample,
        },
        indent=2,
    )


def extract_json_object(text):
    match = re.search(r"\{.*\}", str(text or ""), re.DOTALL)
    if not match:
        raise ValueError("No JSON object found.")
    return match.group(0)


def sanitize_generated_metadata(metadata):
    file_type = make_snake(metadata.get("file_type") or "uploaded_document")
    category = make_snake(metadata.get("category") or "other")
    description = str(metadata.get("description") or "").strip()[:220]
    document_types = sanitize_string_list(metadata.get("document_types"), [file_type])
    major_categories = sanitize_string_list(metadata.get("major_categories"), [category])
    major_categories = [
        item if item in ALLOWED_MAJOR_CATEGORIES else "other"
        for item in major_categories
    ]
    category = category if category in ALLOWED_MAJOR_CATEGORIES else major_categories[0]

    return {
        "file_type": file_type,
        "category": category,
        "description": description,
        "document_types": document_types,
        "major_categories": unique_list(major_categories),
    }


def infer_document_metadata(file_name, extracted_text):
    text = f"{file_name} {extracted_text or ''}".lower()
    categories = set()
    document_types = set()

    for keywords, rule_categories, rule_document_types in KEYWORD_RULES:
        if any(keyword in text for keyword in keywords):
            categories.update(rule_categories)
            document_types.update(rule_document_types)

    if not categories:
        categories.add("other")
    if not document_types:
        document_types.add(make_snake(Path(file_name).stem) or "uploaded_document")

    primary_type = sorted(document_types)[0]
    primary_category = sorted(categories)[0]
    return {
        "file_type": primary_type,
        "category": primary_category,
        "description": make_description(file_name, sorted(document_types), sorted(categories)),
        "document_types": sorted(document_types),
        "major_categories": sorted(categories),
    }


def make_description(file_name, document_types, categories):
    label = document_types[0].replace("_", " ").title() if document_types else "Uploaded document"
    category = categories[0].replace("_", " ") if categories else "underwriting"
    return f"Uploaded {label} document for {category} review ({file_name})"


def append_document_metadata(folder_path, document_metadata):
    validate_named_schema("document_metadata", document_metadata)
    metadata_path = folder_path / "metadata.json"
    submission = read_json(metadata_path)
    documents = [
        document
        for document in submission.get("documents", [])
        if document.get("file_name") != document_metadata["file_name"]
    ]
    documents.append(document_metadata)
    submission["documents"] = documents
    submission["updated_at"] = utc_now()
    validate_named_schema("submission_metadata", submission)
    metadata_path.write_text(json.dumps(submission, indent=2) + "\n", encoding="utf-8")


def sanitize_string_list(value, fallback):
    if isinstance(value, str):
        items = [value]
    elif isinstance(value, list):
        items = value
    else:
        items = fallback

    sanitized = [make_snake(item) for item in items]
    sanitized = [item for item in sanitized if item]
    return unique_list(sanitized or fallback)


def make_snake(value):
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", str(value or "").lower())).strip("_")


def unique_list(items):
    result = []
    for item in items:
        if item not in result:
            result.append(item)
    return result


def utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
