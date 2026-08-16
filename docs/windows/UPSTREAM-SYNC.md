# Upstream synchronization

Remotes:

- origin: https://github.com/Alot1z/nurb-windows
- upstream: https://github.com/Shpigford/nurb

Use:

```
python tools/upstream_sync.py status
python tools/upstream_sync.py prepare
```

The sync tool classifies changed paths:

- **SAFE:** upstream core, tests, examples, evals, skills.
- **REVIEW:** shared desktop/frontend or packaging metadata.
- **WINDOWS-SPECIFIC:** Tauri configuration, Windows scripts, and Windows CI.

The goal is to keep the Windows-specific patch surface small so routine upstream updates merge cleanly.

## What a merge actually does (measured)

A sync simulation that cherry-picked a change touching `src/nurb/cli.py`,
`src/nurb/server.py`, `src/nurb/slicing.py`, `pyproject.toml`,
`desktop/src-tauri/tauri.conf.json`, and `desktop/src/About.tsx` onto real
upstream history behaved like this:

- **Merged cleanly:** `src/nurb/cli.py`, `src/nurb/server.py`,
  `pyproject.toml` (changes landed in regions the fork did not touch).
- **Conflicted, fork side wins:** `src/nurb/slicing.py` (the fork's
  `_windows_install_roots` sits where upstream added a comment),
  `desktop/src-tauri/tauri.conf.json` (fork changed the window block and
  rewrote the updater block), and `desktop/src/About.tsx` (fork replaced
  upstream's repo links with the fork's).

So conflicts concentrate exactly where the fork deviates on purpose, which is
the point of the patch register. But note the one failure mode that did not
self-report: resolving the `tauri.conf.json` conflict once kept upstream's
`plugins.updater.endpoints` value, which would have pointed every installed app
at `Shpigford/nurb` releases. `tests/test_cli.py::test_the_updater_never_points_at_upstream_nurb`
now fails that configuration, and also requires the embedded pubkey to equal
`desktop/signing/tauri-updater.key.pub`.

## Post-merge checklist

1. `uv run pytest -q -n auto` (includes the updater-endpoint guard).
2. `cd desktop/src-tauri && cargo test` (includes the pubkey-parse test).
3. Grep resolved files for leftover `<<<<<<<` / `>>>>>>>` markers.
4. Confirm `desktop/src/About.tsx` and `src/nurb/cli.py` still name the fork's
   repository and the Windows launcher, not upstream's.
5. If `pyproject.toml` moved: bump `tauri.conf.json` + `Cargo.toml` to match or
   the version-agreement test fails by design.
