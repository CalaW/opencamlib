"""Deterministic public API probes based on src/pythonlib/ocl_{cutters,algo,dropcutter}.cpp.

The runner isolates every case because native-library failures can terminate Python.
Point/contact order is retained; only unordered graph collections are sorted.
"""
from functools import partial
import math


CASES = {}
COVERAGE = {}
LIMITATIONS = {
    "CompositeCutter.offsetCutter": "Native implementation is explicitly unsupported (assert(0)); inherited by all composite cutters.",
    "CutterLocationSurface.run": "Native run is an empty implementation; graph construction/setters are still checked.",
    "BatchDropCutter.getCalls": "Exact counters checked with one thread; native parallel counter can vary, so multi-thread cases check range/type instead.",
}


def register(name, function, members):
    name = "algorithms." + name
    CASES[name] = function
    COVERAGE[name] = members


def point(p):
    return [p.x, p.y, p.z]


def contact(p):
    return {"point": point(p), "type": int(p.type)}


def clpoint(p):
    return {"point": point(p), "contact": contact(p.getCC())}


def interval(i):
    # Empty intervals' bounds/contact points are not defined by the contract.
    if i.empty():
        return {"empty": True}
    return {"empty": False, "lower": i.lower, "upper": i.upper,
            "lower_cc": contact(i.lower_cc), "upper_cc": contact(i.upper_cc)}


def fiber(f):
    return {"p1": point(f.p1), "p2": point(f.p2),
            "intervals": [interval(i) for i in f.getInts()]}


def triangle(t):
    return [point(p) for p in t.getPoints()]


def contour(loop):
    """Canonical cyclic start of graph contour, preserving winding and repeats."""
    coords = [point(p) for p in loop]
    if not coords:
        return coords
    # Face traversal starts from pointer-ordered graph vertices; compare the
    # same directed closed contour without depending on allocator addresses.
    return min(coords[i:] + coords[:i] for i in range(len(coords)))


def triangles(ocl):
    # Flat facet, oblique facet, vertical wall, and a distant miss.
    coords = [((-2, -2, 0), (2, -2, 0), (0, 2, 0)),
              ((-2, -2, 0), (2, -2, 1), (0, 2, 2)),
              ((0, -2, 0), (0, 2, 0), (0, 0, 3)),
              ((10, 10, 0), (12, 10, 0), (10, 12, 1))]
    return [ocl.Triangle(*(ocl.Point(*p) for p in c)) for c in coords]


def surface(ocl):
    # Closed pyramid avoids open-contour degeneracy in waterline/weave.
    s = ocl.STLSurf()
    a, b, c, d, top = [ocl.Point(*v) for v in
                       [(-2, -2, 0), (2, -2, 0), (2, 2, 0), (-2, 2, 0), (0, 0, 3)]]
    for vertices in [(a, b, top), (b, c, top), (c, d, top), (d, a, top), (a, c, b), (a, d, c)]:
        s.addTriangle(ocl.Triangle(*vertices))
    return s


CUTTERS = {
    "CylCutter": (1.2, 6.0), "BallCutter": (1.2, 6.0),
    "BullCutter": (1.2, .2, 6.0), "ConeCutter": (1.2, math.pi / 4, 6.0),
    "CompCylCutter": (1.2, 6.0), "CompBallCutter": (1.2, 6.0),
    "CylConeCutter": (.6, 1.2, math.pi / 4),
    "BallConeCutter": (.6, 1.2, math.pi / 4),
    "BullConeCutter": (.6, .1, 1.2, math.pi / 4),
    "ConeConeCutter": (.6, math.pi / 3, 1.2, math.pi / 6),
}


def cutter_properties(c):
    return {"radius": c.getRadius(), "diameter": c.getDiameter(),
            "length": c.getLength(), "str": str(c)}


def cutter_drop(ocl, name, method):
    cutter = getattr(ocl, name)(*CUTTERS[name])
    output = []
    for ti, t in enumerate(triangles(ocl)):
        for xyz in [(0, 0, -2), (.3, -.4, -2), (1.8, -1.8, -2), (5, 5, -2), (0, 0, 10)]:
            p = ocl.CLPoint(*xyz)
            changed = getattr(cutter, method)(p, t)
            output.append({"triangle": ti, "input": xyz, "changed": changed, "cl": clpoint(p)})
    return {"properties": cutter_properties(cutter), "drops": output}


def cutter_push(ocl, name):
    cutter = getattr(ocl, name)(*CUTTERS[name])
    output = []
    for ti, t in enumerate(triangles(ocl)):
        for ends in [((-4, 0, .2), (4, 0, .2)), ((0, -4, .8), (0, 4, .8)),
                     ((-4, 5, .2), (4, 5, .2)), ((-4, 0, 5), (4, 0, 5))]:
            f = ocl.Fiber(*(ocl.Point(*p) for p in ends))
            i = ocl.Interval()
            changed = cutter.pushCutter(f, i, t)
            output.append({"triangle": ti, "ends": ends, "changed": changed, "interval": interval(i)})
    return output


def cutter_offset(ocl, name):
    c = getattr(ocl, name)(*CUTTERS[name])
    output = []
    for distance in [0., .15, .6]:
        offset = c.offsetCutter(distance)
        drops = []
        for t in triangles(ocl)[:3]:
            p = ocl.CLPoint(.2, .1, -2)
            drops.append({"changed": offset.dropCutter(p, t), "cl": clpoint(p)})
        output.append({"distance": distance, "properties": cutter_properties(offset), "drops": drops})
    return output


def cutter_stl(ocl, name):
    c, s = getattr(ocl, name)(*CUTTERS[name]), surface(ocl)
    output = []
    for xyz in [(0, 0, -2), (1, 1, -2), (5, 5, -2), (0, 0, 10)]:
        p = ocl.CLPoint(*xyz)
        output.append({"input": xyz, "changed": c.dropCutterSTL(p, s), "cl": clpoint(p)})
    return output


for _name in CUTTERS:
    for _method in ["vertexDrop", "facetDrop", "edgeDrop", "dropCutter"]:
        register("cutter.%s.%s" % (_name, _method), partial(cutter_drop, name=_name, method=_method),
                 [_name + ".__init__", "MillingCutter." + _method,
                  "MillingCutter.getRadius", "MillingCutter.getDiameter", "MillingCutter.getLength", "MillingCutter.__str__"])
    register("cutter.%s.pushCutter" % _name, partial(cutter_push, name=_name), ["MillingCutter.pushCutter"])
    if _name in ["CylCutter", "BallCutter", "BullCutter", "ConeCutter"]:
        register("cutter.%s.offsetCutter" % _name, partial(cutter_offset, name=_name), ["MillingCutter.offsetCutter"])
    if _name in ["CylCutter", "BallCutter"]:
        register("cutter.%s.dropCutterSTL" % _name, partial(cutter_stl, name=_name), [_name + ".dropCutterSTL"])


def batch_drop(ocl, name, threads):
    s, c = surface(ocl), getattr(ocl, name)(*CUTTERS[name])
    b = ocl.BatchDropCutter()
    b.setThreads(threads)
    b.setBucketSize(2)
    b.setSTL(s)
    b.setCutter(c)
    inputs = [ocl.CLPoint(x, y, z) for x, y, z in
              [(0, 0, -2), (1, 1, -2), (-2.3, 0, -2), (6, 6, -2), (0, 0, 5)]]
    # Original Boost.Python returns opaque Triangle_base objects here; their
    # coordinates cannot be inspected. Compare candidate counts per query.
    under = [len(b.getTrianglesUnderCutter(p, c)) for p in inputs]
    for p in inputs:
        b.appendPoint(p)
    before = [clpoint(p) for p in b.getCLPoints()]
    b.run()
    after = [clpoint(p) for p in b.getCLPoints()]
    calls = b.getCalls()
    b.run()
    second_calls = b.getCalls()
    if threads > 1:
        # Native counting is not synchronized in every historical build.
        # Keep geometry exact; validate counter bounds without flaky equality.
        calls = {"integer": isinstance(calls, int), "valid": 0 <= calls <= len(inputs) * s.size()}
        second_calls = {"integer": isinstance(second_calls, int), "valid": 0 <= second_calls <= len(inputs) * s.size()}
    return {"threads": b.getThreads(), "bucket": b.getBucketSize(), "under": under,
            "before": before, "after": after, "calls": calls,
            "second": [clpoint(p) for p in b.getCLPoints()], "second_calls": second_calls,
            "inputs": [clpoint(p) for p in inputs]}


_batch_drop_members = ["BatchDropCutter." + m for m in
                       ["__init__", "setThreads", "getThreads", "setBucketSize", "getBucketSize", "setSTL", "setCutter",
                        "appendPoint", "getTrianglesUnderCutter", "run", "getCLPoints", "getCalls"]]
for _name in ["CylCutter", "BallCutter", "BullCutter", "ConeCutter"]:
    for _threads in [1, 2]:
        register("batch_drop.%s.threads%d" % (_name, _threads), partial(batch_drop, name=_name, threads=_threads), _batch_drop_members)


def path_drop(ocl, name, shape, minimum):
    s, c, path = surface(ocl), ocl.BallCutter(1.2, 6.), ocl.Path()
    if shape == "line":
        path.append(ocl.Line(ocl.Point(-3, -.4, 7), ocl.Point(0, -.4, 7)))
        path.append(ocl.Line(ocl.Point(0, -.4, 7), ocl.Point(3, .8, 7)))
    else:
        path.append(ocl.Arc(ocl.Point(2, 0, 7), ocl.Point(0, 2, 7), ocl.Point(0, 0, 7), True))
    b = getattr(ocl, name)()
    b.setCutter(c)
    b.setSTL(s)
    b.setSampling(.5)
    if name == "AdaptivePathDropCutter":
        b.setMinSampling(.0625)
        b.setCosLimit(.995)
    b.setPath(path)
    b.setZ(minimum)
    z = b.getZ()
    b.minimumZ = minimum + .1
    property_z = [b.minimumZ, b.getZ()]
    b.minimumZ = minimum
    before = [clpoint(p) for p in b.getCLPoints()]
    b.run()
    after = [clpoint(p) for p in b.getCLPoints()]
    b.run()
    return {"z": z, "property_z": property_z, "before": before, "after": after,
            "second": [clpoint(p) for p in b.getCLPoints()],
            "sampling": b.getSampling() if name == "AdaptivePathDropCutter" else .5}


for _name in ["PathDropCutter", "AdaptivePathDropCutter"]:
    _members = ["__init__", "setCutter", "setSTL", "setSampling", "setPath", "getZ", "setZ", "minimumZ", "run", "getCLPoints"]
    if _name == "AdaptivePathDropCutter":
        _members += ["setMinSampling", "setCosLimit", "getSampling"]
    for _shape in ["line", "arc"]:
        for _minimum in [-2., 2.]:
            register("path_drop.%s.%s.z%g" % (_name, _shape, _minimum), partial(path_drop, name=_name, shape=_shape, minimum=_minimum),
                     [_name + "." + m for m in _members])


def batch_push(ocl, axis, name):
    s, c, b = surface(ocl), getattr(ocl, name)(*CUTTERS[name]), ocl.BatchPushCutter()
    getattr(b, "set%sDirection" % axis)()
    b.setThreads(1)
    b.setBucketSize(2)
    b.setSTL(s)
    b.setCutter(c)
    fs = []
    for v in [-2.5, -.5, 0., 1.5, 5.]:
        ends = [(-4, v, 1), (4, v, 1)] if axis == "X" else [(v, -4, 1), (v, 4, 1)]
        fs.append(ocl.Fiber(*(ocl.Point(*p) for p in ends)))
    overlaps = [len(b.getOverlapTriangles(f)) for f in fs]
    for f in fs:
        b.appendFiber(f)
    b.run()
    return {"threads": b.getThreads(), "bucket": b.getBucketSize(), "calls": b.getCalls(), "overlaps": overlaps,
            "fibers": [fiber(f) for f in b.getFibers()], "points": [clpoint(p) for p in b.getCLPoints()],
            "inputs": [fiber(f) for f in fs]}


for _axis in ["X", "Y"]:
    for _name in ["CylCutter", "BallCutter", "BullCutter", "ConeCutter"]:
        register("batch_push.%s.%s" % (_axis, _name), partial(batch_push, axis=_axis, name=_name),
                 ["BatchPushCutter." + m for m in ["__init__", "set" + _axis + "Direction", "setThreads", "getThreads", "setBucketSize",
                  "getBucketSize", "setSTL", "setCutter", "getOverlapTriangles", "appendFiber", "run", "getCalls", "getFibers", "getCLPoints"]])


def waterline(ocl, name, method, canonical=False):
    s, c, w = surface(ocl), ocl.BallCutter(.6, 6.), getattr(ocl, name)()
    w.setThreads(1)
    w.setCutter(c)
    w.setSTL(s)
    w.setSampling(.4)
    if name == "AdaptiveWaterline":
        w.setMinSampling(.1)
    w.setZ(1.)
    getattr(w, method)()
    def loops():
        if canonical:
            return sorted(contour(loop) for loop in w.getLoops())
        return [[point(p) for p in loop] for loop in w.getLoops()]
    first = {"loops": loops(),
             "x": [fiber(f) for f in w.getXFibers()], "y": [fiber(f) for f in w.getYFibers()]}
    w.reset()
    reset = {"loops": loops(),
             "x": [fiber(f) for f in w.getXFibers()], "y": [fiber(f) for f in w.getYFibers()]}
    w.setZ(1.5)
    getattr(w, method)()
    return {"threads": w.getThreads(), "first": first, "reset": reset,
            "second": {"loops": loops(),
                       "x": [fiber(f) for f in w.getXFibers()], "y": [fiber(f) for f in w.getYFibers()]}}


for _name in ["Waterline", "AdaptiveWaterline"]:
    for _method in ["run", "run2"]:
        _members = ["__init__", "setThreads", "getThreads", "setCutter", "setSTL", "setSampling", "setZ", _method, "reset", "getLoops", "getXFibers", "getYFibers"]
        if _name == "AdaptiveWaterline":
            _members.append("setMinSampling")
        register("waterline.%s.%s" % (_name, _method), partial(waterline, name=_name, method=_method), [_name + "." + m for m in _members])
        register("waterline.%s.%s.canonical_geometry" % (_name, _method), partial(waterline, name=_name, method=_method, canonical=True), [_name + "." + m for m in _members])


def weave(ocl, name):
    w = getattr(ocl, name)()
    # Explicit overlapping square grid guarantees connected contour topology.
    for axis in ["X", "Y"]:
        for v in [-.75, 0., .75]:
            ends = [(-2, v, 1), (2, v, 1)] if axis == "X" else [(v, -2, 1), (v, 2, 1)]
            f = ocl.Fiber(*(ocl.Point(*p) for p in ends))
            f.addInterval(ocl.Interval(.25, .75))
            w.addFiber(f)
    w.build()
    types = ["CL", "CL_DONE", "ADJ", "TWOADJ", "INT", "FULLINT"]
    result = {"str": str(w), "count": w.numVertices(), "vertices": sorted(point(p) for p in w.getVertices()),
              "edges": sorted([point(a), point(b)] for a, b in w.getEdges()),
              "types": {t: sorted(point(p) for p in w.getVerticesByType(getattr(ocl.WeaveVertexType, t))) for t in types},
              "cl": sorted(point(p) for p in w.getCLVertices()), "int": sorted(point(p) for p in w.getINTVertices())}
    w.printGraph()
    w.face_traverse()
    result["loops"] = sorted(contour(loop) for loop in w.getLoops())
    assert result["count"] == len(result["vertices"]) and result["count"] > 0
    assert result["edges"] and result["loops"]
    assert all(p in result["vertices"] for loop in result["loops"] for p in loop)
    return result


for _name in ["SimpleWeave", "SmartWeave"]:
    register("weave." + _name, partial(weave, name=_name), [_name + ".__init__"] + ["Weave." + m for m in
             ["addFiber", "build", "__str__", "numVertices", "getVertices", "getEdges", "getVerticesByType", "getCLVertices", "getINTVertices", "printGraph", "face_traverse", "getLoops"]])


def line_filter(ocl, tolerance, shape):
    f = ocl.LineCLFilter()
    f.setTolerance(tolerance)
    inputs = {"straight": [(0, 0, 0), (1, 0, 0), (2, 0, 0), (3, 0, 0)],
              "bend": [(0, 0, 0), (1, 0, .01), (2, 0, 0), (3, 1, .5), (4, 2, 1)],
              "duplicate": [(0, 0, 0), (0, 0, 0), (1, 0, 0), (1, 0, 0), (2, 1, 0)]}[shape]
    for n, xyz in enumerate(inputs):
        cc = ocl.CCPoint(*xyz)
        cc.type = ocl.CCType.VERTEX if n % 2 else ocl.CCType.FACET
        f.addCLPoint(ocl.CLPoint(*xyz, cc))
    before = [clpoint(p) for p in f.getCLPoints()]
    f.run()
    after = [clpoint(p) for p in f.getCLPoints()]
    f.run()
    return {"before": before, "after": after, "second": [clpoint(p) for p in f.getCLPoints()]}


for _shape in ["straight", "bend", "duplicate"]:
    for _tol in [.001, .1]:
        register("line_filter.%s.%g" % (_shape, _tol), partial(line_filter, shape=_shape, tolerance=_tol),
                 ["LineCLFilter." + m for m in ["__init__", "setTolerance", "addCLPoint", "getCLPoints", "run"]])


def cl_surface(ocl):
    s, c, obj = surface(ocl), ocl.BallCutter(1., 6.), ocl.CutterLocationSurface(4.)
    obj.setSTL(s)
    obj.setCutter(c)
    obj.setSampling(.5)
    obj.setMinSampling(.1)
    before = sorted(point(p) for p in obj.getVertices())
    obj.run()
    return {"before": before, "after": sorted(point(p) for p in obj.getVertices()),
            "edges": sorted([point(a), point(b)] for a, b in obj.getEdges()), "str": str(obj)}


register("cl_surface", cl_surface, ["CutterLocationSurface." + m for m in
         ["__init__", "setSTL", "setCutter", "setSampling", "setMinSampling", "run", "getVertices", "getEdges", "__str__"]])


def tsp(ocl):
    obj = ocl.TSPSolver()
    inputs = [(0, 0), (2, .1), (3, 2), (-.5, 3), (.7, .9)]
    for x, y in inputs:
        obj.addPoint(x, y)
    obj.run()
    first = {"output": list(obj.getOutput()), "length": obj.getLength()}
    tour = first["output"]
    assert len(tour) == len(inputs) + 1 and tour[0] == tour[-1]
    assert sorted(tour[:-1]) == list(range(len(inputs)))
    geometric_length = sum(math.hypot(inputs[a][0] - inputs[b][0], inputs[a][1] - inputs[b][1])
                           for a, b in zip(tour, tour[1:]))
    assert math.isclose(first["length"], geometric_length, rel_tol=1e-12)
    obj.reset()
    reset = list(obj.getOutput())
    for x, y in [(0, 0), (3, 0), (0, 4)]:
        obj.addPoint(x, y)
    obj.run()
    second = {"output": list(obj.getOutput()), "length": obj.getLength()}
    assert reset == []
    assert math.isclose(second["length"], 12., rel_tol=1e-12)
    assert sorted(second["output"][:-1]) == [0, 1, 2]
    return {"first": first, "reset": reset, "second": second}


register("tsp", tsp, ["TSPSolver." + m for m in ["__init__", "addPoint", "run", "getOutput", "getLength", "reset"]])


def zigzag(ocl, direction):
    obj = ocl.ZigZag()
    obj.setDirection(ocl.Point(*direction))
    obj.setOrigin(ocl.Point(.2, -.1, 0))
    obj.setStepOver(.5)
    for xyz in [(-2, -1, 0), (3, -1, 0), (3, 2, 0), (-2, 2, 0)]:
        obj.addPoint(ocl.Point(*xyz))
    obj.run()
    first = [point(p) for p in obj.getOutput()]
    obj.run()
    return {"str": str(obj), "first": first, "second": [point(p) for p in obj.getOutput()]}


for _direction in [(1, 0, 0), (0, 1, 0), (1, 1, 0)]:
    register("zigzag.%s" % str(_direction), partial(zigzag, direction=_direction), ["ZigZag." + m for m in
             ["__init__", "setDirection", "setOrigin", "setStepOver", "addPoint", "run", "getOutput", "__str__"]])


def numeric(ocl):
    # version strings identify builds rather than geometry behavior; verify shape.
    v = ocl.version()
    return {"eps": ocl.eps(), "epsF": [ocl.epsF(v) for v in [0., 1., -1., 1.e-8, 1.e8]],
            "epsD": [ocl.epsD(v) for v in [0., 1., -1., 1.e-8, 1.e8]],
            "version_string": isinstance(v, str) and bool(v),
            "max_threads_positive": isinstance(ocl.max_threads(), int) and ocl.max_threads() >= 1}


register("module.numeric", numeric, ["eps", "epsF", "epsD", "version", "max_threads"])


def collection_contract(value):
    """Expose concrete Python container and element APIs, without addresses."""
    return {"type": type(value).__name__, "length": len(value),
            "elements": [{"type": type(v).__name__,
                          "members": sorted(n for n in dir(v) if not n.startswith("_"))}
                         for v in value[:2]]}


def return_contracts(ocl):
    s, c = surface(ocl), ocl.BallCutter(.6, 6.)
    result = {}
    b = ocl.BatchDropCutter()
    b.setThreads(1)
    b.setSTL(s)
    b.setCutter(c)
    p = ocl.CLPoint(0, 0, -2)
    result["BatchDropCutter.getTrianglesUnderCutter"] = collection_contract(b.getTrianglesUnderCutter(p, c))
    b.appendPoint(p)
    b.run()
    result["BatchDropCutter.getCLPoints"] = collection_contract(b.getCLPoints())
    push = ocl.BatchPushCutter()
    push.setXDirection()
    push.setThreads(1)
    push.setCutter(c)
    push.setSTL(s)
    f = ocl.Fiber(ocl.Point(-4, 0, 1), ocl.Point(4, 0, 1))
    result["BatchPushCutter.getOverlapTriangles"] = collection_contract(push.getOverlapTriangles(f))
    push.appendFiber(f)
    push.run()
    result["BatchPushCutter.getCLPoints"] = collection_contract(push.getCLPoints())
    result["BatchPushCutter.getFibers"] = collection_contract(push.getFibers())
    w = ocl.Waterline()
    w.setThreads(1)
    w.setSTL(s)
    w.setCutter(c)
    w.setSampling(.5)
    w.setZ(1.)
    w.run()
    result["Waterline.getLoops"] = collection_contract(w.getLoops())
    result["Waterline.getXFibers"] = collection_contract(w.getXFibers())
    result["Waterline.getYFibers"] = collection_contract(w.getYFibers())
    cl = ocl.CutterLocationSurface(4.)
    result["CutterLocationSurface.getVertices"] = collection_contract(cl.getVertices())
    result["CutterLocationSurface.getEdges"] = collection_contract(cl.getEdges())
    try:
        obj = ocl.MillingCutter()
    except Exception:
        result["MillingCutter.constructible"] = False
    else:
        result["MillingCutter.constructible"] = True
    return result


register("return_contracts", return_contracts, ["MillingCutter.__init__"])


def constructor_contract(ocl, name):
    cls = getattr(ocl, name)
    try:
        obj = cls()
    except Exception:
        return {"constructible": False}
    return {"constructible": True, "members": sorted(n for n in dir(obj) if not n.startswith("_"))}


for _name in ["AdaptivePathDropCutter_base", "AdaptiveWaterline_base", "BatchDropCutter_base",
              "BatchPushCutter_base", "LineCLFilter_base", "PathDropCutter_base", "Waterline_base", "ZigZag_base", "Weave"]:
    register("constructor." + _name, partial(constructor_contract, name=_name), [_name + ".__init__"])


NEW_API_CASES = {
    "algorithms.weave.SimpleWeave": "SimpleWeave/Weave were not exported by the original pip wheel.",
    "algorithms.weave.SmartWeave": "SmartWeave/Weave were not exported by the original pip wheel.",
    "algorithms.tsp": "TSPSolver was not exported by the original pip wheel.",
    "algorithms.constructor.Weave": "Weave was not exported by the original pip wheel; candidate abstract constructor availability is checked.",
}

REFERENCE_UNAVAILABLE = {
    name: {"exception": "AttributeError", "reason": reason}
    for name, reason in NEW_API_CASES.items()
}


def tsp_reset_then_destroy(ocl):
    """Ordinary lifecycle must not double-delete the graph after reset.

    Deliberately isolated by the runner: the unfixed candidate aborted here.
    The reset/refill/run scenario above cannot detect this dangling pointer.
    """
    solver = ocl.TSPSolver()
    for x, y in [(0., 0.), (3., 0.), (0., 4.)]:
        solver.addPoint(x, y)
    solver.run()
    solver.reset()
    del solver
    return {"destroyed_after_reset": True}


register("tsp.reset_then_destroy", tsp_reset_then_destroy,
         ["TSPSolver.__init__", "TSPSolver.addPoint", "TSPSolver.run", "TSPSolver.reset"])
REFERENCE_UNAVAILABLE["algorithms.tsp.reset_then_destroy"] = {
    "exception": "AttributeError", "reason": "TSPSolver is absent from the original pip wheel."
}
