# Gate reviewed changes without losing the strict report

`runner.py` remains the complete historical comparison and intentionally exits
1 when accepted differences exist. Its JSON report retains raw results, failures,
API differences and coverage. `check_report.py` is a separate required gate:

```sh
python tests/compat/check_report.py build/compat/report.json
```

Run the full runner first. A workflow may continue only for runner exit 0 or 1,
then require this checker and the independent candidate safety/default/TSP tests
to succeed. Missing reports, runner usage errors and unexpected exits must fail.
Upload the report even when either step fails. A gate pass means the tested
payloads obey the reviewed exceptions; it is not complete library or application
compatibility, and raw FreeCAD entry-point/G-code differences remain observable.

## What is permitted

`expectations.json` pins the reference distribution and complete case list, and
contains the exact approved API-inventory transitions. It enumerates cases;
there are no case-prefix or wildcard exceptions. Each rule has a reason:

- Removed Boost wrapper/default constructors must preserve the recorded original
  outcome and raise the exact expected candidate Python exception. Native crashes
  and timeouts are never accepted.
- Framework capability lists, enum string representations, tuple pair markers,
  default accessibility and the `minimumZ` property use exact nested-property
  transitions. Other properties, including all sampled/contact geometry, still
  compare normally.
- Newly exposed/repaired APIs have exact reference errors and bounded candidate
  semantic results. These candidate-only fixtures cannot establish historical
  parity. Their known results are recorded to reject future silent drift.
- Contours may rotate their cyclic origin and reorder separate components.
  Coordinates, winding, repeated vertices and explicit closure are preserved.
  Raw contour acceptance also requires the separately executed paired geometry
  case to pass. Algorithm layers, thread counts and contact data remain checked.
- Adaptive-waterline getters may include exactly the recorded extra empty-fiber
  descriptors. Only those fibers are removed for the historical comparison;
  unexpected coordinates, counts, properties or nonempty intervals fail.

The checker recomputes comparisons from reference/candidate payloads and API
inventories. It does not trust report `status`, `counts`, `differences`, or a more
permissive report tolerance. Expectations use fixed 1e-10 relative/absolute
numeric tolerances; strings, types, container shapes and integers compare
strictly. Missing/extra cases, uncovered inventory members and unexpected
Python exceptions fail. Reviewed constructor errors are the only candidate
errors permitted.

## Reviewing an update

Inspect the raw report and establish the cause of each new difference first.
Update only the affected nested-property contract, explicitly named case or
API transition after approval. Avoid replacing an entire existing geometry
payload to accept a changed coordinate. For new candidate-only APIs, review all
stored semantic results and add independent safety tests as needed. Do not
regenerate the manifest automatically from arbitrary failures or relax numeric
tolerances to make a build green. Updated test cases must update the complete
case list deliberately; temporary filtered reports cannot pass this gate.

`test_check_report.py` injects regressions into minimal reports and checks
rejection of unknown properties, forged match summaries, inflated report
tolerances, missing tests, unexpected API exports, exceptions, native failures,
changed candidate-only results, fiber changes, reversed winding and lost
closure. Run it with the other harness unit tests:

```sh
python -m unittest discover -s tests/compat -p 'test_*.py' -v
```
