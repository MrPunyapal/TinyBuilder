"""Collect candidate wheel pins without installing or importing downloaded code.

The native runner resolves dependencies; PyPI release metadata independently
checks the downloaded file hashes. Results are evidence for review, not a
trusted lock, and must never be consumed automatically by build workflows.
"""
import argparse
from email.parser import BytesParser
from email.policy import default
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from urllib.parse import quote
from urllib.request import urlopen
import zipfile


PINS = {"macos": "6.22.2", "linux": "6.15.0"}


def wheel_record(path, lookup):
    with zipfile.ZipFile(path) as wheel:
        metadata = [entry for entry in wheel.infolist()
                    if entry.filename.endswith(".dist-info/METADATA")]
        if len(metadata) != 1 or metadata[0].file_size > 1024 * 1024:
            raise ValueError("Unexpected wheel metadata")
        fields = BytesParser(policy=default).parsebytes(wheel.read(metadata[0]))
    name, version = fields["Name"], fields["Version"]
    if (not name or not version or not re.fullmatch(r"[A-Za-z0-9_.-]+", name)
            or not re.fullmatch(r"[A-Za-z0-9_.!+-]+", version)):
        raise ValueError("Invalid wheel identity")
    name = re.sub(r"[-_.]+", "-", name).lower()
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    release = lookup(name, version)
    if release["info"]["version"] != version:
        raise ValueError("Release metadata version mismatch")
    matches = [item for item in release["urls"] if item["filename"] == path.name
               and item["packagetype"] == "bdist_wheel" and not item["yanked"]]
    if len(matches) != 1 or matches[0]["digests"]["sha256"] != digest:
        raise ValueError("Wheel differs from published non-yanked release")
    return name, version, digest


def pypi_release(name, version):
    url = "https://pypi.org/pypi/" + quote(name, safe="") + "/" + quote(version, safe="") + "/json"
    with urlopen(url, timeout=30) as response:
        data = response.read(4 * 1024 * 1024 + 1)
    if len(data) > 4 * 1024 * 1024:
        raise ValueError("Release metadata too large")
    return json.loads(data)


def collect(directory, target, lookup=pypi_release):
    records = {}
    for path in sorted(directory.iterdir()):
        if not path.is_file() or path.suffix != ".whl":
            raise ValueError("Only wheels may be resolved")
        name, version, digest = wheel_record(path, lookup)
        if name in records:
            raise ValueError("Duplicate package")
        records[name] = (version, digest)
    if records.get("pyinstaller", (None,))[0] != PINS[target]:
        raise ValueError("Expected PyInstaller pin missing")
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", choices=PINS)
    args = parser.parse_args()
    if sys.version_info[:2] != (3, 12):
        raise SystemExit("Python 3.12 required")
    expected_platform = {"macos": "darwin", "linux": "linux"}[args.target]
    if sys.platform != expected_platform:
        raise SystemExit("Native target runner required")
    with tempfile.TemporaryDirectory(prefix="tinybuilder-wheel-evidence-") as tmp:
        # Wheels only: no build backend execution, no package installation.
        env = {key: value for key, value in os.environ.items()
               if not key.upper().startswith("PIP_")}
        env["PIP_CONFIG_FILE"] = os.devnull
        subprocess.run([sys.executable, "-I", "-m", "pip", "--isolated",
                        "--disable-pip-version-check", "download",
                        "--index-url", "https://pypi.org/simple", "--no-cache-dir",
                        "--only-binary=:all:", "--dest", tmp,
                        "pyinstaller==" + PINS[args.target]],
                       env=env, check=True, timeout=600)
        records = collect(Path(tmp), args.target)
        print("\nCANDIDATE LOCK ONLY - REVIEW BEFORE USE")
        for name, (version, digest) in sorted(records.items()):
            print(f"{name}=={version} --hash=sha256:{digest}")


if __name__ == "__main__":
    main()
