"""Bounded optional evaluator tool-round tests. No PHP or Ollama required."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from benchmarks.evaluate import main, task
from benchmarks.compare import compare


class SlowModel:
    def __init__(self):
        self.calls = 0

    def complete(self, messages, tools, **kwargs):
        self.calls += 1
        if self.calls <= 8:
            return {"content": json.dumps({"type": "tool", "name": "read_file",
                                           "arguments": {"path": "composer.json"}})}
        return {"content": json.dumps({"type": "final", "content": "tinybuilder/sample and ^12.0"})}


class StepBudgetTests(unittest.TestCase):
    def test_default_stays_eight_but_opt_in_can_finish_in_nine_rounds(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "composer.json").write_text(
                '{"name":"tinybuilder/sample","require":{"laravel/framework":"^12.0"}}')
            observed = []
            for opts in ({}, {"max_steps": 12}):
                with patch("benchmarks.evaluate.ChatModel", return_value=SlowModel()):
                    with contextlib.redirect_stdout(io.StringIO()):
                        observed.append(task("fake", root, "Inspect",
                                             expected=("tinybuilder/sample", "^12.0"),
                                             tool_protocol="strict-json",
                                             strict_json_profile="constrained", **opts))
            self.assertFalse(observed[0]["passed"])
            self.assertTrue(observed[1]["passed"])
            self.assertEqual([r["valid_tool_calls"] for r in observed], [8, 8])

    def test_invalid_rounds_rejected_before_output(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "missing"
            for rounds in ("0", "3", "21"):
                with self.subTest(rounds=rounds), patch("sys.argv", [
                    "evaluate.py", "--max-steps", rounds, "--output", str(output)
                ]), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
                    main()
                self.assertEqual(caught.exception.code, 2)
                self.assertFalse(output.exists())

    def test_comparison_rejects_different_budgets(self):
        with tempfile.TemporaryDirectory() as directory:
            outputs = []
            for rounds in (8, 12):
                output = Path(directory) / str(rounds)
                with patch("sys.argv", ["evaluate.py", "--max-steps", str(rounds),
                                        "--trials", "2", "--models", "fake",
                                        "--output", str(output)]), \
                     patch("benchmarks.evaluate.ChatModel") as model, \
                     contextlib.redirect_stdout(io.StringIO()):
                    model.return_value.complete.return_value = {"content": "No tool"}
                    self.assertEqual(main(), 1)
                report = output / "results.json"
                self.assertEqual(json.loads(report.read_text())["configuration"]["max_steps"], rounds)
                outputs.append(report)
            with self.assertRaisesRegex(ValueError, "max_steps"):
                compare(*outputs)


if __name__ == "__main__":
    unittest.main()
