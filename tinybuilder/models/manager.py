"""Managed downloads. Call blocking operations on a UI worker, not the UI thread."""
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
import ctypes
import errno
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import shutil
import stat
import sys
import threading
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .catalog import CATALOG, CatalogEntry
from .paths import native_model_dir

_CHUNK = 256 * 1024


class ModelError(RuntimeError):
    """An operation failed without producing a verified model."""


class DownloadCancelled(ModelError):
    pass


class _Interrupted(ModelError):
    pass


class _InvalidResponse(ModelError):
    pass


class ModelStatus(str, Enum):
    MISSING = "missing"
    PARTIAL = "partial"
    VERIFIED = "verified"
    INVALID = "invalid"


@dataclass(frozen=True)
class ModelSelection:
    path: Path
    catalog_id: str | None
    managed: bool
    # A matching digest establishes catalog identity, not runtime compatibility.
    provenance: str


@dataclass(frozen=True)
class ModelOffer:
    """Display-only description; download() does not accept this type."""
    entry: CatalogEntry
    destination: Path


@dataclass(frozen=True)
class DownloadRequest:
    entry: CatalogEntry
    destination: Path


@dataclass(frozen=True)
class DownloadProgress:
    received_bytes: int
    total_bytes: int
    phase: str


@dataclass(frozen=True)
class SpaceCheck:
    required_bytes: int
    free_bytes: int

    @property
    def sufficient(self):
        return self.free_bytes >= self.required_bytes


class CancellationToken:
    def __init__(self):
        self._event = threading.Event()

    def cancel(self):
        self._event.set()

    def check(self):
        if self._event.is_set():
            raise DownloadCancelled("Model download cancelled")


def _info(path, *, directory=False, missing=False, links=1):
    try:
        info = path.lstat()
    except FileNotFoundError:
        if missing:
            return None
        raise
    if (stat.S_ISLNK(info.st_mode) or
            getattr(info, "st_file_attributes", 0) & 0x400 or
            not (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)) or
            (not directory and info.st_nlink != links)):
        raise ModelError("Unsafe managed filesystem path")
    return info


def _open(path, flags, mode, *, links=1):
    """Check the opened object as well as the path; never truncate on open."""
    _info(path, missing=True, links=links)
    fd = os.open(path, flags | getattr(os, "O_NOFOLLOW", 0) |
                 getattr(os, "O_BINARY", 0), 0o600)
    try:
        info = _info(path, links=links)
        opened = os.fstat(fd)
        if not os.path.samestat(info, opened) or opened.st_nlink != links:
            raise ModelError("Managed path changed during open")
        return os.fdopen(fd, mode)
    except BaseException:
        os.close(fd)
        raise


def _read(path, limit):
    with _open(path, os.O_RDONLY, "rb") as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise ModelError("Unexpected managed metadata length")
    return data


def _new(path, data):
    with _open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def _unlink(path):
    if _info(path, missing=True) is not None:
        path.unlink()


@contextmanager
def _lock(path):
    # Never unlink a lock file: another process may already have it open.
    with _open(path, os.O_RDWR | os.O_CREAT, "r+b") as stream:
        try:
            if os.name == "nt":
                import msvcrt
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise ModelError("Model operation already active or locking unavailable") from None
        # Closing releases the OS lock, including after process termination.
        yield


def _publish(part, final):
    """Atomic exclusive publication, including volumes without hard links."""
    _info(part)
    if os.name == "nt":
        os.rename(part, final)  # Windows rename never replaces an existing file.
        return
    # Linux renameat2(RENAME_NOREPLACE) and Darwin renamex_np(RENAME_EXCL)
    # are exclusive, unlike POSIX rename. Use hard links only as a fallback
    # where exclusive rename is unsupported by libc/kernel/filesystem.
    libc = ctypes.CDLL(None, use_errno=True)
    source, target = os.fsencode(part), os.fsencode(final)
    function = None
    if sys.platform.startswith("linux"):
        function = getattr(libc, "renameat2", None)
        args = (-100, source, -100, target, 1)  # AT_FDCWD, RENAME_NOREPLACE
        types = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    elif sys.platform == "darwin":
        function = getattr(libc, "renamex_np", None)
        args = (source, target, 4)  # RENAME_EXCL (Darwin sys/stdio.h)
        types = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint]
    if function is not None:
        function.argtypes = types
        function.restype = ctypes.c_int
        if function(*args) == 0:
            return
        code = ctypes.get_errno()
        if code not in {errno.ENOSYS, errno.ENOTSUP, errno.EINVAL}:
            raise OSError(code, os.strerror(code), str(final))
    os.link(part, final)
    part.unlink()


def _strong_etag(value):
    return value if value and re.fullmatch(r'"[!#-~]+"', value) else None


def _allowed_url(url, loopback):
    parsed = urlsplit(url)
    return (parsed.username is None and parsed.password is None and not parsed.fragment and
            bool(parsed.hostname) and (parsed.scheme == "https" or
            (loopback and parsed.scheme == "http" and
             parsed.hostname in {"127.0.0.1", "::1", "localhost"})))


class _Redirects(HTTPRedirectHandler):
    def __init__(self, loopback):
        self.loopback = loopback

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if (not _allowed_url(newurl, self.loopback) or
                (urlsplit(req.full_url).scheme == "https" and urlsplit(newurl).scheme != "https")):
            raise ModelError("Unsafe model download redirect")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _matches(path, entry, token=None, *, external=False, links=1):
    info = path.stat() if external else _info(path, links=links)
    if info.st_size != entry.size_bytes:
        return False
    digest = hashlib.sha256()
    with (path.open("rb") if external else _open(path, os.O_RDONLY, "rb", links=links)) as stream:
        if stream.read(4) != b"GGUF":
            return False
        stream.seek(0)
        total = 0
        while True:
            if token is not None:
                token.check()
            block = stream.read(_CHUNK)
            if not block:
                break
            total += len(block)
            if total > entry.size_bytes:
                return False
            digest.update(block)
        if not os.path.samestat(info, os.fstat(stream.fileno())):
            return False
    return total == entry.size_bytes and digest.hexdigest() == entry.sha256


class ModelManager:
    def __init__(self, storage_dir=None, *, catalog=CATALOG, timeout=15,
                 allow_http_loopback=False):
        self.root = Path(storage_dir if storage_dir is not None else native_model_dir()).expanduser().resolve()
        # Pin the nearest existing directory identity. If an explicitly
        # selected mounted volume disappears, do not recreate its old path
        # on the underlying system volume.
        anchor = self.root
        while _info(anchor, directory=True, missing=True) is None:
            if anchor == anchor.parent:
                raise ModelError("Storage volume unavailable")
            anchor = anchor.parent
        self._anchor = anchor
        self._anchor_info = _info(anchor, directory=True)
        self.catalog = tuple(catalog)
        self._entries = {entry.model_id: entry for entry in self.catalog}
        if len(self._entries) != len(self.catalog):
            raise ValueError("Duplicate model IDs")
        if timeout <= 0:
            raise ValueError("Positive network timeout required")
        self._timeout = timeout
        self._loopback = allow_http_loopback
        self._opener = build_opener(_Redirects(allow_http_loopback))

    def _entry(self, model_id):
        try:
            return self._entries[model_id]
        except KeyError:
            raise ModelError("Unknown catalog model") from None

    def _check_root(self):
        if self.root.resolve() != self.root:
            raise ModelError("Storage root changed")
        info = _info(self._anchor, directory=True, missing=True)
        if info is None or not os.path.samestat(self._anchor_info, info):
            raise ModelError("Selected storage volume or directory changed")

    def _directory(self, entry, *, create=False):
        # A selected root is canonicalized once. Never follow links below it.
        self._check_root()
        if create:
            self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        if _info(self.root, directory=True, missing=True) is None:
            return None
        directory = self.root / ("tinybuilder-" + entry.sha256)
        if create:
            try:
                directory.mkdir(mode=0o700)
            except FileExistsError:
                pass
            else:
                _new(directory / "owner", entry.sha256.encode("ascii"))
        if _info(directory, directory=True, missing=True) is None:
            return None
        if _read(directory / "owner", 64) != entry.sha256.encode("ascii"):
            raise ModelError("Not a TinyBuilder managed model directory")
        return directory

    def destination(self, model_id):
        entry = self._entry(model_id)
        return self.root / ("tinybuilder-" + entry.sha256) / entry.filename

    def select_local(self, path):
        path = Path(path).expanduser().resolve(strict=True)
        if path.suffix.lower() != ".gguf" or not path.is_file():
            raise ModelError("Select a regular GGUF file")
        with path.open("rb") as stream:
            header = stream.read(8)
        if len(header) != 8 or header[:4] != b"GGUF":
            raise ModelError("Missing GGUF header")
        for entry in self.catalog:
            if _matches(path, entry, external=True):
                return ModelSelection(path, entry.model_id, False, "catalog-verified")
        return ModelSelection(path, None, False, "user-provided-unverified")

    def status(self, model_id):
        entry = self._entry(model_id)
        try:
            directory = self._directory(entry)
            if directory is None:
                return ModelStatus.MISSING
            final = directory / entry.filename
            if _info(final, missing=True) is not None:
                return ModelStatus.VERIFIED if _matches(final, entry) else ModelStatus.INVALID
            if _info(directory / "download.part", missing=True) is not None:
                return ModelStatus.PARTIAL
            return ModelStatus.MISSING
        except (OSError, ModelError):
            return ModelStatus.INVALID

    def verified_path(self, model_id):
        if self.status(model_id) != ModelStatus.VERIFIED:
            raise ModelError("No verified managed model")
        return self.destination(model_id)

    def check_space(self, model_id):
        entry = self._entry(model_id)
        self._check_root()
        ancestor = self.root
        while not ancestor.exists():
            if ancestor == ancestor.parent:
                raise ModelError("Storage volume unavailable")
            ancestor = ancestor.parent
        # Conservative full-size estimate; resumption checks remaining bytes again.
        return SpaceCheck(entry.size_bytes, shutil.disk_usage(ancestor).free)

    def download_offer(self, model_id):
        """Full immutable identity for display; no writes or network."""
        self._check_root()
        return ModelOffer(self._entry(model_id), self.destination(model_id))

    def request_download(self, model_id, *, consent=False, expected=None):
        if consent is not True:
            raise ModelError("Explicit model download consent required")
        request = self.download_offer(model_id)
        if expected is not None and expected != request:
            raise ModelError("Catalog or destination changed; obtain fresh consent")
        return DownloadRequest(request.entry, request.destination)

    def download(self, request, *, progress=None, cancellation=None, retries=2):
        if (not isinstance(request, DownloadRequest) or
                request.entry != self._entry(request.entry.model_id) or
                request.destination != self.destination(request.entry.model_id)):
            raise ModelError("Download request does not match catalog and destination")
        if type(retries) is not int or not 0 <= retries <= 5:
            raise ValueError("Retries must be between zero and five")
        entry = request.entry
        if not _allowed_url(entry.source_url, self._loopback):
            raise ModelError("HTTPS required for model downloads")
        token = cancellation if cancellation is not None else CancellationToken()
        notify = progress if progress is not None else lambda event: None
        token.check()
        directory = self._directory(entry, create=True)
        final = directory / entry.filename
        part = directory / "download.part"
        meta = directory / "download.json"
        with _lock(directory / "operation.lock"):
            self._check_root()
            if _info(final, missing=True) is not None:
                if not _matches(final, entry, token):
                    raise ModelError("Existing model is invalid; refusing overwrite")
                return ModelSelection(final, entry.model_id, True, "catalog-verified")
            for attempt in range(retries + 1):
                try:
                    self._transfer(entry, part, meta, token, notify)
                    break
                except _Interrupted:
                    if attempt == retries:
                        raise
                except _InvalidResponse:
                    _unlink(part)
                    _unlink(meta)
                    raise
            token.check()
            notify(DownloadProgress(entry.size_bytes, entry.size_bytes, "verifying"))
            if not _matches(part, entry, token):
                _unlink(part)
                _unlink(meta)
                raise ModelError("Model checksum or length mismatch")
            token.check()
            self._check_root()
            _publish(part, final)
            _unlink(meta)
            notify(DownloadProgress(entry.size_bytes, entry.size_bytes, "complete"))
            return ModelSelection(final, entry.model_id, True, "catalog-verified")

    def _transfer(self, entry, part, meta, token, notify):
        token.check()
        self._check_root()
        info = _info(part, missing=True)
        offset = info.st_size if info else 0
        identity = None
        if _info(meta, missing=True) is not None:
            try:
                identity = json.loads(_read(meta, 4096))
            except (ValueError, UnicodeError):
                identity = None
        if offset == entry.size_bytes:
            return  # Entire partial still requires full independent verification.
        if (not 0 < offset < entry.size_bytes or not isinstance(identity, dict) or
                identity.get("source") != entry.source_url or
                identity.get("sha256") != entry.sha256 or
                not isinstance(identity.get("etag"), str) or
                not _strong_etag(identity["etag"])):
            _unlink(part)
            _unlink(meta)
            offset = 0
            identity = None
        if shutil.disk_usage(part.parent).free < entry.size_bytes - offset:
            raise ModelError("Insufficient free disk space")
        headers = {"Accept-Encoding": "identity"}
        if offset:
            headers.update({"Range": "bytes=%d-" % offset, "If-Range": identity["etag"]})
        try:
            response = self._opener.open(Request(entry.source_url, headers=headers), timeout=self._timeout)
        except (URLError, TimeoutError, http.client.HTTPException):
            raise _Interrupted("Model connection failed") from None
        with response:
            token.check()
            self._check_root()
            if not _allowed_url(response.geturl(), self._loopback):
                raise ModelError("Unsafe model response URL")
            if response.headers.get("Content-Encoding", "identity").lower() != "identity":
                raise ModelError("Unexpected model content encoding")
            etag = _strong_etag(response.headers.get("ETag"))
            effective = hashlib.sha256(response.geturl().encode("utf-8")).hexdigest()
            length = response.headers.get("Content-Length")
            if response.status == 206:
                expected_range = "bytes %d-%d/%d" % (offset, entry.size_bytes - 1, entry.size_bytes)
                if (not offset or etag != identity["etag"] or effective != identity.get("effective") or
                        response.headers.get("Content-Range") != expected_range or
                        length != str(entry.size_bytes - offset)):
                    raise ModelError("Invalid range or changed resource identity; refusing append")
            elif response.status == 200:
                if response.headers.get("Content-Range") is not None or (
                        length is not None and length != str(entry.size_bytes)):
                    raise ModelError("Unexpected full model response length")
                _unlink(part)
                _unlink(meta)
                offset = 0
                if shutil.disk_usage(part.parent).free < entry.size_bytes:
                    raise ModelError("Insufficient free disk space for restart")
                _new(meta, json.dumps({"source": entry.source_url, "sha256": entry.sha256,
                                       "etag": etag, "effective": effective}).encode("utf-8"))
            else:
                raise ModelError("Unexpected model HTTP status")
            flags = os.O_WRONLY | (os.O_APPEND if offset else os.O_CREAT | os.O_EXCL)
            with _open(part, flags, "ab" if offset else "wb") as stream:
                if os.fstat(stream.fileno()).st_size != offset:
                    raise ModelError("Partial length changed")
                received = offset
                notify(DownloadProgress(received, entry.size_bytes, "downloading"))
                try:
                    while received < entry.size_bytes:
                        token.check()
                        try:
                            block = response.read1(min(_CHUNK, entry.size_bytes - received))
                        except (OSError, http.client.HTTPException):
                            raise _Interrupted("Model transfer interrupted") from None
                        if not block:
                            raise _Interrupted("Model transfer ended early")
                        stream.write(block)
                        received += len(block)
                        notify(DownloadProgress(received, entry.size_bytes, "downloading"))
                    token.check()
                    try:
                        if response.read(1):
                            raise _InvalidResponse("Model response exceeds declared length")
                    except (OSError, http.client.HTTPException):
                        raise _InvalidResponse("Model response did not finish") from None
                finally:
                    stream.flush()
                    os.fsync(stream.fileno())

    def recover_publication(self, model_id, *, consent=False):
        """Repair only a verified two-link fallback publication after a crash."""
        if consent is not True:
            raise ModelError("Explicit publication recovery consent required")
        entry = self._entry(model_id)
        directory = self._directory(entry)
        if directory is None:
            return False
        with _lock(directory / "operation.lock"):
            self._check_root()
            final, part = directory / entry.filename, directory / "download.part"
            meta = directory / "download.json"
            a = _info(final, missing=True, links=2)
            b = _info(part, missing=True, links=2)
            if a is None or b is None or not os.path.samestat(a, b):
                raise ModelError("No matching interrupted fallback publication")
            _info(meta, missing=True)
            if not _matches(final, entry, links=2):
                raise ModelError("Interrupted publication failed verification")
            self._check_root()
            if not (os.path.samestat(a, _info(final, links=2)) and
                    os.path.samestat(b, _info(part, links=2))):
                raise ModelError("Publication paths changed")
            part.unlink()
            _unlink(meta)
            return True

    def discard_partial(self, model_id, *, consent=False):
        """Explicitly reset an interrupted transfer without touching final files."""
        if consent is not True:
            raise ModelError("Explicit partial deletion consent required")
        entry = self._entry(model_id)
        directory = self._directory(entry)
        if directory is None:
            return False
        with _lock(directory / "operation.lock"):
            self._check_root()
            part, meta = directory / "download.part", directory / "download.json"
            part_info = _info(part, missing=True)
            meta_info = _info(meta, missing=True)
            _unlink(part)
            _unlink(meta)
            return part_info is not None or meta_info is not None

    def delete_managed(self, model_id, *, consent=False):
        if consent is not True:
            raise ModelError("Explicit model deletion consent required")
        entry = self._entry(model_id)
        directory = self._directory(entry)
        if directory is None:
            return False
        with _lock(directory / "operation.lock"):
            self._check_root()
            final = directory / entry.filename
            if _info(final, missing=True) is None:
                return False
            if not _matches(final, entry):
                raise ModelError("Refusing deletion of unverified file")
            final.unlink()
            return True
