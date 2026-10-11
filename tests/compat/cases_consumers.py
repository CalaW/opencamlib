# SPDX-License-Identifier: LGPL-2.1-or-later
# Extracted FreeCAD functions: Copyright 2025 Dimitrios Pana,
# Copyright 2016 Brad Collette; 2019 Russell Johnson and Brad Collette;
# Copyright 2020 Russell Johnson. See CONSUMERS.md for full provenance.
"""Pinned consumer functions and independently written BlenderCAM call fixtures."""
import math
import time
from functools import partial
from types import SimpleNamespace

# AST-extracted function bodies. Only docstrings/comments and formatting removed.
_FREECAD_FUNCTIONS = """
def batch_dropcutter(stl, cutter, polylines, min_z, threads=None):
    ocl = _get_ocl()
    bdc = ocl.BatchDropCutter()
    bdc.setSTL(stl)
    bdc.setCutter(cutter)
    if threads is not None and threads > 0:
        bdc.setThreads(threads)
    total_points = 0
    for line in polylines:
        for pt in line:
            bdc.appendPoint(ocl.CLPoint(pt[0], pt[1], min_z))
            total_points += 1
    t0 = time.time()
    bdc.run()
    t1 = time.time()
    Path.Log.debug('batch_dropcutter: {} points in {:.3f}s'.format(total_points, t1 - t0))
    results = []
    for cl in bdc.getCLPoints():
        results.append((cl.x, cl.y, cl.z))
    return results

def path_dropcutter(stl, cutter, polylines, min_z, sampling):
    ocl = _get_ocl()
    ocl_path = ocl.Path()
    for line in polylines:
        if len(line) < 2:
            continue
        for i in range(len(line) - 1):
            p1 = ocl.Point(line[i][0], line[i][1], min_z)
            p2 = ocl.Point(line[i + 1][0], line[i + 1][1], min_z)
            ocl_path.append(ocl.Line(p1, p2))
    pdc = ocl.PathDropCutter()
    pdc.setSTL(stl)
    pdc.setCutter(cutter)
    pdc.setZ(min_z)
    pdc.setSampling(sampling)
    pdc.setPath(ocl_path)
    t0 = time.time()
    pdc.run()
    t1 = time.time()
    Path.Log.debug('path_dropcutter: {:.3f}s'.format(t1 - t0))
    return [(cl.x, cl.y, cl.z) for cl in pdc.getCLPoints()]

def adaptive_path_dropcutter(stl, cutter, polylines, min_z, sampling, min_sampling=None):
    ocl = _get_ocl()
    ocl_path = ocl.Path()
    for line in polylines:
        if len(line) < 2:
            continue
        for i in range(len(line) - 1):
            p1 = ocl.Point(line[i][0], line[i][1], min_z)
            p2 = ocl.Point(line[i + 1][0], line[i + 1][1], min_z)
            ocl_path.append(ocl.Line(p1, p2))
    if min_sampling is None:
        min_sampling = sampling / 10.0
    apdc = ocl.AdaptivePathDropCutter()
    apdc.setSTL(stl)
    apdc.setCutter(cutter)
    apdc.setZ(min_z)
    apdc.setSampling(sampling)
    apdc.setMinSampling(min_sampling)
    apdc.setPath(ocl_path)
    t0 = time.time()
    apdc.run()
    t1 = time.time()
    Path.Log.debug('adaptive_path_dropcutter: {:.3f}s'.format(t1 - t0))
    return [(cl.x, cl.y, cl.z) for cl in apdc.getCLPoints()]

def waterline(stl, cutter, sampling, z, threads=None, timer=None):
    ocl = _get_ocl()
    wl = ocl.Waterline()
    wl.setSTL(stl)
    wl.setCutter(cutter)
    wl.setSampling(sampling)
    wl.setZ(z)
    if threads is not None and threads > 0:
        wl.setThreads(threads)
    t0 = time.time()
    wl.run()
    t1 = time.time()
    if timer:
        timer('waterline_z{:.3f}'.format(z), t1 - t0)
    raw_loops = wl.getLoops()
    loops = []
    for raw_loop in raw_loops:
        loop = [(pt.x, pt.y, pt.z) for pt in raw_loop]
        loops.append(loop)
    Path.Log.debug('waterline z={:.3f}: {} loops in {:.3f}s'.format(z, len(loops), t1 - t0))
    return loops

def adaptive_waterline(stl, cutter, sampling, min_sampling, z, threads=None, timer=None):
    ocl = _get_ocl()
    awl = ocl.AdaptiveWaterline()
    awl.setSTL(stl)
    awl.setCutter(cutter)
    awl.setSampling(sampling)
    awl.setMinSampling(min_sampling)
    awl.setZ(z)
    if threads is not None and threads > 0:
        awl.setThreads(threads)
    t0 = time.time()
    awl.run()
    t1 = time.time()
    if timer:
        timer('adaptive_waterline_z{:.3f}'.format(z), t1 - t0)
    raw_loops = awl.getLoops()
    loops = []
    for raw_loop in raw_loops:
        loop = [(pt.x, pt.y, pt.z) for pt in raw_loop]
        loops.append(loop)
    Path.Log.debug('adaptive_waterline z={:.3f}: {} loops in {:.3f}s'.format(z, len(loops), t1 - t0))
    return loops

def waterline_stack(stl, cutter, sampling, min_sampling, min_z, max_z, step_down, adaptive=False, depth_offset=0.0, threads=None, timer=None):
    from collections import OrderedDict
    epsilon = 0.001
    z_heights = []
    z = max_z
    while z >= min_z - 1e-06:
        z_heights.append(z)
        z -= step_down
    if z_heights and abs(z_heights[-1] - min_z) > 1e-06:
        z_heights.append(min_z)
    result = OrderedDict()
    t0 = time.time()
    for z in z_heights:
        zh = z + epsilon
        if adaptive:
            loops = adaptive_waterline(stl, cutter, sampling, min_sampling, zh, threads=threads, timer=timer)
        else:
            loops = waterline(stl, cutter, sampling, zh, threads=threads, timer=timer)
        if not loops:
            Path.Log.debug('waterline_stack: no loops at z={:.3f}, skipping'.format(zh))
            continue
        if abs(depth_offset) > 1e-09:
            offset_loops = []
            for loop in loops:
                offset_loops.append([(pt[0], pt[1], pt[2] + depth_offset) for pt in loop])
            result[zh] = offset_loops
        else:
            result[zh] = loops
    t1 = time.time()
    if timer:
        timer('waterline_stack_total', t1 - t0)
    Path.Log.debug('waterline_stack: {} heights, {} total loops in {:.3f}s'.format(len(z_heights), sum((len(v) for v in result.values())), t1 - t0))
    return result

def filter_cl_points(cl_points, tolerance):
    ocl = _get_ocl()
    if len(cl_points) < 3:
        return list(cl_points)
    f = ocl.LineCLFilter()
    f.setTolerance(tolerance)
    for pt in cl_points:
        f.addCLPoint(ocl.CLPoint(pt[0], pt[1], pt[2]))
    filter_start = time.perf_counter()
    f.run()
    filter_time = time.perf_counter() - filter_start
    result = [(cl.x, cl.y, cl.z) for cl in f.getCLPoints()]
    Path.Log.debug('filter_cl_points: {} -> {} points in {:.3f}s'.format(len(cl_points), len(result), filter_time))
    return result

def _planarDropCutScan(self, pdc, A, B):
    x1, y1 = A
    x2, y2 = B
    path = ocl.Path()
    p1 = ocl.Point(x1, y1, 0)
    p2 = ocl.Point(x2, y2, 0)
    lo = ocl.Line(p1, p2)
    path.append(lo)
    pdc.setPath(path)
    pdc.run()
    CLP = pdc.getCLPoints()
    PNTS = [FreeCAD.Vector(p.x, p.y, p.z) for p in CLP]
    return PNTS

def _planarCircularDropCutScan(self, pdc, Arc, cMode):
    path = ocl.Path()
    sp, ep, cp = Arc
    p1 = ocl.Point(sp[0], sp[1], 0)
    p2 = ocl.Point(ep[0], ep[1], 0)
    C = ocl.Point(cp[0], cp[1], 0)
    ao = ocl.Arc(p1, p2, C, cMode)
    path.append(ao)
    pdc.setPath(path)
    pdc.run()
    CLP = pdc.getCLPoints()
    return [FreeCAD.Vector(p.x, p.y, p.z) for p in CLP]

def _planarGetPDC(self, stl, finalDep, SampleInterval, cutter):
    pdc = ocl.PathDropCutter()
    pdc.setSTL(stl)
    pdc.setCutter(cutter)
    pdc.setZ(finalDep)
    pdc.setSampling(SampleInterval)
    return pdc

def _waterlineAdaptiveScan(self, stl, smplInt, minSmplInt, zheights, depOfst):
    msg = translate('Waterline', ": Steps below the model's top Face will be the only ones processed.")
    Path.Log.info('Waterline ' + msg)
    awl = ocl.AdaptiveWaterline()
    awl.setSTL(stl)
    awl.setCutter(self.cutter)
    awl.setSampling(smplInt)
    awl.setMinSampling(minSmplInt)
    adapt_loops = []
    for zh in zheights:
        awl.setZ(zh)
        awl.run()
        temp_loops = awl.getLoops()
        if not temp_loops:
            newPropMsg = translate('PathWaterline', 'Step Down above model. Skipping height : ')
            newPropMsg += '{} mm'.format(zh)
            FreeCAD.Console.PrintWarning(newPropMsg + '\\n')
            continue
        for loop in temp_loops:
            fc_loop = [FreeCAD.Vector(P.x, P.y, P.z + depOfst) for P in loop]
            adapt_loops.append(fc_loop)
    return adapt_loops

def _makeSafeCutter(self):
    if self.safe:
        self.diameter = self.diameter * 1.25
        if self.flatRadius == 0.0:
            self.flatRadius = self.diameter * 0.25
        elif self.flatRadius > 0.0:
            self.flatRadius = self.flatRadius * 1.25

def _oclCylCutter(self):
    if self.diameter == -1.0 or self.cutEdgeHeight == -1.0:
        return
    self.oclTool = self.ocl.CylCutter(self.diameter, self.cutEdgeHeight + self.lengthOffset)

def _oclBallCutter(self):
    if self.diameter == -1.0 or self.cutEdgeHeight == -1.0:
        return
    self.tiltCutter = True
    if self.cutEdgeHeight == 0:
        self.cutEdgeHeight = self.diameter / 2
    self.oclTool = self.ocl.BallCutter(self.diameter, self.cutEdgeHeight + self.lengthOffset)

def _oclBullCutter(self):
    if self.diameter == -1.0 or self.flatRadius == -1.0 or self.cutEdgeHeight == -1.0:
        return
    self.oclTool = self.ocl.BullCutter(self.diameter, self.diameter / 2 - self.flatRadius, self.cutEdgeHeight + self.lengthOffset)

def _oclConeCutter(self):
    if self.diameter == -1.0 or self.cutEdgeAngle == -1.0 or self.cutEdgeHeight == -1.0:
        return
    self.oclTool = self.ocl.ConeCutter(self.diameter, self.cutEdgeAngle / 2, self.lengthOffset)
"""


def _freecad(ocl):
    """Execute authentic function bodies with only host logging/vector stubs."""
    noop = lambda *args, **kwargs: None
    env = {
        '_get_ocl': lambda: ocl, 'ocl': ocl, 'time': time,
        'Path': SimpleNamespace(Log=SimpleNamespace(debug=noop, info=noop)),
        'FreeCAD': SimpleNamespace(Vector=lambda x, y, z: (x, y, z),
                                   Console=SimpleNamespace(PrintWarning=noop)),
        'translate': lambda context, message: message,
    }
    exec(_FREECAD_FUNCTIONS, env)
    return env


def _mesh(ocl, scale=1.0, skin=0.0):
    """Synthetic 6 mm pyramid with a flat skirt; all data is locally authored."""
    corners = [(-3, -3, 0), (3, -3, 0), (3, 3, 0), (-3, 3, 0)]
    apex = (0, 0, 3)
    faces = [(corners[i], corners[(i + 1) % 4], apex) for i in range(4)]
    faces += [((-6, -6, 0), (6, -6, 0), (6, 6, 0)),
              ((-6, -6, 0), (6, 6, 0), (-6, 6, 0))]
    surf = ocl.STLSurf()
    for face in faces:
        pts = [ocl.Point(x * scale, y * scale, (z + skin) * scale) for x, y, z in face]
        surf.addTriangle(ocl.Triangle(*pts))
    return surf


def _coords(points):
    return [[p.x, p.y, p.z] for p in points]


def _blender_cutter(ocl, kind, skin):
    # Meter-valued operation settings and formulas from pinned ocl_sample.
    diameter = 0.002
    tip = math.radians(60) / 2
    d_mm = (diameter + skin * 2) * 1000
    if kind == 'END':
        return ocl.CylCutter(d_mm, 10)
    if kind == 'BALLNOSE':
        return ocl.BallCutter(d_mm, 10)
    if kind == 'VCARVE':
        return ocl.ConeCutter(d_mm, tip, (diameter / math.tan(tip)) / 2)
    if kind == 'CYLCONE':
        return ocl.CylConeCutter((0.0008 / 2 + skin) * 2000, d_mm, tip)
    if kind == 'BALLCONE':
        return ocl.BallConeCutter((0.0004 + skin) * 2000, d_mm, tip)
    if kind == 'BULLNOSE':
        return ocl.BullCutter(d_mm, 0.0003 * 1000, 10)
    raise ValueError(kind)


def blender_sample(ocl, kind, skin=0.0):
    # Mesh vertices enter get_oclSTL in meters and receive the Z skin offset.
    # The mesh helper has mm coordinates, so constructing it at scale=1 gives
    # precisely the same result as 0.001-meter vertices times OCL_SCALE=1000.
    surf = _mesh(ocl, skin=skin * 1000)
    cutter = _blender_cutter(ocl, kind, skin)
    chunks = [[[-0.004, -0.001, 99], [-0.002, -0.001, 99], [0, -0.001, 99]],
              [[0.002, 0.001, 99], [0.004, 0.001, 99], [0.007, 0.007, 99]]]
    results = []
    # Second request reuses the cached STL, as use_cached_mesh=True does.
    for min_z in (-0.001, 0.0015):
        bdc = ocl.BatchDropCutter()
        bdc.setSTL(surf)
        bdc.setCutter(cutter)
        for chunk in chunks:
            for x, y, _ in chunk:
                bdc.appendPoint(ocl.CLPoint(x * 1000, y * 1000, min_z * 1000))
        bdc.run()
        samples = bdc.getCLPoints()
        # pointSamplesFromOCL and chunkPointSamplesFromOCL preserve XY/order.
        resampled = []
        index = 0
        for chunk in chunks:
            resampled.append([[x, y, samples[index + i].z / 1000]
                              for i, (x, y, _) in enumerate(chunk)])
            index += len(chunk)
        results.append({'minimum_z_m': min_z, 'chunks_m': resampled,
                        'raw_mm': _coords(samples)})
    return results


def freecad_batch(ocl, threads=None):
    fc = _freecad(ocl)
    lines = [[], [(-4, -1, 99), (-2, -1, 99), (0, -1, 99)],
             [(2, 1, 99), (4, 1, 99), (7, 7, 99)]]
    surf, cutter = _mesh(ocl), ocl.BallCutter(2, 10)
    return {str(z): fc['batch_dropcutter'](surf, cutter, lines, z, threads=threads)
            for z in (-1, 1.5)}


def freecad_path(ocl, adaptive=False):
    fc = _freecad(ocl)
    lines = [[], [(0, 0, 99)], [(-4, -1, 99), (0, -1, 99), (4, -1, 99)],
             [(4, 1, 99), (-4, 1, 99)]]
    surf, cutter = _mesh(ocl), ocl.BallCutter(2, 10)
    name = 'adaptive_path_dropcutter' if adaptive else 'path_dropcutter'
    return {str(z): fc[name](surf, cutter, lines, z, 0.5) for z in (-1, 1.5)}


def freecad_filter(ocl, tolerance):
    fc = _freecad(ocl)
    inputs = [[], [(0, 0, 0)], [(0, 0, 0), (1, 0, 0)],
              [(0, 0, 0), (0.5, 0, 0), (1, 0, 0), (1.5, 0, 0.01),
               (2, 0, 0), (3, 0, 1), (4, 0, 1)]]
    return [fc['filter_cl_points'](points, tolerance) for points in inputs]


def freecad_legacy_lines_arcs(ocl):
    fc = _freecad(ocl)
    # FreeCAD retains these dependencies; the original binding does not own them.
    surf, cutter = _mesh(ocl), ocl.BallCutter(2, 10)
    pdc = fc['_planarGetPDC'](None, surf, -1, 0.5, cutter)
    outputs = []
    for a, b in [((-4, -1), (4, -1)), ((4, 1), (-4, 1)), ((-4, -1), (4, -1))]:
        outputs.append(fc['_planarDropCutScan'](None, pdc, a, b))
    arc = ((2, 0), (0, 2), (0, 0))
    for clockwise in (False, True):
        outputs.append(fc['_planarCircularDropCutScan'](None, pdc, arc, clockwise))
    return outputs


def freecad_waterline(ocl, adaptive=False, threads=None):
    fc = _freecad(ocl)
    stack = fc['waterline_stack'](_mesh(ocl), ocl.BallCutter(1, 10),
                                 0.6, 0.1, 0.5, 3.5, 1.2, adaptive=adaptive,
                                 depth_offset=0.125, threads=threads)
    # Preserve layer and point ordering as actually returned to FreeCAD.
    return [[z, loops] for z, loops in stack.items()]


def freecad_legacy_adaptive_layers(ocl):
    fc = _freecad(ocl)
    host = SimpleNamespace(cutter=ocl.BallCutter(1, 10))
    return fc['_waterlineAdaptiveScan'](host, _mesh(ocl), 0.6, 0.1,
                                       [3.5, 1.5, 0.5, 1.5], 0.125)


def waterline_reset_layers(ocl, adaptive=False):
    # Supplemental state contract: reset between layers versus new objects.
    cls = ocl.AdaptiveWaterline if adaptive else ocl.Waterline
    surf, cutter = _mesh(ocl), ocl.BallCutter(1, 10)
    wl = cls()
    wl.setSTL(surf)
    wl.setCutter(cutter)
    wl.setSampling(0.6)
    if adaptive:
        wl.setMinSampling(0.1)
    outputs = []
    for z in (1.5, 0.5, 1.5):
        wl.setZ(z)
        wl.run()
        outputs.append([_coords(loop) for loop in wl.getLoops()])
        wl.reset()
    return outputs


CASES = {}
COVERAGE = {}
_MESH = ['STLSurf.__init__', 'STLSurf.addTriangle', 'Triangle.__init__', 'Point.__init__']
_BATCH = ['BatchDropCutter.__init__', 'BatchDropCutter.setSTL',
          'BatchDropCutter.setCutter', 'BatchDropCutter.appendPoint',
          'CLPoint.__init__', 'BatchDropCutter.run', 'BatchDropCutter.getCLPoints',
          'CLPoint.x', 'CLPoint.y', 'CLPoint.z']


def _case(name, fn, members):
    CASES['consumers.' + name] = fn
    COVERAGE['consumers.' + name] = sorted(set(members))


for kind, cls in [('END', 'CylCutter'), ('BALLNOSE', 'BallCutter'),
                  ('VCARVE', 'ConeCutter'), ('CYLCONE', 'CylConeCutter'),
                  ('BALLCONE', 'BallConeCutter'), ('BULLNOSE', 'BullCutter')]:
    for skin in (0.0, 0.0001):
        _case('blendercam.' + kind.lower() + ('.skin' if skin else '.plain'),
              partial(blender_sample, kind=kind, skin=skin),
              _MESH + _BATCH + [cls + '.__init__'])

for threads in (None, 1, 2):
    _case('freecad.batch.threads_' + str(threads), partial(freecad_batch, threads=threads),
          _MESH + _BATCH + ['BallCutter.__init__'] +
          (['BatchDropCutter.setThreads'] if threads else []))
for adaptive in (False, True):
    cls = 'AdaptivePathDropCutter' if adaptive else 'PathDropCutter'
    _case('freecad.' + cls, partial(freecad_path, adaptive=adaptive),
          _MESH + ['BallCutter.__init__', 'Path.__init__', 'Path.append', 'Line.__init__'] +
          [cls + '.' + member for member in ('__init__', 'setSTL', 'setCutter', 'setZ',
                                           'setSampling', 'setPath', 'run', 'getCLPoints')] +
          ([cls + '.setMinSampling'] if adaptive else []))
    cls = 'AdaptiveWaterline' if adaptive else 'Waterline'
    members = (_MESH + ['BallCutter.__init__'] + [cls + '.' + member for member in
                ('__init__', 'setSTL', 'setCutter', 'setSampling', 'setZ', 'run', 'getLoops')] +
                ([cls + '.setMinSampling'] if adaptive else []))
    _case('freecad.' + cls + '.stack', partial(freecad_waterline, adaptive=adaptive), members)
    _case('freecad.' + cls + '.threads',
          partial(freecad_waterline, adaptive=adaptive, threads=2), members + [cls + '.setThreads'])
    _case('waterline.' + cls + '.reset', partial(waterline_reset_layers, adaptive=adaptive),
          members + [cls + '.reset'])

_case('freecad.legacy.lines_arcs_reuse', freecad_legacy_lines_arcs,
      _MESH + ['BallCutter.__init__', 'Path.__init__', 'Path.append', 'Line.__init__',
               'Arc.__init__'] + ['PathDropCutter.' + m for m in
               ('__init__', 'setSTL', 'setCutter', 'setZ', 'setSampling', 'setPath', 'run', 'getCLPoints')])
_case('freecad.legacy.adaptive_layers_reuse', freecad_legacy_adaptive_layers,
      _MESH + ['BallCutter.__init__'] + ['AdaptiveWaterline.' + m for m in
               ('__init__', 'setSTL', 'setCutter', 'setSampling', 'setMinSampling', 'setZ', 'run', 'getLoops')])
for tolerance in (0.001, 0.1):
    _case('freecad.filter.' + str(tolerance), partial(freecad_filter, tolerance=tolerance),
          ['LineCLFilter.__init__', 'LineCLFilter.setTolerance', 'LineCLFilter.addCLPoint',
           'CLPoint.__init__', 'LineCLFilter.run', 'LineCLFilter.getCLPoints'])


def freecad_tool_mapping(ocl, kind, safe=False):
    fc = _freecad(ocl)
    # SurfaceSupport accepts CuttingEdgeAngle as float without conversion.
    # Use the common 90-degree V-bit setting, preserving that exact behavior.
    host = SimpleNamespace(ocl=ocl, diameter=2.0, flatRadius=0.7,
                           cutEdgeHeight=0.0 if kind == 'Ball' else 4.0,
                           cutEdgeAngle=90.0, lengthOffset=2.0, safe=safe,
                           tiltCutter=False, oclTool=None)
    fc['_makeSafeCutter'](host)
    fc['_ocl' + kind + 'Cutter'](host)
    cutter = host.oclTool
    raw = _freecad(ocl)['batch_dropcutter'](_mesh(ocl), cutter,
                   [[(-4, -1, 50), (-2, -1, 50), (0, -1, 50), (2, 1, 50), (7, 7, 50)]], -1)
    return {'diameter': cutter.getDiameter(), 'length': cutter.getLength(),
            'tilt_cutter': host.tiltCutter, 'points': raw}


for kind in ('Cyl', 'Ball', 'Bull', 'Cone'):
    for safe in (False, True):
        _case('freecad.tool_mapping.' + kind + ('.safe' if safe else '.normal'),
              partial(freecad_tool_mapping, kind=kind, safe=safe),
              _MESH + _BATCH + [kind + 'Cutter.__init__',
                               'MillingCutter.getDiameter', 'MillingCutter.getLength'])


def _canonical_loop(loop):
    """Rotate the origin, retaining every vertex, winding and closure status."""
    points = [tuple(point) for point in loop]
    if not points:
        return []
    closed = len(points) > 1 and points[0] == points[-1]
    if closed:
        points.pop()
    # Full rotated sequence breaks ties deterministically at repeated vertices.
    start = min(range(len(points)), key=lambda i: points[i:] + points[:i])
    rotated = points[start:] + points[:start]
    if closed:
        rotated.append(rotated[0])
    return [list(point) for point in rotated]


def _canonical_loops(loops):
    return sorted(_canonical_loop(loop) for loop in loops)


def _geometry_only(ocl, case, shape):
    result = CASES[case](ocl)
    if shape == 'stack':
        return [[height, _canonical_loops(loops)] for height, loops in result]
    if shape == 'layers':
        return [_canonical_loops(loops) for loops in result]
    return _canonical_loops(result)


# Keep original consumer output ordering as the primary test. These paired
# cases distinguish contour coordinate/winding parity from entry-point parity.
for name in list(CASES):
    if 'Waterline.stack' in name or 'Waterline.threads' in name:
        shape = 'stack'
    elif name.startswith('consumers.waterline.'):
        shape = 'layers'
    elif name == 'consumers.freecad.legacy.adaptive_layers_reuse':
        shape = 'loops'
    else:
        continue
    CASES[name + '.geometry'] = partial(_geometry_only, case=name, shape=shape)
    COVERAGE[name + '.geometry'] = COVERAGE[name]


def freecad_island_waterlines(ocl, adaptive=False):
    """Two distinct synthetic islands exercise separate contour components."""
    surf = ocl.STLSurf()
    for center_x in (-4, 4):
        corners = [(center_x - 3, -3, 0), (center_x + 3, -3, 0),
                   (center_x + 3, 3, 0), (center_x - 3, 3, 0)]
        for i in range(4):
            face = (corners[i], corners[(i + 1) % 4], (center_x, 0, 3))
            surf.addTriangle(ocl.Triangle(*(ocl.Point(*point) for point in face)))
    fc = _freecad(ocl)
    name = 'adaptive_waterline' if adaptive else 'waterline'
    if adaptive:
        return fc[name](surf, ocl.BallCutter(1, 10), 0.6, 0.1, 1.5)
    return fc[name](surf, ocl.BallCutter(1, 10), 0.6, 1.5)


for adaptive in (False, True):
    cls = 'AdaptiveWaterline' if adaptive else 'Waterline'
    name = 'consumers.freecad.' + cls + '.islands'
    CASES[name] = partial(freecad_island_waterlines, adaptive=adaptive)
    COVERAGE[name] = COVERAGE['consumers.freecad.' + cls + '.stack']
    CASES[name + '.geometry'] = partial(_geometry_only, case=name, shape='loops')
    COVERAGE[name + '.geometry'] = COVERAGE[name]
