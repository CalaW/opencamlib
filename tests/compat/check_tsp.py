#!/usr/bin/env python3
"""Lifetime and result regression checks against an installed OpenCAMLib wheel.

Run with the target environment's Python. Every scenario runs in a child process
so a native assertion, invalid free, or segmentation fault is a test failure.
"""
import gc
import math
import os
from pathlib import Path
import subprocess
import sys
import unittest


POINTS = [(0., 0.), (2., .1), (3., 2.), (-.5, 3.), (.7, .9)]


def add_points(solver, points):
    for x, y in points:
        solver.addPoint(x, y)


def assert_tour(solver, points):
    tour = solver.getOutput()
    if not points:
        assert tour == [], tour
        assert solver.getLength() == 0., solver.getLength()
        return
    assert len(tour) == len(points) + 1, tour
    assert tour[0] == tour[-1], tour
    assert sorted(tour[:-1]) == list(range(len(points))), tour
    distance = sum(math.hypot(points[a][0] - points[b][0], points[a][1] - points[b][1])
                   for a, b in zip(tour, tour[1:]))
    assert math.isclose(solver.getLength(), distance, abs_tol=1e-12), (solver.getLength(), distance)


def scenario(name):
    import opencamlib as ocl

    if name == "initial_state":
        solver = ocl.TSPSolver()
        assert solver.getOutput() == []
        assert solver.getLength() == 0.
        del solver
        gc.collect()
    elif name == "reset_before_run":
        solver = ocl.TSPSolver()
        solver.reset()
        solver.reset()
        assert solver.getOutput() == []
        assert solver.getLength() == 0.
        del solver
        gc.collect()
    elif name == "reset_then_destroy":
        solver = ocl.TSPSolver()
        add_points(solver, POINTS)
        solver.run()
        assert_tour(solver, POINTS)
        solver.reset()
        assert solver.getOutput() == []
        assert solver.getLength() == 0.
        del solver
        gc.collect()
    elif name == "repeated_run":
        solver = ocl.TSPSolver()
        add_points(solver, POINTS)
        solver.run()
        first = (solver.getOutput(), solver.getLength())
        assert_tour(solver, POINTS)
        for _ in range(20):
            solver.run()
            assert_tour(solver, POINTS)
            assert (solver.getOutput(), solver.getLength()) == first
    elif name == "reset_refill":
        solver = ocl.TSPSolver()
        for points in [POINTS, [(0., 0.), (3., 0.), (0., 4.)], POINTS]:
            solver.reset()
            solver.reset()
            assert solver.getOutput() == []
            assert solver.getLength() == 0.
            add_points(solver, points)
            solver.run()
            assert_tour(solver, points)
        solver.reset()
    elif name == "empty":
        solver = ocl.TSPSolver()
        solver.run()
        assert_tour(solver, [])
        solver.run()
        assert_tour(solver, [])
        solver.reset()
        add_points(solver, POINTS)
        solver.run()
        solver.reset()
        solver.run()
        assert_tour(solver, [])
    elif name == "singleton":
        solver = ocl.TSPSolver()
        solver.addPoint(3., 4.)
        solver.run()
        assert_tour(solver, [(3., 4.)])
        assert solver.getOutput() == [0, 0]
        solver.run()
        assert_tour(solver, [(3., 4.)])
        solver.reset()
    elif name == "append_after_run":
        solver = ocl.TSPSolver()
        points = [(0., 0.), (3., 0.)]
        add_points(solver, points)
        solver.run()
        assert_tour(solver, points)
        solver.addPoint(0., 4.)
        points.append((0., 4.))
        solver.run()
        assert_tour(solver, points)
        assert solver.getLength() == 12.
    elif name == "duplicates":
        solver = ocl.TSPSolver()
        points = [(1., 2.), (1., 2.), (1., 2.)]
        add_points(solver, points)
        solver.run()
        assert_tour(solver, points)
        assert solver.getLength() == 0.
        solver.reset()
    elif name == "normal_contract":
        solver = ocl.TSPSolver()
        points = [(0., 0.), (3., 0.), (0., 4.)]
        add_points(solver, points)
        solver.run()
        assert_tour(solver, points)
        assert solver.getLength() == 12.
    elif name == "many_lifetimes":
        for _ in range(100):
            solver = ocl.TSPSolver()
            add_points(solver, POINTS)
            solver.run()
            solver.reset()
            del solver
        gc.collect()
    else:
        raise ValueError(name)


SCENARIOS = ["initial_state", "reset_before_run", "reset_then_destroy", "repeated_run",
             "reset_refill", "empty", "singleton", "append_after_run", "duplicates",
             "normal_contract", "many_lifetimes"]


class TSPLifetimeTests(unittest.TestCase):
    def check_scenario(self, name):
        env = os.environ.copy()
        env.pop("PYTHONPATH", None)
        env.pop("PYTHONHOME", None)
        result = subprocess.run([sys.executable, "-I", str(Path(__file__).resolve()), "--scenario", name],
                                capture_output=True, text=True, env=env, timeout=15)
        self.assertEqual(result.returncode, 0,
                         "%s exited %s\n%s\n%s" % (name, result.returncode, result.stdout, result.stderr))


for _name in SCENARIOS:
    def _test(self, name=_name):
        self.check_scenario(name)
    setattr(TSPLifetimeTests, "test_" + _name, _test)


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--scenario":
        try:
            import resource
            resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        except ImportError:
            pass
        scenario(sys.argv[2])
    else:
        unittest.main()
