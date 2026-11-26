from pathlib import Path
import unittest
from unittest.mock import patch

from benchmarks.contained_corpus import TAX_PATH, score_tax
from benchmarks.contained_php import EvaluationBlocked, Observation


class ContainedCorpusTests(unittest.TestCase):
    def score(self, observe):
        with patch("benchmarks.contained_corpus.observe", side_effect=observe):
            return score_tax(b"candidate bytes", docker=Path("/usr/bin/docker"),
                             image_id="image", approved_guest=True)

    def test_only_input_is_sent_and_expected_results_are_scored_outside(self):
        calls = []

        def observe(**kwargs):
            request = kwargs["request"]
            calls.append(request)
            self.assertEqual(set(request), {"net", "exempt"})
            self.assertEqual(kwargs["fixtures"], {TAX_PATH: b"candidate bytes"})
            self.assertTrue(kwargs["approved_guest"])
            return Observation(0 if request["exempt"] else request["net"] // 10, "fixture", "image")

        report = self.score(observe)
        self.assertEqual(report["behavior"], {"total": 4, "passed": 4})
        self.assertEqual(report["regression"], {"total": 3, "passed": 3})
        self.assertEqual(len(calls), 7)
        self.assertNotIn("candidate bytes", str(report))

    def test_wrong_and_boolean_outputs_never_match_integer_results(self):
        constant = self.score(lambda **_: Observation(0, "fixture", "image"))
        wrong_type = self.score(lambda **_: Observation(True, "fixture", "image"))
        self.assertEqual(constant["behavior"]["passed"], 1)
        self.assertEqual(wrong_type["behavior"]["passed"], 0)
        self.assertEqual(wrong_type["regression"]["passed"], 0)

    def test_blocked_runner_never_falls_back_to_host_php(self):
        with self.assertRaises(EvaluationBlocked):
            self.score(EvaluationBlocked("guest unavailable"))
