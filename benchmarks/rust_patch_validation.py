"""Run an independently scored Laravel validation repair with the Rust patch lab."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess

from .evaluate import command, prepare_route_variant, require, route_registered, validate_laravel_baseline
from .identity import sha256_file
from .validation_case import (
    VALIDATION_PATH, VALIDATION_HIDDEN_PATH, fresh_fixture_path,
    hidden_validation_test, reference_fixed_route,
)

TASK = (
    "Fix only routes/web.php. The POST /tinybuilder/contact endpoint must require "
    "a valid email and a string message of at least 3 characters. Invalid JSON "
    "requests must return Laravel's HTTP 422 with the relevant field errors. "
    "Valid requests must still return the exact JSON {\"accepted\":true}. "
    "Preserve the existing routes and response for valid input."
)
HIDDEN_FILTER = "--filter=TinyBuilderValidationHiddenTest"


def verify_model(model, expected):
    if not model.is_file() or model.is_symlink() or model.suffix.lower() != ".gguf":
        raise ValueError("Select an existing regular GGUF")
    if sha256_file(model) != expected:
        raise ValueError("Model SHA-256 mismatch")


def test_exit(php, root, *args):
    return command([php, "artisan", "test", *args], root).returncode


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("baseline", "lab", "runtime", "model", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--php", required=True)
    parser.add_argument("--select-line", action="store_true", help="Use the fixture return line as the exact lab anchor")
    parser.add_argument("--expected-model-sha256", required=True)
    args = parser.parse_args()
    base, output = args.baseline.resolve(), args.output.resolve()
    model, lab, runtime = (p.resolve(strict=True) for p in (args.model, args.lab, args.runtime))
    model_hash = args.expected_model_sha256.lower()
    verify_model(model, model_hash)
    revision = validate_laravel_baseline(base, output)
    output.mkdir()
    project = output / "laravel"
    report = {"status": "failed", "baseline_commit": revision, "model_sha256": model_hash,
              "runtime_manifest_sha256": sha256_file(runtime / "runtime-manifest.json"),
              "lab_sha256": sha256_file(lab)}
    try:
        require(["git", "worktree", "add", "--detach", str(project), revision], base)
        shutil.copytree(base / "vendor", project / "vendor")
        env_file = project / ".env"
        shutil.copyfile(project / ".env.example", env_file)
        require([args.php, "artisan", "key:generate", "--no-interaction"], project)
        protected_env = env_file.read_bytes()
        baseline = test_exit(args.php, project)
        variant = prepare_route_variant(project, "validation", preserve_sibling_route=True)
        route = project / "routes/web.php"
        seed = route.read_bytes()
        visible = project / VALIDATION_PATH
        original_test = visible.read_bytes()
        hidden = fresh_fixture_path(project, VALIDATION_HIDDEN_PATH)
        hidden_source = hidden_validation_test(variant["slug"], variant["marker"])
        git_status = ["git", "status", "--porcelain", "--untracked-files=all"]
        scoped_status = require(git_status, project)
        reference = reference_fixed_route(seed.decode("utf-8"))
        # A repair that checks presence but accepts a malformed email is insufficient.
        wrong = reference.replace("'email' => ['required', 'email']", "'email' => ['required']")
        if wrong == reference:
            raise ValueError("Incorrect-repair control was not seeded")
        try:
            hidden.write_text(hidden_source, encoding="utf-8")
            negative = test_exit(args.php, project, HIDDEN_FILTER)
            route.write_bytes(reference.encode("utf-8"))
            positive = test_exit(args.php, project)
            route.write_bytes(wrong.encode("utf-8"))
            incorrect = test_exit(args.php, project, HIDDEN_FILTER)
        finally:
            route.write_bytes(seed)
            hidden.unlink(missing_ok=True)
        report["controls"] = {"untouched_suite": baseline, "broken_route": negative,
                              "reference_repair": positive, "incorrect_repair": incorrect}
        if (baseline, negative, positive, incorrect) != (0, 1, 0, 1):
            raise ValueError("Laravel semantic controls did not produce the expected outcomes")
        print("Controls passed. Review the proposed diff. Approve only a safe edit to routes/web.php.", flush=True)
        anchor_args = []
        if args.select_line:
            anchor = "    return response()->json(['accepted' => true]);"
            lines = [index for index, line in enumerate(seed.decode("utf-8").splitlines(), 1) if line == anchor]
            if len(lines) != 1:
                raise ValueError("The evaluator expected one route return line")
            anchor_args = ["--line", str(lines[0])]
        report["proposal_mode"] = "selected_line" if args.select_line else "model_selected_replacement"
        result = subprocess.run([
            lab, "--project", project, "--runtime", runtime, "--model", model,
            "edit", TASK, "--allow-write", "--target", "routes/web.php", *anchor_args,
        ], cwd=project, timeout=240)
        report["lab_exit"] = result.returncode
        report["route_changed"] = route.read_bytes() != seed
        report["scope_preserved"] = (
            require(git_status, project) == scoped_status
            and visible.read_bytes() == original_test and env_file.read_bytes() == protected_env
            and not hidden.exists()
        )
        if result.returncode or not report["route_changed"] or not report["scope_preserved"]:
            return 1
        hidden.write_text(hidden_source, encoding="utf-8")
        try:
            report["php_lint_exit"] = command([args.php, "-l", str(route)], project).returncode
            report["phpunit_exit"] = test_exit(args.php, project)
            routes = command([args.php, "artisan", "route:list", "--path=tinybuilder/contact", "--json"], project)
            report["route_registered"] = route_registered(routes, "tinybuilder/contact", "POST")
        finally:
            hidden.unlink(missing_ok=True)
        if (report["php_lint_exit"] == 0 and report["phpunit_exit"] == 0 and report["route_registered"]
                and require(git_status, project) == scoped_status
                and visible.read_bytes() == original_test and env_file.read_bytes() == protected_env):
            report["status"] = "passed"
    finally:
        try:
            verify_model(model, model_hash)
        except (OSError, ValueError):
            report["status"] = "failed"
            report["model_unchanged"] = False
            raise
        finally:
            report.setdefault("model_unchanged", True)
            (output / "laravel-patch.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"Laravel semantic repair {report['status']}. See {output / 'laravel-patch.json'}")
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
