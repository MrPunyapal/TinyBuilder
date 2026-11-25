"""Model-free inspection of a trusted, already extracted distribution."""
import argparse
import hashlib
import json
from pathlib import Path
import stat
import struct
import subprocess


def architecture(path):
    with path.open("rb") as stream:
        head = stream.read(64)
        if head.startswith(b"MZ") and len(head) == 64:
            stream.seek(struct.unpack_from("<I", head, 60)[0])
            pe = stream.read(6)
            if pe[:4] == b"PE\0\0":
                return {0x8664: "x64", 0xAA64: "arm64"}.get(int.from_bytes(pe[4:6], "little"))
        if head.startswith(b"\x7fELF") and len(head) >= 20 and head[4:6] == b"\x02\x01":
            return {62: "x64", 183: "arm64"}.get(int.from_bytes(head[18:20], "little"))
        if head[:4] == b"\xcf\xfa\xed\xfe":
            return {0x0100000C: "arm64", 0x01000007: "x64"}.get(int.from_bytes(head[4:8], "little"))
    return None


def forbidden(path):
    parts = [part.lower() for part in path.parts]
    return any(p in {".git", ".venv", "__pycache__", ".ssh", "transcripts", "private", "credentials.json", "id_rsa", "id_ed25519"} or p.startswith(".env") for p in parts) or Path(parts[-1]).suffix in {".gguf", ".safetensors", ".sqlite", ".sqlite3", ".db", ".pem", ".p12", ".pfx", ".key", ".jsonl", ".pt", ".pth", ".onnx", ".bin"}


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def inspect(root, expected, required):
    if not root.is_dir() or root.is_symlink():
        raise ValueError("Expected extracted directory")
    records = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if forbidden(relative) or path.is_symlink():
            raise ValueError("Forbidden path or symlink in distribution")
        if path.is_dir():
            continue
        if not stat.S_ISREG(path.stat().st_mode):
            raise ValueError("Non-regular distribution file")
        with path.open("rb") as stream:
            header = stream.read(32)
        if header.startswith((b"GGUF", b"SQLite format 3\0")):
            raise ValueError("Forbidden model/database content")
        records[relative.as_posix()] = {"bytes": path.stat().st_size, "sha256": digest(path)}
    for name in required:
        if name not in records:
            raise ValueError("Required file missing")
    return {"installed_file_bytes": sum(v["bytes"] for v in records.values()), "files": records, "expected_arch": expected}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--arch", choices=["x64", "arm64"], required=True)
    parser.add_argument("--app", required=True, help="Relative executable path")
    parser.add_argument("--server", required=True, help="Relative executable path")
    parser.add_argument("--license", required=True)
    parser.add_argument("--notices", required=True)
    parser.add_argument("--sbom", required=True)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = inspect(args.root, args.arch, [args.app, args.server, args.license, args.notices, args.sbom])
    for name in (args.app, args.server):
        if architecture(args.root / name) != args.arch:
            raise ValueError("Unexpected executable architecture")
    report["compressed_bytes"] = args.artifact.stat().st_size
    report["artifact_sha256"] = digest(args.artifact)
    report["qualification"] = "static-only; gates A/B/C not tested"
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
