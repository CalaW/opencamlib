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
#ifndef STLSURF_PY_H
#define STLSURF_PY_H

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <sstream>

#include "stlsurf.hpp"
#include "triangle_py.hpp"

namespace ocl {

/// STLSurf python wrapper
class STLSurf_py : public STLSurf {
public:
    /// default constructor
    STLSurf_py() : STLSurf() {}

    /// return list of all triangles to python
    std::vector<Triangle_py> getTriangles() const {
        std::vector<Triangle_py> tlist;
        for (const auto& t : tris) {
            tlist.push_back(Triangle_py(t));
        }
        return tlist;
    }

    /// return bounds in a list to python
    std::vector<double> getBounds() const {
        return {bb.minpt.x, bb.maxpt.x, bb.minpt.y, bb.maxpt.y, bb.minpt.z, bb.maxpt.z};
    }

    /// string output
    std::string str() const {
        std::ostringstream o;
        o << *this;
        return o.str();
    }
};

} // end namespace ocl

#endif // STLSURF_PY_H
