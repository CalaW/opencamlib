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

#ifndef ZIGZAG_PY_H
#define ZIGZAG_PY_H

#include <pybind11/pybind11.h>

#include "zigzag.hpp"

namespace py = pybind11;

namespace ocl {
/// Python wrapper for ZigZag
class ZigZag_py : public ZigZag {
public:
    ZigZag_py() : ZigZag() {};

    py::list getOutput() const {
        py::list o;
        for (const auto& p : out) {
            o.append(p);
        }
        return o;
    }
};

} // namespace ocl

#endif // ZIGZAG_PY_H
