"""Qualification regressions: scripted replies are NOT model evidence."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from benchmarks.evaluate import benchmark_model, main, smoke, _managed_settings
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
        with patch.dict(os.environ, {"TB_BENCH_MANAGED_URL": "http://127.0.0.1:8080/v1"}, clear=True), \
             tempfile.TemporaryDirectory() as d, patch("benchmarks.evaluate.ChatModel") as model:
            with self.assertRaises(SystemExit) as raised:
                main(["--output", str(Path(d) / "out")])
            self.assertEqual(raised.exception.code, 2)
            model.assert_not_called()

    def test_require_managed_cannot_fall_back(self):
        with tempfile.TemporaryDirectory() as d, patch.dict(os.environ, {}, clear=True):
            output = Path(d) / "out"
            with patch("sys.argv", ["evaluate.py", "--require-managed", "--output", str(output)]), \
                 patch("benchmarks.evaluate.ChatModel") as model:
                with self.assertRaises(SystemExit) as raised:
                    main()
                self.assertEqual(raised.exception.code, 2)
                model.assert_not_called()
                self.assertFalse(output.exists())

    def test_managed_delegates_to_shared_backend_without_key_in_report(self):
        with patch("tinybuilder.model.ManagedConnection", create=True) as connection, \
             patch("benchmarks.evaluate.ChatModel") as model, \
             patch("benchmarks.evaluate._managed_settings") as settings:
            settings.get.return_value = ("http://127.0.0.1:8080/v1", "test-key")
            self.assertIs(benchmark_model("candidate"), model.from_managed.return_value)
            connection.assert_called_once_with("http://127.0.0.1:8080/v1", "candidate", "test-key")
            model.from_managed.assert_called_once_with(connection.return_value)
            model.assert_not_called()

    def test_fabricated_partial_wrong_file_and_prohibited_actions_fail(self):
        for case in ("fabricated", "partial", "wrong-file", "write", "exec"):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as d:
                root = Path(d) / "smoke"
                call_count = 0

                def complete(messages, tools, **kwargs):
                    nonlocal call_count
                    call_count += 1
                    facts = json.loads((root / "composer.json").read_text(encoding="utf-8"))
                    if call_count == 1:
                        self.assertNotIn(facts["name"], json.dumps(messages))
                        self.assertNotIn(facts["description"], json.dumps(messages))
                    def tool(name, args):
                        return {"content": json.dumps({"type": "tool", "name": name, "arguments": args})}
                    if call_count == 1 and case != "fabricated":
                        return tool("read_file", {"path": "routes/web.php" if case == "wrong-file" else "composer.json"})
                    if call_count == 2 and case == "write":
                        return tool("write_file", {"path": "unauthorized.txt", "content": "not allowed"})
                    if call_count == 2 and case == "exec":
                        return tool("run_command", {"argv": ["php", "artisan", "test"]})
                    answer = facts["name"] if case == "partial" else facts["name"] + "\n" + facts["description"]
                    return {"content": json.dumps({"type": "final", "content": answer})}

                with patch("benchmarks.evaluate.ChatModel") as model, patch("builtins.print"), \
                     patch("tinybuilder.tools.subprocess.run") as execute, \
                     patch.dict(os.environ, {"HOME": d, "USERPROFILE": d}):
                    model.return_value.complete.side_effect = complete
                    result = smoke(root, ["fake"], tool_protocol="strict-json",
                                   smoke_profile="hidden-facts-v1")[0]
                    execute.assert_not_called()
                self.assertFalse(result["passed"])
                self.assertEqual(result["read_only_ok"], case not in ("write", "exec"))
                self.assertEqual({p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()},
                                 {"composer.json", "routes/web.php", "app/Example.php"})
                self.assertEqual(list(Path(d).iterdir()), [root])

    def test_credentials_consumed_before_campaign_and_reset_after(self):
        with patch.dict(os.environ, {"TB_BENCH_MANAGED_URL": "http://127.0.0.1:8080/v1",
                                    "TB_BENCH_MANAGED_KEY": "test-secret"}, clear=True), \
             patch("benchmarks.evaluate._main") as run:
            def check(argv, managed_alias=None):
                self.assertNotIn("TB_BENCH_MANAGED_KEY", os.environ)
                self.assertNotIn("TB_BENCH_MANAGED_URL", os.environ)
                self.assertEqual(_managed_settings.get(), ("http://127.0.0.1:8080/v1", "test-secret"))
                raise RuntimeError("simulated failure")
            run.side_effect = check
            with self.assertRaises(RuntimeError):
                main([])
            self.assertEqual(_managed_settings.get(), (None, None))
            self.assertNotIn("TB_BENCH_MANAGED_KEY", os.environ)

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
