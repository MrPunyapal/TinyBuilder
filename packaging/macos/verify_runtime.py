"""Verify a pre-staged runtime against an independently trusted SHA256SUMS.

The checksum file is a packaging input, not a replacement for the shared
runtime manifest. The caller must authenticate the checksum file itself.
"""
import hashlib
import re
import sys
from pathlib import Path

LINE = re.compile(r"([a-fA-F0-9]{64}) [ *](.+)")


def verify(root: Path) -> None:
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
    seen = set()
    for line in (root / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        match = LINE.fullmatch(line)
        if not match:
            raise ValueError("invalid checksum line")
        digest, name = match.groups()
        if name not in files or name in seen or name == "SHA256SUMS":
            raise ValueError("invalid or duplicate checksum path")
        if name.lower().endswith((".gguf", ".sqlite", ".sqlite3", ".db", ".env")) or Path(name).name.startswith(".env"):
            raise ValueError("private data or model in runtime")
        with (root / name).open("rb") as stream:
            actual = hashlib.file_digest(stream, "sha256").hexdigest()
        if actual != digest.lower():
            raise ValueError(f"checksum mismatch: {name}")
        seen.add(name)
    if seen != files - {"SHA256SUMS"}:
        raise ValueError("unlisted runtime files")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: verify_runtime.py DIRECTORY")
    verify(Path(sys.argv[1]))
