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
#ifndef BDC_PY_H
#define BDC_PY_H

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "batchdropcutter.hpp"

namespace ocl {

/// Python wrapper for BatchDropCutter using pybind11
class BatchDropCutter_py : public BatchDropCutter {
public:
    BatchDropCutter_py() : BatchDropCutter() {}

    /// Return CL-points to Python as a std::vector (automatically converted to a Python list)
    std::vector<CLPoint> getCLPoints_py() {
        std::vector<CLPoint> plist;
        for (const auto& p : *clpoints)
            plist.push_back(p);
        return plist;
    } // TODO use auto conversion

    /// Return triangles under cutter to Python.
    std::vector<Triangle> getTrianglesUnderCutter(CLPoint& cl, MillingCutter& cutter) {
        std::vector<Triangle> trilist;
        std::list<Triangle>* triangles_under_cutter = root->search_cutter_overlap(&cutter, &cl);
        for (const auto& t : *triangles_under_cutter)
            trilist.push_back(t);
        delete triangles_under_cutter;
        return trilist;
    }
};

} // end namespace ocl

#endif // BDC_PY_H
