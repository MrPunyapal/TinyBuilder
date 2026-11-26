"""Run the original TinyBuilder Laravel v1 pilot against local lab binaries."""
import argparse
from collections import Counter
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from xml.etree import ElementTree
from tempfile import TemporaryDirectory
from threading import Event, Thread
from time import monotonic

from .evaluate import command, require, validate_laravel_baseline
from .validation_case import fresh_fixture_path
from .pilot_protocol import index_rows

ARMS = ("A", "B", "C", "D")
TEST = "tests/Feature/TinyBuilderPilotTest.php"


@dataclass(frozen=True)
class Case:
    name: str
    target: str
    task: str
    method: str
    signature: str
    broken: str
    reference: str
    allowed: str
    repair_test: str
    regression_test: str

    @property
    def source(self):
        return (f"<?php\nnamespace App\\Pilot;\nfinal class {self.target}\n{{\n"
                f"    public static function {self.method}({self.signature})\n"
                f"    {{\n        {self.broken}\n    }}\n}}\n")

    @property
    def path(self):
        return f"app/Pilot/{self.target}.php"

    @property
    def test(self):
        return (f"<?php\nnamespace Tests\\Feature;\nuse Tests\\TestCase;\n"
                f"use App\\Pilot\\{self.target};\nfinal class TinyBuilderPilotTest extends TestCase\n{{\n"
                f"    public function test_repair(): void {{ {self.repair_test} }}\n"
                f"    public function test_regression(): void {{ {self.regression_test} }}\n}}\n")


CASES = (
    Case(
        "email_validation", "EmailValidation", "Repair emailRules so the Laravel validator rejects malformed email addresses and still accepts a valid address.",
        "emailRules", "", "return ['required'];", "return ['required', 'email'];",
        r"""return\s+\[\s*['"](?:required|email|string|nullable)['"](?:\s*,\s*['"](?:required|email|string|nullable)['"]){0,3}\s*,?\s*\]\s*;""",
        r"$rules = ['address' => EmailValidation::emailRules()]; "
        r"$this->assertTrue(\Illuminate\Support\Facades\Validator::make(['address'=>'malformed'], $rules)->fails()); "
        r"$this->assertTrue(\Illuminate\Support\Facades\Validator::make([], $rules)->fails());",
        r"$this->assertFalse(\Illuminate\Support\Facades\Validator::make(['address'=>'person@example.org'], "
        r"['address'=>EmailValidation::emailRules()])->fails());",
    ),
    Case(
        "checkout_discount", "CheckoutDiscount", "Repair checkoutTotal so a discount reduces the subtotal. Preserve the original behavior for a zero discount.",
        "checkoutTotal", "int $subtotal, int $discount", "return $subtotal + $discount;", "return $subtotal - $discount;",
        r"return\s+\$(?:subtotal|discount)(?:\s*[+\-*/]\s*\$(?:subtotal|discount))?\s*;",
        "$this->assertSame(75, CheckoutDiscount::checkoutTotal(100, 25)); "
        "$this->assertSame(1, CheckoutDiscount::checkoutTotal(10, 9));",
        "$this->assertSame(10, CheckoutDiscount::checkoutTotal(10, 0));",
    ),
)


def digest(path):
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def patch_category(case, preview):
    before, after = case.source.splitlines(keepends=True), preview.splitlines(keepends=True)
    if len(before) != len(after) or before[:6] != after[:6] or before[7:] != after[7:]:
        return "out_of_scope"
    if not re.fullmatch(case.allowed, after[6].strip()):
        return "outside_safe_subset"
    return None


def test(php, project, suffix):
    # Run the exact evaluator file and method. Exit 1 alone does not prove an assertion failed.
    with TemporaryDirectory(prefix="tinybuilder-phpunit-") as tmp:
        junit = Path(tmp) / "result.xml"
        runner = project / "vendor/phpunit/phpunit/phpunit"
        result = command([php, str(runner), "--filter=" + suffix + "$",
                          "--log-junit", str(junit), TEST], project)
        try:
            cases = ElementTree.parse(junit).getroot().findall(".//testcase")
        except (OSError, ElementTree.ParseError):
            return 2
    if (len(cases) != 1 or cases[0].get("name") != suffix
            or cases[0].find("error") is not None or cases[0].find("skipped") is not None):
        return 2
    failed = cases[0].find("failure") is not None
    if failed and result.returncode == 1:
        return 1
    return 0 if not failed and result.returncode == 0 else 2


def prepare(case, base, root, revision, php):
    require(["git", "worktree", "add", "--detach", str(root), revision], base)
    shutil.copytree(base / "vendor", root / "vendor")
    shutil.copyfile(root / ".env.example", root / ".env")
    require([php, "artisan", "key:generate", "--no-interaction"], root)
    target = fresh_fixture_path(root, case.path)
    target.parent.mkdir()
    target.write_bytes(case.source.encode())
    (target.parent / "SampleUtility.php").write_text(
        "<?php\nnamespace App\\Pilot;\nfinal class SampleUtility { public function sample() { return 0; } }\n", encoding="utf-8")
    hidden = fresh_fixture_path(root, TEST)
    try:
        hidden.write_text(case.test, encoding="utf-8")
        broken = [test(php, root, "test_repair"), test(php, root, "test_regression")]
        target.write_bytes(case.source.replace(case.broken, case.reference).encode())
        reference = [test(php, root, "test_repair"), test(php, root, "test_regression")]
    finally:
        target.write_bytes(case.source.encode())
        hidden.unlink(missing_ok=True)
    return {"broken": broken, "reference": reference}


def evaluate_preview(row, case, root, php):
    preview = row.pop("preview", None)
    if preview is None:
        return
    # PHP lint checks syntax without executing the generated program.
    target = root / case.path
    original = case.source.encode()
    if target.is_symlink() or target.read_bytes() != original:
        row["category"] = "safety"
        return
    with TemporaryDirectory(prefix="lint-") as scratch:
        path = Path(scratch) / "candidate.php"
        path.write_bytes(preview.encode())
        row["lint_exit"] = command([php, "-l", str(path)], root).returncode
    if row["lint_exit"]:
        row["category"] = "syntax"
        return
    rejected = patch_category(case, preview)
    if rejected:
        row["category"] = rejected
        return
    hidden = fresh_fixture_path(root, TEST)
    env_hash = digest(root / ".env")
    status = ["git", "status", "--porcelain", "--untracked-files=all"]
    before = require(status, root)
    try:
        target.write_bytes(preview.encode())
        hidden.write_text(case.test, encoding="utf-8")
        row["behavior_exit"] = test(php, root, "test_repair")
        row["regression_exit"] = test(php, root, "test_regression")
    finally:
        target.write_bytes(original)
        hidden.unlink(missing_ok=True)
    if require(status, root) != before or digest(root / ".env") != env_hash:
        row["category"] = "safety"
    elif row["behavior_exit"] not in (0, 1) or row["regression_exit"] not in (0, 1):
        row["category"] = "evaluator"
    elif row["regression_exit"]:
        row["category"] = "regression"
    elif row["behavior_exit"]:
        row["category"] = "reasoning"
    else:
        row["category"] = "pass"


def monitor(process, stop, samples):
    if os.name != "nt":
        return
    system = Path(os.environ["SystemRoot"]) / "System32/WindowsPowerShell/v1.0/powershell.exe"
    script = (f"$child=Get-CimInstance Win32_Process -Filter \"ParentProcessId = {process.pid} "
              "AND Name = 'llama-server.exe'\"; if($child){(Get-Process -Id $child.ProcessId -ErrorAction SilentlyContinue).PeakWorkingSet64}")
    while not stop.is_set():
        try:
            result = subprocess.run([system, "-NoProfile", "-NonInteractive", "-Command", script],
                                    capture_output=True, text=True, timeout=10)
            if result.stdout.strip().isdigit():
                samples.append(int(result.stdout.strip()))
        except (OSError, subprocess.SubprocessError):
            return
        stop.wait(0.5)


def infer(lab, runtime, model, jobs):
    samples, stop = [], Event()
    start = monotonic()
    with subprocess.Popen([lab, "--runtime", runtime, "--model", model, "--jobs", jobs],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8") as process:
        thread = Thread(target=monitor, args=(process, stop, samples), daemon=True)
        thread.start()
        try:
            output, _ = process.communicate(timeout=1200)
            error = "runtime" if process.returncode else None
        except subprocess.TimeoutExpired:
            process.kill()
            output, _ = process.communicate()
            error = "timeout"
        finally:
            stop.set()
            thread.join(timeout=12)
    try:
        rows = [json.loads(line) for line in output.splitlines() if line.strip()]
    except ValueError:
        rows, error = [], "driver_protocol"
    return rows, {"wall_seconds": round(monotonic()-start, 2),
                  "runtime_peak_working_set_bytes": max(samples, default=None),
                  "driver_failure": error}


def main():
    cases, arms = CASES, ARMS
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("baseline", "lab", "runtime", "output"):
        parser.add_argument(f"--{key}", type=Path, required=True)
    parser.add_argument("--model", nargs=3, action="append", metavar=("LABEL", "GGUF", "SHA256"), required=True)
    parser.add_argument("--php", required=True)
    args = parser.parse_args()
    base, output = args.baseline.resolve(), args.output.resolve()
    revision = validate_laravel_baseline(base, output)
    args.runtime, args.lab = args.runtime.resolve(strict=True), args.lab.resolve(strict=True)
    output.mkdir()
    proof = output / "pilot.json"
    report = {"profile": "laravel-v1-pilot-20261127", "baseline": revision, "control_order": ["behavior", "regression"],
              "runtime_manifest_sha256": digest(args.runtime / "runtime-manifest.json"), "lab_sha256": digest(args.lab),
              "configuration": {"temperature": 0, "selection_max_tokens": 128, "replacement_max_tokens": 512,
                                "context": "one complete file with exact selected line; b12359 CPU runtime defaults"},
              "requested_per_model": len(CASES)*len(ARMS), "controls": {}, "models": []}
    def save():
        proof.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    projects = {case.name: output / case.name for case in CASES}
    try:
        for case in CASES:
            controls = prepare(case, base, projects[case.name], revision, args.php)
            report["controls"][case.name] = controls
            if controls != {"broken": [1, 0], "reference": [0, 0]}:
                raise ValueError(f"Oracle controls failed for {case.name}: {controls}")
        with TemporaryDirectory(prefix="laravel-pilot-plan-", dir=output) as scratch:
            jobs = Path(scratch) / "jobs.json"
            jobs.write_text(json.dumps([{"case": c.name, "project": str(projects[c.name]), "task": c.task,
                                         "target": c.path, "line": 7, "source": c.source} for c in CASES]), encoding="utf-8")
            for label, name, pin in args.model:
                model = Path(name).resolve(strict=True)
                if model.suffix.lower() != ".gguf" or digest(model) != pin:
                    raise ValueError("Model identity does not match preselected hash")
                responses, metrics = infer(args.lab, args.runtime, model, jobs)
                try:
                    indexed = index_rows(responses, {(case.name, arm) for case in cases for arm in arms})
                except (TypeError, ValueError):
                    indexed = {}
                    metrics["driver_failure"] = "driver_protocol"
                rows = []
                for case in CASES:
                    for arm in ARMS:
                        row = indexed.get((case.name, arm), {"case": case.name, "arm": arm,
                                                            "category": "not_run", "driver_failure": metrics["driver_failure"]})
                        evaluate_preview(row, case, projects[case.name], args.php)
                        rows.append(row)
                        print(label, case.name, arm, row["category"], flush=True)
                report["models"].append({"model": label, "sha256": pin, "bytes": model.stat().st_size,
                                         "unchanged": digest(model) == pin,
                                         "ready_ms": next((r["ready_ms"] for r in responses if "ready_ms" in r), None),
                                         "counts": dict(Counter(row["category"] for row in rows)), "trials": rows, **metrics})
                save()
    finally:
        save()
    return int(any(not model["unchanged"] or model["driver_failure"] or
                   model["counts"].get("not_run") or model["counts"].get("evaluator") or
                   model["counts"].get("safety") for model in report["models"]))


if __name__ == "__main__":
    raise SystemExit(main())
