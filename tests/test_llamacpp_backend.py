import json
import os
import threading
import unittest
import tempfile
from pathlib import Path
from types import SimpleNamespace
from tinybuilder.agent import Agent
from tinybuilder.tools import LocalTools
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

from tinybuilder.model import ChatModel, ManagedConnection, ModelError
from tinybuilder.protocol import strict_response_format


class BackendTests(unittest.TestCase):
    def setUp(self):
        self.seen = []
        self.status = 200
        self.before_reply = None
        self.raw = None
        self.declared_length = None
        self.reply = {"choices": [{"finish_reason": "stop", "message": {"content": "ok"}}]}
        owner = self
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                owner.seen.append((self.path, self.headers.get("Authorization"),
                                   json.loads(self.rfile.read(int(self.headers["Content-Length"])))))
                if owner.before_reply:
                    owner.before_reply()
                data = owner.raw if owner.raw is not None else json.dumps(owner.reply).encode()
                self.send_response(owner.status)
                self.send_header("Location", "http://127.0.0.1:1/other")
                self.send_header("Content-Length", str(owner.declared_length if owner.declared_length is not None else len(data)))
                self.end_headers()
                try:
                    self.wfile.write(data)
                except (BrokenPipeError, ConnectionResetError):
                    pass
            def log_message(self, *args):
                pass
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.connection = ManagedConnection("http://127.0.0.1:" + str(self.server.server_port),
                                            "alias", "session-secret")
        self.model = ChatModel.from_managed(SimpleNamespace(**vars(self.connection)))

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def test_exact_schema_and_auth(self):
        schema = strict_response_format()
        with patch.dict(os.environ, {"http_proxy": "http://127.0.0.1:1", "no_proxy": ""}):
            self.assertEqual(self.model.complete([], [], schema)["content"], "ok")
        path, auth, body = self.seen[-1]
        self.assertEqual(path, "/v1/chat/completions")
        self.assertEqual(auth, "Bearer session-secret")
        self.assertEqual(body["model"], "alias")
        self.assertEqual(body["response_format"], schema)
        self.assertEqual(len(body["response_format"]["json_schema"]["schema"]["oneOf"]), 6)
        self.assertFalse(body["stream"])
        self.assertNotIn("tools", body)
        self.assertNotIn("session-secret", repr(self.connection))

    def test_native_and_truncation(self):
        calls = [{"id": "1", "type": "function", "function": {
            "name": "read_file", "arguments": '{"path":"README.md"}'}}]
        self.reply["choices"][0].update(finish_reason="tool_calls", message={"tool_calls": calls})
        self.assertEqual(self.model.complete([], [{"type": "function"}])["tool_calls"], calls)
        self.assertEqual(self.seen[-1][2]["tool_choice"], "auto")
        self.reply["choices"][0]["finish_reason"] = "length"
        with self.assertRaises(ModelError) as err:
            self.model.complete([], [])
        self.assertEqual(err.exception.kind, "generation_limit")

    def test_errors_no_redirect(self):
        for status, kind in [(401, "authentication"), (403, "authentication"), (307, "http"), (400, "http")]:
            self.status = status
            with self.assertRaises(ModelError) as err:
                self.model.complete([], [])
            self.assertEqual(err.exception.kind, kind)
            self.assertNotIn("session-secret", str(err.exception))
        self.assertEqual(len(self.seen), 4)

    def test_cancel_before_request(self):
        cancel = threading.Event()
        cancel.set()
        with self.assertRaises(ModelError) as err:
            self.model.complete([], [], cancel_event=cancel)
        self.assertEqual(err.exception.kind, "cancelled")
        self.assertFalse(self.seen)

    def test_managed_rejects_non_loopback(self):
        for url in ("http://example.com:80/v1", "http://localhost:80/v1",
                    "http://127.0.0.1:80/v1?x=1", "http://user@127.0.0.1:80/v1"):
            with self.assertRaises(ModelError):
                ChatModel.from_managed(ManagedConnection(url, "alias", "secret"))

    def test_cancelled_response_never_dispatches_native_tool(self):
        cancel = threading.Event()
        self.before_reply = cancel.set
        self.reply["choices"][0].update(finish_reason="tool_calls", message={"tool_calls": [
            {"id": "1", "function": {"name": "read_file", "arguments": '{"path":"fact.txt"}'}}]})
        model = self.model

        class TaskModel:
            def complete(self, messages, tools, response_format=None):
                return model.complete(messages, tools, response_format, cancel_event=cancel)

        events = []
        with tempfile.TemporaryDirectory() as directory:
            local = LocalTools(Path(directory))
            with patch.object(local, "call", wraps=local.call) as call:
                with self.assertRaises(ModelError) as err:
                    Agent(TaskModel(), local, on_event=events.append).run("Read fact.txt")
                self.assertEqual(err.exception.kind, "cancelled")
                call.assert_not_called()
        self.assertFalse(any(e["event"] == "tool_start" for e in events))

    def test_response_limit_and_incomplete_response(self):
        self.raw = b' ' * 4097
        with patch("tinybuilder.model.MAX_RESPONSE_BYTES", 4096):
            with self.assertRaisesRegex(ModelError, "byte limit"):
                self.model.complete([], [])
        self.raw = b'{"choices":[]}'
        self.declared_length = len(self.raw) + 1
        with self.assertRaisesRegex(ModelError, "Incomplete"):
            self.model.complete([], [])

    def test_invalid_credentials_and_urls(self):
        for key in ("", "secret\r\nInjected: yes", "has space", "é"):
            with self.assertRaises(ModelError):
                ChatModel.from_managed(ManagedConnection(self.connection.base_url, "alias", key))
        for url in ("http://127.0.0.1:0/v1", "http://127.0.0.1:99999/v1",
                    "http://127.0.0.1:80/v1//", "http://127.0.0.1:80/v1\n",
                    "https://127.0.0.1:80/v1"):
            with self.assertRaises(ModelError):
                ChatModel.from_managed(ManagedConnection(url, "alias", "secret"))

    def test_external_schema_and_native_compatibility(self):
        external = ChatModel(self.connection.base_url + "/v1", "alias")
        schema = strict_response_format()
        external.complete([], [], schema)
        self.assertEqual(self.seen[-1][2]["response_format"], schema)
        self.assertIsNone(self.seen[-1][1])
        external.complete([], [{"type": "function"}])
        self.assertEqual(self.seen[-1][2]["tool_choice"], "auto")

    def test_schema_rejection_is_not_malformed_action(self):
        self.status = 400
        self.reply = {"error": {"message": "session-secret"}}
        with self.assertRaisesRegex(ModelError, "constrained request rejected") as err:
            self.model.complete([], [], strict_response_format())
        self.assertEqual(err.exception.kind, "http")
        self.assertTrue(err.exception.__cause__.closed)
        self.assertNotIn("session-secret", str(err.exception.__cause__))

    def test_missing_finish_reason_fails_closed_for_managed(self):
        del self.reply["choices"][0]["finish_reason"]
        with self.assertRaisesRegex(ModelError, "finish reason"):
            self.model.complete([], [])
