"""Template plugin: copy this directory to start a new nurb plugin.

A plugin is a directory with a plugin.toml manifest and this module. The
loader validates the manifest, imports plugin.py, and calls register() with
the shared registry and the parsed manifest. Everything the plugin contributes
(CLI commands, MCP tools, build checks) is wired up inside register().

Keep plugin.py dependency-light: it runs in nurb's process, so heavy imports
slow every nurb invocation that loads the plugin.
"""


def cmd_hello(args):
    """A trivial command: `nurb my-plugin-hello`."""
    print("  hello from my-plugin")


def _mcp_handle_my_tool(arguments: dict) -> dict:
    """MCP handler for the my_tool tool declared in plugin.toml."""
    return {
        "content": [{"type": "text", "text": "my_tool ran"}],
        "isError": False,
    }


def register(registry, manifest):
    """Wire this plugin's contributions into nurb."""
    # CLI command: `nurb my-plugin-hello`
    registry.add_command("my-plugin-hello", cmd_hello, manifest.id)

    # MCP tool: the tool_def is the full MCP tool object, so the name and
    # inputSchema shown to agents live here, not in the manifest.
    registry.add_mcp_tool(
        "my_tool",
        {
            "name": "my_tool",
            "description": "What my_tool does",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
        manifest.id,
    )

    # Build check: a function (shape, ctx) -> list[Finding]. Only add this if
    # the manifest declares build_checks = true.
    # def check_thing(shape, ctx):
    #     from nurb.checks import Finding
    #     return []
    # registry.add_build_check(check_thing, manifest.id)
