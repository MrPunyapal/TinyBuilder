"""Package the pinned upstream runtime, not a runtime lifecycle implementation."""
import hashlib
import json
import re
import shutil
import stat
import subprocess
import sys
import zipfile
from pathlib import Path, PurePosixPath

ARCHIVE = "llama-b6500-bin-macos-arm64.zip"
ARCHIVE_SHA256 = "4f34ae19823ee22e8036d6da91f083ca62ab926c2a0a4a5ce9df34897360087b"
LICENSE_BLOB = "acb96ce78e0486e9dc7602cdcdd2f491c34f335a"
NAME = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.+-]*")


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def extract(archive, output, expected):
    """Select server and dylibs from authenticated archive; never extract links."""
    if digest(archive) != expected:
        raise ValueError("upstream archive digest mismatch")
    selected = {}
    with zipfile.ZipFile(archive) as source:
        for item in source.infolist():
            path = PurePosixPath(item.filename)
            if path.is_absolute() or ".." in path.parts or "\\" in item.filename:
                raise ValueError("unsafe archive path")
            name = path.name
            if name != "llama-server" and not name.endswith(".dylib"):
                continue
            mode = item.external_attr >> 16
            if (not NAME.fullmatch(name) or item.is_dir() or
                    stat.S_IFMT(mode) not in (0, stat.S_IFREG) or
                    name.casefold() in selected):
                raise ValueError("unsafe or duplicate native member")
            selected[name.casefold()] = item
        if "llama-server" not in selected:
            raise ValueError("missing server")
        output.mkdir()
        for item in selected.values():
            target = output / PurePosixPath(item.filename).name
            with source.open(item) as src, target.open("xb") as dst:
                shutil.copyfileobj(src, dst)
            target.chmod(0o755 if target.name == "llama-server" else 0o644)


def stage(archive, license_path, output, sign):
    if archive.name != ARCHIVE:
        raise ValueError("unexpected upstream archive name")
    license_bytes = license_path.read_bytes()
    blob = b"blob " + str(len(license_bytes)).encode() + b"\0" + license_bytes
    if hashlib.sha1(blob).hexdigest() != LICENSE_BLOB:
        raise ValueError("pinned license blob mismatch")
    extract(archive, output, ARCHIVE_SHA256)
    dependencies = sorted(p.name for p in output.iterdir() if p.suffix == ".dylib")
    for name in [*dependencies, "llama-server"]:
        sign(output / name)
    (output / "LICENSE").write_bytes(license_bytes)
    manifest = {
        "schema": 1, "revision": "b6500", "os": "macos", "architecture": "arm64",
        "backend": "cpu", "executable": "llama-server", "archive": ARCHIVE,
        "archive_sha256": ARCHIVE_SHA256, "native_dependencies": dependencies,
        "files": {p.name: digest(p) for p in sorted(output.iterdir())},
    }
    (output / "runtime-manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")


def ad_hoc_sign(path):
    subprocess.run(["/usr/bin/lipo", "-verify_arch", "arm64", str(path)], check=True)
    subprocess.run(["/usr/bin/codesign", "--force", "--sign", "-", str(path)], check=True)
    subprocess.run(["/usr/bin/codesign", "--verify", "--strict", str(path)], check=True)


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit("usage: stage_runtime.py ARCHIVE PINNED_LICENSE NEW_DIRECTORY")
    stage(*(Path(arg) for arg in sys.argv[1:]), ad_hoc_sign)
