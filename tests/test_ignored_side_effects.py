"""Reject indirect mutation of an ignored .env file by an otherwise passing run.

Fake artisan simulates a test side effect, not real Laravel or Ollama.
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

from benchmarks.evaluate import laravel
from benchmarks.validation_case import VALIDATION_PATH, reference_fixed_route
from test_laravel_harness import HarnessTest, response_tool
from test_validation_harness import FAKE_VALIDATION_ARTISAN, read_model


class EnvTamperModel:
    def __init__(self, root):
        self.root = root
        self.round = 0

    def complete(self, messages, tools, **kwargs):
        self.round += 1
        if self.round == 1:
            return response_tool("read_file", path="routes/web.php")
        if self.round == 2:
            return response_tool("read_file", path=VALIDATION_PATH)
        if self.round == 3:
            source = (self.root / "routes/web.php").read_text(encoding="utf-8")
            return response_tool("write_file", path="routes/web.php",
                                 content=reference_fixed_route(source) + "\n// tamper-env-on-test\n")
        if self.round == 4:
            return response_tool("run_command", argv=[sys.executable, "artisan", "test"])
        return {"content": json.dumps({"type": "final", "content": "Tests passed"})}


class IgnoredSideEffectTests(unittest.TestCase):
    def test_allowed_command_indirectly_mutating_ignored_env_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            top = Path(directory)
            home = top / "baseline"
            HarnessTest().seed_repo(home)
            modified = FAKE_VALIDATION_ARTISAN.replace(
                'if argv and argv[0] == "test":\n',
                'if argv and argv[0] == "test":\n'
                '    if "tamper-env-on-test" in source:\n'
                '        (root / ".env").write_text("changed-by-test")\n')
            self.assertNotEqual(modified, FAKE_VALIDATION_ARTISAN)
            (home / "artisan").write_text(modified, encoding="utf-8")
            subprocess.run(["git", "add", "artisan"], cwd=home, check=True)
            subprocess.run(["git", "commit", "-qm", "fake command with env side effect"],
                           cwd=home, check=True)
            output = top / "results"
            output.mkdir()
            model_root = output / "laravel-0"
            with patch("benchmarks.evaluate.ChatModel",
                       side_effect=[read_model(), EnvTamperModel(model_root)]):
                with contextlib.redirect_stdout(io.StringIO()):
                    result = laravel(home, output, ["fake"], sys.executable,
                                     scenario="validation", preserve_sibling_route=True,
                                     tool_protocol="strict-json",
                                     strict_json_profile="constrained")[0]
            self.assertEqual(result["validation_test_exit"], 0)
            self.assertTrue(result["change_scope_ok"])
            self.assertTrue(result["model_write_scope_ok"])
            self.assertTrue(result["write"]["tests_after_last_edit"])
            self.assertTrue(result["write"]["required_reads_before_edit"])
            self.assertFalse(result["protected_env_unchanged"])
            self.assertFalse(result["passed"])
            self.assertNotIn(str(top), json.dumps(result))


if __name__ == "__main__":
    unittest.main()
