"""Offline inventory and verification of an already-staged Windows payload.

This is build tooling, not a runtime manager or an uninstall program.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import stat
import struct

MANIFEST = "windows-payload.json"
FORBIDDEN = {".git", ".venv", "__pycache__", ".env", "node_modules", "vendor"}
SUFFIXES = {".gguf", ".safetensors", ".sqlite", ".sqlite3", ".db", ".pem",
            ".pfx", ".p12", ".key", ".pyc", ".onnx", ".pt", ".bin"}
RESERVED = {"CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$",
            *(f"COM{i}" for i in "123456789¹²³"),
            *(f"LPT{i}" for i in "123456789¹²³")}


def safe_relative(value):
    """Use a deliberately narrow, portable Windows installer path alphabet."""
    if not isinstance(value, str) or not value:
        raise ValueError("empty or non-string path")
    for part in value.split("/"):
        if (not re.fullmatch(r"[A-Za-z0-9_.+() -]+", part)
                or part in {".", ".."} or part.endswith((" ", "."))
                or part.split(".")[0].rstrip(" ").upper() in RESERVED):
            raise ValueError(f"unsafe payload path: {value!r}")
        lower = part.lower()
        if (lower in FORBIDDEN or lower.startswith(".env.")
                or Path(lower).suffix in SUFFIXES):
            raise ValueError(f"forbidden payload path: {value!r}")
    return value


def plain(path):
    info = path.lstat()
    if (stat.S_ISLNK(info.st_mode) or
            getattr(info, "st_file_attributes", 0) & 0x400):
        raise ValueError(f"link/reparse point: {path.name}")
    if not (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode)):
        raise ValueError(f"non-regular payload entry: {path.name}")
    if stat.S_ISREG(info.st_mode) and info.st_nlink != 1:
        raise ValueError(f"hardlinked payload entry: {path.name}")
    return info


def root_directory(root):
    root = Path(root).absolute()
    for parent in reversed((root, *root.parents)):
        if not stat.S_ISDIR(plain(parent).st_mode):
            raise ValueError("payload root is not a directory")
    return root


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_x64(path):
    """Check PE signature, AMD64 machine and PE32+ optional-header magic."""
    with path.open("rb") as stream:
        header = stream.read(64)
        if len(header) != 64 or header[:2] != b"MZ":
            raise ValueError(f"not a PE file: {path.name}")
        offset = struct.unpack_from("<I", header, 60)[0]
        if offset < 64 or offset > path.stat().st_size - 26:
            raise ValueError(f"invalid PE offset: {path.name}")
        stream.seek(offset)
        pe = stream.read(26)
    if (len(pe) != 26 or pe[:4] != b"PE\0\0"
            or struct.unpack_from("<H", pe, 4)[0] != 0x8664
            or struct.unpack_from("<H", pe, 20)[0] < 2
            or struct.unpack_from("<H", pe, 24)[0] != 0x20B):
        raise ValueError(f"not Windows x64 PE32+: {path.name}")


def inventory(root):
    root = root_directory(root)
    rows = []
    seen = set()

    def walk(directory):
        for item in sorted(directory.iterdir()):
            name = safe_relative(item.relative_to(root).as_posix())
            folded = name.casefold()
            if folded in seen or folded == MANIFEST.casefold():
                raise ValueError(f"duplicate or reserved payload path: {name}")
            seen.add(folded)
            info = plain(item)
            if stat.S_ISDIR(info.st_mode):
                walk(item)
            else:
                if item.suffix.lower() in {".exe", ".dll", ".pyd"}:
                    require_x64(item)
                rows.append({"path": name, "bytes": info.st_size,
                             "sha256": sha256(item)})

    walk(root)
    return sorted(rows, key=lambda row: row["path"])


def make_manifest(root, app, server, runtime_files):
    """Runtime files are supplied by the shared runtime release owner.

    Map exact payload-relative paths to independently trusted SHA-256 values
    for llama-server and its native dependencies. No assets are fetched here.
    """
    if not isinstance(runtime_files, dict):
        raise ValueError("runtime file pins must be a mapping")
    app, server = safe_relative(app), safe_relative(server)
    if (app.casefold() == server.casefold() or not app.lower().endswith(".exe")
            or server.split("/")[-1].lower() != "llama-server.exe"):
        raise ValueError("invalid executable roles")
    rows = inventory(root)
    by_path = {row["path"]: row for row in rows}
    if app not in by_path or server not in runtime_files:
        raise ValueError("missing application or runtime executable pin")
    for path, digest in runtime_files.items():
        safe_relative(path)
        if not isinstance(digest, str) or not re.fullmatch("[0-9a-f]{64}", digest):
            raise ValueError("invalid runtime SHA-256")
        if path not in by_path or by_path[path]["sha256"] != digest:
            raise ValueError(f"missing or mismatched pinned runtime file: {path}")
    # The runtime directory must not silently pick up other libraries.
    prefix = server.rpartition("/")[0]
    if not prefix:
        raise ValueError("runtime must have its own directory")
    if app.startswith(prefix + "/"):
        raise ValueError("application must be outside runtime directory")
    actual_runtime = {p for p in by_path if p.startswith(prefix + "/")}
    if actual_runtime != set(runtime_files):
        raise ValueError("runtime inventory differs from trusted file list")
    return {"schema": 1, "app": app, "server": server,
            "bytes": sum(row["bytes"] for row in rows), "files": rows}


def verify(root, manifest):
    if not isinstance(manifest, dict) or manifest.get("schema") != 1:
        raise ValueError("unsupported inventory schema")
    rows = inventory(root)
    if rows != manifest["files"] or sum(r["bytes"] for r in rows) != manifest["bytes"]:
        raise ValueError("payload differs from trusted inventory")
    paths = {r["path"] for r in rows}
    for key in ("app", "server"):
        if safe_relative(manifest[key]) not in paths:
            raise ValueError(f"missing {key}")
    return manifest["bytes"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("create", "verify"))
    parser.add_argument("root", type=Path)
    parser.add_argument("manifest", type=Path, help="external trusted inventory")
    parser.add_argument("--app")
    parser.add_argument("--server")
    parser.add_argument("--runtime-files", type=Path)
    args = parser.parse_args()
    try:
        root = root_directory(args.root)
        output = args.manifest.resolve()
        if output == root.resolve() or root.resolve() in output.parents:
            raise ValueError("inventory must live outside payload")
        if args.mode == "create":
            if not (args.app and args.server and args.runtime_files):
                parser.error("create requires --app, --server and --runtime-files")
            pins = json.loads(args.runtime_files.read_text(encoding="utf-8"))
            manifest = make_manifest(root, args.app, args.server, pins)
            with output.open("x", encoding="utf-8") as stream:
                json.dump(manifest, stream, indent=2)
                stream.write("\n")
            size = manifest["bytes"]
        else:
            manifest = json.loads(output.read_text(encoding="utf-8"))
            size = verify(root, manifest)
        print(f"Verified payload: {size} logical bytes")
    except (OSError, ValueError, TypeError, KeyError) as exc:
        parser.exit(1, f"Payload check failed: {exc}\n")


if __name__ == "__main__":
    main()
