# Enhancement ledger

Autonomous enhancement discovery for the nurb-windows fork. Every row names
the problem it solves, the evidence it rests on, the layer it belongs in,
and a decision. Nothing here is built speculatively: the ledger exists so a
future session can check a candidate against the fork's actual state instead
of re-deriving it.

Decision keys: **BUILD NOW** (clear value, low cost, no dependencies),
**BUILD NEXT** (value, but needs a release or a decision first),
**DEFER** (value, but the trigger is an external event), **DO NOT BUILD**
(already covered, or cost exceeds value).

## 1. Deterministic project state snapshot

- **Problem**: every session re-derives the same ground truth (HEAD,
  upstream HEAD, merge base, gate state, PR state) from git and gh.
- **Evidence**: this session's first act was exactly that forensics; the
  `tools/` directory has no single command that prints it.
- **Solution**: a `tools/state.py status` that prints fork HEAD, upstream
  HEAD, merge base, ahead/behind, strict-gate verdict, release-gate verdict,
  and open PR state in one pass. Machine-readable JSON behind a `--json`
  flag.
- **Layer**: deterministic script (no model).
- **Complexity**: low (~60 lines, all subprocess calls already proven).
- **Decision**: **BUILD NEXT**. The ground truth is already cheap to
  assemble; the value is a canonical one-liner. It must be explicitly
  non-authoritative (docs + a timestamp), so it never becomes a stale cache
  that gates decisions.

## 2. Changed-file → affected-test mapping

- **Problem**: a merge touching `src/nurb/slicing.py` plus three test files
  made CI run the whole 573-test suite; the failures were collection errors
  that a targeted run would have caught first.
- **Evidence**: the v0.21.0 merge's collection `NameError` failed the full
  job; `pytest --collect-only` on changed modules would have caught it in
  seconds.
- **Solution**: a `tools/impact.py <path>...` that maps changed paths to the
  test modules that import them (via `tests/test_*.py` imports), printing a
  targeted pytest command, with "or run the full suite" as the escalation.
- **Layer**: deterministic script.
- **Complexity**: low-moderate (import graph is shallow in this repo).
- **Decision**: **BUILD NEXT**. It shortens the loop after every merge,
  which is the fork's recurring cost center.

## 3. Release automation pipeline (build → hash → inspect → smoke)

- **Problem**: releases require the signed installer, a `.sig`, and
  `latest.json`; RELEASE.md documents the steps but nothing validates the
  artifact set before the tag is cut.
- **Evidence**: `windows-build.yml` already validates the installer artifact
  (exists, >1MB, has a `.sig`); the release path has no equivalent
  pre-tag gate.
- **Solution**: extend the release gate (or a `tools/release_audit.py`) to
  check, against the tag being cut: installer exists, `.sig` parses for the
  committed pubkey, `latest.json` version matches the tag, and the
  embedded pubkey matches the committed one.
- **Layer**: CI + deterministic script.
- **Complexity**: moderate.
- **Decision**: **BUILD NEXT**, only when the first release is actually
  being cut. Until then it is a spec for a gate nothing exercises.

## 4. Windows torture / regression suite

- **Problem**: ordinary unit tests run on paths like `tmp_path` and never
  exercise `%APPDATA%`, spaces-in-paths, Unicode names, ConPTY, or process
  trees.
- **Evidence**: `docs/windows/PORTING.md` documents Windows path and process
  rules precisely because the port keeps finding these failures.
- **Solution**: a `tests/windows/` module of parametrized cases (spaces,
  Unicode, long paths) against the platform layer, plus a process-tree kill
  test through `process.rs`.
- **Layer**: tests + CI.
- **Complexity**: moderate; the platform layer already isolates the seams to
  test.
- **Decision**: **BUILD NEXT** (two or three cases only, not a suite-for-its-
  own-sake; the platform layer is the boundary worth hammering).

## 5. Machine-readable project knowledge

- **Problem**: architecture, invariants, and porting rules live in prose
  docs; an agent re-reads them per session.
- **Evidence**: `docs/windows/ARCHITECTURE.md` is accurate and current;
  duplicating it into JSON would create a second source to drift.
- **Solution**: none needed.
- **Decision**: **DO NOT BUILD**. The docs are the single source; the
  enhancement ledger and AGENT-WORKFLOWS.md point agents at them. A registry
  file would be a second copy with a sync burden.

## 6. CI intelligence (actionable failure summaries)

- **Problem**: when windows-build fails, the failed step name is visible but
  the reason needs log digging.
- **Evidence**: this session pulled logs from three failed runs to learn the
  cause; the release gate and sync audit already print one-line verdicts.
- **Solution**: make every gate-style step end with a `::error::` summary
  line (the release gate already does this via exit codes; the sync audit
  prints the drift count).
- **Layer**: CI.
- **Complexity**: trivial.
- **Decision**: **BUILD NOW** (tiny, and the merge proved the pain). The
  upstream-sync step already prints `strict: N path(s) drift`; ensure every
  step in windows-build that can fail prints a one-line actionable summary
  as its last output.

## 7. Scheduled-sync conflict tracking (issues vs PRs)

- **Problem**: the scheduled sync's conflict path calls `gh issue create`,
  but the fork repo has issues disabled, so a conflict would fail at that
  step with a gh error instead of producing a tracker.
- **Evidence**: `gh repo view` reports `hasIssuesEnabled: false`; the
  workflow already carries the fallback PR logic after this session's fix.
- **Solution**: already implemented this session (fallback to the
  persistent `upstream-sync/conflict-tracker` PR).
- **Decision**: **BUILD NOW — DONE**, verified by YAML parse + pwsh syntax
  check + local tracker-mechanics simulation.

## 8. Upstream-parity agent skill / subagent

- **Problem**: a merge session re-learns the protocol each time.
- **Evidence**: `docs/windows/PORTING-MERGE-CHECKLIST.md` now records the
  v0.21.0 decisions and traps; the personal subagent is described in
  AGENT-WORKFLOWS.md.
- **Solution**: a personal `upstream-port` subagent (per-harness, not repo
  content) reading the checklist.
- **Decision**: **DO NOT BUILD into the repo** (it is a personal harness
  file, and the checklist doc already carries the procedure).

## Summary

| Item | Decision |
|---|---|
| State snapshot (`tools/state.py`) | BUILD NEXT |
| Changed-file → affected tests (`tools/impact.py`) | BUILD NEXT |
| Release artifact audit | BUILD NEXT (at first release) |
| Windows torture tests (2-3 cases) | BUILD NEXT |
| Machine-readable project knowledge | DO NOT BUILD |
| CI actionable summaries | BUILD NOW (this session: upstream-sync fix) |
| Scheduled-sync conflict tracking | BUILD NOW — DONE |
| Upstream-parity subagent | DO NOT BUILD into repo |
