/*  $Id$
 *
 *  Copyright (c) 2010 Anders Wallin (anders.e.e.wallin "at" gmail.com).
 *
 *  This file is part of OpenCAMlib
 *  (see https://github.com/aewallin/opencamlib).
 *
 *  This program is free software: you can redistribute it and/or modify
 *  it under the terms of the GNU Lesser General Public License as published by
 *  the Free Software Foundation, either version 2.1 of the License, or
 *  (at your option) any later version.
 *
 *  This program is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU Lesser General Public License for more details.
 *
 *  You should have received a copy of the GNU Lesser General Public License
 *  along with this program. If not, see <http://www.gnu.org/licenses/>.
 */
#include <pybind11/operators.h>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "bbox.hpp"    // no python
#include "ccpoint.hpp" // no python
#include "clpoint.hpp" // no python
#include "ellipse.hpp" // no python
#include "ellipseposition.hpp"
#include "path_py.hpp"     // new-style wrapper
#include "point.hpp"       // contains no python-specific code
#include "stlreader.hpp"   // no python
#include "stlsurf_py.hpp"  // new-style wrapper
#include "triangle_py.hpp" // new-style python wrapper-class

namespace py = pybind11;
using namespace ocl;

void export_geometry(py::module_& m) {
    py::class_<Point>(m, "Point")
        .def(py::init<double, double, double>())
        .def(py::init<double, double>())
        .def(py::init<Point>())
        .def(py::self * double())
        .def(double() * py::self)
        .def(py::self - py::self)
        .def(py::self -= py::self)
        .def(py::self + py::self)
        .def(py::self += py::self)
        .def("norm", &Point::norm)
        .def("xyNorm", &Point::xyNorm)
        .def("normalize", &Point::normalize)
        .def("dot", &Point::dot)
        .def("cross", &Point::cross)
        .def("xRotate", &Point::xRotate)
        .def("yRotate", &Point::yRotate)
        .def("zRotate", &Point::zRotate)
        .def("isRight", &Point::isRight)
        // .def("isInside", &Point::isInside)
        // .def("isInsidePoints", &Point::isInside)
        .def("xyDistance", &Point::xyDistance)
        .def("__str__", &Point::str)
        .def_readwrite("x", &Point::x)
        .def_readwrite("y", &Point::y)
        .def_readwrite("z", &Point::z);

    py::class_<CLPoint>(m, "CLPoint") // FIXME: should inherit from Point
        .def(py::init<CLPoint>())
        .def(py::init<double, double, double>())
        .def(py::init<double, double, double, CCPoint&>())
        .def("__str__", &CLPoint::str)
        .def_readwrite("x", &CLPoint::x)
        .def_readwrite("y", &CLPoint::y)
        .def_readwrite("z", &CLPoint::z)
        .def("cc", &CLPoint::getCC)
        .def("getCC", &CLPoint::getCC);

    py::class_<CCPoint>(m, "CCPoint") // FIXME: CCPoint should inherit from Point
        .def(py::init<CCPoint>())
        .def(py::init<double, double, double>())
        .def("__str__", &CCPoint::str)
        .def_readwrite("type", &CCPoint::type)
        .def_readwrite("x", &CCPoint::x)
        .def_readwrite("y", &CCPoint::y)
        .def_readwrite("z", &CCPoint::z);

    py::enum_<CCType>(m, "CCType")
        .value("NONE", NONE)
        .value("VERTEX", VERTEX)
        .value("VERTEX_CYL", VERTEX_CYL)
        .value("EDGE", EDGE)
        .value("EDGE_SHAFT", EDGE_SHAFT)
        .value("EDGE_HORIZ", EDGE_HORIZ)
        .value("EDGE_CYL", EDGE_CYL)
        .value("EDGE_BALL", EDGE_BALL)
        .value("EDGE_CONE", EDGE_CONE)
        .value("EDGE_CONE_BASE", EDGE_CONE_BASE)
        .value("EDGE_HORIZ_CYL", EDGE_HORIZ_CYL)
        .value("EDGE_HORIZ_TOR", EDGE_HORIZ_TOR)
        .value("EDGE_POS", EDGE_POS)
        .value("EDGE_NEG", EDGE_NEG)
        .value("FACET", FACET)
        .value("FACET_TIP", FACET_TIP)
        .value("FACET_CYL", FACET_CYL)
        .value("ERROR", ERROR)
        .export_values();

    // Base class for Triangle_py
    py::class_<Triangle>(m, "Triangle_base");

    py::class_<Triangle_py, Triangle>(m, "Triangle")
        .def(py::init<Point, Point, Point>())
        .def("getPoints", &Triangle_py::getPoints)
        .def("__str__", &Triangle_py::str)
        .def_readonly("p", &Triangle_py::p)
        .def_readonly("n", &Triangle_py::n);

    // Base class for STLSurf_py
    py::class_<STLSurf>(m, "STLSurf_base").def(py::init<>());

    py::class_<STLSurf_py, STLSurf>(m, "STLSurf")
        .def(py::init<>())
        .def("addTriangle", &STLSurf_py::addTriangle)
        .def("__str__", &STLSurf_py::str)
        .def("size", &STLSurf_py::size)
        .def("rotate", &STLSurf_py::rotate)
        .def("getBounds", &STLSurf_py::getBounds)
        .def("getTriangles", &STLSurf_py::getTriangles)
        .def_readonly("tris", &STLSurf_py::tris)
        .def_readonly("bb", &STLSurf_py::bb);

    py::class_<STLReader>(m, "STLReader").def(py::init<const std::wstring&, STLSurf&>());

    py::class_<Bbox>(m, "Bbox")
        .def("isInside", &Bbox::isInside)
        .def_readonly("maxpt", &Bbox::maxpt)
        .def_readonly("minpt", &Bbox::minpt);

    // EllipsePosition and Ellipse for toroidal tool edge-tests
    py::class_<EllipsePosition>(m, "EllipsePosition")
        .def_readwrite("s", &EllipsePosition::s)
        .def_readwrite("t", &EllipsePosition::t)
        .def("setDiangle", &EllipsePosition::setDiangle)
        .def("__str__", &EllipsePosition::str);

    py::class_<Ellipse>(m, "Ellipse")
        .def(py::init<Point&, double, double, double>())
        .def("ePoint", &Ellipse::ePoint)
        .def("oePoint", &Ellipse::oePoint)
        .def("normal", &Ellipse::normal);

    py::class_<Line>(m, "Line")
        .def(py::init<Point, Point>())
        .def(py::init<Line>())
        .def_readwrite("p1", &Line::p1)
        .def_readwrite("p2", &Line::p2);

    py::class_<Arc>(m, "Arc")
        .def(py::init<Point, Point, Point, bool>())
        .def(py::init<Arc>())
        .def_readwrite("p1", &Arc::p1)
        .def_readwrite("p2", &Arc::p2)
        .def_readwrite("c", &Arc::c)
        .def_readwrite("dir", &Arc::dir);

    py::enum_<SpanType>(m, "SpanType")
        .value("LineSpanType", LineSpanType)
        .value("ArcSpanType", ArcSpanType)
        .export_values();

    // Base class for Path_py
    py::class_<Path>(m, "Path_base");

    py::class_<Path_py, Path>(m, "Path")
        .def(py::init<>())
        .def(py::init<Path>())
        .def("getSpans", &Path_py::getSpans)
        .def("getTypeSpanPairs", &Path_py::getTypeSpanPairs)
        .def("append", (void(Path_py::*)(const Line&)) & Path_py::append)
        .def("append", (void(Path_py::*)(const Arc&)) & Path_py::append);
}
