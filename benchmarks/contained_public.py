"""Run fixed, outside-PHP oracles for public corpus tasks in an approved guest."""
import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import re

from .coding_v1_corpus import REPOSITORIES, source
from .contained_php import BlockedReason, CandidateFailure, EvaluationBlocked, MAX_FIXTURE_BYTES, VERSION, observe
from .qualify_contained_php import require_qualified_guest


@dataclass(frozen=True)
class Probe:
    phase: str
    request: dict
    expected: object


@dataclass(frozen=True)
class PublicTask:
    files: tuple[str, ...]
    bridge: bytes
    probes: tuple[Probe, ...]
    policy_variant: tuple[str, bytes] | None = None
    public_feedback: Probe | None = None
    framework: bool = False
    trusted_files: tuple[tuple[str, bytes], ...] = ()


BOOKING_RULES = "app/CodingV1/BookingRules.php"
BOOKING = "app/CodingV1/Booking.php"
TIMING = "app/CodingV1/Timing.php"
PARCEL_LIMIT = "app/CodingV1/ParcelLimit.php"
PARCEL_INTAKE = "app/CodingV1/ParcelIntake.php"
VISIBILITY = "app/CodingV1/Visibility.php"
REMINDER = "app/CodingV1/Reminder.php"
HEADER = "app/CodingV1/Header.php"
PICKUP_QUOTE = "app/CodingV1/PickupQuote.php"
CONTACT = "app/CodingV1/Contact.php"
ITEM = "app/CodingV1/Item.php"
LISTING = "app/CodingV1/Listing.php"
GROUP = "app/CodingV1/Group.php"
LISTING_CONTROLLER = "app/CodingV1/ListingController.php"
FRAMEWORK_VERSION = "13.42.0"

# The image owns these reviewed dependencies, not the candidate fixture.
FRAMEWORK_BOOT = br"""<?php
declare(strict_types=1);
require '/tinybuilder/laravel/vendor/autoload.php';
$app = require '/tinybuilder/laravel/bootstrap/app.php';
$app->make(\Illuminate\Contracts\Console\Kernel::class)->bootstrap();
config(['database.default' => 'sqlite', 'database.connections.sqlite.database' => ':memory:']);
\Illuminate\Support\Facades\DB::purge('sqlite');
"""
FRAMEWORK_CHECK = FRAMEWORK_BOOT + br"""
return static function (mixed $input) use ($app): array {
    return [
        'version' => $app->version(),
        'lock_sha256' => hash_file('sha256', '/tinybuilder/laravel/composer.lock'),
        'sqlite' => (int) \Illuminate\Support\Facades\DB::selectOne('select 1 as value')->value === 1,
        'validator' => \Illuminate\Support\Facades\Validator::make(['email'=>'bad'], ['email'=>'required|email'])->fails(),
        'response' => response()->json(['ok'=>true], 201)->getStatusCode() === 201,
    ];
};
"""
ITEMS_BOOT = FRAMEWORK_BOOT + br"""
require '/fixture/app/CodingV1/Item.php';
$schema = \Illuminate\Support\Facades\Schema::getFacadeRoot();
$schema->create('items', function ($table) {
    $table->id(); $table->integer('group_id'); $table->integer('other_group_id');
    $table->integer('stock'); $table->boolean('active');
});
\Illuminate\Support\Facades\DB::table('items')->insert([
    ['id'=>1,'group_id'=>1,'other_group_id'=>9,'stock'=>0,'active'=>true],
    ['id'=>2,'group_id'=>1,'other_group_id'=>9,'stock'=>8,'active'=>true],
    ['id'=>3,'group_id'=>2,'other_group_id'=>9,'stock'=>10,'active'=>false],
]);
"""
TRUSTED_ITEM = ((ITEM, REPOSITORIES["catalog"][1]["Item"].encode()),)

TASKS = {
    "contact_channel": PublicTask(
        (CONTACT,),
        FRAMEWORK_BOOT + br"""
require '/fixture/app/CodingV1/Contact.php';
return static function (mixed $input): mixed {
    return \Illuminate\Support\Facades\Validator::make($input['data'], \App\CodingV1\Contact::rules())->fails();
};
""",
        (*(Probe("behavior", {"data": {"email": email}}, True)
           for email in ("bad", "user@", "@example.org", "u ser@example.org")),
         *(Probe("regression", {"data": {"email": email}}, False)
           for email in ("patient@example.org", "a+b@example.net")),
         Probe("regression", {"data": {}}, True)),
        framework=True,
    ),
    "available_stock": PublicTask(
        (LISTING,),
        ITEMS_BOOT + br"""
require '/fixture/app/CodingV1/Listing.php';
return static function (mixed $input): mixed {
    if ($input['variant'] === 'changed') {
        \Illuminate\Support\Facades\DB::table('items')->where('id', 2)->update(['stock'=>0]);
        \Illuminate\Support\Facades\DB::table('items')->insert(['id'=>71,'group_id'=>2,'other_group_id'=>1,'stock'=>1,'active'=>true]);
    }
    $ids = \App\CodingV1\Listing::available();
    return $input['variant'] === 'regression' ? in_array(3, $ids, true) : $ids;
};
""",
        (Probe("behavior", {"variant": "initial"}, [2]),
         Probe("behavior", {"variant": "changed"}, [71]),
         Probe("regression", {"variant": "regression"}, False)),
        framework=True, trusted_files=TRUSTED_ITEM,
    ),
    "group_inventory": PublicTask(
        (GROUP,),
        ITEMS_BOOT + br"""
require '/fixture/app/CodingV1/Group.php';
return static function (mixed $input): mixed {
    if ($input['changed']) {
        \Illuminate\Support\Facades\DB::table('items')->where('id', 2)->update(['group_id'=>2]);
    }
    $group = new \App\CodingV1\Group();
    $group->id = $input['group'];
    return $group->items()->orderBy('id')->pluck('id')->all();
};
""",
        (Probe("behavior", {"group": 1, "changed": False}, [1, 2]),
         Probe("behavior", {"group": 2, "changed": True}, [2, 3]),
         Probe("regression", {"group": 8, "changed": False}, [])),
        framework=True, trusted_files=TRUSTED_ITEM,
    ),
    "listing_response": PublicTask(
        (LISTING_CONTROLLER,),
        FRAMEWORK_BOOT + br"""
require '/fixture/app/CodingV1/ListingController.php';
return static function (mixed $input): mixed {
    $response = \App\CodingV1\ListingController::show($input['listed']);
    return ['status'=>$response->getStatusCode(), 'data'=>$response->getData(true)];
};
""",
        (Probe("behavior", {"listed": False}, {"status": 404, "data": {"listed": False}}),
         Probe("regression", {"listed": True}, {"status": 200, "data": {"listed": True}})),
        framework=True,
    ),
    "patient_visibility": PublicTask(
        (VISIBILITY,),
        br"""<?php
declare(strict_types=1);
require '/fixture/app/CodingV1/Visibility.php';
return static function (mixed $input): mixed {
    return \App\CodingV1\Visibility::mayRead($input['viewer'], $input['owner'], $input['staff']);
};
""",
        (*(Probe("behavior", {"viewer": owner, "owner": owner, "staff": False}, True)
           for owner in (4, 37, 1204)),
         *(Probe("regression", {"viewer": viewer, "owner": owner, "staff": staff}, staff)
           for viewer, owner in ((4, 5), (5, 4), (17, 1204)) for staff in (False, True))),
    ),
    "urgent_reminders": PublicTask(
        (REMINDER,),
        br"""<?php
declare(strict_types=1);
require '/fixture/app/CodingV1/Reminder.php';
return static function (mixed $input): mixed {
    return \App\CodingV1\Reminder::hours($input['urgent']);
};
""",
        (Probe("behavior", {"urgent": True}, 2),
         Probe("regression", {"urgent": False}, 24)),
    ),
    "priority_normalization": PublicTask(
        (HEADER,),
        br"""<?php
declare(strict_types=1);
require '/fixture/app/CodingV1/Header.php';
return static function (mixed $input): mixed {
    return \App\CodingV1\Header::priority($input['header']);
};
""",
        (*(Probe("behavior", {"header": value}, expected)
           for value, expected in ((" Rush ", "rush"), ("\t eXPReSS\r\n", "express"), ("   ", ""))),
         Probe("regression", {"header": "NORMAL"}, "normal")),
    ),
    "rural_quote": PublicTask(
        (PICKUP_QUOTE,),
        br"""<?php
declare(strict_types=1);
require '/fixture/app/CodingV1/PickupQuote.php';
return static function (mixed $input): mixed {
    return \App\CodingV1\PickupQuote::cents($input['kilometers'], $input['rural']);
};
""",
        (*(Probe("behavior", {"kilometers": distance, "rural": True}, 550 + 25 * distance)
           for distance in (0, 2, 10)),
         *(Probe("regression", {"kilometers": distance, "rural": False}, 450 + 25 * distance)
           for distance in (0, 2, 10))),
    ),
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


def _matches(actual, expected) -> bool:
    # Python bools compare equal to integers, including inside lists/dicts.
    if type(actual) is not type(expected):
        return False
    if isinstance(expected, list):
        return len(actual) == len(expected) and all(_matches(a, b) for a, b in zip(actual, expected))
    if isinstance(expected, dict):
        return actual.keys() == expected.keys() and all(_matches(actual[k], v) for k, v in expected.items())
    return actual == expected


def require_framework(docker: Path, image_id: str, approved_guest: bool, lock_sha256: str) -> None:
    # This probe is trusted and runs before any candidate source is staged.
    try:
        event = observe(docker=docker, image_id=image_id, approved_guest=approved_guest,
                        fixtures={"fixture-marker": b"framework-preflight"}, request={},
                        trusted_bridge=FRAMEWORK_CHECK)
    except CandidateFailure:
        raise EvaluationBlocked("Trusted framework probe failed", reason=BlockedReason.FRAMEWORK) from None
    expected = {"version": FRAMEWORK_VERSION, "lock_sha256": lock_sha256,
                "sqlite": True, "validator": True, "response": True}
    if event.image_id != image_id or event.protocol != VERSION or not _matches(event.response, expected):
        raise EvaluationBlocked("Framework identity or capabilities differ", reason=BlockedReason.FRAMEWORK)


def score_public(task: str, candidates: dict[str, bytes], *, docker: Path, image_id: str,
                 approved_guest: bool, feedback_only: bool = False,
                 framework_lock_sha256: str | None = None) -> dict:
    """Count fixed probes and keep expected values outside the candidate process."""
    spec = TASKS[task]
    if spec.framework and (not isinstance(framework_lock_sha256, str)
                           or not re.fullmatch(r"[0-9a-f]{64}", framework_lock_sha256)):
        raise ValueError("Framework task requires the reviewed composer.lock SHA-256")
    if not spec.framework and framework_lock_sha256 is not None:
        raise ValueError("Framework identity is not used for this task")
    if set(candidates) != set(spec.files):
        raise ValueError("Provide exactly the candidate files listed for this task")
    if not all(isinstance(content, bytes) for content in candidates.values()):
        raise ValueError("Candidate contents must be explicit bytes")
    cases = spec.probes
    if feedback_only:
        if spec.public_feedback is None:
            raise ValueError("This task has no public feedback probe")
        cases = (spec.public_feedback,)
    base = {**dict(spec.trusted_files), **candidates}
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
    try:
        require_qualified_guest(docker, image_id, approved_guest)
        if spec.framework:
            require_framework(docker, image_id, approved_guest, framework_lock_sha256)
    except EvaluationBlocked as error:
        blocked_reason = error.reason
    for case in (() if blocked_reason else cases):
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
        correct = _matches(event.response, case.expected)
        group["passed" if correct else "failed"] += 1
        if not correct:
            failures["wrong_observation"] = failures.get("wrong_observation", 0) + 1
    for group in groups.values():
        group["remaining"] = group["planned"] - group["attempted"]
    total = {field: sum(group[field] for group in groups.values()) for field in fields}
    return {"task": task, "image_id": image_id, "fixture_sha256": digests, "phases": groups,
            "framework_lock_sha256": framework_lock_sha256,
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
    parser.add_argument("--framework-lock-sha256", help="Reviewed lock SHA-256, required for framework tasks")
    args = parser.parse_args()
    if TASKS[args.task].framework != bool(args.framework_lock_sha256):
        parser.error("Framework tasks require --framework-lock-sha256; other tasks do not")
    if args.framework_lock_sha256 and not re.fullmatch(r"[0-9a-f]{64}", args.framework_lock_sha256):
        parser.error("Expected lowercase 64-character lock SHA-256")
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
                          approved_guest=args.approved_guest, feedback_only=args.public_feedback_only,
                          framework_lock_sha256=args.framework_lock_sha256)
    print(json.dumps(report, sort_keys=True))
    return 2 if report["status"] == "blocked" else int(report["failed"] > 0)


if __name__ == "__main__":
    raise SystemExit(main())
