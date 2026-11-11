"""Evaluator-only regression checks. No PHP, Ollama or network is invoked."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from benchmarks.evaluate import (READ_TASK, REPAIR_TASK, REPAIR_TEST_PATH, change_scope_verified,
                                 hidden_health_test, main, prepare_route_variant, sequence_verified)


class TestEvaluationVariants(unittest.TestCase):
    def test_default_scenario_does_not_rewrite_measured_fixture(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "routes").mkdir()
            route = root / "routes/web.php"
            original = b"<?php\r\nRoute::get('/', fn () => 'ok');\r\n"
            route.write_bytes(original)
            result = prepare_route_variant(root)
            self.assertEqual(route.read_bytes(), original)
            self.assertEqual(result["initial_route"].replace("\n", "\r\n").encode(), original)
            self.assertIsNone(result["slug"])

    def test_repair_and_preservation_seed_only_disposable_route(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "routes").mkdir()
            (root / "routes/web.php").write_text("<?php\nRoute::get('/', fn () => 'ok');\n")
            fixture = prepare_route_variant(root, scenario="repair", preserve_sibling_route=True)
            route = (root / "routes/web.php").read_text()
            self.assertIn("'status' => 'broken'", route)
            self.assertIn(fixture["slug"], route)
            self.assertTrue((root / REPAIR_TEST_PATH).is_file())
            visible = (root / REPAIR_TEST_PATH).read_text()
            self.assertIn("TinyBuilderRepairRegressionTest", visible)
            self.assertIn("'status' => 'ok'", visible)
            hidden = hidden_health_test(fixture["slug"], fixture["marker"])
            self.assertIn("test_original_home_survives", hidden)
            self.assertIn("test_sibling_route_is_preserved", hidden)
            self.assertIn("test_health_endpoint", hidden)
            self.assertIn(fixture["marker"], hidden)
            self.assertNotIn(fixture["marker"], REPAIR_TASK)
            self.assertNotIn(fixture["marker"], READ_TASK)

    def test_repair_never_accepts_visible_test_changes_or_unchanged_route(self):
        paths = ["routes/web.php", REPAIR_TEST_PATH]
        self.assertTrue(change_scope_verified(paths, True, "repair", True))
        self.assertFalse(change_scope_verified(paths, False, "repair", True))
        self.assertFalse(change_scope_verified(paths, True, "repair", False))
        self.assertFalse(change_scope_verified(paths + ["tests/Feature/Other.php"], True, "repair", True))
        self.assertFalse(change_scope_verified([REPAIR_TEST_PATH], True, "repair", True))

    def test_only_correctly_ordered_successful_operations_satisfy_sequence(self):
        expected = [("read_file", "routes/web.php"), ("write_file", "routes/web.php"),
                    ("run_command", ("php", "artisan", "test"))]
        self.assertTrue(sequence_verified(expected, expected))
        self.assertFalse(sequence_verified(expected[:2], expected))
        self.assertFalse(sequence_verified([expected[1], expected[0], expected[2]], expected))
        self.assertFalse(sequence_verified([expected[0], expected[2], expected[1]], expected))
        self.assertFalse(sequence_verified([expected[0], ("read_file", "other.php"), expected[2]], expected))

    def test_repeated_smoke_uses_fresh_hidden_names_and_does_not_log_them(self):
        with tempfile.TemporaryDirectory() as d, patch("benchmarks.evaluate.ChatModel") as model:
            root = Path(d)
            output = root / "runs"
            seen_prompts = []

            def complete(messages, tools):
                seen_prompts.append(json.dumps(messages))
                return {"content": "No tool call"}

            model.return_value.complete.side_effect = complete
            with patch("sys.argv", ["evaluate.py", "--output", str(output), "--trials", "3",
                                    "--models", "fake"]), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(), 1)  # A claim without real read must fail.
            packages = [json.loads((output / f"trial-{i:03d}" / "smoke/composer.json").read_text())["name"]
                        for i in (1, 2, 3)]
            self.assertEqual(len(set(packages)), 3)
            report_text = (output / "results.json").read_text()
            self.assertFalse(any(package in report_text for package in packages))
            self.assertFalse(any(package in prompt for package in packages for prompt in seen_prompts))
            report = json.loads(report_text)
            self.assertEqual(len(report["trials"]), 3)
            self.assertEqual(report["summary"]["fake"]["smoke"], {"passed": 0, "total": 3})
            self.assertTrue(all(not trial["smoke"][0]["passed"] for trial in report["trials"]))

    def test_variant_flags_refuse_unmarked_or_missing_laravel_baseline(self):
        with tempfile.TemporaryDirectory() as d:
            for rest in (["--scenario", "repair"], ["--preserve-sibling-route"]):
                with patch("sys.argv", ["evaluate.py", "--output", str(Path(d) / "attempt"), *rest]):
                    with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
                        main()
                    self.assertEqual(caught.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
