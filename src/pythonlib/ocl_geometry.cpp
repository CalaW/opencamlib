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

#include "bbox.hpp"
#include "ccpoint.hpp"
#include "clpoint.hpp"
#include "ellipse.hpp"
#include "ellipseposition.hpp"
#include "ostream_str.hpp"
#include "path.hpp"
#include "point.hpp"
#include "stlreader.hpp"
#include "stlsurf.hpp"
#include "triangle.hpp"

namespace py = pybind11;
using namespace ocl;

void export_geometry(py::module_& m) {
    py::class_<Point>(m, "Point")
        .def(py::init<>())
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
        .def("isInside", py::overload_cast<const Triangle&>(&Point::isInside, py::const_))
        .def("isInside",
             py::overload_cast<const Point&, const Point&>(&Point::isInside, py::const_))
        .def("xyDistance", &Point::xyDistance)
        .def("__str__", &ostream_str<Point>)
        .def_readwrite("x", &Point::x)
        .def_readwrite("y", &Point::y)
        .def_readwrite("z", &Point::z);

    py::class_<CLPoint, Point>(m, "CLPoint")
        .def(py::init<>())
        .def(py::init<CLPoint>())
        .def(py::init<double, double, double>())
        .def(py::init<double, double, double, CCPoint&>())
        .def("__str__", &CLPoint::str)
        .def("cc", &CLPoint::getCC)
        .def("getCC", &CLPoint::getCC);

    py::class_<CCPoint, Point>(m, "CCPoint")
        .def(py::init<>())
        .def(py::init<CCPoint>())
        .def(py::init<double, double, double>())
        .def("__str__", &CCPoint::str)
        .def_readwrite("type", &CCPoint::type);

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

    py::class_<Triangle>(m, "Triangle")
        .def(py::init<Point, Point, Point>())
        .def("getPoints", [](const Triangle& t) { return std::to_array(t.p); })
        .def("__str__", &ostream_str<Triangle>)
        .def_property_readonly("p", [](const Triangle& t) { return std::to_array(t.p); })
        .def_readonly("n", &Triangle::n);

    py::class_<STLSurf>(m, "STLSurf")
        .def(py::init<>())
        .def("addTriangle", &STLSurf::addTriangle)
        .def("__str__", &ostream_str<STLSurf>)
        .def("size", &STLSurf::size)
        .def("rotate", &STLSurf::rotate)
        .def("getBounds",
             [](const STLSurf& stl) {
                 return std::array<double, 6>{stl.bb.minpt.x, stl.bb.maxpt.x, stl.bb.minpt.y,
                                              stl.bb.maxpt.y, stl.bb.minpt.z, stl.bb.maxpt.z};
             })
        .def("getTriangles", [](const STLSurf& stl) { return stl.tris; })
        .def_readonly("tris", &STLSurf::tris)
        .def_readonly("bb", &STLSurf::bb);

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

    py::class_<Path>(m, "Path")
        .def(py::init<>())
        .def(py::init<Path>())
        .def("getSpans",
             [](const Path& p) {
                 py::list spans;
                 for (auto span : p.span_list) {
                     if (span->type() == LineSpanType)
                         spans.append(static_cast<LineSpan*>(span)->line);
                     else if (span->type() == ArcSpanType)
                         spans.append(static_cast<ArcSpan*>(span)->arc);
                 }
                 return spans;
             })
        .def("getTypeSpanPairs",
             [](const Path& p) {
                 py::list slist;
                 for (auto span : p.span_list) {
                     if (span->type() == LineSpanType) {
                         auto tuple =
                             py::make_tuple(span->type(), static_cast<LineSpan*>(span)->line);
                         slist.append(tuple);
                     } else if (span->type() == ArcSpanType) {
                         auto tuple =
                             py::make_tuple(span->type(), static_cast<ArcSpan*>(span)->arc);
                         slist.append(tuple);
                     }
                 }
                 return slist;
             })
        .def("append", py::overload_cast<const Line&>(&Path::append))
        .def("append", py::overload_cast<const Arc&>(&Path::append));
}
