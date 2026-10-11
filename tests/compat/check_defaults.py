"""Check useful default states against the installed candidate wheel."""
import unittest

import opencamlib as ocl


def xyz(point):
    return (point.x, point.y, point.z)


class DefaultStateTests(unittest.TestCase):
    def test_zero_points_and_unset_contacts(self):
        for cls in (ocl.Point, ocl.CCPoint, ocl.CLPoint):
            with self.subTest(cls=cls.__name__):
                self.assertEqual(xyz(cls()), (0., 0., 0.))
        self.assertEqual(ocl.CCPoint().type, ocl.CCType.NONE)
        self.assertEqual(ocl.CLPoint().getCC().type, ocl.CCType.NONE)

    def test_empty_path_can_be_populated(self):
        path = ocl.Path()
        self.assertEqual(path.getSpans(), [])
        path.append(ocl.Line(ocl.Point(0, 0), ocl.Point(2, 1)))
        spans = path.getSpans()
        self.assertEqual(len(spans), 1)
        self.assertEqual(xyz(spans[0].p2), (2., 1., 0.))

    def test_empty_surface_can_be_populated(self):
        surface = ocl.STLSurf()
        self.assertEqual(surface.size(), 0)
        self.assertEqual(surface.getTriangles(), [])
        surface.addTriangle(ocl.Triangle(ocl.Point(0, 0), ocl.Point(2, 0), ocl.Point(0, 3)))
        self.assertEqual(surface.size(), 1)
        self.assertEqual(list(surface.getBounds()), [0., 2., 0., 3., 0., 0.])

    def test_empty_interval_accepts_first_contact(self):
        interval = ocl.Interval()
        self.assertTrue(interval.empty())
        contact = ocl.CCPoint(1, 2, 3)
        contact.type = ocl.CCType.EDGE
        interval.updateLower(.25, contact)
        interval.updateUpper(.75, contact)
        self.assertFalse(interval.empty())
        self.assertEqual((interval.lower, interval.upper), (.25, .75))
        self.assertEqual(interval.lower_cc.type, ocl.CCType.EDGE)

    def test_ellipse_position_starts_at_zero_angle_and_samples_ellipse(self):
        position = ocl.EllipsePosition()
        self.assertEqual((position.s, position.t), (1., 0.))
        ellipse = ocl.Ellipse(ocl.Point(1, 2, 3), 4., 2., .5)
        self.assertEqual(xyz(ellipse.ePoint(position)), (5., 2., 3.))
        self.assertEqual(xyz(ellipse.oePoint(position)), (5.5, 2., 3.))
        self.assertEqual(xyz(ellipse.normal(position)), (1., 0., 0.))
        position.setDiangle(1.)
        self.assertEqual((position.s, position.t), (0., 1.))
        self.assertEqual(xyz(ellipse.ePoint(position)), (1., 4., 3.))
        self.assertEqual(xyz(ellipse.oePoint(position)), (1., 4.5, 3.))


if __name__ == "__main__":
    unittest.main(verbosity=2)
