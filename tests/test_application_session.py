import tempfile
import unittest
from pathlib import Path
from threading import Event, Thread

from tinybuilder.application import Session, Permissions, DownloadOffer, Cancelled


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.session = Session()

    def offer(self):
        self.session.select_project(self.root)
        offer = DownloadOffer("test", 4, self.root / "model.gguf", "MIT")
        self.session.offer_download(offer)
        return offer

    def test_project_and_model(self):
        self.assertEqual(self.session.snapshot().phase, "welcome")
        self.session.select_project(self.root)
        model = self.root / "existing.gguf"
        model.write_bytes(b"GGUF")
        self.session.select_model(model)
        self.assertEqual(self.session.snapshot().model, model)
        self.assertEqual(self.session.snapshot().phase, "backend_selection")

    def test_permissions_reset(self):
        self.session.select_project(self.root)
        self.session.set_permissions(Permissions(True, (("php", "artisan", "test"),)))
        self.assertEqual(self.session.snapshot().permissions.tool_options()["exec_commands"],
                         [["php", "artisan", "test"]])
        self.session.set_constrained(True)
        self.session.select_project(self.root)
        self.assertEqual(self.session.snapshot().permissions, Permissions())
        self.assertEqual(self.session.snapshot().protocol, "native")
        with self.assertRaises(ValueError):
            Permissions(False, ((),))

    def test_consent_and_retry(self):
        offer = self.offer()
        calls = []
        def transfer(o, event, progress):
            calls.append(o)
            o.destination.write_bytes(b"GGUF")
            progress(4)
            return o.destination
        with self.assertRaises(RuntimeError):
            self.session.download(DownloadOffer("other", 4, offer.destination, "MIT"), transfer)
        self.assertEqual(calls, [])
        def fail(*args):
            raise OSError("private information")
        self.assertFalse(self.session.download(offer, fail))
        self.assertNotIn("private", self.session.snapshot().error)
        self.assertTrue(self.session.download(offer, transfer))
        self.assertEqual(self.session.snapshot().phase, "backend_selection")

    def test_cancellation_waits_for_worker(self):
        offer = self.offer()
        started, release = Event(), Event()
        results = []
        def transfer(o, event, progress):
            started.set()
            if not release.wait(5):
                raise RuntimeError("test timeout")
            if event.is_set():
                raise Cancelled()
            raise AssertionError("expected cancellation")
        worker = Thread(target=lambda: results.append(self.session.download(offer, transfer)))
        worker.start()
        try:
            self.assertTrue(started.wait(5))
            self.assertTrue(self.session.cancel())
            self.assertEqual(self.session.snapshot().phase, "cancelling")
            with self.assertRaises(RuntimeError):
                self.session.close()
        finally:
            release.set()
            worker.join(5)
        self.assertFalse(worker.is_alive())
        self.assertEqual(results, [False])
        self.assertEqual(self.session.snapshot().phase, "consent")
        self.session.close()
        self.assertEqual(self.session.snapshot().phase, "closed")
