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
#ifndef ADAPTIVEWATERLINE_PY_H
#define ADAPTIVEWATERLINE_PY_H

#include "adaptivewaterline.hpp"
#include "fiber_py.hpp"

#include <iostream>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

namespace ocl {

/// \brief python wrapper for AdaptiveWaterline
class AdaptiveWaterline_py : public AdaptiveWaterline {
public:
    AdaptiveWaterline_py() : AdaptiveWaterline() {}
    ~AdaptiveWaterline_py() { std::cout << "~AdaptiveWaterline_py()\n"; }

    /// return loop as a list of lists to python
    py::list py_getLoops() const {
        py::list loop_list;
        for (const auto& loop : loops) {
            py::list point_list;
            for (const auto& p : loop) {
                point_list.append(p);
            }
            loop_list.append(point_list);
        }
        return loop_list;
    }

    /// return a list of xfibers to python
    py::list getXFibers() const {
        py::list flist;
        for (const Fiber& f : xfibers) {
            if (!f.empty()) {
                Fiber_py f2(f);
                flist.append(f2);
            }
        }
        return flist;
    }

    /// return a list of yfibers to python
    py::list getYFibers() const {
        py::list flist;
        for (const Fiber& f : yfibers) {
            if (!f.empty()) {
                Fiber_py f2(f);
                flist.append(f2);
            }
        }
        return flist;
    }
};

} // end namespace ocl

#endif // ADAPTIVEWATERLINE_PY_H
