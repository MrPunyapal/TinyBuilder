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

from runtime_evidence import download, inspect, CPU_ARCHIVES, REVISION

ROOT = Path(__file__).resolve().parents[1]
TARGETS = {
    "x86_64-pc-windows-msvc": ("windows", "x64"),
    "aarch64-apple-darwin": ("macos", "arm64"),
    "x86_64-unknown-linux-gnu": ("linux", "x64"),
}
UPSTREAM_COMMIT = "a7a98e0fffed794396b3fbad4dcdbbc184963645"


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write_json(path, value):
    path.write_bytes((json.dumps(value, sort_keys=True, indent=2) + "\n").encode())


def selected(name, platform):
    return (name == ("llama-server.exe" if platform == "windows" else "llama-server")
            or name == "LICENSE" or name.startswith("LICENSE-")
            or (platform == "windows" and name.endswith(".dll"))
            or (platform == "linux" and name.endswith(".so"))
            or (platform == "macos" and (name.endswith(".dylib") or name in {
                "ggml-common.h", "ggml-metal-impl.h", "ggml-metal.metal"})))


def stage(archive, target, runtime):
    platform, arch = TARGETS[target]
    filename, expected = CPU_ARCHIVES[(platform, arch)]
    records = inspect(archive, expected)
    runtime.mkdir(parents=True, exist_ok=False)
    server = "llama-server.exe" if platform == "windows" else "llama-server"
    files = {}
    deps = []
    with zipfile.ZipFile(archive) as z:
        for row in records:
            name = PurePosixPath(row["path"]).name
            if not selected(name, platform):
                continue
            prefix = "" if platform == "windows" else "build/bin/"
            if (row["kind"] != "regular" or row["path"] != prefix + name
                    or not re.fullmatch(r"[A-Za-z0-9_+.-]{1,128}", name)
                    or name.casefold() in {n.casefold() for n in files}):
                raise ValueError("Unexpected selected runtime member")
            dst = runtime / name
            with z.open(row["path"]) as src, dst.open("xb") as out:
                shutil.copyfileobj(src, out)
            if digest(dst) != row["sha256"]:
                raise ValueError("Staged runtime digest mismatch")
            dst.chmod(0o755 if name == server else 0o644)
            files[name] = row["sha256"]
            if name != server and not name.startswith("LICENSE"):
                deps.append(name)
    if "LICENSE" not in files and platform == "windows":
        data = (ROOT / "acceptance" / "llama-b6500-LICENSE").read_bytes().replace(b"\r\n", b"\n")
        blob = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        if blob != "acb96ce78e0486e9dc7602cdcdd2f491c34f335a":
            raise ValueError("Upstream license blob mismatch")
        (runtime / "LICENSE").write_bytes(data)
        files["LICENSE"] = digest(runtime / "LICENSE")
    if not {server, "LICENSE", "LICENSE-curl", "LICENSE-httplib",
            "LICENSE-jsonhpp", "LICENSE-linenoise"} <= files.keys() or not deps:
        raise ValueError("Incomplete runtime payload")
    write_json(runtime / "runtime-manifest.json", {
        "schema": 1, "revision": REVISION, "os": platform, "architecture": arch,
        "backend": "cpu", "executable": server, "archive": filename,
        "archive_sha256": expected, "native_dependencies": sorted(deps), "files": files,
    })
    return digest(runtime / "runtime-manifest.json")


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
