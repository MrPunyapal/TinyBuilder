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
        offer = DownloadOffer("test", 4, self.root / "model.gguf", "MIT", "a" * 64)
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
            self.session.download(DownloadOffer("other", 4, offer.destination, "MIT", "a" * 64), transfer)
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

    def setup_backend(self):
        self.session.select_project(self.root)
        model = self.root / "existing.gguf"
        model.write_bytes(b"GGUF")
        self.session.select_model(model)
        self.session.select_backend("cpu")

    def test_start_failure_and_retry(self):
        self.setup_backend()
        def fail(*args):
            raise OSError("secret endpoint")
        self.assertFalse(self.session.start(fail))
        self.assertEqual(self.session.snapshot().phase, "backend_selection")
        self.assertNotIn("secret", self.session.snapshot().error)
        handle = FakeBackend()
        self.assertTrue(self.session.start(lambda *args: handle))
        self.assertEqual(self.session.snapshot().phase, "ready")
        self.assertTrue(self.session.stop())
        self.assertEqual(handle.closed, 1)
        self.session.close()

    def test_task_permissions_one_shot_and_switch(self):
        self.setup_backend()
        handle = FakeBackend()
        self.session.start(lambda *args: handle)
        self.session.set_permissions(Permissions(True, (("php", "artisan", "test"),)))
        self.session.set_constrained(True)
        self.assertEqual(self.session.run_task("inspect"), "answer")
        self.assertEqual(handle.calls[0][1], Permissions(True, (("php", "artisan", "test"),)))
        self.assertEqual(handle.calls[0][2], "strict-json")
        self.assertEqual(self.session.run_task("inspect again"), "answer")
        self.assertEqual(handle.calls[1][1], Permissions())
        with self.assertRaises(RuntimeError):
            self.session.select_project(self.root)
        self.session.stop()
        self.session.select_project(self.root)
        self.assertEqual(self.session.snapshot().protocol, "native")
        self.assertIsNone(self.session.snapshot().backend)

    def test_cleanup_failure_retains_ownership(self):
        self.setup_backend()
        handle = FakeBackend()
        handle.fail_close = True
        self.session.start(lambda *args: handle)
        self.assertFalse(self.session.stop())
        self.assertEqual(self.session.snapshot().phase, "cleanup_failed")
        with self.assertRaises(RuntimeError):
            self.session.close()
        with self.assertRaises(RuntimeError):
            self.session.select_project(self.root)
        handle.fail_close = False
        self.assertTrue(self.session.stop())
        self.session.close()

    def test_cancelled_start_closes_late_handle(self):
        self.setup_backend()
        handle = FakeBackend()
        def start(model, backend, event):
            self.session.cancel()
            self.assertTrue(event.is_set())
            return handle
        self.assertFalse(self.session.start(start))
        self.assertEqual(handle.closed, 1)
        self.assertEqual(self.session.snapshot().phase, "backend_selection")

    def test_cancelled_task_discards_late_answer(self):
        self.setup_backend()
        session = self.session
        class Backend(FakeBackend):
            def run(self, project, task, permissions, protocol, cancel, activity):
                activity("secret payload")
                if session.snapshot().activity != "tool":
                    raise AssertionError("unsanitized activity")
                session.cancel()
                if not cancel.is_set():
                    raise AssertionError("cancel not delivered")
                return "late answer"
        self.session.start(lambda *args: Backend())
        self.assertIsNone(self.session.run_task("inspect"))
        self.assertEqual(self.session.snapshot().error, "Task cancelled")
        self.assertEqual(self.session.snapshot().phase, "ready")
        self.session.stop()

    def test_digest_required_and_consent_bound(self):
        with self.assertRaises(ValueError):
            DownloadOffer("test", 4, self.root / "model.gguf", "MIT", "invalid")
        offer = self.offer()
        changed = DownloadOffer("test", 4, offer.destination, "MIT", "b" * 64)
        with self.assertRaises(RuntimeError):
            self.session.download(changed, lambda *args: self.fail("unexpected transfer"))


class FakeBackend:
    def __init__(self):
        self.closed = 0
        self.fail_close = False
        self.calls = []

    def run(self, project, task, permissions, protocol, cancel, activity):
        self.calls.append((project, permissions, protocol))
        activity("model")
        return "answer"

    def close(self):
        if self.fail_close:
            raise OSError("private path")
        self.closed += 1
