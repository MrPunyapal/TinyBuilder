"""Build model-free native portable candidates. Never publish releases."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import tarfile
import tempfile
import zipfile

from runtime_evidence import download, inspect
from runtime_upgrade_evidence import PINS, REVISION, SOURCE_COMMIT, inspect_tar

ROOT = Path(__file__).resolve().parents[1]
TARGETS = {
    "x86_64-pc-windows-msvc": ("windows", "x64"),
    "aarch64-apple-darwin": ("macos", "arm64"),
    "x86_64-unknown-linux-gnu": ("linux", "x64"),
}
UPSTREAM_COMMIT = SOURCE_COMMIT
CPU_ARCHIVES = {(platform, arch): PINS[platform] for platform, arch in TARGETS.values()}
SOURCE_NOTICES = {
    "LICENSE": "e7dca554bcb802f98408383a864404e3aa4eacca",
    "LICENSE-jsonhpp": "b5a10275c1cdff6d2d1b4d84f51922d42499dec5",
    "LICENSE-httplib": "3e5ed359a2bb16f52c383745c25f14bb7a81c9e4",
}


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write_json(path, value):
    path.write_bytes((json.dumps(value, sort_keys=True, indent=2) + "\n").encode())


def selected(name, platform):
    if name in {"LICENSE", "LICENSE-LLVM-OpenMP", "LICENSE-jsonhpp", "LICENSE-httplib"}:
        return True
    if platform == "windows":
        return (name == "llama-server.exe"
                or re.fullmatch(r"ggml(?:-[a-z0-9-]+)?\.dll", name) is not None
                or name in {"llama.dll", "llama-common.dll", "llama-server-impl.dll", "mtmd.dll", "libomp.dll"})
    if name == "llama-server":
        return True
    stem = r"lib(?:ggml(?:-[a-z0-9-]+)?|llama(?:-common|-server-impl)?|mtmd)"
    extension = r"(?:\.[0-9]+)*\.dylib" if platform == "macos" else r"\.so(?:\.[0-9]+)*"
    return re.fullmatch(stem + extension, name) is not None


def source_notice(name):
    data = (ROOT / "acceptance" / ("llama-b12359-" + name)).read_bytes().replace(b"\r\n", b"\n")
    blob = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
    if blob != SOURCE_NOTICES[name]:
        raise ValueError("Pinned source notice mismatch")
    return data


def resolve_alias(name, inventory):
    """Only same-directory selected library aliases, never filesystem links."""
    visited = set()
    while True:
        if name in visited or len(visited) >= 8 or name not in inventory:
            raise ValueError("Invalid runtime alias chain")
        visited.add(name)
        record = inventory[name]
        if record["kind"] == "regular":
            return name
        if record["kind"] != "symlink":
            raise ValueError("Unsupported selected runtime link")
        target = record["target"]
        if not re.fullmatch(r"[A-Za-z0-9_+.-]{1,128}", target) or target in {".", ".."}:
            raise ValueError("Unsafe runtime alias")
        name = target


def stage(archive, target, runtime):
    platform, arch = TARGETS[target]
    filename, expected = CPU_ARCHIVES[(platform, arch)]
    is_zip = filename.endswith(".zip")
    if is_zip != (platform == "windows"):
        raise ValueError("Unexpected native archive format")
    records = inspect(archive, expected) if is_zip else inspect_tar(archive, expected)
    runtime.mkdir(parents=True, exist_ok=False)
    server = "llama-server.exe" if platform == "windows" else "llama-server"
    files = {}
    inventory = {}
    prefix = "" if platform == "windows" else f"llama-{REVISION}/"
    for row in records:
        name = PurePosixPath(row["path"]).name
        if not selected(name, platform):
            continue
        if (row["path"] != prefix + name
                or not re.fullmatch(r"[A-Za-z0-9_+.-]{1,128}", name)
                or name.casefold() in {n.casefold() for n in inventory}):
            raise ValueError("Unexpected selected runtime member")
        if row["kind"] != "regular" and (is_zip or row["kind"] != "symlink"
                or name == server or name.startswith("LICENSE")):
            raise ValueError("Unexpected selected runtime member type")
        inventory[name] = row
    if server not in inventory:
        raise ValueError("Missing native server")
    # Resolve every alias before copying; malformed chains cannot influence paths.
    canonical = {name: resolve_alias(name, inventory) for name in inventory}
    context = zipfile.ZipFile(archive) if is_zip else tarfile.open(archive, "r:gz")
    with context as z:
        for name, row in inventory.items():
            if row["kind"] != "regular":
                continue
            dst = runtime / name
            src = z.open(row["path"]) if is_zip else z.extractfile(row["path"])
            if src is None:
                raise ValueError("Missing selected member data")
            with src, dst.open("xb") as out:
                shutil.copyfileobj(src, out)
            if dst.stat().st_size != row["bytes"] or digest(dst) != row["sha256"]:
                raise ValueError("Staged runtime digest mismatch")
            dst.chmod(0o755 if name == server else 0o644)
            files[name] = row["sha256"]
    # Materialize aliases as regular byte-identical files. The embedded manifest
    # authenticates every alias; no symlink/hardlink survives installation.
    for name, resolved in canonical.items():
        if name == resolved:
            continue
        if resolved == server or resolved.startswith("LICENSE"):
            raise ValueError("Alias target is not a library")
        dst = runtime / name
        with (runtime / resolved).open("rb") as src, dst.open("xb") as out:
            shutil.copyfileobj(src, out)
        dst.chmod(0o644)
        if digest(dst) != files[resolved]:
            raise ValueError("Materialized alias digest mismatch")
        files[name] = files[resolved]
    for name in SOURCE_NOTICES:
        data = source_notice(name)
        if name in files:
            if (runtime / name).read_bytes().replace(b"\r\n", b"\n") != data:
                raise ValueError("Archive and pinned source notice disagree")
        else:
            (runtime / name).write_bytes(data)
            files[name] = digest(runtime / name)
    if platform == "windows" and not {"libomp.dll", "LICENSE-LLVM-OpenMP"} <= files.keys():
        raise ValueError("Missing Windows OpenMP dependency or notice")
    required = {
        "windows": {"ggml.dll", "llama.dll", "llama-server-impl.dll", "llama-common.dll", "mtmd.dll"},
        "macos": {"libggml.1.dylib", "libllama.1.dylib", "libllama-server-impl.dylib", "libllama-common.1.dylib", "libmtmd.1.dylib"},
        "linux": {"libggml.so.1", "libllama.so.1", "libllama-server-impl.so", "libllama-common.so.1", "libmtmd.so.1"},
    }[platform]
    if not required <= files.keys():
        raise ValueError("Incomplete runtime payload")
    deps = sorted(n for n in files if n != server and not n.startswith("LICENSE"))
    write_json(runtime / "runtime-manifest.json", {
        "schema": 1, "revision": REVISION, "os": platform, "architecture": arch,
        "backend": "cpu", "executable": server, "archive": filename,
        "archive_sha256": expected, "native_dependencies": deps, "files": files,
    })
    return digest(runtime / "runtime-manifest.json")


def dependency_notices(target, root):
    """Inventory locked crate notices; legal completeness still needs review."""
    metadata = json.loads(subprocess.check_output(
        ["cargo", "metadata", "--locked", "--filter-platform", target, "--format-version", "1"],
        cwd=ROOT / "rust", encoding="utf-8", timeout=120))
    directory = root / "crate-notices"
    directory.mkdir()
    records = []
    for pkg in sorted(metadata["packages"], key=lambda p: (p["name"], p["version"])):
        if pkg["source"] is None:
            continue
        source = Path(pkg["manifest_path"]).parent
        dest = directory / (pkg["name"] + "-" + pkg["version"])
        names = set()
        for p in source.iterdir():
            if p.is_file() and not p.is_symlink() and p.name.upper().startswith(
                    ("LICENSE", "LICENCE", "COPYING", "NOTICE", "COPYRIGHT")):
                names.add(p.name)
        declared = pkg.get("license_file")
        if declared and Path(declared).name == declared:
            names.add(declared)
        copied = []
        for name in sorted(names):
            p = source / name
            if not p.is_file() or p.is_symlink():
                continue
            dest.mkdir(exist_ok=True)
            shutil.copyfile(p, dest / name)
            copied.append(name)
        records.append({"name": pkg["name"], "version": pkg["version"],
                        "source": pkg["source"], "license": pkg.get("license"),
                        "declared_license_file": declared, "copied_notice_files": copied})
    write_json(directory / "inventory.json", {
        "status": "locked dependency notice inventory; not legal clearance",
        "target": target, "packages": records,
    })


def build(target, source_commit, output):
    actual = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if actual != source_commit or not re.fullmatch(r"[0-9a-f]{40}", source_commit):
        raise ValueError("Checkout SHA mismatch")
    version = (ROOT / "rust" / "PRODUCT_VERSION").read_text().strip()
    platform, arch = TARGETS[target]
    filename, expected = CPU_ARCHIVES[(platform, arch)]
    output.mkdir(parents=True, exist_ok=False)
    name = f"tinybuilder-{version}-{target}"
    with tempfile.TemporaryDirectory(prefix="tinybuilder-package-") as tmp:
        root = Path(tmp) / name
        archive = Path(tmp) / filename
        download(f"https://github.com/ggml-org/llama.cpp/releases/download/{REVISION}/{filename}",
                 archive, expected)
        manifest_hash = stage(archive, target, root / "runtime")
        env = dict(os.environ, TINYBUILDER_RUNTIME_MANIFEST_SHA256=manifest_hash)
        subprocess.run(["cargo", "build", "--release", "--locked", "--target", target],
                       cwd=ROOT / "rust", env=env, check=True)
        binary = "tinybuilder.exe" if platform == "windows" else "tinybuilder"
        shutil.copy2(ROOT / "rust" / "target" / target / "release" / binary, root / binary)
        shutil.copy2(ROOT / "LICENSE", root / "LICENSE")
        shutil.copy2(ROOT / "docs" / "CANDIDATE_QUICKSTART.md", root / "README.md")
        dependency_notices(target, root)
        with tempfile.TemporaryDirectory(prefix="tinybuilder smoke ") as project:
            project = Path(project)
            (project / "probe.txt").write_text("candidate-smoke-fact", encoding="utf-8")
            commands = [
                ["--version"], ["doctor", "--project", str(project), "--runtime", str(root / "runtime")],
                ["read", "probe.txt", "--project", str(project)],
                ["search", "candidate-smoke-fact", "--project", str(project)],
                ["inspect", "probe.txt", "--project", str(project)],
            ]
            for args in commands:
                result = subprocess.check_output([str(root / binary), *args], text=True, encoding="utf-8", cwd=project, timeout=30)
                print(result)
                if args[0] in {"read", "search", "inspect"} and "candidate-smoke-fact" not in result:
                    raise ValueError("Smoke evidence missing")
            if list(project.iterdir()) != [project / "probe.txt"] or (project / "probe.txt").read_text() != "candidate-smoke-fact":
                raise ValueError("Project mutated")
            manifest = root / "runtime" / "runtime-manifest.json"
            original = manifest.read_bytes()
            try:
                manifest.write_bytes(original + b"\n")
                result = subprocess.run([str(root / binary), "doctor", "--project", str(project),
                                         "--runtime", str(root / "runtime")], cwd=project)
                if result.returncode == 0:
                    raise ValueError("Packaged CLI accepted altered manifest")
            finally:
                manifest.write_bytes(original)
        runtime_env = dict(os.environ)
        if platform == "linux":
            runtime_env["LD_LIBRARY_PATH"] = str(root / "runtime")
        server = "llama-server.exe" if platform == "windows" else "llama-server"
        subprocess.run([str(root / "runtime" / server), "--version"],
                       cwd=root / "runtime", env=runtime_env, check=True, timeout=30)
        files = [{"path": p.relative_to(root).as_posix(), "bytes": p.stat().st_size,
                  "sha256": digest(p)} for p in sorted(root.rglob("*")) if p.is_file()]
        write_json(root / "build.json", {
            "product_version": version, "source_commit": source_commit, "target": target,
            "runtime_revision": REVISION, "runtime_source_commit": UPSTREAM_COMMIT,
            "runtime_archive_sha256": expected, "runtime_manifest_sha256": manifest_hash,
            "signing": "unsigned; not notarized", "status": "unqualified candidate; not for public distribution",
            "files": files,
        })
        if platform == "windows":
            package = output / (name + ".zip")
            with zipfile.ZipFile(package, "x", compression=zipfile.ZIP_DEFLATED) as z:
                for p in sorted(root.rglob("*")):
                    if p.is_file():
                        z.write(p, name + "/" + p.relative_to(root).as_posix())
        else:
            package = output / (name + ".tar.gz")
            with tarfile.open(package, "x:gz") as tar:
                tar.add(root, arcname=name)
        # Exercise the exact archive that will be retained, rather than only
        # the staging folder. Extraction here is of our own verified output.
        with tempfile.TemporaryDirectory(prefix="tinybuilder unpack ") as unpacked:
            destination = Path(unpacked)
            if platform == "windows":
                with zipfile.ZipFile(package) as z:
                    z.extractall(destination)
            else:
                with tarfile.open(package, "r:gz") as tar:
                    tar.extractall(destination, filter="data")
            installed = destination / name
            for record in files:
                p = installed / record["path"]
                if p.stat().st_size != record["bytes"] or digest(p) != record["sha256"]:
                    raise ValueError("Unpacked file hash mismatch")
            project = destination / "separate project"
            project.mkdir()
            probe = project / "probe.txt"
            probe.write_text("unpacked-smoke-marker", encoding="utf-8")
            result = subprocess.check_output(
                [str(installed / binary), "app", "--project", str(project)],
                input="\n/cat probe.txt\n/quit\n", text=True, encoding="utf-8",
                cwd=project, timeout=30)
            if "Model-free mode" not in result or "unpacked-smoke-marker" not in result:
                raise ValueError("Unpacked first launch failed")
            subprocess.run([str(installed / binary), "doctor", "--project", str(project),
                            "--runtime", str(installed / "runtime")],
                           cwd=project, check=True, timeout=30)
            shutil.rmtree(installed)
            if list(project.iterdir()) != [probe] or probe.read_text() != "unpacked-smoke-marker":
                raise ValueError("Project changed during package lifecycle")
        write_json(output / "artifact.json", {
            "name": package.name, "bytes": package.stat().st_size, "sha256": digest(package),
            "source_commit": source_commit, "target": target,
        })


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", required=True, choices=TARGETS)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    build(args.target, args.source_commit, args.output.resolve())
