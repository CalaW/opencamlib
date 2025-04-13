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
#ifndef PATH_PY_H
#define PATH_PY_H

#include <pybind11/pybind11.h>

#include "path.hpp"

namespace ocl {
namespace py = pybind11;

/// Python wrapper for Path
class Path_py : public Path {
public:
    Path_py() : Path() {}
    /// copy constructor
    Path_py(const Path& p) : Path(p) {}

    /// return the span-list to python
    py::list getSpans() {
        py::list slist;
        for (auto span : span_list) {
            if (span->type() == LineSpanType)
                slist.append(static_cast<LineSpan*>(span)->line);
            else if (span->type() == ArcSpanType)
                slist.append(static_cast<ArcSpan*>(span)->arc);
        }
        return slist;
    }

    /// return a list of type/span pairs
    py::list getTypeSpanPairs() {
        py::list slist;
        for (auto span : span_list) {
            if (span->type() == LineSpanType) {
                py::list tuple;
                tuple.append(span->type());
                tuple.append(static_cast<LineSpan*>(span)->line);
                slist.append(tuple);
            } else if (span->type() == ArcSpanType) {
                py::list tuple;
                tuple.append(span->type());
                tuple.append(static_cast<ArcSpan*>(span)->arc);
                slist.append(tuple);
            }
        }
        return slist;
    }
};

} // namespace ocl

#endif // PATH_PY_H
