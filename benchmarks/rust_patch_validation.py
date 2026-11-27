"""Run an independently scored Laravel validation repair with the Rust patch lab."""
import argparse
import json
from pathlib import Path
import shutil

from .evaluate import command, prepare_route_variant, require, validate_laravel_baseline
from .identity import sha256_file
from .validation_case import (
    VALIDATION_HIDDEN_PATH, fresh_fixture_path,
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
    for name in ("baseline", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--php", required=True)
    parser.add_argument("--trusted-controls-only", action="store_true",
                        help="Run reviewed reference controls without model inference or candidate execution")
    args = parser.parse_args()
    if not args.trusted_controls_only:
        parser.error("Legacy generated-code execution is disabled; use a separately qualified contained evaluator")
    base, output = args.baseline.resolve(), args.output.resolve()
    revision = validate_laravel_baseline(base, output)
    output.mkdir()
    project = output / "laravel"
    report = {"status": "failed", "baseline_commit": revision, "mode": "trusted_controls_only"}
    try:
        require(["git", "worktree", "add", "--detach", str(project), revision], base)
        shutil.copytree(base / "vendor", project / "vendor")
        env_file = project / ".env"
        shutil.copyfile(project / ".env.example", env_file)
        require([args.php, "artisan", "key:generate", "--no-interaction"], project)
        baseline = test_exit(args.php, project)
        variant = prepare_route_variant(project, "validation", preserve_sibling_route=True)
        route = project / "routes/web.php"
        seed = route.read_bytes()
        hidden = fresh_fixture_path(project, VALIDATION_HIDDEN_PATH)
        hidden_source = hidden_validation_test(variant["slug"], variant["marker"])
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
        report["status"] = "trusted_controls_passed"
        print("Trusted controls passed; model inference and candidate execution disabled.", flush=True)
        return 0
    finally:
        (output / "laravel-patch.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"Laravel control status: {report['status']}. See {output / 'laravel-patch.json'}")


if __name__ == "__main__":
    raise SystemExit(main())
