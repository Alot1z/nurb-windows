"""Everything (voidtools) integration plugin.

Discovers the ``es`` command-line tool (and the ``Everything`` GUI) on PATH,
never a hard-coded install path, so the plugin works on any machine where
Everything is installed normally.

Provides:
- A CLI command ``nurb everything-search <query>``
- An MCP tool ``everything_search`` for agent-driven filename searches

The Windows Search API and Everything's IPC are out of scope: this plugin
talks to the executable the user already has.
"""

import shutil
import subprocess


def _find_es() -> str | None:
    """Locate es.exe (Everything's command-line tool) on PATH, or None."""
    return shutil.which("es")


def _find_everything() -> str | None:
    """Locate the Everything GUI on PATH, or None."""
    for name in ("Everything", "Everything.exe"):
        found = shutil.which(name)
        if found:
            return found
    return None


def cmd_everything_search(args):
    """Search filenames with Everything's es.exe. Usage: nurb everything-search <query> [--limit N]"""
    argv = list(getattr(args, "argv", []) or [])
    limit = 25
    rest = []
    while argv:
        if argv[0] == "--limit" and len(argv) > 1:
            try:
                limit = int(argv[1])
            except ValueError:
                pass
            argv = argv[2:]
        else:
            rest.append(argv.pop(0))
    es = _find_es()
    if not es:
        print("  everything: es.exe not found on PATH")
        print("  install Everything from https://www.voidtools.com, or put es.exe on PATH")
        return
    query = " ".join(rest)
    try:
        result = subprocess.run(
            [es, query],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except FileNotFoundError:
        print(f"  everything: {es} no longer exists")
        return
    except subprocess.TimeoutExpired:
        print("  everything: search timed out after 15s")
        return
    lines = [ln for ln in result.stdout.splitlines() if ln.strip()]
    if not lines:
        print(f"  everything: no matches for {query!r}")
        return
    shown = limit
    print(f"  everything: {len(lines)} match(es) for {query!r}")
    for ln in lines[:shown]:
        print(f"      {ln}")
    if len(lines) > shown:
        print(f"      ... and {len(lines) - shown} more")


def _mcp_handle_everything_search(arguments: dict) -> dict:
    """MCP tool handler for everything_search."""
    query = arguments.get("query", "")
    es = _find_es()
    if not es:
        return {
            "content": [{"type": "text", "text": "es.exe not found on PATH. Install Everything from voidtools.com."}],
            "isError": True,
        }
    try:
        result = subprocess.run([es, query], capture_output=True, text=True, timeout=15)
    except Exception as exc:
        return {"content": [{"type": "text", "text": f"search failed: {exc}"}], "isError": True}
    lines = [ln for ln in result.stdout.splitlines() if ln.strip()]
    if not lines:
        return {"content": [{"type": "text", "text": f"no matches for {query!r}"}], "isError": False}
    return {
        "content": [{"type": "text", "text": "\n".join(lines[:50])}],
        "isError": False,
    }


def register(registry, manifest):
    """Register Everything's CLI command and MCP tool."""
    registry.add_command("everything-search", cmd_everything_search, manifest.id)
    registry.add_mcp_tool(
        "everything_search",
        {
            "name": "everything_search",
            "description": "Search filenames with voidtools Everything (es.exe) when it is on PATH",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "filename pattern to search for"},
                },
                "required": ["query"],
            },
        },
        manifest.id,
    )
