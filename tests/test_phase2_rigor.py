"""No network/model/PHP: deterministic rigor checks for opt-in paired trials."""
import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from benchmarks.evaluate import (main, smoke, task, tests_after_last_edit_verified,
                                 validate_laravel_baseline)

SEED = "0123456789abcdef0123456789abcdef"


class Phase2RigorTests(unittest.TestCase):
    def test_paired_seed_matches_same_trial_and_varies_between_trials(self):
        with tempfile.TemporaryDirectory() as d, patch("benchmarks.evaluate.ChatModel") as model:
            model.return_value.complete.return_value = {"content": "No source inspection"}
            root = Path(d)
            prompts = []

            def no_tool(messages, tools):
                prompts.append(json.dumps(messages))
                return {"content": "No source inspection"}

            model.return_value.complete.side_effect = no_tool
            packages, reports = [], []
            for index in (1, 1, 2):
                fixture = root / f"fixture-{len(packages)}"
                with patch("builtins.print"):
                    reports.extend(smoke(fixture, ["fake"], fixture_seed=SEED, trial_number=index))
                packages.append(json.loads((fixture / "composer.json").read_text())["name"])
            self.assertEqual(packages[0], packages[1])
            self.assertNotEqual(packages[0], packages[2])
            self.assertTrue(all(not item["passed"] for item in reports))
            self.assertTrue(all(pkg not in json.dumps(reports) for pkg in packages))
            self.assertTrue(all(pkg not in prompt for pkg in packages for prompt in prompts))

    def test_paired_sibling_route_is_repeatable_and_hidden(self):
        from benchmarks.evaluate import prepare_route_variant
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            markers = []
            for i in (1, 2):
                project = root / str(i)
                (project / "routes").mkdir(parents=True)
                (project / "routes/web.php").write_text("<?php\n")
                fixture = prepare_route_variant(project, preserve_sibling_route=True,
                                                paired_marker="a" * 32)
                markers.append((fixture["slug"], fixture["marker"]))
            self.assertEqual(markers[0], markers[1])
            self.assertEqual(markers[0][0], "tinybuilder-preserve-aaaaaaaaaaaa")

    def test_invalid_seed_refused_before_any_output_creation(self):
        with tempfile.TemporaryDirectory() as d:
            for seed in ("short", "z" * 32, "0" * 31 + "\\n", "0" * 33):
                output = Path(d) / "out"
                with self.subTest(seed=seed), patch("sys.argv", ["evaluate.py", "--output", str(output),
                                                                  "--fixture-seed", seed]), \
                        contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
                    main()
                self.assertEqual(caught.exception.code, 2)
                self.assertFalse(output.exists())

    def test_test_command_must_follow_last_edit(self):
        target = Path("routes/web.php")
        allowed = ("php", "artisan", "test")
        read, write, test = (("read_file", target), ("write_file", target),
                             ("run_command", allowed))
        self.assertTrue(tests_after_last_edit_verified([read, write, test], target, allowed))
        self.assertFalse(tests_after_last_edit_verified([read, write, test, write], target, allowed))
        self.assertTrue(tests_after_last_edit_verified([read, write, test, write, test], target, allowed))
        self.assertFalse(tests_after_last_edit_verified([read, test, write], target, allowed))
        self.assertFalse(tests_after_last_edit_verified([read, write], target, allowed))

    def test_tool_order_failure_when_model_edits_after_its_last_test(self):
        with tempfile.TemporaryDirectory() as d, patch("benchmarks.evaluate.ChatModel") as model:
            root = Path(d)
            (root / "routes").mkdir()
            (root / "routes/web.php").write_text("before")
            (root / "artisan").write_text("print('ok')\n")
            replies = [
                {"content": json.dumps({"type": "tool", "name": "read_file", "arguments": {"path": "routes/web.php"}})},
                {"content": json.dumps({"type": "tool", "name": "write_file", "arguments": {"path": "routes/web.php", "content": "first"}})},
                {"content": json.dumps({"type": "tool", "name": "run_command", "arguments": {"argv": [sys.executable, "artisan", "test"]}})},
                {"content": json.dumps({"type": "tool", "name": "write_file", "arguments": {"path": "routes/web.php", "content": "second"}})},
                {"content": '{"type":"final","content":"All tests passed"}'}
            ]
            model.return_value.complete.side_effect = replies
            with patch("builtins.print"):
                result = task("fake", root, "Read, edit and test", write=True, php=sys.executable,
                              tool_protocol="strict-json", required_files=("routes/web.php",),
                              required_tools=("read_file", "write_file", "run_command"),
                              required_sequence=(("read_file", root / "routes/web.php"),
                                                 ("write_file", root / "routes/web.php"),
                                                 ("run_command", (sys.executable, "artisan", "test"))))
            self.assertTrue(result["required_sequence_ok"])
            self.assertFalse(result["tests_after_last_edit"])
            self.assertEqual(result["failure_kind"], "tool_order")
            self.assertEqual((root / "routes/web.php").read_text(), "second")

    def _baseline(self, root):
        root.mkdir()
        for name, content in {
            ".tinybuilder-disposable": "ONLY FOR BENCHMARKS", ".gitignore": "vendor/\n.env\n",
            "composer.lock": "{}", ".env.example": "APP_KEY=\n",
            "routes/web.php": "<?php\n", "bootstrap/app.php": "<?php\n"
        }.items():
            file = root / name
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text(content)
        subprocess.run(["git", "init", "-q", "--initial-branch=main"], cwd=root, check=True)
        subprocess.run(["git", "add", "."], cwd=root, check=True)
        subprocess.run(["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                        "commit", "-qm", "test fixture"], cwd=root, check=True)
        (root / "vendor").mkdir()
        return root

    def test_preflight_refuses_nested_output_untracked_and_missing_dependencies(self):
        with tempfile.TemporaryDirectory() as d:
            top = Path(d)
            base = self._baseline(top / "baseline")
            self.assertTrue(validate_laravel_baseline(base, top / "separate"))
            with self.assertRaisesRegex(ValueError, "separate"):
                validate_laravel_baseline(base, base / "eval")
            (base / "untracked.php").write_text("not committed")
            with self.assertRaisesRegex(ValueError, "untracked"):
                validate_laravel_baseline(base, top / "separate")
            (base / "untracked.php").unlink()
            (base / "vendor").rmdir()
            with self.assertRaisesRegex(ValueError, "vendor"):
                validate_laravel_baseline(base, top / "separate")

    def test_main_rejects_bad_baseline_before_model_or_output(self):
        with tempfile.TemporaryDirectory() as d:
            top = Path(d)
            base = self._baseline(top / "baseline")
            output = base / "unsafe-benchmark"
            with patch("sys.argv", ["evaluate.py", "--output", str(output), "--laravel", str(base)]), \
                 patch("benchmarks.evaluate.ChatModel") as model, \
                 contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
                main()
            self.assertEqual(caught.exception.code, 2)
            self.assertFalse(output.exists())
            model.assert_not_called()


if __name__ == "__main__":
    unittest.main()
