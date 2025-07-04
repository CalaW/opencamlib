import matplotlib.pyplot as plt
from opencamlib import ocl

# Travelling Salesman Problem
# a.k.a. drill-path optimization

# we have multiple points in the 2D plane to visit.
# the task is to optimize the distance travelled by the tool while
# visiting all points
#
# uses data from TSPLIB (not included in opencamlib)
#
# ocl.TSPSolver() is a wrapper for boost::metric_tsp_approx()
# https://www.boost.org/doc/libs/1_67_0/libs/graph/doc/metric_tsp_approx.html


def draw_points(ax, pts):
    x = [p.x for p in pts]
    y = [p.y for p in pts]
    ax.scatter(x, y, color="blue", label="Points")


def draw_tour(ax, pts, tour, tour_color="red"):
    x = [pts[tour[i]].x for i in range(len(tour))]
    y = [pts[tour[i]].y for i in range(len(tour))]
    ax.plot(x, y, color=tour_color, label="Tour")


def tsp_lib_reader(filename):
    """read a .tsp format TSPLIB file, and return list of points"""
    from pathlib import Path

    infile = Path(filename).open()
    points = []
    found = 0
    for line in infile.readlines():
        if not found:
            if "NODE_COORD_SECTION" in line:
                found = 1
        else:
            words = line.split()
            if len(words) != 0 and words[0] != "EOF":
                points.append(ocl.Point(float(words[1]), float(words[2])))

    print("read ", len(points), " points from ", filename)
    return points


if __name__ == "__main__":
    tsp_name = "a280"
    opt_len = 2579

    tspfile = "tsplib/" + tsp_name + ".tsp"
    pts = tsp_lib_reader(tspfile)
    print(" optimal tour length = ", opt_len)

    tsp = ocl.TSPSolver()
    for p in pts:
        tsp.addPoint(p.x, p.y)
    print(" added ", len(pts), " points")
    tsp.run()
    tour_length = tsp.getLength()
    print(" tour length= ", tour_length, " ratio = ", tour_length / opt_len)

    # Visualization using matplotlib
    fig, ax = plt.subplots()
    draw_points(ax, pts)
    draw_tour(ax, pts, tsp.getOutput())
    ax.set_title(f"TSP Solution for {tsp_name}")
    ax.legend()
    plt.show()
