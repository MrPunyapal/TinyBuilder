"""Adapt a verified local upstream archive to PR #10's flat runtime contract.

No downloading, extraction, model loading or process lifecycle is performed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import stat
import zipfile

from payload import inventory, plain, safe_relative, sha256

MANIFEST = "runtime-manifest.json"


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique)


def flat(name):
    safe_relative(name)
    if (not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.+-]*", name)
            or name.casefold() == MANIFEST.casefold()):
        raise ValueError("runtime filenames must be flat and not reserved")
    return name


def member_hash(stream):
    digest = hashlib.sha256()
    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
        digest.update(chunk)
    return digest.hexdigest()


def prepare(runtime, archive, selection, extra_pins, catalog):
    """Return the runtime manifest after checking staged bytes against sources.

    selection maps staged flat filenames to exact archive members.
    extra_pins maps independently audited additions (e.g. LICENSE) to hashes.
    catalog is the shared runtime catalog; tests inject a synthetic fixture.
    """
    runtime, archive = Path(runtime), Path(archive)
    archive_name, archive_hash = catalog.CPU_ARCHIVES[("windows", "x64")]
    if archive.name != archive_name or not stat.S_ISREG(plain(archive).st_mode):
        raise ValueError("wrong runtime archive")
    if sha256(archive) != archive_hash:
        raise ValueError("runtime archive digest mismatch")
    if not isinstance(selection, dict) or not isinstance(extra_pins, dict):
        raise ValueError("selection and extra pins must be mappings")
    if set(selection) & set(extra_pins):
        raise ValueError("ambiguous file provenance")
    for name in (*selection, *extra_pins):
        flat(name)
    if "llama-server.exe" not in selection:
        raise ValueError("server must originate in the pinned archive")
    rows = inventory(runtime)
    if any(not stat.S_ISREG(plain(path).st_mode) for path in runtime.iterdir()):
        raise ValueError("runtime directory must contain only regular files")
    hashes = {flat(row["path"]): row["sha256"] for row in rows}
    if set(hashes) != set(selection) | set(extra_pins) or "LICENSE" not in hashes:
        raise ValueError("staged runtime inventory or license mismatch")
    if any(hashes[name] != digest for name, digest in extra_pins.items()):
        raise ValueError("additional runtime file digest mismatch")
    if len(set(selection.values())) != len(selection):
        raise ValueError("archive member selected more than once")
    with zipfile.ZipFile(archive) as source:
        members = {}
        for info in source.infolist():
            if info.is_dir():
                continue
            if info.filename in members:
                raise ValueError("duplicate archive member")
            members[info.filename] = info
        for name, member in selection.items():
            safe_relative(member)
            info = members.get(member)
            if info is None or stat.S_ISLNK(info.external_attr >> 16):
                raise ValueError("missing or linked archive member")
            if member.rsplit("/", 1)[-1] != name:
                raise ValueError("archive member basename differs from staged file")
            if info.file_size != (runtime / name).stat().st_size:
                raise ValueError("archive member size mismatch")
            with source.open(info) as stream:
                if member_hash(stream) != hashes[name]:
                    raise ValueError("staged runtime differs from verified archive")
    return {
        "schema": 1, "revision": catalog.REVISION, "os": "windows",
        "architecture": "x64", "backend": "cpu",
        "executable": "llama-server.exe", "archive": archive_name,
        "archive_sha256": archive_hash,
        "native_dependencies": sorted(n for n in hashes if n.lower().endswith(".dll")),
        "files": hashes,
    }


def write_json(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--payload-root", required=True, type=Path)
    parser.add_argument("--runtime-dir", default="runtime")
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--selection", required=True, type=Path)
    parser.add_argument("--extra-pins", type=Path)
    parser.add_argument("--pins-out", required=True, type=Path)
    args = parser.parse_args()
    try:
        # The shared owner is authoritative for the revision and archive pin.
        from tinybuilder.runtime import catalog
        relative = safe_relative(args.runtime_dir)
        root = args.payload_root.resolve(strict=True)
        runtime = args.payload_root / relative
        output = args.pins_out.resolve()
        if output == root or root in output.parents or output.exists():
            raise ValueError("pins output must be new and outside payload")
        manifest = prepare(runtime, args.archive, read_json(args.selection),
                           read_json(args.extra_pins) if args.extra_pins else {},
                           catalog)
        target = runtime / MANIFEST
        write_json(target, manifest)
        pins = {relative + "/" + name: digest
                for name, digest in manifest["files"].items()}
        pins[relative + "/" + MANIFEST] = sha256(target)
        write_json(output, pins)
        print("Prepared shared Windows CPU runtime manifest and external pins")
    except (ImportError, OSError, ValueError, KeyError, TypeError,
            RuntimeError, zipfile.BadZipFile) as exc:
        parser.exit(1, f"Runtime packaging failed: {type(exc).__name__}: {exc}\n")


if __name__ == "__main__":
    main()
