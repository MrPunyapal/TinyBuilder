import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from benchmarks.evaluate import laravel, smoke, task


class TestBenchmark(unittest.TestCase):
    def test_correct_guess_without_tool_call_is_failure(self):
        with tempfile.TemporaryDirectory() as d, patch("benchmarks.evaluate.ChatModel") as model:
            model.return_value.complete.return_value = {"content": "random/package ^12.0"}
            with patch("builtins.print"):
                result = task("fake", Path(d), "inspect", expected=["random/package", "^12.0"])
            self.assertTrue(result["facts_correct"])
            self.assertFalse(result["passed"])
            self.assertEqual(result["failure_kind"], "no_tool_call")

    def test_random_package_is_not_in_prompt_or_report(self):
        with tempfile.TemporaryDirectory() as d, patch("benchmarks.evaluate.ChatModel") as model:
            root = Path(d) / "smoke"
            def complete(messages, tools):
                package = json.loads((root / "composer.json").read_text())["name"]
                self.assertNotIn(package, json.dumps(messages))
                return {"content": package + " ^12.0"}
            model.return_value.complete.side_effect = complete
            with patch("builtins.print"):
                result = smoke(root, ["fake"])
            self.assertFalse(result[0]["passed"])
            self.assertNotIn("tinybuilder/", json.dumps(result))

    def test_refuses_unmarked_laravel_project_before_commands(self):
        with tempfile.TemporaryDirectory() as d, patch("benchmarks.evaluate.command") as command:
            with self.assertRaisesRegex(ValueError, "NEW disposable"):
                laravel(Path(d), Path(d), ["fake"], "php")
            command.assert_not_called()

    def test_strict_json_valid_read_only_passes_only_with_real_tool_call(self):
        with tempfile.TemporaryDirectory() as d, patch("benchmarks.evaluate.ChatModel") as model:
            root = Path(d) / "smoke"
            replies = []
            def complete(messages, tools):
                self.assertEqual(tools, [])
                if len(messages) == 2:
                    return {"content": json.dumps({"type": "tool", "name": "read_file", "arguments": {"path": "composer.json"}})}
                package = json.loads((root / "composer.json").read_text())["name"]
                return {"content": json.dumps({"type": "final", "content": package + " ^12.0"})}
            model.return_value.complete.side_effect = complete
            with patch("builtins.print"):
                result = smoke(root, ["fake"], tool_protocol="strict-json")
            self.assertTrue(result[0]["passed"])
            self.assertEqual(result[0]["tool_protocol"], "strict-json")
