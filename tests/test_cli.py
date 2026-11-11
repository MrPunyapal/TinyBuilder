import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tinybuilder.cli import main


class TestCLI(unittest.TestCase):
    def test_constrained_profile_requires_strict_protocol_before_model_call(self):
        with tempfile.TemporaryDirectory() as d, patch("tinybuilder.cli.ChatModel") as model:
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(["chat", "inspect", "--project", d,
                                       "--strict-json-profile", "constrained"]), 2)
            model.assert_not_called()

    def test_checklist_flags_are_explicit_and_fail_before_model_start(self):
        with tempfile.TemporaryDirectory() as d, patch("tinybuilder.cli.ChatModel") as model:
            for extra in (["--progress-guidance", "checklist"],
                          ["--required-read", "composer.json"],
                          ["--tool-protocol", "strict-json", "--strict-json-profile", "constrained",
                           "--progress-guidance", "checklist"],
                          ["--tool-protocol", "strict-json", "--progress-guidance", "checklist"],
                          ["--tool-protocol", "native", "--strict-json-profile", "constrained",
                           "--progress-guidance", "checklist"]):
                with self.subTest(extra=extra), contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(main(["chat", "inspect", "--project", d, *extra]), 2)
            model.assert_not_called()

    def test_verbose_cli_emits_metadata_only(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "private.txt").write_text("private-token")
            replies = [
                {"tool_calls": [{"id": "private-id", "function": {
                    "name": "read_file", "arguments": '{"path":"private.txt"}'}}]},
                {"content": "Done"}]
            out, err = io.StringIO(), io.StringIO()
            with patch("tinybuilder.cli.ChatModel") as model, contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                model.return_value.complete.side_effect = replies
                code = main(["chat", "Inspect", "--project", d, "--verbose",
                             "--memory-db", str(root / "preferences.sqlite")])
            self.assertEqual(code, 0)
            events = [json.loads(line) for line in err.getvalue().splitlines()]
            self.assertTrue(any(e.get("tool") == "read_file" and e.get("status") == "ok" for e in events))
            self.assertNotIn("private", err.getvalue())
            self.assertEqual(out.getvalue().strip(), "Done")

    def test_invalid_exec_restrictions_fail_before_model_call(self):
        with tempfile.TemporaryDirectory() as d, patch("tinybuilder.cli.ChatModel") as model:
            for extra in (["--exec-command", '["php","artisan","test"]'],
                          ["--allow-exec", "--exec-command", '{}'],
                          ["--allow-exec", "--exec-command", 'invalid']):
                with contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(main(["chat", "test", "--project", d, *extra]), 2)
            model.assert_not_called()

    def test_strict_json_rejects_mcp_config_without_starting_server(self):
        with tempfile.TemporaryDirectory() as d, patch("tinybuilder.cli.MCPBridge") as bridge:
            with contextlib.redirect_stderr(io.StringIO()):
                code = main(["chat", "test", "--project", d, "--tool-protocol", "strict-json",
                             "--mcp-config", "some-mcp.json"])
            self.assertEqual(code, 2)
            bridge.assert_not_called()
