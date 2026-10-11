"""Deterministic geometry observations for independently installed pip wheels.

Every case receives the extension module and returns JSON-compatible observations.
No candidate implementation is used as an oracle. API failures propagate to the
subprocess harness, apart from cases explicitly testing Python error contracts.
"""
import math
import struct
import tempfile
from pathlib import Path as FilePath

CASES = {}
COVERAGE = {}


def case(name, *members):
    def register(fn):
        CASES[name] = fn
        COVERAGE[name] = list(members)
        return fn
    return register


def point(p):
    return {"type": type(p).__name__, "xyz": [p.x, p.y, p.z]}


def contact(p):
    return {**point(p), "contact_type": int(p.type)}


def triangle(ocl):
    return ocl.Triangle(ocl.Point(-2, -1, 0), ocl.Point(3, -1, 1), ocl.Point(0, 4, 2))


def surface(ocl):
    s = ocl.STLSurf()
    s.addTriangle(triangle(ocl))
    s.addTriangle(ocl.Triangle(ocl.Point(-2, -1, 0), ocl.Point(0, 4, 2), ocl.Point(-3, 2, -1)))
    return s


def interval(ocl, lower, upper):
    i = ocl.Interval()
    a, b = ocl.CCPoint(lower, 1, 2), ocl.CCPoint(upper, 3, 4)
    a.type, b.type = ocl.CCType.EDGE, ocl.CCType.FACET
    i.updateLower(lower, a)
    i.updateUpper(upper, b)
    return i


def interval_data(i):
    return {"bounds": [i.lower, i.upper], "empty": i.empty(),
            "lower_cc": contact(i.lower_cc), "upper_cc": contact(i.upper_cc)}


def error_contract(operation):
    # Boost.Python.ArgumentError subclasses TypeError. Compare the Python error
    # contract without requiring binding-framework-specific exception names.
    try:
        result = operation()
    except Exception as exc:
        return {"accepted": False, "type_error": isinstance(exc, TypeError),
                "attribute_error": isinstance(exc, AttributeError),
                "value_error": isinstance(exc, ValueError)}
    return {"accepted": True, "result_type": type(result).__name__}


# Constructors, copying, inherited operations, and coordinate setters.
for clsname, args_list in (("Point", [(), (1.25, -2.5), (1.25, -2.5, 3.75)]),
                           ("CCPoint", [(), (1.25, -2.5, 3.75)]),
                           ("CLPoint", [(), (1.25, -2.5, 3.75)])):
    for args in args_list:
        @case(f"geometry.{clsname}.construct_{len(args)}", f"{clsname}.__init__", *(f"{clsname}.{c}" for c in "xyz"))
        def construct(ocl, clsname=clsname, args=args):
            p = getattr(ocl, clsname)(*args)
            return point(p)

    @case(f"geometry.{clsname}.copy", f"{clsname}.__init__", f"{clsname}.x")
    def copy_point(ocl, clsname=clsname):
        cls = getattr(ocl, clsname)
        p = cls(1, 2, 3)
        q = cls(p)
        q.x = 17
        return {"original": point(p), "copy": point(q)}

    @case(f"geometry.{clsname}.coordinates", *(f"{clsname}.{c}" for c in "xyz"))
    def coordinates(ocl, clsname=clsname):
        p = getattr(ocl, clsname)(1, 2, 3)
        p.x, p.y, p.z = -4.5, 6.25, -7.75
        return point(p)

    @case(f"geometry.{clsname}.string", f"{clsname}.__str__")
    def point_string(ocl, clsname=clsname):
        return str(getattr(ocl, clsname)(1.25, -2.5, 3.75))

    @case(f"geometry.{clsname}.inherited_metrics", f"{clsname}.norm", f"{clsname}.dot", f"{clsname}.cross")
    def inherited_metrics(ocl, clsname=clsname):
        p = getattr(ocl, clsname)(3, 4, 12)
        q = ocl.Point(-2, 5, 1)
        return {"norm": p.norm(), "dot": p.dot(q), "cross": point(p.cross(q))}

for method in ("norm", "xyNorm", "normalize"):
    for coords in ((3, 4, 12), (0, 0, 0), (-0.25, 0.5, -0.75)):
        @case(f"geometry.Point.{method}_{coords}", f"Point.{method}")
        def metric(ocl, method=method, coords=coords):
            p = ocl.Point(*coords)
            result = getattr(p, method)()
            return {"result": result, "point": point(p)}

for op in ("add", "sub", "mul", "rmul", "iadd", "isub", "imul", "eq", "ne"):
    @case(f"geometry.Point.operator_{op}", f"Point.__{op}__")
    def operator(ocl, op=op):
        p, q = ocl.Point(1, -2, 3), ocl.Point(-4, 5, 6)
        alias = p
        if op == "add": result = p + q
        elif op == "sub": result = p - q
        elif op == "mul": result = p * 2.5
        elif op == "rmul": result = -2.5 * p
        elif op == "iadd": p += q; result = p
        elif op == "isub": p -= q; result = p
        elif op == "imul": p *= 2.5; result = p
        elif op == "eq": return {"same": p == p, "copy": p == ocl.Point(p), "other": p == q}
        else: return {"same": p != p, "copy": p != ocl.Point(p), "other": p != q}
        return {"result": point(result), "source": point(p), "alias": point(alias),
                "same_object": result is alias}

for method in ("dot", "cross", "xyDistance"):
    @case(f"geometry.Point.{method}", f"Point.{method}")
    def binary_metric(ocl, method=method):
        p, q = ocl.Point(1.25, -2.5, 7), ocl.Point(-3, 0.75, -11)
        result = getattr(p, method)(q)
        return {"result": point(result) if method == "cross" else result, "source": point(p)}

for axis in "xyz":
    @case(f"geometry.Point.{axis}Rotate", f"Point.{axis}Rotate")
    def rotate_point(ocl, axis=axis):
        p = ocl.Point(1, 2, 3)
        result = getattr(p, axis + "Rotate")(math.pi / 3)
        forward = point(p)
        getattr(p, axis + "Rotate")(-math.pi / 3)
        return {"return": result, "forward": forward, "inverse": point(p)}

@case("geometry.Point.isRight", "Point.isRight")
def point_right(ocl):
    a, b = ocl.Point(0, 0, 3), ocl.Point(2, 0, 8)
    return [ocl.Point(*p).isRight(a, b) for p in ((1, -1, 0), (1, 1, 0), (1, 0, 0), (0, 0, 0), (1, -1e-16, 0))]

@case("geometry.Point.isInside_triangle", "Point.isInside", "Triangle.__init__")
def point_inside_triangle(ocl):
    a, b, c = ocl.Point(0, 0, 0), ocl.Point(4, 0, 1), ocl.Point(0, 4, 2)
    probes = [(1, 1, 0), (1, 1, 100), (0, 0, 0), (2, 0, 0), (2, 2, 0), (-1, 1, 0)]
    return [[ocl.Point(*p).isInside(t) for p in probes] for t in (ocl.Triangle(a, b, c), ocl.Triangle(c, b, a))]

@case("geometry.Point.isInside_segment", "Point.isInside")
def point_inside_segment(ocl):
    a, b = ocl.Point(0, 0, 0), ocl.Point(4, 0, 0)
    return [ocl.Point(*p).isInside(a, b) for p in ((0, 0, 0), (4, 0, 0), (2, 0, 0), (2, 100, 9), (-1, 0, 0), (5, 0, 0))]

@case("geometry.CCPoint.type", "CCPoint.type", "CCPoint.__init__")
def ccpoint_type(ocl):
    p = ocl.CCPoint(1, 2, 3)
    before = contact(p)
    p.type = ocl.CCType.EDGE_BALL
    q = ocl.CCPoint(p)
    p.type = ocl.CCType.FACET
    return {"default": before, "assigned": contact(p), "copy": contact(q)}

for method in ("cc", "getCC"):
    @case(f"geometry.CLPoint.{method}", "CLPoint.__init__", f"CLPoint.{method}")
    def clpoint_contact(ocl, method=method):
        cc = ocl.CCPoint(7, 8, 9)
        cc.type = ocl.CCType.EDGE
        p = ocl.CLPoint(1, 2, 3, cc)
        cc.x, cc.type = -10, ocl.CCType.ERROR
        first = getattr(p, method)()
        before = contact(first)
        first.y, first.type = -20, ocl.CCType.VERTEX
        return {"point": point(p), "before": before, "after": contact(getattr(p, method)()),
                "edited": contact(first)}

@case("geometry.CLPoint.copy_contact", "CLPoint.__init__", "CLPoint.getCC")
def clpoint_copy_contact(ocl):
    cc = ocl.CCPoint(7, 8, 9)
    cc.type = ocl.CCType.EDGE
    p = ocl.CLPoint(1, 2, 3, cc)
    q = ocl.CLPoint(p)
    p.x = -10
    return {"original": point(p), "copy": point(q), "contact": contact(q.getCC())}

for method in ("getPoints", "p", "n"):
    @case(f"geometry.Triangle.{method}", "Triangle.__init__", f"Triangle.{method}")
    def triangle_points(ocl, method=method):
        t = triangle(ocl)
        if method == "n": return point(t.n)
        result = t.getPoints() if method == "getPoints" else t.p
        before = [point(p) for p in result]
        result[0].x = -99
        again = t.getPoints() if method == "getPoints" else t.p
        return {"container_type": type(result).__name__, "points": before, "after": [point(p) for p in again]}

@case("geometry.Triangle.input_copy", "Triangle.__init__", "Triangle.getPoints")
def triangle_input_copy(ocl):
    a, b, c = ocl.Point(0, 0, 0), ocl.Point(3, 0, 1), ocl.Point(0, 3, 2)
    t = ocl.Triangle(a, b, c)
    a.x = 99
    return [point(p) for p in t.getPoints()]

@case("geometry.Triangle.string", "Triangle.__str__")
def triangle_string(ocl):
    return str(triangle(ocl))

@case("geometry.Triangle.normal_reference", "Triangle.n")
def triangle_normal_reference(ocl):
    t = triangle(ocl)
    n = t.n
    before = point(n)
    n.x = 41
    return {"before": before, "after": point(t.n)}

@case("geometry.STLSurf.empty", "STLSurf.__init__", "STLSurf.size", "STLSurf.getBounds", "STLSurf.getTriangles", "STLSurf.__str__")
def surface_empty(ocl):
    s = ocl.STLSurf()
    return {"size": s.size(), "bounds": s.getBounds(), "triangles": s.getTriangles(), "str": str(s)}

@case("geometry.STLSurf.addTriangle", "STLSurf.addTriangle", "STLSurf.size", "STLSurf.getBounds", "STLSurf.__str__")
def surface_add(ocl):
    s = ocl.STLSurf()
    result = s.addTriangle(triangle(ocl))
    first = s.getBounds()
    s.addTriangle(triangle(ocl))
    return {"return": result, "size": s.size(), "bounds": s.getBounds(), "first": first, "str": str(s)}

for method in ("getTriangles", "tris"):
    @case(f"geometry.STLSurf.{method}", f"STLSurf.{method}", "Triangle.getPoints", "Triangle.n")
    def surface_triangles(ocl, method=method):
        s = surface(ocl)
        result = s.getTriangles() if method == "getTriangles" else s.tris
        before = [[point(p) for p in t.getPoints()] for t in result]
        result[0].n.x = 61
        result.pop()
        after = s.getTriangles() if method == "getTriangles" else s.tris
        return {"container_type": type(after).__name__, "before": before, "size_after": s.size(),
                "normals_after": [point(t.n) for t in after]}

for axis in "xyz":
    @case(f"geometry.STLSurf.rotate_{axis}", "STLSurf.rotate", "STLSurf.getBounds", "STLSurf.getTriangles")
    def surface_rotate(ocl, axis=axis):
        s = surface(ocl)
        angles = [0., 0., 0.]
        angles["xyz".index(axis)] = math.pi / 2
        result = s.rotate(*angles)
        return {"return": result, "bounds": s.getBounds(),
                "triangles": [[point(p) for p in t.getPoints()] for t in s.getTriangles()]}

@case("geometry.STLSurf.rotate_composed", "STLSurf.rotate", "STLSurf.getBounds")
def surface_composed_rotation(ocl):
    s = surface(ocl)
    s.rotate(0.2, -0.3, 0.4)
    return {"bounds": s.getBounds(), "normals": [point(t.n) for t in s.getTriangles()]}

@case("geometry.Bbox.construct", "Bbox.__init__")
def bbox_construct(ocl):
    return error_contract(ocl.Bbox)

@case("geometry.Bbox.bounds", "STLSurf.bb", "Bbox.minpt", "Bbox.maxpt")
def bbox_bounds(ocl):
    s = surface(ocl)
    return {"min": point(s.bb.minpt), "max": point(s.bb.maxpt), "type": type(s.bb).__name__}

@case("geometry.Bbox.isInside", "Bbox.isInside")
def bbox_inside(ocl):
    s = surface(ocl)
    return [s.bb.isInside(ocl.Point(*p)) for p in ((0, 0, 0), (-3, -1, -1), (3, 4, 2), (-3.001, 0, 0), (0, 4.001, 0), (0, 0, 2.001))]

for attr in ("minpt", "maxpt"):
    @case(f"geometry.Bbox.{attr}_reference", f"Bbox.{attr}", "STLSurf.bb", "STLSurf.getBounds")
    def bbox_reference(ocl, attr=attr):
        s = surface(ocl)
        p = getattr(s.bb, attr)
        p.x = -41 if attr == "minpt" else 41
        return {"nested": point(getattr(s.bb, attr)), "bounds": s.getBounds()}

_ASCII = """solid deterministic
  facet normal 0 0 1
    outer loop
      vertex 0 0 0
      vertex 3 0 1
      vertex 0 3 2
    endloop
  endfacet
endsolid deterministic
"""
for encoding in ("ascii", "binary", "missing", "empty", "unicode"):
    @case(f"geometry.STLReader.{encoding}", "STLReader.__init__", "STLSurf.size", "STLSurf.getBounds", "STLSurf.getTriangles")
    def read_stl(ocl, encoding=encoding):
        with tempfile.TemporaryDirectory(prefix="ocl-compat-") as directory:
            filename = FilePath(directory) / ("测试.stl" if encoding == "unicode" else "fixture.stl")
            if encoding == "binary":
                data = b"deterministic binary fixture".ljust(80, b"\0") + struct.pack("<I", 1)
                data += struct.pack("<12fH", 0, 0, 1, 0, 0, 0, 3, 0, 1, 0, 3, 2, 0)
                filename.write_bytes(data)
            elif encoding == "empty": filename.write_bytes(b"")
            elif encoding != "missing": filename.write_text(_ASCII, encoding="ascii")
            s = ocl.STLSurf()
            reader = ocl.STLReader(str(filename), s)
            return {"reader_type": type(reader).__name__, "size": s.size(), "bounds": s.getBounds(),
                    "triangles": [[point(p) for p in t.getPoints()] for t in s.getTriangles()]}

@case("geometry.STLReader.append_existing", "STLReader.__init__", "STLSurf.size")
def reader_append(ocl):
    with tempfile.TemporaryDirectory(prefix="ocl-compat-") as directory:
        filename = FilePath(directory) / "fixture.stl"
        filename.write_text(_ASCII, encoding="ascii")
        s = surface(ocl)
        ocl.STLReader(str(filename), s)
        ocl.STLReader(str(filename), s)
        return {"size": s.size(), "bounds": s.getBounds()}

# Check receiver construction separately from numerical ellipse behavior.
@case("geometry.EllipsePosition.construct_accessibility", "EllipsePosition.__init__")
def ellipse_position_accessibility(ocl):
    return error_contract(ocl.EllipsePosition)

for member in ("s", "t", "setDiangle", "__str__"):
    @case(f"geometry.EllipsePosition.{member}_accessibility", f"EllipsePosition.{member}")
    def ellipse_position_member(ocl, member=member):
        descriptor = getattr(ocl.EllipsePosition, member)
        return {"exposed": True, "callable": callable(descriptor),
                "valid_receiver_available": error_contract(ocl.EllipsePosition)["accepted"]}

@case("geometry.Ellipse.construct", "Ellipse.__init__")
def ellipse_construct(ocl):
    center = ocl.Point(1, 2, 3)
    ellipse = ocl.Ellipse(center, 4, 2, 0.5)
    center.x = -99
    return {"type": type(ellipse).__name__}

for member in ("ePoint", "oePoint", "normal"):
    @case(f"geometry.Ellipse.{member}_invalid_position", f"Ellipse.{member}")
    def ellipse_invalid(ocl, member=member):
        ellipse = ocl.Ellipse(ocl.Point(1, 2, 3), 4, 2, 0.5)
        return error_contract(lambda: getattr(ellipse, member)(ocl.Point(1, 0, 0)))

for clsname in ("Line", "Arc"):
    @case(f"geometry.{clsname}.construct_copy", f"{clsname}.__init__", f"{clsname}.p1", f"{clsname}.p2")
    def span_construct(ocl, clsname=clsname):
        a, b = ocl.Point(1, 0, 0), ocl.Point(0, 1, 0)
        cls = getattr(ocl, clsname)
        p = cls(a, b) if clsname == "Line" else cls(a, b, ocl.Point(0, 0, 0), True)
        q = cls(p)
        a.x = 99
        q.p1.x = 17
        return {"original": [point(p.p1), point(p.p2)], "copy": [point(q.p1), point(q.p2)]}

    for member in (("p1", "p2") if clsname == "Line" else ("p1", "p2", "c", "dir")):
        @case(f"geometry.{clsname}.{member}_mutation", f"{clsname}.{member}")
        def span_mutation(ocl, clsname=clsname, member=member):
            cls = getattr(ocl, clsname)
            a, b = ocl.Point(1, 0, 0), ocl.Point(0, 1, 0)
            p = cls(a, b) if clsname == "Line" else cls(a, b, ocl.Point(0, 0, 0), True)
            if member == "dir":
                before = p.dir
                p.dir = False
                return {"before": before, "after": p.dir}
            alias = getattr(p, member)
            alias.x = -3
            nested = point(getattr(p, member))
            setattr(p, member, ocl.Point(7, 8, 9))
            return {"nested": nested, "assigned": point(getattr(p, member))}


def path_fixture(ocl):
    p = ocl.Path()
    line = ocl.Line(ocl.Point(0, 0, 0), ocl.Point(1, 0, 0))
    arc = ocl.Arc(ocl.Point(1, 0, 0), ocl.Point(0, 1, 0), ocl.Point(0, 0, 0), True)
    p.append(line)
    p.append(arc)
    return p


def span_data(s):
    data = {"type": type(s).__name__, "p1": point(s.p1), "p2": point(s.p2)}
    if type(s).__name__ == "Arc": data.update(center=point(s.c), direction=s.dir)
    return data

@case("geometry.Path.empty", "Path.__init__", "Path.getSpans", "Path.getTypeSpanPairs")
def path_empty(ocl):
    p = ocl.Path()
    return {"spans": p.getSpans(), "pairs": p.getTypeSpanPairs()}

@case("geometry.Path.getSpans", "Path.append", "Path.getSpans")
def path_spans(ocl):
    p = path_fixture(ocl)
    spans = p.getSpans()
    before = [span_data(s) for s in spans]
    spans[0].p1.x = 71
    spans.pop()
    return {"container_type": type(spans).__name__, "before": before, "after": [span_data(s) for s in p.getSpans()]}

@case("geometry.Path.getTypeSpanPairs", "Path.getTypeSpanPairs", "Path.append")
def path_pairs(ocl):
    pairs = path_fixture(ocl).getTypeSpanPairs()
    return {"container_type": type(pairs).__name__, "pairs": [[int(t), span_data(s)] for t, s in pairs],
            "pair_types": [type(p).__name__ for p in pairs]}

@case("geometry.Path.copy", "Path.__init__", "Path.append", "Path.getSpans")
def path_copy(ocl):
    p = path_fixture(ocl)
    q = ocl.Path(p)
    q.append(ocl.Line(ocl.Point(2, 0), ocl.Point(3, 0)))
    q.getSpans()[0].p1.x = 91
    return {"original": [span_data(s) for s in p.getSpans()], "copy": [span_data(s) for s in q.getSpans()]}

@case("geometry.Path.append_input_copy", "Path.append", "Path.getSpans")
def path_append_copy(ocl):
    p = ocl.Path()
    line = ocl.Line(ocl.Point(0, 0), ocl.Point(1, 0))
    result = p.append(line)
    line.p1.x = 81
    return {"return": result, "spans": [span_data(s) for s in p.getSpans()]}

for bounds in ((), (0., 0.), (0.25, 0.75), (-1., 2.)):
    @case(f"geometry.Interval.construct_{bounds}", "Interval.__init__", "Interval.lower", "Interval.upper", "Interval.lower_cc", "Interval.upper_cc", "Interval.empty", "Interval.__str__")
    def interval_construct(ocl, bounds=bounds):
        i = ocl.Interval(*bounds)
        return {**interval_data(i), "str": str(i)}

for method in ("updateLower", "updateUpper"):
    @case(f"geometry.Interval.{method}", f"Interval.{method}", "Interval.lower_cc", "Interval.upper_cc")
    def interval_update(ocl, method=method):
        i = ocl.Interval()
        observations = []
        for value, cc_type in ((0.5, "EDGE"), (0.25, "VERTEX"), (0.75, "FACET"), (0.5, "ERROR")):
            cc = ocl.CCPoint(value, 2, 3)
            cc.type = getattr(ocl.CCType, cc_type)
            result = getattr(i, method)(value, cc)
            cc.x = 99
            observations.append({"return": result, **interval_data(i)})
        return observations

@case("geometry.Interval.contact_reference", "Interval.lower_cc", "Interval.upper_cc")
def interval_contact_reference(ocl):
    i = interval(ocl, 0.25, 0.75)
    lower, upper = i.lower_cc, i.upper_cc
    lower.x, upper.y = 81, 91
    lower.type = ocl.CCType.ERROR
    return interval_data(i)

@case("geometry.Fiber.construct", "Fiber.__init__", "Fiber.p1", "Fiber.p2", "Fiber.dir", "Fiber.getInts")
def fiber_construct(ocl):
    a, b = ocl.Point(1, 2, 3), ocl.Point(4, 6, 3)
    f = ocl.Fiber(a, b)
    a.x = 91
    return {"p1": point(f.p1), "p2": point(f.p2), "dir": point(f.dir), "intervals": f.getInts()}

@case("geometry.Fiber.point", "Fiber.point")
def fiber_points(ocl):
    f = ocl.Fiber(ocl.Point(1, 2, 3), ocl.Point(4, 6, 3))
    return [point(f.point(t)) for t in (-0.5, 0, 0.25, 1, 1.5)]

for scenario, bounds in (("empty", [(0., 0.)]), ("disjoint", [(0.1, 0.2), (0.7, 0.9)]),
                         ("nested", [(0.1, 0.9), (0.2, 0.4)]), ("overlap", [(0.1, 0.4), (0.3, 0.8)]),
                         ("touching", [(0.1, 0.4), (0.4, 0.8)]), ("bridge", [(0.1, 0.2), (0.6, 0.8), (0.15, 0.7)])):
    @case(f"geometry.Fiber.addInterval_{scenario}", "Fiber.addInterval", "Fiber.getInts")
    def fiber_intervals(ocl, scenario=scenario, bounds=bounds):
        f = ocl.Fiber(ocl.Point(0, 0, 0), ocl.Point(10, 0, 0))
        observed = []
        for lower, upper in bounds:
            i = ocl.Interval() if scenario == "empty" else interval(ocl, lower, upper)
            result = f.addInterval(i)
            observed.append({"return": result, "intervals": [interval_data(j) for j in f.getInts()]})
        return observed

@case("geometry.Fiber.getInts_copy", "Fiber.getInts", "Fiber.addInterval")
def fiber_interval_copy(ocl):
    f = ocl.Fiber(ocl.Point(0, 0), ocl.Point(10, 0))
    i = interval(ocl, 0.25, 0.75)
    f.addInterval(i)
    i.updateUpper(0.95, i.upper_cc)
    result = f.getInts()
    result[0].lower_cc.x = 91
    result.pop()
    return [interval_data(j) for j in f.getInts()]

for member in ("p1", "p2", "dir"):
    @case(f"geometry.Fiber.{member}_reference", f"Fiber.{member}")
    def fiber_reference(ocl, member=member):
        f = ocl.Fiber(ocl.Point(0, 0), ocl.Point(10, 0))
        p = getattr(f, member)
        p.x = 81
        return {"property": point(getattr(f, member)), "midpoint": point(f.point(0.5))}

@case("geometry.Fiber.printInts", "Fiber.printInts")
def fiber_print(ocl):
    f = ocl.Fiber(ocl.Point(0, 0), ocl.Point(10, 0))
    f.addInterval(interval(ocl, 0.25, 0.75))
    return {"return": f.printInts()}

_ENUMS = {
    "CCType": "NONE VERTEX VERTEX_CYL EDGE EDGE_SHAFT EDGE_HORIZ EDGE_CYL EDGE_BALL EDGE_CONE EDGE_CONE_BASE EDGE_HORIZ_CYL EDGE_HORIZ_TOR EDGE_POS EDGE_NEG FACET FACET_TIP FACET_CYL ERROR".split(),
    "SpanType": ["LineSpanType", "ArcSpanType"],
    "WeaveVertexType": "CL CL_DONE ADJ TWOADJ INT FULLINT".split(),
}
for enum_name, names in _ENUMS.items():
    for name in names:
        @case(f"geometry.enum.{enum_name}.{name}", f"{enum_name}.{name}")
        def enum_value(ocl, enum_name=enum_name, name=name):
            cls = getattr(ocl, enum_name)
            value = getattr(cls, name)
            return {"value": int(value), "self_equal": value == getattr(cls, name),
                    "integer_equal": value == int(value), "type": type(value).__name__}

for name in ("LineSpanType", "ArcSpanType"):
    @case(f"geometry.enum.exported.{name}", name)
    def enum_export(ocl, name=name):
        return {"value": int(getattr(ocl, name)), "matches": getattr(ocl, name) == getattr(ocl.SpanType, name)}

# Public read-only attributes reject replacement; nested Point mutation has its
# own cases because writable children and read-only parents differ semantically.
for clsname, attrs in (("Triangle", ("p", "n")), ("Bbox", ("minpt", "maxpt")),
                       ("STLSurf", ("bb", "tris")), ("Interval", ("lower", "upper", "lower_cc", "upper_cc")),
                       ("Fiber", ("p1", "p2", "dir"))):
    for attr in attrs:
        @case(f"geometry.readonly.{clsname}.{attr}", f"{clsname}.{attr}")
        def readonly(ocl, clsname=clsname, attr=attr):
            if clsname == "Triangle": obj = triangle(ocl)
            elif clsname == "Bbox": obj = surface(ocl).bb
            elif clsname == "STLSurf": obj = surface(ocl)
            elif clsname == "Interval": obj = interval(ocl, 0.25, 0.75)
            else: obj = ocl.Fiber(ocl.Point(0, 0), ocl.Point(10, 0))
            if clsname == "Triangle" and attr == "p": value = [ocl.Point(), ocl.Point(), ocl.Point()]
            elif clsname == "STLSurf" and attr == "tris": value = []
            else: value = getattr(obj, attr)
            return error_contract(lambda: setattr(obj, attr, value))

for name, operation, coverage in (
    ("point_bad_coordinate", lambda o: o.Point("x", 1, 2), ["Point.__init__"]),
    ("point_bad_arity", lambda o: o.Point(1), ["Point.__init__"]),
    ("point_add_wrong_type", lambda o: o.Point(1, 2, 3) + 3, ["Point.__add__"]),
    ("point_dot_wrong_type", lambda o: o.Point(1, 2, 3).dot(3), ["Point.dot"]),
    ("point_assign_wrong_type", lambda o: setattr(o.Point(), "x", "x"), ["Point.x"]),
    ("ccpoint_assign_wrong_enum", lambda o: setattr(o.CCPoint(), "type", "EDGE"), ["CCPoint.type"]),
    ("surface_add_wrong_type", lambda o: o.STLSurf().addTriangle(o.Point()), ["STLSurf.addTriangle"]),
    ("path_append_wrong_type", lambda o: o.Path().append(o.Point()), ["Path.append"]),
    ("fiber_add_wrong_type", lambda o: o.Fiber(o.Point(0, 0), o.Point(1, 0)).addInterval(0.5), ["Fiber.addInterval"]),
    ("interval_update_wrong_contact", lambda o: o.Interval().updateUpper(0.5, o.Point()), ["Interval.updateUpper"]),
):
    @case(f"geometry.errors.{name}", *coverage)
    def invalid_argument(ocl, operation=operation):
        return error_contract(lambda: operation(ocl))

# Coverage exemptions are explicit and machine-readable. Calling native routines
# on invalid geometric inputs can abort the interpreter or read uninitialized data.
LIMITATIONS = {
    "Bbox.isInside(empty)": "Native assertion requires an initialized bounding box.",
    "Interval.__init__(reversed_bounds)": "Native assertion requires lower <= upper.",
    "Fiber.__init__(non_horizontal)": "Native assertion requires endpoints at equal z.",
    "Triangle.__init__(degenerate)": "Normal calculation for coincident vertices is not a stable numerical oracle.",
    "STLReader.__init__(truncated_binary)": "Native reader uses uninitialized float data on truncated facets.",
}

# Original Boost.Python bindings supply implicit default constructors. Numerical
# probes intentionally fail if a rewrite makes their receiver unreachable.
@case("geometry.EllipsePosition.default", "EllipsePosition.__init__", "EllipsePosition.s", "EllipsePosition.t", "EllipsePosition.__str__")
def ellipse_position_default(ocl):
    p = ocl.EllipsePosition()
    return {"s": p.s, "t": p.t, "str": str(p)}

@case("geometry.EllipsePosition.mutate", "EllipsePosition.s", "EllipsePosition.t")
def ellipse_position_mutate(ocl):
    p = ocl.EllipsePosition()
    p.s, p.t = 0.6, 0.8
    return {"s": p.s, "t": p.t, "str": str(p)}

for diangle in (0., 0.25, 0.75, 1., 1.5, 2., 2.5, 3., 3.5, 4.):
    @case(f"geometry.EllipsePosition.setDiangle_{diangle}", "EllipsePosition.setDiangle", "EllipsePosition.s", "EllipsePosition.t")
    def ellipse_diangle(ocl, diangle=diangle):
        p = ocl.EllipsePosition()
        result = p.setDiangle(diangle)
        return {"return": result, "s": p.s, "t": p.t, "norm_squared": p.s * p.s + p.t * p.t}

for method in ("ePoint", "oePoint", "normal"):
    for diangle in (0., 0.5, 1., 1.5, 2., 3.):
        @case(f"geometry.Ellipse.{method}_{diangle}", f"Ellipse.{method}", "Ellipse.__init__", "EllipsePosition.setDiangle")
        def ellipse_sample(ocl, method=method, diangle=diangle):
            center = ocl.Point(1, 2, 3)
            e = ocl.Ellipse(center, 4, 2, 0.5)
            p = ocl.EllipsePosition()
            p.setDiangle(diangle)
            before = point(getattr(e, method)(p))
            center.x = 91
            return {"value": before, "after_center_mutation": point(getattr(e, method)(p))}

@case("geometry.Ellipse.default_accessibility", "Ellipse.__init__")
def ellipse_default(ocl):
    # The default native ellipse has uninitialized radii; do not call its methods.
    return {"type": type(ocl.Ellipse()).__name__}

for clsname in ("Triangle_base", "STLSurf_base", "Fiber_base", "Path_base"):
    @case(f"geometry.base.{clsname}.construct", f"{clsname}.__init__")
    def base_construct(ocl, clsname=clsname):
        return {"type": type(getattr(ocl, clsname)()).__name__}

for clsname in ("Triangle", "Line", "Arc", "Fiber"):
    @case(f"geometry.{clsname}.implicit_default_constructor", f"{clsname}.__init__")
    def implicit_constructor(ocl, clsname=clsname):
        # Merely construct and destroy: implicit defaults have no useful geometry,
        # but accepting this overload is part of the historical Python contract.
        return {"type": type(getattr(ocl, clsname)()).__name__}

for enum_name in _ENUMS:
    COVERAGE[f"geometry.enum.{enum_name}.{_ENUMS[enum_name][0]}"].append(enum_name)

REFERENCE_UNAVAILABLE = {
    "geometry.CCPoint.inherited_metrics": {"exception": "AttributeError", "reason": "Original CCPoint exposes coordinates but does not inherit Point methods."},
    "geometry.CLPoint.inherited_metrics": {"exception": "AttributeError", "reason": "Original CLPoint exposes coordinates but does not inherit Point methods."},
    "geometry.Point.isInside_segment": {"exception": "AttributeError", "reason": "Point.isInside was not exported by the original Python binding."},
    "geometry.Point.isInside_triangle": {"exception": "AttributeError", "reason": "Point.isInside was not exported by the original Python binding."},
    "geometry.STLSurf.tris": {"exception": "TypeError", "reason": "Original tris property has no registered std::list<Triangle> converter; getTriangles is usable."},
    "geometry.Triangle.p": {"exception": "TypeError", "reason": "Original p property has no registered Point[3] converter; getPoints is usable."},
}

for enum_name, names in _ENUMS.items():
    @case(f"geometry.enum.{enum_name}.strings", enum_name)
    def enum_strings(ocl, enum_name=enum_name, names=names):
        cls = getattr(ocl, enum_name)
        return [{"name": name, "str": str(getattr(cls, name)), "repr": repr(getattr(cls, name))} for name in names]

    @case(f"geometry.enum.{enum_name}.numeric_constructor", enum_name)
    def enum_constructor(ocl, enum_name=enum_name, names=names):
        cls = getattr(ocl, enum_name)
        return [{"value": int(cls(int(getattr(cls, name)))), "equal": cls(int(getattr(cls, name))) == getattr(cls, name),
                 "hash": hash(cls(int(getattr(cls, name))))} for name in names]

    @case(f"geometry.enum.{enum_name}.unknown_numeric_value", enum_name)
    def enum_unknown(ocl, enum_name=enum_name):
        cls = getattr(ocl, enum_name)
        return error_contract(lambda: cls(9999))
