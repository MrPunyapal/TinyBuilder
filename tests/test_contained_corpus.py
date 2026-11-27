from pathlib import Path
import unittest
from unittest.mock import patch

from benchmarks.contained_corpus import TAX_PATH, score_tax
from benchmarks.contained_php import BlockedReason, CandidateFailure, EvaluationBlocked, Observation


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
        self.assertEqual(report["behavior"], {"total": 5, "passed": 5, "failed": 0, "blocked": 0, "attempted": 5, "remaining": 0})
        self.assertEqual(report["regression"], {"total": 4, "passed": 4, "failed": 0, "blocked": 0, "attempted": 4, "remaining": 0})
        self.assertEqual(len(calls), 9)
        self.assertNotIn("candidate bytes", str(report))

    def test_wrong_and_boolean_outputs_never_match_integer_results(self):
        constant = self.score(lambda **_: Observation(0, "fixture", "image"))
        wrong_type = self.score(lambda **_: Observation(True, "fixture", "image"))
        self.assertEqual(constant["behavior"]["passed"], 1)
        self.assertEqual(wrong_type["behavior"]["passed"], 0)
        self.assertEqual(wrong_type["regression"]["passed"], 0)

    def test_blocked_runner_never_falls_back_to_host_php(self):
        report = self.score(EvaluationBlocked("private guest detail"))
        self.assertEqual(report["status"], "blocked")
        self.assertEqual(report["blocked_reason"], "probe_blocked_unattributed")
        self.assertEqual(report["behavior"], {"total": 5, "passed": 0, "failed": 0,
                                             "blocked": 1, "attempted": 1, "remaining": 4})
        self.assertEqual(report["regression"]["remaining"], 4)
        self.assertNotIn("private guest detail", str(report))

    def test_partial_probe_failure_retains_completed_counts(self):
        report = self.score([Observation(0, "fixture", "image"),
                             Observation(2, "fixture", "image"),
                             EvaluationBlocked("private staging path", reason=BlockedReason.CLEANUP)])
        self.assertEqual(report["behavior"], {"total": 5, "passed": 1, "failed": 1,
                                             "blocked": 1, "attempted": 3, "remaining": 2})
        self.assertEqual(report["regression"]["remaining"], 4)
        self.assertEqual(report["blocked_reason"], "cleanup_unverified")
        self.assertNotIn("private staging path", str(report))

    def test_identity_mismatch_blocks_remaining_probes(self):
        report = self.score([Observation(0, "fixture", "image"),
                             Observation(1, "changed", "image")])
        self.assertEqual(report["blocked_reason"], "identity_mismatch")
        self.assertEqual(report["behavior"]["attempted"], 2)
        self.assertEqual(report["behavior"]["passed"], 1)
        self.assertEqual(report["behavior"]["blocked"], 1)
        self.assertEqual(report["behavior"]["remaining"], 3)

    def test_candidate_failure_retains_failed_count_and_continues(self):
        report = self.score([CandidateFailure("candidate_output"),
                             EvaluationBlocked("untrusted detail")])
        self.assertEqual(report["candidate_failures"], {"candidate_output": 1})
        self.assertEqual(report["behavior"]["failed"], 1)
        self.assertEqual(report["behavior"]["blocked"], 1)
        self.assertEqual(report["behavior"]["remaining"], 3)

    def test_protocol_mismatch_is_an_infrastructure_block(self):
        report = self.score([Observation(0, "fixture", "image", protocol=-1)])
        self.assertEqual(report["blocked_reason"], "identity_mismatch")
        self.assertEqual(report["behavior"]["blocked"], 1)
