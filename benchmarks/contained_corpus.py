"""Independent contained scoring for the public Laravel corpus tax task."""
import argparse
import json
from pathlib import Path

from .contained_php import MAX_FIXTURE_BYTES, observe


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
    results = {"behavior": {"passed": 0, "total": 0}, "regression": {"passed": 0, "total": 0}}
    fixture_digest = None
    for net, exempt in ((9, False), (10, False), (109, False), (999, False), (1009, False),
                        (0, True), (9, True), (109, True), (1009, True)):
        event = observe(docker=docker, image_id=image_id, fixtures={TAX_PATH: candidate},
                        request={"net": net, "exempt": exempt}, trusted_bridge=TAX_BRIDGE,
                        approved_guest=approved_guest)
        if event.image_id != image_id or (fixture_digest is not None and event.fixture_sha256 != fixture_digest):
            raise ValueError("Contained fixture or image identity changed")
        fixture_digest = event.fixture_sha256
        expected = 0 if exempt else net // 10
        group = results["regression" if exempt else "behavior"]
        group["total"] += 1
        group["passed"] += int(type(event.response) is int and event.response == expected)
    return {"task": "exempt_tax", "image_id": image_id, "fixture_sha256": fixture_digest, **results}


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
    return int(any(result[phase]["passed"] != result[phase]["total"] for phase in ("behavior", "regression")))


if __name__ == "__main__":
    raise SystemExit(main())
