# Changelog

All notable changes to **nurb-windows port** are recorded here, in reverse
chronological order. The format follows [Keep a Changelog](https://keepachangelog.com);
this file is the single source of truth and is regenerated from git on every
release — hand edits here are authoritative between regeneration runs.

The upstream project's changelog lives at
[nurb.dev/changelog](https://nurb.dev/changelog) and is referenced verbatim
for upstream-only entries below. Where the fork diverges, the change is
marked **WINDOWS ADAPTATION**; where the fork adds entirely new capability,
it is marked **FORK FEATURE**.

## Versioning scheme

`MAJOR.MINOR.PATCH` carries the upstream scheme. Fork-only additions roll into
the PATCH position and bump the local patch counter separately in `desktop/
src-tauri/tauri.conf.json`. Tags are `vX.Y.Z` on `main`.

---

## Unreleased

### Added

- **Brand mark `assets/logo.png`** (`assets/render_logo.py`, `parts/logo.py`):
  procedurally generated NURB ribbon under the *Anodized Fillet* philosophy
  (`assets/DESIGN-PHILOSOPHY.md`). The PNG is the commit artifact; the
  geometry behind it is a real `@part` that builds through OCCT, so the
  brand mark provably derives from the kernel the user's parts ship through.
  README hero block now references the image at width `780`, the same visual
  footprint as the prior ASCII mark.

- **Strict upstream-sync gate** (`10ca148`,
  `tools/upstream_sync.py`, `tests/test_upstream_sync.py`,
  `.github/workflows/windows-build.yml`): the `status` subcommand now
  accepts `--strict`, which exits non-zero when SAFE-zone drift is present
  against an upstream that the fork is behind or diverged with. Wired into
  `windows-build.yml`. Pure decision logic extracted into
  `safe_drift_paths(sync_state)` and `strict_should_fail(safe_count,
  relative)` so it is unit-testable without touching the network.

- **Release-gate script** (`6d3ab5b`, `tools/release_gate.py`): single Python
  entry point with eight invariants:
  `clean-tree`, `private-key-ignored`, `private-space-untracked`,
  `updater-pin`, `updater-pubkey`, `stage-script`, `self`, `toolchain`.
  Exit code is the failure count; final line printed is `release-gate:
  READY` (all green) or `release-gate: N FAILURE(S)`.

- **Authenticode signing pipeline** (`6d3ab5b`, `desktop/scripts/stage.py`):
  `signable_targets()` enumerates the per-target produced artifacts;
  `check_authenticode_signing()` invokes `signtool` when
  `NURB_WINDOWS_AUTHENTICODE_REQUIRED=1`. No certificate material is ever
  in the repo; the cert lives in the `.env.signing` file at `desktop/
  signing/`, which `.gitignore` excludes. Loud failure under the required
  mode if cert or signtool are missing; silent no-op otherwise.

- **Belt-and-braces local pre-commit hook** (`1d079d9`, `.githooks/
  pre-commit`): scans staged diffs for the same banned-phrase list that
  the release-gate enforces at release time. Currently configured but the
  core policy work happens at release-time via the gate; the hook is the
  developer's local safety net.

- **CI hardening for shallow checkouts** (`240b736`,
  `tests/test_upstream_sync.py`): the two live-CLI integration tests in
  the new gate are now skipped when CI checkout uses the default shallow
  `fetch-depth: 0` (the `test` workflow); the `windows-build.yml` workflow
  uses `fetch-depth: 0` explicitly and continues to exercise the full
  integration path.

### Fixed

- **CI failure on shallow checkouts** (`240b736`): the live-CLI tests in
  `tests/test_upstream_sync.py` invoked `git merge-base HEAD upstream/main`,
  which fails on shallow fetches because git cannot walk a common ancestor.
  The fix flags those two tests with `pytest.mark.skipif` driven by an env
  marker, so the unit tests pass everywhere even though the
  integration coverage only fires against full-history checkouts.

### Documentation

- New `assets/DESIGN-PHILOSOPHY.md` codifies the brand mark's visual
  language so future regenerations stay inside the same line.
- New `docs/windows/WINDOWS-PATCHES.md` patch register gains three
  sections under their own headings (`Release-gate script`, `Authenticode
  signing pipelined, certificate EXTERNAL`, `Loadable user extensions`)
  so a future `tools/upstream_sync.py status` reviewer sees the additions
  in one place.

---

## v0.20.1 (fork baseline pinned to upstream v0.20.1)

The fork-branched baseline. Pre-existing fork work — substantial, fork-only,
additive — all of which is preserved under the following headings.

### Fork features (added on top of upstream v0.20.x)

**Product surface**

- **Tauri desktop shell** (`desktop/src-tauri/`): per-user-per-app window,
  shipped as `nurb_<version>_x64-setup.exe` (NSIS, no admin rights).
  First launch provisions Python, OCCT (cp313 wheels), the Node adapter
  runtime, and the `nurb` wheel into `%APPDATA%\nurb\`. Updates itself
  from this fork's own release channel.
- **Belt-and-braces local hooks** (`.githooks/`) for the banned-phrase list.
- **PowerShell helpers** (`desktop/scripts/`, `*.ps1`).

**Engine layer**

- **Windows process model** (`desktop/src-tauri/src/process.rs`): central
  child-process ownership and tree termination. Used by `acp.rs`,
  `agents.rs`, `provision.rs`, `supervisor.rs`.
- **Stage script** (`desktop/scripts/stage.py`): builds the per-target
  resources tree — wheel, requirements lock, Node adapter runtime —
  before the Tauri build runs.

**Engine layer (capabilities the prototype advertised)**

- **Extension registry** (`desktop/src-tauri/src/extensions.rs`): generic,
  host-kind-driven registry. Manifest validation lives next to the data
  it guards. Hosts currently implemented: `terminal` (ConPTY session),
  `externalApp` (detached child), `acp` (existing).
- **MCP bridge** (`:mcp-bridge` socket, discoverable by the app).
- **i18n scaffolding** (`desktop/src/i18n/`, English baseline).

**Distribution**

- **Updater keypair** (`desktop/signing/tauri-updater.key.pub`): pinning
  the updater channel to this fork. Private key + password are
  gitignored; the public half is the only tracked piece.
- **NSIS installer**: per-user, signed, supports headless install via
  `/S` for CI smoke tests.

**Workflows**

- **`windows-build.yml`**: build + smoke + portable artifact + signed
  updater pinned to the fork, all on Windows runners.
- **`test.yml`**: only-runner-on-non-Windows workflows (evals, sanctuary
  test) plus portable Python unit tests.
- **Scheduled `upstream-sync.yml`**: every six hours, attempts an
  automatic merge and opens an issue on conflict.

### Upstream parity (all present, with fork tagging)

- Viewer (`src/nurb/viewer.html`): three.js r169, vendored, offline.
- B-rep kernels (build123d → OCP → OCCT 7.x).
- Print readiness rule pack (`src/nurb/checks.py`): the full v0.20 set
  preserved.
- 3MF / STEP / STL / GLB exporters.
- `nurb skill`, `nurb rules`, `nurb api`, `nurb check`, `nurb inspect`,
  `nurb build`, `nurb new`, `nurb diff`, `nurb update`, `nurb verify`.
- Tauri shell integrity model, process tree, MCP discovery.

### Windows adaptations of upstream behavior

- `src/nurb/platform/**`: central Windows paths, executable naming,
  subprocess helpers, registry-of-files abstraction.
- `src/nurb/checks.py`: paths resolved through the platform module.
- `src/nurb/cli.py`: Windows-specific launcher (`launcher.cmd` →
  `viewer.cmd`), socket probing, code-page tolerance.
- `src/nurb/slicing.py`: Windows slicer discovery (OrcaSlicer,
  BambuStudio under `%LOCALAPPDATA%\Programs\`).
- `src/nurb/server.py`: latest-version cache lives in the platform cache
  directory; no XDG on Windows.
- Viewer paths: `%APPDATA%\nurb\config.toml` is the user config location.

### Known external gaps (not in this fork, blocked by outside)

- **Authenticode code-signing certificate**: external; pipeline is
  ready, the only missing piece is the actual EV or OV cert from a
  CA. `desktop/scripts/stage.py` runs the hook; does not fabricate the
  cert.
- **Native ARM64 OCCT/OCP build chain**: depends on upstream
  releasing win-arm64 wheels; tracked as **EXTERNAL**.
- **Apple sandbox equivalent on Windows**: AC/AppContainer is not
  macOS Seatbelt; the limitation is acknowledged in code.

---

## Upstream drift — what v0.21.0 contains that the fork lacks

As of this checkout (`HEAD`):

- `upstream/main` is **129 commits ahead** of `origin/main` (which is the
  fork's published main).
- `tools/upstream_sync.py status` classifies the drift across three
  buckets: **SAFE** (cherry-pick candidates, 22 paths today),
  **REVIEW** (likely conflicts, 0) and **WINDOWS-SPECIFIC** (fork files
  the upstream does not know about, the bulk of the 81 paths).
- The strict gate now fails any push that creates new SAFE drift while
  the fork is behind (the `10ca148` change). Resolving the gate is the
  upstream merge of v0.21.0 — tracked as a dedicated session and not
  shortcut in this changelog.

See `docs/windows/PORTING.md` for the merge protocol and
`docs/windows/UPSTREAM-SYNC.md` for the strict-gate semantics.

---

## How this file is built

Until a generator script lands, this file is hand-edited and the
release-gate validates that:

- the three version files (`pyproject.toml`, `src/nurb/skill.md`,
  `skills/nurb/SKILL.md`) carry the same `version` line in lockstep.
- the changelog files referenced from `site/changelog.html` are kept
  in the package.

The `release-gate.py` `clean-tree`, `updater-pin`, and `updater-pubkey`
checks all read this file's editable region to anchor their verdicts.
