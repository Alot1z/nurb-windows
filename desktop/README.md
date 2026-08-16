# nurb desktop

A Tauri shell around nurb: project rail, agent chat column, and the live viewer in one window. This is the Windows desktop half of the nurb-windows fork.

## Dev setup

Windows 10/11 x64, the Rust toolchain with the MSVC target, Node 22+, uv, and Python 3.13. Then:

```
npm install
npm run tauri dev
```

Debug builds run nurb out of this checkout (`uv run --project <repo> nurb dev`) and the ACP adapters through PATH `npx`, so nothing needs provisioning. `cargo test` inside `src-tauri/` needs `scripts/stage.py` to have run once (the build script wants the uv sidecar); any `tauri dev` or `tauri build` runs it for you.

## Provisioning model

Release builds never touch the dev environment. On first launch the app provisions everything into its app data directory (`%APPDATA%\dev.alot1z.nurb.windows`):

- `python/`, `env/`: a managed CPython and a venv holding the bundled nurb wheel plus its hash-pinned lock, installed by the bundled uv sidecar (`binaries/uv/uv.exe` on Windows).
- `node/`, `adapters/`: the pinned Node LTS (downloaded from nodejs.org, checksum-verified) and the Claude and Codex ACP adapters, installed with `npm ci` from a committed integrity lock. The adapters are deliberately not bundled: the Claude Code binary inside `@anthropic-ai/claude-agent-sdk` is all-rights-reserved and must not be redistributed. Cursor and Grok speak ACP natively and are never provisioned at all: the app finds the CLI the vendor's own installer put on the machine, then PATH.
- `provisioned.json`: what was installed, compared per component on every launch. A changed wheel payload, Python lock, Node version, or adapter lock redoes only its own component; a broken venv is deleted and rebuilt.

`scripts/stage.py` stages the bundle inputs before every build, cross-platform: the nurb wheel from this checkout, a hash-pinned uv lock, the committed adapter manifest and lock, and the checksum-verified uv binary for the target platform.

Debug-build test overrides, never compiled into release: `NURB_DESKTOP_PROVISIONED=1` makes a debug build use the provisioned environment, and `NURB_DESKTOP_DATA=<dir>` points the whole app (registry, sessions, provisioned env) at a scratch directory.

## Release

The engine and the app share one version. `windows-release.yml` builds the signed NSIS installer (`nurb_<version>_x64-setup.exe`), its updater signature, and the `latest.json` updater manifest on the `vX.Y.Z` tag, and attaches them to the fork's GitHub release. In-app updates are signed with an Ed25519 keypair: the public key is committed and embedded in the app, and the private key lives only in the repository secrets `TAURI_SIGNING_PRIVATE_KEY` and `TAURI_SIGNING_PRIVATE_KEY_PASSWORD`. Losing that private key means shipped apps can never update again. See `docs/windows/RELEASE.md` for the full ceremony.

macOS and Linux remain supported by the shared core, but their desktop packaging and notarization are upstream's flow; this fork's desktop release pipeline is Windows.
