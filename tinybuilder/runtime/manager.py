"""Own one loopback llama-server session; no prompts or output are retained."""
import atexit
import http.client
import json
import math
import secrets
import socket
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

from .errors import RuntimeFailure
from .manifest import absolute_directory, resolve_runtime
from .processes import spawn, terminate_owned


@dataclass(frozen=True)
class RuntimeConnection:
    base_url: str
    model_alias: str
    api_key: str = field(repr=False)


@dataclass(frozen=True)
class RuntimeStatus:
    state: str
    failure: str | None = None


def _model_path(value):
    try:
        path = Path(value)
        if not path.is_absolute():
            raise ValueError
        path = path.resolve(strict=True)
        if not path.is_file() or path.suffix.lower() != ".gguf":
            raise ValueError
        with path.open("rb") as stream:
            if stream.read(4) != b"GGUF":
                raise ValueError
        return path
    except (OSError, ValueError, TypeError, RuntimeError):
        raise RuntimeFailure("invalid_model") from None


def _available_port():
    # No portable socket handoff to llama-server. Release the socket and
    # verify session identity after bind; never kill a competing listener.
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            return sock.getsockname()[1]
    except OSError:
        raise RuntimeFailure("port_conflict") from None


def _get(port, path, timeout, key=None):
    # http.client uses no environment proxy and never follows redirects.
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=timeout)
    try:
        headers = {} if key is None else {"Authorization": "Bearer " + key}
        conn.request("GET", path, headers=headers)
        with conn.getresponse() as response:
            # Only bounded metadata from /v1/models is parsed.
            if path == "/v1/models" and key is not None and response.status == 200:
                body = response.read(65537)
                if len(body) > 65536:
                    raise RuntimeFailure("authentication")
                try:
                    data = json.loads(body)
                except (ValueError, UnicodeError):
                    raise RuntimeFailure("authentication") from None
                return response.status, data
            return response.status, None
    finally:
        conn.close()


class RuntimeManager:
    """Call start on a worker; status and cancel are safe from the UI thread.

    stop waits for startup to observe cancellation and then owns cleanup.
    A manager may be reused only after cleanup succeeds. No auto-restart.
    """
    def __init__(self, runtime_root):
        self._root = absolute_directory(runtime_root)
        self._operation = threading.Lock()
        self._state_lock = threading.Lock()
        self._cancel = threading.Event()
        self._status = RuntimeStatus("stopped")
        self._process = None

    def _set(self, state, failure=None):
        with self._state_lock:
            self._status = RuntimeStatus(state, failure)

    def status(self):
        with self._state_lock:
            current, process = self._status, self._process
        if current.state == "ready" and process is not None and process.poll() is not None:
            return RuntimeStatus("failed", "server_crash")
        return current

    def cancel(self):
        with self._state_lock:
            if self._status.state in ("starting", "loading"):
                self._cancel.set()

    def _check_cancel(self):
        if self._cancel.is_set():
            raise RuntimeFailure("cancelled")

    def start(self, model_path, backend="cpu", timeout=180.0):
        if not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("timeout must be finite and positive")
        if not self._operation.acquire(blocking=False):
            raise RuntimeFailure("busy")
        try:
            if self._process is not None:
                raise RuntimeFailure("busy")
            with self._state_lock:
                self._cancel.clear()
                self._status = RuntimeStatus("starting")
            try:
                model = _model_path(model_path)
                executable = resolve_runtime(self._root, backend)
                self._check_cancel()
                port = _available_port()
                alias = "tinybuilder-" + secrets.token_hex(16)
                key = secrets.token_urlsafe(32)
                self._process = spawn(executable, model, port, alias, key)
                atexit.register(self._exit_cleanup)
                self._set("loading")
                self._wait_ready(port, alias, key, time.monotonic() + timeout)
                with self._state_lock:
                    self._check_cancel()
                    self._status = RuntimeStatus("ready")
                return RuntimeConnection(f"http://127.0.0.1:{port}/v1", alias, key)
            except BaseException as exc:
                failure = exc.kind if isinstance(exc, RuntimeFailure) else "startup_failure"
                try:
                    self._cleanup()
                except RuntimeFailure:
                    self._set("failed", "cleanup_failed")
                    raise RuntimeFailure("cleanup_failed") from None
                self._set("failed", failure)
                raise
        finally:
            self._operation.release()

    def _wait_ready(self, port, alias, key, deadline):
        saw_health = False
        while True:
            self._check_cancel()
            if self._process.poll() is not None:
                # Exit alone is not evidence of loader vs model failure.
                raise RuntimeFailure("server_crash")
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise RuntimeFailure("startup_timeout")

            def request(path, secret=None):
                self._check_cancel()
                left = deadline - time.monotonic()
                if left <= 0:
                    raise RuntimeFailure("startup_timeout")
                return _get(port, path, min(0.5, left), secret)

            try:
                status, _ = request("/health")
                if status in (200, 503):
                    saw_health = True
                elif status not in (401, 403):
                    raise RuntimeFailure("port_conflict")
                if status == 200:
                    denied, _ = request("/v1/models")
                    if denied not in (401, 403):
                        raise RuntimeFailure("authentication")
                    accepted, data = request("/v1/models", key)
                    if accepted != 200 or not isinstance(data, dict):
                        raise RuntimeFailure("authentication")
                    models = data.get("data")
                    if (not isinstance(models, list) or not any(
                            isinstance(m, dict) and m.get("id") == alias for m in models)):
                        raise RuntimeFailure("authentication")
                    if self._process.poll() is not None:
                        raise RuntimeFailure("server_crash")
                    if time.monotonic() >= deadline:
                        raise RuntimeFailure("startup_timeout")
                    return
            except (OSError, http.client.HTTPException):
                # A not-yet-listening child is normal. Do not expose raw errors.
                pass
            self._cancel.wait(min(0.05, max(0, deadline - time.monotonic())))

    def _cleanup(self):
        if self._process is not None:
            terminate_owned(self._process)
            self._process = None
            atexit.unregister(self._exit_cleanup)

    def _exit_cleanup(self):
        try:
            self.stop()
        except RuntimeFailure:
            # No private output from interpreter shutdown.
            pass

    def stop(self):
        self.cancel()
        with self._operation:
            self._set("stopping")
            try:
                self._cleanup()
            except RuntimeFailure:
                self._set("failed", "cleanup_failed")
                raise
            self._set("stopped")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.stop()
