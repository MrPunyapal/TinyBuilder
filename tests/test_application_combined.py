"""Combined application contract test; real managers/client, synthetic bytes and HTTP."""
import hashlib
import importlib.util
import json
import os
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from tinybuilder.application import Session
from tinybuilder.application.managed import ManagedServices
from tinybuilder.model import ChatModel


class CombinedContractTests(unittest.TestCase):
    def test_actual_dependencies_with_loopback_fixture(self):
        available = (importlib.util.find_spec("tinybuilder.models") is not None
                     and importlib.util.find_spec("tinybuilder.runtime") is not None
                     and hasattr(ChatModel, "from_managed"))
        if not available:
            if os.environ.get("TINYBUILDER_REQUIRE_INTEGRATION") == "1":
                self.fail("Pinned integration dependencies missing")
            self.skipTest("Run combined application contract workflow")
        from tinybuilder.models.catalog import CatalogEntry
        from tinybuilder.models.manager import ModelManager
        from tinybuilder.runtime.manager import RuntimeManager
        from tinybuilder.runtime.catalog import CPU_ARCHIVES, REVISION
        from tinybuilder.runtime.manifest import MANIFEST_NAME, platform_key

        fixture = b"GGUF0000"  # Not a real inference model; no weights.
        revision = "a" * 40
        identity = {}
        posts = []
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def send_body(self, status, body):
                self.send_response(status)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("ETag", '"fixture"')
                self.end_headers()
                self.wfile.write(body)
            def do_GET(self):
                if self.path == "/" + revision + "/fixture.gguf":
                    self.send_body(200, fixture)
                elif self.path == "/health":
                    self.send_body(200, b"{}")
                elif self.path == "/v1/models":
                    self.send_body(200, json.dumps({"data": [{"id": identity["alias"]}]}).encode())
                elif self.path == "/props":
                    self.send_body(200 if self.headers.get("Authorization") == "Bearer " + identity["key"] else 401, b"{}")
                else:
                    self.send_body(404, b"{}")
            def do_POST(self):
                if self.path != "/v1/chat/completions" or self.headers.get("Authorization") != "Bearer " + identity["key"]:
                    self.send_body(401, b"{}")
                    return
                data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                posts.append(data)
                if data.get("response_format"):
                    answer = '{"type":"final","content":"strict answer"}'
                    message, finish = {"content": answer}, "stop"
                elif not any(m["role"] == "tool" for m in data["messages"]):
                    message = {"content": None, "tool_calls": [{"id": "call_1", "type": "function",
                               "function": {"name": "read_file", "arguments": '{"path":"source.txt"}'}}]}
                    finish = "tool_calls"
                else:
                    message, finish = {"content": "native answer"}, "stop"
                self.send_body(200, json.dumps({"choices": [{"message": message, "finish_reason": finish}]}).encode())
        class Process:
            def poll(self):
                return None
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        def close_server():
            server.shutdown()
            server.server_close()
            thread.join(3)
        self.addCleanup(close_server)
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name).resolve()
        runtime = root / "runtime"
        runtime.mkdir()
        target = platform_key()
        if target not in CPU_ARCHIVES:
            self.skipTest("Preview runtime target only")
        executable = runtime / ("llama-server.exe" if target[0] == "windows" else "llama-server")
        executable.write_bytes(b"synthetic executable")
        (runtime / "LICENSE").write_text("fixture", encoding="utf-8")
        archive, digest = CPU_ARCHIVES[target]
        manifest = {"schema": 1, "revision": REVISION, "os": target[0], "architecture": target[1],
                    "backend": "cpu", "executable": executable.name, "archive": archive,
                    "archive_sha256": digest, "native_dependencies": [],
                    "files": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in runtime.iterdir()}}
        (runtime / MANIFEST_NAME).write_text(json.dumps(manifest), encoding="utf-8")
        project = root / "project"
        project.mkdir()
        (project / "source.txt").write_text("known fact", encoding="utf-8")
        catalog = CatalogEntry("fixture", revision, len(fixture), hashlib.sha256(fixture).hexdigest(),
                               "MIT", "fixture.gguf", f"http://127.0.0.1:{server.server_port}/{revision}/fixture.gguf")
        manager = ModelManager(root / "models", catalog=(catalog,), allow_http_loopback=True)
        actual_runtime = RuntimeManager(runtime)
        session = Session()
        services = ManagedServices(manager, actual_runtime, ChatModel.from_managed, lambda a: False)
        def spawn(exe, path, port, alias, key):
            self.assertEqual(exe, executable)
            identity.update(alias=alias, key=key)
            return Process()
        with patch.dict(os.environ, {"NO_PROXY": "127.0.0.1", "no_proxy": "127.0.0.1"}), \
                patch("tinybuilder.runtime.manager._available_port", return_value=server.server_port), \
                patch("tinybuilder.runtime.manager.spawn", side_effect=spawn), \
                patch("tinybuilder.runtime.manager.terminate_owned") as terminate:
            try:
                session.select_project(project)
                offer = services.offers()[0]
                session.offer_download(offer)
                self.assertTrue(session.download(offer, services.transfer), session.snapshot().error)
                self.assertEqual(services.inspect_model(offer.destination).provenance, "catalog-verified")
                session.select_backend("cpu")
                self.assertTrue(session.start(services.start), session.snapshot().error)
                self.assertEqual(session.run_task("inspect"), "native answer")
                self.assertTrue(any(m.get("content") == "known fact" for m in posts[1]["messages"]))
                session.set_constrained(True)
                self.assertEqual(session.run_task("inspect"), "strict answer")
                self.assertIn("schema", posts[-1]["response_format"]["json_schema"])
                self.assertEqual(posts[-1]["model"], identity["alias"])
                self.assertTrue(session.stop())
                terminate.assert_called_once()
                session.close()
            finally:
                actual_runtime.stop()
