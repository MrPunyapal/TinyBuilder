"""Build-time adapter to the shared runtime manifest; no network access."""
import hashlib
import json
import stat
import sys
import zipfile
from pathlib import Path, PurePosixPath

from verify_runtime import verify


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def prepare(root, sums, archive, pin, revision):
    verify(root, sums)
    name, sha = pin
    if archive.name != name or digest(archive) != sha:
        raise ValueError("upstream archive does not match shared pin")
    files = {p.name: digest(p) for p in sorted(root.iterdir())}
    native = sorted(n for n in files if n.startswith("lib") and ".so" in n)
    with zipfile.ZipFile(archive) as source:
        for filename in ["llama-server", *native]:
            matches = [i for i in source.infolist()
                       if PurePosixPath(i.filename).name == filename and not i.is_dir()]
            if len(matches) != 1 or stat.S_ISLNK(matches[0].external_attr >> 16):
                raise ValueError("missing, ambiguous or symlink upstream payload: " + filename)
            with source.open(matches[0]) as stream:
                if hashlib.file_digest(stream, "sha256").hexdigest() != files[filename]:
                    raise ValueError("staged binary differs from pinned archive: " + filename)
    manifest = {"schema": 1, "revision": revision, "os": "linux", "architecture": "x64",
                "backend": "cpu", "executable": "llama-server", "archive": name,
                "archive_sha256": sha, "native_dependencies": native, "files": files}
    with (root / "runtime-manifest.json").open("x", encoding="utf-8") as stream:
        json.dump(manifest, stream, indent=2, sort_keys=True)
        stream.write("\n")


if __name__ == "__main__":
    # Import the shared source checkout, not a potentially stale installed copy.
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from tinybuilder.runtime.catalog import CPU_ARCHIVES, REVISION
    from tinybuilder.runtime.manifest import resolve_runtime

    root, sums, archive = map(Path, sys.argv[1:])
    prepare(root, sums, archive, CPU_ARCHIVES[("linux", "x64")], REVISION)
    resolve_runtime(root.resolve(), "cpu")
