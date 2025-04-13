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

#ifndef FIBER_PY_H
#define FIBER_PY_H

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "fiber.hpp"

namespace ocl {

class Fiber_py : public Fiber {
public:
    Fiber_py() : Fiber() {}
    Fiber_py(const Point& p1, const Point& p2) : Fiber(p1, p2) {}
    Fiber_py(const Fiber& f) : Fiber(f) {}

    pybind11::list getInts() const {
        pybind11::list l;
        for (const auto& i : ints) {
            l.append(i);
        }
        return l;
    }
};

} // namespace ocl

#endif // FIBER_PY_H
