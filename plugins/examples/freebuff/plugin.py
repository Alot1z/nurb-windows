""" public extension contract.

This plugin demonstrates the public integration surface for  in nurb.
It does not contain or reference any private  implementation details.

The extension provides:
- A CLI command ``nurb -status`` to check availability
- An MCP tool ``_status`` for agent-driven availability checks

The actual  session runs externally; nurb only hosts the terminal
or exposes the MCP bridge. This plugin never parses or injects into the session.
"""

import shutil
from pathlib import Path


def _find_() -> str | None:
    """Locate the  executable on PATH, or None."""
    return shutil.which("")


def cmd__status(args):
    """Report whether the  CLI is available."""
    path = _find_()
    if path:
        print(f"  : found at {path}")
    else:
        print("  : not found on PATH")
        print("  install: npm install -g ")


def _mcp_handle__status(arguments: dict) -> dict:
    """MCP tool handler for _status."""
    path = _find_()
    if path:
        text = f" is installed at {path}"
    else:
        text = " is not installed on PATH. Install with: npm install -g "
    return {"content": [{"type": "text", "text": text}], "isError": False}


def register(registry, manifest):
    """Register 's CLI command and MCP tool with the nurb plugin system."""
    registry.add_command("-status", cmd__status, manifest.id)

    registry.add_mcp_tool(
        "_status",
        {
            "name": "_status",
            "description": "Check if  CLI is installed and available on PATH",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
        manifest.id,
    )
