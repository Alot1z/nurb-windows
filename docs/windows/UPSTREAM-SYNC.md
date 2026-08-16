# Upstream synchronization

Remotes:

- origin: https://github.com/Alot1z/nurb-windows
- upstream: https://github.com/Shpigford/nurb

Use:

`powershell
python tools/upstream_sync.py status
python tools/upstream_sync.py prepare
`

The sync tool classifies changed paths:

- **SAFE:** upstream core, tests, examples, evals, skills.
- **REVIEW:** shared desktop/frontend or packaging metadata.
- **WINDOWS-SPECIFIC:** Tauri configuration, Windows scripts, and Windows CI.

The goal is to keep the Windows-specific patch surface small so routine upstream updates merge cleanly.
