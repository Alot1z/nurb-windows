# nurb core progress

## Status: Phase 1 - Not Started

Prerequisites outstanding. See below.

## Quick reference

- Research: `docs/core/RESEARCH.md`
- Implementation: `docs/core/IMPLEMENTATION.md`

## Prerequisites

- [ ] Commit the current tree. **No restore point exists.** Everything below the
      phase list was built uncommitted.
- [ ] Decide where the Notch port lives. Recommendation: `examples/notch/` in this
      repo, its own project directory with `parts/` and `system.py`, doubling as
      test corpus and worked example.

---

## Phase progress

### Phase 1: Kernel proof
**Status:** Not Started

Port `Hook - Scissors - 1x` and `Shelf - Gridfinity 2x2 - 4x` to prove OCCT handles
real Notch geometry.

#### Tasks completed
- (none yet)

#### Decisions made
- (none yet)

#### Blockers
- (none)

---

### Phase 2: `nurb check`
**Status:** Not Started

Printability rules on the in-memory B-rep, calibrated to zero false positives.

#### Tasks completed
- (none yet)

#### Decisions made
- (none yet)

#### Blockers
- Depends on Phase 1 producing parts to calibrate against

---

### Phase 3: Agent interface
**Status:** Not Started

`nurb rules`, card generation, headless render, harness shims.

#### Tasks completed
- (none yet)

#### Decisions made
- (none yet)

#### Blockers
- (none)

---

### Phase 4: Viewer and human UX
**Status:** Not Started

Parameter sliders, vendored three.js, section view.

#### Tasks completed
- (none yet)

#### Decisions made
- (none yet)

#### Blockers
- (none)

---

### Phase 5: Full port, extract, tests
**Status:** Not Started

Remaining 14 Notch parts, `nurb extract`, pytest suite, CI.

#### Tasks completed
- (none yet)

#### Decisions made
- (none yet)

#### Blockers
- Depends on Phase 1 establishing the part patterns

---

## Pre-phase work (already built)

The runtime skeleton predates this plan and belongs to no phase. Recorded here so a
future session knows what exists.

**Built and verified 2026-07-25:**

- `nurb new / dev / build / export`, 744 lines across six files
- Live rebuild loop: save a part, geometry swaps in the browser
- **Camera survives rebuilds.** Verified by parking the camera at a known position
  and diffing after a rebuild. Persists per part to localStorage across reloads.
- Reframe offered as a button, only when the bbox changes more than 3x
- Build errors show a traceback trimmed to the user's file, retain the last good
  geometry at 22% opacity, and clear on the next good build
- Draft mode wired through the part contract

**Verified only on `Box() - chamfer()`.** This is the central caveat on everything
above, and the entire reason Phase 1 comes first.

---

## Session log

### 2026-07-25

Built the runtime skeleton, then wrote RESEARCH.md and IMPLEMENTATION.md.

Measured on this machine (M-series arm64, Python 3.13):

```
import build123d          45.7s cold, 2.28s warm
build + boolean            4ms
chamfer, 8 edges           6ms
tessellate (tol 0.1)      51ms
export STL / STEP          3ms / 15ms
draft vs polished         1ms vs 18ms
```

Three bugs found and fixed (see Lessons learned).

Next session: prerequisites, then Phase 1.

---

## Files changed

```
src/nurb/__init__.py      part decorator + build123d re-export
src/nurb/registry.py      @part, signature introspection
src/nurb/builder.py       load, build, tessellate, GLB
src/nurb/server.py        watcher, rebuild, HTTP + websocket on one port
src/nurb/viewer.html      three.js viewer, Z-up, camera persistence
src/nurb/cli.py           new / dev / build / export
parts/bracket.py          throwaway demo part
README.md
docs/core/*.md
```

---

## Architectural decisions

Carried from research and the questions answered during planning.

| Decision | Rationale |
|---|---|
| build123d / OCCT as the kernel | Same class of B-rep kernel as Fusion's ASM, runs headless, real chamfers and STEP |
| Keyword defaults are the parameters | One declaration serves the agent, CLI, slider UI, tests, and any future configurator. A separate `PARAMS` dict would drift. |
| Checks run on in-memory B-rep, not files | Exact face areas and normals instead of triangles. Costs standalone usefulness; accepted. |
| Notch ports to nurb | Its 16 parts become the test corpus and the calibration set for the rules |
| Systems extracted, never scaffolded | Notch did not begin as a system; `block_width` exists because a wall got measured. `nurb extract`, not `nurb new system`. |
| No MCP server | The existing Fusion MCP needed a hand-written HTTP client to be usable. A CLI works in every harness. |
| Boring command names | The primary user is a model. It can guess `build` and `check`; it cannot guess a themed alias. |
| Persistent process is mandatory | 2.28s warm import per rebuild would make the loop unusable |
| Do not port Fusion's scaffolding | `ChannelTool`, the 16-lobe comb, `CombWeb`, `JoinComb` exist only because combine tool lists never grow. Use a `for` loop. |
| Name: nurb, command `nurb` | Clean on PyPI, npm, nurb.dev. NURBS is the geometry primitive, so the search overlap is on-topic rather than misleading. |

---

## Lessons learned

**Three bugs from building the runtime, all non-obvious:**

1. **Black render.** trimesh welded a box to 8 shared corners and dropped the normal
   attribute, leaving the shader nothing to light. Fix: `process=False` on the
   `Trimesh` constructor, and touch `mesh.vertex_normals` before export. OCCT already
   splits vertices at face boundaries, which is the layout you want.
2. **Hot reload silently dead.** The watchdog `Observer` and the asyncio drain task
   were both created without holding a reference, and asyncio keeps only weak
   references to tasks. Failed by never firing, with no error.
3. **Canvas stacking regression.** Fixing a ResizeObserver feedback loop by making
   the canvas `position: absolute` turned it into a positioned element appended after
   the overlay divs, so it painted over the HUD. Needed explicit `z-index`.

**Process lessons:**

- A repro that starts at equilibrium proves nothing. Reapplying the old canvas CSS
  live failed to reproduce the resize loop because the canvas was already the right
  size; the loop needs an initial mismatch to ratchet against. Nearly filed it as
  "not the cause."
- `elementFromPoint` skips `pointer-events: none` elements, so it reported the canvas
  covering the HUD when painting was fine. Screenshots were the real evidence.
- Redirect stdout early. The first hot-reload debugging session was blind because
  Python buffers stdout when it is not a tty and none of the prints had `flush=True`.
