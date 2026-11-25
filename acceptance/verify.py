"""Model-free inspection of a trusted, already extracted distribution."""
import argparse
import hashlib
import json
from pathlib import Path
import stat
import struct
import os
import subprocess
import tempfile


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


def inspect(root, expected, required, *, allow_contained_links=False):
    if not root.is_dir() or root.is_symlink() or root.is_junction():
        raise ValueError("Expected extracted directory")
    root = root.resolve(strict=True)
    records, links = {}, {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if forbidden(relative) or path.is_junction():
            raise ValueError("Forbidden path or junction in distribution")
        if path.is_symlink():
            if not allow_contained_links:
                raise ValueError("Symlink requires explicit contained-link policy")
            target = Path(os.readlink(path))
            if target.is_absolute() or target.drive:
                raise ValueError("Absolute symlink")
            try:
                resolved = path.resolve(strict=True).relative_to(root)
            except (OSError, RuntimeError, ValueError):
                raise ValueError("Broken or escaping symlink") from None
            if resolved == Path(".") or forbidden(resolved) or path.parent.is_relative_to(root / resolved):
                raise ValueError("Forbidden or cyclic symlink target")
            links[relative.as_posix()] = resolved.as_posix()
            continue
        if path.is_dir():
            continue
        if not stat.S_ISREG(path.stat().st_mode):
            raise ValueError("Non-regular distribution file")
        with path.open("rb") as stream:
            header = stream.read(32)
        if header.startswith((b"GGUF", b"SQLite format 3\0")):
            raise ValueError("Forbidden model/database content")
        arch = architecture(path)
        if arch is not None and arch != expected:
            raise ValueError("Unexpected native binary architecture")
        records[relative.as_posix()] = {"bytes": path.stat().st_size, "sha256": digest(path)}
        if arch is not None:
            records[relative.as_posix()]["architecture"] = arch
    for name in required:
        if name not in records:
            raise ValueError("Required file missing")
    return {"installed_file_bytes": sum(v["bytes"] for v in records.values()), "files": records, "links": links, "expected_arch": expected}


def smoke(root, app, server):
    """Explicit trusted-binary smoke only; no model or first-launch claim."""
    root = root.resolve(strict=True)
    with tempfile.TemporaryDirectory(prefix="tinybuilder-smoke-") as tmp:
        home = Path(tmp)
        project = home / "project"
        project.mkdir()
        # Retain only system environment necessary to start a native process.
        allowed = {"SYSTEMROOT", "WINDIR", "COMSPEC", "PATH", "PATHEXT", "TEMP", "TMP", "TMPDIR", "LANG"}
        env = {key: value for key, value in os.environ.items() if key.upper() in allowed}
        env.update(HOME=tmp, USERPROFILE=tmp, LOCALAPPDATA=tmp, APPDATA=tmp,
                   XDG_DATA_HOME=tmp, XDG_CONFIG_HOME=tmp, XDG_CACHE_HOME=tmp)
        checks = {"app_help": [root / app, "--help"],
                  "app_doctor": [root / app, "doctor", "--project", project],
                  "server_version": [root / server, "--version"],
                  "server_help": [root / server, "--help"]}
        for label, command in checks.items():
            try:
                subprocess.run([str(arg) for arg in command], cwd=project, env=env,
                               stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL, shell=False, timeout=30, check=True)
            except (OSError, subprocess.SubprocessError):
                raise ValueError("Smoke check failed: " + label) from None
        return {label: "pass" for label in checks}


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
    parser.add_argument("--expected-artifact-sha256", help="Independently trusted artifact digest")
    parser.add_argument("--allow-contained-links", action="store_true")
    parser.add_argument("--smoke", action="store_true", help="Execute trusted binaries only")
    args = parser.parse_args()
    if args.output.resolve().is_relative_to(args.root.resolve()):
        parser.error("Output must be outside the distribution")
    report = inspect(args.root, args.arch, [args.app, args.server, args.license, args.notices, args.sbom], allow_contained_links=args.allow_contained_links)
    for name in (args.app, args.server):
        if architecture(args.root / name) != args.arch:
            raise ValueError("Unexpected executable architecture")
    report["compressed_bytes"] = args.artifact.stat().st_size
    report["artifact_sha256"] = digest(args.artifact)
    if args.expected_artifact_sha256 is not None and report["artifact_sha256"] != args.expected_artifact_sha256.lower():
        raise ValueError("Artifact digest mismatch")
    report["trusted_artifact_digest_checked"] = args.expected_artifact_sha256 is not None
    if args.smoke:
        if args.expected_artifact_sha256 is None:
            parser.error("Smoke requires an independently trusted artifact digest")
        report["smoke"] = smoke(args.root, args.app, args.server)
    report["qualification"] = "static or explicit smoke only; gates A/B/C not tested"
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
