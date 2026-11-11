"""Opt-in local-model evaluation. Never downloads weights or saves model/MCP content.

Run with the installed TinyBuilder Python: python benchmarks/evaluate.py --help.
"""

import argparse
import hashlib
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


READ_TASK = ("Use read_file to inspect composer.json. Report its exact package name and "
             "laravel/framework version constraint. Do not guess or change any files.")
ROUTE_TASK = ("Read routes/web.php and bootstrap/app.php using tools. Explain the existing routes "
              "and how to add GET /health returning JSON {\"status\":\"ok\"}. Do not change files.")
WRITE_TASK = ("Read routes/web.php first. Add GET /health returning JSON {\"status\":\"ok\"} in "
              "routes/web.php, preserving all existing routes. Use write_file to make the change. "
              "Then run [\"php\",\"artisan\",\"test\"] using run_command. Do not modify tests or other files.")
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
    if expected and not result.get("facts_correct", False):
        return "factual"
    return None


def task(model_name, root, prompt, write=False, expected=None, php="php", tool_protocol="native",
         required_tools=()):
    events = []
    local = LocalTools(root, allow_write=write, allow_exec=write,
                       exec_commands=[[php, "artisan", "test"]])
    started = time.monotonic()
    answer, error, error_kind = "", None, None
    try:
        answer = Agent(ChatModel("http://127.0.0.1:11434/v1", model_name), local,
                       max_steps=8, on_event=events.append, tool_protocol=tool_protocol).run(prompt)
    except (ModelError, ProtocolError, OSError, ValueError) as exc:
        # Do not persist HTTP error bodies, which may contain remote or model content.
        error = type(exc).__name__
        error_kind = exc.kind if isinstance(exc, ModelError) else ("protocol" if isinstance(exc, ProtocolError) else "execution")
        if isinstance(exc, ProtocolError) and any(
                event.get("reason", "").startswith("argument_")
                for event in events if event["event"] == "protocol_error"):
            error_kind = "argument"
        print(f"{model_name}: {exc}", file=sys.stderr, flush=True)
    calls = [event for event in events if event["event"] == "tool_end"]
    result = {"model": model_name, "tool_protocol": tool_protocol,
              "duration_seconds": round(time.monotonic() - started, 3),
              "error": error, "error_kind": error_kind, "events": events, "tool_calls": len(calls),
              "valid_tool_calls": sum(event["status"] == "ok" for event in calls),
              "read_file_called": any(event["tool"] == "read_file" and event["status"] == "ok" for event in calls),
              "write_file_called": any(event["tool"] == "write_file" and event["status"] == "ok" for event in calls),
              "run_command_called": any(event["tool"] == "run_command" and event["status"] == "ok" for event in calls),
              "final_answer": bool(answer) and not answer.startswith("Stopped after")}
    if expected:
        required_tools = (*required_tools, "read_file")
    required_tools = tuple(dict.fromkeys(required_tools))
    result["missing_required_tools"] = [name for name in required_tools if not any(
        event["tool"] == name and event["status"] == "ok" for event in calls)]
    if expected:
        result["facts_correct"] = all(value in answer for value in expected)
        result["passed"] = result["facts_correct"] and result["read_file_called"] and result["final_answer"]
    result["failure_kind"] = _failure_kind(result, expected=bool(expected))
    # Answers and observations stay in RAM. Metadata alone goes to the report.
    print(json.dumps(result), flush=True)
    return result


def smoke(root, models, tool_protocol="native"):
    root.mkdir()
    package = "tinybuilder/" + uuid.uuid4().hex
    (root / "composer.json").write_text(json.dumps({"name": package, "type": "project", "require": {
        "php": "^8.2", "laravel/framework": "^12.0"}, "autoload": {"psr-4": {"App\\": "app/"}}}), encoding="utf-8")
    (root / "routes").mkdir()
    (root / "routes/web.php").write_text("<?php\nuse Illuminate\\Support\\Facades\\Route;\nRoute::get('/', fn () => view('welcome'));\n", encoding="utf-8")
    (root / "app").mkdir()
    (root / "app/Example.php").write_text("<?php\nnamespace App;\nclass Example {}\n", encoding="utf-8")
    return [task(model, root, READ_TASK, expected=[package, "^12.0"], tool_protocol=tool_protocol) for model in models]


def laravel(base, output, models, php, tool_protocol="native"):
    # Never execute tests or install dependencies inside an arbitrary user's project.
    # The marker is created explicitly by the operator in a NEW disposable project.
    if not (base / ".tinybuilder-disposable").is_file():
        raise ValueError("--laravel requires a NEW disposable Git project with .tinybuilder-disposable marker")
    revision = require(["git", "rev-parse", "HEAD"], base)
    if require(["git", "status", "--porcelain", "--untracked-files=no"], base):
        raise ValueError("Disposable baseline must have no tracked changes")
    if not (base / "composer.lock").is_file():
        raise ValueError("Disposable baseline requires composer.lock")
    results = []
    for index, model in enumerate(models):
        root = output / f"laravel-{index}"
        require(["git", "worktree", "add", "--detach", str(root), revision], base)
        # Copy installed dependencies from this disposable baseline; no network fetches.
        shutil.copytree(base / "vendor", root / "vendor")
        shutil.copyfile(root / ".env.example", root / ".env")
        require([php, "artisan", "key:generate", "--no-interaction"], root)
        baseline = command([php, "artisan", "test"], root)
        test = root / "tests/Feature/TinyBuilderHealthTest.php"
        test.write_text(HEALTH_TEST, encoding="utf-8")
        negative = command([php, "artisan", "test", "--filter=TinyBuilderHealthTest"], root)
        (output / f"baseline-health-{index}.txt").write_text(negative.stdout + negative.stderr, encoding="utf-8")
        test.unlink()  # Evaluator-owned file, kept hidden from the agent.
        read = task(model, root, ROUTE_TASK, tool_protocol=tool_protocol, required_tools=("read_file",))
        write_prompt = WRITE_TASK.replace('["php","artisan","test"]', json.dumps([php, "artisan", "test"]))
        write = task(model, root, write_prompt, write=True, php=php, tool_protocol=tool_protocol,
                     required_tools=("read_file", "write_file", "run_command"))
        # Capture the actual agent diff BEFORE adding the evaluator-owned hidden tests.
        diff = require(["git", "diff", "--", "routes/web.php"], root)
        (output / f"diff-{index}.patch").write_text(diff + "\n", encoding="utf-8")
        changed = require(["git", "status", "--porcelain"], root)
        paths = require(["git", "diff", "--name-only", "HEAD"], root).splitlines()
        paths += require(["git", "ls-files", "--others", "--exclude-standard"], root).splitlines()
        scope_ok = set(paths) == {"routes/web.php"}
        test.write_text(HEALTH_TEST, encoding="utf-8")
        validation = command([php, "artisan", "test"], root)
        routes = command([php, "artisan", "route:list", "--path=health", "--json"], root)
        try:
            health_registered = any(route["uri"] == "health" and "GET" in route["method"]
                                    for route in json.loads(routes.stdout))
        except (ValueError, TypeError, KeyError):
            health_registered = False
        (output / f"phpunit-{index}.txt").write_text(validation.stdout + validation.stderr, encoding="utf-8")
        result = {"model": model, "baseline_commit": revision, "worktree": str(root),
                  "composer_lock_sha256": hashlib.sha256((base / "composer.lock").read_bytes()).hexdigest(),
                  "baseline_test_exit": baseline.returncode, "baseline_health_exit": negative.returncode,
                  "read": read, "write": write,
                  "agent_changes": changed.splitlines(), "route_registered": health_registered,
                  "change_scope_ok": scope_ok,
                  "validation_test_exit": validation.returncode,
                  "passed": baseline.returncode == 0 and negative.returncode == 1 and
                  validation.returncode == 0 and health_registered and bool(diff) and scope_ok and
                  write["write_file_called"] and write["run_command_called"]}
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
    parser.add_argument("--output", type=Path, required=True, help="New directory for disposable fixtures and metadata")
    parser.add_argument("--laravel", type=Path, help="Explicitly marked disposable Laravel baseline Git repository")
    parser.add_argument("--php", default="php", help="PHP binary for evaluator checks")
    args = parser.parse_args()
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=False)
    report = {"smoke": smoke(args.output / "smoke", args.models, tool_protocol=args.tool_protocol)}
    # Save partial evidence even if dependency/setup work later fails.
    report_path = args.output / "results.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    if args.laravel:
        report["laravel"] = laravel(args.laravel.resolve(), args.output, args.models, args.php,
                                    tool_protocol=args.tool_protocol)
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return 0 if all(r["passed"] for group in report.values() for r in group) else 1


if __name__ == "__main__":
    raise SystemExit(main())
