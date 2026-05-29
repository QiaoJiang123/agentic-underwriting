from fastmcp import FastMCP

from backend.services.document_tools import (
    extract_submission_metadata,
    read_documents,
    select_documents_for_prompt,
)
from backend.services.chat_action_service import add_guide, add_note, add_task
from backend.services.agent_tool_registry import get_agent_tool, get_agent_tool_registry_record
from backend.services.decision_package_service import get_decision_package as build_decision_package
from backend.services.model_governance_service import get_model_governance as read_model_governance


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
def list_agent_tool_contracts(compact: bool = True) -> dict:
    """Return the central agent tool registry with permissions, schemas, and MCP exposure."""
    record = get_agent_tool_registry_record()
    if not compact:
        return record
    return {
        **record,
        "tools": [
            {
                key: tool.get(key)
                for key in [
                    "skill",
                    "label",
                    "description",
                    "required_permission",
                    "access_scope",
                    "tool_type",
                    "mcp_exposed",
                    "mcp_tool_name",
                    "write_requires_confirmation",
                ]
            }
            for tool in record.get("tools", [])
        ],
    }


@mcp.tool
def get_agent_tool_contract(skill: str, compact: bool = False) -> dict:
    """Return one central agent tool contract by skill name."""
    contract = get_agent_tool(skill, compact=compact)
    if not contract:
        return {"error": f"Unknown tool skill: {skill}", "skill": skill}
    return {"tool": contract}


@mcp.tool
def get_decision_package(submission_id: str, package_type: str = "review") -> dict:
    """Return a structured underwriting decision package for review, quote, referral, or bind."""
    return build_decision_package(submission_id, package_type)


@mcp.tool
def get_model_governance(model_name: str = "") -> dict:
    """Return model governance registry or a single model governance record."""
    return read_model_governance(model_name or None)


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
