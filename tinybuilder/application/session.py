"""In-memory setup state and cooperative operation ownership.

A UI runs blocking operations on a worker and polls snapshot(). Adapters must
observe cancellation, release resources, and return only after cleanup.
No backend is selected or downloaded by this module.
"""
from dataclasses import dataclass
from pathlib import Path
from threading import Event, RLock
from typing import Callable


class Cancelled(Exception):
    """An operation acknowledged cancellation."""


@dataclass(frozen=True)
class DownloadOffer:
    model_id: str
    size_bytes: int
    destination: Path
    license: str

    def __post_init__(self):
        if not self.model_id.strip() or type(self.size_bytes) is not int or self.size_bytes <= 0:
            raise ValueError("An exact model size and identity are required")
        if not self.license.strip() or not self.destination.is_absolute():
            raise ValueError("An absolute destination and license are required")


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

    def snapshot(self):
        with self._lock:
            return Snapshot(self._phase, self._project, self._model, self._offer,
                            self._permissions, self._protocol, self._progress, self._error)

    def _idle(self):
        if self._cancel is not None or self._phase in ("ready", "closed"):
            raise RuntimeError("Finish or close the active session first")

    def select_project(self, path):
        project = Path(path).expanduser().resolve(strict=True)
        if not project.is_dir():
            raise ValueError("Choose a project directory")
        with self._lock:
            self._idle()
            self._project = project
            self._model = self._offer = self._error = None
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
            self._offer = self._error = None
            self._phase = "backend_selection"

    def offer_download(self, offer: DownloadOffer):
        with self._lock:
            self._idle()
            if self._project is None:
                raise RuntimeError("Choose a project first")
            self._offer = offer
            self._model = self._error = None
            self._progress = 0
            self._phase = "consent"

    def set_permissions(self, permissions: Permissions):
        with self._lock:
            self._idle()
            if self._project is None:
                raise RuntimeError("Choose a project first")
            if not isinstance(permissions, Permissions):
                raise TypeError("Expected Permissions")
            self._permissions = permissions

    def set_constrained(self, enabled: bool):
        with self._lock:
            self._idle()
            if type(enabled) is not bool:
                raise TypeError("Explicit boolean required")
            self._protocol = "strict-json" if enabled else "native"

    def cancel(self):
        with self._lock:
            if self._cancel is None:
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
                    if type(count) is not int or not self._progress <= count <= consent.size_bytes:
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

    def close(self):
        with self._lock:
            if self._cancel is not None:
                raise RuntimeError("Cancel and join the worker before closing")
            self._project = self._model = self._offer = self._error = None
            self._permissions = Permissions()
            self._protocol = "native"
            self._progress = 0
            self._phase = "closed"
