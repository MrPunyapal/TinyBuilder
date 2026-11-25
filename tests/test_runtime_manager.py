import hashlib
import json
import os
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from tinybuilder.runtime import RuntimeFailure, RuntimeManager
from tinybuilder.runtime.catalog import CPU_ARCHIVES, REVISION
from tinybuilder.runtime.manifest import MANIFEST_NAME, platform_key, resolve_runtime
from tinybuilder.runtime.processes import child_environment


class FakeProcess:
    def __init__(self):
        self.exitcode = None

    def poll(self):
        return self.exitcode


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve() / "runtime"
        self.root.mkdir()
        self.model = self.root.parent / "model with spaces é.gguf"
        self.model.write_bytes(b"GGUF")
        self.target = platform_key()
        if self.target not in CPU_ARCHIVES:
            self.skipTest("preview target only")
        self.exe = self.root / ("llama-server.exe" if self.target[0] == "windows" else "llama-server")
        self.exe.write_bytes(b"test double")
        (self.root / "LICENSE").write_text("test only", encoding="utf-8")
        archive, digest = CPU_ARCHIVES[self.target]
        self.manifest = {
            "schema": 1, "revision": REVISION, "os": self.target[0],
            "architecture": self.target[1], "backend": "cpu", "executable": self.exe.name,
            "archive": archive, "archive_sha256": digest, "native_dependencies": [],
            "files": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in self.root.iterdir()},
        }
        self.write_manifest()
        self.manager = RuntimeManager(self.root)
        self.process = FakeProcess()
        self.credentials = {}
        self.mode = "ready"
        self.cleaned = 0
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                if self.path == "/health":
                    status, body = (503 if outer.mode == "loading" else 200), {}
                elif self.path == "/v1/models":
                    expected = "Bearer " + outer.credentials.get("key", "")
                    if outer.mode == "open":
                        status, body = 200, {}
                    elif self.headers.get("Authorization") != expected:
                        status, body = 401, {}
                    else:
                        alias = outer.credentials["alias"] if outer.mode != "wrong_alias" else "other"
                        status, body = 200, {"data": [{"id": alias}]}
                else:
                    status, body = 404, {}
                payload = json.dumps(body).encode()
                self.send_response(status)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.close_server)
        for name, replacement in (
            ("_available_port", lambda: self.server.server_port),
            ("spawn", self.fake_spawn), ("terminate_owned", self.fake_stop),
        ):
            p = patch("tinybuilder.runtime.manager." + name, side_effect=replacement)
            p.start()
            self.addCleanup(p.stop)
        self.addCleanup(self.manager.stop)

    def write_manifest(self):
        (self.root / MANIFEST_NAME).write_text(json.dumps(self.manifest), encoding="utf-8")

    def close_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(2)

    def fake_spawn(self, exe, model, port, alias, key):
        self.assertEqual(exe, self.exe)
        self.assertEqual(model, self.model)
        self.credentials.update(alias=alias, key=key)
        return self.process

    def fake_stop(self, process):
        self.assertIs(process, self.process)
        self.cleaned += 1
        process.exitcode = 0

    def test_authenticated_ready_and_cleanup(self):
        connection = self.manager.start(self.model)
        self.assertEqual(connection.base_url, f"http://127.0.0.1:{self.server.server_port}/v1")
        self.assertEqual(connection.model_alias, self.credentials["alias"])
        self.assertEqual(connection.api_key, self.credentials["key"])
        self.assertNotIn(connection.api_key, repr(connection))
        self.assertEqual(self.manager.status().state, "ready")
        self.manager.stop()
        self.manager.stop()
        self.assertEqual(self.cleaned, 1)
        self.assertEqual(self.manager.status().state, "stopped")

    def test_rejects_unauthenticated_server_and_wrong_alias(self):
        for mode in ("open", "wrong_alias"):
            self.mode = mode
            self.process = FakeProcess()
            with self.assertRaises(RuntimeFailure) as exc:
                self.manager.start(self.model)
            self.assertEqual(exc.exception.kind, "authentication")
        self.assertEqual(self.cleaned, 2)

    def test_timeout(self):
        self.mode = "loading"
        with self.assertRaises(RuntimeFailure) as exc:
            self.manager.start(self.model, timeout=0.2)
        self.assertEqual(exc.exception.kind, "startup_timeout")
        self.assertEqual(self.cleaned, 1)

    def test_cancellation(self):
        self.mode = "loading"
        errors = []

        def worker():
            try:
                self.manager.start(self.model, timeout=5)
            except RuntimeFailure as exc:
                errors.append(exc.kind)

        thread = threading.Thread(target=worker)
        thread.start()
        deadline = time.monotonic() + 2
        while self.manager.status().state != "loading" and time.monotonic() < deadline:
            time.sleep(0.01)
        self.manager.cancel()
        thread.join(2)
        self.assertFalse(thread.is_alive())
        self.assertEqual(errors, ["cancelled"])
        self.assertEqual(self.cleaned, 1)

    def test_crash(self):
        self.process.exitcode = 1
        with self.assertRaises(RuntimeFailure) as exc:
            self.manager.start(self.model)
        self.assertEqual(exc.exception.kind, "server_crash")
        self.assertEqual(self.cleaned, 1)

    def test_ready_child_crash(self):
        self.manager.start(self.model)
        self.process.exitcode = 1
        self.assertEqual(self.manager.status().failure, "server_crash")

    def test_bad_model_and_backend(self):
        with self.assertRaises(RuntimeFailure) as exc:
            self.manager.start(Path("model.gguf"))
        self.assertEqual(exc.exception.kind, "invalid_model")
        with self.assertRaises(RuntimeFailure) as exc:
            self.manager.start(self.model, backend="cuda")
        self.assertEqual(exc.exception.kind, "unsupported_backend")
        self.assertTrue(exc.exception.cpu_recovery)

    def test_runtime_inventory(self):
        self.assertEqual(resolve_runtime(self.root, "cpu"), self.exe)
        self.exe.write_bytes(b"tampered")
        with self.assertRaises(RuntimeFailure) as exc:
            resolve_runtime(self.root, "cpu")
        self.assertEqual(exc.exception.kind, "integrity_failure")

    def test_manifest_rejects_traversal_and_unlisted_file(self):
        self.manifest["files"]["../escape"] = "0" * 64
        self.write_manifest()
        with self.assertRaises(RuntimeFailure):
            resolve_runtime(self.root, "cpu")
        del self.manifest["files"]["../escape"]
        self.write_manifest()
        (self.root / "unexpected.dll").write_bytes(b"x")
        with self.assertRaises(RuntimeFailure):
            resolve_runtime(self.root, "cpu")

    def test_port_selection_failure(self):
        with patch("tinybuilder.runtime.manager._available_port",
                   side_effect=RuntimeFailure("port_conflict")):
            with self.assertRaises(RuntimeFailure) as exc:
                self.manager.start(self.model)
        self.assertEqual(exc.exception.kind, "port_conflict")
        self.assertEqual(self.cleaned, 0)

    def test_environment_isolation(self):
        with patch.dict(os.environ, {"LLAMA_ARG_HOST": "0.0.0.0", "LD_PRELOAD": "bad",
                                     "DYLD_INSERT_LIBRARIES": "bad", "HTTPS_PROXY": "bad"}):
            env = child_environment(self.exe, "session-key")
        self.assertEqual(env["LLAMA_API_KEY"], "session-key")
        self.assertTrue({"LLAMA_ARG_HOST", "LD_PRELOAD", "DYLD_INSERT_LIBRARIES",
                         "HTTPS_PROXY"}.isdisjoint(env))


if __name__ == "__main__":
    unittest.main()
