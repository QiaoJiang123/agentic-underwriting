from contextlib import asynccontextmanager
from typing import Any

from backend.services.agent_tool_registry import list_mcp_tool_names
from backend.services.mcp_client_service import load_mcp_config, run_async
from backend.services.openai_service import build_model_instructions


READ_ONLY_MCP_TOOLS = list_mcp_tool_names(read_only=True)


def run_openai_agents_sdk(
    messages: list[dict[str, str]],
    model: str,
    api_key: str,
    guide_instructions: list[str],
    underwriter_notes: list[str],
) -> dict[str, Any]:
    return run_async(
        _run_openai_agents_sdk(
            messages=messages,
            model=model,
            api_key=api_key,
            guide_instructions=guide_instructions,
            underwriter_notes=underwriter_notes,
        )
    )


async def _run_openai_agents_sdk(
    messages: list[dict[str, str]],
    model: str,
    api_key: str,
    guide_instructions: list[str],
    underwriter_notes: list[str],
) -> dict[str, Any]:
    from agents import Agent, ModelSettings, RunConfig, Runner, set_default_openai_key

    set_default_openai_key(api_key, use_for_tracing=False)
    instructions = build_agent_instructions(guide_instructions, underwriter_notes)

    async with openai_agents_mcp_server() as mcp_server:
        mcp_servers = [mcp_server] if mcp_server else []
        agent = Agent(
            name="Cyber Underwriting Agent",
            instructions=instructions,
            model=model,
            mcp_servers=mcp_servers,
            model_settings=ModelSettings(max_tokens=900),
        )
        result = await Runner.run(
            agent,
            input=messages,
            max_turns=6,
            run_config=RunConfig(
                tracing_disabled=True,
                workflow_name="Agentic Underwriting Chat",
            ),
        )

    return {
        "reply": format_final_output(result.final_output),
        "response_id": result.last_response_id,
        "framework": "openai-agents-sdk",
        "mcp_server": "agentic-underwriting" if mcp_server else None,
        "mcp_tools": READ_ONLY_MCP_TOOLS if mcp_server else [],
    }


def build_agent_instructions(guide_instructions, underwriter_notes):
    instructions = build_model_instructions(guide_instructions, underwriter_notes)
    return "\n".join(
        [
            instructions,
            "",
            "You have native MCP access to the approved local underwriting server for read-side data retrieval.",
            "Use MCP tools when the current prompt needs fresh submission metadata, document selection, document text, tool-contract details, model governance, or a decision package beyond the context already supplied.",
            "Do not use side-effecting tools for notes, guides, task creation, file changes, or stage changes; those actions are handled by the FastAPI permission layer before the model runs.",
            "When you rely on MCP or retrieved context, cite the source names already present in the context when practical.",
        ]
    )


@asynccontextmanager
async def openai_agents_mcp_server():
    server_config = get_agentic_underwriting_mcp_config()
    if not server_config:
        yield None
        return

    from agents.mcp import MCPServerStdio
    from agents.mcp.util import create_static_tool_filter

    async with MCPServerStdio(
        name="agentic-underwriting",
        params=server_config,
        cache_tools_list=True,
        client_session_timeout_seconds=20,
        tool_filter=create_static_tool_filter(allowed_tool_names=READ_ONLY_MCP_TOOLS),
        use_structured_content=True,
    ) as server:
        yield server


def get_agentic_underwriting_mcp_config():
    config = load_mcp_config()
    servers = config.get("mcpServers") or {}
    server = servers.get("agentic-underwriting")
    if not isinstance(server, dict):
        return None

    command = server.get("command")
    if not command:
        return None

    params = {
        "command": command,
        "args": list(server.get("args") or []),
    }
    for key in ("cwd", "env"):
        value = server.get(key)
        if value:
            params[key] = value
    return params


def format_final_output(output):
    if output is None:
        return "I could not produce a response."
    if isinstance(output, str):
        return output.strip() or "I could not produce a response."
    return str(output).strip() or "I could not produce a response."
