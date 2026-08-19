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

## 9. Release artifact audit (was BUILD NEXT — now DONE)

- **Problem**: nothing in CI proved the published installer, `.sig`, and
  `latest.json` were what they claimed; a wrong upload shipped silently.
- **Evidence**: the v0.21.0 release was verified by hand this session, and
  the first automated check was this session's `tools/release_verify.py`.
- **Solution**: `tools/release_verify.py` downloads the actual released
  assets and verifies the minisign signature against the committed updater
  key with the same decoding semantics the app uses (base64 envelope,
  prehashed blake2b, Ed25519, global signature), plus version/url/signature
  identity and SHA-256 provenance. Run from `windows-release` after
  tauri-action attaches assets; the provenance JSON is uploaded as a
  workflow artifact. Pure-Python Ed25519 keeps it dependency-free for CI.
- **Coverage**: `tests/test_release_verify.py` (12 cases) pins the failure
  modes: tampered artifact, wrong key, key-id mismatch, malformed metadata,
  version/url drift, signature/asset disagreement, missing files,
  idempotent re-check.
- **Decision**: **BUILD NOW — DONE**; live-verified against the real
  v0.21.0 and v0.20.1 releases and cross-checked against the Rust
  `minisign-verify` crate and `cryptography`.

## 10. Release orchestration (was the manual workflow_dispatch gap)

- **Problem**: a release tag created by the publish workflow's own token
  does not re-trigger tag-push workflows, so `windows-release` never ran
  and the release shipped with no Windows artifacts until a human
  dispatched it by hand.
- **Evidence**: the v0.21.0 release had zero assets when the publish
  workflow auto-created it; this session completed it via manual dispatch.
- **Solution**: `publish.yml` now dispatches `windows-release.yml` at the
  exact tag it just created (workflow_dispatch is the one event a
  workflow-created token may trigger), with `actions: write` added to the
  publish job. One release act produces the full artifact set.
- **Decision**: **BUILD NOW — DONE**; the dispatch command was exercised
  live against v0.21.0.

## 11. ARM64 feasibility

- **Problem**: is an ARM64 (aarch64-pc-windows-msvc) build possible?
- **Evidence**: `desktop/scripts/stage.py` already names the
  `uv-aarch64-pc-windows-msvc.exe` binary in `signable_targets`, so the
  staging layer is ARM64-aware. The bundle config targets `nsis` with no
  architecture pin; tauri can target `aarch64-pc-windows-msvc` given the
  toolchain target installed. CI's windows-build pins
  `x86_64-pc-windows-msvc` only.
- **Assessment**: **FEASIBLE, DEFERRED**. The Rust toolchain, uv staging,
  and NSIS bundling all support aarch64. What is unproven is a real ARM64
  runner (windows-build runs on windows-latest x64) and a native WebView2
  ARM64 test. The updater's latest.json already carries a
  `windows-aarch64` platform entry, so the metadata side is ready.
- **Decision**: **DEFER** until a native ARM64 test device exists; the
  pipeline changes needed are mechanical (add the rust target, one
  platform entry in the release job).

## 12. Authenticode integration readiness

- **Problem**: the installer has no Authenticode (SmartScreen) signature;
  users see an unknown-publisher warning.
- **Evidence**: `stage.py::check_authenticode_signing` is fully
  implemented and env-gated: `NURB_WINDOWS_AUTHENTICODE_REQUIRED=1` forces
  signing via `signtool.exe` with `NURB_WINDOWS_AUTHENTICODE_PFX` and an
  optional timestamp URL (default DigiCert). The repo never stores cert
  material. windows-build does not set the env vars, so today it is a
  no-op print.
- **Assessment**: **EXTERNAL, integration-ready**. The code path exists
  and fails loud if asked to sign without material; what is missing is the
  certificate (a purchased code-signing cert or an org CA), which no repo
  change can provide. When the cert exists, setting the three env vars in
  the windows-release workflow is the entire integration.
- **Decision**: **EXTERNAL** (certificate); **integration-ready** once
  the cert exists.

## 13. Windows torture/regression — spaced & Unicode install paths

- **Problem**: the mission names Windows-specific torture cases as required;
  unproven was whether the real installer and app survive an install path
  with spaces and non-ASCII characters.
- **Evidence** (live, this session, against the released v0.21.0 installer):
  silent install into `E:\space agent test\Nürb 测试\` succeeded; the app
  launched from that path (main + WebView2 processes, backend HTTP 200 on
  the pinned port); and the updater endpoint resolved from that install —
  with the check-cache marker deleted, the v0.20.1 app launched from a
  spaced/Unicode path wrote a fresh marker naming `0.21.0`, proving its own
  updater fetched and parsed the live latest.json. `tools/release_verify.py`
  verified the release from a spaced/Unicode scratch dir, and
  `desktop/scripts/stage.py` passes paths as list args (never through a
  shell), so staging/signing are safe there too.
- **Regression test**: `test_spaced_and_unicode_paths_still_verify` builds
  the fixture under `space agent test/Nürb 测试/` and runs the verifier as a
  subprocess, pinning the no-shell property.
- **Decision**: **VERIFIED COMPLETE**; one small regression test added.

## 14. Fresh install from a clean user profile

- **Problem**: does first-run provisioning actually complete on a machine
  that has never run the app?
- **Evidence** (live, this session): deleted the app's `%APPDATA%` and
  `%LOCALAPPDATA%` directories, installed v0.21.0 fresh, launched it.
  Provisioning completed from scratch: `provisioned.json` written with all
  required fields (wheel lock, node v24.19.0, both adapter pins, adapter
  lock), ~35k provisioned files across env/python/node/adapters, app process
  running and responding with WebView2 up. The backend dev server spawns per
  project by design (Supervisor), so a fresh profile with no open project
  has no listener until one is opened; that is architecture, not a gap.
- **Decision**: **VERIFIED COMPLETE** (provisioning); backend-on-demand
  confirmed by design.

## 15. NSIS repair mode

- **Problem**: can a broken install be repaired through the installer, or
  does Windows offer Modify/Repair?
- **Evidence** (live, this session): the installed app's uninstall registry
  key reports `NoModify: 1` and `NoRepair: 1` with no `ModifyPath` or
  `RepairString`, so Windows shows no Repair/Modify entry. The tauri NSIS
  template defines no repair page. The equivalent recovery path that does
  exist is reinstall-in-place: running the v0.21.0 installer over an
  existing install replaces the files and preserves user data (proven in
  the updater-lifecycle test, v0.20.1 -> v0.21.0 in place).
- **Decision**: **N-A** (repair mode does not exist in NSIS installers;
  reinstall-in-place is the supported recovery path, documented here so a
  future session does not search for a repair button).
