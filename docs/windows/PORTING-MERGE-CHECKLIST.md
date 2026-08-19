# Porting merge checklist

A repeatable reconciliation workflow for merging upstream nurb into the Windows port.
Grounded in the v0.21.0 merge (August 2026) so each row is a real decision, not a template.
Run the strict gate first; it tells you which paths actually drifted.

```
python tools/upstream_sync.py status --strict
python tools/release_gate.py
```

## The decision rule

For every path the gate flags, classify one of:

- **PORT** — adopt upstream unchanged (the fork had nothing to preserve).
- **ADAPT** — take upstream's structure, keep the fork's Windows behavior inside it.
- **KEEP** — fork content wins; upstream's change is not applicable to a Windows port.
- **REWRITE** — neither side is right after the merge; write it fresh.
- **DROP** — reject the upstream change deliberately (obsolete workaround).
- **DEFER** — needs a human decision or a separate change.

Preserve `src/nurb/platform/` (fork-additive), the Windows adaptations in
`cli.py`/`server.py`/`mcp.py`/`viewer.html`, the strict upstream-sync gate, the
release gate, and the fork's tests. A textual merge is not a resolution: check
callers, tests, dependencies, and platform effect before choosing.

## v0.21.0 conflict map (worked example)

The merge of upstream `d8164e6` produced these resolutions. Use the columns as the
shape for the next merge.

| Path | Upstream change | Fork change | Windows impact | Decision |
|---|---|---|---|---|
| `src/nurb/slicing.py` | print settings embedded in exported 3MFs (#150) | Windows paths / slicer handoff | Slicer profile lookup and per-user config paths | ADAPT: upstream feature, fork path layer kept |
| `src/nurb/viewer.html` | viewer edits | Z-up camera persistence, section, sliders | None (browser) | ADAPT: merged both edit sets |
| `src/nurb/cli.py` | command surface changes | `platform` layer, `%APPDATA%` config | Shell launcher, macOS-only branches | ADAPT + KEEP Windows branches |
| `src/nurb/server.py` | watcher/server changes | Windows process routing | Port picking, browser open | ADAPT |
| `src/nurb/checks.py`, `doctrine.md` | rule updates | none | none | PORT |
| `tests/test_assembly.py` | new tests | Windows-skip decorators | Some upstream tests assume POSIX | ADAPT: skip + fork equivalent |
| `tests/test_cli.py` | new tests | `os.name` checks | `os` import dropped by merge | ADAPT: restored import |
| `tests/test_server.py`, `test_slicing.py` | new tests | Windows adaptations | see above | ADAPT |
| `pyproject.toml`, `uv.lock`, `evals/uv.lock` | version 0.21.0 | fork versioning | none | PORT (bump fork to match) |
| `desktop/src-tauri/Cargo.toml` | plugin set changed | fork adds clipboard-manager, minisign-verify | tauri CLI rewrites this file at build | KEEP fork set; see line endings below |
| `desktop/.gitignore` | upstream additions | fork additions | none | PORT + KEEP fork entries |
| `.github/workflows/publish.yml`, `site/*`, `CONTRIBUTING.md` | new upstream files | none | none | PORT |
| `skills/nurb/SKILL.md`, `src/nurb/skill.md`, `src/nurb/agents.md` | wording drift | fork shim contract ("3MF into build/") | none | ADAPT: restored fork wording in all three |

## Traps that cost real CI cycles (from v0.21.0)

1. **The tauri CLI rewrites `desktop/src-tauri/Cargo.toml` on every build.**
   `rewrite_manifest` re-serializes the manifest to LF. CI checks out with
   `core.autocrlf=true`, so the worktree is CRLF and the rewrite counts as a
   modification, tripping the release gate's `clean-tree` check. Fix: `.gitattributes`
   pins `*.toml text eol=lf`. Symptom: gate reports `M desktop/src-tauri/Cargo.toml`
   only on the Windows runner, never locally (local clones use `autocrlf=false`).

2. **Post-merge test patches can drop imports.** Adding `os.name` to a module-level
   `skipif` decorator without `import os` fails at collection with a `NameError`,
   which is a test-suite failure, not a test failure. Run `pytest --collect-only`
   after any merge before running the suite.

3. **`agents.md` is a contract, not prose.** `test_the_shim_promises_what_export_actually_writes`
   asserts literal strings in `src/nurb/agents.md`, and the trigger test
   (`test_the_skill_is_the_shim_with_a_trigger_on_top`) enforces `skill.md` and
   `skills/nurb/SKILL.md` are one body ending in `agents.md`. Changing one without
   the other two breaks CI.

## Verification order (do not skip)

1. Workflows parse: `python -c "import yaml; yaml.safe_load(open('.github/workflows/windows-build.yml'))"` and same for `upstream-sync.yml`.
2. `python tools/upstream_sync.py status --strict` — must exit 0 (no SAFE-zone drift).
3. `python tools/release_gate.py` — must read `release-gate: READY`.
4. `uv run --project . pytest tests/ --collect-only` — no collection errors.
5. `uv run --project . pytest tests/` — full suite green.
6. Push, then monitor both workflows on the PR to completion; do not merge while any required check is red.

## The next merge, in one pass

```bash
git fetch upstream main
git merge --no-commit --no-ff upstream/main        # enumerate conflicts
python tools/upstream_sync.py status --strict      # classify before resolving
# resolve per the decision rule, then:
git merge --continue
python tools/upstream_sync.py status --strict      # must exit 0
python tools/release_gate.py                       # must be READY
uv run --project . pytest tests/ --collect-only    # no collection errors
uv run --project . pytest tests/                   # full suite
```

Document each resolved path above before finishing. The strict gate only tells you
what drifted; the table is where the reasoning lives.
