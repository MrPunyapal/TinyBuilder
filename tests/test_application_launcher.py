import io
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
from contextlib import redirect_stdout

from tinybuilder.application.install import runtime_root
from tinybuilder.application.agent_backend import AgentBackend
from tinybuilder.tools import LocalTools
from tinybuilder.mcp import MCPServer
from tinybuilder.application.session import DownloadOffer
from tinybuilder.cli import main
from tinybuilder.external_env import external_env
from tinybuilder.ui.guided import Guided, plain, block


class LauncherTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        self.runtime = self.root / "runtime"
        self.runtime.mkdir()
        (self.runtime / "runtime-manifest.json").write_text("{}", encoding="utf-8")

    def test_installation_layouts_ignore_cwd(self):
        for platform, relative in (("linux", "app/tinybuilder"),
                                   ("darwin", "tinybuilder/tinybuilder"),
                                   ("win32", "TinyBuilder.exe")):
            executable = self.root / relative
            executable.parent.mkdir(exist_ok=True)
            executable.touch()
            with patch.object(sys, "frozen", True, create=True), patch.object(sys, "platform", platform), patch.object(sys, "executable", str(executable)):
                self.assertEqual(runtime_root(), self.runtime)
        self.assertEqual(runtime_root(self.runtime), self.runtime)
        with self.assertRaises(ValueError):
            runtime_root("runtime")

    def test_cli_entry_points(self):
        with patch("tinybuilder.ui.guided.launch", return_value=0) as launch:
            self.assertEqual(main(["app", "--runtime-root", str(self.runtime)]), 0)
            launch.assert_called_once_with(str(self.runtime))
        with patch.object(sys, "frozen", True, create=True), patch("tinybuilder.ui.guided.launch", return_value=0) as launch:
            self.assertEqual(main([]), 0)
            launch.assert_called_once_with(None)
        with redirect_stdout(io.StringIO()) as out:
            self.assertEqual(main(["app", "--runtime-root", "relative"]), 2)
        self.assertIn("trusted runtime missing", out.getvalue())

    def test_plain_text(self):
        output = []
        block("hello\x1b[2J\r\u202e\n/quit", output.append)
        self.assertEqual(output, ["| hello\\x1b[2J\\r\\u202e", "| /quit"])
        self.assertEqual(plain("café"), "café")
        self.assertNotIn("\x00", plain("a\x00b"))

    def test_guided_existing_model_and_quit(self):
        model = self.root / "model with spaces é.gguf"
        model.write_bytes(b"GGUF0000")
        output, calls = [], []
        class Backend:
            def run(self, project, task, permissions, protocol, cancel, activity):
                calls.append((project, permissions, protocol))
                return "answer\x1b[2J"
            def close(self):
                calls.append("closed")
        service = NS(inspect_model=lambda path: NS(path=model, provenance="user-provided-unverified"),
                     start=lambda *args: Backend())
        entries = iter([str(self.root), "", "1", str(model), "yes", "inspect", "/quit"])
        app = Guided(self.runtime, read=lambda prompt: next(entries), write=output.append,
                     service_factory=lambda *args: service)
        self.assertEqual(app.run(), 0)
        self.assertIn("Provenance: user-provided-unverified", output)
        self.assertIn("| answer\\x1b[2J", output)
        self.assertFalse(calls[0][1].allow_write)
        self.assertEqual(calls[0][2], "native")
        self.assertEqual(calls[-1], "closed")
        self.assertEqual(app.session.snapshot().phase, "closed")

    def test_catalog_decline_no_transfer(self):
        offer = DownloadOffer("test", 8, self.root / "test.gguf", "MIT", "a" * 64,
                              "https://example.invalid/model", "b" * 40, "test.gguf", "provisional")
        output = []
        entries = iter([str(self.root), "", "2", "1", "no", "q"])
        service = NS(offers=lambda: (offer,), transfer=lambda *args: self.fail("unexpected transfer"))
        app = Guided(self.runtime, read=lambda prompt: next(entries), write=output.append,
                     service_factory=lambda *args: service)
        self.assertEqual(app.run(), 0)
        for expected in ("Exact bytes: 8", "Revision: " + "b" * 40,
                         "Source: https://example.invalid/model", "Filename: test.gguf",
                         "License: MIT", "Qualification: provisional"):
            self.assertIn(expected, output)

    def test_frozen_linux_env_is_child_only(self):
        with patch.object(sys, "frozen", True, create=True), patch.object(sys, "platform", "linux"):
            with patch.dict(os.environ, {"LD_LIBRARY_PATH": "/bundle", "LD_LIBRARY_PATH_ORIG": "/user"}, clear=True):
                self.assertEqual(external_env()["env"]["LD_LIBRARY_PATH"], "/user")
                self.assertEqual(os.environ["LD_LIBRARY_PATH"], "/bundle")
            with patch.dict(os.environ, {"LD_LIBRARY_PATH": "/bundle"}, clear=True):
                self.assertNotIn("LD_LIBRARY_PATH", external_env()["env"])
                self.assertEqual(os.environ["LD_LIBRARY_PATH"], "/bundle")
        with patch.object(sys, "frozen", False, create=True):
            self.assertEqual(external_env(), {})

    def test_renderer_approval_denial_and_cancel(self):
        model = self.root / "test.gguf"
        model.write_bytes(b"GGUF0000")
        for decision in ("no", "interrupt"):
            with self.subTest(decision=decision):
                calls, output = [], []
                class Model:
                    def complete(self, messages, tools, response_format=None, *, cancel_event):
                        if any(message.get("role") == "tool" for message in messages):
                            return {"content": "done"}
                        return {"content": None, "tool_calls": [{"id": "call_1", "type": "function",
                            "function": {"name": "write_file", "arguments": '{"path":"new.txt","content":"test"}'}}]}
                def factory(root, approve, storage):
                    return NS(inspect_model=lambda path: NS(path=model, provenance="user-provided-unverified"),
                              start=lambda *args: AgentBackend(Model(), lambda: calls.append("closed"), approve))
                entries = iter([str(self.root), "", "1", str(model), "yes", "/settings", "yes",
                                "", "no", "write", decision, "/quit"])
                def read(prompt):
                    value = next(entries)
                    if value == "interrupt":
                        raise KeyboardInterrupt()
                    return value
                app = Guided(self.runtime, read=read, write=output.append, service_factory=factory)
                self.assertEqual(app.run(), 0)
                self.assertIn("Proposed action: write_file", output)
                self.assertIn("Path: new.txt", output)
                self.assertFalse((self.root / "new.txt").exists())
                self.assertEqual(calls, ["closed"])
                if decision == "interrupt":
                    self.assertTrue(any("Cancellation requested" in line for line in output))

    def test_frozen_linux_external_tool_call_sites(self):
        with patch.object(sys, "frozen", True, create=True), patch.object(sys, "platform", "linux"), \
                patch.dict(os.environ, {"LD_LIBRARY_PATH": "/bundle", "LD_LIBRARY_PATH_ORIG": "/user"}, clear=True):
            with patch("tinybuilder.tools.subprocess.run") as run:
                run.return_value = NS(returncode=0, stdout="ok", stderr="")
                self.assertIn("Exit code: 0", LocalTools(self.root, allow_exec=True,
                              exec_commands=[["echo", "ok"]]).call("run_command", {"argv": ["echo", "ok"]}))
                self.assertEqual(run.call_args.kwargs["env"]["LD_LIBRARY_PATH"], "/user")
            with patch("tinybuilder.mcp.subprocess.Popen") as popen, \
                    patch.object(MCPServer, "_reader"), patch.object(MCPServer, "_request"), patch.object(MCPServer, "_send"):
                MCPServer("fixture", "echo", [], self.root)
                self.assertEqual(popen.call_args.kwargs["env"]["LD_LIBRARY_PATH"], "/user")
            self.assertEqual(os.environ["LD_LIBRARY_PATH"], "/bundle")
