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
#ifndef WATERLINE_PY_H
#define WATERLINE_PY_H

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include <iostream>

#include "fiber_py.hpp"
#include "waterline.hpp"

namespace py = pybind11;

namespace ocl {

/// Python wrapper for Waterline
class Waterline_py : public Waterline {
public:
    Waterline_py() : Waterline() {}
    ~Waterline_py() { std::cout << "~Waterline_py()\n"; }
    /// return loop as a list of lists to Python
    py::list py_getLoops() const {
        py::list loop_list;
        for (const auto& loop : this->loops) {
            py::list point_list;
            for (const auto& p : loop) {
                point_list.append(p);
            }
            loop_list.append(point_list);
        }
        return loop_list;
    }
    /// return a list of xfibers to Python
    py::list py_getXFibers() const {
        py::list flist;
        const std::vector<Fiber>& xfibers = *(subOp[0]->getFibers());
        for (const auto& f : xfibers) {
            Fiber_py f2(f);
            flist.append(f2);
        }
        return flist;
    }
    /// return a list of yfibers to Python
    py::list py_getYFibers() const {
        py::list flist;
        const std::vector<Fiber>& yfibers = *(subOp[1]->getFibers());
        for (const auto& f : yfibers) {
            Fiber_py f2(f);
            flist.append(f2);
        }
        return flist;
    }
};

} // end namespace ocl

#endif // WATERLINE_PY_H
