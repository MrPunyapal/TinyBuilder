from pathlib import Path
import unittest
from unittest.mock import patch

from benchmarks.contained_php import BlockedReason, CandidateFailure, EvaluationBlocked, Observation, VERSION
from benchmarks.contained_public import (
    BOOKING, BOOKING_RULES, PARCEL_INTAKE, PARCEL_LIMIT, TIMING, score_public,
)


IMAGE = "sha256:" + "1" * 64


class ContainedPublicTests(unittest.TestCase):
    def score(self, task, candidates, observe, **options):
        with (patch("benchmarks.contained_public.require_qualified_guest"),
              patch("benchmarks.contained_public.observe", side_effect=observe)):
            return score_public(task, candidates, docker=Path("/usr/bin/docker"),
                                image_id=IMAGE, approved_guest=True, **options)

    def test_booking_keeps_candidate_snapshots_and_mutates_only_policy(self):
        candidates = {BOOKING_RULES: b"candidate rules", BOOKING: b"candidate booking"}

        def observe(**call):
            fixtures = call["fixtures"]
            self.assertEqual(set(fixtures), {BOOKING_RULES, BOOKING})
            self.assertEqual(fixtures[BOOKING], candidates[BOOKING])
            self.assertTrue(call["approved_guest"])
            self.assertNotIn("expected", call["request"])
            variant = fixtures[BOOKING_RULES] != candidates[BOOKING_RULES]
            capacity = 11 if variant else 8
            return Observation(max(0, capacity - call["request"].get("occupied", 0)),
                               "mutation" if variant else "original", IMAGE)

        report = self.score("booking_availability", candidates, observe)
        self.assertEqual(report["passed"], 14)
        self.assertEqual(report["remaining"], 0)
        self.assertEqual(report["fixture_sha256"], {"baseline": "original", "policy_mutation": "mutation"})
        self.assertNotIn("candidate", str(report))
        self.assertEqual(candidates[BOOKING_RULES], b"candidate rules")

    def test_parcel_mutation_rejects_hardcoded_limit(self):
        candidates = {PARCEL_LIMIT: b"candidate limit", PARCEL_INTAKE: b"candidate intake"}

        def hardcoded(**call):
            fixtures = call["fixtures"]
            self.assertEqual(fixtures[PARCEL_INTAKE], candidates[PARCEL_INTAKE])
            variant = fixtures[PARCEL_LIMIT] != candidates[PARCEL_LIMIT]
            weight = call["request"].get("weight")
            return Observation(20 if weight is None else 0 < weight <= 20,
                               "mutation" if variant else "original", IMAGE)

        report = self.score("parcel_weight", candidates, hardcoded)
        self.assertEqual(report["phases"]["behavior"]["passed"], 7)
        self.assertEqual(report["phases"]["regression"]["passed"], 4)
        self.assertEqual(report["phases"]["policy_mutation"]["failed"], 2)

    def test_single_visible_feedback_can_pass_while_independent_oracle_fails(self):
        calls = []

        def narrow(**call):
            request = call["request"]
            calls.append(request)
            actual = request["elapsed"] >= request["deadline"] and request != {"elapsed": 60, "deadline": 60}
            return Observation(actual, "fixture", IMAGE)

        files = {TIMING: b"candidate timing"}
        feedback = self.score("deadline_boundary", files, narrow, feedback_only=True)
        self.assertEqual(calls, [{"elapsed": 60, "deadline": 60}])
        self.assertEqual(feedback["passed"], 1)
        full = self.score("deadline_boundary", files, narrow)
        self.assertEqual(full["failed"], 3)
        self.assertEqual(full["phases"]["regression"]["passed"], 6)

    def test_candidate_failure_continues_and_infrastructure_blocks_remaining(self):
        report = self.score("deadline_boundary", {TIMING: b"source"}, [
            CandidateFailure("candidate_exit"),
            Observation(False, "fixture", IMAGE),
            EvaluationBlocked("private daemon detail", reason=BlockedReason.DAEMON),
        ])
        self.assertEqual(report["status"], "blocked")
        self.assertEqual(
            [report[key] for key in ("planned", "attempted", "passed", "failed", "blocked", "remaining")],
            [10, 3, 1, 1, 1, 7],
        )
        self.assertEqual(report["failure_reasons"], {"candidate_exit": 1})
        self.assertEqual(report["blocked_reason"], "docker_unavailable")
        self.assertNotIn("private daemon detail", str(report))

    def test_untrusted_protocol_blocks_and_integer_is_not_boolean(self):
        report = self.score("deadline_boundary", {TIMING: b"source"}, [
            Observation(0, "fixture", IMAGE),
            Observation(False, "fixture", IMAGE, protocol=VERSION + 1),
        ])
        self.assertEqual(report["blocked_reason"], "identity_mismatch")
        self.assertEqual(report["failure_reasons"], {"wrong_observation": 1})
        self.assertEqual(report["remaining"], 8)

    def test_unexpected_candidates_are_rejected_before_observing(self):
        with patch("benchmarks.contained_public.observe") as observe:
            with self.assertRaises(ValueError):
                score_public("deadline_boundary", {TIMING: b"source", "tests/test.php": b"extra"},
                             docker=Path("/usr/bin/docker"), image_id=IMAGE, approved_guest=True)
            observe.assert_not_called()

    def test_failed_qualification_never_submits_candidate(self):
        error = EvaluationBlocked("unverified guest", reason=BlockedReason.QUALIFICATION)
        with (patch("benchmarks.contained_public.require_qualified_guest", side_effect=error),
              patch("benchmarks.contained_public.observe") as observe):
            report = score_public("deadline_boundary", {TIMING: b"candidate"},
                                  docker=Path("/usr/bin/docker"), image_id=IMAGE, approved_guest=True)
        observe.assert_not_called()
        self.assertEqual(report["status"], "blocked")
        self.assertEqual(report["blocked_reason"], "guest_qualification_failed")
        self.assertEqual([report[k] for k in ("planned", "attempted", "passed", "failed", "blocked", "remaining")],
                         [10, 0, 0, 0, 0, 10])
