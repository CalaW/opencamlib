#!/usr/bin/env python3
"""Compare installed OpenCAMLib distributions without loading both native ABIs.

No third-party test dependency is required. See README.md for reproducible setup.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import importlib
import importlib.metadata
import inspect
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import traceback

MODULES = ("cases_geometry", "cases_algorithms", "cases_consumers")
OPERATORS = {"__init__", "__str__", "__add__", "__sub__", "__mul__",
             "__rmul__", "__iadd__", "__isub__", "__eq__", "__ne__"}


def load_cases():
    cases, coverage, limitations = {}, {}, {}
    for name in MODULES:
        module = importlib.import_module(name)
        for key, function in module.CASES.items():
            if key in cases:
                raise ValueError("Duplicate case: " + key)
            cases[key] = function
        coverage.update(module.COVERAGE)
        limitations.update(getattr(module, "LIMITATIONS", {}))
    return cases, coverage, limitations


def reference_unavailable():
    result = {}
    for name in MODULES:
        result.update(getattr(importlib.import_module(name), "REFERENCE_UNAVAILABLE", {}))
    return result


def inventory(ocl):
    """Inventory library-defined methods, properties, enums and module functions.

    Exclude binding framework machinery; inherit members through the declaring
    class so a cutter method is counted once rather than eleven times.
    """
    members, exports = {}, {}
    for name in sorted(dir(ocl)):
        if name.startswith("_") or name == "ocl":
            continue
        obj = getattr(ocl, name)
        if inspect.ismodule(obj):
            continue
        if inspect.isclass(obj):
            exports[name] = "class"
            is_enum = hasattr(obj, "names") or hasattr(obj, "__members__")
            if is_enum:
                members[name] = "enum"
                continue
            for attr, value in vars(obj).items():
                if attr.startswith("_") and attr not in OPERATORS:
                    continue
                if attr in {"__module__", "__doc__"}:
                    continue
                members[name + "." + attr] = "method" if callable(value) else "property"
        elif callable(obj):
            exports[name] = "function"
            members[name] = "function"
        else:
            exports[name] = "constant"
    return {"members": members, "exports": exports}


def metadata(ocl):
    extension = getattr(ocl, "ocl", ocl)
    filename = Path(extension.__file__).resolve()
    return {
        "python": sys.version, "executable": sys.executable,
        "distribution": importlib.metadata.version("opencamlib"),
        "library_version": ocl.version(), "module_path": str(filename),
        "module_sha256": hashlib.sha256(filename.read_bytes()).hexdigest(),
    }


def worker(case, output):
    # Native assertions must not leave large core files in the working tree.
    try:
        import resource
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    except ImportError:
        pass
    try:
        import opencamlib as ocl
        if case == "__inventory__":
            result = {"metadata": metadata(ocl), "api": inventory(ocl)}
        else:
            result = load_cases()[0][case](ocl)
        payload = {"status": "ok", "value": result}
        # Validate serialization here, where errors can be attributed to a case.
        encoded = json.dumps(payload, allow_nan=False, sort_keys=True)
    except Exception as exc:
        encoded = json.dumps({"status": "error", "exception": type(exc).__name__,
                              "message": str(exc), "traceback": traceback.format_exc()})
    Path(output).write_text(encoded, encoding="utf-8")


def invoke(python, case, timeout):
    start = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="ocl-compat-") as directory:
        output = Path(directory) / "result.json"
        env = os.environ.copy()
        env.pop("PYTHONPATH", None)
        env.pop("PYTHONHOME", None)
        env.update(OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", LC_ALL="C",
                   PYTHONHASHSEED="0")
        command = [str(python), "-I", str(Path(__file__).resolve()),
                   "--worker", case, "--output", str(output)]
        try:
            process = subprocess.run(command, cwd=directory, env=env,
                                     capture_output=True, timeout=timeout)
            logs = {"stdout": process.stdout.decode("utf-8", "replace")[-16000:],
                    "stderr": process.stderr.decode("utf-8", "replace")[-16000:]}
            if process.returncode:
                result = {"status": "crash", "returncode": process.returncode}
            elif not output.exists():
                result = {"status": "protocol_error", "message": "worker produced no result"}
            else:
                result = json.loads(output.read_text(encoding="utf-8"))
            result.update(logs)
            if case in {"algorithms.weave.SimpleWeave", "algorithms.weave.SmartWeave"} and result["status"] == "ok":
                expected = graph_output(result["value"])
                if result["stdout"] != expected:
                    result.update(status="error", exception="AssertionError",
                                  message="Weave.printGraph output disagrees with graph counts",
                                  expected_stdout=expected)
        except subprocess.TimeoutExpired:
            result = {"status": "timeout", "timeout_seconds": timeout}
        except OSError as exc:
            result = {"status": "launch_error", "message": str(exc)}
    result["duration_seconds"] = time.monotonic() - start
    return result


def graph_output(value):
    vertices, edges, cl = value["count"], len(value["edges"]), len(value["cl"])
    return (f" number of vertices: {vertices}\n number of edges: {edges}\n"
            f" counted {vertices} vertices\n          CL-nodes: {cl}\n"
            f"    internal-nodes: {vertices - cl}\n")


def differences(left, right, path="$", *, rtol=1e-10, atol=1e-10):
    """Strict structure/types and tolerant floating-point comparison."""
    if type(left) is not type(right):
        return [{"path": path, "reference": left, "candidate": right, "reason": "type"}]
    if isinstance(left, dict):
        result = []
        for key in sorted(left.keys() | right.keys()):
            where = path + "." + key
            if key not in left or key not in right:
                result.append({"path": where, "reason": "missing key",
                               "reference_present": key in left, "candidate_present": key in right})
            else:
                result.extend(differences(left[key], right[key], where, rtol=rtol, atol=atol))
        return result
    if isinstance(left, list):
        if len(left) != len(right):
            return [{"path": path, "reason": "length", "reference": len(left), "candidate": len(right)}]
        result = []
        for index, (a, b) in enumerate(zip(left, right)):
            result.extend(differences(a, b, f"{path}[{index}]", rtol=rtol, atol=atol))
        return result
    equal = math.isclose(left, right, rel_tol=rtol, abs_tol=atol) if isinstance(left, float) else left == right
    return [] if equal else [{"path": path, "reference": left, "candidate": right, "reason": "value"}]


def classify(reference, candidate, **tolerances):
    if reference["status"] != "ok":
        return "baseline_error", []
    if candidate["status"] != "ok":
        return "candidate_error", []
    changes = differences(reference["value"], candidate["value"], **tolerances)
    return ("different" if changes else "match"), changes


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, help="Python with original pip wheel installed")
    parser.add_argument("--candidate", type=Path, help="Python with rewrite pip wheel installed")
    parser.add_argument("--output", type=Path, default=Path("build/compat/report.json"))
    parser.add_argument("--case", action="append", default=[], help="Case substring filter (repeatable)")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--timeout", type=float, default=30)
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--rtol", type=float, default=1e-10)
    parser.add_argument("--atol", type=float, default=1e-10)
    parser.add_argument("--worker", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.worker:
        worker(args.worker, args.output)
        return 0
    if (args.jobs < 1 or not math.isfinite(args.timeout) or args.timeout <= 0
            or any(not math.isfinite(v) or v < 0 for v in (args.rtol, args.atol))):
        parser.error("jobs/timeout must be positive; timeout and nonnegative tolerances must be finite")
    cases, coverage, limitations = load_cases()
    known_unavailable = reference_unavailable()
    selected = sorted(k for k in cases if not args.case or any(term in k for term in args.case))
    if args.list:
        print("\n".join(selected))
        return 0
    if not args.reference or not args.candidate:
        parser.error("--reference and --candidate are required")
    if not selected:
        parser.error("No cases selected")
    # Do not resolve symlinks: venv executables point to the same base interpreter.
    reference, candidate = args.reference.absolute(), args.candidate.absolute()
    inventories = {label: invoke(python, "__inventory__", args.timeout)
                   for label, python in (("reference", reference), ("candidate", candidate))}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if any(item["status"] != "ok" for item in inventories.values()):
        args.output.write_text(json.dumps(inventories, indent=2), encoding="utf-8")
        print("Package import/inventory failed; see", args.output)
        return 2
    observed = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = {pool.submit(invoke, python, case, args.timeout): (case, label)
                   for case in selected
                   for label, python in (("reference", reference), ("candidate", candidate))}
        for future in concurrent.futures.as_completed(futures):
            case, label = futures[future]
            observed.setdefault(case, {})[label] = future.result()
    results, counts = {}, {}
    for case in selected:
        pair = observed[case]
        status, changes = classify(pair["reference"], pair["candidate"], rtol=args.rtol, atol=args.atol)
        if case == "geometry.Fiber.printInts" and status == "match":
            changes = differences(pair["reference"]["stdout"], pair["candidate"]["stdout"], "$.stdout")
            status = "different" if changes else "match"
        exception = known_unavailable.get(case)
        if (exception and pair["reference"]["status"] == "error"
                and pair["reference"].get("exception") == exception["exception"]):
            status = "candidate_only" if pair["candidate"]["status"] == "ok" else "candidate_error"
        results[case] = {"status": status, "differences": changes, **pair,
                         "declared_members": coverage.get(case, [])}
        if exception:
            results[case]["reference_limitation"] = exception
        counts[status] = counts.get(status, 0) + 1
        if status != "match":
            failure = pair["reference"] if status in {"baseline_error", "candidate_only"} else pair["candidate"]
            detail = changes[0]["path"] if changes else failure.get("exception", failure["status"])
            print(f"{status}: {case}: {detail}")
    apis = {label: item["value"]["api"] for label, item in inventories.items()}
    all_members = set(apis["reference"]["members"]) | set(apis["candidate"]["members"])
    declared = {member for case in selected for member in coverage.get(case, [])}
    successful = {member for case in selected if results[case]["status"] == "match"
                  for member in coverage.get(case, [])}
    coverage_report = {"inventory": sorted(all_members), "declared": sorted(declared),
                       "matching_case_members": sorted(successful),
                       "uncovered": sorted(all_members - declared - set(limitations)),
                       "limitations": limitations,
                       "note": "Explicit case declarations, not instrumented C++ branch coverage. A matching case does not prove every input."}
    report = {"schema_version": 1, "inventories": inventories, "counts": counts,
              "tolerances": {"rtol": args.rtol, "atol": args.atol},
              "api_differences": differences(apis["reference"], apis["candidate"]),
              "coverage": coverage_report, "cases": results}
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(counts, sort_keys=True), f"; uncovered members: {len(coverage_report['uncovered'])}")
    print("Report:", args.output)
    return int(any(k != "match" for k in counts) or bool(report["api_differences"])
               or (not args.case and bool(coverage_report["uncovered"])))


if __name__ == "__main__":
    # -I deliberately excludes cwd and PYTHONPATH; add only this test directory.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    raise SystemExit(main())
