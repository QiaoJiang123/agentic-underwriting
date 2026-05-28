from fastmcp import FastMCP

from backend.services.document_tools import (
    extract_submission_metadata,
    read_documents,
    select_documents_for_prompt,
)
from backend.services.chat_action_service import add_guide, add_note, add_task


mcp = FastMCP("agentic-underwriting")


@mcp.tool
def extract_metadata(submission_id: str) -> dict:
    """Return submission and document metadata without file contents."""
    return extract_submission_metadata(submission_id)


@mcp.tool
def select_documents(submission_id: str, prompt: str, max_documents: int = 6) -> dict:
    """Select relevant documents for a prompt using underwriting metadata."""
    return select_documents_for_prompt(submission_id, prompt, max_documents)


@mcp.tool
def read_selected_documents(submission_id: str, file_names: list[str]) -> dict:
    """Read extracted text and metadata for selected documents."""
    return read_documents(submission_id, file_names)


@mcp.tool
def add_underwriter_note(submission_id: str, text: str) -> dict:
    """Add an underwriter note for a submission. Notes are ground-truth context."""
    return add_note(submission_id, text)


@mcp.tool
def add_guide_instruction(submission_id: str, text: str) -> dict:
    """Add a guide instruction for a submission. Guides are sent as operating guidance."""
    return add_guide(submission_id, text)


@mcp.tool
def add_scheduled_task(submission_id: str, title: str, due_date: str) -> dict:
    """Add a scheduled underwriting task for a submission. due_date must be YYYY-MM-DD."""
    record, created_task = add_task(submission_id, title, due_date)
    return {"record": record, "created_task": created_task}


if __name__ == "__main__":
    mcp.run()
