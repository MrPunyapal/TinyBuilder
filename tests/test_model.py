import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from tinybuilder.model import ChatModel, ModelError


class Handler(BaseHTTPRequestHandler):
    mode = "ok"
    seen = []

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(length))
        Handler.seen.append(body)
        assert self.path == "/v1/chat/completions"
        assert body["model"] == "fake-model"
        if self.mode == "bad_http":
            data = b'private-secret-content-should-not-be-shown'
            status = 400
        elif self.mode == "bad_calls":
            data = json.dumps({"choices": [{"message": {"role": "assistant", "content": None,
                                                         "tool_calls": "not-an-array"}}]}).encode()
            status = 200
        elif self.mode == "bad_json":
            data, status = b'not json', 200
        else:
            data = json.dumps({"choices": [{"message": {"role": "assistant", "content": "ready"}}]}).encode()
            status = 200
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


class TestModel(unittest.TestCase):
    def setUp(self):
        Handler.seen = []
        Handler.mode = "ok"
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.worker = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.worker.start()
        self.model = ChatModel(f"http://127.0.0.1:{self.server.server_port}/v1", "fake-model")

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.worker.join(timeout=2)

    def test_openai_compatible_protocol(self):
        result = self.model.complete([{"role": "user", "content": "hi"}],
                                     [{"type": "function", "function": {"name": "test"}}])
        self.assertEqual(result["content"], "ready")
        self.assertIn("tools", Handler.seen[-1])
        self.assertEqual(Handler.seen[-1]["tool_choice"], "auto")

    def test_opt_in_protocol_sends_no_native_tool_definitions(self):
        self.model.complete([{"role": "user", "content": "hi"}], [])
        self.assertNotIn("tools", Handler.seen[-1])
        self.assertNotIn("tool_choice", Handler.seen[-1])

    def test_malformed_http_response_is_rejected(self):
        Handler.mode = "bad_calls"
        with self.assertRaises(ModelError) as err:
            self.model.complete([], [])
        self.assertEqual(err.exception.kind, "response_protocol")
        Handler.mode = "bad_json"
        with self.assertRaises(ModelError) as err:
            self.model.complete([], [])
        self.assertEqual(err.exception.kind, "response_protocol")

    def test_http_error_does_not_disclose_server_body(self):
        Handler.mode = "bad_http"
        with self.assertRaises(ModelError) as err:
            self.model.complete([], [])
        self.assertEqual(err.exception.kind, "http")
        self.assertNotIn("private-secret", str(err.exception))
