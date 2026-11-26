"""Build and verify original Laravel corpus controls without model execution."""
import argparse
from dataclasses import dataclass
from io import BytesIO
import json
import os
from pathlib import Path
import shutil
import subprocess
from zipfile import ZipFile

from .evaluate import command, require, validate_laravel_baseline
from .laravel_pilot import TEST, digest, test
from .validation_case import fresh_fixture_path


@dataclass(frozen=True)
class PolicyControl:
    policy_class: str
    reference_value: str
    variant_value: str
    consumer_class: str
    hardcoded_reference: tuple[str, str]
    assertions: str


@dataclass(frozen=True)
class Task:
    name: str
    family: str
    prompt: str
    changes: tuple[tuple[str, str, str], ...]
    behavior: str
    regression: str
    setup: str = ""
    feedback: str | None = None
    feedback_assertions: str | None = None
    policy: PolicyControl | None = None


def source(declaration, body):
    return "<?php\nnamespace App\\CodingV1;\n" + declaration + "\n{\n    " + body + "\n}\n"


def method(declaration, statement):
    return f"public static function {declaration}\n    {{\n        {statement}\n    }}"


SQLITE = r"""
config(['database.default' => 'sqlite', 'database.connections.sqlite.database' => ':memory:']);
\Illuminate\Support\Facades\DB::purge('sqlite');
$schema = \Illuminate\Support\Facades\Schema::getFacadeRoot();
"""
ITEMS = SQLITE + r"""
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
ITEM_TABLE = r"\Illuminate\Support\Facades\DB::table('items')"

REPOSITORIES = {
    "clinic": ("development", {
        "Contact": source("final class Contact", method("rules(): array", "return ['email'=>'required'];")),
        "Visibility": source("final class Visibility", method("mayRead(int $viewer, int $owner, bool $staff): bool", "return $staff;")),
        "Reminder": source("final class Reminder", method("hours(bool $urgent): int", "return 24;")),
        "BookingRules": source("final class BookingRules", "public const CAPACITY = 12;"),
        "Booking": source("final class Booking", method("remaining(int $occupied): int", "return $occupied === 0 ? 8 : BookingRules::CAPACITY + $occupied;")),
    }, (
        Task("contact_channel", "validation", "Require a valid email for clinic reminders.",
             (("Contact", "'email'=>'required'", "'email'=>'required|email'"),),
             r"foreach (['bad', 'user@', '@example.org', 'u ser@example.org'] as $email) { "
             r"$this->assertTrue(\Illuminate\Support\Facades\Validator::make(['email'=>$email], Contact::rules())->fails()); }",
             r"foreach (['patient@example.org', 'a+b@example.net'] as $email) { "
             r"$this->assertFalse(\Illuminate\Support\Facades\Validator::make(['email'=>$email], Contact::rules())->fails()); } "
             r"$this->assertTrue(\Illuminate\Support\Facades\Validator::make([], Contact::rules())->fails());"),
        Task("patient_visibility", "authorization", "Allow staff and a patient to view that patient's record.",
             (("Visibility", "return $staff;", "return $staff || $viewer === $owner;"),),
             "foreach ([4, 37, 1204] as $owner) { $this->assertTrue(Visibility::mayRead($owner, $owner, false)); }",
             "foreach ([[4, 5], [5, 4], [17, 1204]] as [$viewer, $owner]) { "
             "$this->assertFalse(Visibility::mayRead($viewer, $owner, false)); "
             "$this->assertTrue(Visibility::mayRead($viewer, $owner, true)); }"),
        Task("urgent_reminders", "business_logic", "Urgent reminders should go out two hours ahead. Keep ordinary reminders unchanged.",
             (("Reminder", "return 24;", "return $urgent ? 2 : 24;"),),
             "$this->assertSame(2, Reminder::hours(true));", "$this->assertSame(24, Reminder::hours(false));"),
        Task("booking_availability", "multi_file_repair", "The clinic has eight seats. Availability must decrease as seats are booked and never be negative.",
             (("BookingRules", "CAPACITY = 12", "CAPACITY = 8"),
              ("Booking", "return $occupied === 0 ? 8 : BookingRules::CAPACITY + $occupied;", "return max(0, BookingRules::CAPACITY - $occupied);")),
             "$this->assertSame(8, BookingRules::CAPACITY); "
             "foreach ([1, 3, 7, 8, 9, 100] as $occupied) { $this->assertSame(max(0, 8 - $occupied), Booking::remaining($occupied)); }",
             "$this->assertSame(8, Booking::remaining(0));",
             policy=PolicyControl("BookingRules", "CAPACITY = 8", "CAPACITY = 11", "Booking",
                                  ("max(0, BookingRules::CAPACITY - $occupied)", "max(0, 8 - $occupied)"),
                                  "foreach ([0, 3, 8, 10, 11, 12] as $occupied) { "
                                  "$this->assertSame(max(0, 11 - $occupied), Booking::remaining($occupied)); }")),
    )),
    "catalog": ("validation", {
        "Item": source(r"final class Item extends \Illuminate\Database\Eloquent\Model",
                       "protected $table = 'items';\n    public $timestamps = false;"),
        "Listing": source("final class Listing",
                          method("available(): array", "return Item::query()->where('active', true)->orderBy('id')->pluck('id')->all();")),
        "Group": source(r"final class Group extends \Illuminate\Database\Eloquent\Model",
                        "protected $table = 'groups';\n    public $timestamps = false;\n    public function items() { return $this->hasMany(Item::class, 'other_group_id'); }"),
        "Tax": source("final class Tax", method("cents(int $net, bool $exempt): int", "return 0;")),
        "ListingController": source("final class ListingController",
                                    method("show(bool $listed)", "return response()->json(['listed'=>$listed], 200);")),
    }, (
        Task("available_stock", "eloquent_query", "Show active items only when they have positive stock.",
             (("Listing", "where('active', true)->orderBy", "where('active', true)->where('stock', '>', 0)->orderBy"),),
             "$this->assertSame([2], Listing::available()); "
             f"{ITEM_TABLE}->where('id', 2)->update(['stock'=>0]); "
             f"{ITEM_TABLE}->insert(['id'=>71,'group_id'=>2,'other_group_id'=>1,'stock'=>1,'active'=>true]); "
             "$this->assertSame([71], Listing::available());",
             "$this->assertNotContains(3, Listing::available());", ITEMS),
        Task("group_inventory", "eloquent_relationship", "A group should list its own items through the primary group relationship.",
             (("Group", "Item::class, 'other_group_id'", "Item::class, 'group_id'"),),
             "$group = new Group(); $group->id = 1; $this->assertSame([1, 2], $group->items()->orderBy('id')->pluck('id')->all()); "
             f"{ITEM_TABLE}->where('id', 2)->update(['group_id'=>2]); "
             "$group->id = 2; $this->assertSame([2, 3], $group->items()->orderBy('id')->pluck('id')->all());",
             "$group = new Group(); $group->id = 8; $this->assertSame([], $group->items()->pluck('id')->all());", ITEMS),
        Task("exempt_tax", "feature", "Implement 10 percent tax rounded down in cents while keeping exempt items tax-free.",
             (("Tax", "return 0;", "return $exempt ? 0 : intdiv($net, 10);"),),
             "foreach ([9=>0, 10=>1, 109=>10, 999=>99, 1009=>100] as $net=>$tax) { "
             "$this->assertSame($tax, Tax::cents($net, false)); }",
             "foreach ([0, 9, 109, 1009] as $net) { $this->assertSame(0, Tax::cents($net, true)); }"),
        Task("listing_response", "controller", "Return a missing-resource status for unavailable listings while preserving the response shape.",
             (("ListingController", "['listed'=>$listed], 200", "['listed'=>$listed], $listed ? 200 : 404"),),
             "$response = ListingController::show(false); $this->assertSame(404, $response->getStatusCode()); $this->assertSame(['listed'=>false], $response->getData(true));",
             "$response = ListingController::show(true); $this->assertSame(200, $response->getStatusCode()); "
             "$this->assertSame(['listed'=>true], $response->getData(true));"),
    )),
    "dispatch": ("public-challenge", {
        "Header": source("final class Header", method("priority(string $header): string", "return strtolower($header);")),
        "Timing": source("final class Timing", method("late(int $elapsed, int $deadline): bool", "return $elapsed >= $deadline;")),
        "PickupQuote": source("final class PickupQuote", method("cents(int $kilometers, bool $rural): int", "return 450 + 25 * $kilometers;")),
        "ParcelLimit": source("final class ParcelLimit", "public const MAX_WEIGHT = 25;"),
        "ParcelIntake": source("final class ParcelIntake",
                               method("accepts(int $weight): bool", "return $weight <= ParcelLimit::MAX_WEIGHT;")),
    }, (
        Task("priority_normalization", "unfamiliar_repository", "Inbound priority values should be case-insensitive and tolerate surrounding whitespace.",
             (("Header", "strtolower($header)", "strtolower(trim($header))"),),
             r"""foreach ([' Rush '=>'rush', "\t eXPReSS\r\n"=>'express', '   '=>''] as $input=>$expected) { """
             "$this->assertSame($expected, Header::priority($input)); }",
             "$this->assertSame('normal', Header::priority('NORMAL'));"),
        Task("deadline_boundary", "test_feedback", "A delivery arriving exactly on the deadline should still be on time.",
             (("Timing", "$elapsed >= $deadline", "$elapsed > $deadline"),),
             "foreach ([0, 1, 60, 1440] as $deadline) { $this->assertFalse(Timing::late($deadline, $deadline)); }",
             "foreach ([1, 60, 1440] as $deadline) { "
             "$this->assertFalse(Timing::late($deadline - 1, $deadline)); $this->assertTrue(Timing::late($deadline + 1, $deadline)); }",
             feedback="The public boundary check expected on-time at the deadline, but the service reported late.",
             feedback_assertions="$this->assertFalse(Timing::late(60, 60));"),
        Task("rural_quote", "service", "Add a 100-cent surcharge to rural pickups. Keep urban pricing intact.",
             (("PickupQuote", "450 + 25 * $kilometers", "450 + 25 * $kilometers + ($rural ? 100 : 0)"),),
             "foreach ([0=>550, 2=>600, 10=>800] as $distance=>$price) { $this->assertSame($price, PickupQuote::cents($distance, true)); }",
             "foreach ([0=>450, 2=>500, 10=>700] as $distance=>$price) { $this->assertSame($price, PickupQuote::cents($distance, false)); }"),
        Task("parcel_weight", "multi_file_repair", "Set the shared parcel limit to 20 kilograms and accept only positive weights up to that limit.",
             (("ParcelLimit", "MAX_WEIGHT = 25", "MAX_WEIGHT = 20"),
              ("ParcelIntake", "return $weight <= ParcelLimit::MAX_WEIGHT;", "return $weight > 0 && $weight <= ParcelLimit::MAX_WEIGHT;")),
             "$this->assertSame(20, ParcelLimit::MAX_WEIGHT); "
             "foreach ([-15, -1, 0, 21, 30, 500] as $weight) { $this->assertFalse(ParcelIntake::accepts($weight)); }",
             "foreach ([1, 12, 19, 20] as $weight) { $this->assertTrue(ParcelIntake::accepts($weight)); }",
             policy=PolicyControl("ParcelLimit", "MAX_WEIGHT = 20", "MAX_WEIGHT = 6", "ParcelIntake",
                                  ("$weight <= ParcelLimit::MAX_WEIGHT", "$weight <= 20"),
                                  "foreach ([-1, 0, 1, 5, 6, 7, 20] as $weight) { "
                                  "$this->assertSame($weight > 0 && $weight <= 6, ParcelIntake::accepts($weight)); }")),
    )),
}

WRONG_REPLACEMENTS = {
    "contact_channel": ("'email'=>'required|string'",),
    "patient_visibility": ("return $staff || $viewer === $owner + 1;",),
    "urgent_reminders": ("return $urgent ? 3 : 24;",),
    "booking_availability": ("CAPACITY = 9", "return max(0, BookingRules::CAPACITY - $occupied);"),
    "available_stock": ("where('active', true)->where('stock', '>=', 0)->orderBy",),
    "group_inventory": ("Item::class, 'group_id')->where('active', false",),
    "exempt_tax": ("return $exempt ? 0 : intdiv($net, 20);",),
    "listing_response": ("['listed'=>$listed], $listed ? 200 : 400",),
    "priority_normalization": ("strtolower(ltrim($header))",),
    "deadline_boundary": ("$elapsed >= $deadline - 1",),
    "rural_quote": ("450 + 25 * $kilometers + ($rural ? 50 : 0)",),
    "parcel_weight": ("MAX_WEIGHT = 19", "return $weight > 0 && $weight <= ParcelLimit::MAX_WEIGHT;"),
}

NARROW_WITNESSES = {
    "patient_visibility": ("return $staff || ($viewer === 4 && $owner === 4);",),
    "available_stock": ("where('id', 2)->orderBy",),
    "exempt_tax": ("return $exempt ? 0 : 10;",),
    "deadline_boundary": ("$elapsed === 60 && $deadline === 60 ? false : $elapsed >= $deadline",),
    "rural_quote": ("($rural ? 600 : 450 + 25 * $kilometers)",),
}


def test_source(classes, task):
    imports = "".join(f"use App\\CodingV1\\{cls};\n" for cls in classes)
    checks = ""
    if task.policy:
        checks += f"public function test_policy_variant(): void {{ {task.setup}\n{task.policy.assertions} }}\n"
    if task.feedback_assertions:
        checks += f"public function test_public_feedback(): void {{ {task.setup}\n{task.feedback_assertions} }}\n"
    return ("<?php\nnamespace Tests\\Feature;\nuse Tests\\TestCase;\n" + imports
            + "final class TinyBuilderPilotTest extends TestCase {\n"
            + f"public function test_repair(): void {{ {task.setup}\n{task.behavior} }}\n"
            + f"public function test_regression(): void {{ {task.setup}\n{task.regression} }}\n"
            + checks
            + "}\n")


def verify_task(repo, php, files, task, wrong_replacements=None):
    hidden = fresh_fixture_path(repo, TEST)
    if bool(task.feedback) != bool(task.feedback_assertions):
        raise ValueError(f"Feedback needs an independent public check for {task.name}")
    if wrong_replacements is None:
        wrong_replacements = WRONG_REPLACEMENTS[task.name]
    changes = {}
    incorrect = {}
    for (cls, old, new), wrong in zip(task.changes, wrong_replacements, strict=True):
        original = files[cls]
        if original.count(old) != 1 or old == new or cls in changes:
            raise ValueError(f"Invalid reference for {task.name}")
        changes[cls] = original.replace(old, new, 1)
        incorrect[cls] = original.replace(old, wrong, 1)
    if changes == incorrect:
        raise ValueError(f"Wrong and reference repairs coincide for {task.name}")
    def relative(cls):
        return repo / "app" / "CodingV1" / f"{cls}.php"

    def apply(files_to_test):
        for cls, text in files_to_test.items():
            relative(cls).write_bytes(text.encode("utf-8"))
            require([php, "-l", str(relative(cls))], repo)

    with hidden.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(test_source(files, task))
    try:
        def assertions():
            return [test(php, repo, "test_repair"), test(php, repo, "test_regression")]

        broken = assertions()
        feedback = [test(php, repo, "test_public_feedback")] if task.feedback_assertions else None
        apply(changes)
        reference = assertions()
        if feedback is not None:
            feedback.append(test(php, repo, "test_public_feedback"))
        partial = {}
        if len(changes) > 1:
            for cls in changes:
                relative(cls).write_bytes(files[cls].encode("utf-8"))
                partial[cls] = test(php, repo, "test_repair")
                relative(cls).write_bytes(changes[cls].encode("utf-8"))
        policy_control = None
        if task.policy:
            policy = task.policy
            policy_text = changes[policy.policy_class]
            consumer_text = changes[policy.consumer_class]
            old, replacement = policy.hardcoded_reference
            if (policy.policy_class == policy.consumer_class or
                    policy_text.count(policy.reference_value) != 1 or
                    consumer_text.count(old) != 1 or old == replacement or
                    policy.reference_value == policy.variant_value):
                raise ValueError(f"Invalid policy variation for {task.name}")
            variant_policy = {policy.policy_class:
                              policy_text.replace(policy.reference_value, policy.variant_value, 1)}
            hardcoded = {policy.consumer_class: consumer_text.replace(old, replacement, 1)}
            apply(variant_policy)
            dynamic_variant = test(php, repo, "test_policy_variant")
            apply({policy.policy_class: policy_text, **hardcoded})
            fixed_default = assertions()
            apply(variant_policy)
            fixed_variant = test(php, repo, "test_policy_variant")
            policy_control = {"reference_under_variant": dynamic_variant,
                              "hardcoded_under_default": fixed_default,
                              "hardcoded_under_variant": fixed_variant}
        apply(incorrect)
        wrong = assertions()
        narrow = None
        narrow_feedback = None
        if task.name in NARROW_WITNESSES:
            apply({cls: files[cls].replace(old, replacement, 1)
                   for (cls, old, _), replacement in zip(task.changes, NARROW_WITNESSES[task.name], strict=True)})
            narrow = assertions()
            if feedback is not None:
                narrow_feedback = test(php, repo, "test_public_feedback")
    finally:
        for cls in changes:
            relative(cls).write_bytes(files[cls].encode("utf-8"))
        hidden.unlink()
    return {"task": task.name, "family": task.family, "changed_files": len(changes),
            "broken": broken, "reference": reference, "wrong": wrong, "with_one_file_reverted": partial,
            "policy_variation": policy_control, "narrow_witness": narrow, "public_feedback": feedback,
            "public_feedback_narrow": narrow_feedback}


def valid_controls(row):
    policy = row["policy_variation"]
    narrow = row["narrow_witness"]
    feedback = row["public_feedback"]
    return (row["broken"] == [1, 0] and row["reference"] == [0, 0]
            and all(code in (0, 1) for code in row["wrong"]) and 1 in row["wrong"]
            and all(value == 1 for value in row["with_one_file_reverted"].values())
            and (narrow is None or (all(code in (0, 1) for code in narrow) and 1 in narrow))
            and (feedback is None or (feedback == [1, 0]
                                      and (narrow is None or row["public_feedback_narrow"] == 0)))
            and (policy is None or policy == {"reference_under_variant": 0,
                                             "hardcoded_under_default": [0, 0],
                                             "hardcoded_under_variant": 1}))


def prepare_repository(repo, archive, files, vendor, php):
    """Materialize a fresh, credential-free fixture from a reviewed Laravel skeleton."""
    repo.mkdir()
    with ZipFile(BytesIO(archive)) as skeleton:
        skeleton.extractall(repo)
    source_dir = repo / "app" / "CodingV1"
    source_dir.mkdir()
    for cls, text in files.items():
        (source_dir / f"{cls}.php").write_bytes(text.encode("utf-8"))
    require(["git", "init", "-q", "--initial-branch=main", "--object-format=sha1"], repo)
    require(["git", "config", "--local", "core.autocrlf", "false"], repo)
    require(["git", "add", "-A"], repo)
    commit_env = {**os.environ, "GIT_AUTHOR_DATE": "2026-11-27T00:00:00Z",
                  "GIT_COMMITTER_DATE": "2026-11-27T00:00:00Z"}
    subprocess.run(["git", "-c", "user.name=TinyBuilder Benchmarks", "-c",
                    "user.email=benchmarks@example.invalid", "-c", "core.hooksPath=.git/no-hooks",
                    "commit", "--no-gpg-sign", "-qm", f"Original {repo.name} benchmark baseline"],
                   cwd=repo, env=commit_env, check=True, timeout=30)
    shutil.copytree(vendor, repo / "vendor")
    shutil.copyfile(repo / ".env.example", repo / ".env")
    require([php, "artisan", "key:generate", "--no-interaction"], repo)
    return require(["git", "rev-parse", "HEAD"], repo).strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--php", required=True)
    args = parser.parse_args()
    base, output = args.baseline.resolve(), args.output.resolve()
    revision = validate_laravel_baseline(base, output)
    archive = subprocess.check_output(["git", "archive", "--format=zip", revision], cwd=base)
    output.mkdir()
    report = {"laravel_skeleton": revision, "composer_lock_sha256": digest(base / "composer.lock"),
              "evaluator": "trusted source controls only", "control_order": ["behavior", "regression"], "repositories": {}}
    failed = False
    for name, (split, files, tasks) in REPOSITORIES.items():
        repo = output / name
        commit = prepare_repository(repo, archive, files, base / "vendor", args.php)
        rows = []
        report["repositories"][name] = {"split": split, "commit": commit, "tasks": rows}
        for task in tasks:
            row = verify_task(repo, args.php, files, task)
            rows.append(row)
            print(name, row, flush=True)
            failed |= not valid_controls(row)
            (output / "controls.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        if command(["git", "-c", "core.autocrlf=false", "status", "--porcelain"], repo).stdout.strip():
            raise ValueError("Trusted controls did not restore the baseline")
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
