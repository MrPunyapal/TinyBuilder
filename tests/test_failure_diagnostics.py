"""Sanitized classification regressions; no Laravel, Ollama or PHP required."""
import contextlib
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from benchmarks.evaluate import task, laravel_diagnostics, route_php_lint_exit


class RepeatRead:
    def complete(self, messages, tools, **kwargs):
        return {"content": json.dumps({"type": "tool", "name": "read_file",
                                      "arguments": {"path": "composer.json"}})}


class FailureDiagnosticTests(unittest.TestCase):
    def test_round_budget_is_distinguishable_from_final_answer(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "composer.json").write_text("private-fixture")
            with patch("benchmarks.evaluate.ChatModel", return_value=RepeatRead()):
                with contextlib.redirect_stdout(io.StringIO()):
                    result = task("mock", root, "Read", tool_protocol="strict-json",
                                  strict_json_profile="constrained", max_steps=4)
            self.assertTrue(result["round_exhausted"])
            self.assertFalse(result["final_answer"])
            self.assertEqual(result["failure_kind"], "round_exhausted")
            self.assertEqual(result["test_command_nonzero_count"], 0)
            self.assertEqual(sum(e["event"] == "round_exhausted" for e in result["events"]), 1)
            self.assertNotIn("private-fixture", json.dumps(result))

    def test_only_real_php_binary_triggers_lint(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            with patch("benchmarks.evaluate.command",
                       return_value=subprocess.CompletedProcess([], 255)) as runner:
                self.assertEqual(route_php_lint_exit("php", root), 255)
                runner.assert_called_once_with(["php", "-l", "routes/web.php"], root)
                runner.reset_mock()
                self.assertIsNone(route_php_lint_exit("python", root))
                runner.assert_not_called()

    def test_independent_diagnostics_are_sanitized(self):
        write = {"events": [
            {"event": "protocol_error", "failure_class": "argument"},
            {"event": "tool_end", "tool": "run_command", "reason": "permission"},
            {"event": "final_deferred"}],
            "test_command_nonzero_count": 3, "required_reads_before_edit": False,
            "tests_after_last_edit": False, "round_exhausted": True}
        profile = laravel_diagnostics(write, 255, 1)
        self.assertTrue(profile["php_parse_error"])
        self.assertTrue(profile["final_php_tests_failed"])
        self.assertTrue(profile["round_exhausted"])
        self.assertTrue(profile["missing_pre_edit_reads"])
        self.assertTrue(profile["missing_post_edit_test"])
        self.assertTrue(profile["premature_final_deferred"])
        self.assertEqual(profile["denied_argv_count"], 1)
        self.assertEqual(profile["invalid_argument_count"], 1)
        self.assertEqual(profile["model_test_nonzero_count"], 3)
        self.assertFalse(laravel_diagnostics({"events": []}, 0, 1)["php_parse_error"])
        self.assertNotIn("private", json.dumps(profile))


if __name__ == "__main__":
    unittest.main()
