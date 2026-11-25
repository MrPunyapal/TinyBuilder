import tempfile
import unittest
from pathlib import Path
from threading import Event

from tinybuilder.application import Permissions, Cancelled
from tinybuilder.application.agent_backend import AgentBackend


class FakeModel:
    def __init__(self, replies):
        self.replies = iter(replies)
        self.calls = []

    def complete(self, messages, tools, response_format=None, *, cancel_event):
        self.calls.append((list(messages), tools, response_format, cancel_event))
        return next(self.replies)


class AgentBackendTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.cancel = Event()
        self.activity = []
        self.closed = []
        self.approvals = []

    def backend(self, model):
        def approve(request):
            self.approvals.append(request)
            return True
        return AgentBackend(model, lambda: self.closed.append(True), approve)

    def test_native_read_only(self):
        (self.root / "example.txt").write_text("known", encoding="utf-8")
        model = FakeModel([
            {"content": None, "tool_calls": [{"id": "call_1", "type": "function",
             "function": {"name": "read_file", "arguments": '{"path":"example.txt"}'}}]},
            {"content": "answer"},
        ])
        backend = self.backend(model)
        answer = backend.run(self.root, "inspect", Permissions(), "native",
                             self.cancel, self.activity.append)
        self.assertEqual(answer, "answer")
        self.assertIn("known", [m["content"] for m in model.calls[1][0]])
        self.assertIn("read_file", self.activity)
        self.assertEqual(self.approvals, [])
        backend.close()
        self.assertEqual(self.closed, [True])

    def test_constrained_profile(self):
        model = FakeModel([{"content": '{"type":"final","content":"answer"}'}])
        answer = self.backend(model).run(self.root, "inspect", Permissions(),
                                         "strict-json", self.cancel, self.activity.append)
        self.assertEqual(answer, "answer")
        self.assertEqual(model.calls[0][1], [])
        self.assertEqual(model.calls[0][2]["type"], "json_schema")
        self.assertIs(model.calls[0][3], self.cancel)

    def test_cancellation_after_model_prevents_write(self):
        cancel = self.cancel
        class CancelModel:
            def complete(self, *args, **kwargs):
                cancel.set()
                return {"content": None, "tool_calls": [{"id": "call_1", "type": "function",
                    "function": {"name": "write_file", "arguments": '{"path":"new.txt","content":"x"}'}}]}
        with self.assertRaises(Cancelled):
            self.backend(CancelModel()).run(self.root, "write", Permissions(True),
                                            "native", self.cancel, self.activity.append)
        self.assertFalse((self.root / "new.txt").exists())
        self.assertEqual(self.approvals, [])
