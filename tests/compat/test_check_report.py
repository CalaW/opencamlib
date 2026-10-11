"""Inject regressions into minimal reports to prove the reviewed gate rejects them."""
import copy
import unittest

from check_report import check_report, _loops


def fixture(value=None):
    value = {'approved': 'old', 'height': 2.0} if value is None else value
    report = {'schema_version': 1, 'inventories': {
        side: {'status': 'ok', 'value': {'metadata': {'distribution': '2023.1.11'},
                                      'api': {'exports': {}, 'members': {}}}}
        for side in ('reference', 'candidate')},
        'coverage': {'uncovered': []}, 'cases': {'probe': {
            'reference': {'status': 'ok', 'value': copy.deepcopy(value)},
            'candidate': {'status': 'ok', 'value': copy.deepcopy(value)}}}}
    manifest = {'schema_version': 1, 'reference_distribution': '2023.1.11',
                'tolerances': {'rtol': 1e-10, 'atol': 1e-10},
                'api_transitions': [], 'required_cases': ['probe'], 'cases': {}}
    return report, manifest


class ReviewedGateTests(unittest.TestCase):
    def test_matching_report_passes(self):
        self.assertEqual(check_report(*fixture()), [])

    def test_only_exact_reviewed_property_can_change(self):
        report, manifest = fixture()
        report['cases']['probe']['candidate']['value']['approved'] = 'new'
        manifest['cases']['probe'] = {'transitions': [
            {'location': ['approved'], 'reference': 'old', 'candidate': 'new'}]}
        self.assertEqual(check_report(report, manifest), [])
        report['cases']['probe']['candidate']['value']['height'] = 99.0
        self.assertTrue(check_report(report, manifest))
        report['cases']['probe']['candidate']['value']['height'] = 2.0
        report['cases']['probe']['candidate']['value']['approved'] = 'other'
        self.assertTrue(check_report(report, manifest))

    def test_forged_match_summary_does_not_hide_changed_value(self):
        report, manifest = fixture()
        report['counts'] = {'match': 1}
        report['cases']['probe'].update(status='match', differences=[])
        report['cases']['probe']['candidate']['value']['height'] = 99.0
        self.assertTrue(check_report(report, manifest))

    def test_report_tolerance_cannot_relax_gate(self):
        report, manifest = fixture()
        report['tolerances'] = {'rtol': 100, 'atol': 100}
        report['cases']['probe']['candidate']['value']['height'] = 3.0
        self.assertTrue(check_report(report, manifest))

    def test_crashes_timeouts_and_protocol_failures_always_fail(self):
        for side in ('reference', 'candidate'):
            for status in ('crash', 'timeout', 'protocol_error'):
                report, manifest = fixture()
                report['cases']['probe'][side] = {'status': status}
                self.assertTrue(check_report(report, manifest), (side, status))

    def test_unexpected_python_error_fails(self):
        report, manifest = fixture()
        report['cases']['probe']['candidate'] = {'status': 'error', 'exception': 'TypeError'}
        self.assertTrue(check_report(report, manifest))

    def test_missing_case_unknown_case_and_uncovered_member_fail(self):
        report, manifest = fixture()
        report['cases'].clear()
        self.assertTrue(check_report(report, manifest))
        report, manifest = fixture()
        report['cases']['unexpected'] = copy.deepcopy(report['cases']['probe'])
        self.assertTrue(check_report(report, manifest))
        report, manifest = fixture()
        report['coverage']['uncovered'] = ['Point.newMethod']
        self.assertTrue(check_report(report, manifest))

    def test_api_change_is_recomputed_from_inventory(self):
        report, manifest = fixture()
        report['api_differences'] = []
        report['inventories']['candidate']['value']['api']['exports']['Surprise'] = 'class'
        self.assertTrue(check_report(report, manifest))

    def test_raw_rotation_requires_successful_separate_geometry_case(self):
        triangle = [[0.0, 0.0, 1.0], [1.0, 0.0, 1.0], [0.0, 1.0, 1.0]]
        report, manifest = fixture([triangle])
        report['cases']['probe']['candidate']['value'] = [triangle[1:] + triangle[:1]]
        canonical = {'reference': {'status': 'ok', 'value': _loops([triangle])},
                     'candidate': {'status': 'ok', 'value': _loops([triangle])}}
        report['cases']['geometry'] = canonical
        manifest['required_cases'].append('geometry')
        manifest['cases']['probe'] = {'contours': 'loops', 'paired_case': 'geometry'}
        self.assertEqual(check_report(report, manifest), [])
        del report['cases']['geometry']
        self.assertTrue(check_report(report, manifest))
        report['cases']['geometry'] = canonical
        canonical['candidate']['value'][0][0][2] = 99.0
        self.assertTrue(check_report(report, manifest))

    def test_loop_winding_vertices_closure_and_duplicates_are_preserved(self):
        triangle = [[0.0, 0.0, 1.0], [1.0, 0.0, 1.0], [0.0, 1.0, 1.0]]
        for changed in (triangle[::-1], triangle + [triangle[0]], triangle + [triangle[1]],
                        [[0.0, 0.0, 9.0]] + triangle[1:]):
            report, manifest = fixture([triangle])
            report['cases']['probe']['candidate']['value'] = [changed]
            manifest['cases']['probe'] = {'contours': 'loops'}
            self.assertTrue(check_report(report, manifest))

    def test_added_empty_fibers_require_exact_descriptors(self):
        full = {'intervals': [{'empty': False, 'lower': 0.2}], 'p1': [0, 0, 1], 'p2': [1, 0, 1]}
        empty = {'intervals': [], 'p1': [0, -1, 1], 'p2': [1, -1, 1]}
        report, manifest = fixture({'fibers': [full]})
        report['cases']['probe']['candidate']['value']['fibers'].insert(0, copy.deepcopy(empty))
        manifest['cases']['probe'] = {'empty_fibers': [{'location': ['fibers'], 'expected': [empty]}]}
        self.assertEqual(check_report(report, manifest), [])
        report['cases']['probe']['candidate']['value']['fibers'][0]['p1'][0] = 99
        self.assertTrue(check_report(report, manifest))

    def test_constructor_exceptions_are_exact_and_never_allow_crashes(self):
        report, manifest = fixture({'type': 'Line'})
        report['cases']['probe']['candidate'] = {'status': 'error', 'exception': 'TypeError', 'message': 'No default'}
        manifest['cases']['probe'] = {'kind': 'removed_constructor', 'reference_value': {'type': 'Line'},
                                     'candidate_exception': 'TypeError', 'candidate_message': 'No default'}
        self.assertEqual(check_report(report, manifest), [])
        report['cases']['probe']['candidate']['message'] = 'Unrelated bad input'
        self.assertTrue(check_report(report, manifest))
        report['cases']['probe']['candidate'] = {'status': 'crash'}
        self.assertTrue(check_report(report, manifest))

    def test_candidate_only_result_is_checked_not_merely_successful(self):
        report, manifest = fixture({'result': 42})
        report['cases']['probe']['reference'] = {'status': 'error', 'exception': 'AttributeError', 'message': 'missing'}
        manifest['cases']['probe'] = {'kind': 'candidate_only', 'reference_exception': 'AttributeError',
                                     'reference_message': 'missing', 'candidate_value': {'result': 42}}
        self.assertEqual(check_report(report, manifest), [])
        report['cases']['probe']['candidate']['value']['result'] = 99
        self.assertTrue(check_report(report, manifest))

    def test_wrong_reference_and_bad_schema_fail(self):
        report, manifest = fixture()
        report['inventories']['reference']['value']['metadata']['distribution'] = 'another'
        self.assertTrue(check_report(report, manifest))
        self.assertTrue(check_report({}, manifest))


if __name__ == '__main__':
    unittest.main()
