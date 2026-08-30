# nurb-windows: Implementation Plan

> Generated: 2026-08-22 | Based on comprehensive project report

## Current State

| Surface | Status |
|---------|--------|
| Python tests | 586 pass, 8 skip |
| Rust tests | 47 pass |
| TypeScript | tsc clean |
| JS tests | 9 pass |
| CI (all 3 workflows) | PASSED |
| Release gate | READY (8/8) |
| Estimated line coverage | ~72% |

## Priority 1: Coverage Gaps (High Impact)

### 1.1 React Component Tests

- **Problem:** 0 unit tests for 380 TSX definitions across 13 components
- **Impact:** High. UI regressions are caught only by manual testing.
- **Approach:** Add Vitest + React Testing Library. Start with App.tsx,
  Settings.tsx, Chat.tsx (the three largest components).
- **Effort:** 2-3 days
- **Files:** desktop/src/*.test.tsx (new), desktop/vitest.config.ts (new)

### 1.2 builder.py Direct Tests

- **Problem:** 55% coverage, tested only indirectly through render and CLI
- **Impact:** Medium. Core build pipeline is the foundation of everything.
- **Approach:** Add test_builder.py with tests for load(), build(),
  tessellate(), to_mesh(), to_glb(), write_stl(), write_3mf().
- **Effort:** 1 day
- **Files:** tests/test_builder.py (new)

### 1.3 render.py Tests

- **Problem:** 40% coverage, 5 tests for 6 functions
- **Impact:** Medium. Headless render is used by CI and the agent.
- **Approach:** Mock Playwright for unit tests. Test free_port(),
  _host(), _view() logic. Integration test needs Playwright installed.
- **Effort:** 1 day
- **Files:** tests/test_render.py (extend)

## Priority 2: Desktop Test Coverage

### 2.1 Rust Integration Tests

- **Problem:** acp.rs (1160 lines), provision.rs (1065 lines), agents.rs
  (535 lines), supervisor.rs (380 lines) have 0 tests
- **Impact:** Medium. These are core desktop backend modules.
- **Approach:** Add #[cfg(test)] modules with mock I/O. Test acp message
  routing, provision path resolution, agent lifecycle states.
- **Effort:** 3-4 days
- **Files:** desktop/src-tauri/src/acp.rs, provision.rs, agents.rs

### 2.2 Supervisor Process Management

- **Problem:** 0 tests for restart logic, PID tracking, crash recovery
- **Impact:** High. Supervisor is the reliability backbone.
- **Approach:** Mock process spawning. Test restart-on-crash, PID reuse
  detection, graceful shutdown sequences.
- **Effort:** 2 days
- **Files:** desktop/src-tauri/src/supervisor.rs

## Priority 3: Integration Hardening

### 3.1 End-to-End Plugin Flow

- **Problem:** Plugin tests are unit-level. No test for the full flow:
  scaffold -> load -> register command -> CLI invocation -> server endpoint
- **Impact:** Medium. The plugin system is new and needs E2E confidence.
- **Approach:** Add test_plugin_e2e.py that exercises the complete lifecycle
  in a temp project directory.
- **Effort:** 1 day
- **Files:** tests/test_plugin_e2e.py (new)

### 3.2 Desktop-Server Communication

- **Problem:** No test for the Rust-to-Python IPC seam (plugin_statuses,
  set_plugin_enabled Tauri commands)
- **Impact:** Medium. This seam is where the desktop meets the engine.
- **Approach:** Mock the Python server response. Test Tauri command
  serialization, error handling, timeout behavior.
- **Effort:** 1-2 days
- **Files:** desktop/src-tauri/src/plugins.rs

## Priority 4: Documentation

### 4.1 ADR Completion

- **Problem:** 7 ADRs written, but missing: stress.py FEA approach,
  crown.py wall analysis, scan.py measurement model
- **Impact:** Low. Existing ADRs cover the major decisions.
- **Approach:** Add ADR-008 (Voxel FEA), ADR-009 (Crown Wall Analysis),
  ADR-010 (Mesh Measurement Model).
- **Effort:** 0.5 days
- **Files:** docs/decisions/ADR-008-*.md, ADR-009-*.md, ADR-010-*.md

### 4.2 API Reference Documentation

- **Problem:** The public API (__init__.py) has no generated documentation.
- **Impact:** Low. The `nurb api` command exists but is CLI-only.
- **Approach:** Add a docs/API.md that mirrors the `nurb api` output.
- **Effort:** 0.5 days
- **Files:** docs/API.md (new)

## Execution Order

| Phase | Tasks | Duration | Checkpoint |
|-------|-------|----------|------------|
| 1 | 1.1 + 1.2 + 1.3 | 4-5 days | All Python modules >60% |
| 2 | 2.1 + 2.2 | 5-6 days | All Rust modules have tests |
| 3 | 3.1 + 3.2 | 2-3 days | E2E flows covered |
| 4 | 4.1 + 4.2 | 1 day | Docs complete |
| **Total** | | **12-15 days** | |

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| React tests require Playwright | High | Medium | Use Vitest + jsdom for unit, Playwright for E2E |
| Rust mock I/O is fragile | Medium | Low | Focus on state transitions, not I/O |
| Plugin E2E needs real build123d | High | Low | Mock the build step, test registration only |
| Headless render tests flaky | High | Medium | Increase timeouts, add retry logic |

## Definition of Done

- [ ] Every Python module has >60% estimated coverage
- [ ] Every Rust module with >100 lines has at least 5 tests
- [ ] Top 3 React components have snapshot/unit tests
- [ ] Plugin E2E test covers full lifecycle
- [ ] All ADRs written for major decisions
- [ ] API reference documented
- [ ] CI passes all workflows
- [ ] Release gate READY