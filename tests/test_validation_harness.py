"""Model-free end-to-end harness counterexamples for the validation scenario.

The fake artisan only checks fixture plumbing; it is NOT PHP or Laravel proof.
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

from benchmarks.evaluate import laravel, main
from benchmarks.validation_case import VALIDATION_PATH, reference_fixed_route
from test_laravel_harness import HarnessTest, ScriptedModel, response_tool


FAKE_VALIDATION_ARTISAN = r'''import json, pathlib, sys, re
root = pathlib.Path.cwd()
source = (root / "routes/web.php").read_text()
argv = sys.argv[1:]
visible = root / "tests/Feature/TinyBuilderValidationRegressionTest.php"
hidden = root / "tests/Feature/TinyBuilderValidationHiddenTest.php"
fixed = "$request->validate([" in source and "'min:3'" in source and "'email'" in source
if argv and argv[0] == "test":
    if (visible.exists() or hidden.exists()) and not fixed:
        sys.exit(1)
    if hidden.exists() and "test_unrelated_sibling_route_survives" in hidden.read_text():
        slug = re.search(r"tinybuilder-preserve-[0-9a-f]+", hidden.read_text())
        if not slug or slug.group(0) not in source:
            sys.exit(1)
    sys.exit(0)
if argv[:2] == ["route:list", "--path=tinybuilder/contact"]:
    result = ([{"uri": "tinybuilder/contact", "method": "POST"}]
              if "Route::post('/tinybuilder/contact'" in source else [])
    print(json.dumps(result))
    sys.exit(0)
sys.exit(0)
'''


def read_model():
    return ScriptedModel([
        response_tool("read_file", path="routes/web.php"),
        response_tool("read_file", path="bootstrap/app.php"),
        {"content": json.dumps({"type": "final", "content": "Inspected both files"})},
    ])


class EditModel:
    def __init__(self, project, early_visible=False, off_target=False, no_edit=False):
        self.project = project
        self.early_visible = early_visible
        self.off_target = off_target
        self.no_edit = no_edit
        self.n = 0

    def complete(self, messages, tools, **kwargs):
        self.n += 1
        if self.n == 1:
            return response_tool("read_file", path="routes/web.php")
        if self.n == 2:
            if self.early_visible:
                # Correct run reads both files before the first write.
                return response_tool("read_file", path=VALIDATION_PATH)
            source = (self.project / "routes/web.php").read_text()
            return response_tool("write_file", path="routes/web.php", content=reference_fixed_route(source))
        if self.n == 3:
            if not self.early_visible:
                # Incorrect run reads visible regression only AFTER editing.
                return response_tool("read_file", path=VALIDATION_PATH)
            source = (self.project / "routes/web.php").read_text()
            if self.no_edit:
                return {"content": json.dumps({"type": "final", "content": "Finished without editing"})}
            return response_tool("write_file", path="routes/web.php", content=reference_fixed_route(source))
        if self.n == 4 and self.off_target:
            return response_tool("write_file", path=".env", content="APP_KEY=changed-by-model")
        if self.n == (5 if self.off_target else 4):
            return response_tool("run_command", argv=[sys.executable, "artisan", "test"])
        return {"content": json.dumps({"type": "final", "content": "Tests passed"})}


class ValidationHarnessTests(unittest.TestCase):
    def seed(self, location):
        home = location / "baseline"
        HarnessTest().seed_repo(home)
        (home / "artisan").write_text(FAKE_VALIDATION_ARTISAN, encoding="utf-8")
        subprocess.run(["git", "add", "artisan"], cwd=home, check=True)
        subprocess.run(["git", "commit", "-qm", "fake validation runner"], cwd=home, check=True)
        return home

    def test_controls_only_never_calls_the_model(self):
        with tempfile.TemporaryDirectory() as directory:
            top = Path(directory)
            home = self.seed(top)
            output = top / "controls"
            with patch("benchmarks.evaluate.ChatModel") as model:
                with patch("sys.argv", ["evaluate.py", "--scenario", "validation",
                                        "--controls-only", "--laravel", str(home),
                                        "--php", sys.executable, "--output", str(output)]):
                    with contextlib.redirect_stdout(io.StringIO()):
                        exit_code = main()
            self.assertEqual(exit_code, 0)
            model.assert_not_called()
            data = json.loads((output / "results.json").read_text())
            control = data["controls"][0]
            self.assertTrue(control["passed"])
            self.assertTrue(control["reference_passed"])
            self.assertEqual(control["negative_hidden_exit"], 1)
            self.assertEqual(control["negative_visible_exit"], 1)
            self.assertEqual(control["worktree"], "laravel-0")
            self.assertNotIn(str(top), json.dumps(data))
            self.assertFalse((output / "laravel-0/tests/Feature/TinyBuilderValidationHiddenTest.php").exists())
            self.assertNotIn("$request->validate(", (output / "laravel-0/routes/web.php").read_text())

    def evaluate(self, home, output, **kwargs):
        model_root = output / "laravel-0"
        with patch("benchmarks.evaluate.ChatModel", side_effect=[
                read_model(), EditModel(model_root, **kwargs)]):
            with contextlib.redirect_stdout(io.StringIO()):
                return laravel(home, output, ["fake"], sys.executable,
                               tool_protocol="strict-json", strict_json_profile="constrained",
                               scenario="validation", preserve_sibling_route=True)[0]

    def test_scripted_reference_edit_passes_only_after_real_tool_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            top = Path(directory)
            home = self.seed(top)
            output = top / "out"
            output.mkdir()
            result = self.evaluate(home, output, early_visible=True)
            self.assertTrue(result["passed"], json.dumps(result, indent=2))
            self.assertTrue(result["validation_reference_passed"])
            self.assertTrue(result["write"]["required_reads_before_edit"])
            self.assertTrue(result["write"]["tests_after_last_edit"])
            self.assertTrue(result["change_scope_ok"])
            self.assertEqual(result["validation_test_exit"], 0)
            self.assertNotIn(str(top), json.dumps(result))

    def test_late_test_read_rejected_even_after_reference_fix_and_passing_suite(self):
        with tempfile.TemporaryDirectory() as directory:
            top = Path(directory)
            home = self.seed(top)
            output = top / "out"
            output.mkdir()
            result = self.evaluate(home, output, early_visible=False)
            self.assertEqual(result["validation_test_exit"], 0)
            self.assertFalse(result["write"]["required_reads_before_edit"])
            self.assertFalse(result["passed"])

    def test_off_target_ignored_write_rejected_despite_passing_tests(self):
        with tempfile.TemporaryDirectory() as directory:
            top = Path(directory)
            home = self.seed(top)
            output = top / "out"
            output.mkdir()
            result = self.evaluate(home, output, early_visible=True, off_target=True)
            self.assertEqual(result["validation_test_exit"], 0)
            self.assertFalse(result["model_write_scope_ok"])
            self.assertFalse(result["passed"])


if __name__ == "__main__":
    unittest.main()
