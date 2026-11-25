"""Validate a flat, trusted installed runtime payload before spawning it."""
import hashlib
import json
import platform
import re
from pathlib import Path

from .catalog import BACKENDS, CPU_ARCHIVES, REVISION
from .errors import RuntimeFailure

MANIFEST_NAME = "runtime-manifest.json"
_NAME = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.+-]*")
_DIGEST = re.compile(r"[a-f0-9]{64}")


def platform_key():
    system = {"Windows": "windows", "Darwin": "macos", "Linux": "linux"}.get(
        platform.system(), "unsupported")
    machine = platform.machine().lower()
    arch = {"amd64": "x64", "x86_64": "x64", "aarch64": "arm64",
            "arm64": "arm64"}.get(machine, "unsupported")
    return system, arch


def absolute_directory(path):
    try:
        p = Path(path)
        if not p.is_absolute():
            raise ValueError
        p = p.resolve(strict=True)
        if not p.is_dir():
            raise ValueError
        return p
    except (OSError, ValueError, TypeError, RuntimeError):
        raise RuntimeFailure("runtime_missing") from None


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate field")
        result[key] = value
    return result


def _sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_runtime(root: Path, backend: str) -> Path:
    """Return verified absolute executable; never consult PATH or project."""
    target = platform_key()
    if target not in CPU_ARCHIVES:
        raise RuntimeFailure("unsupported_platform")
    # Accelerator payloads need separate reviewed catalog entries and device
    # qualification. Do not pretend that a CPU archive supports acceleration.
    if backend not in BACKENDS or backend != "cpu":
        raise RuntimeFailure("unsupported_backend", cpu_recovery=True)
    root = absolute_directory(root)
    manifest = root / MANIFEST_NAME
    try:
        if manifest.is_symlink() or not manifest.is_file():
            raise RuntimeFailure("runtime_missing")
        if manifest.stat().st_size > 1024 * 1024:
            raise ValueError
        data = json.loads(manifest.read_text(encoding="utf-8"),
                          object_pairs_hook=_unique)
        archive, digest = CPU_ARCHIVES[target]
        exe = "llama-server.exe" if target[0] == "windows" else "llama-server"
        required = {
            "schema": 1, "revision": REVISION, "os": target[0],
            "architecture": target[1], "backend": "cpu", "executable": exe,
            "archive": archive, "archive_sha256": digest,
        }
        if not isinstance(data, dict) or any(data.get(k) != v for k, v in required.items()):
            raise ValueError
        if type(data["schema"]) is not int:
            raise ValueError
        inventory = data["files"]
        deps = data["native_dependencies"]
        if (not isinstance(inventory, dict) or not isinstance(deps, list)
                or not all(isinstance(v, str) for v in deps)
                or len(set(deps)) != len(deps)
                or not {exe, "LICENSE", *deps} <= inventory.keys()
                or exe in deps or "LICENSE" in deps):
            raise ValueError
        for name, value in inventory.items():
            if (not _NAME.fullmatch(name) or name == MANIFEST_NAME
                    or name.endswith(".") or name.lower().endswith(
                        (".gguf", ".sqlite", ".sqlite3", ".db", ".env", ".pem", ".p12"))
                    or not isinstance(value, str) or not _DIGEST.fullmatch(value)):
                raise ValueError
        if len({name.casefold() for name in inventory}) != len(inventory):
            raise ValueError
        entries = list(root.iterdir())
        if any(p.is_symlink() or not p.is_file() for p in entries):
            raise ValueError
        if {p.name for p in entries} != set(inventory) | {MANIFEST_NAME}:
            raise ValueError
        for name, value in inventory.items():
            if _sha256(root / name) != value:
                raise RuntimeFailure("integrity_failure")
        return root / exe
    except RuntimeFailure:
        raise
    except (OSError, UnicodeError, ValueError, KeyError, TypeError, RuntimeError):
        raise RuntimeFailure("manifest_invalid") from None
