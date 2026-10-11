"""Candidate binding ownership checks, intentionally separate from parity tests.

Run with the candidate wheel's interpreter. The old Boost.Python API did not
guarantee these keep-alive relationships; running dangling pointers there is not
a valid reference oracle. Weakrefs verify retention before entering native code.
"""
import gc
import subprocess
import sys
import tempfile
import textwrap
import unittest
import weakref

import opencamlib as ocl


def mesh():
    result = ocl.STLSurf()
    result.addTriangle(ocl.Triangle(ocl.Point(-2, -2, 0),
                                    ocl.Point(2, -2, 0), ocl.Point(0, 2, 0)))
    return result


class OwnershipTests(unittest.TestCase):
    def attach_temporary_dependencies(self, operation, with_path=False):
        surface, cutter = mesh(), ocl.BallCutter(1., 4.)
        refs = [weakref.ref(surface), weakref.ref(cutter)]
        operation.setSTL(surface)
        operation.setCutter(cutter)
        if with_path:
            path = ocl.Path()
            path.append(ocl.Line(ocl.Point(-1, 0, -1), ocl.Point(1, 0, -1)))
            operation.setPath(path)
            refs.append(weakref.ref(path))
        return refs

    def assert_retained(self, refs):
        gc.collect()
        # Prevent a use-after-free native call if the binding loses keep_alive.
        self.assertTrue(all(ref() is not None for ref in refs))

    def assert_released(self, refs):
        gc.collect()
        self.assertTrue(all(ref() is None for ref in refs))

    def test_batch_drop_owns_dependencies(self):
        operation = ocl.BatchDropCutter()
        operation.setThreads(1)
        refs = self.attach_temporary_dependencies(operation)
        self.assert_retained(refs)
        operation.appendPoint(ocl.CLPoint(0, 0, -1))
        operation.run()
        result = operation.getCLPoints()
        del operation
        self.assert_released(refs)
        self.assertAlmostEqual(result[0].z, 0.)

    def test_path_operations_own_dependencies(self):
        for cls in (ocl.PathDropCutter, ocl.AdaptivePathDropCutter):
            with self.subTest(operation=cls.__name__):
                operation = cls()
                operation.setSampling(.5)
                operation.setZ(-1.)
                if cls is ocl.AdaptivePathDropCutter:
                    operation.setMinSampling(.1)
                refs = self.attach_temporary_dependencies(operation, with_path=True)
                self.assert_retained(refs)
                operation.run()
                result = operation.getCLPoints()
                del operation
                self.assert_released(refs)
                self.assertGreater(len(result), 1)
                self.assertTrue(all(abs(p.z) < 1e-10 for p in result))

    def test_waterlines_own_dependencies(self):
        for cls in (ocl.Waterline, ocl.AdaptiveWaterline):
            with self.subTest(operation=cls.__name__):
                operation = cls()
                refs = self.attach_temporary_dependencies(operation)
                self.assert_retained(refs)
                # No native contour run on an open triangle is needed to prove
                # the setters' ownership contract.
                del operation
                self.assert_released(refs)

    def test_batch_push_owns_dependencies(self):
        operation = ocl.BatchPushCutter()
        operation.setXDirection()
        operation.setThreads(1)
        refs = self.attach_temporary_dependencies(operation)
        self.assert_retained(refs)
        operation.appendFiber(ocl.Fiber(ocl.Point(-3, 0, -.1), ocl.Point(3, 0, -.1)))
        before_run = operation.getFibers()
        operation.run()
        result = operation.getFibers()
        self.assertEqual(before_run[0].getInts(), [])
        del operation
        # Snapshot results do not retain the operation or its dependencies.
        self.assert_released(refs)
        self.assertEqual(len(result), 1)
        self.assertGreater(len(result[0].getInts()), 0)

    def test_fiber_snapshots_survive_reallocation_and_are_independent(self):
        # Run in a child: the old reference_internal binding segfaults after
        # vector reallocation, which must be reported as a failed test.
        program = textwrap.dedent("""
            import gc
            try:
                import resource
                resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
            except ImportError:
                pass
            import opencamlib as ocl
            operation = ocl.BatchPushCutter()
            source = ocl.Fiber(ocl.Point(1, 2, 0), ocl.Point(3, 2, 0))
            source.addInterval(ocl.Interval(.25, .75))
            operation.appendFiber(source)
            snapshot = operation.getFibers()[0]
            endpoint = snapshot.p1
            for i in range(1024):
                operation.appendFiber(ocl.Fiber(ocl.Point(i, 7, 0), ocl.Point(i + 1, 7, 0)))
            assert (endpoint.x, endpoint.y, endpoint.z) == (1, 2, 0)
            assert (snapshot.p2.x, snapshot.p2.y, snapshot.p2.z) == (3, 2, 0)
            assert [(i.lower, i.upper) for i in snapshot.getInts()] == [(.25, .75)]
            snapshot.p1.x = 101
            snapshot.addInterval(ocl.Interval(.8, .9))
            fresh = operation.getFibers()[0]
            assert fresh.p1.x == 1
            assert [(i.lower, i.upper) for i in fresh.getInts()] == [(.25, .75)]
            del operation, source, fresh
            gc.collect()
            assert snapshot.p1.x == 101
            assert [(i.lower, i.upper) for i in snapshot.getInts()] == [(.25, .75), (.8, .9)]
        """)
        with tempfile.TemporaryDirectory(prefix="ocl-fiber-snapshot-") as directory:
            result = subprocess.run([sys.executable, "-I", "-c", program], cwd=directory,
                                    capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_cl_surface_owns_dependencies(self):
        operation = ocl.CutterLocationSurface(4.)
        refs = self.attach_temporary_dependencies(operation)
        self.assert_retained(refs)
        del operation
        self.assert_released(refs)

    def test_owned_offset_outlives_source(self):
        cutter = ocl.BallCutter(1., 4.)
        offset = cutter.offsetCutter(.2)
        del cutter
        gc.collect()
        self.assertAlmostEqual(offset.getRadius(), .7)
        position = ocl.CLPoint(0, 0, -1)
        surface = mesh()
        offset.dropCutter(position, surface.getTriangles()[0])
        self.assertAlmostEqual(position.z, 0.)


if __name__ == "__main__":
    unittest.main(verbosity=2)
