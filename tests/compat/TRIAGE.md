# Which differences matter, and why

**Current decisions and fixes:** the user accepted removing meaningless geometric
defaults, returning all adaptive-waterline fibers consistently with C++,
returning tuple-valued span pairs, and intentionally removing Python-defined
`MillingCutter` virtual callbacks. The recommendations below describe the
initial historical-compatibility review and are superseded by those decisions.
`EllipsePosition()` has now been restored, including its Python type stub. The
TSP lifetime fix uses a graph local to `run()`, resets result state, and supports
empty and singleton input safely. The meaningful defaults for points, paths,
surfaces and intervals were already present and now have dedicated semantic
checks. The strict differential report still records intentional API changes;
it is not a release-pass verdict.

Follow-up to the strict [initial audit](RESULTS.md), 2026-10-04. Raw mismatch
counts are not counts of independent defects: one missing constructor breaks
many probes, and some changes repair the old bindings. Removal of the Boost
`*_base` classes is explicitly accepted by the user. Other classifications below
are recommendations, not silently approved test exceptions.

## Fix before declaring the rewrite ready

### Newly exposed TSPSolver can abort Python

Confirmed with the candidate wheel in a subprocess:

```python
solver = ocl.TSPSolver()
for x, y in [(0, 0), (3, 0), (0, 4)]:
    solver.addPoint(x, y)
solver.run()
solver.reset()
del solver  # SIGABRT: free(): double free detected in tcache 2
```

Cause: `reset()` deletes `g` but does not null it, and the destructor deletes the
same pointer again ([tsp.hpp](../../src/algo/tsp.hpp), lines 85–87 and 110–114).
The constructor also leaves `g` and `length` uninitialized, and repeated `run()`
overwrites `g` without releasing the previous graph. The proven reset/destruction
crash is a newly exposed Python failure, although the native defects predate the
rewrite. The original PyPI wheel has no `TSPSolver` export.

Recommendation: fix ownership/initialization, preferably RAII, before exposing
this API; define/reset output and length consistently. This is not a request to
reproduce old behavior. The old differential test reset, refilled and reran the
solver, masking the dangling pointer. A new isolated
`algorithms.tsp.reset_then_destroy` case now detects the crash. Its report is
`build/compat/tsp-lifecycle.json`.

### EllipsePosition lost its only construction route

Cause: Boost's `class_<EllipsePosition>(...)` implicitly supplied the default
constructor. The replacement `py::class_` at
[ocl_geometry.cpp](../../src/pythonlib/ocl_geometry.cpp), line 142, supplies no
`.def(py::init<>())`. There is no alternate Python factory.

Consequence: `EllipsePosition()` raises TypeError; its setters and all three
`Ellipse` sampling functions requiring that argument become unusable. This is a
real lost capability, not framework cleanup. The C++ default constructor is
valid and initializes the unit-circle position through `setD()`
([ellipseposition.cpp](../../src/cutters/ellipseposition.cpp), line 36).

Recommendation: restore `.def(py::init<>())`. This addresses many of the initial
39 geometry candidate errors without changing any milling calculation. No use
of these helpers was found in the inspected consumer call sites, so the evidence
is an API regression rather than a demonstrated BlenderCAM/FreeCAD failure.

### AdaptiveWaterline getters lost empty-fiber filtering

At tag `2023.01.11`, `src/pythonlib/adaptivewaterline_py.hpp:51–69` returned fibers
only when `!f.empty()`. Commit `21022dc` removed that wrapper. The current
bindings at [ocl_algo.cpp](../../src/pythonlib/ocl_algo.cpp), lines 100–101, expose
the inherited [Waterline getters](../../src/algo/waterline.hpp), lines 57–58,
which return every stored fiber.

Confirmed: the candidate's 17 X/Y fibers contain exactly the original's 8
nonempty fibers at the first layer and 6 at the second. Filtering candidate
fibers with `f.getInts()` reproduces the old arrays exactly. Contours also match
after cyclic-origin normalization.

Consequence: callers assuming returned fibers contain intervals can fail on
`f.getInts()[0]`, and counts/visualization change. This is a wrapper semantics
regression, not different cutter intersection geometry. The inspected consumer
waterline paths use `getLoops()`, so this does not explain their loop differences.

Recommendation: restore filtering for **AdaptiveWaterline only**. Ordinary
`Waterline` historically returned empty fibers too; do not change its contract.

## Preserve where inexpensive; lower compatibility priority

| Difference | Cause and practical impact | Recommendation |
| --- | --- | --- |
| `Line()` and `Triangle()` disappear | Same implicit-default-constructor migration omission. `Line()` followed by assigning endpoints and appending to a path worked; `Triangle()` creates a valid unit-axis triangle. Both workflows were reproduced against the original wheel. | Restore these valid constructors. They are not equivalent to removing `_base` scaffolding. |
| `getTypeSpanPairs()` inner list becomes tuple | Old `path_py.hpp` called a variable `tuple` but actually built a `boost::python::list`. The rewrite uses `py::make_tuple` at `ocl_geometry.cpp:192,195`. Unpacking/indexing still works; mutation, list equality and exact type checks can break. | Return inner lists for inexpensive compatibility, unless immutability is an intentional documented API change. No inspected consumer break was established. |
| Enum text changes | Boost prints `EDGE`; pybind prints `CCType.EDGE`, and repr also changes. Numeric values/equality remain usable. | Treat as a logging/text-serialization compatibility decision, not a geometry defect. Preserve text only if downstream code depends on it. |

Do **not** blindly restore all other default constructors. `Ellipse()` leaves
essential geometry uninitialized and has no Python setters to complete it.
`Bbox()` sets `initialized=false`, while its initializing methods are not exposed.
`Arc()` leaves scalar state uninitialized until populated/copied, and `Fiber()`
does not compute a usable direction. `MillingCutter` is an incomplete base tool,
not a usable cutting geometry. These need an explicit supported construction
contract; their previous constructibility alone is weak evidence of a capability
that should be preserved. Parameterized Arc/Fiber construction and `surface.bb`
remain available.

## Acceptable cleanup or improvements

### Intentional removal of custom Python cutter callbacks

The old callback wrapper was publicly reachable. Before the migration commit
`bdaced5`, `src/pythonlib/ocl_cutters.cpp` registered `MillingCutter_py` with an
implicit constructor. Its `src/pythonlib/millingcutter_py.hpp` wrapper dispatched
native virtual `facetDrop` and `edgeDrop` calls to Python overrides. This minimal
example runs against the original `2023.1.11` wheel:

```python
import opencamlib as ocl

class CustomCutter(ocl.MillingCutter):
    def __init__(self):
        super().__init__()
        self.calls = []

    def facetDrop(self, cl, triangle):
        self.calls.append("facetDrop")
        return True

cutter = CustomCutter()
triangle = ocl.Triangle(ocl.Point(0, 0, 0), ocl.Point(1, 0, 0), ocl.Point(0, 1, 0))
cl = ocl.CLPoint(0.1, 0.1, -1)
assert ocl.MillingCutter.dropCutter(cutter, cl, triangle) is True
assert cutter.calls == ["facetDrop"]
```

The explicit call to the library's `dropCutter` invokes C++ code, establishing
actual virtual dispatch rather than a direct call to a Python method. The
current wheel fails at `super().__init__()` with `TypeError: CustomCutter: No
constructor defined!`: [ocl_cutters.cpp](../../src/pythonlib/ocl_cutters.cpp)
registers plain `MillingCutter`, without a constructor or callback trampoline.

**Decision:** the user intentionally removes this callback API; no preservation
test or trampoline will be added. This is a real compatibility break for custom
Python cutter implementations, not merely removal of inaccessible scaffolding.
Use the supplied native cutters or implement a new cutter in C++ with bindings.
Python overrides on a built-in cutter do not restore native callback dispatch.
The README's migration section documents this policy.

The old wrapper also had limitations: `vertexDrop` is not virtual in C++, so it
was not dispatched by native `dropCutter`; mutation of the callback's `cl` copy
did not update the original CLPoint. Those limitations do not negate the proven
`facetDrop` callback. No use of this customization API was found in the pinned
BlenderCAM/FreeCAD source paths inspected in [CONSUMERS.md](CONSUMERS.md).

### Other accepted changes

- **`*_base` removal:** accepted. These exported the C++ parents of the Boost
  Python wrapper classes. Exposing the real types directly eliminates the need
  for them. Do not add dummy classes just to pass the strict snapshot.
- **Usable `Triangle`/`Fiber` results instead of opaque base wrappers:** an
  improvement, provided their data and operations remain compatible.
- **CCPoint/CLPoint inheritance, Point.isInside, repaired tris/p conversions:**
  added working capabilities; an original error should not be the desired result.
- **Ownership retention:** the new keep-alive policies allow safe temporary
  inputs. Candidate ownership checks pass. Do not reproduce dangling-pointer
  behavior from the old wrapper.
- **`minimumZ`:** commit `646ca4e` adds a property alias calling `setZ`. The old
  wheel accepted the assignment merely as an arbitrary Python attribute, leaving
  native Z unchanged. For standard PathDropCutter this now affects actual floor
  heights, so document it as a functional bug fix/API addition, not parity.
  `setZ()` is the cross-version API. Separately, AdaptivePathDropCutter samples
  `span->getPoint()` without applying the stored floor in **both versions**
  ([adaptivepathdropcutter.cpp](../../src/dropcutter/adaptivepathdropcutter.cpp),
  lines 62–65 and 75–77). Its alias changes stored `getZ()` but does not repair
  that pre-existing sampling behavior.

## Waterline ordering: old allocation sensitivity, observable FreeCAD impact

The initial repeated-worker tests did not find reference variation. A more
discriminating probe now does: retaining 1, 20, 100 or 10,000 unrelated `ocl.Point`
objects before the **original** wheel runs the same waterline changes its loop
origins. Every canonical geometry comparison remains identical. These results
supersede any inference that the original loop starting points were stable.

Cause: [weave.cpp](../../src/algo/weave.cpp), line 53, starts traversal at
`*clVertexSet.begin()`. That set holds pointer-valued Boost `listS` vertex
descriptors ([weave.hpp](../../src/algo/weave.hpp), line 62;
[weave_typedef.hpp](../../src/algo/weave_typedef.hpp), lines 108–118). Selection
therefore depends on heap addresses. The relevant traversal and waterline
algorithms are unchanged from tag `2023.01.11`; allocation differences between
the bindings/builds explain the observed behavior, though the precise allocation
responsible for each cross-wheel difference was not isolated.

Recommendation: compare closed-loop geometry allowing cyclic rotations and
component permutations, while preserving vertices, closure and winding. Keep
raw order as diagnostic information. Matching one old wheel's pointer order is
not a meaningful portability target. If deterministic paths are required, define
a geometric start/component ordering or implement consumer-side seam/travel
selection as a separate improvement.

This is not completely invisible to users: FreeCAD's pinned `waterline_to_gcode`
uses the first loop's start and aligns subsequent seams; retained `_loopToGcode`
also positions at `loop[0]`. Entry, plunge and travel positions can change even
when cutting contours are identical. All nine consumer contour geometry pairs
match. BlenderCAM's inspected sampling path uses BatchDropCutter and does not
consume these loops; its 12 scenarios match. See [CONSUMERS.md](CONSUMERS.md) for
source pins and application scope.

The initial diagnosis did not modify production bindings. The subsequent fixes
and their validation are recorded in [RESULTS.md](RESULTS.md). Strict audit
differences remain visible; this classification does not silently waive them.
