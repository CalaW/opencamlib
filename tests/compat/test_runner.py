"""Tests of the test harness; run with python -m unittest discover -s tests/compat."""
import sys
import contextlib
import io
import tempfile
from pathlib import Path
import unittest

from runner import classify, differences, invoke, main


class ComparisonTests(unittest.TestCase):
    def test_float_tolerance_is_local_and_preserves_structure(self):
        self.assertEqual(differences([1.0], [1.0 + 1e-12]), [])
        self.assertTrue(differences([1.0], [1.001]))
        self.assertTrue(differences([1.0], [1]))
        self.assertTrue(differences([True], [1]))
        self.assertTrue(differences([1, 2], [2, 1]))
        self.assertTrue(differences([1], [1, 2]))

    def test_reports_nested_field_and_removed_member(self):
        change = differences({"p": {"z": 2.0}}, {"p": {"z": 3.0}})
        self.assertEqual(change[0]["path"], "$.p.z")
        self.assertEqual(differences({"norm": "method"}, {})[0]["reason"], "missing key")

    def test_equal_errors_and_timeouts_never_pass(self):
        for status in ("error", "timeout", "crash", "protocol_error"):
            with self.subTest(status=status):
                self.assertEqual(classify({"status": status}, {"status": status})[0], "baseline_error")
                self.assertEqual(classify({"status": "ok", "value": []}, {"status": status})[0], "candidate_error")

    def test_real_worker_timeout_is_reported(self):
        # A deadline shorter than process startup exercises subprocess cleanup.
        result = invoke(sys.executable, "__inventory__", 1e-9)
        self.assertEqual(result["status"], "timeout")

    def test_matching_data_passes(self):
        value = {"status": "ok", "value": {"point": [1., 2., 3.]}}
        self.assertEqual(classify(value, value), ("match", []))

    def test_missing_interpreter_is_setup_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            result = invoke(Path(directory) / "no-python", "__inventory__", 1)
        self.assertEqual(result["status"], "launch_error")

    def test_nonfinite_cli_tolerances_are_rejected(self):
        for option in ("--rtol", "--atol", "--timeout"):
            for value in ("nan", "inf", "-inf"):
                with self.subTest(option=option, value=value), contextlib.redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit) as error:
                        main([option + "=" + value])
                    self.assertEqual(error.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
