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
#ifndef TRIANGLE_PY_H
#define TRIANGLE_PY_H

#include <pybind11/pybind11.h>

#include <sstream>

#include "triangle.hpp"

namespace py = pybind11;

namespace ocl {

/// \brief python wrapper for Triangle
class Triangle_py : public Triangle {
public:
    // Default constructor
    Triangle_py() : Triangle() {}

    // Construct from three points
    Triangle_py(const Point& p0, const Point& p1, const Point& p2) : Triangle(p0, p1, p2) {}

    // Copy constructor
    Triangle_py(const Triangle_py& t) : Triangle(t) {}

    // Cast-down constructor
    Triangle_py(const Triangle& t) : Triangle(t) {}

    // String representation
    std::string str() const {
        std::ostringstream o;
        o << *this;
        return o.str();
    }

    // Returns a list of the vertices to Python
    py::list getPoints() const {
        py::list plist;
        for (const auto& vertex : p) {
            plist.append(vertex);
        }
        return plist;
    }
};

} // namespace ocl

#endif // TRIANGLE_PY_H
