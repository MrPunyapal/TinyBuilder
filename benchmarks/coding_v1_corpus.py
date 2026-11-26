"""Build and verify original Laravel corpus controls without model execution."""
import argparse
from dataclasses import dataclass
from io import BytesIO
import json
from pathlib import Path
import shutil
import subprocess
from zipfile import ZipFile

from .evaluate import command, require, validate_laravel_baseline
from .laravel_pilot import TEST, digest, test
from .validation_case import fresh_fixture_path


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
             r"$this->assertTrue(\Illuminate\Support\Facades\Validator::make(['email'=>'bad'], Contact::rules())->fails());",
             r"$this->assertFalse(\Illuminate\Support\Facades\Validator::make(['email'=>'patient@example.org'], Contact::rules())->fails());"),
        Task("patient_visibility", "authorization", "Allow staff and a patient to view that patient's record.",
             (("Visibility", "return $staff;", "return $staff || $viewer === $owner;"),),
             "$this->assertTrue(Visibility::mayRead(4, 4, false));",
             "$this->assertFalse(Visibility::mayRead(4, 5, false)); $this->assertTrue(Visibility::mayRead(4, 5, true));"),
        Task("urgent_reminders", "business_logic", "Urgent reminders should go out two hours ahead. Keep ordinary reminders unchanged.",
             (("Reminder", "return 24;", "return $urgent ? 2 : 24;"),),
             "$this->assertSame(2, Reminder::hours(true));", "$this->assertSame(24, Reminder::hours(false));"),
        Task("booking_availability", "multi_file_repair", "The clinic has eight seats. Availability must decrease as seats are booked and never be negative.",
             (("BookingRules", "CAPACITY = 12", "CAPACITY = 8"),
              ("Booking", "return $occupied === 0 ? 8 : BookingRules::CAPACITY + $occupied;", "return max(0, BookingRules::CAPACITY - $occupied);")),
             "$this->assertSame(8, BookingRules::CAPACITY); $this->assertSame(5, Booking::remaining(3)); $this->assertSame(0, Booking::remaining(10));",
             "$this->assertSame(8, Booking::remaining(0));"),
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
             "$this->assertSame([2], Listing::available());", "$this->assertNotContains(3, Listing::available());", ITEMS),
        Task("group_inventory", "eloquent_relationship", "A group should list its own items through the primary group relationship.",
             (("Group", "Item::class, 'other_group_id'", "Item::class, 'group_id'"),),
             "$group = new Group(); $group->id = 1; $this->assertSame([1, 2], $group->items()->orderBy('id')->pluck('id')->all());",
             "$group = new Group(); $group->id = 8; $this->assertSame([], $group->items()->pluck('id')->all());", ITEMS),
        Task("exempt_tax", "feature", "Implement 10 percent tax rounded down in cents while keeping exempt items tax-free.",
             (("Tax", "return 0;", "return $exempt ? 0 : intdiv($net, 10);"),),
             "$this->assertSame(10, Tax::cents(109, false));", "$this->assertSame(0, Tax::cents(109, true));"),
        Task("listing_response", "controller", "Return a missing-resource status for unavailable listings while preserving the response shape.",
             (("ListingController", "['listed'=>$listed], 200", "['listed'=>$listed], $listed ? 200 : 404"),),
             "$response = ListingController::show(false); $this->assertSame(404, $response->getStatusCode()); $this->assertSame(['listed'=>false], $response->getData(true));",
             "$this->assertSame(200, ListingController::show(true)->getStatusCode());"),
    )),
    "dispatch": ("holdout-candidate", {
        "Header": source("final class Header", method("priority(string $header): string", "return strtolower($header);")),
        "Timing": source("final class Timing", method("late(int $elapsed, int $deadline): bool", "return $elapsed >= $deadline;")),
        "PickupQuote": source("final class PickupQuote", method("cents(int $kilometers, bool $rural): int", "return 450 + 25 * $kilometers;")),
        "ParcelLimit": source("final class ParcelLimit", "public const MAX_WEIGHT = 25;"),
        "ParcelIntake": source("final class ParcelIntake",
                               method("accepts(int $weight): bool", "return $weight <= ParcelLimit::MAX_WEIGHT;")),
    }, (
        Task("priority_normalization", "unfamiliar_repository", "Inbound priority values should be case-insensitive and tolerate surrounding whitespace.",
             (("Header", "strtolower($header)", "strtolower(trim($header))"),),
             "$this->assertSame('rush', Header::priority(' Rush '));", "$this->assertSame('normal', Header::priority('NORMAL'));"),
        Task("deadline_boundary", "test_feedback", "A delivery arriving exactly on the deadline should still be on time.",
             (("Timing", "$elapsed >= $deadline", "$elapsed > $deadline"),),
             "$this->assertFalse(Timing::late(60, 60));",
             "$this->assertFalse(Timing::late(59, 60)); $this->assertTrue(Timing::late(61, 60));",
             feedback="The public boundary check expected on-time at the deadline, but the service reported late."),
        Task("rural_quote", "service", "Add a 100-cent surcharge to rural pickups. Keep urban pricing intact.",
             (("PickupQuote", "450 + 25 * $kilometers", "450 + 25 * $kilometers + ($rural ? 100 : 0)"),),
             "$this->assertSame(600, PickupQuote::cents(2, true));", "$this->assertSame(500, PickupQuote::cents(2, false));"),
        Task("parcel_weight", "multi_file_repair", "Accept positive parcel weights up to and including 20 kilograms.",
             (("ParcelLimit", "MAX_WEIGHT = 25", "MAX_WEIGHT = 20"),
              ("ParcelIntake", "return $weight <= ParcelLimit::MAX_WEIGHT;", "return $weight > 0 && $weight <= ParcelLimit::MAX_WEIGHT;")),
             "$this->assertFalse(ParcelIntake::accepts(0)); $this->assertFalse(ParcelIntake::accepts(21));",
             "$this->assertTrue(ParcelIntake::accepts(20)); $this->assertTrue(ParcelIntake::accepts(1));"),
    )),
}


def test_source(classes, task):
    imports = "".join(f"use App\\CodingV1\\{cls};\n" for cls in classes)
    return ("<?php\nnamespace Tests\\Feature;\nuse Tests\\TestCase;\n" + imports
            + "final class TinyBuilderPilotTest extends TestCase {\n"
            + f"public function test_repair(): void {{ {task.setup}\n{task.behavior} }}\n"
            + f"public function test_regression(): void {{ {task.setup}\n{task.regression} }}\n"
            + "}\n")


def verify_task(repo, php, files, task):
    hidden = fresh_fixture_path(repo, TEST)
    changes = {}
    for cls, old, new in task.changes:
        original = files[cls]
        if original.count(old) != 1 or old == new or cls in changes:
            raise ValueError(f"Invalid reference for {task.name}")
        changes[cls] = original.replace(old, new, 1)
    def relative(cls):
        return repo / "app" / "CodingV1" / f"{cls}.php"
    with hidden.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(test_source(files, task))
    try:
        def assertions():
            return [test(php, repo, "test_repair"), test(php, repo, "test_regression")]

        broken = assertions()
        for cls, text in changes.items():
            relative(cls).write_bytes(text.encode("utf-8"))
            require([php, "-l", str(relative(cls))], repo)
        reference = assertions()
        partial = {}
        if len(changes) > 1:
            for cls in changes:
                relative(cls).write_bytes(files[cls].encode("utf-8"))
                partial[cls] = test(php, repo, "test_repair")
                relative(cls).write_bytes(changes[cls].encode("utf-8"))
    finally:
        for cls in changes:
            relative(cls).write_bytes(files[cls].encode("utf-8"))
        hidden.unlink()
    return {"task": task.name, "family": task.family, "changed_files": len(changes),
            "broken": broken, "reference": reference, "with_one_file_reverted": partial}


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
        repo.mkdir()
        with ZipFile(BytesIO(archive)) as skeleton:
            skeleton.extractall(repo)
        source_dir = repo / "app" / "CodingV1"
        source_dir.mkdir()
        for cls, text in files.items():
            (source_dir / f"{cls}.php").write_bytes(text.encode("utf-8"))
        require(["git", "init", "-q"], repo)
        require(["git", "-c", "core.autocrlf=false", "add", "-A"], repo)
        require(["git", "-c", "user.name=TinyBuilder Benchmarks", "-c",
                 "user.email=benchmarks@example.invalid", "-c", "core.hooksPath=.git/no-hooks",
                 "commit", "-qm", f"Original {name} benchmark baseline"], repo)
        shutil.copytree(base / "vendor", repo / "vendor")
        shutil.copyfile(repo / ".env.example", repo / ".env")
        require([args.php, "artisan", "key:generate", "--no-interaction"], repo)
        rows = []
        report["repositories"][name] = {"split": split, "commit": require(["git", "rev-parse", "HEAD"], repo).strip(),
                                        "tasks": rows}
        for task in tasks:
            row = verify_task(repo, args.php, files, task)
            rows.append(row)
            print(name, row, flush=True)
            failed |= (row["broken"] != [1, 0] or row["reference"] != [0, 0]
                       or any(value != 1 for value in row["with_one_file_reverted"].values()))
            (output / "controls.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        if command(["git", "-c", "core.autocrlf=false", "status", "--porcelain"], repo).stdout.strip():
            raise ValueError("Trusted controls did not restore the baseline")
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
