"""Agent-Yoke platform integration plugin.

Agent Yoke is a routing and orchestration platform exposed through the
``universal`` CLI. This plugin discovers that executable on PATH and exposes
read-only surface: a CLI command and an MCP tool that report availability and
the installed version.

Only availability and version are queried; inventory/plan commands are heavy
and belong to the interactive session, not to a plugin side effect.
"""

import shutil
import subprocess


def _find_universal() -> str | None:
    """Locate the agent-yoke ``universal`` CLI on PATH, or None."""
    return shutil.which("universal")


def _version() -> str | None:
    """The universal CLI's version line, if the command supports it."""
    exe = _find_universal()
    if not exe:
        return None
    try:
        result = subprocess.run(
            [exe, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    text = (result.stdout or result.stderr).strip()
    return text.splitlines()[0] if text else None


def cmd_agent_yoke_status(args):
    """Report whether the agent-yoke universal CLI is available."""
    exe = _find_universal()
    if not exe:
        print("  agent-yoke: universal CLI not found on PATH")
        print("  install: see the agent-yoke project README, or put universal on PATH")
        return
    version = _version()
    print(f"  agent-yoke: universal CLI at {exe}" + (f" ({version})" if version else ""))


def _mcp_handle_agent_yoke_status(arguments: dict) -> dict:
    """MCP tool handler for agent_yoke_status."""
    exe = _find_universal()
    if not exe:
        return {
            "content": [{"type": "text", "text": "agent-yoke universal CLI not found on PATH"}],
            "isError": True,
        }
    version = _version()
    text = f"agent-yoke universal CLI at {exe}"
    if version:
        text += f" ({version})"
    return {"content": [{"type": "text", "text": text}], "isError": False}


def register(registry, manifest):
    """Register agent-yoke's CLI command and MCP tool."""
    registry.add_command("agent-yoke-status", cmd_agent_yoke_status, manifest.id)
    registry.add_mcp_tool(
        "agent_yoke_status",
        {
            "name": "agent_yoke_status",
            "description": "Check whether the agent-yoke universal CLI is installed and report its version",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
        manifest.id,
    )
