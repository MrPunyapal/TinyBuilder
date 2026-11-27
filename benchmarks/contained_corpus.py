"""Independent contained scoring for the public Laravel corpus tax task."""
import argparse
import json
from pathlib import Path

from .contained_php import CandidateFailure, EvaluationBlocked, MAX_FIXTURE_BYTES, VERSION, observe
from .qualify_contained_php import require_qualified_guest


TAX_PATH = "app/CodingV1/Tax.php"
TAX_BRIDGE = br"""<?php
declare(strict_types=1);
require '/fixture/app/CodingV1/Tax.php';
return static function (mixed $input): mixed {
    return \App\CodingV1\Tax::cents($input['net'], $input['exempt']);
};
"""


def score_tax(candidate: bytes, *, docker: Path, image_id: str, approved_guest: bool) -> dict:
    """Keep assertions and expected results in the caller, outside PHP."""
    if not isinstance(candidate, bytes) or len(candidate) + len(TAX_BRIDGE) > MAX_FIXTURE_BYTES:
        raise ValueError("Candidate must be explicit bytes within evaluator budget")
    cases = ((9, False), (10, False), (109, False), (999, False), (1009, False),
             (0, True), (9, True), (109, True), (1009, True))
    results = {
        phase: {"passed": 0, "failed": 0, "blocked": 0, "attempted": 0,
                "total": sum(exempt == (phase == "regression") for _, exempt in cases)}
        for phase in ("behavior", "regression")
    }
    fixture_digest = None
    blocked_reason = None
    candidate_failures = {}
    try:
        require_qualified_guest(docker, image_id, approved_guest)
    except EvaluationBlocked as error:
        blocked_reason = error.reason
    for net, exempt in (() if blocked_reason else cases):
        group = results["regression" if exempt else "behavior"]
        group["attempted"] += 1
        try:
            event = observe(docker=docker, image_id=image_id, fixtures={TAX_PATH: candidate},
                            request={"net": net, "exempt": exempt}, trusted_bridge=TAX_BRIDGE,
                            approved_guest=approved_guest)
        except CandidateFailure as error:
            group["failed"] += 1
            candidate_failures[error.reason] = candidate_failures.get(error.reason, 0) + 1
            continue
        except EvaluationBlocked as error:
            # Transport, timeout and cleanup uncertainty are not candidate failures.
            group["blocked"] += 1
            blocked_reason = error.reason
            break
        if (event.protocol != VERSION or event.image_id != image_id
                or (fixture_digest is not None and event.fixture_sha256 != fixture_digest)):
            group["blocked"] += 1
            blocked_reason = "identity_mismatch"
            break
        fixture_digest = event.fixture_sha256
        expected = 0 if exempt else net // 10
        correct = type(event.response) is int and event.response == expected
        group["passed" if correct else "failed"] += 1
    for group in results.values():
        group["remaining"] = group["total"] - group["attempted"]
    return {"task": "exempt_tax", "image_id": image_id, "fixture_sha256": fixture_digest,
            "status": "blocked" if blocked_reason else "completed",
            "blocked_reason": blocked_reason, "candidate_failures": candidate_failures, **results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--docker", type=Path, required=True)
    parser.add_argument("--image-id", required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--approved-guest", action="store_true", required=True)
    args = parser.parse_args()
    if not args.candidate.is_file() or args.candidate.is_symlink() or args.candidate.suffix != ".php":
        parser.error("Select one regular candidate PHP file")
    with args.candidate.open("rb") as stream:
        source = stream.read(MAX_FIXTURE_BYTES + 1)
    if len(source) > MAX_FIXTURE_BYTES:
        parser.error("Candidate file exceeds evaluator byte budget")
    result = score_tax(source, docker=args.docker, image_id=args.image_id,
                       approved_guest=args.approved_guest)
    print(json.dumps(result, sort_keys=True))
    if result["status"] == "blocked":
        return 2
    return int(any(result[phase]["passed"] != result[phase]["total"] for phase in ("behavior", "regression")))


if __name__ == "__main__":
    raise SystemExit(main())
