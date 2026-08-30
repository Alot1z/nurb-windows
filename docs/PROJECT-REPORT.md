# nurb-windows: Comprehensive Project Report

> Generated: 2026-08-22 | Branch: main (cde6d50) | Release gate: READY (8/8)

## Executive Summary

nurb is an agentic CAD tool for 3D printing. Parts are Python functions; a
long-lived process rebuilds them on save and pushes geometry to a browser viewer.
Built on build123d (OCCT), so parts are real B-rep solids.

| Dimension | Count |
|-----------|-------|
| Python source files | 29 (src/nurb/*.py + src/nurb/plugins/*.py) |
| Python source lines | 10,778 |
| Python defs/classes | 402 |
| Python test files | 29 |
| Python test lines | 6,963 |
| Python test functions | 586 |
| Rust source files | 14 |
| Rust source lines | 5,903 |
| Rust defs | 259 |
| Rust tests | 47 |
| TypeScript/TSX files | 20 |
| TypeScript defs | 380 |
| JS tests | 9 |
| CI workflows | 3 (publish, test, windows-build) |

**All CI workflows: PASSED.** Release gate: READY (8/8 checks).

---

## 1. Python Core Engine (src/nurb/)

### Source File Inventory

| Module | Lines | Defs | Test File | Tests | Est. Coverage |
|--------|-------|------|-----------|-------|---------------|
| **checks.py** | 1,683 | 62 | test_rules + 3 others | 93 | ~85% |
| **cli.py** | 1,537 | 46 | test_cli | 54 | ~80% |
| **server.py** | 1,417 | 39 | test_server | 67 | ~85% |
| **slicing.py** | 580 | 27 | test_slicing | 38 | ~70% |
| **assembly.py** | 488 | 23 | test_assembly | 16 | ~60% |
| **mcp.py** | 425 | 11 | test_mcp | 12 | ~65% |
| **builder.py** | 383 | 18 | indirect | ~8 | ~55% |
| **stress.py** | 370 | 16 | test_stress | 9 | ~65% |
| **crown.py** | 360 | 11 | test_crown | 13 | ~70% |
| **scan.py** | 321 | 9 | test_scan | 19 | ~80% |
| **edit.py** | 273 | 14 | test_edit | 23 | ~75% |
| **card.py** | 254 | 11 | test_card | 33 | ~80% |
| **render.py** | 214 | 6 | test_render | 5 | ~40% |
| **probe.py** | 199 | 7 | test_probe | 8 | ~60% |
| **mesh.py** | 174 | 4 | test_mesh | 19 | ~85% |
| **compare.py** | 166 | 9 | test_compare | 10 | ~70% |
| **orient.py** | 160 | 4 | test_orient | 7 | ~50% |
| **polish.py** | 152 | 8 | test_chamfer_errors | 9 | ~60% |
| **extract.py** | 151 | 7 | test_extract | 8 | ~65% |
| **measurements.py** | 125 | 7 | test_measurements | 11 | ~75% |
| **registry.py** | 101 | 7 | test_params | 21 | ~80% |
| **api.py** | 123 | 8 | test_api | 9 | ~80% |
| **holes.py** | 60 | 1 | test_holes | 6 | ~90% |
| **__init__.py** | 84 | 1 | implicit | - | - |

**Overall Python estimated coverage: ~72%** (weighted by lines)

---

## 2. Plugin System (src/nurb/plugins/)

| Module | Lines | Defs | Tests | Notes |
|--------|-------|------|-------|-------|
| registry.py | 233 | 24 | test_plugins.py (53) | All operations tested |
| loader.py | 290 | 8 | test_plugins.py | Discovery, import, disabled |
| manifest.py | 208 | 9 | test_plugins.py | TOML parsing, compat |
| scaffold.py | 70 | 2 | test_plugins.py | Template substitution |
| state.py | 64 | 3 | test_plugins.py | Enable/disable persistence |
| __init__.py | 36 | 0 | - | Package init |

**14/14 plugin functions fully tested.** All lifecycle operations covered.

---

## 3. Desktop App (desktop/)

### Rust Backend

| Module | Lines | Defs | Notes |
|--------|-------|------|-------|
| acp.rs | 1,160 | 24 | Agent Control Protocol |
| provision.rs | 1,065 | 45 | Project provisioning |
| lib.rs | 705 | 25 | Tauri commands (tested) |
| agents.rs | 535 | 26 | Agent management |
| supervisor.rs | 380 | 21 | Process supervision |
| extensions.rs | 364 | 24 | Extension registry (empty) |
| env.rs | 379 | 29 | Environment detection (tested) |
| terminal.rs | 409 | 23 | Terminal emulation |
| plugins.rs | 127 | 5 | Plugin toggle (tested) |
| prefs.rs | 270 | 15 | Preferences |
| registry.rs | 189 | 12 | Part registry (tested) |
| sessions.rs | 175 | 9 | Session management |
| process.rs | 72 | 0 | Process utils |
| main.rs | 6 | 1 | Entry point |

**47 Rust tests.** tsc --noEmit clean. npm test 9/9.

### TypeScript Frontend

| File | Lines | Defs | Notes |
|------|-------|------|-------|
| App.tsx | 1,502 | 161 | Main shell, state, postMessage |
| Chat.tsx | 923 | 87 | Chat panel, markdown |
| Settings.tsx | 195 | 14 | Plugin toggles, printer config |
| TerminalPanel.tsx | 134 | 15 | Terminal integration |
| Markdown.tsx | 118 | 18 | Markdown rendering |
| Icons.tsx | 138 | 10 | SVG icons |
| About.tsx | 129 | 7 | About dialog |
| Setup.tsx | 119 | 11 | First-run setup |
| ExtensionsModal.tsx | 108 | 3 | Extensions modal |
| GeminiKeyDialog.tsx | 86 | 5 | API key dialog |
| AgentsHelp.tsx | 70 | 5 | Agent help |
| Logo.tsx | 29 | 1 | Logo |
| main.tsx | 9 | 0 | Entry point |
| + 7 utility .ts files | 271 | 51 | Types, layouts, sounds |

**No React component unit tests.** JS tests cover utility functions only.

---

## 4. CI/CD Pipeline

| Workflow | Status | Duration |
|----------|--------|----------|
| publish | PASSED | ~2min |
| test | PASSED | ~6min |
| windows-build | PASSED | ~18min |

Release gate: READY (8/8 checks)

---

## 5. Coverage Gaps

| Gap | Severity | Impact |
|-----|----------|--------|
| render.py (40%) | Medium | Headless render hard to test locally |
| orient.py (50%) | Low | Print stance is visual, hard to assert |
| builder.py (55%) | Medium | Indirect testing only |
| All TSX (0%) | High | No React component tests |
| acp.rs (0%) | Medium | Agent Control Protocol untested |
| provision.rs (0%) | Low | Provisioning is integration-heavy |

---

## 6. Architecture

nurb-windows/
  src/nurb/              # Python engine (10,778 lines)
    __init__.py          # Public API (@part, build, polish, etc.)
    builder.py           # Part loading, tessellation, GLB
    checks.py            # Printability rules (62 functions)
    cli.py               # CLI surface (46 commands)
    server.py            # HTTP+websocket (39 handlers)
    plugins/             # Plugin system (6 modules)
  tests/                 # Python tests (6,963 lines, 586 functions)
  desktop/               # Tauri desktop app
    src-tauri/src/       # Rust backend (5,903 lines, 47 tests)
    src/                 # React frontend (380 defs, 9 JS tests)
  plugins/               # Shipped plugin examples
  examples/              # Example parts (also tests)
  evals/                 # Model leaderboard
  tools/                 # Build/release tooling

---

*Report from static analysis + test execution, 2026-08-22.*
*Coverage estimates based on test-to-module mapping, not line-level instrumentation.*