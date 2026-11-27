from pathlib import Path
import unittest
from unittest.mock import patch

from benchmarks import qualify_contained_php as qualification
from benchmarks.contained_php import BlockedReason, CandidateFailure, EvaluationBlocked, Observation, ProbeDeadlineExceeded


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

    def test_guest_preflight_reports_a_registered_reason_without_private_details(self):
        error = EvaluationBlocked("sensitive path", reason=BlockedReason.GUEST)
        with patch.object(qualification, "observe", side_effect=error):
            report = qualification.qualify(Path("/usr/bin/docker"), "image", True)
        self.assertEqual(report["blocked_reason"], "approved_guest_unavailable")
        self.assertNotIn("sensitive path", str(report))

    def test_candidate_gate_requires_operator_and_fresh_complete_qualification(self):
        image = "image"
        checks = dict.fromkeys((*qualification.CHECKS, "memory_enforced", "timeout_and_cleanup"), True)
        valid = {"status": "qualified", "image_id": image, "checks": checks}
        with patch.object(qualification, "qualify", return_value=valid) as run:
            with self.assertRaises(EvaluationBlocked):
                qualification.require_qualified_guest(Path("/usr/bin/docker"), image, False)
            run.assert_not_called()
            qualification.require_qualified_guest(Path("/usr/bin/docker"), image, True)
            run.assert_called_once_with(Path("/usr/bin/docker"), image, True)
        for report in ({**valid, "status": "blocked"}, {**valid, "image_id": "other"},
                       {**valid, "checks": {}}, {**valid, "checks": {**checks, "memory_enforced": False}}):
            with (self.subTest(report=report), patch.object(qualification, "qualify", return_value=report),
                  self.assertRaises(EvaluationBlocked)):
                qualification.require_qualified_guest(Path("/usr/bin/docker"), image, True)
