import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
import socket
import tempfile
import threading
import unittest
from dataclasses import replace
from unittest.mock import patch

from tinybuilder.models import (
    CATALOG, CancellationToken, CatalogEntry, DownloadCancelled,
    ModelError, ModelManager, ModelStatus, native_model_dir,
)

DATA = b"GGUF\x03\x00\x00\x00" + bytes(range(256)) * 64
REVISION = "a" * 40


class ModelManagerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "model space \u00e9"
        self.mode = "ok"
        self.requests = []
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                range_header = self.headers.get("Range")
                owner.requests.append((range_header, self.headers.get("If-Range")))
                mode = owner.mode
                offset = int(range_header[6:-1]) if range_header else 0
                if mode == "restart":
                    offset = 0
                body = DATA[offset:]
                if mode == "corrupt":
                    body = body[:-1] + b"!"
                self.send_response(206 if offset else 200)
                self.send_header("ETag", '"changed"' if mode in {"changed", "restart"} else '"v1"')
                self.send_header("Content-Length", str(len(body)))
                if offset:
                    start = offset + 1 if mode == "bad-range" else offset
                    self.send_header("Content-Range", "bytes %d-%d/%d" %
                                     (start, len(DATA) - 1, len(DATA)))
                self.end_headers()
                if mode in {"interrupt", "interrupt-once"}:
                    if mode == "interrupt-once":
                        owner.mode = "ok"
                    self.wfile.write(body[:4096])
                    self.wfile.flush()
                    self.connection.shutdown(socket.SHUT_WR)
                    self.close_connection = True
                else:
                    try:
                        self.wfile.write(body)
                    except (BrokenPipeError, ConnectionResetError):
                        pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.entry = CatalogEntry(
            "fixture", REVISION, len(DATA), hashlib.sha256(DATA).hexdigest(),
            "MIT", "fixture.gguf",
            "http://127.0.0.1:%d/%s/fixture.gguf" % (self.server.server_port, REVISION),
        )
        self.manager = ModelManager(self.root, catalog=[self.entry], allow_http_loopback=True)
        self.request = self.manager.request_download("fixture", consent=True)
        self.final = self.request.destination
        self.part = self.final.parent / "download.part"

    def download(self, **kwargs):
        return self.manager.download(self.request, retries=0, **kwargs)

    def interrupt(self):
        self.mode = "interrupt"
        with self.assertRaises(ModelError):
            self.download()
        self.assertFalse(self.final.exists())
        self.assertEqual(self.part.stat().st_size, 4096)
        self.assertEqual(self.manager.status("fixture"), ModelStatus.PARTIAL)

    def test_consent_offline_and_atomic_completion(self):
        self.assertEqual(self.manager.status("fixture"), ModelStatus.MISSING)
        self.assertFalse(self.root.exists())
        with self.assertRaises(ModelError):
            self.manager.request_download("fixture")
        self.assertEqual(self.requests, [])
        events = []

        def progress(event):
            events.append(event)
            if event.phase != "complete":
                self.assertFalse(self.final.exists())

        selected = self.download(progress=progress)
        self.assertEqual(selected.path, self.final)
        self.assertEqual(selected.provenance, "catalog-verified")
        self.assertEqual(self.final.read_bytes(), DATA)
        self.assertFalse(self.part.exists())
        self.assertEqual(events[-1].phase, "complete")
        self.assertEqual(self.manager.verified_path("fixture"), self.final)
        self.download()
        self.assertEqual(len(self.requests), 1)
        with self.assertRaises(ModelError):
            self.manager.delete_managed("fixture")
        unrelated = self.final.parent / "notes.txt"
        unrelated.write_text("keep")
        self.assertTrue(self.manager.delete_managed("fixture", consent=True))
        self.assertEqual(unrelated.read_text(), "keep")
        self.assertFalse(self.manager.delete_managed("fixture", consent=True))

    def test_interrupted_resume(self):
        self.interrupt()
        self.mode = "ok"
        self.download()
        self.assertEqual(self.requests[-1], ("bytes=4096-", '"v1"'))
        self.assertEqual(self.final.read_bytes(), DATA)

    def test_invalid_range_and_identity_never_append(self):
        self.interrupt()
        before = self.part.read_bytes()
        for mode in ("bad-range", "changed"):
            self.mode = mode
            with self.assertRaisesRegex(ModelError, "Invalid range"):
                self.download()
            self.assertEqual(self.part.read_bytes(), before)
            self.assertFalse(self.final.exists())
        self.mode = "restart"
        self.download()
        self.assertEqual(self.final.read_bytes(), DATA)

    def test_retry_and_explicit_partial_reset(self):
        self.mode = "interrupt-once"
        self.manager.download(self.request, retries=1)
        self.assertEqual(self.requests, [(None, None), ("bytes=4096-", '"v1"')])
        self.manager.delete_managed("fixture", consent=True)
        self.interrupt()
        with self.assertRaises(ModelError):
            self.manager.discard_partial("fixture")
        self.assertTrue(self.manager.discard_partial("fixture", consent=True))
        self.assertEqual(self.manager.status("fixture"), ModelStatus.MISSING)
        self.mode = "ok"
        self.download()
        self.assertEqual(self.requests[-1], (None, None))

    def test_atomic_no_clobber_even_if_destination_appears(self):
        def progress(event):
            if event.phase == "verifying":
                self.final.write_bytes(b"unrelated")
        with self.assertRaises(FileExistsError):
            self.download(progress=progress)
        self.assertEqual(self.final.read_bytes(), b"unrelated")
        self.assertEqual(self.part.read_bytes(), DATA)

    def test_checksum_failure_and_retry(self):
        self.mode = "corrupt"
        with self.assertRaisesRegex(ModelError, "checksum"):
            self.download()
        self.assertFalse(self.part.exists())
        self.assertFalse(self.final.exists())
        self.mode = "ok"
        self.download()
        self.assertEqual(self.final.read_bytes(), DATA)

    def test_cancel_before_network_and_mid_transfer(self):
        token = CancellationToken()
        token.cancel()
        with self.assertRaises(DownloadCancelled):
            self.download(cancellation=token)
        self.assertEqual(self.requests, [])
        token = CancellationToken()

        def progress(event):
            if event.received_bytes:
                token.cancel()

        with self.assertRaises(DownloadCancelled):
            self.download(cancellation=token, progress=progress)
        self.assertFalse(self.final.exists())
        self.download()
        self.assertEqual(self.final.read_bytes(), DATA)

    def test_selected_volume_replacement_fails_closed(self):
        self.root.mkdir()
        manager = ModelManager(self.root, catalog=[self.entry], allow_http_loopback=True)
        request = manager.request_download("fixture", consent=True)
        self.root.rename(self.root.with_name("old-volume"))
        self.root.mkdir()
        with self.assertRaisesRegex(ModelError, "storage volume or directory changed"):
            manager.download(request, retries=0)
        self.assertEqual(manager.status("fixture"), ModelStatus.INVALID)
        self.assertEqual(self.requests, [])
        self.assertEqual(list(self.root.iterdir()), [])

    def test_insufficient_space(self):
        with patch("tinybuilder.models.manager.shutil.disk_usage",
                   return_value=SimpleNamespace(free=0)):
            self.assertFalse(self.manager.check_space("fixture").sufficient)
            with self.assertRaisesRegex(ModelError, "Insufficient"):
                self.download()
        self.assertEqual(self.requests, [])
        self.assertFalse(self.final.exists())

    def test_external_selection_and_switching(self):
        external = Path(self.temp.name) / "existing.gguf"
        external.write_bytes(DATA)
        selected = self.manager.select_local(external)
        self.assertEqual(selected.path, external.resolve())
        self.assertFalse(selected.managed)
        self.assertEqual(selected.catalog_id, "fixture")
        other = external.with_name("unknown.gguf")
        other.write_bytes(DATA + b"?")
        self.assertEqual(self.manager.select_local(other).provenance, "user-provided-unverified")
        self.assertFalse(self.root.exists())
        self.assertFalse(self.manager.delete_managed("fixture", consent=True))
        self.assertTrue(external.exists())
        self.assertEqual(self.requests, [])

    def test_invalid_catalog_and_request(self):
        for name in ("../evil.gguf", "CON.gguf", "a:b.gguf", "a\\b.gguf"):
            with self.assertRaises(ValueError):
                replace(self.entry, filename=name)
        with self.assertRaises(ValueError):
            replace(self.entry, revision="main")
        with self.assertRaises(ModelError):
            self.manager.download(replace(self.request, destination=self.root / "other.gguf"))
        self.assertEqual(self.requests, [])

    def test_unowned_directory_and_invalid_final_not_overwritten(self):
        self.final.parent.mkdir(parents=True)
        self.final.write_bytes(b"unrelated")
        with self.assertRaises((ModelError, OSError)):
            self.download()
        self.assertEqual(self.final.read_bytes(), b"unrelated")
        self.final.unlink()
        self.final.parent.rmdir()
        self.download()
        self.final.write_bytes(b"changed")
        self.assertEqual(self.manager.status("fixture"), ModelStatus.INVALID)
        with self.assertRaises(ModelError):
            self.download()
        with self.assertRaises(ModelError):
            self.manager.delete_managed("fixture", consent=True)
        self.assertEqual(self.final.read_bytes(), b"changed")

    def test_symlink_escape(self):
        self.interrupt()
        self.part.unlink()
        outside = Path(self.temp.name) / "outside"
        outside.write_bytes(b"keep")
        try:
            self.part.symlink_to(outside)
        except (OSError, NotImplementedError):
            self.skipTest("Symlink creation unavailable")
        with self.assertRaises(ModelError):
            self.download()
        self.assertEqual(outside.read_bytes(), b"keep")
        self.assertFalse(self.final.exists())

    def test_concurrent_download_and_delete(self):
        second = ModelManager(self.root, catalog=[self.entry], allow_http_loopback=True)
        checked = []

        def progress(event):
            if event.phase == "downloading" and not checked:
                with self.assertRaisesRegex(ModelError, "operation already active"):
                    second.download(self.request, retries=0)
                with self.assertRaisesRegex(ModelError, "operation already active"):
                    second.delete_managed("fixture", consent=True)
                checked.append(True)

        self.download(progress=progress)
        self.assertTrue(checked)
        self.assertEqual(len(self.requests), 1)


class NativePathsAndCatalogTests(unittest.TestCase):
    def test_native_paths(self):
        home = Path.home()
        custom = home / "alternate"
        for platform, env, expected in (
            ("win32", {"LOCALAPPDATA": str(custom)}, custom / "TinyBuilder" / "models"),
            ("win32", {}, home / "AppData" / "Local" / "TinyBuilder" / "models"),
            ("darwin", {}, home / "Library" / "Application Support" / "TinyBuilder" / "models"),
            ("linux", {"XDG_DATA_HOME": str(custom)}, custom / "tinybuilder" / "models"),
            ("linux", {"XDG_DATA_HOME": "relative"}, home / ".local" / "share" / "tinybuilder" / "models"),
        ):
            self.assertEqual(native_model_dir(platform=platform, environ=env, home=home), expected)

    def test_pinned_provisional_catalog(self):
        entry, = CATALOG
        self.assertEqual(entry.size_bytes, 1117320768)
        self.assertEqual(entry.license, "Apache-2.0")
        self.assertEqual(entry.qualification, "provisional")
        self.assertIn(entry.revision, entry.source_url)


if __name__ == "__main__":
    unittest.main()
