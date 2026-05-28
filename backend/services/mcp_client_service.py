import asyncio
import copy
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastmcp import Client


ROOT = Path(__file__).resolve().parents[2]
MCP_SERVERS_PATH = ROOT / "data" / "mcp" / "servers.json"


class MCPToolError(RuntimeError):
    pass


def call_mcp_tool(tool_name, arguments):
    """Call an approved MCP tool through the configured server registry."""
    config = load_mcp_config()
    if not config.get("mcpServers"):
        raise MCPToolError("No enabled MCP servers are configured.")

    return run_async(_call_mcp_tool(tool_name, arguments or {}, config))


def load_mcp_config(path=None):
    config_path = Path(path) if path else MCP_SERVERS_PATH
    if not config_path.exists():
        return {"mcpServers": {}}

    raw_config = json.loads(config_path.read_text(encoding="utf-8"))
    servers = raw_config.get("mcpServers") if isinstance(raw_config, dict) else {}
    enabled_servers = {}

    for name, server in (servers or {}).items():
        if not isinstance(server, dict) or server.get("enabled") is False:
            continue
        if server.get("trusted") is False:
            continue

        normalized = copy.deepcopy(server)
        if normalized.get("cwd") in {None, "", "."}:
            normalized["cwd"] = str(ROOT)
        enabled_servers[name] = normalized

    return {"mcpServers": enabled_servers}


async def _call_mcp_tool(tool_name, arguments, config):
    async with Client(config, timeout=20) as client:
        result = await client.call_tool(tool_name, arguments)
        return parse_mcp_result(result)


def parse_mcp_result(result):
    if isinstance(result, dict):
        return result

    for attribute in ("structured_content", "data"):
        value = getattr(result, attribute, None)
        if isinstance(value, dict):
            return value

    content = getattr(result, "content", None)
    if isinstance(content, list) and content:
        text = getattr(content[0], "text", None)
        if text:
            try:
                return json.loads(text)
            except json.JSONDecodeError as error:
                raise MCPToolError(f"MCP tool returned non-JSON text: {text[:120]}") from error

    raise MCPToolError("MCP tool returned an unsupported result shape.")


def run_async(coro):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    with ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(lambda: asyncio.run(coro)).result()
