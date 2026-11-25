import tempfile
import unittest
from pathlib import Path
from threading import Event
from unittest.mock import patch

from tinybuilder.application import Permissions
from tinybuilder.application.approvals import ApprovedTools


class ApprovalTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name).resolve()
        self.cancel = Event()
        self.requests = []
        self.file = self.root / "source.txt"
        self.file.write_bytes(b"old\n")

    def tools(self, permissions=Permissions(), approve=None):
        def accept(request):
            self.requests.append(request)
            return True
        return ApprovedTools(self.root, permissions, self.cancel,
                             approve if approve is not None else accept)

    def test_read_only_denies_before_prompt(self):
        tools = self.tools()
        self.assertEqual(tools.call("read_file", {"path": "source.txt"}), "old\n")
        self.assertTrue(tools.call("write_file", {"path": "source.txt", "content": "new"}).startswith("Permission denied"))
        self.assertTrue(tools.call("run_command", {"argv": ["echo", "hi"]}).startswith("Permission denied"))
        self.assertEqual(self.requests, [])
        self.assertEqual(self.file.read_bytes(), b"old\n")

    def test_approved_diff_and_denial(self):
        args = {"path": "source.txt", "content": "new\n"}
        denied = self.tools(Permissions(True), lambda request: 1)
        self.assertTrue(denied.call("write_file", args).startswith("Permission denied"))
        self.assertEqual(self.file.read_bytes(), b"old\n")
        tools = self.tools(Permissions(True))
        self.assertTrue(tools.call("write_file", args).startswith("Wrote"))
        self.assertEqual(self.file.read_text(), "new\n")
        self.assertIn("old", self.requests[0].diff)
        self.assertIn("new", self.requests[0].diff)

    def test_changed_file_and_cancel_rejected(self):
        def changed(request):
            self.file.write_bytes(b"external")
            return True
        tools = self.tools(Permissions(True), changed)
        args = {"path": "source.txt", "content": "new"}
        self.assertIn("file changed", tools.call("write_file", args))
        self.assertEqual(self.file.read_bytes(), b"external")
        def cancel(request):
            self.cancel.set()
            return True
        tools = self.tools(Permissions(True), cancel)
        self.assertTrue(tools.call("write_file", args).startswith("Permission denied"))
        self.assertEqual(self.file.read_bytes(), b"external")

    def test_exact_command_and_cancel(self):
        tools = self.tools(Permissions(False, (("echo", "hi"),)))
        with patch("tinybuilder.tools.subprocess.run") as run:
            run.return_value.returncode = 0
            run.return_value.stdout = "hi"
            run.return_value.stderr = ""
            self.assertTrue(tools.call("run_command", {"argv": ["echo", "other"]}).startswith("Permission denied"))
            run.assert_not_called()
            self.assertEqual(tools.call("run_command", {"argv": ["echo", "hi"]}), "Exit code: 0\nhi")
            self.assertEqual(run.call_args.args[0], ["echo", "hi"])
            self.assertFalse(run.call_args.kwargs["shell"])
            self.assertEqual(self.requests[0].argv, ("echo", "hi"))
            self.cancel.set()
            self.assertTrue(tools.call("run_command", {"argv": ["echo", "hi"]}).startswith("Permission denied"))
            self.assertEqual(run.call_count, 1)

    def test_large_diff_and_escape_denied(self):
        tools = self.tools(Permissions(True))
        self.assertTrue(tools.call("write_file", {"path": "source.txt", "content": "a" * 25_000}).startswith("Permission denied"))
        self.assertTrue(tools.call("write_file", {"path": "../escape.txt", "content": "new"}).startswith("Tool failed"))
        self.assertEqual(self.requests, [])
        self.assertEqual(self.file.read_bytes(), b"old\n")
