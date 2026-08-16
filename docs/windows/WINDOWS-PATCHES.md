# Windows-specific patch register

This file records intentional downstream changes found in the current working tree.

## Runtime and platform

- `src/nurb/platform/**`: central Windows paths, executable naming, and subprocess helpers.
- `src/nurb/checks.py`: global config now uses the platform path surface.
- `src/nurb/server.py`: latest-version cache uses the platform cache directory.
- `src/nurb/cli.py`: Windows launcher, socket probing, and path-aware messages.
- `src/nurb/slicing.py`: Windows slicer discovery and user-profile locations.

## Desktop process model

- `desktop/src-tauri/src/process.rs`: central child-process ownership and tree termination.
- `acp.rs`, `agents.rs`, `provision.rs`, and `supervisor.rs`: use the centralized process layer.
- `acp/sandbox.rs`: Seatbelt remains on macOS; Windows currently runs without an equivalent sandbox boundary and this limitation is explicit.

## Runtime layout

- `env.rs`: Windows `Scripts/`, `node.exe`, npm layout, adapter JS entry resolution, and native Codex path resolution.
- The inherited Windows `PATH` is split into individual entries before being rebuilt; this was corrected during the audit.
- `provision.rs`: Windows Node archive selection, checksum validation, extraction, OS identification, and process cleanup.
- `desktop/scripts/stage.py`: cross-platform staging and verified uv acquisition.

## Desktop identity and UX

- `pyproject.toml` `[project.urls]` names the fork (`Alot1z/nurb-windows`) as Repository/Issues and keeps upstream as a separate `Upstream` link, so packaging metadata and bug reports land on the fork. Merge strategy: take the fork side on `pyproject.toml` conflicts; it does not affect the uv lock.
- Windows removes macOS overlay-titlebar behavior and DMG packaging.
- Project-name validation rejects `\\` on Windows.
- About/help links point at `Alot1z/nurb-windows`.
- Windows wording uses Explorer, Recycle Bin, PowerShell, and PC where appropriate.

## Release/update security

The inherited upstream updater was removed and replaced with a fork-owned channel: the plugin now points only at `Alot1z/nurb-windows` releases (`latest.json` on the fork's releases), signed by a fork keypair whose public key is committed (`desktop/signing/tauri-updater.key.pub` -> `tauri.conf.json` `plugins.updater.pubkey`) and whose private key exists only as a CI secret plus a gitignored local copy. The Windows surface is the rail's "check for updates" button; the macOS "Check for Updates…" menu item forwards to the same flow. `.github/workflows/windows-release.yml` builds the signed installer on the `v*` tag and publishes the installer, `.sig`, and `latest.json` to the fork's release. Builds fail loudly when the signing key is absent, so an unsigned update channel cannot ship. See `docs/windows/RELEASE.md` for the secret setup.

## Windows-only Python fixes worth remembering

- `src/nurb/platform/paths.py` `home_dir()` honors `HOME` even on Windows, where `pathlib.Path.home()` only reads `USERPROFILE`. This is what makes the skill-install tests (which monkeypatch `HOME`) pass, and it is the right semantic for agents that set `HOME` to stage a skill.
- `src/nurb/cli.py` writes `viewer.cmd` with `newline=""` and `open(..., "w", newline="")` so the launcher stays exactly CRLF instead of becoming CRCRLF on Windows text-mode writes; `nurb launcher` prints the Explorer double-click path.
- The dev-server port probe uses `SO_EXCLUSIVEADDRUSE` on Windows (upstream's `SO_REUSEADDR` permits binding over a live listener there, so the "already serving" guard never fired).

## Maintenance policy

Prefer adding future Windows behavior behind platform boundaries instead of modifying upstream-core logic. Every new Windows-only deviation should be added here with a reason and merge strategy.
