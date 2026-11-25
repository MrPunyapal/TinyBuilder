"""Frontend-neutral worker and approval mailbox, no terminal rendering."""
from dataclasses import dataclass
from threading import Condition, Event, Thread

from .approvals import Approval


@dataclass(frozen=True)
class PendingApproval:
    sequence: int
    request: Approval


@dataclass(frozen=True)
class Result:
    value: object = None
    error: str | None = None


class Worker:
    """One non-daemon worker, one consumable result, one approval at a time.

    UI polls busy(), pending(), and take_result(). While busy, disable other
    session changes. approve() is called by the worker, never the UI thread.
    Cancel signals the same Event passed to Session; it does not join or hide
    running work. On exit, cancel then poll until complete, stop the backend on
    the worker, and close the session. No answers or approvals are persisted.
    """

    def __init__(self, session):
        self.session = session
        self._condition = Condition()
        self._thread = None
        self._token = None
        self._cancellable = False
        self._result = None
        self._pending = None
        self._decision = None
        self._sequence = 0

    def busy(self):
        with self._condition:
            return self._thread is not None and self._thread.is_alive()

    def submit(self, operation, *, cancellable=True):
        with self._condition:
            if self.busy() or self._result is not None:
                raise RuntimeError("Finish the previous operation and consume its result")
            token = self._token = Event()
            self._cancellable = cancellable

            def run():
                try:
                    value = operation(token)
                    result = Result(value=value)
                except BaseException:
                    # Frontend receives no arbitrary exception details.
                    result = Result(error="Operation failed; inspect session status and retry")
                finally:
                    with self._condition:
                        self._pending = self._decision = None
                        self._result = result
                        self._condition.notify_all()

            self._thread = Thread(target=run, name="tinybuilder-application")
            self._thread.start()

    def cancel(self):
        with self._condition:
            if not self.busy() or not self._cancellable:
                return False
            self._token.set()
            self.session.cancel()
            self._condition.notify_all()
            return True

    def pending(self):
        with self._condition:
            return self._pending

    def approve(self, request):
        with self._condition:
            if not self.busy() or self._token.is_set() or self._pending is not None:
                return False
            self._sequence += 1
            self._pending = PendingApproval(self._sequence, request)
            self._decision = None
            self._condition.notify_all()
            try:
                while self._decision is None and not self._token.is_set():
                    self._condition.wait(0.05)
                return self._decision is True and not self._token.is_set()
            finally:
                self._pending = self._decision = None

    def respond(self, sequence, allow):
        if type(allow) is not bool:
            raise TypeError("Explicit boolean decision required")
        with self._condition:
            if (self._pending is None or sequence != self._pending.sequence
                    or self._decision is not None or self._token.is_set()):
                return False
            self._decision = allow
            self._condition.notify_all()
            return True

    def take_result(self):
        with self._condition:
            if self.busy():
                return None
            result, self._result = self._result, None
            return result

    def download(self, offer, transfer):
        self.submit(lambda token: self.session.download(offer, transfer, cancel_event=token))

    def start(self, factory):
        self.submit(lambda token: self.session.start(factory, cancel_event=token))

    def task(self, task):
        self.submit(lambda token: self.session.run_task(task, cancel_event=token))

    def stop(self):
        self.submit(lambda token: self.session.stop(), cancellable=False)
