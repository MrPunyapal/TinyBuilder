from pathlib import Path
import unittest
from unittest.mock import patch

from benchmarks.contained_php import BlockedReason, CandidateFailure, EvaluationBlocked, Observation, VERSION
from benchmarks.contained_public import (
    BOOKING, BOOKING_RULES, PARCEL_INTAKE, PARCEL_LIMIT, TIMING, LISTING, ITEM,
    FRAMEWORK_VERSION, FRAMEWORK_CHECK, ROUTE_PATH, ROUTE_REFERENCE, ROUTE_PROBES, _matches, score_public,
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

    def test_framework_requires_exact_lock_and_preflight_before_candidate(self):
        lock = "a" * 64
        with patch("benchmarks.contained_public.require_qualified_guest") as qualify:
            with self.assertRaises(ValueError):
                score_public("available_stock", {LISTING: b"candidate"}, docker=Path("/unused"),
                             image_id=IMAGE, approved_guest=True)
            qualify.assert_not_called()
        with (patch("benchmarks.contained_public.require_qualified_guest"),
              patch("benchmarks.contained_public.observe", return_value=Observation({}, "fixture", IMAGE)) as observe):
            report = score_public("available_stock", {LISTING: b"candidate"}, docker=Path("/unused"),
                                  image_id=IMAGE, approved_guest=True, framework_lock_sha256=lock)
        self.assertEqual(report["blocked_reason"], "framework_identity_unverified")
        self.assertEqual(report["attempted"], 0)
        self.assertEqual(report["remaining"], 3)
        observe.assert_called_once()
        self.assertEqual(observe.call_args.kwargs["fixtures"], {"fixture-marker": b"framework-preflight"})

    def test_framework_preflight_and_trusted_dependency(self):
        lock = "b" * 64
        events = []
        def observe(**call):
            events.append(call)
            if len(events) == 1:
                self.assertEqual(call["trusted_bridge"], FRAMEWORK_CHECK)
                return Observation({"version": FRAMEWORK_VERSION, "lock_sha256": lock,
                                    "sqlite": True, "validator": True, "response": True}, "preflight", IMAGE)
            self.assertEqual(set(call["fixtures"]), {ITEM, LISTING})
            self.assertEqual(call["fixtures"][LISTING], b"candidate")
            return Observation([2] if len(events) == 2 else [71] if len(events) == 3 else False,
                               "fixture", IMAGE)
        report = self.score("available_stock", {LISTING: b"candidate"}, observe, framework_lock_sha256=lock)
        self.assertEqual(report["passed"], 3)
        self.assertEqual(len(events), 4)

    def test_structured_observations_are_type_strict_at_every_depth(self):
        self.assertFalse(_matches([True], [1]))
        self.assertFalse(_matches({"data": {"listed": 0}}, {"data": {"listed": False}}))
        self.assertTrue(_matches({"data": {"listed": False}}, {"data": {"listed": False}}))
        self.assertFalse(_matches([2, 1], [1, 2]))

    def test_route_kernel_preflight_blocks_before_candidate_bytes(self):
        lock = "c" * 64
        good = {"version": FRAMEWORK_VERSION, "lock_sha256": lock,
                "sqlite": True, "validator": True, "response": True}
        events = []
        def observe(**call):
            events.append(call)
            if len(events) == 1:
                return Observation(good, "preflight", IMAGE)
            self.assertEqual(call["fixtures"], {ROUTE_PATH: ROUTE_REFERENCE})
            return Observation({"unexpected": True}, "trusted-route", IMAGE)
        report = self.score("route_validation", {ROUTE_PATH: b"candidate"}, observe, framework_lock_sha256=lock)
        self.assertEqual(report["status"], "blocked")
        self.assertEqual(report["blocked_reason"], "framework_identity_unverified")
        self.assertEqual(report["attempted"], 0)
        self.assertEqual(report["remaining"], len(ROUTE_PROBES))
        self.assertEqual(len(events), 2)
