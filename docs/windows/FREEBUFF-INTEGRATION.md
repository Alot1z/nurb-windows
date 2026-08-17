# Nurb-Windows x : Integration Research

Status: research and architecture investigation only. Nothing in this document is implemented.
Scope: how Nurb-Windows can legitimately integrate the official  product (CLI and Desktop) without violating 's Terms of Service, without reverse-engineering, and without sacrificing the upstream-port cleanliness of the fork.

Sources were inspected directly on 2026-08-17: the  npm package (@0.0.149), the AI/ GitHub repository (Apache-2.0), .com (product pages), .com/terms-of-service (effective 2026-07-23), .com/privacy-policy (effective 2026-07-23), .com/docs, and the npm registry. The complete source register is section 34.

---

## 1. Executive Summary

 is an official, free, ad-supported coding agent whose Terms of Service deliberately restrict how its free inference may be accessed: individual, human-directed use through the normal interfaces of official products, with a human present for the whole session. The Terms are unusually explicit that scripts, custom clients, wrappers, integrations, bots, and autonomous agents are not allowed to reach free inference, and that a human must initiate and stay present in every session.

The single most important finding: **Nurb's existing agent model (Agent Client Protocol over stdio, where the app drives the agent) is exactly the shape of automation the  Terms prohibit for the free service.**  cannot be plugged into the ACP slot the way Claude, Codex, Cursor, and Grok are. This is not a technical limitation ( simply has no ACP interface either), it is a contractual one.

The strongest legitimate architecture is therefore:

1. A **terminal-hosted agent** surface in Nurb-Windows that launches the official  CLI (discovered on the machine like Cursor/Grok are today, never bundled) inside a Nurb-hosted ConPTY terminal panel, passing the user's project via 's own `--cwd` flag. Nurb moves bytes, never prompts: the human types into the official TUI, the official product authenticates, shows ads, and talks to its own backend. This is functionally identical to running `` in the VS Code integrated terminal, which is normal use.
2. An **MCP server shipped by Nurb** that exposes nurb commands and project resources as MCP tools.  is an MCP *client* (standard `mcp.json`, the Claude Code format), so the user can configure  to call nurb build/check/inspect through its own supported mechanism. Tool calls the agent makes after a human starts the session are explicitly allowed by the Terms ("Automation performed by our products after a human starts a session is allowed").
3. A clear **human-in-the-loop contract**: Nurb never sends a prompt to  programmatically, never injects context, never chains sessions, never auto-restarts. Every session is started by a human keystroke and the human stays at the terminal.

Everything else in the more ambitious wish list is either prohibited (driving  as a sub-agent, mirroring parsed output into the Nurb chat, embedding Desktop, direct API calls to free inference, bundling the binary) or unsupported by  (no ACP, no open-project desktop IPC). The officially documented programmatic path that *is* allowed is the paid  service through the `@/sdk` with a  API key, which the Terms' SDK carve-out explicitly protects. That is a different product from free  and should be treated as such.

The full decision table is section 26 (recommendation) and section 32 (BUILD / WAIT / DO NOT BUILD).

---

## 2. Current Nurb-Windows Architecture

Nurb-Windows is a Tauri v2 desktop app around a Python CAD core:

- `src/nurb/` — the Python runtime: registry (`@part`, signature introspection), builder (build123d/OCCT B-rep, tessellation, GLB), checks, polish, orient, probe, api, card, extract, mesh, measurements, edit, render, slicing, stress, doctrine, server (watcher + HTTP/websocket), viewer.html (three.js r169 vendored), cli.
- `src/nurb/platform/` — the Windows abstraction layer: paths (HOME/USERPROFILE, `%APPDATA%\nurb` config, cache, temp), process launching, executable resolution, launcher (`viewer.cmd`).
- `desktop/src-tauri/` — the Rust shell: provisioning of a private Node + uv + adapter runtime into `%APPDATA%\dev.alot1z.nurb.windows`, ACP session management, agent registry, updater (minisign-signed, pinned to the fork's release endpoint), NSIS installer config.
- `desktop/src/` — React frontend: rail of parts, chat columns, agent pane, permission dialogs, setup wizard.
- Release: tag-pushed `windows-release.yml` publishes the signed NSIS installer, `.sig`, and `latest.json` to Alot1z/nurb-windows releases. CI: `windows-build.yml` (portability audit, 553 Python tests with Chromium, cargo tests, npm tests, signed build, artifact validation) and `upstream-sync.yml`.

The extension insertion points are enumerated in section 4.

## 3. Existing Agent Architecture

The agent model is a closed enum in `desktop/src-tauri/src/agents.rs` with two host categories:

- **Adapter-hosted (Claude, Codex):** the app provisions pinned npm adapters (`@agentclientprotocol/claude-agent-acp`, `@agentclientprotocol/codex-acp`) into the private runtime; the adapter bundles the vendor's real CLI. Sign-in reads the vendor's own credential store.
- **ACP-native (Cursor, Grok):** the app never installs these; it discovers the vendor-installed binary on disk (`~/.local/bin/agent.exe`, `~/.grok/bin/grok.exe`, PATH fallback) and spawns `agent acp` / `grok agent stdio`.
- **Help-only ( today):** `ExternalAgent` entries with an install command and an honest note; the rail filters them out and the "More agents" modal shows them. An id here cannot parse as an `AgentKind`, which is what prevents a login or session from ever spawning it.

Sessions run in `acp.rs`: one ACP process per chat column, JSON-RPC over stdio, events (`user_text`, `agent_text`, `tool_call`, `permission_request`, `session_error`), permission dialogs, tool cards. The whole model assumes the app *drives* the agent and parses its output. That assumption is exactly what cannot be applied to 's free service (section 8, section 11).

What Nurb assumes every agent provides: a spawnable process, a machine-readable protocol, session events, and permission/tool visibility. An external agent that provides none of those (a human-driven interactive TUI) needs a different host shape: a terminal host, not a protocol host.

## 4. Existing Windows Port Architecture

The fork's Windows work is isolated so upstream merges stay cheap:

- Platform layer in `src/nurb/platform/` with OS-standard directories: config `%APPDATA%\nurb`, cache, temp; `HOME`/`USERPROFILE` handling; `viewer.cmd` launcher.
- Desktop provisioning and process handling in Rust (`provision.rs`, `env.rs`): Windows-specific probe files, retry-hardened health checks, WebView2, NSIS, minisign updater pinned to the fork.
- `.github/workflows/windows-build.yml`, `windows-release.yml`, `upstream-sync.yml` are fork-owned; upstream's `test.yml` is untouched.
- `docs/windows/WINDOWS-PATCHES.md` registers every intentional deviation from upstream.

A future agent-extension layer should follow the same rule: live in the fork's platform/desktop layer, keep `src/nurb` upstream-compatible, and keep upstream's `desktop/src` React surface additive. Nothing in this proposal touches upstream core files.

## 5. Current  CLI Architecture

Verified from the published npm package (@0.0.149) and the AI/ repository:

```
npm install -g         (MIT wrapper, engines node>=16, one dep: tar)
   ->  bin -> index.js -> launcher.js (createLauncher)
   -> downloads native binary "codecane" from GitHub releases
      (asset codecane-win32-x64.tar.gz; darwin/linux/win32 x arm64)
   -> stores the binary under the user config dir
      (docs: ~/.config/manicode/; the runtime is the shared Manicode/ engine)
   -> runs an interactive TUI (OpenTUI + React) in the current terminal
```

The launcher is a genuine self-updating wrapper: it checks the npm registry for the latest wrapper, downloads/extracts the binary with resume support, detects Windows native crashes (NTSTATUS 0xC0000409 etc.), falls back to a no-AVX2 build on old CPUs, and resets terminal state when the child dies. The binary is Bun-based.

The  CLI argument surface (from `cli/src/cli-args.ts`) is deliberately minimal and interactive-only:

```
 [-v, --version] [--continue [conversation-id]] [--cwd <directory>] [login]
```

There is **no prompt argument, no non-interactive mode, no scripted output, no agent override, no mode flags** ( always runs LITE). Compare the paid `` CLI, which adds `[prompt...]`, `--agent`, `--lite/--max/--plan`, `login`, `publish`.  is a TUI, period. It requires a TTY (raw mode, alternate screen, mouse modes), which means hosting it over plain pipes is not viable; it needs a real terminal (ConPTY on Windows).

When run on Windows: the npm shim downloads `codecane.exe`, then the TUI takes over the console. The product handles its own authentication (GitHub/Google sign-in), account state, model access, ads, telemetry, and updates. The wrapper sends bounded update/telemetry events itself (e.g. `cli.update__failed`).

## 6. Current  Desktop Architecture

 Desktop is a separate native installer product: Windows 64-bit plus a "no AVX2" build, macOS (Apple Silicon and Intel), Linux AppImage. It is free and ad-supported, sign-in with GitHub or Google, no API keys. Per the product page it runs multiple agents in parallel, each in its own workspace, and can also drive locally installed Claude Code and Codex agents using the user's own provider accounts.

Two facts matter for integration: the builds are **not code-signed yet** (the product page says so explicitly, and Windows shows SmartScreen "More info -> Run anyway"), and there is **no public evidence of a supported embedding or project-targeting mechanism** (no documented CLI args, deep links, IPC, or URI scheme for opening a project in an existing instance). The source repository has no `desktop/` tree; the desktop product is closed. Any assumption that Desktop can be embedded in another app's window, or instructed to open a project, is unsupported speculation and must not be built on.

## 7. Official  Package/Binary Structure

| Component | What it is | License | Distributed by |
| --- | --- | --- | --- |
| npm `` | Thin launcher wrapper (index.js, launcher.js, http.js) | MIT | npm registry |
| `codecane` binary | The real agent runtime, Bun-compiled | Apache-2.0 repo | GitHub releases of AI/, downloaded on first run |
| `` (npm) | Paid sibling CLI, `` and `cb` bins | (commercial) | npm registry |
| `@/sdk` | Programmatic SDK, Client + custom agents/tools | Apache-2.0 | npm registry |
|  Desktop | Native installer app (Windows/macOS/Linux) | closed | .com/desktop |

The official execution chain is: user installs the npm wrapper, the wrapper fetches the official binary from official releases, the binary talks to the official backend. For Nurb integration, the correct posture (matching how Nurb already treats Cursor and Grok) is: **require a legitimate user installation, discover it on the machine, never bundle it.** Redistribution of the binary would additionally trigger Apache-2.0 attribution duties and, more importantly, update-responsibility and trademark questions. Discovery should target the documented locations: the `` npm bin on PATH, and the downloaded binary under the user config dir (`~/.config/manicode/`).

## 8.  ToS Clause Analysis

Source: https://.com/terms-of-service, effective 2026-07-23. Clause-by-clause table for the parts that govern this integration:

| Clause | Exact requirement | Applies? | Risk | Confidence | Action |
| --- | --- | --- | --- | --- | --- |
| Free access is individual, human-directed use through normal interfaces | Free usage is "provided for individual, human-directed use through the normal interfaces and intended functionality of our products" | Yes, to any free use | Core constraint | High (explicit) | Design every integration so the human drives the official product directly |
| No custom clients/wrappers/integrations for free inference | "You may not call the underlying servers or endpoints directly or through scripts, custom clients, wrappers, integrations, or third-party software" | Yes | High for any proxy/re-presentation | High (explicit) | Never route, parse, or re-send  traffic; the official binary talks to its own backend |
| No bots/scripts/autonomous agents | "Use a bot, script, macro, headless browser, autonomous agent, or similar automation to operate our products or submit requests" | Yes | High for ACP-style driving | High (explicit) | Nurb must not send prompts, chain, or auto-continue  sessions |
| Human initiates and remains actively present | "A human must initiate each session and remain actively present while it runs" | Yes | High | High (explicit) | Session start and every prompt is a human keystroke at the TUI |
| Product-side automation allowed | "Automation performed by our products after a human starts a session is allowed" | Yes | Enables MCP tools | High (explicit) |  calling nurb tools via MCP after a human starts is product automation |
| No location spoofing | No proxy/VPN/relay to fake country for models/features/pricing | Yes | Must never touch | High (explicit) | Nurb must not alter proxy/locale behavior of the  process |
| Reverse engineering | "Reverse engineer, decompile, disassemble, or derive Service's source code or underlying components" prohibited except where law permits | Yes | High if we parse internals | High (explicit) | No protocol reverse engineering; no TUI output parsing as a protocol |
| Trademarks/trade dress | "Our trademarks and trade dress may not be used in connection with any product or service without the prior written consent" | Yes | Medium for branding | High (explicit) | The  name in Nurb's UI needs care; ask for consent to use the logo/branding |
| SDK/API/open-source carve-out | "Nothing in these Terms limits rights granted under an applicable open-source license or in our published documentation for an SDK, API, or other developer tool" | Yes, for SDK use | Low | Medium (interpretive) | The paid  SDK and the Apache-2.0 repo are governed by their licenses/docs, not the free-access restrictions |
| No impersonation | "Impersonate Company or another person or entity" prohibited | Yes | Low if honest | High (explicit) | Nurb must present  as the official product, never as a Nurb feature |
| No interference/scraping | "Disable, overburden, damage, or impair Service"; "Scrape, monitor, or copy material from Service through automated means without our written consent" | Yes | Low-Medium | High (explicit) | No output scraping into a database; no ad suppression |
| One account per person | One  account per person | Yes | Low | High (explicit) | Nurb must never create or manage accounts |

## 9. Privacy/Telemetry Analysis

From the Privacy Policy (effective 2026-07-23):  collects prompts, messages, code, files, repository data ("Prompt and Project Data"), plus usage/device information (IP, country, app version, OS, features used, timestamps, install/session identifiers, crash info, diagnostics). Products "send bounded usage, performance, and diagnostic events to analytics and observability providers." Free access is ad-supported, and prompt analysis feeds ad selection; separately uploaded files and connected repositories are not passed to ad providers. No AI training unless a model or feature is labeled for it.

Consequences for Nurb:

- The official product's telemetry is expected and must run untouched. Nurb must not suppress, filter, or redirect it.
- What reaches  is whatever the user types plus the working directory. Nurb's `--cwd` does not upload files; the agent reads them itself under the user's own session.
- Nurb-side data flow must be minimal and explicit: project path only; no CAD state, no environment, no credentials forwarded into the  process.

## 10. Security/Abuse-System Analysis

 operates account limits, per-person free limits, location checks, session limits (e.g. six one-hour sessions per day for limited regions), and fraud/abuse scoring (the Privacy Policy lists "fraud, abuse, or security scores"). Nurb's design must stay within normal, legitimate, human-directed use:

- Do not design around avoiding logs, disguising traffic, spoofing identity, suppressing telemetry, defeating rate limits or location checks, or creating extra accounts.
- Keep Nurb-created behavior within documented usage: one human, one official session, official auth, official binary.
- If a human wants more capacity, the legitimate answers are the paid  service (SDK/API key) or 's own limits, not Nurb-side workarounds.

## 11. CLI vs Desktop Comparison

| Criterion |  CLI |  Desktop |
| --- | --- | --- |
| Technical integration | Strong: spawnable process, `--cwd`, official TUI, ConPTY-hostable | Weak: no documented launch/project targeting mechanism |
| Human interaction | Terminal TUI; ideal for Nurb's panel | Own window, own workspace model |
| Project context | `--cwd` is official | No verified open-project path |
| Windows support | First-class (win32-x64/arm64 binaries, AVX2 fallback, WINDOWS.md in repo) | Windows builds exist but not code-signed yet |
| Process hosting | Nurb can host the process (ConPTY) | External launch only |
| Session control | Human-driven by contract; no scriptable mode | Even less |
| Auth | Official sign-in flow in the TUI | Official sign-in flow in the app |
| Ads | Shown by the product itself | Shown by the product itself |
| ToS exposure | Same free-access rules for both | Same free-access rules for both |
| Future compatibility | The CLI surface is minimal and stable; MCP client support is documented | Closed product; no public extension surface |

Verdict: the CLI is the integration target. Desktop is a "launch the official app" convenience at most.

## 12. Nurb <->  Boundary

| Direction | What is allowed | What is not |
| --- | --- | --- |
| Nurb ->  | Launch the official CLI; pass the project via `--cwd`; provide a terminal for it; let the user type | Sending prompts, injecting context, chaining sessions, auto-restart, parsing its output into chat |
|  -> Nurb | The user configures 's MCP client to call Nurb's MCP server (nurb build/check/etc.) | Nothing Nurb-side receives internal  state; no protocol shims |

The two directions are asymmetric on purpose: Nurb treats  as a product to be hosted, not a backend to be driven.

## 13. MCP Analysis

 is an MCP **client**: the repository has `common/src/mcp/client.ts` (stdio, SSE, and streamable-HTTP transports via the official `@modelcontextprotocol/sdk`) and `sdk/src/agents/load-mcp-config.ts`, which reads the standard `mcp.json` format (the same shape Claude Code and Cursor use), including `$VAR` env expansion. So the officially supported way to give  nurb capabilities is:

- Nurb-Windows runs a local **MCP server over stdio** exposing nurb tools (`nurb_build`, `nurb_check`, `nurb_inspect`, `nurb_export`, project resources like the card and doctrine).
- The user adds one entry to their project `mcp.json` (or Nurb writes the entry with explicit user consent, never silently).
- The agent's tool calls are "automation performed by our products after a human starts a session," which the Terms explicitly allow.

Where MCP is insufficient: it does not carry terminal bytes, human-presence state, or a session lifecycle for interactive TUIs. That is what the ConPTY host is for. MCP and the terminal host are complementary, not alternatives.

## 14. LSP Analysis

LSP contributes useful *shapes*: initialize/capabilities negotiation, request/response with ids, notifications, cancellation, workspace roots, and lifecycle discipline. But LSP is server-to-editor about documents and diagnostics;  is neither an editor nor a language server. Using LSP for the  integration would be forcing a square peg. Two ideas are worth borrowing, both inside the MCP server instead: explicit capability/version negotiation on initialize, and cancel-on-session-end. No separate LSP surface.

## 15. PTY/ConPTY Analysis

The  TUI needs a real terminal: raw input mode, alternate screen (`?1049`), mouse modes (`?1000`-`?1006`), focus reporting, bracketed paste, and resize events. The launcher explicitly resets these modes on exit, which confirms the TUI's terminal assumptions. Hosting it over pipes breaks it; hosting it over a Windows **ConPTY** (pseudoconsole) works.

ConPTY is the right mechanism on Windows: it provides a console-adjacent terminal surface for a child process with resize, ANSI handling, Unicode, and Ctrl+C/Ctrl+Break semantics, and it is what every modern Windows terminal (Windows Terminal, VS Code) is built on. In Rust, `portable-pty` (the crate behind many Rust terminals) wraps ConPTY on Windows and pty on Unix with a small API. Process groups, cancellation, and cleanup follow the terminal-emulator pattern: kill the child tree on panel close, send Ctrl+C on the user's request, never auto-restart.

One design rule: the ConPTY host is a terminal transport. Nurb reads bytes only to render them, writes bytes only from the user's keyboard, and never interprets the TUI as structured data. That keeps the integration a terminal, not a custom client.

## 16. Agent Runtime Analysis

Nurb's ACP runtime is for automatable agents and is fine as-is for Claude/Codex/Cursor/Grok.  is a different *kind* of agent: an external, human-driven product with no machine protocol. The correct abstraction is a new host kind, "terminal-hosted agent," defined by: a discovered executable, an official launch command (`--cwd`), a ConPTY session, and a strict no-automation contract. It is not a sub-agent, not an MCP server, not an LSP server: it is a hosted product session. Classifying  as "an external agent runtime rather than a sub-agent" is accurate and is exactly why it must not be driven like one.

## 17. Tiny Agent Analysis

Not needed.  ships its own native runtime (Bun-compiled codecane) and its own launcher. A TypeScript shim between Nurb and  would add a third party to a two-party interaction for no capability gain, and it would risk looking like exactly the "wrapper" the Terms prohibit. No tiny-agent component.

## 18. New Nurb Agent Runtime Protocol Proposal

Not justified for . ACP already covers every automatable agent Nurb hosts;  must not be automated; so there is no protocol-shaped gap to fill. The real gap is the **terminal host** (section 15) plus the **MCP server** (section 13). Recommendation: do not invent a protocol. If Nurb later wants a generic "external agent" contract, the honest one is a manifest + launch descriptor (id, label, install/discovery rule, launch argv, host kind: `acp` or `terminal`) rather than a wire protocol.

## 19. Plugin/Addon System Proposal

A light extension registry in the fork's desktop layer, not in upstream core:

- Manifest fields: id, label, host kind (`acp` / `terminal`), discovery (fixed install dir, PATH, or npm bin), launch argv template, install command, capability note, minimum nurb version, tested-against version.
- Discovery mirrors the existing Cursor/Grok pattern (`native_bin()`): vendor-installed location first, PATH fallback, no bundling.
- A `terminal` host kind is the only new runtime capability; `acp` reuses the existing session code.
- Security: the registry only launches known vendors' binaries from known locations; PATH resolution is validated; the user confirms before a new host is enabled.
- The registry lives in `desktop/src-tauri/src/agents.rs` style code and `docs/windows/WINDOWS-PATCHES.md` registers it; upstream `src/nurb` is untouched, so sync stays clean.

## 20. Human-in-the-Loop Design

The contract, enforced by design rather than policy:

- Session start: user clicks "" in Nurb, Nurb spawns the official CLI in a ConPTY panel; the TUI's own login/session flow runs. Nurb does not authenticate anything.
- Presence: the panel is the session. If the user closes it, the session ends; there is no background .
- Prompts: only keystrokes reach the TUI. Nurb has no path to inject text (the panel input is wired user -> ConPTY directly).
- No chaining, no queuing, no auto-continue. `--continue` is available but only if the user invokes it in the TUI.
- MCP tools: the user must have added the nurb MCP server to `mcp.json`; Nurb may offer to write that entry with explicit consent. Agent tool calls after a human-started session are allowed.
- The autonomous mode that the ACP agents support does not exist for  and must not be offered in the UI.

## 21. Token/Request Analysis

Hosting the CLI in ConPTY and rendering bytes adds **zero model tokens**: the requests are made by the official product to its own backend exactly as in a normal terminal. Mirroring output into the Nurb chat UI would add nothing in *model* tokens either, but it is prohibited for other reasons (custom-client re-presentation). What *would* add tokens/requests: injecting Nurb project context into the session, chaining follow-ups, sending prompts programmatically, duplicated history. All of those are both wasteful and prohibited. The token-efficient design is the compliant design: one user, one official session, one official request per prompt.

## 22. Security Threat Model

| Threat | Control |
| --- | --- |
| PATH hijack / malicious  | Discover the npm bin and the documented config-dir binary; do not exec bare names from arbitrary PATH entries without checking; warn on unknown locations |
| Argument injection | `--cwd` is passed as a single argv element via `Command::arg`, never string-concatenated into a shell |
| Project path injection | Validate the project dir is a real directory under a user-chosen root; no shell evaluation |
| Privilege inheritance | Spawn with the user's normal token; never elevated |
| Secret leakage | Nurb never writes credentials; the  process manages its own auth store |
| Process cleanup | Kill the ConPTY child tree on panel close; no orphaned TUIs; no auto-restart |
| Malicious MCP config | The nurb MCP server binds to stdio of a process Nurb itself starts; it serves only the local project; tools are the existing nurb CLI commands |

## 23. Privacy/Data-Flow Model

```
User -> Nurb: clicks "" + types (keystrokes go to the TUI only)
Nurb -> : launch + --cwd <project dir> (no files, no env, no CAD state)
 -> backend: official product traffic, unchanged, ads and telemetry intact
 -> user: official TUI rendered byte-for-byte in the ConPTY panel
 -> nurb MCP server (user-configured): nurb_build / nurb_check / ... tool calls
```

The only automatic data transfer from Nurb into the  process is the project directory path. Everything else is explicit user action. Nurb-side data (CAD state, measurements) never leaves Nurb except through tools the agent explicitly calls after a user-started session.

## 24. Architecture Comparison

| Architecture | Technical | ToS | Licensing | Security | Privacy | Performance | Maintainability | UX | Future |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A. External Desktop launch | Weak (no targeting) | Probably allowed (launching an installed app) | Fine | Fine | Fine | Fine | Trivial | Poor (two windows, no --cwd) | Weak |
| B. Official CLI in external terminal | Simple | Allowed (normal use) | Fine | Fine | Fine | Fine | Trivial | Poor (Nurb just shows a command) | Good |
| C. Official CLI in Nurb ConPTY panel | Strong | Probably allowed (terminal hosting) | Fine | Good (process control) | Fine | Fine | Moderate | Best (one window, --cwd) | Good |
| D. CLI + ACP-style Nurb driver | Possible for paid SDK; prohibited for free service | Prohibited for free access | Fine only via paid SDK | N/A | N/A | N/A | High | N/A | N/A |
| E. Desktop + invented IPC/deep-link | Unsupported (no official mechanism) | Unsupported; would need hacks | N/A | Poor | N/A | N/A | High | N/A | Dead end |
| F. Full custom API/client | Backend calls | Prohibited without written permission | N/A | N/A | N/A | N/A | High | N/A | Dead end |
| G. Generic extension runtime | Good | Depends on host kind per agent | Fine | Good | Good | Good | Moderate | Good | Good |

## 25. ToS Compliance Matrix

| Architecture | Technical status | ToS status | Risk | Written permission? |
| --- | --- | --- | --- | --- |
| Direct launch of official CLI (user runs it) | Works today | Explicitly allowed (normal use) | None | No |
| Nurb launches official CLI | Trivial | Probably allowed (launching an app) | Low | Unlikely, but confirm |
| Nurb launches CLI with --cwd | Trivial | Probably allowed (official flag) | Low | Unlikely, but confirm |
| ConPTY hosting of official CLI | Strong | Probably allowed (terminal emulation) | Low-Medium | Confirm with  before shipping as a headline feature |
| Output mirroring into Nurb chat | Possible | Probably prohibited (custom client re-presentation) | High | Yes |
| Context injection into sessions | Possible | Probably prohibited (integration access) | High | Yes |
| Nurb tools exposed to  (MCP) | Strong, official | Allowed (MCP client is official; product-side automation allowed) | Low | No, but document it |
|  capability events into Nurb | Not supported | N/A | N/A | N/A |
| Desktop external launch | Possible | Probably allowed | Low | No |
| Desktop embedding | Hack | Probably prohibited + unsupported | High | Yes |
| MCP integration | Official | Allowed | Low | No |
| LSP integration | Unnecessary | N/A | N/A | N/A |
| Custom protocol | Possible | Probably prohibited for free access | High | Yes |
| Direct API calls to free inference | Technically reachable | Explicitly prohibited | Very high | Yes |
| Copying  code into Nurb | Possible (Apache-2.0) | Allowed by license with attribution, but unnecessary | Low | No (license suffices) |
| Bundling the  binary | Possible | License allows; product posture unclear; update responsibility | Medium | Prefer discovery over bundling |

## 26. Recommended Architecture

Build, in order:

1. **Terminal-hosted agent surface** (`host kind: terminal`) in the Nurb-Windows desktop: discover the official  CLI (npm bin + config-dir binary, like Cursor/Grok discovery), launch ` --cwd <project>` in a ConPTY panel (Rust `portable-pty`), render bytes only, wire user keystrokes to the TTY only, kill the tree on close. The  entry moves from the "More agents" help list into the rail as a real, hostable agent whose card says "runs in a terminal in this app; official  session, your account and ads stay 's."
2. **Nurb MCP server** (stdio) exposing the nurb CLI tools and project resources, with an offer-to-configure `mcp.json` flow that requires explicit consent.
3. **Desktop convenience**: a "Open in  Desktop" action that launches the official app (no project targeting, because none is officially supported).
4. **Documentation**: this report, a user-facing " in nurb" page, and the honest capability notes in the UI.

Do not build: ACP driving of , chat mirroring, context injection, auto-chaining, Desktop embedding, direct API calls, bundling the binary, or any location/telemetry manipulation.

## 27. Required  Permission Questions

Before shipping the headline integration, ask  (support@.com) for written confirmation of:

1. Is hosting the official  CLI inside a third-party terminal panel (ConPTY) acceptable as normal use? (Recommended wording: "we run your official binary in our own terminal surface; no prompts are sent programmatically; the user types into the official TUI.")
2. Is using the  name and logo in the Nurb agent list acceptable, and under what conditions? (The ToS requires written consent for trademarks/trade dress in connection with another product.)
3. Is the nurb MCP server in the user's `mcp.json` acceptable? (Expected yes: MCP is official and the Terms allow product-side automation.)
4. May Nurb auto-write the `mcp.json` entry, or must the user paste it manually? (Consent detail.)
5. Anything beyond the above (e.g. autonomous driving, embedding Desktop) is out of scope until written permission exists.

## 28. Repository/Extension Structure

```
desktop/src-tauri/src/
  agents.rs        extend: AgentKind stays 4 ACP agents; add HostKind::{Acp, Terminal}
                   and a TERMINAL_HOSTS registry entry for 
  terminal.rs      NEW: ConPTY session (portable-pty), byte transport, resize,
                   child-tree kill, no parsing
  mcp.rs           NEW: stdio MCP server exposing nurb CLI tools + project resources
  prefs.rs         maybe: remember which hosts the user enabled
desktop/src/
  TerminalPanel.tsx  NEW: renders the ConPTY surface (xterm.js style panel, local)
  AgentsHelp.tsx     update:  card now points at the hosted session
  Chat.tsx           no change to ACP paths
src/nurb/          no changes (upstream core stays clean)
docs/windows/      -INTEGRATION.md (this file), WINDOWS-PATCHES.md entry
```

The terminal host and MCP server are additive and Windows-first but not Windows-only; on macOS/Linux the same host uses the pty side of `portable-pty`. Upstream sync impact: none to `src/nurb`; `desktop/src-tauri` additions are new files plus one additive registry change, both documented in WINDOWS-PATCHES.md.

## 29. Implementation Specification

- **Discovery**: resolve `` via (a) `%APPDATA%\npm\.cmd` and PATH ``, (b) the config-dir binary (`~/.config/manicode/`, platform-appropriate). None found -> the help modal shows `npm install -g `, unchanged.
- **Launch**: `Command` with argv `["", "--cwd", <project>]`, inheriting the user environment, normal privileges, working directory = project.
- **Host**: `portable-pty` PtyPair; a reader thread pumps bytes to the panel; a writer path pumps panel input to the TTY; resize events call `resize(size)`; on close, kill the child tree (job object on Windows) and drop the pair.
- **Contract**: no other I/O paths. No prompt injection, no output parsing, no logging of session content beyond what the panel shows.
- **MCP server**: stdio transport, `initialize` with protocol version and a server info block, `tools/list` (nurb build/check/inspect/verify/export/render/rules/api + project file resources), `tools/call` runs the nurb CLI in the project dir with a timeout, `resources/read` for the card and doctrine. Config: user adds `nurb` to `mcp.json`; Nurb offers to write it with consent.
- **UI**: rail entry "" with a note ("official  session in a terminal here"); panel with the TUI; a separate small action "Open  Desktop" (external launch).
- **Error states**: binary missing (show install command), TUI crash (show the launcher's own error text), panel closed (end session), no project (disable).
- **Tests**: unit tests for discovery/argv construction (no shell), ConPTY smoke test that spawns a dummy TUI and round-trips bytes, MCP server tool-call tests against a scratch project, a "no-injection" test asserting there is no code path that writes to the TTY except user input.
- **Packaging**: nothing new to ship in the installer; the feature discovers the user's own  install.

## 30. Testing Strategy

| Area | Test |
| --- | --- |
| Discovery |  present/absent/invalid location; PATH hijack case |
| Launch | argv correctness (--cwd as one arg), cwd set, env inherited |
| ConPTY | round-trip input/output with a fake TUI; resize; Unicode; Ctrl+C; crash; cleanup; no orphans |
| No-automation contract | static test: the terminal writer is only reachable from the input event path |
| MCP | tools/list, tools/call against scratch project, timeout, missing project |
| UI | rail shows  when installed; help modal otherwise; panel renders |
| ToS/behavioral | checklist in CI docs, not code: human-initiated, human-present, no chaining, no telemetry suppression |

## 31. Production Gate

Ship the  terminal host only when: the ConPTY session passes the fake-TUI round-trip and cleanup tests on a real Windows runner; the MCP server passes tool-call tests; the no-injection test exists and passes; the docs (this file) are complete; and written confirmation from  is attached for any item flagged in section 27. Anything that requires written permission but lacks it must ship behind a clearly labeled opt-in at most, and the autonomous capabilities must not exist at all.

## 32. Future Extensions

The `terminal` host kind generalizes to any interactive CLI agent (e.g. a future local-model TUI). The MCP server generalizes to any MCP-capable agent that uses nurb tools. The registry pattern (manifest + host kind) means new integrations are config, not core changes. None of this depends on  specifics.

## 33. Open Questions

1. Does  consider a third-party terminal panel "normal use"? (Section 27, question 1. This is the one interpretive call with real weight.)
2. Is the  brand usable in the Nurb agent list without written consent? (The ToS says written consent for trade dress; a text name may differ from the logo, but ask.)
3. Does the MCP client configuration surface in the  CLI TUI have an official UI, or is `mcp.json` file-only? (The repo shows file-based loading; the UI question is cosmetic.)
4. Will  Desktop gain an official open-project mechanism? (If yes, external launch becomes project-targeted; if no, it stays a convenience.)
5. Is the paid  SDK path something Nurb should support as a second, distinct "" agent? (Allowed, documented, but it is a different product with API keys.)

## 34. Complete Source Register

All inspected 2026-08-17:

- https://.com/terms-of-service (effective 2026-07-23) - ToS text quoted in section 8
- https://.com/privacy-policy (effective 2026-07-23) - privacy/telemetry facts in section 9
- https://.com/desktop - Desktop product page (Windows builds, no-AVX2 build, not code-signed, workspace model)
- https://.com/cli - CLI install page (npm install -g )
- https://github.com/AI/ - repository (Apache-2.0, TypeScript/Bun monorepo, pushed 2026-08-17); README (five products, models, free-access tiers); WINDOWS.md; cli/README.md; sdk/README.md; sdk/package.json (@/sdk 0.10.7); cli/src/cli-args.ts ( vs  arg surface); sdk/src/agents/load-mcp-config.ts (mcp.json format); common/src/mcp/client.ts (stdio/SSE/streamable-HTTP MCP client); git tree listing (acp: 0 hits; mcp: 8 hits)
- https://api.github.com/repos/AI//releases - release assets codecane-darwin/linux/win32 x64/arm64 tarballs
- npm registry: @0.0.149 package tarball (package.json MIT, bin  -> index.js, dep tar; index.js -> launcher.js createLauncher; launcher.js: npm-registry latest check, tar download/extract with resume, Windows NTSTATUS crash handling, AVX2 fallback, terminal reset; http.js release client)
- npm registry: @1.0.685 (bins , cb)
- https://.com/docs (quick-start; binary path ~/.config/manicode/; modes)
- https://www..com/api-keys (referenced by the SDK README as the API-key source)
- Nurb-Windows local repo: desktop/src-tauri/src/agents.rs, acp.rs, provision.rs, env.rs; desktop/src/AgentsHelp.tsx, Chat.tsx, App.tsx; src/nurb/platform; docs/windows/WINDOWS-PATCHES.md

---

## Appendix: Implementation status (2026-08-17)

Per the implementation direction, the generic extension system and the two
 developer extensions are now built, as developer-only and off by
default:

- Extension registry (`desktop/src-tauri/src/extensions.rs`): manifests,
  declarative lookups, enable/disable state, version gate, dev-only flag.
- Terminal host (`desktop/src-tauri/src/terminal.rs`): ConPTY on Windows via
  `portable-pty`, byte-only transport, tested with a real child round trip.
-  CLI extension: discovers the user's own install (npm bin, then the
  config-dir binary), launches ` --cwd <project>` in the hosted
  terminal. No prompt injection, no parsing, no chaining: the human drives
  the official TUI.
-  Desktop extension: external launch only, no window manipulation.
- Nurb MCP server (`src/nurb/mcp.py`, `nurb mcp`): stdio MCP whose tools are
  the CLI commands; tested over a real pipe against a scratch project and
  smoke-tested against `examples/notch`.
- UI: xterm.js terminal panel and a "developer extensions" rail entry, both
  opt-in; the  pair stays out of the normal release surface.

What this appendix does not change: the ToS boundary analysis in sections
8-25 stands, the BUILD/WAIT/DO NOT BUILD table below still governs release
status, and the written-permission questions in section 27 still gate
promoting the  entries out of developer-only.

## Appendix: BUILD / WAIT / DO NOT BUILD

| Decision | Item | Basis |
| --- | --- | --- |
| BUILD | Terminal-hosted  (ConPTY panel, --cwd, byte-only transport) | Official binary, official auth/ads/telemetry, human-driven; equivalent to a terminal emulator; ToS probably allowed |
| BUILD | Nurb MCP server (stdio) exposing nurb tools to 's official MCP client | Official MCP support; product-side automation allowed; user-configured |
| BUILD | Move  from help-only to a real rail agent with the honest "terminal session" card | Matches how Cursor/Grok are surfaced; truthful capability note |
| BUILD | "Open  Desktop" external-launch convenience | Launching an installed app; no targeting, no embedding |
| BUILD | Human-in-the-loop contract tests + docs (this file) | Makes the boundary explicit and testable |
| WAIT | Desktop project-targeting/deep-link integration | No official mechanism exists; revisit if  ships one |
| WAIT | Using the  logo/trade dress in Nurb branding | ToS requires written consent for trade dress |
| WAIT | Auto-writing mcp.json | Needs a consent decision; default to user paste |
| WAIT | Anything named "" (paid SDK agent) | Allowed and documented, but a distinct product needing its own plan and API keys |
| DO NOT BUILD | ACP-style driving of  (prompts, events, tools into the session) | Explicitly prohibited: wrappers/integrations/autonomous agents may not operate the product; no ACP exists anyway |
| DO NOT BUILD | Mirroring/parsing  TUI output into the Nurb chat UI | Custom-client re-presentation; prohibited shape |
| DO NOT BUILD | Context injection or autonomous chaining of  sessions | Human must initiate each session and remain actively present |
| DO NOT BUILD | Embedding  Desktop in a Nurb window | Unsupported (closed product, no mechanism) and high-risk |
| DO NOT BUILD | Direct calls to 's inference backend | Explicitly prohibited without written permission |
| DO NOT BUILD | Bundling the  binary in the installer | Discovery is the Nurb pattern; bundling adds license/update/trademark duties |
| DO NOT BUILD | Telemetry suppression, location spoofing, rate-limit or account workarounds | Explicitly prohibited and abusive; never |

Technically possible is not the test. Supported by , permitted by the Terms, and honest about what it is: those three gates decide every row above.
