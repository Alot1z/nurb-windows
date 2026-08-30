# Architecture Decision Records

## ADR-001: Parts as Python Functions

**Status:** Accepted

**Date:** 2026-01-01

**Context:** We need a way to define 3D-printable parts that an agent can
understand, modify, and rebuild programmatically.

**Decision:** Each part is a Python function with keyword defaults as parameters.
The @part decorator handles registration, signature introspection, and viewer
slider generation. A single declaration feeds the agent, CLI, viewer, tests,
and any future configurator.

**Alternatives Considered:**
- YAML/JSON parameter files: Rejected because parameters would drift from the actual function signature.
- Separate PARAMS dict: Rejected for the same drift reason.
- Class-based parts: Rejected because functions compose more naturally.

**Consequences:**
- Positive: Single source of truth. No parallel configuration.
- Positive: Agent can read the signature and know every parameter.
- Negative: Parts must be importable Python (no arbitrary CAD scripts).

---

## ADR-002: build123d (OCCT) Over FreeCAD or OpenSCAD

**Status:** Accepted

**Date:** 2026-01-01

**Context:** We need a real CAD kernel for B-rep solids, not mesh-only.

**Decision:** Use build123d, which wraps Open CASCADE Technology (OCCT).
Parts are real B-rep solids with exact geometry.

**Alternatives Considered:**
- FreeCAD: Rejected because it is stateful and hard to script idempotently.
- OpenSCAD: Rejected because it is mesh-only, no true B-rep.
- CadQuery: Considered, but build123d has better algebra-mode API.

**Consequences:**
- Positive: Real B-rep solids. Exact fillets, chamfers, boolean ops.
- Positive: Algebra mode (no builder state) fits the function model.
- Negative: OCCT is large (~200MB). LGPL-2.1-with-exception license.
- Negative: Some operations are slow (tessellation was 620ms, now 30ms).

---

## ADR-003: HTTP+WebSocket Server for Viewer Communication

**Status:** Accepted

**Date:** 2026-01-01

**Context:** The viewer needs to receive geometry updates in real-time without
page reloads, and the server must handle file watching, rebuilding, and API
endpoints simultaneously.

**Decision:** Single Python process runs an HTTP server (static files + API)
and WebSocket (live geometry push + status). One port for everything.

**Alternatives Considered:**
- Separate HTTP and WebSocket servers: Rejected because two ports = two processes = harder to manage.
- Electron IPC: Rejected because the viewer must also work standalone.
- SSE only: Rejected because WebSocket supports bidirectional communication.

**Consequences:**
- Positive: Single process, single port, simple deployment.
- Positive: Viewer works in browser and in Tauri iframe.
- Negative: Python GIL limits concurrent request handling.
- Negative: File watcher and rebuild run in the same event loop.

---

## ADR-004: Three.js Vendor Bundle (Offline-First Viewer)

**Status:** Accepted

**Date:** 2026-01-01

**Context:** The CAD tool must work offline (planes, air-gapped environments).

**Decision:** Vendor three.js r169 into src/nurb/vendor/three/. The viewer
needs no network access.

**Alternatives Considered:**
- CDN import: Rejected because it fails offline.
- npm + bundler: Rejected because it adds build complexity to the viewer.

**Consequences:**
- Positive: Works offline. No CDN dependency.
- Positive: No build step for the viewer HTML.
- Negative: Manual version updates. Larger package size.

---

## ADR-005: Plugin System with TOML Manifests

**Status:** Accepted

**Date:** 2026-08-22

**Context:** Users need to extend nurb with custom commands, MCP tools, and
build checks without modifying the core.

**Decision:** Plugins are directories with a plugin.toml manifest. The loader
discovers, imports, and registers them. Enable/disable state persists in
.nurb/plugins.toml per project.

**Alternatives Considered:**
- Python entry points: Rejected because they require package installation.
- JSON manifests: Rejected because TOML is more human-readable.
- Single global plugins dir: Rejected because plugins should be project-local.

**Consequences:**
- Positive: Project-local. No global state pollution.
- Positive: CLI + desktop toggle + server endpoint all read the same state.
- Negative: Each plugin import loads code into the process.
- Negative: Disabled plugins are still visible (by design, for toggles).

---

## ADR-006: Tauri Desktop App with Embedded Viewer

**Status:** Accepted

**Date:** 2026-01-01

**Context:** The desktop app is the primary entry point. It must embed the
viewer, manage projects, handle chat, and expose CLI capabilities.

**Decision:** Use Tauri (Rust backend + webview frontend). The viewer runs
in an iframe. The Rust side handles process management, provisioning, and
native integration. React shell handles UI chrome.

**Alternatives Considered:**
- Electron: Rejected because of larger bundle size and security surface.
- Native GUI (Qt/GTK): Rejected because the viewer is web-based anyway.
- VS Code extension: Rejected because it limits the surface area.

**Consequences:**
- Positive: Small bundle. Native file system access via Rust.
- Positive: Viewer iframe is the same code as nurb dev in browser.
- Negative: Tauri webview quirks (CORS, CSP, IPC).
- Negative: Shell duplicates viewer state on purpose (postMessage seam).

---

## ADR-007: Conventional Commits with Guard Hooks

**Status:** Accepted

**Date:** 2026-08-22

**Context:** Commit messages should be machine-readable and consistent.

**Decision:** Use conventional commits (feat:, fix:, etc.). Enforce via
.githooks/commit-msg hook. No AI footers (Co-Authored-By, Generated with).

**Alternatives Considered:**
- No commit convention: Rejected because it makes changelog generation hard.
- Semantic PR titles only: Rejected because commit messages are more reliable.

**Consequences:**
- Positive: Consistent history. Changelog generation possible.
- Positive: Pre-push hook scans entire history for banned phrases.
- Negative: Amending commits to fix the message is annoying.
- Negative: Pre-push scan is slow on large histories.

---

*ADR-001 through ADR-004 recorded at project inception.
ADR-005 through ADR-007 recorded during the 2026-08-22 hardening session.*