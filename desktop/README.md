# Nurb Windows desktop

The Windows desktop shell for nurb: a Tauri 2 app that provisions the nurb
engine, hosts the ACP agents, and embeds the nurb viewer.

## Provisioning model

Release builds never touch the dev environment. On first launch the app
provisions everything into its app data directory (`%APPDATA%\dev.alot1z.nurb.windows`):

- `python/`, `env/`: a managed CPython and a venv holding the bundled nurb wheel plus its hash-pinned lock, installed by the bundled uv sidecar (`binaries/uv/uv.exe` on Windows).
- `node/`, `adapters/`: the pinned Node LTS (downloaded from nodejs.org, checksum-verified), the Claude and Codex ACP adapters, and the official Gemini CLI, installed with `npm ci` from a committed integrity lock. Gemini speaks ACP natively through `--acp`; the app validates its Google AI Studio API key through ACP and stores the key in the OS credential store (Windows Credential Manager here; macOS Keychain upstream), never app preferences. These packages are deliberately not bundled: the Claude Code binary inside `@anthropic-ai/claude-agent-sdk` is all-rights-reserved and must not be redistributed. Cursor and Grok speak ACP natively and are never provisioned at all: the app finds the CLI the vendor's own installer put on the machine, then PATH.
- `provisioned.json`: what was installed, compared per component on every launch. A changed wheel payload, Python lock, Node version, or adapter lock redoes only its own component; a broken venv is deleted and rebuilt.

`scripts/stage.py` stages the bundle inputs before every build, cross-platform: the nurb wheel from this checkout, a hash-pinned uv lock, the committed adapter manifest and lock, and the checksum-verified uv binary for the target platform.

Debug-build test overrides, never compiled into release: `NURB_DESKTOP_PROVISIONED=1` makes a debug build use the provisioned environment, and `NURB_DESKTOP_DATA=<dir>` points the whole app (registry, sessions, provisioned env) at a scratch directory.
