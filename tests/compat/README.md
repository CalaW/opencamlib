# Python wheel compatibility tests

See [TRIAGE.md](TRIAGE.md) for the distinction between real defects, accepted
Boost wrapper cleanup, improvements, and allocation-dependent contour ordering.

This suite runs the **installed pip packages** in separate interpreters. It does
not import the checkout's extension or load two native libraries into one process.
The reference is the released Boost.Python wheel `opencamlib==2023.1.11`; the
candidate is a wheel built from the current checkout, including uncommitted edits.
Python 3.11 has an original release wheel on the supported mainstream platforms.

## Reproduce

Run from the repository root with Python 3.11 and the build prerequisites from
the project README (CMake, C++ compiler, Boost headers, Python development files):

```sh
python3.11 -m venv /tmp/ocl-reference
python3.11 -m venv /tmp/ocl-rewrite
/tmp/ocl-reference/bin/python -m pip install --only-binary=:all: opencamlib==2023.1.11
/tmp/ocl-rewrite/bin/python -m pip install .
python3 tests/compat/runner.py \
  --reference /tmp/ocl-reference/bin/python \
  --candidate /tmp/ocl-rewrite/bin/python \
  --output build/compat/report.json
```

On Windows use each environment's `Scripts/python.exe`. The runner itself only
needs Python 3.10+ and the standard library; the workers require Python 3.10+.
No Blender, FreeCAD, GUI, display server, pytest, or network is needed after setup.
Rebuild/reinstall the candidate after changing its C++ bindings.

Use `--list` to list cases, `--case substring` to select cases (repeatable),
`--jobs 4` to set worker concurrency, and `--timeout 30` for each worker's deadline.
OpenMP is restricted to one thread for deterministic comparison. Floating-point
values use relative/absolute tolerances of `1e-10`; `--rtol 0 --atol 0` requests
exact comparison. Types, booleans, integer counters, ordering, and lengths are
strict. Cases explicitly encode native return types where those are observable.

The report includes the distribution version, native module SHA-256, library
version, interpreter, import location, complete results from both libraries,
native output, exceptions, crashes, timeouts, API inventories, and per-field
differences. Exit status 1 means differences, failed probes, API changes, or
uncovered members; status 2 means setup/import failed. A reference failure is
**inconclusive**, even if the candidate fails identically. Nothing is silently
xfail'ed to make the rewrite pass.

`candidate_only` identifies a documented, precisely matched original-wheel
exception for an added or newly usable API. It is recorded separately from parity
passes. Raw contour cases preserve starting points and component order; paired
geometry cases canonicalize only cyclic start and component order, preserving
vertices and winding. Both results remain visible. Library diagnostics are saved
but not generally compared (they contain timings and binding-specific messages);
the explicit `Fiber.printInts` probe compares printed output too.
Candidate-only weave probes validate `printGraph` output against graph counts.

## Scope and honest coverage

The API inventory is discovered at runtime in both installed libraries. Case
declarations map public members to scenarios. Uncovered members and explicitly
documented unsafe/unreachable methods are reported separately. These declarations
are **not C++ branch coverage** and cannot prove all possible inputs or machining
geometries. A case that fails before completion does not count as a matching case.
Exported framework base classes and new APIs are also visible in the API diff.
Library versions and build metadata are recorded, not compared as toolpath data.

Geometry probes cover overloads, operators, properties, ownership/copy semantics,
STL loading, intervals, paths, and enums. Algorithm probes cover cutters,
contact/drop/push behavior, batches, paths, filtering, and contours. Consumer
probes reproduce the OpenCAMLib call sequences used by BlenderCAM and FreeCAD;
see [CONSUMERS.md](CONSUMERS.md) for pinned sources and boundaries. They are not
full GUI application or G-code/postprocessor integration tests.

Run the harness's own failure-detection tests with:

```sh
python3 -m unittest discover -s tests/compat -p 'test_*.py' -v
OMP_NUM_THREADS=1 /tmp/ocl-rewrite/bin/python tests/compat/check_lifetimes.py
/tmp/ocl-rewrite/bin/python tests/compat/check_defaults.py
/tmp/ocl-rewrite/bin/python tests/compat/check_tsp.py
```

The separate lifetime checks verify the rewrite's `keep_alive` policies,
release after owner destruction, and owned offset cutters. `getFibers()` returns
independent snapshots: later runs/appends and operation destruction cannot alter
or invalidate them, and changing a snapshot does not change the operation.
The vector-reallocation regression runs in a subprocess to report native crashes.
Weak references are checked before native calls to avoid accessing
freed dependencies. These are candidate safety checks, not parity claims about
the original wheel's undocumented dangling-pointer behavior.

Default-state checks exercise zero points/unset contacts, populated initially
empty paths/surfaces/intervals, and zero-angle `EllipsePosition` sampling. These
are the supported meaningful defaults; arbitrary or uninitialized geometric
defaults from Boost are not the desired behavior. TSP checks run each lifecycle
scenario in a subprocess, covering reset/destruction, repeated runs, reuse and
empty/singleton inputs. An empty solver returns an empty tour and zero length;
a singleton returns the closed tour `[0, 0]` with zero length.

To add a probe, add a deterministic function accepting the imported `opencamlib`
module to one of `cases_*.py`, register it in `CASES`, and declare exercised
qualified members in `COVERAGE`. Return JSON-safe semantic observations; encode
expected errors inside the case, and let unexpected errors reach the runner.
Each probe runs in a fresh process with a temporary working directory and a
deadline. Avoid undefined behavior and document unsupported methods explicitly.
