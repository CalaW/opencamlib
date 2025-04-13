/*  $Id$
 *
 *  Copyright (c) 2010-2011 Anders Wallin (anders.e.e.wallin "at" gmail.com).
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
#ifndef WEAVE_PY_H
#define WEAVE_PY_H

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "weave.hpp"

namespace py = pybind11;

namespace ocl {
namespace weave {

class Weave_py : public Weave {
public:
    Weave_py() : Weave() {}

    int numVertices() const { return g.num_vertices(); }

    py::list getVertices(VertexType t) {
        py::list plist;
        for (auto v : g.vertices()) {
            if (g[v].type == t)
                plist.append(g[v].position);
        }
        return plist;
    }

    // return CL-points to python
    py::list getCLVertices() { return getVertices(CL); }

    // return internal points to python
    py::list getINTVertices() { return getVertices(INT); }

    // return edges to python
    // format is [ [p1,p2] , [p3,p4] , ... ]
    py::list getEdges() {
        py::list edge_list;
        for (auto e : g.edges()) {
            py::list point_list;
            Vertex v1 = g.source(e);
            Vertex v2 = g.target(e);
            point_list.append(g[v1].position);
            point_list.append(g[v2].position);
            edge_list.append(point_list);
        }
        return edge_list;
    }

    // return loops to python
    py::list getLoops() {
        py::list loop_list;
        for (const auto& loop : loops) {
            py::list point_list;
            for (auto v : loop) {
                point_list.append(g[v].position);
            }
            loop_list.append(point_list);
        }
        return loop_list;
    }
};

} // end namespace weave
} // end namespace ocl

#endif // WEAVE_PY_H
