"""Model-free inspection of a trusted, already extracted distribution."""
import argparse
import hashlib
import json
from pathlib import Path
import stat
import struct
import os
import re
import subprocess
import tempfile


def native_architectures(path):
    """Identify native headers, not complete loader compatibility.

    An empty set means a recognized but unsupported/malformed native header.
    None means ordinary non-native content.
    """
    with path.open("rb") as stream:
        head = stream.read(64)
        if head.startswith(b"MZ"):
            if len(head) < 64:
                return set()
            offset = struct.unpack_from("<I", head, 60)[0]
            if offset < 64 or offset + 6 > path.stat().st_size:
                return set()
            stream.seek(offset)
            pe = stream.read(6)
            if pe[:4] != b"PE\0\0":
                return set()
            arch = {0x8664: "x64", 0xAA64: "arm64"}.get(int.from_bytes(pe[4:6], "little"))
            return {arch} if arch else set()
        if head.startswith(b"\x7fELF"):
            if len(head) < 20 or head[4:6] != b"\x02\x01":
                return set()
            arch = {62: "x64", 183: "arm64"}.get(int.from_bytes(head[18:20], "little"))
            return {arch} if arch else set()
        cpus = {0x0100000C: "arm64", 0x01000007: "x64"}
        if head[:4] == b"\xcf\xfa\xed\xfe":
            arch = cpus.get(int.from_bytes(head[4:8], "little")) if len(head) >= 32 else None
            return {arch} if arch else set()
        if head[:4] in (b"\xfe\xed\xfa\xce", b"\xce\xfa\xed\xfe", b"\xfe\xed\xfa\xcf"):
            return set()
        if head[:4] in (b"\xca\xfe\xba\xbe", b"\xca\xfe\xba\xbf"):
            # A Java class shares the first magic; ordinary .class data is not Mach-O.
            if path.suffix.lower() == ".class":
                return None
            count = int.from_bytes(head[4:8], "big")
            if not 1 <= count <= 16:
                return set()
            wide = head[:4] == b"\xca\xfe\xba\xbf"
            entry_size = 32 if wide else 20
            table_end = 8 + count * entry_size
            size = path.stat().st_size
            stream.seek(8)
            arches, ranges = set(), []
            for _ in range(count):
                entry = stream.read(entry_size)
                if len(entry) != entry_size:
                    return set()
                cpu = int.from_bytes(entry[:4], "big")
                n = 8 if wide else 4
                offset = int.from_bytes(entry[8:8+n], "big")
                length = int.from_bytes(entry[8+n:8+2*n], "big")
                if (cpu not in cpus or offset < table_end or length < 32
                        or offset + length > size or any(offset < hi and lo < offset + length for lo, hi in ranges)):
                    return set()
                position = stream.tell()
                stream.seek(offset)
                inner = stream.read(8)
                stream.seek(position)
                if inner[:4] != b"\xcf\xfa\xed\xfe" or int.from_bytes(inner[4:8], "little") != cpu:
                    return set()
                ranges.append((offset, offset + length))
                arches.add(cpus[cpu])
            return arches
    return None


def architecture(path):
    arches = native_architectures(path)
    return next(iter(arches)) if arches and len(arches) == 1 else None


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
            if resolved == Path(".") or forbidden(resolved) or not (root / resolved).is_file():
                raise ValueError("Forbidden or non-file symlink target")
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
        arches = native_architectures(path)
        if arches is not None and expected not in arches:
            raise ValueError("Unexpected or unsupported native binary architecture")
        records[relative.as_posix()] = {"bytes": path.stat().st_size, "sha256": digest(path)}
        if arches is not None:
            records[relative.as_posix()]["architectures"] = sorted(arches)
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


def check_provenance(report, artifact_sha=None, inventory=None, inventory_sha=None):
    """Compare independently supplied digests and the exact reviewed inventory.

    The caller must obtain both trusted values independently of the files under
    inspection. This is not a signature or proof of how the artifact was built.
    """
    if artifact_sha is not None:
        if not re.fullmatch("[0-9a-fA-F]{64}", artifact_sha) or report["artifact_sha256"] != artifact_sha.lower():
            raise ValueError("Artifact digest mismatch")
    if (inventory is None) != (inventory_sha is None):
        raise ValueError("Inventory and its independently trusted digest must be supplied together")
    if inventory is not None:
        if not re.fullmatch("[0-9a-fA-F]{64}", inventory_sha):
            raise ValueError("Invalid inventory digest")
        raw = inventory.read_bytes()
        if hashlib.sha256(raw).hexdigest() != inventory_sha.lower():
            raise ValueError("Inventory digest mismatch")
        expected = json.loads(raw)
        keys = ("candidate_sha", "artifact_sha256", "compressed_bytes", "expected_arch",
                "installed_file_bytes", "files", "links", "required_metadata")
        if not isinstance(expected, dict) or any(key not in report or key not in expected or expected[key] != report[key] for key in keys):
            raise ValueError("Reviewed inventory does not match candidate or distribution")
    report["trusted_artifact_digest_checked"] = artifact_sha is not None
    report["trusted_inventory_checked"] = inventory is not None


def required_metadata(report, names):
    if len(set(names)) != len(names):
        raise ValueError("License, notices and SBOM must be separate files")
    for name in names:
        if name not in report["files"] or report["files"][name]["bytes"] <= 0:
            raise ValueError("Missing or empty license, notice or SBOM")
    return dict(zip(("license", "notices", "sbom"), names))


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
    parser.add_argument("--candidate-sha", help="Exact source candidate SHA supplied by release owner")
    parser.add_argument("--expected-artifact-sha256", help="Independently trusted artifact digest")
    parser.add_argument("--expected-inventory", type=Path, help="Previously reviewed inventory report")
    parser.add_argument("--expected-inventory-sha256", help="Independently trusted inventory digest")
    parser.add_argument("--allow-contained-links", action="store_true")
    parser.add_argument("--smoke", action="store_true", help="Execute trusted binaries only")
    args = parser.parse_args()
    if args.output.resolve().is_relative_to(args.root.resolve()):
        parser.error("Output must be outside the distribution")
    if args.output.resolve() in {args.artifact.resolve(), args.expected_inventory.resolve() if args.expected_inventory else None}:
        parser.error("Output must not overwrite an input")
    if args.candidate_sha is not None and not re.fullmatch("[0-9a-f]{40}", args.candidate_sha):
        parser.error("Candidate must be an exact lowercase Git SHA")
    if args.expected_inventory and args.expected_inventory.resolve().is_relative_to(args.root.resolve()):
        parser.error("Reviewed inventory must be outside the distribution")
    if args.smoke and not all((args.candidate_sha, args.expected_artifact_sha256, args.expected_inventory, args.expected_inventory_sha256)):
        parser.error("Smoke requires candidate SHA and independently trusted artifact and inventory digests")
    required = [args.app, args.server, args.license, args.notices, args.sbom]
    if len(set(required)) != len(required):
        parser.error("Required executable and metadata paths must be distinct")
    report = inspect(args.root, args.arch, required, allow_contained_links=args.allow_contained_links)
    report["required_metadata"] = required_metadata(report, [args.license, args.notices, args.sbom])
    if args.candidate_sha:
        report["candidate_sha"] = args.candidate_sha
    for name in (args.app, args.server):
        if args.arch not in (native_architectures(args.root / name) or set()):
            raise ValueError("Unexpected executable architecture")
    if not args.artifact.is_file() or args.artifact.is_symlink() or args.artifact.resolve().is_relative_to(args.root.resolve()):
        parser.error("Artifact must be a regular file outside the extracted tree")
    report["compressed_bytes"] = args.artifact.stat().st_size
    report["artifact_sha256"] = digest(args.artifact)
    check_provenance(report, args.expected_artifact_sha256, args.expected_inventory, args.expected_inventory_sha256)
    if args.smoke:
        report["smoke"] = smoke(args.root, args.app, args.server)
    report["qualification"] = "static or explicit smoke only; gates A/B/C not tested"
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
