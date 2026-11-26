import unittest

from benchmarks.pilot_protocol import index_rows


class PilotProtocolTests(unittest.TestCase):
    def test_rejects_driver_pass_duplicate_and_malformed_patch(self):
        base = {"case": "fixture", "arm": "A", "category": "proposal", "preview": "source"}
        expected = {("fixture", "A")}
        self.assertEqual(index_rows([{"ready_ms": 2}, base], expected)[("fixture", "A")], base)
        for rows in ([{**base, "category": "pass"}], [base, base],
                     [{**base, "preview": []}], [{**base, "arm": "D"}],
                     [{"ready_ms": 1}, {"ready_ms": 2}]):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                index_rows(rows, expected)

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from benchmarks.laravel_pilot import test as verified_phpunit


class PHPUnitProofTests(unittest.TestCase):
    def test_requires_matching_junit_assertion_failure(self):
        def result(code, marker):
            def run(argv, _project):
                output = Path(argv[argv.index("--log-junit") + 1])
                if marker is not None:
                    output.write_text("<testsuites><testsuite>" + marker + "</testsuite></testsuites>", encoding="utf-8")
                self.assertTrue(argv[-1].endswith("TinyBuilderPilotTest.php"))
                return SimpleNamespace(returncode=code)
            return run

        for code, xml, expected in (
            (0, '<testcase name="test_repair" assertions="1"/>', 0),
            (1, '<testcase name="test_repair" assertions="1"><failure/></testcase>', 1),
            (1, None, 2),
            (1, '<testcase name="another_test"><failure/></testcase>', 2),
            (1, '<testcase name="test_repair"><error/></testcase>', 2),
        ):
            with self.subTest(code=code, xml=xml), patch("benchmarks.laravel_pilot.command", result(code, xml)):
                self.assertEqual(verified_phpunit("php", Path("."), "test_repair"), expected)
