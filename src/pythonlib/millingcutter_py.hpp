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

#ifndef MILLING_CUTTER_PY_H
#define MILLING_CUTTER_PY_H

#include <pybind11/pybind11.h>

#include "millingcutter.hpp"

namespace ocl {

class MillingCutter_py : public MillingCutter {
public:
    using MillingCutter::MillingCutter; // inherit constructors if needed

    bool vertexDrop(CLPoint& cl, const Triangle& t) const {
        PYBIND11_OVERRIDE(bool, MillingCutter, vertexDrop, cl, t);
    }

    bool facetDrop(CLPoint& cl, const Triangle& t) const override {
        PYBIND11_OVERRIDE(bool, MillingCutter, facetDrop, cl, t);
    }

    bool edgeDrop(CLPoint& cl, const Triangle& t) const override {
        PYBIND11_OVERRIDE(bool, MillingCutter, edgeDrop, cl, t);
    }

    MillingCutter* offsetCutter(double d) const override {
        PYBIND11_OVERRIDE(MillingCutter*, MillingCutter, offsetCutter, d);
    }

    std::string str() const override { PYBIND11_OVERRIDE(std::string, MillingCutter, str); }
};

} // end namespace ocl

#endif // MILLING_CUTTER_PY_H
