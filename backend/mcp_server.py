from fastmcp import FastMCP

from backend.services.document_tools import (
    extract_submission_metadata,
    read_documents,
    select_documents_for_prompt,
)


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


if __name__ == "__main__":
    mcp.run()
