"""Opt-in local-model evaluation. Never downloads weights or saves model/MCP content.

Run with the installed TinyBuilder Python: python benchmarks/evaluate.py --help.
"""

import argparse
import difflib
import hashlib
import hmac
import json
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

from tinybuilder.agent import Agent
from tinybuilder.model import ChatModel, ModelError
from tinybuilder.protocol import ProtocolError
from tinybuilder.tools import LocalTools

# Keep direct "python benchmarks/evaluate.py" and package imports both working.
if __package__:
    from .validation_case import (
        VALIDATION_HIDDEN_PATH, VALIDATION_PATH, VALIDATION_READ_TASK,
        VALIDATION_ROUTE_URI, VALIDATION_WRITE_TASK, hidden_validation_test,
        reference_fixed_route, seed_validation,
    )
else:
    from validation_case import (
        VALIDATION_HIDDEN_PATH, VALIDATION_PATH, VALIDATION_READ_TASK,
        VALIDATION_ROUTE_URI, VALIDATION_WRITE_TASK, hidden_validation_test,
        reference_fixed_route, seed_validation,
    )


READ_TASK = ("Use read_file to inspect composer.json. Report its exact package name and "
             "laravel/framework version constraint. Do not guess or change any files.")
ROUTE_TASK = ("Read routes/web.php and bootstrap/app.php using tools. Explain the existing routes "
              "and how to add GET /health returning JSON {\"status\":\"ok\"}. Do not change files.")
WRITE_TASK = ("Read routes/web.php first. Add GET /health returning JSON {\"status\":\"ok\"} in "
              "routes/web.php, preserving all existing routes. Use write_file to make the change. "
              "Then run [\"php\",\"artisan\",\"test\"] using run_command. Do not modify tests or other files.")
REPAIR_TASK = ("Read routes/web.php and tests/Feature/TinyBuilderRepairRegressionTest.php using "
               "read_file. A test for GET /health is failing. Fix the Laravel route in routes/web.php "
               "without changing tests or other routes. Use write_file, then run "
               '["php","artisan","test"] via run_command. If tests fail, inspect and fix the failure.')
REPAIR_VISIBLE_TEST = '''<?php
namespace Tests\\Feature;
use Tests\\TestCase;
class TinyBuilderRepairRegressionTest extends TestCase
{
    public function test_health_regression(): void
    {
        $this->getJson('/health')->assertOk()->assertExactJson(['status' => 'ok']);
    }
}
'''
REPAIR_TEST_PATH = "tests/Feature/TinyBuilderRepairRegressionTest.php"
HEALTH_TEST = '''<?php
namespace Tests\\Feature;
use Tests\\TestCase;
class TinyBuilderHealthTest extends TestCase
{
    public function test_health_endpoint(): void
    {
        $this->getJson('/health')->assertOk()->assertExactJson(['status' => 'ok']);
    }
    public function test_original_home_survives(): void
    {
        $this->get('/')->assertOk();
    }
}
'''


def hidden_health_test(preserved_slug: str | None = None, marker: str | None = None) -> str:
    """Hidden assertions remain absent from the model's inference worktree."""
    if preserved_slug is None:
        return HEALTH_TEST
    if marker is None:
        raise ValueError("Preservation marker required")
    extra = ("    public function test_sibling_route_is_preserved(): void\n"
             "    {\n"
             f"        $this->getJson('/{preserved_slug}')->assertOk()"
             f"->assertExactJson(['marker' => '{marker}']);\n"
             "    }\n")
    return HEALTH_TEST[:-2] + extra + "}\n"


def prepare_route_variant(root: Path, scenario: str = "health", preserve_sibling_route: bool = False,
                          paired_marker: str | None = None):
    """Seed only disposable worktrees, never the original Laravel baseline."""
    if scenario not in ("health", "repair", "validation"):
        raise ValueError("Unknown evaluation scenario")
    route_path = root / "routes/web.php"
    previous = route_path.read_text(encoding="utf-8")
    if "'/health'" in previous or '"/health"' in previous:
        raise ValueError("Disposable baseline already has /health; use a fresh baseline")
    if scenario == "validation":
        previous = seed_validation(root, previous)
    if scenario == "repair":
        previous += "\nRoute::get('/health', fn () => response()->json(['status' => 'broken']));\n"
        visible_path = root / REPAIR_TEST_PATH
        if visible_path.exists():
            raise ValueError("Repair regression fixture already exists")
        visible_path.parent.mkdir(parents=True, exist_ok=True)
        visible_path.write_text(REPAIR_VISIBLE_TEST, encoding="utf-8")
    marker = None
    slug = None
    if preserve_sibling_route:
        marker = paired_marker if paired_marker is not None else uuid.uuid4().hex
        slug = "tinybuilder-preserve-" + marker[:12]
        previous += (f"\nRoute::get('/{slug}', fn () => response()->json("
                     f"['marker' => '{marker}']));\n")
    # No rewrite in the measured default scenario (preserves Windows line endings).
    if scenario in ("repair", "validation") or preserve_sibling_route:
        route_path.write_text(previous, encoding="utf-8")
    return {"initial_route": previous, "slug": slug, "marker": marker}


def command(argv, root, timeout=180):
    # Resolve Windows PHP/Composer launchers without enabling a shell ourselves.
    resolved = [shutil.which(argv[0]) or argv[0], *argv[1:]]
    return subprocess.run(resolved, cwd=root, capture_output=True, text=True,
                          errors="replace", timeout=timeout, stdin=subprocess.DEVNULL)


def require(argv, root):
    result = command(argv, root)
    if result.returncode:
        raise RuntimeError(f"Setup failed: {argv[0]} {argv[1]} (exit {result.returncode})")
    return result.stdout.strip()


def _failure_kind(result: dict, expected: bool = False) -> str | None:
    """Separate protocol, permissions and execution from factual benchmark failures."""
    events = result["events"]
    if result.get("passed") is True:
        return None
    if result["error"]:
        if result["error_kind"]:
            return result["error_kind"]
        return "execution"
    if any(e.get("event") == "protocol_error" for e in events):
        errors = [e for e in events if e.get("event") == "protocol_error"]
        return "argument" if errors[-1].get("reason", "").startswith("argument_") else "protocol"
    failures = [e.get("reason") for e in events if e.get("event") == "tool_end" and e.get("status") != "ok"]
    if "permission" in failures:
        return "permission"
    if "unknown_tool" in failures:
        return "protocol"
    if failures:
        return "execution"
    if result["tool_calls"] == 0:
        return "no_tool_call"
    if result.get("missing_required_tools"):
        return "missing_required_tool"
    if result.get("missing_required_files"):
        return "missing_required_file"
    if result.get("model_write_scope_ok") is False:
        return "scope"
    if (result.get("required_sequence_ok") is False or
            result.get("tests_after_last_edit") is False or
            result.get("required_reads_before_edit") is False):
        return "tool_order"
    if not result["final_answer"]:
        return "incomplete"
    if expected and not result.get("facts_correct", False):
        return "factual"
    return None


class EvaluationTools(LocalTools):
    """Remember read targets in RAM without persisting arguments or observations."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.files_read = set()
        self.operations = []  # Transient local-only sequence; not included in results.json.

    def call(self, name, args):
        output = super().call(name, args)
        if name == "read_file" and not output.startswith(("Tool error:", "File not found")):
            path = self._path(args["path"])
            self.files_read.add(path)
            self.operations.append(("read_file", path))
        elif name == "write_file" and output.startswith("Wrote "):
            self.operations.append(("write_file", self._path(args["path"])))
        elif name == "run_command" and output.startswith("Exit code: 0\n"):
            self.operations.append(("run_command", tuple(args["argv"])))
        return output


def sequence_verified(operations, sequence):
    """Check ordered, successful local events, not model assertions or printed JSON."""
    cursor = iter(operations)
    return all(any(item == wanted for item in cursor) for wanted in sequence)


def tests_after_last_edit_verified(operations, target, command_argv):
    """The last edit to the target must precede a successful allowed test run.

    A test run before a later edit does not demonstrate validation of the final
    model-authored contents. Operations are transient and contain no model prose.
    """
    writes = [idx for idx, item in enumerate(operations)
              if item == ("write_file", target)]
    tests = [idx for idx, item in enumerate(operations)
             if item == ("run_command", tuple(command_argv))]
    return bool(writes and tests and tests[-1] > writes[-1])


def reads_before_first_edit_verified(operations, files, target):
    """Required source reads must precede the FIRST model edit, not merely a later edit.

    This is a benchmark evidence check, not an automatic action or permission.
    """
    first_write = next((idx for idx, event in enumerate(operations)
                        if event == ("write_file", target)), None)
    if first_write is None:
        return False
    prior_reads = {path for operation, path in operations[:first_write]
                   if operation == "read_file"}
    return set(files).issubset(prior_reads)


def writes_only_target_verified(operations, target):
    """Git status misses ignored paths (.env, vendor); check successful tool writes too."""
    writes = [path for operation, path in operations if operation == "write_file"]
    return bool(writes) and all(path == target for path in writes)


def validate_laravel_baseline(base: Path, output: Path):
    """Refuse unsafe benchmark locations before any model request or fixture write."""
    base, output = base.resolve(), output.resolve()
    if not (base / ".tinybuilder-disposable").is_file():
        raise ValueError("--laravel requires a NEW disposable Git project with .tinybuilder-disposable marker")
    if output.is_relative_to(base) or base.is_relative_to(output):
        raise ValueError("Benchmark output must be separate from the disposable Laravel baseline")
    if not (base / "composer.lock").is_file():
        raise ValueError("Disposable baseline requires composer.lock")
    if not (base / "vendor").is_dir():
        raise ValueError("Disposable baseline requires installed vendor dependencies")
    for path in ("routes/web.php", "bootstrap/app.php", ".env.example"):
        if not (base / path).is_file():
            raise ValueError("Disposable baseline is missing required Laravel project files")
    revision = require(["git", "rev-parse", "HEAD"], base)
    repo_root = Path(require(["git", "rev-parse", "--show-toplevel"], base)).resolve()
    if repo_root != base:
        raise ValueError("Disposable Laravel baseline must be the Git repository root")
    # Respect normal .gitignore rules for vendor/.env, but refuse untracked
    # source files that would not be present in the detached worktrees.
    if require(["git", "status", "--porcelain"], base):
        raise ValueError("Disposable baseline must have no tracked or untracked changes")
    return revision


def change_scope_verified(paths, model_changed_route, scenario, visible_intact):
    """Exclude an evaluator-owned visible test only if the model left it byte-identical."""
    visible_path = (REPAIR_TEST_PATH if scenario == "repair" else
                    VALIDATION_PATH if scenario == "validation" else None)
    ignored = {visible_path} if visible_path and visible_intact else set()
    return (set(paths) - ignored == {"routes/web.php"} and visible_intact and model_changed_route)


def route_registered(result, uri, verb):
    """Validate a real artisan route:list JSON result, including successful exit."""
    if result.returncode != 0:
        return False
    try:
        items = json.loads(result.stdout)
        return isinstance(items, list) and any(
            isinstance(route, dict) and route.get("uri") == uri and
            verb in route.get("method", "").split("|") for route in items
        )
    except (ValueError, TypeError):
        return False


def task(model_name, root, prompt, write=False, expected=None, php="php", tool_protocol="native",
         required_tools=(), strict_json_profile="prompt", required_files=(),
         progress_guidance="off", required_sequence=()):
    if expected:
        required_tools = (*required_tools, "read_file")
        required_files = (*required_files, "composer.json")
    required_tools = tuple(dict.fromkeys(required_tools))
    required_files = tuple(dict.fromkeys(required_files))
    events = []
    local = EvaluationTools(root, allow_write=write, allow_exec=write,
                       exec_commands=[[php, "artisan", "test"]])
    started = time.monotonic()
    answer, error, error_kind = "", None, None
    try:
        answer = Agent(ChatModel("http://127.0.0.1:11434/v1", model_name), local,
                       max_steps=8, on_event=events.append, tool_protocol=tool_protocol,
                       strict_json_profile=strict_json_profile,
                       progress_guidance=progress_guidance,
                       required_reads=required_files if progress_guidance == "checklist" else (),
                       required_tools=required_tools if progress_guidance == "checklist" else ()).run(prompt)
    except (ModelError, ProtocolError, OSError, ValueError) as exc:
        # Do not persist HTTP error bodies, which may contain remote or model content.
        error = type(exc).__name__
        error_kind = (exc.kind if isinstance(exc, ModelError) else
                      "incomplete" if isinstance(exc, ProtocolError) and exc.code == "task_requirements_missing" else
                      "protocol" if isinstance(exc, ProtocolError) else "execution")
        if isinstance(exc, ProtocolError) and any(
                event.get("reason", "").startswith("argument_")
                for event in events if event["event"] == "protocol_error"):
            error_kind = "argument"
        print(f"{model_name}: {exc}", file=sys.stderr, flush=True)
    calls = [event for event in events if event["event"] == "tool_end"]
    result = {"model": model_name, "tool_protocol": tool_protocol,
              "strict_json_profile": strict_json_profile, "progress_guidance": progress_guidance,
              "duration_seconds": round(time.monotonic() - started, 3),
              "error": error, "error_kind": error_kind, "events": events, "tool_calls": len(calls),
              "valid_tool_calls": sum(event["status"] == "ok" for event in calls),
              "read_file_called": any(event["tool"] == "read_file" and event["status"] == "ok" for event in calls),
              "write_file_called": any(event["tool"] == "write_file" and event["status"] == "ok" for event in calls),
              "run_command_called": any(event["tool"] == "run_command" and event["status"] == "ok" for event in calls),
              "final_answer": bool(answer) and not answer.startswith("Stopped after")}
    result["missing_required_tools"] = [name for name in required_tools if not any(
        event["tool"] == name and event["status"] == "ok" for event in calls)]
    # Only evaluator-supplied public fixture names appear in metadata, never arbitrary paths.
    result["missing_required_files"] = [name for name in dict.fromkeys(required_files)
                                        if (local.root / name).resolve() not in local.files_read]
    if required_sequence:
        # Only booleans are persisted. Actual paths and argv remain in process RAM.
        result["required_sequence_ok"] = sequence_verified(local.operations, required_sequence)
        # Distinct from finding any read->write->test subsequence: no later
        # edit may invalidate the proof that the model tested its final edit.
        result["tests_after_last_edit"] = tests_after_last_edit_verified(
            local.operations, required_sequence[1][1], required_sequence[-1][1])
        result["required_reads_before_edit"] = reads_before_first_edit_verified(
            local.operations, [local.root / name for name in required_files],
            required_sequence[1][1])
        result["model_write_scope_ok"] = writes_only_target_verified(
            local.operations, required_sequence[1][1])
    if expected:
        result["facts_correct"] = all(value in answer for value in expected)
        result["passed"] = (result["facts_correct"] and result["read_file_called"] and
                            result["final_answer"] and not result["missing_required_files"])
    result["failure_kind"] = _failure_kind(result, expected=bool(expected))
    # Answers and observations stay in RAM. Metadata alone goes to the report.
    print(json.dumps(result), flush=True)
    return result


def smoke(root, models, tool_protocol="native", strict_json_profile="prompt", progress_guidance="off",
          fixture_seed=None, trial_number=1):
    root.mkdir()
    # A shared, operator-owned seed permits matched inputs across separate
    # baseline/guided runs. This value and the generated identity are never
    # sent to the model, included in the task prompt, or saved in results.json.
    suffix = (hmac.new(bytes.fromhex(fixture_seed), f"smoke:{trial_number}".encode(),
                       hashlib.sha256).hexdigest()[:32] if fixture_seed is not None
              else uuid.uuid4().hex)
    package = "tinybuilder/" + suffix
    (root / "composer.json").write_text(json.dumps({"name": package, "type": "project", "require": {
        "php": "^8.2", "laravel/framework": "^12.0"}, "autoload": {"psr-4": {"App\\": "app/"}}}), encoding="utf-8")
    (root / "routes").mkdir()
    (root / "routes/web.php").write_text("<?php\nuse Illuminate\\Support\\Facades\\Route;\nRoute::get('/', fn () => view('welcome'));\n", encoding="utf-8")
    (root / "app").mkdir()
    (root / "app/Example.php").write_text("<?php\nnamespace App;\nclass Example {}\n", encoding="utf-8")
    return [task(model, root, READ_TASK, expected=[package, "^12.0"], tool_protocol=tool_protocol,
                 strict_json_profile=strict_json_profile, progress_guidance=progress_guidance) for model in models]


def laravel(base, output, models, php, tool_protocol="native", strict_json_profile="prompt",
            progress_guidance="off", scenario="health", preserve_sibling_route=False,
            fixture_seed=None, trial_number=1, controls_only=False):
    # Never execute tests or install dependencies inside an arbitrary user's project.
    revision = validate_laravel_baseline(base, output)
    results = []
    for index, model in enumerate(models):
        root = output / f"laravel-{index}"
        require(["git", "worktree", "add", "--detach", str(root), revision], base)
        # Copy dependencies from the explicitly disposable baseline, without network requests.
        shutil.copytree(base / "vendor", root / "vendor")
        shutil.copyfile(root / ".env.example", root / ".env")
        require([php, "artisan", "key:generate", "--no-interaction"], root)
        baseline = command([php, "artisan", "test"], root)
        # Optional route variations belong only to each detached worktree, never to baseline.
        paired_marker = (hmac.new(bytes.fromhex(fixture_seed),
                                  f"sibling:{trial_number}:{index}".encode(), hashlib.sha256).hexdigest()[:32]
                         if fixture_seed is not None else None)
        fixture = prepare_route_variant(root, scenario=scenario,
                                        preserve_sibling_route=preserve_sibling_route,
                                        paired_marker=paired_marker)
        validation_case = scenario == "validation"
        hidden_test = (hidden_validation_test(fixture["slug"], fixture["marker"]) if validation_case
                       else hidden_health_test(fixture["slug"], fixture["marker"]))
        hidden_path = VALIDATION_HIDDEN_PATH if validation_case else "tests/Feature/TinyBuilderHealthTest.php"
        hidden_filter = "TinyBuilderValidationHiddenTest" if validation_case else "TinyBuilderHealthTest"
        test = root / hidden_path
        if test.exists():
            raise ValueError("Disposable baseline already contains the evaluator's hidden test")
        test.write_text(hidden_test, encoding="utf-8")
        negative = command([php, "artisan", "test", f"--filter={hidden_filter}"], root)
        negative_label = "baseline-validation-hidden" if validation_case else "baseline-health"
        (output / f"{negative_label}-{index}.txt").write_text(
            negative.stdout + negative.stderr, encoding="utf-8")
        test.unlink()  # Never let model read the hidden assertions.
        visible_path = (VALIDATION_PATH if validation_case else
                        REPAIR_TEST_PATH if scenario == "repair" else None)
        visible_test = root / visible_path if visible_path else None
        visible_before = visible_test.read_bytes() if visible_test else None
        visible_filter = ("TinyBuilderValidationRegressionTest" if validation_case else
                          "TinyBuilderRepairRegressionTest")
        visible_negative = (command([php, "artisan", "test", f"--filter={visible_filter}"], root)
                            if visible_test else None)

        # Only the new scenario runs a reference implementation before inference.
        # The reference patch exists in RAM/on disk solely while evaluator tests
        # run; it is reverted and the hidden test is removed BEFORE model access.
        reference_passed = None
        if validation_case:
            if (baseline.returncode != 0 or negative.returncode != 1 or
                    visible_negative.returncode != 1):
                raise RuntimeError("Validation seed controls failed; refusing model evaluation")
            seed_bytes = (root / "routes/web.php").read_bytes()
            try:
                (root / "routes/web.php").write_text(
                    reference_fixed_route(seed_bytes.decode("utf-8")), encoding="utf-8")
                test.write_text(hidden_test, encoding="utf-8")
                reference = command([php, "artisan", "test"], root)
                reference_routes = command(
                    [php, "artisan", "route:list", f"--path={VALIDATION_ROUTE_URI}", "--json"], root)
                reference_passed = (reference.returncode == 0 and
                                    route_registered(reference_routes, VALIDATION_ROUTE_URI, "POST"))
            finally:
                (root / "routes/web.php").write_bytes(seed_bytes)
                if test.exists():
                    test.unlink()
            if not reference_passed or (root / "routes/web.php").read_bytes() != seed_bytes:
                raise RuntimeError("Validation reference controls failed; refusing model evaluation")
            # A passing reference must not leave the broken seed accidentally fixed.
            if command([php, "artisan", "test", f"--filter={visible_filter}"], root).returncode != 1:
                raise RuntimeError("Validation seed was not restored after reference control")

        if controls_only:
            control = {"model": "reference-control", "scenario": scenario,
                       "worktree": root.name, "baseline_commit": revision,
                       "baseline_test_exit": baseline.returncode,
                       "negative_hidden_exit": negative.returncode,
                       "negative_visible_exit": visible_negative.returncode,
                       "reference_passed": reference_passed,
                       "passed": baseline.returncode == 0 and negative.returncode == 1 and
                       visible_negative.returncode == 1 and reference_passed is True}
            results.append(control)
            continue

        # No hidden tests and no answer content are persisted by the agent.
        read_prompt = VALIDATION_READ_TASK if validation_case else ROUTE_TASK
        read = task(model, root, read_prompt, tool_protocol=tool_protocol, required_tools=("read_file",),
                    strict_json_profile=strict_json_profile, progress_guidance=progress_guidance,
                    required_files=("routes/web.php", "bootstrap/app.php"))
        write_prompt = (VALIDATION_WRITE_TASK if validation_case else
                        REPAIR_TASK if scenario == "repair" else WRITE_TASK)
        write_prompt = write_prompt.replace('["php","artisan","test"]', json.dumps([php, "artisan", "test"]))
        required = (("routes/web.php", visible_path) if visible_path else ("routes/web.php",))
        write = task(model, root, write_prompt, write=True, php=php, tool_protocol=tool_protocol,
                     required_tools=("read_file", "write_file", "run_command"),
                     strict_json_profile=strict_json_profile, progress_guidance=progress_guidance,
                     required_files=required,
                     required_sequence=(("read_file", root / "routes/web.php"),
                                        ("write_file", root / "routes/web.php"),
                                        ("run_command", (php, "artisan", "test"))))
        # This model delta excludes any evaluator-seeded route (including intentionally broken one).
        current_route = (root / "routes/web.php").read_text(encoding="utf-8")
        model_changed_route = current_route != fixture["initial_route"]
        model_diff = "".join(difflib.unified_diff(fixture["initial_route"].splitlines(keepends=True),
                                                  current_route.splitlines(keepends=True),
                                                  fromfile="seeded/routes/web.php", tofile="model/routes/web.php"))
        (output / f"model-diff-{index}.patch").write_text(model_diff, encoding="utf-8")
        diff = require(["git", "diff", "--", "routes/web.php"], root)
        (output / f"diff-{index}.patch").write_text(diff + "\n", encoding="utf-8")
        changed = require(["git", "status", "--porcelain"], root)
        paths = require(["git", "diff", "--name-only", "HEAD"], root).splitlines()
        paths += require(["git", "ls-files", "--others", "--exclude-standard"], root).splitlines()
        # The evaluator-created visible repair test must remain byte-identical; exclude it only if intact.
        visible_intact = visible_before is None or (
            visible_test.is_file() and visible_test.read_bytes() == visible_before)
        scope_ok = change_scope_verified(paths, model_changed_route, scenario, visible_intact)
        test.write_text(hidden_test, encoding="utf-8")
        validation = command([php, "artisan", "test"], root)
        route_uri = VALIDATION_ROUTE_URI if validation_case else "health"
        route_verb = "POST" if validation_case else "GET"
        routes = command([php, "artisan", "route:list", f"--path={route_uri}", "--json"], root)
        health_registered = route_registered(routes, route_uri, route_verb)
        (output / f"phpunit-{index}.txt").write_text(validation.stdout + validation.stderr, encoding="utf-8")
        result = {"model": model, "scenario": scenario, "preserve_sibling_route": preserve_sibling_route,
                  "baseline_commit": revision, "worktree": root.name,
                  "composer_lock_sha256": hashlib.sha256((base / "composer.lock").read_bytes()).hexdigest(),
                  "baseline_test_exit": baseline.returncode,
                  "baseline_health_exit": negative.returncode if not validation_case else None,
                  "baseline_repair_exit": (visible_negative.returncode if scenario == "repair" else None),
                  "baseline_validation_exit": (visible_negative.returncode if validation_case else None),
                  "validation_reference_passed": reference_passed,
                  "read": read, "write": write, "changed_path_count": len(paths),
                  "route_registered": health_registered, "model_changed_route": model_changed_route,
                  "change_scope_ok": scope_ok, "validation_test_exit": validation.returncode,
                  "model_write_scope_ok": write.get("model_write_scope_ok"),
                  "passed": baseline.returncode == 0 and negative.returncode == 1 and
                  (visible_negative is None or visible_negative.returncode == 1) and
                  reference_passed is not False and validation.returncode == 0 and health_registered and bool(diff) and model_changed_route and
                  scope_ok and read["final_answer"] and not read["missing_required_files"] and
                  write["write_file_called"] and write["run_command_called"] and
                  write["final_answer"] and not write["missing_required_tools"] and
                  not write["missing_required_files"] and write.get("required_sequence_ok") is True and
                  write.get("tests_after_last_edit") is True and
                  write.get("required_reads_before_edit") is True and
                  write.get("model_write_scope_ok") is True}
        result["failure_kind"] = (None if result["passed"] else
                                  read["failure_kind"] or write["failure_kind"] or "validation")
        results.append(result)
        print(json.dumps({"laravel_result": result}), flush=True)
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", nargs="+", default=["qwen2.5-coder:0.5b", "qwen2.5-coder:1.5b"])
    parser.add_argument("--tool-protocol", choices=("native", "strict-json"), default="native",
                        help="Native OpenAI tool calls or experimental opt-in strict JSON actions")
    parser.add_argument("--strict-json-profile", choices=("prompt", "constrained"), default="prompt",
                        help="constrained: compact prompt plus server JSON schema; requires strict-json")
    parser.add_argument("--progress-guidance", choices=("off", "checklist"), default="off",
                        help="opt-in bounded checklist; requires constrained strict-json")
    parser.add_argument("--trials", type=int, default=1, help="1–10 independent random-name trials")
    parser.add_argument("--fixture-seed", default=None,
                        help="optional 32-character hex seed for matched hidden-name trials; never logged")
    parser.add_argument("--scenario", choices=("health", "repair", "validation"), default="health",
                        help="health is the measured baseline; repair and validation are opt-in")
    parser.add_argument("--controls-only", action="store_true",
                        help="Check validation negative/reference PHP controls in a disposable worktree, without Ollama")
    parser.add_argument("--preserve-sibling-route", action="store_true",
                        help="seed a random unrelated route and assert it survives (opt-in)")
    parser.add_argument("--output", type=Path, required=True, help="New directory for disposable fixtures and metadata")
    parser.add_argument("--laravel", type=Path, help="Explicitly marked disposable Laravel baseline Git repository")
    parser.add_argument("--php", default="php", help="PHP binary for evaluator checks")
    args = parser.parse_args()
    if args.strict_json_profile != "prompt" and args.tool_protocol != "strict-json":
        parser.error("--strict-json-profile constrained requires --tool-protocol strict-json")
    if args.progress_guidance != "off" and (args.tool_protocol != "strict-json" or args.strict_json_profile != "constrained"):
        parser.error("--progress-guidance checklist requires constrained strict-json")
    if not 1 <= args.trials <= 10:
        parser.error("--trials must be between 1 and 10")
    if args.fixture_seed is not None and (len(args.fixture_seed) != 32 or
                                         any(c not in "0123456789abcdefABCDEF" for c in args.fixture_seed)):
        parser.error("--fixture-seed must be exactly 32 hexadecimal characters")
    if (args.scenario != "health" or args.preserve_sibling_route) and not args.laravel:
        parser.error("Non-default scenarios and sibling preservation require --laravel")
    if args.controls_only and (args.scenario != "validation" or not args.laravel or args.trials != 1):
        parser.error("--controls-only requires --scenario validation --laravel and --trials 1")
    args.output = args.output.resolve()
    if args.laravel:
        try:
            validate_laravel_baseline(args.laravel.resolve(), args.output)
        except ValueError as exc:
            parser.error(str(exc))
    args.output.mkdir(parents=True, exist_ok=False)
    if args.controls_only:
        controls = laravel(args.laravel.resolve(), args.output, ["reference-control"],
                          args.php, scenario="validation",
                          preserve_sibling_route=args.preserve_sibling_route,
                          fixture_seed=args.fixture_seed, controls_only=True)
        (args.output / "results.json").write_text(
            json.dumps({"scenario": "validation", "controls_only": True, "controls": controls},
                       indent=2), encoding="utf-8")
        return 0 if all(item["passed"] for item in controls) else 1
    all_trials = []
    report_path = args.output / "results.json"
    for trial_number in range(1, args.trials + 1):
        trial_root = args.output if args.trials == 1 else args.output / f"trial-{trial_number:03d}"
        if args.trials > 1:
            trial_root.mkdir()
        trial = {"trial": trial_number,
                 "smoke": smoke(trial_root / "smoke", args.models, tool_protocol=args.tool_protocol,
                                strict_json_profile=args.strict_json_profile,
                                progress_guidance=args.progress_guidance,
                                fixture_seed=args.fixture_seed, trial_number=trial_number)}
        if args.laravel:
            trial["laravel"] = laravel(args.laravel.resolve(), trial_root, args.models, args.php,
                                      tool_protocol=args.tool_protocol, strict_json_profile=args.strict_json_profile,
                                      progress_guidance=args.progress_guidance, scenario=args.scenario,
                                      preserve_sibling_route=args.preserve_sibling_route,
                                      fixture_seed=args.fixture_seed, trial_number=trial_number)
        all_trials.append(trial)
        # Partial report saved after each trial; model content/hidden names are never reported.
        if args.trials == 1:
            report = {k: v for k, v in trial.items() if k != "trial"}
        else:
            report = {"configuration": {"trials_requested": args.trials, "scenario": args.scenario,
                                         "preserve_sibling_route": args.preserve_sibling_route,
                                         "tool_protocol": args.tool_protocol,
                                         "strict_json_profile": args.strict_json_profile,
                                         "progress_guidance": args.progress_guidance,
                                         "paired_fixture_id": (hashlib.sha256(bytes.fromhex(args.fixture_seed)).hexdigest()[:16]
                                                               if args.fixture_seed else None)},
                      "trials": all_trials}
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    # No optimistic inference from model narratives. Use each task's actual verified pass signal.
    all_results = [result for trial in all_trials for name in ("smoke", "laravel")
                   for result in trial.get(name, [])]
    if args.trials > 1:
        report["summary"] = {
            model: {name: {"passed": sum(1 for trial in all_trials for item in trial.get(name, [])
                                            if item["model"] == model and item["passed"]),
                           "total": sum(1 for trial in all_trials for item in trial.get(name, [])
                                        if item["model"] == model)}
                    for name in ("smoke", "laravel") if any(name in trial for trial in all_trials)}
            for model in args.models}
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return 0 if all(result["passed"] for result in all_results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
