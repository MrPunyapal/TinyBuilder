"""Deterministic Laravel *harness* tests with a fake artisan executable.

These DO NOT represent actual PHP/Laravel inference or runtime validation.
"""
import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from benchmarks.evaluate import REPAIR_TEST_PATH, command, laravel

FAKE_ARTISAN = r'''import json, pathlib, sys
root = pathlib.Path.cwd()
route = (root / "routes/web.php").read_text()
args = sys.argv[1:]
if args and args[0] == "test":
    hidden = root / "tests/Feature/TinyBuilderHealthTest.php"
    visible = root / "tests/Feature/TinyBuilderRepairRegressionTest.php"
    if (hidden.exists() or visible.exists()) and "['status' => 'ok']" not in route:
        sys.exit(1)
    if hidden.exists() and "test_sibling_route_is_preserved" in hidden.read_text():
        # Extract the random route name from the hidden assertion; check source retains it.
        import re
        found = re.search(r"tinybuilder-preserve-[0-9a-f]+", hidden.read_text())
        if not found or found.group(0) not in route:
            sys.exit(1)
    sys.exit(0)
if args[:2] == ["route:list", "--path=health"]:
    print(json.dumps([{"uri": "health", "method": "GET|HEAD"}] if "'/health'" in route else []))
    sys.exit(0)
sys.exit(0)
'''


def response_tool(name, **args):
    return {"content": json.dumps({"type": "tool", "name": name, "arguments": args})}


class ScriptedModel:
    def __init__(self, answers):
        self.answers = iter(answers)

    def complete(self, messages, tools, **kwargs):
        return next(self.answers)


class HarnessTest(unittest.TestCase):
    def test_evaluator_project_commands_use_shell_false(self):
        completed = subprocess.CompletedProcess([], 0, "", "")
        with patch("benchmarks.evaluate.subprocess.run", return_value=completed) as run:
            command([sys.executable, "artisan", "test"], Path.cwd())
        self.assertIs(run.call_args.kwargs["shell"], False)

    def seed_repo(self, home):
        home.mkdir()
        for path, text in {"artisan": FAKE_ARTISAN,
                           "routes/web.php": "<?php\nRoute::get('/', fn () => 'home');\n",
                           "bootstrap/app.php": "<?php\n// boot\n",
                           ".env.example": "APP_KEY=\n", "composer.lock": '{}',
                           ".tinybuilder-disposable": "Disposable only", ".gitignore": "vendor/\n.env\n",
                           "tests/Feature/.gitkeep": ""}.items():
            target = home / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text)
        subprocess.run(["git", "init", "-q", "--initial-branch=main"], cwd=home, check=True)
        subprocess.run(["git", "config", "user.name", "EvaluationTest"], cwd=home, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=home, check=True)
        subprocess.run(["git", "add", "."], cwd=home, check=True)
        subprocess.run(["git", "commit", "-qm", "disposable fixture"], cwd=home, check=True)
        (home / "vendor").mkdir()
        (home / "vendor" / "placeholder").write_text("fake PHP dependencies")

    def test_repair_accepts_only_a_real_scripted_edit_and_test_order(self):
        with tempfile.TemporaryDirectory() as d:
            home = Path(d) / "base"
            output = Path(d) / "out"
            output.mkdir()
            self.seed_repo(home)
            model_root = output / "laravel-0"
            read = ScriptedModel([
                response_tool("read_file", path="routes/web.php"),
                response_tool("read_file", path="bootstrap/app.php"),
                {"content": json.dumps({"type": "final", "content": "Read both files"})},
            ])

            class EditModel:
                calls = 0

                def complete(self, messages, tools, **kwargs):
                    self.calls += 1
                    if self.calls == 1:
                        return response_tool("read_file", path="routes/web.php")
                    if self.calls == 2:
                        return response_tool("read_file", path=REPAIR_TEST_PATH)
                    if self.calls == 3:
                        source = (model_root / "routes/web.php").read_text()
                        return response_tool("write_file", path="routes/web.php",
                                             content=source.replace("'status' => 'broken'", "'status' => 'ok'"))
                    if self.calls == 4:
                        return response_tool("run_command", argv=[sys.executable, "artisan", "test"])
                    return {"content": json.dumps({"type": "final", "content": "Tests passed"})}

            with patch("benchmarks.evaluate.ChatModel", side_effect=[read, EditModel()]):
                with contextlib.redirect_stdout(io.StringIO()):
                    result = laravel(home, output, ["fake"], sys.executable,
                                    tool_protocol="strict-json", strict_json_profile="constrained",
                                    progress_guidance="checklist", scenario="repair",
                                    preserve_sibling_route=True)[0]
            self.assertTrue(result["passed"], json.dumps(result, indent=2))
            self.assertEqual(result["baseline_repair_exit"], 1)
            self.assertTrue(result["model_changed_route"])
            self.assertTrue(result["write"]["required_sequence_ok"])
            self.assertTrue(result["change_scope_ok"])
            self.assertIn("-", (output / "model-diff-0.patch").read_text())



if __name__ == "__main__":
    unittest.main()
