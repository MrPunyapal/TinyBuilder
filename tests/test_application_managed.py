from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event
from types import SimpleNamespace as NS
import unittest

from tinybuilder.application import Session
from tinybuilder.application.managed import ManagedServices


class Models:
    def __init__(self, root):
        self.root = root
        self.catalog = (NS(model_id="test", size_bytes=8, license="MIT", sha256="a" * 64),)
        self.calls = []

    def destination(self, model_id):
        return self.root / "model.gguf"

    def request_download(self, model_id, *, consent):
        self.calls.append(consent)
        return NS(entry=self.catalog[0], destination=self.destination(model_id))

    def download(self, request, *, progress, cancellation):
        cancellation.check()
        for count in (4, 0, 8):
            progress(NS(received_bytes=count, total_bytes=8))
        request.destination.write_bytes(b"GGUF0000")
        return NS(path=request.destination, provenance="catalog-verified", catalog_id="test")

    def select_local(self, path):
        return NS(path=path)


class Runtime:
    def __init__(self):
        self.stops = 0
        self.fail_stop = False
        self.fail_start = False

    def start(self, path, *, backend):
        if self.fail_start:
            raise OSError("startup")
        return NS(base_url="http://127.0.0.1:1/v1", model_alias="alias", api_key="secret")

    def cancel(self):
        pass

    def stop(self):
        self.stops += 1
        if self.fail_stop:
            raise OSError("cleanup")


class Model:
    def complete(self, messages, tools, response_format=None, *, cancel_event):
        return {"content": "answer"}


class ManagedTests(unittest.TestCase):
    def setUp(self):
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        self.models = Models(self.root)
        self.runtime = Runtime()
        self.service = ManagedServices(self.models, self.runtime, lambda c: Model(), lambda a: False)
        self.session = Session()
        self.session.select_project(self.root)

    def setup_model(self):
        offer = self.service.offers()[0]
        self.session.offer_download(offer)
        self.assertTrue(self.session.download(offer, self.service.transfer))
        self.assertEqual(self.models.calls, [True])
        self.session.select_backend("cpu")

    def test_download_start_task_and_stop(self):
        self.setup_model()
        self.assertTrue(self.session.start(self.service.start))
        self.assertEqual(self.session.run_task("inspect"), "answer")
        self.assertTrue(self.session.stop())
        self.assertEqual(self.runtime.stops, 1)

    def test_failed_start_retains_cleanup(self):
        self.setup_model()
        self.runtime.fail_start = self.runtime.fail_stop = True
        self.assertFalse(self.session.start(self.service.start))
        self.assertEqual(self.session.snapshot().phase, "cleanup_failed")
        with self.assertRaises(RuntimeError):
            self.session.close()
        self.runtime.fail_stop = False
        self.assertTrue(self.session.stop())
        self.session.close()

    def test_cancelled_transfer_does_not_request(self):
        cancel = Event()
        cancel.set()
        with self.assertRaises(Exception):
            self.service.transfer(self.service.offers()[0], cancel, lambda n: None)
        self.assertEqual(self.models.calls, [])
