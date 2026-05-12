from __future__ import annotations

import json
import re
import urllib.error
import urllib.request

from backend.services.submission_service import get_submission_detail


KEYWORD_RULES = [
    (
        {"mfa", "edr", "backup", "backups", "ransomware", "restore", "endpoint"},
        {"cyber_security"},
        {"mfa_documentation", "edr_documentation", "backup_documentation", "ransomware_supplemental_application"},
    ),
    (
        {"loss", "claim", "claims", "incident", "breach", "history", "prior event"},
        {"loss_history"},
        {"loss_runs", "claims_history", "incident_history"},
    ),
    (
        {"revenue", "financial", "sales", "employee", "employees", "record", "records"},
        {"financial", "company_profile"},
        {"financial_information", "revenue_breakdown", "company_information"},
    ),
    (
        {"policy", "prior", "expiring", "coverage", "retention", "limit", "limits", "terms"},
        {"coverage_terms"},
        {"prior_cyber_insurance_policy", "policy_form"},
    ),
    (
        {"vendor", "third party", "dependency", "outsourced", "processor", "cloud", "saas"},
        {"vendor_risk"},
        {"vendor_security_assessment", "third_party_risk_assessment"},
    ),
    (
        {"soc", "soc 2", "hipaa", "pci", "compliance", "attestation", "regulatory"},
        {"compliance"},
        {"compliance_documentation"},
    ),
    (
        {"application", "submission", "form", "overview", "requested"},
        {"submission"},
        {"cyber_application", "submission_form"},
    ),
    (
        {"incident response", "response plan", "ir plan", "tabletop", "escalation"},
        {"cyber_security"},
        {"incident_response_plan"},
    ),
]


def extract_submission_metadata(submission_id: str) -> dict:
    """Return submission metadata without document content."""
    detail = get_submission_detail(submission_id)
    submission = detail["submission"]
    documents = []

    for document in submission.get("documents", []):
        documents.append(
            {
                key: value
                for key, value in document.items()
                if key not in {"content", "url"}
            }
        )

    return {
        "submission_id": detail["id"],
        "title": submission.get("title"),
        "status": submission.get("status"),
        "applicant": submission.get("applicant", {}),
        "coverage": submission.get("coverage", {}),
        "document_taxonomy": submission.get("document_taxonomy", {}),
        "documents": documents,
    }


def select_documents_for_prompt(
    submission_id: str,
    prompt: str,
    max_documents: int = 6,
) -> dict:
    """Select relevant documents using metadata-only keyword/category matching."""
    metadata = extract_submission_metadata(submission_id)
    prompt_text = normalize_text(prompt)
    scored = []

    for document in metadata["documents"]:
        score, reasons = score_document(document, prompt_text)
        if score > 0:
            scored.append((score, document, reasons))

    if not scored:
        scored = select_default_documents(metadata["documents"])

    scored.sort(key=lambda item: (-item[0], item[1]["file_name"]))
    selected = scored[: max(1, min(max_documents, 10))]

    return {
        "submission_id": submission_id,
        "source": "metadata_rules",
        "selected_files": [document["file_name"] for _score, document, _reasons in selected],
        "selections": [
            {
                "file_name": document["file_name"],
                "document_types": document.get("document_types", []),
                "major_categories": document.get("major_categories", []),
                "description": document.get("description", ""),
                "reason": "; ".join(reasons) if reasons else "Default relevant underwriting document.",
                "score": score,
            }
            for score, document, reasons in selected
        ],
    }


def select_documents_with_llm(
    submission_id: str,
    prompt: str,
    api_key: str,
    model: str,
    max_documents: int = 6,
) -> dict:
    """Ask the GPT model to choose documents from metadata only, with a rule fallback."""
    metadata = extract_submission_metadata(submission_id)
    if not api_key:
        return select_documents_for_prompt(submission_id, prompt, max_documents)

    document_options = [
        {
            "file_name": document.get("file_name"),
            "document_types": document.get("document_types", []),
            "major_categories": document.get("major_categories", []),
            "description": document.get("description", ""),
        }
        for document in metadata["documents"]
    ]
    allowed_files = {document["file_name"] for document in document_options}
    selection_prompt = {
        "task": "Select the most relevant cyber underwriting documents for the user prompt. Use metadata only. Return strict JSON.",
        "user_prompt": prompt,
        "max_documents": max_documents,
        "documents": document_options,
        "response_schema": {
            "selected_files": ["file-name.txt"],
            "reasons": [{"file_name": "file-name.txt", "reason": "short reason"}],
        },
    }
    payload = {
        "model": model,
        "instructions": "You select underwriting files for a cyber insurance copilot. Return only valid JSON.",
        "input": [{"role": "user", "content": json.dumps(selection_prompt)}],
        "max_output_tokens": 700,
    }

    try:
        response = post_openai_json(api_key, payload)
        text = extract_output_text(response)
        parsed = parse_json_object(text)
        selected_files = [
            file_name
            for file_name in parsed.get("selected_files", [])
            if file_name in allowed_files
        ][:max_documents]
        reason_by_file = {
            item.get("file_name"): item.get("reason", "")
            for item in parsed.get("reasons", [])
            if isinstance(item, dict)
        }

        if not selected_files:
            return select_documents_for_prompt(submission_id, prompt, max_documents)

        documents_by_name = {document["file_name"]: document for document in metadata["documents"]}
        return {
            "submission_id": submission_id,
            "source": "llm_metadata_selector",
            "selected_files": selected_files,
            "selections": [
                {
                    "file_name": file_name,
                    "document_types": documents_by_name[file_name].get("document_types", []),
                    "major_categories": documents_by_name[file_name].get("major_categories", []),
                    "description": documents_by_name[file_name].get("description", ""),
                    "reason": reason_by_file.get(file_name, "Selected by GPT from document metadata."),
                }
                for file_name in selected_files
            ],
        }
    except Exception:
        return select_documents_for_prompt(submission_id, prompt, max_documents)


def read_documents(submission_id: str, file_names: list[str]) -> dict:
    """Return metadata and extracted text for selected document names."""
    detail = get_submission_detail(submission_id)
    documents_by_name = {
        document["file_name"]: document
        for document in detail["submission"].get("documents", [])
    }
    documents = []

    for file_name in file_names:
        document = documents_by_name.get(file_name)
        if not document:
            continue

        documents.append(
            {
                "file_name": document.get("file_name"),
                "file_type": document.get("file_type"),
                "category": document.get("category"),
                "document_types": document.get("document_types", []),
                "major_categories": document.get("major_categories", []),
                "file_created_at": document.get("file_created_at"),
                "received_at": document.get("received_at"),
                "description": document.get("description"),
                "content": document.get("content", ""),
            }
        )

    return {
        "submission_id": submission_id,
        "documents": documents,
    }


def score_document(document: dict, prompt_text: str) -> tuple[int, list[str]]:
    haystack = normalize_text(
        " ".join(
            [
                document.get("file_name", ""),
                document.get("file_type", ""),
                document.get("category", ""),
                document.get("description", ""),
                " ".join(document.get("document_types", [])),
                " ".join(document.get("major_categories", [])),
            ]
        )
    )
    score = 0
    reasons = []
    document_types = set(document.get("document_types", []))
    major_categories = set(document.get("major_categories", []))

    for keywords, categories, types in KEYWORD_RULES:
        matched_keywords = [keyword for keyword in keywords if keyword in prompt_text]
        if not matched_keywords:
            continue

        category_match = major_categories.intersection(categories)
        type_match = document_types.intersection(types)
        text_match = any(keyword in haystack for keyword in matched_keywords)

        if type_match:
            score += 8
            reasons.append(f"Matched document type: {', '.join(sorted(type_match))}")
        if category_match:
            score += 5
            reasons.append(f"Matched category: {', '.join(sorted(category_match))}")
        if text_match:
            score += 2
            reasons.append(f"Matched prompt terms: {', '.join(matched_keywords[:4])}")

    if document.get("file_name") == "cyber-application.txt":
        score += 1
        reasons.append("Baseline submission context.")

    return score, reasons


def select_default_documents(documents: list[dict]) -> list[tuple[int, dict, list[str]]]:
    default_names = {
        "cyber-application.txt": 4,
        "it-security-controls-questionnaire.txt": 3,
        "mfa-edr-backup-documentation.txt": 3,
        "loss-runs-claims-history.txt": 2,
    }
    return [
        (score, document, ["Default cyber underwriting context."])
        for document in documents
        if (score := default_names.get(document.get("file_name"))) is not None
    ]


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").replace("_", " ").replace("-", " ")).lower()


def post_openai_json(api_key: str, payload: dict) -> dict:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Content-Length": str(len(body)),
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            return json.loads(response.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as error:
        raw = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(raw or f"OpenAI request failed with {error.code}.") from error


def extract_output_text(response: dict) -> str:
    if isinstance(response.get("output_text"), str):
        return response["output_text"]

    chunks = []
    for item in response.get("output", []) if isinstance(response.get("output"), list) else []:
        for part in item.get("content", []) if isinstance(item.get("content"), list) else []:
            if isinstance(part.get("text"), str):
                chunks.append(part["text"])

    return "\n".join(chunks).strip()


def parse_json_object(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))
