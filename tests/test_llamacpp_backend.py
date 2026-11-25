import json
import os
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

from tinybuilder.model import ChatModel, ManagedConnection, ModelError
from tinybuilder.protocol import strict_response_format


class BackendTests(unittest.TestCase):
    def setUp(self):
        self.seen = []
        self.status = 200
        self.reply = {"choices": [{"finish_reason": "stop", "message": {"content": "ok"}}]}
        owner = self
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                owner.seen.append((self.path, self.headers.get("Authorization"),
                                   json.loads(self.rfile.read(int(self.headers["Content-Length"])))))
                data = json.dumps(owner.reply).encode()
                self.send_response(owner.status)
                self.send_header("Location", "http://127.0.0.1:1/other")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            def log_message(self, *args):
                pass
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.connection = ManagedConnection("http://127.0.0.1:" + str(self.server.server_port),
                                            "alias", "session-secret")
        self.model = ChatModel.from_managed(self.connection)

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
        self.assertEqual(body["response_format"], {"type": "json_schema",
                                                   "schema": schema["json_schema"]["schema"]})
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
