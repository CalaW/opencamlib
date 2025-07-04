from pathlib import Path

from opencamlib import camvtk, ocl

if __name__ == "__main__":
    s = ocl.STLSurf()
    print(s)
    myscreen = camvtk.VTKScreen()
    stl = camvtk.STLSurf(Path(__file__).parent / "../../stl/demo.stl")
    print("STL surface read")
    myscreen.addActor(stl)
    stl.SetWireframe()

    polydata = stl.src.GetOutput()
    camvtk.vtkPolyData2OCLSTL(polydata, s)

    print(s)
    myscreen.render()
    myscreen.iren.Start()

    # raw_input("Press Enter to terminate")
