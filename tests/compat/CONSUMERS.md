# Consumer compatibility provenance

Sources inspected on 2026-10-04, pinned to:

- BlenderCAM/Fabex: `ae5ab17ed7db880a389749c06f7e7aad48b96939`.
- FreeCAD: `cd403cb5a7ed50e50b3d2f587278164817573848`.

The case module runs offline. `_FREECAD_FUNCTIONS` embeds actual function bodies extracted with Python AST from the pinned sources. Docstrings/comments were removed and formatting regenerated with `ast.unparse`; executable statements are preserved. Host stubs supply logging, translation and tuple-valued FreeCAD vectors. OCL calls execute against each installed native extension. This tests the library boundary and the consumer's own flattening, conversion, filtering and layering logic. It does not launch the Blender or FreeCAD GUI, tessellate a Part shape, or validate downstream G-code/tool-controller behavior.

## Scenarios

- BlenderCAM: independently authored replicas of `get_oclSTL`, `ocl_sample`, `pointSamplesFromOCL`, and `chunkPointSamplesFromOCL` OCL call patterns. All six cutter branches (END, BALLNOSE, VCARVE, CYLCONE, BALLCONE, BULLNOSE) run with zero/nonzero skin; meter-to-mm conversion, angular conversion, constructor dimensions, mesh Z skin, minimum Z, input chunk/point ordering, and cached mesh reuse are preserved. Chunk outputs and raw samples are compared without rounding. A synthetic pyramid/skirt stands in for Blender's transformed mesh; Blender modifiers/transforms/cache invalidation and numpy allocation are outside scope.
- FreeCAD current generators: authentic `batch_dropcutter`, `path_dropcutter`, `adaptive_path_dropcutter`, `waterline`, `adaptive_waterline`, `waterline_stack`, and `filter_cl_points`. Exercise 1/2/default threads, short/empty polylines, ignored input Z, minimum Z, adaptive sampling default, collinear/bent filtering, multiple layers, overshoot/final depth, absent above-model contours, the 0.001 mm layer epsilon, and depth offsets. Preserve contour order and all returned coordinates. Separate two-island fixtures check that distinct contour components remain separate in fixed/adaptive waterline modes.
- FreeCAD retained operation methods: authentic `_planarGetPDC`, `_planarDropCutScan`, `_planarCircularDropCutScan`, `_waterlineAdaptiveScan`; reused drop-cutter paths in opposite directions, clockwise/counterclockwise arcs and repeated adaptive layers. No missing reset is added to the original consumer function.
- FreeCAD tool mapping: authentic `_makeSafeCutter`, `_oclCylCutter`, `_oclBallCutter`, `_oclBullCutter`, `_oclConeCutter`; normal and 25% buffered safe tools, flat-to-corner radius translation, ball edge-height fallback, tool length offsets and tilt marker. Cone uses the source's float-valued 90-degree CuttingEdgeAngle directly (source divides by two without radians conversion), faithfully preserving current behavior.
- Supplemental waterline state contract: explicit reset between layers, including returning to a previous Z. These cases exercise a library state contract; current inspected consumer source creates fresh objects or reuses without resetting.

All geometry and operation inputs are synthetic locally authored fixtures, not copyrighted application models. Success here establishes parity for these inputs and functions, not exhaustive whole-application compatibility.

## Source hashes

Hashes are SHA-256 of downloaded raw files before AST extraction (including original line endings).

| Pinned source | SHA-256 |
| --- | --- |
| [fabex/utilities/ocl_utils.py](https://github.com/vilemduha/blendercam/blob/ae5ab17ed7db880a389749c06f7e7aad48b96939/fabex/utilities/ocl_utils.py) | `c7966f7ddaf2eed689f8b382fee164a79609a785a82c4eff6ea180452b4ef123` |
| [fabex/constants.py](https://github.com/vilemduha/blendercam/blob/ae5ab17ed7db880a389749c06f7e7aad48b96939/fabex/constants.py) | `bf5c7b881736886a606ed46e98d921731f7299b7a16212351479266e167f43b7` |
| [src/Mod/CAM/Path/Base/Generator/surface_dropcutter.py](https://github.com/FreeCAD/FreeCAD/blob/cd403cb5a7ed50e50b3d2f587278164817573848/src/Mod/CAM/Path/Base/Generator/surface_dropcutter.py) | `8be7516aaef0e0bab6f06d893a7854f7b32e900009aa6a8a306cdfa31784dc7d` |
| [src/Mod/CAM/Path/Base/Generator/surface_waterline.py](https://github.com/FreeCAD/FreeCAD/blob/cd403cb5a7ed50e50b3d2f587278164817573848/src/Mod/CAM/Path/Base/Generator/surface_waterline.py) | `77e03c0c520255ed5372f16ff1bea9a5bcfb5b8c6c7a858dfc13e9f0c4e32544` |
| [src/Mod/CAM/Path/Base/Generator/surface_postprocess.py](https://github.com/FreeCAD/FreeCAD/blob/cd403cb5a7ed50e50b3d2f587278164817573848/src/Mod/CAM/Path/Base/Generator/surface_postprocess.py) | `9f0b03e05383cdc5910becef92d168eea6755b7c29040fefa679711e7e3310c6` |
| [src/Mod/CAM/Path/Base/Generator/surface_mesh.py](https://github.com/FreeCAD/FreeCAD/blob/cd403cb5a7ed50e50b3d2f587278164817573848/src/Mod/CAM/Path/Base/Generator/surface_mesh.py) | `d6f5e86025d65caf401135dae893bb8fd329f0652b6926569a51f45cffdf9553` |
| [src/Mod/CAM/Path/Op/Surface.py](https://github.com/FreeCAD/FreeCAD/blob/cd403cb5a7ed50e50b3d2f587278164817573848/src/Mod/CAM/Path/Op/Surface.py) | `a8a5ba0048fc91ce97c01e583d7a0c5265b9a06e0d3fd7b6b235a4e61b798794` |
| [src/Mod/CAM/Path/Op/Waterline.py](https://github.com/FreeCAD/FreeCAD/blob/cd403cb5a7ed50e50b3d2f587278164817573848/src/Mod/CAM/Path/Op/Waterline.py) | `704fb8c3c41193d8975e7665954a39f2dbdd590dc7d4be317426b1035a8335b9` |
| [src/Mod/CAM/Path/Op/SurfaceSupport.py](https://github.com/FreeCAD/FreeCAD/blob/cd403cb5a7ed50e50b3d2f587278164817573848/src/Mod/CAM/Path/Op/SurfaceSupport.py) | `d79e505d11e831bfe9cf8fefe3cf1539c820001ad928eac4a4971478612f154b` |

## License and attribution

The embedded FreeCAD function bodies are LGPL-2.1-or-later per their SPDX headers; the repository's COPYING provides LGPL 2.1. Preserve these notices on redistribution:

- Generator sources: Copyright 2025 Dimitrios Pana <dimitriospana75@gmail.com>; author Brad Collette (sliptonic), FreeCAD contributors.
- Surface.py: Copyright 2016 sliptonic <shopinthewoods@gmail.com>; contributor Russell Johnson (russ4262).
- Waterline.py: Copyright 2019 Russell Johnson <russ4262@gmail.com> and sliptonic <shopinthewoods@gmail.com>.
- SurfaceSupport.py: Copyright 2020 russ4262 <russ4262@gmail.com>.

BlenderCAM behavior was inspected but no BlenderCAM executable source or assets are embedded; those fixtures are independently authored call-pattern replicas. No external code is fetched or executed during test runs.

## Observed contour ordering and paired comparisons

On the local PyPI 2023.1.11 reference wheel and rewrite wheel, 28 of the first 35 consumer cases matched with the suite's 1e-10 numeric tolerance. Seven raw waterline/layer cases differed only in the cyclic origin of otherwise identical contours. All seven matched after rotating loop starts and sorting separate components, with winding, every vertex, loop closure, layers and coordinates preserved. Therefore each has an additional `.geometry` case; the original raw-order case remains the primary compatibility check and can fail. A geometry pass does **not** promise the same initial cutter position or exact downstream G-code sequence.

A reference-vs-reference subprocess pair for each of the seven raw contour cases showed no difference. Twenty additional independent reference subprocesses each for `consumers.freecad.Waterline.stack` and `consumers.freecad.legacy.adaptive_layers_reuse` also showed no ordering difference. This experiment does not establish baseline nondeterminism. The rewrite's different contour origins remain visible as compatibility differences, rather than being dismissed. No coordinates are rounded and winding is never reversed by normalization.

Two additional raw two-island cases also differ in contour entry point/component order; both paired geometry cases match. The complete consumer module has 46 cases (37 matches, 9 raw contour-order differences in local validation).
