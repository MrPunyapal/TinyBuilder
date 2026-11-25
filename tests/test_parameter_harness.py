"""Fake-artisan end-to-end parameter harness tests; NOT Laravel or Ollama proof."""
import contextlib
import io
import json
import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from benchmarks.evaluate import laravel, main
from benchmarks.parameter_case import (
    BAD_PARAMETER_ROUTE, PARAMETER_HIDDEN_PATH, PARAMETER_PATH,
    reference_fixed_parameter,
)
from test_laravel_harness import HarnessTest, ScriptedModel, response_tool


FAKE_PARAMETER_ARTISAN = r'''import json, pathlib, re, sys
root = pathlib.Path.cwd()
source = (root / "routes/web.php").read_text()
visible = root / "tests/Feature/TinyBuilderParameterRegressionTest.php"
hidden = root / "tests/Feature/TinyBuilderParameterHiddenTest.php"
argv = sys.argv[1:]
fixed = "ctype_digit($id)" in source and "['id' => (int) $id]" in source
if argv and argv[0] == "test":
    if (visible.exists() or hidden.exists()) and not fixed:
        sys.exit(1)
    if hidden.exists() and "test_unrelated_sibling_survives" in hidden.read_text():
        slug = re.search(r"tinybuilder-preserve-[0-9a-f]+", hidden.read_text())
        if not slug or slug.group(0) not in source:
            sys.exit(1)
    sys.exit(0)
if argv[:2] == ["route:list", "--path=tinybuilder/items/{id}"]:
    print(json.dumps([{"uri": "tinybuilder/items/{id}", "method": "GET|HEAD"}]
                     if "Route::get('/tinybuilder/items/{id}'" in source else []))
    sys.exit(0)
sys.exit(0)
'''


class ParameterHarnessTests(unittest.TestCase):
    def seed(self, root):
        home = root / "baseline"
        HarnessTest().seed_repo(home)
        (home / "artisan").write_text(FAKE_PARAMETER_ARTISAN, encoding="utf-8")
        subprocess.run(["git", "add", "artisan"], cwd=home, check=True)
        subprocess.run(["git", "commit", "-qm", "fake parameter runner"], cwd=home, check=True)
        return home

    def test_controls_only_does_not_infer_or_leave_reference_patch(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            home = self.seed(root)
            output = root / "controls"
            with patch("benchmarks.evaluate.ChatModel") as model, \
                 patch("sys.argv", ["evaluate.py", "--scenario", "parameter", "--controls-only",
                                    "--laravel", str(home), "--php", sys.executable,
                                    "--preserve-sibling-route", "--output", str(output)]), \
                 contextlib.redirect_stdout(io.StringIO()):
                code = main()
            self.assertEqual(code, 0)
            model.assert_not_called()
            report = json.loads((output / "results.json").read_text(encoding="utf-8"))
            control = report["controls"][0]
            self.assertEqual(report["scenario"], "parameter")
            self.assertTrue(control["passed"])
            self.assertTrue(control["reference_passed"])
            self.assertEqual(control["composer_lock_sha256"],
                             hashlib.sha256((home / "composer.lock").read_bytes()).hexdigest())
            self.assertEqual(control["negative_visible_exit"], 1)
            self.assertEqual(control["negative_hidden_exit"], 1)
            self.assertFalse((output / "laravel-0" / PARAMETER_HIDDEN_PATH).exists())
            self.assertIn(BAD_PARAMETER_ROUTE, (output / "laravel-0/routes/web.php").read_text())
            self.assertNotIn(str(root), json.dumps(report))

    def test_scripted_model_requires_actual_reads_edit_and_test(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            home = self.seed(root)
            output = root / "out"
            output.mkdir()
            model_root = output / "laravel-0"

            class Edit:
                def __init__(self):
                    self.round = 0
                def complete(self, messages, tools, **kwargs):
                    self.round += 1
                    if self.round == 1:
                        return response_tool("read_file", path="routes/web.php")
                    if self.round == 2:
                        return response_tool("read_file", path=PARAMETER_PATH)
                    if self.round == 3:
                        source = (model_root / "routes/web.php").read_text()
                        return response_tool("write_file", path="routes/web.php",
                                             content=reference_fixed_parameter(source))
                    if self.round == 4:
                        return response_tool("run_command", argv=[sys.executable, "artisan", "test"])
                    return {"content": json.dumps({"type": "final", "content": "Passed"})}

            read = ScriptedModel([
                response_tool("read_file", path="routes/web.php"),
                response_tool("read_file", path="bootstrap/app.php"),
                {"content": json.dumps({"type": "final", "content": "Read"})},
            ])
            with patch("benchmarks.evaluate.ChatModel", side_effect=[read, Edit()]), \
                 contextlib.redirect_stdout(io.StringIO()):
                result = laravel(home, output, ["mock"], sys.executable,
                                 scenario="parameter", preserve_sibling_route=True,
                                 tool_protocol="strict-json", strict_json_profile="constrained")[0]
            self.assertTrue(result["passed"], json.dumps(result, indent=2))
            self.assertTrue(result["parameter_reference_passed"])
            self.assertIsNone(result["baseline_health_exit"])
            self.assertEqual(result["baseline_parameter_exit"], 1)
            self.assertTrue(result["write"]["required_reads_before_edit"])
            self.assertTrue(result["write"]["tests_after_last_edit"])
            self.assertEqual(result["validation_test_exit"], 0)
            self.assertTrue(result["change_scope_ok"])
            self.assertIsNone(result["php_lint_exit"])


if __name__ == "__main__":
    unittest.main()
