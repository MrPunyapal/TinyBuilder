"""Inspect pinned upstream runtime ZIPs without extraction or execution.

Results are candidate input evidence, not a trusted staged payload or license,
loader, CPU, installation or model qualification.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import tempfile
from urllib.request import Request, urlopen
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tinybuilder.runtime.catalog import CPU_ARCHIVES, REVISION

MAX_ARCHIVE = 128 * 1024 * 1024
MAX_EXPANDED = 512 * 1024 * 1024


def download(url, destination, expected):
    digest = hashlib.sha256()
    total = 0
    with urlopen(Request(url, headers={"User-Agent": "TinyBuilder-runtime-evidence"}), timeout=60) as response:
        if not response.geturl().startswith("https://"):
            raise ValueError("Non-HTTPS runtime source")
        with destination.open("xb") as stream:
            while block := response.read(1024 * 1024):
                total += len(block)
                if total > MAX_ARCHIVE:
                    raise ValueError("Runtime archive exceeds limit")
                digest.update(block)
                stream.write(block)
    if digest.hexdigest() != expected:
        raise ValueError("Runtime archive digest mismatch")
    return total


def inspect(path, expected):
    if path.stat().st_size > MAX_ARCHIVE:
        raise ValueError("Runtime archive exceeds limit")
    with path.open("rb") as stream:
        if hashlib.file_digest(stream, "sha256").hexdigest() != expected:
            raise ValueError("Runtime archive digest mismatch")
        stream.seek(0)
        with zipfile.ZipFile(stream) as archive:
            entries = archive.infolist()
            if len(entries) > 10000 or sum(e.file_size for e in entries) > MAX_EXPANDED:
                raise ValueError("Runtime archive inventory exceeds limits")
            seen = set()
            records = []
            for entry in entries:
                name = entry.filename.rstrip("/")
                if (not name or not re.fullmatch(r"[A-Za-z0-9_./+ -]+", name)
                        or name.startswith("/") or any(p in {"", ".", ".."} for p in name.split("/"))
                        or name.casefold() in seen):
                    raise ValueError("Unsafe or duplicate archive member")
                seen.add(name.casefold())
                mode = stat.S_IFMT(entry.external_attr >> 16)
                if entry.is_dir():
                    if mode not in (0, stat.S_IFDIR):
                        raise ValueError("Unexpected directory type")
                    continue
                if mode == stat.S_IFLNK:
                    kind = "symlink"
                elif mode in (0, stat.S_IFREG):
                    kind = "regular"
                else:
                    raise ValueError("Unexpected archive member type")
                digest = hashlib.sha256()
                with archive.open(entry) as member:
                    while block := member.read(1024 * 1024):
                        digest.update(block)
                records.append({"path": name, "kind": kind, "bytes": entry.file_size,
                                "sha256": digest.hexdigest()})
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", choices=("windows", "macos", "linux"))
    args = parser.parse_args()
    target = next(key for key in CPU_ARCHIVES if key[0] == args.target)
    filename, expected = CPU_ARCHIVES[target]
    url = f"https://github.com/ggml-org/llama.cpp/releases/download/{REVISION}/{filename}"
    with tempfile.TemporaryDirectory(prefix="tinybuilder-runtime-evidence-") as tmp:
        path = Path(tmp) / filename
        size = download(url, path, expected)
        records = inspect(path, expected)
        server = "llama-server.exe" if target[0] == "windows" else "llama-server"
        candidates = [row for row in records if PurePosixPath(row["path"]).name == server
                      and row["kind"] == "regular"]
        if len(candidates) != 1:
            raise ValueError("Expected unique regular server in archive")
        print(json.dumps({"status": "archive evidence only; not qualified",
                          "source": url, "archive_sha256": expected, "archive_bytes": size,
                          "target": target, "members": records}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
