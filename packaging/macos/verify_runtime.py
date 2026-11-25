"""Verify a pre-staged runtime against an independently trusted SHA256SUMS.

The checksum file is a packaging input, not a replacement for the shared
runtime manifest. The caller must authenticate the checksum file itself.
"""
import hashlib
import re
import sys
import unicodedata
from pathlib import Path

LINE = re.compile(r"([a-fA-F0-9]{64}) [ *](.+)")


def verify(root: Path, inventory_sha256: str) -> None:
    if not re.fullmatch(r"[a-fA-F0-9]{64}", inventory_sha256):
        raise ValueError("invalid trusted inventory digest")
    root = root.resolve(strict=True)
    if not root.is_dir():
        raise ValueError("runtime must be a directory")
    entries = list(root.rglob("*"))
    if any(p.is_symlink() or not (p.is_file() or p.is_dir()) for p in entries):
        raise ValueError("runtime contains symlink or special file")
    files = {p.relative_to(root).as_posix() for p in entries if p.is_file()}
    if not {"SHA256SUMS", "llama-server"} <= files:
        raise ValueError("missing checksum inventory or llama-server")
    if not (root / "llama-server").stat().st_mode & 0o111:
        raise ValueError("llama-server is not executable")
    inventory = (root / "SHA256SUMS").read_bytes()
    if hashlib.sha256(inventory).hexdigest() != inventory_sha256.lower():
        raise ValueError("trusted inventory digest mismatch")
    normalized = set()
    for entry in entries:
        name = entry.relative_to(root).as_posix()
        key = unicodedata.normalize("NFD", name).casefold()
        if key in normalized:
            raise ValueError("case or Unicode path collision")
        normalized.add(key)
        if any(part.startswith(".") or part in {"__pycache__", "node_modules"}
               for part in entry.relative_to(root).parts):
            raise ValueError("hidden or unwanted runtime path")
        if entry.is_file() and entry.stat().st_nlink != 1:
            raise ValueError("hard-linked runtime file")
    seen = set()
    for line in inventory.decode("utf-8").splitlines():
        match = LINE.fullmatch(line)
        if not match:
            raise ValueError("invalid checksum line")
        digest, name = match.groups()
        if name not in files or name in seen or name == "SHA256SUMS":
            raise ValueError("invalid or duplicate checksum path")
        if name.lower().endswith((".gguf", ".safetensors", ".sqlite", ".sqlite3", ".db", ".env", ".pem", ".key", ".p12", ".pfx", ".pyc")) or Path(name).name.startswith(".env"):
            raise ValueError("private data or model in runtime")
        with (root / name).open("rb") as stream:
            if stream.read(4) == b"GGUF":
                raise ValueError("model weights in runtime")
            stream.seek(0)
            actual = hashlib.file_digest(stream, "sha256").hexdigest()
        if actual != digest.lower():
            raise ValueError(f"checksum mismatch: {name}")
        seen.add(name)
    if seen != files - {"SHA256SUMS"}:
        raise ValueError("unlisted runtime files")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: verify_runtime.py DIRECTORY TRUSTED_INVENTORY_SHA256")
    verify(Path(sys.argv[1]), sys.argv[2])
