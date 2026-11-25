"""Qualification regressions: scripted replies are NOT model evidence."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from benchmarks.evaluate import benchmark_model, smoke
from benchmarks.compare import compare


class QualificationTests(unittest.TestCase):
    def test_two_facts_hidden_until_read_and_exact_answer_required(self):
        for suffix, passed in (("", True), ("-incorrect", False)):
            with self.subTest(suffix=suffix), tempfile.TemporaryDirectory() as d:
                root = Path(d) / "smoke"
                with patch("benchmarks.evaluate.ChatModel") as model, patch("builtins.print"):
                    calls = 0

                    def complete(messages, tools):
                        nonlocal calls
                        calls += 1
                        data = json.loads((root / "composer.json").read_text(encoding="utf-8"))
                        facts = [data["name"], data["description"]]
                        if calls == 1:
                            for fact in facts:
                                self.assertNotIn(fact, json.dumps(messages))
                            return {"content": json.dumps({"type": "tool", "name": "read_file",
                                                           "arguments": {"path": "composer.json"}})}
                        for fact in facts:
                            self.assertIn(fact, json.dumps(messages))
                        return {"content": json.dumps({"type": "final", "content": "\n".join(facts) + suffix})}

                    model.return_value.complete.side_effect = complete
                    result = smoke(root, ["fake"], tool_protocol="strict-json",
                                   smoke_profile="hidden-facts-v1")[0]
                self.assertEqual(result["passed"], passed)
                self.assertTrue(result["read_file_called"])
                self.assertEqual(result["smoke_profile"], "hidden-facts-v1")
                self.assertNotIn(data_value(root, "description"), json.dumps(result))
                self.assertNotIn(data_value(root, "name"), json.dumps(result))

    def test_paired_inputs_and_distinct_trials(self):
        with tempfile.TemporaryDirectory() as d, patch("benchmarks.evaluate.task", return_value={}):
            root = Path(d)
            for name, number in (("a", 1), ("b", 1), ("c", 2)):
                smoke(root / name, ["fake"], fixture_seed="a" * 32,
                      trial_number=number, smoke_profile="hidden-facts-v1")
            self.assertEqual(data_value(root / "a", "description"), data_value(root / "b", "description"))
            for field in ("name", "description"):
                self.assertNotEqual(data_value(root / "a", field), data_value(root / "c", field))

    def test_partial_managed_configuration_fails_closed(self):
        with patch.dict(os.environ, {"TB_BENCH_MANAGED_URL": "http://127.0.0.1:8080/v1"}, clear=True):
            with patch("benchmarks.evaluate.ChatModel") as model:
                with self.assertRaisesRegex(ValueError, "requires URL and key"):
                    benchmark_model("candidate")
                model.assert_not_called()

    def test_comparer_rejects_mixed_profiles(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            report = {"configuration": {"trials_requested": 2},
                      "trials": [{"trial": i, "smoke": [{"model": "fake", "passed": True}]}
                                 for i in (1, 2)]}
            a, b = root / "a.json", root / "b.json"
            a.write_text(json.dumps(report), encoding="utf-8")
            report["configuration"]["smoke_profile"] = "hidden-facts-v1"
            b.write_text(json.dumps(report), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "smoke_profile"):
                compare(a, b)


def data_value(root, field):
    return json.loads((root / "composer.json").read_text(encoding="utf-8"))[field]
