"""In-memory setup state and cooperative operation ownership.

A UI runs blocking operations on a worker and polls snapshot(). Adapters must
observe cancellation, release resources, and return only after cleanup.
No backend is selected or downloaded by this module.
"""
from dataclasses import dataclass
import re
from pathlib import Path
from threading import Event, RLock
from typing import Callable, Protocol


class Cancelled(Exception):
    """An operation acknowledged cancellation."""


@dataclass(frozen=True)
class DownloadOffer:
    model_id: str
    size_bytes: int
    destination: Path
    license: str
    sha256: str

    def __post_init__(self):
        if not self.model_id.strip() or type(self.size_bytes) is not int or self.size_bytes <= 0:
            raise ValueError("An exact model size and identity are required")
        if not self.license.strip() or not self.destination.is_absolute():
            raise ValueError("An absolute destination and license are required")
        if not re.fullmatch(r"[0-9a-f]{64}", self.sha256):
            raise ValueError("A pinned SHA-256 digest is required")


@dataclass(frozen=True)
class Permissions:
    allow_write: bool = False
    exec_commands: tuple[tuple[str, ...], ...] = ()

    def __post_init__(self):
        if type(self.allow_write) is not bool or not isinstance(self.exec_commands, tuple):
            raise ValueError("Invalid permissions")
        for argv in self.exec_commands:
            if (not isinstance(argv, tuple) or not 1 <= len(argv) <= 25
                    or any(not isinstance(part, str) or not part or "\x00" in part for part in argv)):
                raise ValueError("Execution requires explicit exact argv")

    def tool_options(self):
        return dict(allow_write=self.allow_write, allow_exec=bool(self.exec_commands),
                    exec_commands=[list(argv) for argv in self.exec_commands])


@dataclass(frozen=True)
class Snapshot:
    phase: str
    project: Path | None
    model: Path | None
    offer: DownloadOffer | None
    permissions: Permissions
    protocol: str
    progress: int
    error: str | None
    backend: str | None
    activity: str | None


class RunningBackend(Protocol):
    def run(self, project: Path, task: str, permissions: Permissions,
            protocol: str, cancel: Event, activity: Callable[[str], None]) -> str:
        """Return only when inference and tools are no longer active."""
        ...

    def close(self) -> None:
        """Stop owned resources; safe to retry if cleanup fails."""
        ...


class CleanupRequired(Exception):
    """A failed factory retained an owned backend requiring shutdown."""

    def __init__(self, running: RunningBackend):
        super().__init__("Backend cleanup required")
        self.running = running


class Session:
    """Single operation at a time; never report cancellation before worker exit."""

    def __init__(self):
        self._lock = RLock()
        self._phase = "welcome"
        self._project = None
        self._model = None
        self._offer = None
        self._permissions = Permissions()
        self._protocol = "native"
        self._progress = 0
        self._error = None
        self._cancel = None
        self._backend = None
        self._running = None
        self._activity = None

    def snapshot(self):
        with self._lock:
            return Snapshot(self._phase, self._project, self._model, self._offer,
                            self._permissions, self._protocol, self._progress, self._error,
                            self._backend, self._activity)

    def _idle(self):
        if self._cancel is not None or self._running is not None or self._phase == "closed":
            raise RuntimeError("Finish or close the active session first")

    def select_project(self, path):
        project = Path(path).expanduser().resolve(strict=True)
        if not project.is_dir():
            raise ValueError("Choose a project directory")
        with self._lock:
            self._idle()
            self._project = project
            self._model = self._offer = self._error = self._backend = self._activity = None
            self._permissions = Permissions()
            self._protocol = "native"
            self._progress = 0
            self._phase = "model_selection"

    def select_model(self, path):
        # The model manager must perform actual GGUF validation before startup.
        model = Path(path).expanduser().resolve(strict=True)
        if not model.is_file() or model.suffix.lower() != ".gguf":
            raise ValueError("Choose an existing GGUF file")
        with self._lock:
            self._idle()
            if self._project is None:
                raise RuntimeError("Choose a project first")
            self._model = model
            self._backend = None
            self._progress = 0
            self._offer = self._error = None
            self._phase = "backend_selection"

    def offer_download(self, offer: DownloadOffer):
        with self._lock:
            self._idle()
            if self._project is None:
                raise RuntimeError("Choose a project first")
            if not isinstance(offer, DownloadOffer):
                raise TypeError("Expected DownloadOffer")
            self._backend = None
            self._offer = offer
            self._model = self._error = None
            self._progress = 0
            self._phase = "consent"

    def set_permissions(self, permissions: Permissions):
        with self._lock:
            if self._cancel is not None or self._phase in ("closed", "cleanup_failed"):
                raise RuntimeError("Settings unavailable during operation or cleanup")
            if self._project is None:
                raise RuntimeError("Choose a project first")
            if not isinstance(permissions, Permissions):
                raise TypeError("Expected Permissions")
            self._permissions = permissions

    def set_constrained(self, enabled: bool):
        with self._lock:
            if self._cancel is not None or self._phase in ("closed", "cleanup_failed"):
                raise RuntimeError("Settings unavailable during operation or cleanup")
            if type(enabled) is not bool:
                raise TypeError("Explicit boolean required")
            self._protocol = "strict-json" if enabled else "native"

    def cancel(self):
        with self._lock:
            if self._cancel is None or self._phase in ("stopping", "cleanup_failed"):
                return False
            self._cancel.set()
            self._phase = "cancelling"
            return True

    def download(self, consent: DownloadOffer,
                 transfer: Callable[[DownloadOffer, Event, Callable[[int], None]], Path]):
        """Run on a worker. Consent must match the currently displayed offer.

        The injected transfer owns verification, partial files and cancellation.
        This service never starts a transfer without matching explicit consent.
        """
        with self._lock:
            self._idle()
            if self._phase != "consent" or self._offer != consent or self._offer is None:
                raise RuntimeError("Confirm the current download offer")
            event = self._cancel = Event()
            self._phase = "downloading"
            self._progress = 0
            self._error = None

        def progress(count):
            with self._lock:
                if self._cancel is event and not event.is_set():
                    if type(count) is not int or not 0 <= count <= consent.size_bytes:
                        raise ValueError("Invalid download progress")
                    self._progress = count

        try:
            model = Path(transfer(consent, event, progress)).resolve(strict=True)
            if model != consent.destination.resolve() or not model.is_file():
                raise ValueError("Unexpected download destination")
            if model.stat().st_size != consent.size_bytes:
                raise ValueError("Unexpected download size")
            with self._lock:
                if event.is_set():
                    raise Cancelled()
                self._model = model
                self._offer = None
                self._progress = consent.size_bytes
                self._phase = "backend_selection"
                self._cancel = None
        except BaseException as exc:
            with self._lock:
                self._phase = "consent"
                self._error = "Download cancelled" if event.is_set() or isinstance(exc, Cancelled) else "Download failed; retry or select another model"
                self._cancel = None
            if not isinstance(exc, (Exception,)):
                raise
            return False
        return True

    def select_backend(self, backend: str):
        """Backend identifiers must come from runtime discovery in the frontend."""
        if not isinstance(backend, str) or not re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", backend):
            raise ValueError("Choose an available backend identifier")
        with self._lock:
            self._idle()
            if self._phase != "backend_selection":
                raise RuntimeError("Choose a verified model first")
            self._backend = backend

    def start(self, factory: Callable[[Path, str, Event], RunningBackend]) -> bool:
        """Worker operation. Factory verifies the model and starts the runtime.

        On failure before returning a handle, the factory owns cleanup.
        Once returned, the application owns the handle even on cancellation.
        """
        with self._lock:
            self._idle()
            if self._phase != "backend_selection" or self._model is None or self._backend is None:
                raise RuntimeError("Choose a model and backend first")
            event = self._cancel = Event()
            model, backend = self._model, self._backend
            self._phase, self._error = "starting", None
        try:
            running = factory(model, backend, event)
        except CleanupRequired as exc:
            with self._lock:
                self._running = exc.running
                self._phase, self._cancel = "cleanup_failed", None
                self._permissions = Permissions()
                self._error = "Backend cleanup failed; retry shutdown"
            return False
        except BaseException as exc:
            with self._lock:
                self._phase = "backend_selection"
                self._error = ("Startup cancelled" if event.is_set() or isinstance(exc, Cancelled)
                               else "Startup failed; check model and backend, then retry")
                self._cancel = None
            if not isinstance(exc, Exception):
                raise
            return False
        with self._lock:
            self._running = running
            if not event.is_set():
                self._phase, self._cancel = "ready", None
                return True
            self._phase = "stopping"
        self._stop_owned("Startup cancelled")
        return False

    def run_task(self, task: str) -> str | None:
        """Worker operation; answer returned to caller only, never persisted."""
        if not isinstance(task, str) or not task.strip():
            raise ValueError("Enter a non-empty task")
        with self._lock:
            if self._phase != "ready" or self._cancel is not None or self._running is None:
                raise RuntimeError("Start a model before running a task")
            event = self._cancel = Event()
            running, project = self._running, self._project
            permissions, protocol = self._permissions, self._protocol
            self._permissions = Permissions()
            self._phase, self._error, self._activity = "inference", None, None

        def activity(label):
            # No arguments, file contents, arbitrary model text or credentials.
            with self._lock:
                if self._cancel is event and not event.is_set():
                    self._activity = label if label in (
                        "model", "list_files", "read_file", "search_files",
                        "write_file", "run_command") else "tool"

        try:
            answer = running.run(project, task, permissions, protocol, event, activity)
            if not isinstance(answer, str):
                raise ValueError("Invalid task result")
            with self._lock:
                if event.is_set():
                    raise Cancelled()
                self._phase, self._cancel, self._activity = "ready", None, None
                return answer
        except BaseException as exc:
            with self._lock:
                self._phase, self._cancel, self._activity = "ready", None, None
                self._error = ("Task cancelled" if event.is_set() or isinstance(exc, Cancelled)
                               else "Task failed; retry or restart the model")
            if not isinstance(exc, Exception):
                raise
            return None

    def _stop_owned(self, message=None) -> bool:
        # Caller has reserved the operation and set phase to stopping.
        try:
            self._running.close()
        except BaseException as exc:
            with self._lock:
                self._phase, self._cancel = "cleanup_failed", None
                self._error = "Backend cleanup failed; retry shutdown"
            if not isinstance(exc, Exception):
                raise
            return False
        with self._lock:
            self._running = None
            self._phase, self._cancel = "backend_selection", None
            self._permissions = Permissions()
            self._activity, self._error = None, message
        return True

    def stop(self) -> bool:
        """Worker operation; retain ownership if cleanup fails."""
        with self._lock:
            if self._cancel is not None or self._phase not in ("ready", "cleanup_failed"):
                raise RuntimeError("Finish the active operation before stopping")
            self._phase, self._cancel = "stopping", Event()
            self._permissions = Permissions()
        return self._stop_owned()

    def close(self):
        with self._lock:
            if self._cancel is not None or self._running is not None:
                raise RuntimeError("Cancel, join and stop the backend before closing")
            self._project = self._model = self._offer = self._error = self._backend = self._activity = None
            self._permissions = Permissions()
            self._protocol = "native"
            self._progress = 0
            self._phase = "closed"
