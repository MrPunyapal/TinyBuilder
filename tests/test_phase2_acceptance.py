"""Counterexamples for Laravel benchmark acceptance with a fake artisan executable.

These exercise the benchmark, not Ollama, PHP or Laravel itself.
"""
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from benchmarks.evaluate import (laravel, reads_before_first_edit_verified,
                                 writes_only_target_verified, REPAIR_TEST_PATH)
from test_laravel_harness import HarnessTest, ScriptedModel, response_tool


class TestPhase2Acceptance(unittest.TestCase):
    def seed_repo(self, path):
        HarnessTest().seed_repo(path)

    def test_required_reads_must_precede_first_edit(self):
        route = Path('routes/web.php')
        regression = Path(REPAIR_TEST_PATH)
        read_route, read_test, edit = (('read_file', route), ('read_file', regression),
                                       ('write_file', route))
        self.assertTrue(reads_before_first_edit_verified([read_route, read_test, edit],
                                                         (route, regression), route))
        self.assertFalse(reads_before_first_edit_verified([read_route, edit, read_test],
                                                          (route, regression), route))
        self.assertFalse(reads_before_first_edit_verified([edit, read_route, read_test, edit],
                                                          (route, regression), route))

    def test_ignored_off_target_write_is_rejected(self):
        route = Path('routes/web.php')
        self.assertTrue(writes_only_target_verified([('write_file', route)], route))
        self.assertFalse(writes_only_target_verified([('write_file', route),
                                                      ('write_file', Path('.env'))], route))
        self.assertFalse(writes_only_target_verified([], route))

    def test_successful_route_cannot_hide_model_write_to_ignored_env(self):
        """A passing PHPUnit suite + clean Git scope must not hide an .env edit."""
        with tempfile.TemporaryDirectory() as d:
            home, output = Path(d) / "base", Path(d) / "out"
            output.mkdir()
            self.seed_repo(home)
            model_root = output / "laravel-0"
            read = ScriptedModel([
                response_tool("read_file", path="routes/web.php"),
                response_tool("read_file", path="bootstrap/app.php"),
                {"content": json.dumps({"type": "final", "content": "Files read"})},
            ])

            class EditModel:
                def __init__(self):
                    self.round = 0

                def complete(self, messages, tools, **kwargs):
                    self.round += 1
                    if self.round == 1:
                        return response_tool("read_file", path="routes/web.php")
                    if self.round == 2:
                        content = (model_root / "routes/web.php").read_text()
                        return response_tool("write_file", path="routes/web.php", content=
                                             content + "\nRoute::get('/health', fn () => "
                                             "response()->json(['status' => 'ok']));\n")
                    if self.round == 3:
                        return response_tool("write_file", path=".env", content="APP_KEY=unexpected\n")
                    if self.round == 4:
                        return response_tool("run_command", argv=[sys.executable, "artisan", "test"])
                    return {"content": json.dumps({"type": "final", "content": "Tests passed"})}

            with patch("benchmarks.evaluate.ChatModel", side_effect=[read, EditModel()]):
                with contextlib.redirect_stdout(io.StringIO()):
                    result = laravel(home, output, ["fake"], sys.executable,
                                    tool_protocol="strict-json", strict_json_profile="constrained")[0]
            self.assertEqual(result["validation_test_exit"], 0)
            self.assertTrue(result["change_scope_ok"])  # Git ignores .env
            self.assertFalse(result["model_write_scope_ok"])
            self.assertFalse(result["passed"])

    def test_repair_read_after_edit_does_not_prove_test_guided_repair(self):
        with tempfile.TemporaryDirectory() as d:
            home, output = Path(d) / "base", Path(d) / "out"
            output.mkdir()
            self.seed_repo(home)
            model_root = output / "laravel-0"
            read = ScriptedModel([
                response_tool("read_file", path="routes/web.php"),
                response_tool("read_file", path="bootstrap/app.php"),
                {"content": json.dumps({"type": "final", "content": "Files read"})},
            ])

            class EditModel:
                def __init__(self):
                    self.round = 0

                def complete(self, messages, tools, **kwargs):
                    self.round += 1
                    if self.round == 1:
                        return response_tool("read_file", path="routes/web.php")
                    if self.round == 2:
                        source = (model_root / "routes/web.php").read_text()
                        return response_tool("write_file", path="routes/web.php",
                                             content=source.replace("'status' => 'broken'", "'status' => 'ok'"))
                    if self.round == 3:
                        return response_tool("read_file", path=REPAIR_TEST_PATH)
                    if self.round == 4:
                        return response_tool("run_command", argv=[sys.executable, "artisan", "test"])
                    return {"content": json.dumps({"type": "final", "content": "Tests passed"})}

            with patch("benchmarks.evaluate.ChatModel", side_effect=[read, EditModel()]):
                with contextlib.redirect_stdout(io.StringIO()):
                    result = laravel(home, output, ["fake"], sys.executable,
                                    tool_protocol="strict-json", strict_json_profile="constrained",
                                    scenario="repair")[0]
            self.assertEqual(result["validation_test_exit"], 0)
            self.assertEqual(result["write"]["missing_required_files"], [])
            self.assertTrue(result["write"]["required_sequence_ok"])
            self.assertFalse(result["write"]["required_reads_before_edit"])
            self.assertFalse(result["passed"])
