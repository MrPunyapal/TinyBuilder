import time
import unittest
from threading import Event

from tinybuilder.application import Session
from tinybuilder.application.approvals import Approval
from tinybuilder.application.worker import Worker


class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.worker = Worker(Session())

    def wait(self, condition):
        deadline = time.monotonic() + 5
        while not condition():
            if time.monotonic() >= deadline:
                self.worker.cancel()
                self.fail("worker did not reach expected state")
            time.sleep(0.005)

    def test_approval_response_and_stale_id(self):
        self.worker.submit(lambda token: self.worker.approve(Approval("run_command", argv=("echo", "hi"))))
        try:
            self.wait(lambda: self.worker.pending() is not None)
            pending = self.worker.pending()
            self.assertFalse(self.worker.respond(pending.sequence + 1, True))
            self.assertTrue(self.worker.respond(pending.sequence, True))
            self.assertFalse(self.worker.respond(pending.sequence, True))
        finally:
            if self.worker.pending() is not None:
                self.worker.cancel()
        self.wait(lambda: not self.worker.busy())
        self.assertTrue(self.worker.take_result().value)
        self.assertIsNone(self.worker.take_result())

    def test_cancellation_unblocks_approval(self):
        self.worker.submit(lambda token: self.worker.approve(Approval("write_file", path="file")))
        try:
            self.wait(lambda: self.worker.pending() is not None)
            pending = self.worker.pending()
            self.assertTrue(self.worker.cancel())
            self.assertFalse(self.worker.respond(pending.sequence, True))
        finally:
            self.worker.cancel()
        self.wait(lambda: not self.worker.busy())
        self.assertFalse(self.worker.take_result().value)

    def test_cancel_before_operation_enters_session(self):
        entered, release = Event(), Event()
        def operation(token):
            entered.set()
            if not release.wait(5):
                raise RuntimeError("timeout")
            return token.is_set()
        self.worker.submit(operation)
        try:
            self.assertTrue(entered.wait(5))
            self.assertTrue(self.worker.cancel())
        finally:
            release.set()
        self.wait(lambda: not self.worker.busy())
        self.assertTrue(self.worker.take_result().value)
