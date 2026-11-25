"""Validate a flat, externally pinned runtime payload before copying it."""
import hashlib
import re
import sys
from pathlib import Path


def verify(root: Path, checksums: Path) -> None:
    expected = {}
    for line in checksums.read_text(encoding="utf-8").splitlines():
        match = re.fullmatch(r"([0-9a-f]{64}) [ *]([A-Za-z0-9_.+-]+)", line)
        if not match:
            raise ValueError("invalid checksum line")
        digest, name = match.groups()
        if name in expected or name in (".", "..") or name.lower().endswith(".gguf"):
            raise ValueError("invalid runtime filename")
        expected[name] = digest
    entries = list(root.iterdir())
    if any(p.is_symlink() or not p.is_file() for p in entries):
        raise ValueError("runtime must contain only regular files")
    if set(expected) != {p.name for p in entries}:
        raise ValueError("checksum inventory mismatch")
    if not {"llama-server", "LICENSE"} <= expected.keys():
        raise ValueError("runtime executable or license missing")
    for p in entries:
        with p.open("rb") as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() != expected[p.name]:
                raise ValueError("runtime checksum mismatch: " + p.name)


if __name__ == "__main__":
    verify(Path(sys.argv[1]), Path(sys.argv[2]))
