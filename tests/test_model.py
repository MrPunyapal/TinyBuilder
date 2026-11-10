import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from tinybuilder.model import ChatModel


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(length))
        assert self.path == "/v1/chat/completions"
        assert body["model"] == "fake-model"
        assert "tools" in body
        data = json.dumps({"choices": [{"message": {"role": "assistant", "content": "ready"}}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


class TestModel(unittest.TestCase):
    def test_openai_compatible_protocol(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            model = ChatModel(f"http://127.0.0.1:{server.server_port}/v1", "fake-model")
            result = model.complete([{"role": "user", "content": "hi"}], [{"type": "function", "function": {"name": "test"}}])
            self.assertEqual(result["content"], "ready")
        finally:
            server.shutdown()
            server.server_close()
            worker.join(timeout=2)
