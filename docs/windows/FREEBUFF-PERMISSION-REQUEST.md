# Written permission request to Freebuff (draft)

Status: draft, not sent. Address: support@codebuff.com.

This is the written-confirmation request the integration research
(`docs/windows/FREEBUFF-INTEGRATION.md`, section 27) requires before the
Freebuff developer extensions can move out of developer-only status. Until a
reply, the extensions stay developer-only and off by default, and none of the
behaviors below are shipped as public features.

Send this from the fork maintainer's address, with a subject line like
"Third-party terminal hosting of the Freebuff CLI - permission request".

---

## Request

Hi Freebuff team,

I maintain a Windows desktop application (nurb-windows,
https://github.com/Alot1z/nurb-windows, a fork of the open-source nurb CAD
tool) and want to let its users start the official Freebuff CLI from inside
the app. I am writing to confirm that the specific integration described
below is acceptable under your Terms of Service before I ship it as anything
more than a developer experiment.

What we do:

1. **Terminal panel hosting.** The app discovers the user's own official
   Freebuff CLI install (npm install -g freebuff, or the downloaded binary)
   and launches it with the official `--cwd` flag, pointed at the user's
   current project, inside a terminal panel the app hosts (a Windows ConPTY,
   the same mechanism Windows Terminal and VS Code use). The official CLI
   runs unmodified: its own login, ads, model access, sessions, and backend
   communication are entirely its own.

2. **Byte-only transport.** The app moves keystrokes and terminal output
   between the user and the CLI. It never sends prompts programmatically,
   never injects context, never chains sessions, never auto-continues, and
   never parses the session as data. A human starts every session and stays
   at the terminal.

3. **Nurb MCP server (user-enabled).** Separately, we ship a local MCP server
   (`nurb mcp`) exposing only nurb's own commands (build, check, inspect,
   verify, export) as tools and the project's files as resources. A user can
   add it to their own Freebuff `mcp.json` if they want; we never edit
   Freebuff configuration. Tool calls happen only inside a session the human
   started.

4. **External launch of Freebuff Desktop.** A button that launches the
   official Freebuff Desktop app installed by the user, with no window
   manipulation and no project targeting (we understand none is documented).

What we do not do: we do not bundle, modify, patch, or recompile any Freebuff
binary; we do not call Freebuff's backend directly; we do not automate,
chain, or headlessly run Freebuff sessions; we do not suppress, filter, or
redirect Freebuff's telemetry or ads; we do not spoof location or identity;
we do not create accounts.

Questions we would like confirmed:

1. Is hosting the official Freebuff CLI in a third-party terminal panel, with
   byte-only transport as described, acceptable as normal use of the
   official product?
2. May the app use the Freebuff name (text only) in its developer extension
   list to label the CLI and Desktop entries? We will not use the logo or
   trade dress without separate consent, and we will label the entries as
   third-party integrations, not official endorsements.
3. Is a user-configured nurb MCP server in the user's own mcp.json
   acceptable? May the app offer to write that entry, or must the user paste
   it manually?
4. Is externally launching Freebuff Desktop acceptable?

If any of these require terms beyond what the Terms of Service already
permit, we would appreciate a short written confirmation or the conditions
under which they are acceptable.

Thank you,
[nurb-windows maintainer]
