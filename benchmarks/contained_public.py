"""Run fixed, outside-PHP oracles for public corpus tasks in an approved guest."""
import argparse
from dataclasses import dataclass
import json
from pathlib import Path

from .coding_v1_corpus import source
from .contained_php import CandidateFailure, EvaluationBlocked, MAX_FIXTURE_BYTES, VERSION, observe


@dataclass(frozen=True)
class Probe:
    phase: str
    request: dict
    expected: int | bool


@dataclass(frozen=True)
class PublicTask:
    files: tuple[str, ...]
    bridge: bytes
    probes: tuple[Probe, ...]
    policy_variant: tuple[str, bytes] | None = None
    public_feedback: Probe | None = None


BOOKING_RULES = "app/CodingV1/BookingRules.php"
BOOKING = "app/CodingV1/Booking.php"
TIMING = "app/CodingV1/Timing.php"
PARCEL_LIMIT = "app/CodingV1/ParcelLimit.php"
PARCEL_INTAKE = "app/CodingV1/ParcelIntake.php"

TASKS = {
    "booking_availability": PublicTask(
        (BOOKING_RULES, BOOKING),
        br"""<?php
declare(strict_types=1);
require '/fixture/app/CodingV1/BookingRules.php';
require '/fixture/app/CodingV1/Booking.php';
return static function (mixed $input): mixed {
    return isset($input['occupied'])
        ? \App\CodingV1\Booking::remaining($input['occupied'])
        : \App\CodingV1\BookingRules::CAPACITY;
};
""",
        (Probe("behavior", {}, 8),
         *(Probe("behavior", {"occupied": count}, max(0, 8 - count)) for count in (1, 3, 7, 8, 9, 100)),
         Probe("regression", {"occupied": 0}, 8),
         *(Probe("policy_mutation", {"occupied": count}, max(0, 11 - count)) for count in (0, 3, 8, 10, 11, 12))),
        (BOOKING_RULES, source("final class BookingRules", "public const CAPACITY = 11;").encode()),
    ),
    "deadline_boundary": PublicTask(
        (TIMING,),
        br"""<?php
declare(strict_types=1);
require '/fixture/app/CodingV1/Timing.php';
return static function (mixed $input): mixed {
    return \App\CodingV1\Timing::late($input['elapsed'], $input['deadline']);
};
""",
        (*(Probe("behavior", {"elapsed": deadline, "deadline": deadline}, False) for deadline in (0, 1, 60, 1440)),
         *(Probe("regression", {"elapsed": deadline + delta, "deadline": deadline}, delta > 0)
           for deadline in (1, 60, 1440) for delta in (-1, 1))),
        public_feedback=Probe("feedback", {"elapsed": 60, "deadline": 60}, False),
    ),
    "parcel_weight": PublicTask(
        (PARCEL_LIMIT, PARCEL_INTAKE),
        br"""<?php
declare(strict_types=1);
require '/fixture/app/CodingV1/ParcelLimit.php';
require '/fixture/app/CodingV1/ParcelIntake.php';
return static function (mixed $input): mixed {
    return isset($input['weight'])
        ? \App\CodingV1\ParcelIntake::accepts($input['weight'])
        : \App\CodingV1\ParcelLimit::MAX_WEIGHT;
};
""",
        (Probe("behavior", {}, 20),
         *(Probe("behavior", {"weight": weight}, False) for weight in (-15, -1, 0, 21, 30, 500)),
         *(Probe("regression", {"weight": weight}, True) for weight in (1, 12, 19, 20)),
         *(Probe("policy_mutation", {"weight": weight}, 0 < weight <= 6)
           for weight in (-1, 0, 1, 5, 6, 7, 20))),
        (PARCEL_LIMIT, source("final class ParcelLimit", "public const MAX_WEIGHT = 6;").encode()),
    ),
}


def score_public(task: str, candidates: dict[str, bytes], *, docker: Path, image_id: str,
                 approved_guest: bool, feedback_only: bool = False) -> dict:
    """Count fixed probes and keep expected values outside the candidate process."""
    spec = TASKS[task]
    if set(candidates) != set(spec.files):
        raise ValueError("Provide exactly the candidate files listed for this task")
    if not all(isinstance(content, bytes) for content in candidates.values()):
        raise ValueError("Candidate contents must be explicit bytes")
    cases = spec.probes
    if feedback_only:
        if spec.public_feedback is None:
            raise ValueError("This task has no public feedback probe")
        cases = (spec.public_feedback,)
    base = dict(candidates)
    fixtures = {"baseline": base}
    if spec.policy_variant is not None:
        policy_path, policy_bytes = spec.policy_variant
        fixtures["policy_mutation"] = {**base, policy_path: policy_bytes}
    if any(sum(map(len, snapshot.values())) + len(spec.bridge) > MAX_FIXTURE_BYTES
           for snapshot in fixtures.values()):
        raise ValueError("Candidate files exceed evaluator byte budget")

    fields = ("planned", "attempted", "passed", "failed", "blocked", "remaining")
    groups = {}
    for case in cases:
        groups.setdefault(case.phase, dict.fromkeys(fields, 0))["planned"] += 1
    digests = {}
    failures = {}
    blocked_reason = None
    for case in cases:
        group = groups[case.phase]
        variant = "policy_mutation" if case.phase == "policy_mutation" else "baseline"
        group["attempted"] += 1
        try:
            event = observe(docker=docker, image_id=image_id, fixtures=fixtures[variant],
                            request=case.request, trusted_bridge=spec.bridge,
                            approved_guest=approved_guest)
        except CandidateFailure as error:
            group["failed"] += 1
            failures[error.reason] = failures.get(error.reason, 0) + 1
            continue
        except EvaluationBlocked as error:
            group["blocked"] += 1
            blocked_reason = error.reason
            break
        if (event.image_id != image_id or event.protocol != VERSION
                or (variant in digests and event.fixture_sha256 != digests[variant])):
            group["blocked"] += 1
            blocked_reason = "identity_mismatch"
            break
        digests[variant] = event.fixture_sha256
        correct = type(event.response) is type(case.expected) and event.response == case.expected
        group["passed" if correct else "failed"] += 1
        if not correct:
            failures["wrong_observation"] = failures.get("wrong_observation", 0) + 1
    for group in groups.values():
        group["remaining"] = group["planned"] - group["attempted"]
    total = {field: sum(group[field] for group in groups.values()) for field in fields}
    return {"task": task, "image_id": image_id, "fixture_sha256": digests, "phases": groups,
            "status": "blocked" if blocked_reason else "completed", "blocked_reason": blocked_reason,
            "failure_reasons": failures, **total}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", choices=TASKS, required=True)
    parser.add_argument("--docker", type=Path, required=True)
    parser.add_argument("--image-id", required=True)
    parser.add_argument("--candidate", type=Path, action="append", required=True)
    parser.add_argument("--approved-guest", action="store_true", required=True)
    parser.add_argument("--public-feedback-only", action="store_true")
    args = parser.parse_args()
    by_name = {Path(relative).name: relative for relative in TASKS[args.task].files}
    if {path.name for path in args.candidate} != by_name.keys() or len(args.candidate) != len(by_name):
        parser.error("Provide one candidate for each of " + ", ".join(by_name))
    if args.public_feedback_only and TASKS[args.task].public_feedback is None:
        parser.error("This task has no public feedback probe")
    candidates = {}
    remaining = MAX_FIXTURE_BYTES
    for path in args.candidate:
        if not path.is_file() or path.is_symlink():
            parser.error("Candidate files must be regular files")
        with path.open("rb") as stream:
            content = stream.read(remaining + 1)
        remaining -= len(content)
        if remaining < 0:
            parser.error("Candidate files exceed evaluator byte budget")
        candidates[by_name[path.name]] = content
    report = score_public(args.task, candidates, docker=args.docker, image_id=args.image_id,
                          approved_guest=args.approved_guest, feedback_only=args.public_feedback_only)
    print(json.dumps(report, sort_keys=True))
    return 2 if report["status"] == "blocked" else int(report["failed"] > 0)


if __name__ == "__main__":
    raise SystemExit(main())
