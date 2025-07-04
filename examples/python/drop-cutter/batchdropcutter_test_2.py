import time
from pathlib import Path

from opencamlib import camvtk, ocl, pyocl

if __name__ == "__main__":
    print(ocl.version())
    myscreen = camvtk.VTKScreen()

    # read STL file from disk
    stl = camvtk.STLSurf(Path(__file__).parent / "../../../stl/gnu_tux_mod.stl")
    # stl = camvtk.STLSurf("../../../stl/beet_mm.stl")
    # stl = camvtk.STLSurf("../../../stl/Blade.stl")
    myscreen.addActor(stl)
    stl.SetWireframe()
    stl.SetColor((0.5, 0.5, 0.5))

    polydata = stl.src.GetOutput()
    s = ocl.STLSurf()
    camvtk.vtkPolyData2OCLSTL(polydata, s)
    print("STL surface read ", s.size(), " triangles")

    # Define a cutter
    length = 5
    cutter = ocl.BallCutter(1.4321, length)
    # cutter = ocl.CylCutter(1.123, length)
    # cutter = ocl.BullCutter(1.4123, 0.5, length)
    # cutter = ocl.ConeCutter(0.43, math.pi/7, length)
    print(cutter)

    # a grid of XY points where we run drop-cutter
    minx, dx, maxx = 0, 0.006, 9
    miny, dy, maxy = 0, 0.1, 12
    z = -5
    clpoints = pyocl.CLPointGrid(minx, dx, maxx, miny, dy, maxy, z)
    print("generated grid with", len(clpoints), " CL-points")

    # batchdropcutter
    bdc1 = ocl.BatchDropCutter()
    bdc1.setSTL(s)
    bdc1.setCutter(cutter)

    for p in clpoints:
        bdc1.appendPoint(p)

    t_before = time.perf_counter()
    print("threads=", bdc1.getThreads())
    bdc1.run()
    t_after = time.perf_counter()
    calctime = t_after - t_before
    print(f" done in {calctime:f} s")
    print(f" time/point {calctime / len(clpoints)} s")

    clpoints = bdc1.getCLPoints()

    print(len(clpoints), " cl points evaluated")

    print("rendering...")

    # draw the CL-points
    camvtk.drawCLPointCloud(myscreen, clpoints)

    print("done")

    myscreen.camera.SetPosition(3, 23, 15)
    myscreen.camera.SetFocalPoint(4, 5, 0)

    t = camvtk.Text()
    t.SetText("OpenCAMLib")
    t.SetPos((myscreen.width - 200, myscreen.height - 30))
    myscreen.addActor(t)

    t2 = camvtk.Text()
    stltext = f"{s.size()} triangles\n{len(clpoints)} CL-points\n{calctime:0.1f} seconds"
    t2.SetText(stltext)
    t2.SetPos((50, myscreen.height - 200))
    myscreen.addActor(t2)

    t3 = camvtk.Text()
    ctext = f"Cutter: {str(cutter)}"

    t3.SetText(ctext)
    t3.SetPos((50, myscreen.height - 250))
    myscreen.addActor(t3)

    myscreen.render()
    myscreen.iren.Start()
