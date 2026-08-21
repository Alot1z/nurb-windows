# Nurb-Windows extensions

Optional capabilities that ship as data, not as core code. An extension is a
manifest plus a host kind; the core knows how to run each host kind and
nothing else about the extension.

## Host kinds

| Kind | What the core does | Who drives it |
| --- | --- | --- |
| `terminal` | Spawns the extension's own executable in a ConPTY session (pty elsewhere) and moves bytes between the user and the child | The human, in the official CLI's own TUI |
| `externalApp` | Launches the extension's own application detached and does not touch it | The human, in the official app |
| `acp` (existing) | Hosts an agent over the Agent Client Protocol (Claude, Codex, Cursor, Grok) | The app, with human permission prompts |

The terminal and externalApp kinds are the new ones. Their contract is
deliberately thin: no prompt injection, no output parsing, no session
chaining, no auto-restart. The app is a host, not a client of the extension's
service.

## Manifests

`desktop/src-tauri/src/extensions.rs` ships a builtin table. Each manifest
carries: id, label, version, minimum app version (enforced at launch),
developer-only flag, host kind, declarative lookup locations, a launch argv
template (`{project}` is the only substitution, passed as a single argument),
an install hint, and an honest one-sentence note.

Lookups are declarative so future extensions are data: on PATH, under the
user home, or under `%LOCALAPPDATA%`. The app never bundles an extension's
binary; it finds what the user's own installer put on the machine, exactly
like the Cursor and Grok agent discovery.

## Enable/disable

Extensions are disabled by default. State lives in
`extensions.json` in the app data dir, separate from the manifests. Unknown
ids are rejected, so a typo can never enable something the app cannot run. A
disabled or uninstalled extension refuses to launch.

## The terminal host

`desktop/src-tauri/src/terminal.rs` uses `portable-pty` (ConPTY on Windows,
pty elsewhere). Each open panel is one session: a reader thread pumps the
child's output to the UI as base64 (terminal bytes are not UTF-8), and the
only writer path is the user's keystrokes. Resize and Ctrl+C follow the
terminal-emulator pattern; closing the panel kills the child tree. There is
no code path that can inject text into the session, which is what keeps the
host a terminal and not a custom client.

The frontend surface is `desktop/src/TerminalPanel.tsx`, an xterm.js panel
(vendored through the normal npm build, no CDN) fed byte-for-byte.

## The MCP server

`src/nurb/mcp.py` is a stdio MCP server (newline-delimited JSON-RPC, the
framing the official `@modelcontextprotocol/sdk` clients use). Every tool is
literally the nurb CLI command of the same name: the server builds the same
argparse Namespace and calls the same `cmd_*` function, capturing its output,
so the tools cannot drift from the CLI and expose nothing the CLI does not
have.

Tools: `nurb_build`, `nurb_check`, `nurb_inspect`, `nurb_verify`,
`nurb_export`, `nurb_rules`, `nurb_api`. Resources: `nurb://parts`,
`nurb://card/<part>`, `nurb://doctrine`.

An MCP-capable agent can call these through its own supported mechanism once
the user adds the server to the agent's `mcp.json`:

```json
{
  "mcpServers": {
    "nurb": { "command": "nurb", "args": ["mcp", "--project", "C:\\path\\to\\project"] }
  }
}
```

The `--project` flag is optional; without it the server serves the nearest
project from cwd, like every other nurb command. Setup requires explicit user
consent: the app never edits an agent's configuration.

## Security model

- Only the extension registry decides what runs: ids must name a known
  manifest, executables come from the user's own install locations, and PATH
  resolution checks the npm bin and documented install dirs.
- The launch template has exactly one substitution (`{project}`), passed via
  `Command::arg`, never a shell string.
- The MCP server is local stdio, serves only the given project, makes no
  network calls, and reads no credentials.
- Spawned processes run with the user's normal token, never elevated, and
  are killed with their tree when their panel closes.

## Known limitations

- Extensions with no documented open-project mechanism launch without
  targeting a project.
- Extensions requiring human-directed use must not gain automation through
  the terminal host.
- Extension manifests are builtin, not yet loadable from disk; a directory
  scanner is the next step if third-party extensions arrive.

## Public-release status

All extensions are developer-only and opt-in by default. Nothing in the
extension system itself is blocked; individual extensions may have additional
release requirements.

##  integration

 is a terminal-hosted extension registered in the builtin table. The
app discovers the `` CLI on PATH, launches it in a ConPTY terminal
panel, and passes `--cwd {project}` so  opens the user's project.
The human drives the session; nurb hosts the terminal but never parses or
injects into it.

### MCP server configuration

 is also an MCP client (Claude Code format). It can call nurb's
built-in MCP server to run `nurb build`, `nurb check`, `nurb inspect`,
and15 other tools directly. Add this to your  `mcp.json` (usually
at `~/.config/manicode//mcp.json` or wherever your  config
lives):



If nurb is installed globally (not via uv), use:



Replace `/path/to/your/nurb/project` with the actual path to your nurb
project (the directory containing `parts/`).

### What  can do through MCP

Once configured,  can call these nurb tools:

- `nurb_build` - build a part and report dimensions
- `nurb_check` - run printability checks
- `nurb_inspect` - measure faces, normals, concave edges
- `nurb_export` - export to 3MF/STL/STEP/GLB
- `nurb_new` - create a new part file
- `nurb_card` - regenerate a part card
- `nurb_diff` - compare part to card
- `nurb_stress` - static stress analysis
- `nurb_scan` - measure a mesh file
- `nurb_compare` - compare part to target mesh
- `nurb_rules` - print the design doctrine
- `nurb_api` - print the vocabulary
- `nurb_extract` - find duplication across parts
- `nurb_slice` - estimate print time and filament
- `nurb_render` - write a PNG of a part
- `nurb_skill` - print the agent skill file
- `nurb_update` - upgrade nurb

### Human-in-the-loop contract

The MCP path and the terminal path serve different purposes:

- **Terminal path** (extension panel): 's own TUI, its own auth, its
  own model. The human types, nurb hosts. This is the primary integration.
- **MCP path** (mcp.json):  calls nurb tools as if they were its
  own. This is useful for automation within a  session, but the human
  must start and stay present in every session per 's Terms of Service.

Both paths are legitimate. The terminal path is simpler and more honest about
what  is. The MCP path is more powerful but requires the human to
understand that  is calling nurb's tools, not its own.
