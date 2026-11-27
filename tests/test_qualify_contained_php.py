from pathlib import Path
import unittest
from unittest.mock import patch

from benchmarks import qualify_contained_php as qualification
from benchmarks.contained_php import CandidateFailure, EvaluationBlocked, Observation, ProbeDeadlineExceeded


class GuestQualificationTests(unittest.TestCase):
    def test_requires_every_kernel_probe_and_live_enforcement_check(self):
        for timeout, expected in (
            (ProbeDeadlineExceeded("attachment deadline"), "qualified"),
            (EvaluationBlocked("container command deadline exceeded"), "blocked"),
            (EvaluationBlocked("container cleanup could not be verified"), "blocked"),
        ):
            events = [Observation(dict.fromkeys(qualification.CHECKS, True), "fixture", "image"),
                      CandidateFailure("candidate_resource"), timeout]
            with (self.subTest(timeout=timeout), patch.object(qualification, "observe", side_effect=events),
                  patch.object(qualification, "monotonic", side_effect=[0, 21])):
                report = qualification.qualify(Path("/usr/bin/docker"), "image", True)
            self.assertEqual(report["status"], expected)

    def test_policy_failure_prevents_resource_probe(self):
        checks = dict.fromkeys(qualification.CHECKS, True)
        checks["readonly_fixture"] = False
        with patch.object(qualification, "observe", return_value=Observation(checks, "fixture", "image")) as observe:
            report = qualification.qualify(Path("/usr/bin/docker"), "image", True)
        self.assertEqual(report["status"], "blocked")
        self.assertIsNone(report["checks"]["memory_enforced"])
        observe.assert_called_once()
