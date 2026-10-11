# Initial compatibility audit — 2026-10-04

For severity and source-level causes, see [TRIAGE.md](TRIAGE.md). Follow-up testing
demonstrated allocation-dependent ordering in the original wheel and exposed a
TSPSolver reset/destruction crash with a newly added 375th scenario. The table
below preserves the original 374-case audit, not the latest suite totals.

## Implemented follow-up

The candidate now restores the meaningful `EllipsePosition()` default and its
type annotation. Other meaningful point/container defaults already existed.
TSPSolver now owns its graph only as a local variable during `run()`, starts with
zero length, clears prior results on rerun/reset, and handles empty/singleton
inputs. Default geometric constructors without a useful supported state remain
unexposed, per the agreed API direction.

Validation against the rebuilt pip wheel: **11 TSP lifecycle tests, 5 default
state tests, 6 ownership tests and 7 harness tests pass**. A standalone native
test passed AddressSanitizer/UndefinedBehaviorSanitizer with leak detection,
including copying solvers and 1,000 run/reset cycles.

The 375-case strict audit is saved as `build/compat/after-fixes.json`: 318 matches,
29 differing results, 17 candidate errors for intentionally unexposed historical
constructors/classes, and 11 candidate-only cases. All 17 EllipsePosition cases
and 22 parameterized-ellipse cases match; the unsupported `Ellipse()` default
remains intentionally absent. The TSP reset/destruction probe succeeds. The
strict audit still exits 1 for recorded API differences; it is not an assertion
that all historical wrapper behavior should be restored.

## Original audit

Compared pip-installed wheels in isolated CPython 3.11.17 environments on Linux
x86-64. Reference: PyPI `opencamlib==2023.1.11` (native version `2023.01.11`).
Candidate: this checkout at `e6808d3` plus its existing staged binding edits,
built and installed with pip (package version `2022.12.18`, native version
`2023.01.11-55-ge6808d3`). The version mismatch is recorded, not treated as
numerical failure.

| Probe group | Match | Different result | Candidate error | Candidate-only API |
| --- | ---: | ---: | ---: | ---: |
| Geometry | 161 | 10 | 39 | 6 |
| Cutters and algorithms | 85 | 15 | 8 | 4 |
| BlenderCAM and FreeCAD | 37 | 9 | 0 | 0 |
| Total | **283** | **34** | **47** | **10** |

All **255 inventoried public API members** have explicit scenario declarations;
none are unaccounted for. This means member-level scenarios, not exhaustive input
or C++ branch coverage. There were no unexpected reference errors, crashes, or
timeouts. Seven harness tests and six candidate ownership tests also passed.
The differential command correctly exits **1**: strict parity is not established.

## Material findings

- Default constructors formerly exposed by Boost.Python are missing, including
  `EllipsePosition`, `Bbox`, `Ellipse`, `Line`, `Arc`, `Triangle`, and `Fiber`.
  Loss of `EllipsePosition()` prevents using its fields/`setDiangle` and the
  ellipse sampling methods. Old exported `*_base` classes are absent too.
- `Path.getTypeSpanPairs()` changes inner pairs from lists to tuples.
- Assigning `minimumZ` now changes native `getZ()` on path drop-cutters. In the
  original wheel the assignment creates a Python attribute and leaves native Z
  unchanged. This may be an intentional repair, but is a behavior change.
- Enum `str`/`repr` values and several returned objects' Python interfaces differ.
  Triangle queries now return usable `Triangle` objects instead of opaque
  `Triangle_base` objects; contact points expose additional inherited methods.
- Adaptive waterline fiber getters return different numbers of fibers for the
  synthetic pyramid (17 versus 8 at the first layer, and 17 versus 6 at the
  second). Separate contour geometry comparisons do not show coordinate drift
  for these fixtures, but the fiber API itself differs.
- New weave/TSP APIs, `Point.isInside`, inherited point methods and repaired
  property converters are recorded as candidate-only observations. An expected
  original exception is never counted as a parity pass.

## Consumer outcome

All **12 BlenderCAM scenarios match**, covering six cutter types with two skin
settings, unit conversions, minimum Z, cached mesh reuse and chunk ordering.

FreeCAD's tested drop-cutter, tool mapping and filtering scenarios match.
Nine raw waterline scenarios return different loop starting points and/or
component ordering. All nine paired geometry cases match while preserving every
vertex and winding. Baseline repetitions did not establish nondeterminism, so
the ordered differences remain failures; they can affect toolpath entry/travel
order. Full Blender/FreeCAD GUI runs and downstream G-code were not tested.
See [CONSUMERS.md](CONSUMERS.md) for pinned application code and exact boundaries.

## Re-run and inspect

Follow [README.md](README.md). The generated `build/compat/report.json` records
each observation and field difference, stderr/stdout, timings, import paths and
native extension hashes. It is a local generated artifact, not a golden snapshot.
Initial module SHA-256 values:

- Reference: `44eeda0f1d92bbcbe7376ca7d26bb4613e9cff6e6fd2a679594cdbffa46a3653`
- Candidate: `758f25785a610b1bcdadd034183e61e99239f24ebce2533432dbc055b0aa9b8a`

Production bindings were not modified by this test-writing work.
