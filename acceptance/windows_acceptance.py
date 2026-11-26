"""Run packaged Windows acceptance and retain a single evidence directory."""
import argparse
import json
import os
from pathlib import Path
import platform
from queue import Empty, Queue
import subprocess
import sys
from tempfile import TemporaryDirectory
from threading import Thread
from time import monotonic, sleep
from zipfile import ZipFile

from qualify_packaged_read import check_regular, digest, safe_path, verify_package

TARGET = "x86_64-pc-windows-msvc"


def unpack(archive, manifest, commit, archive_hash, destination):
    check_regular(archive)
    artifact = json.loads(manifest.read_text(encoding="utf-8"))
    if (archive.suffix != ".zip" or artifact["name"] != archive.name
            or artifact["source_commit"] != commit or artifact["target"] != TARGET
            or artifact["bytes"] != archive.stat().st_size
            or artifact["sha256"] != archive_hash or digest(archive) != archive_hash):
        raise ValueError("Windows archive identity mismatch")
    with ZipFile(archive) as source:
        seen = set()
        for entry in source.infolist():
            member = safe_path(entry.filename)
            if (len(member.parts) < 2 or member.parts[0] != archive.stem
                    or entry.is_dir() or entry.filename.casefold() in seen):
                raise ValueError("Unexpected ZIP member")
            seen.add(entry.filename.casefold())
        source.extractall(destination)
    package = destination / archive.stem
    build, binary = verify_package(package, archive, manifest, commit)
    if build["runtime_revision"] != "b12359":
        raise ValueError("Expected pinned b12359 runtime")
    return package, build, binary


def powershell(system, command):
    executable = system / "WindowsPowerShell/v1.0/powershell.exe"
    return subprocess.check_output(
        [executable, "-NoProfile", "-NonInteractive", "-Command",
         "$ErrorActionPreference = 'Stop'; [Console]::OutputEncoding = [Text.Encoding]::UTF8; " + command],
        encoding="utf-8", timeout=20,
    ).strip()


def run_cli(binary, args, project, env, stdin=None, *, returns=0):
    result = subprocess.run(
        [binary, *args], input=stdin, text=True, encoding="utf-8",
        capture_output=True, cwd=project, env=env, timeout=30,
    )
    if result.returncode != returns:
        raise ValueError(f"Product command failed: {args[0] if args else 'first launch'} (exit {result.returncode})")
    return result.stdout


def model_free(binary, runtime, project, env):
    version = run_cli(binary, ["--version"], project, env).strip()
    doctor = run_cli(binary, ["doctor", "--project", project, "--runtime", runtime], project, env)
    if "Runtime inventory verified" not in doctor:
        raise ValueError("Doctor did not verify the runtime")
    output = run_cli(binary, [], project, env, f"{project}\n\n/cat demo.py\n/search demo_total\n/inspect demo_total\n/help\n/quit\n")
    expected = ("Model-free mode", "File read verified: demo.py", "demo.py:1:", "Deterministic source selection:", "/quit")
    if any(marker not in output for marker in expected):
        raise ValueError("Model-free first launch or command check failed")
    for flag in ("--allow-write", "--allow-exec"):
        run_cli(binary, [flag], project, env, returns=2)
    return {"version": version, "doctor": True, "first_launch": True, "read_search_inspect": True, "write_exec_denied": True}


def listeners(system, pid=None):
    output = subprocess.check_output([system / "netstat.exe", "-ano"], timeout=15)
    rows = (line.split() for line in output.splitlines())
    return {
        fields[1].decode("ascii")
        for fields in rows if len(fields) == 5 and fields[0] == b"TCP"
        and fields[2] in {b"0.0.0.0:0", b"[::]:0"}
        and (pid is None or fields[-1] == str(pid).encode("ascii"))
    }


def lifecycle(binary, model, project, env, system, *, force):
    start = monotonic()
    with subprocess.Popen(
        [binary, "app", "--project", project, "--model", model], cwd=project, env=env,
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, encoding="utf-8", errors="replace",
    ) as process:
        lines = Queue()

        def read_ready():
            for line in process.stdout:
                if line.startswith("Ready."):
                    lines.put(monotonic())
            lines.put(None)

        Thread(target=read_ready, daemon=True).start()
        try:
            try:
                ready = lines.get(timeout=200)
            except Empty:
                raise ValueError("Packaged runtime readiness timed out") from None
            if ready is None:
                raise ValueError("Packaged runtime exited before authenticated readiness")
            child = powershell(system, f"""
                $children = @(Get-CimInstance Win32_Process -Filter "ParentProcessId = {process.pid} AND Name = 'llama-server.exe'")
                if ($children.Count -ne 1) {{ throw 'Expected one managed runtime child' }}
                $child = Get-Process -Id $children[0].ProcessId
                @{{pid = $child.Id; peak_bytes = $child.PeakWorkingSet64}} | ConvertTo-Json -Compress
            """)
            child = json.loads(child)
            pid = int(child["pid"])
            bound = listeners(system, pid)
            if len(bound) != 1 or not next(iter(bound)).startswith("127.0.0.1:"):
                raise ValueError("Expected a single loopback listener owned by the managed runtime")
            if force:
                process.kill()
            else:
                process.stdin.write("/quit\n")
                process.stdin.flush()
            exit_code = process.wait(timeout=10)
            if not force and exit_code != 0:
                raise ValueError("Normal quit failed")
            deadline = monotonic() + 10
            while True:
                child_count = powershell(system, f"@(Get-Process -Id {pid} -ErrorAction SilentlyContinue).Count")
                if child_count == "0" and not (bound & listeners(system)):
                    break
                if monotonic() >= deadline:
                    raise ValueError("Managed runtime or listener remained after app exit")
                sleep(0.2)
            return {
                "authenticated_ready_ms": round((ready - start) * 1000),
                "runtime_peak_working_set_bytes": child["peak_bytes"],
                "loopback_only": True, "child_exited": True, "listener_removed": True,
            }
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=10)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--artifact-json", type=Path, required=True)
    parser.add_argument("--expected-commit", required=True)
    parser.add_argument("--expected-archive-sha256", required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--expected-model-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dev-host", action="store_true", help="Allow a connected development-host rehearsal")
    args = parser.parse_args()
    if os.name != "nt":
        parser.error("Windows acceptance requires Windows")
    output = args.output.resolve()
    output.mkdir()
    system = Path(os.environ["SystemRoot"]) / "System32"
    archive, manifest, model = (p.absolute() for p in (args.archive, args.artifact_json, args.model))
    expected_model_hash = args.expected_model_sha256.lower()
    qualification = output / "qualification"
    report = {"status": "failed", "scope": "development_host" if args.dev_host else "windows_qa",
              "windows": platform.platform(), "review_required": ["clean host and standard user", "Windows security prompts"]}
    stage = "host"
    try:
        host = json.loads(powershell(system, """
            $principal = [Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent())
            @{
                active_adapters = @(Get-NetAdapter | Where-Object Status -eq Up).Count
                elevated = $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
                cpu = @((Get-CimInstance Win32_Processor).Name)
                ram_bytes = (Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory
            } | ConvertTo-Json -Compress
        """))
        report.update(host)
        if not args.dev_host and (host["active_adapters"] or host["elevated"]):
            raise ValueError("Disconnect networking and run as a standard user for clean Windows acceptance")
        stage = "model_identity"
        check_regular(model)
        if model.suffix.lower() != ".gguf" or digest(model) != expected_model_hash:
            raise ValueError("Model identity mismatch")
        with TemporaryDirectory(prefix="disposable acceptance ", dir=output) as temporary:
            scratch = Path(temporary)
            env = {**os.environ, "PATH": str(system), "TMP": str(scratch), "TEMP": str(scratch)}
            project = scratch / "read-only demo"
            project.mkdir()
            fixture = project / "demo.py"
            fixture.write_text("def demo_total(price, discount):\n    return price - discount\n", encoding="ascii")
            original = digest(fixture)
            stage = "package_identity"
            with TemporaryDirectory(prefix="package files ", dir=scratch) as extracted:
                package, build, binary = unpack(archive, manifest, args.expected_commit,
                                                args.expected_archive_sha256.lower(), Path(extracted))
                report.update({key: build[key] for key in (
                    "source_commit", "target", "runtime_revision", "runtime_archive_sha256", "runtime_manifest_sha256"
                )})
                report.update(archive_sha256=args.expected_archive_sha256.lower(), archive_bytes=archive.stat().st_size,
                              model_sha256=expected_model_hash, model_bytes=model.stat().st_size)
                stage = "model_free"
                report["model_free"] = model_free(binary, package / "runtime", project, env)
                stage = "normal_quit"
                report["normal_quit"] = lifecycle(binary, model, project, env, system, force=False)
                stage = "forced_exit"
                report["forced_exit"] = lifecycle(binary, model, project, env, system, force=True)
                stage = "qualification"
                gate = subprocess.run([
                    sys.executable, Path(__file__).with_name("qualify_packaged_read.py"),
                    "--package-root", package, "--archive", archive, "--artifact-json", manifest,
                    "--expected-commit", args.expected_commit, "--model", model,
                    "--expected-model-sha256", expected_model_hash, "--output", qualification,
                ], env=env)
                report["qualification_exit_code"] = gate.returncode
                if (qualification / "campaign.json").is_file():
                    campaign = json.loads((qualification / "campaign.json").read_text(encoding="utf-8"))
                    report["qualification"] = {key: campaign[key] for key in
                                                ("requested", "attempted", "passed", "not_run", "read_gate_passed")}
            stage = "preservation"
            report["preservation"] = {
                "app_copy_removed": not package.exists(),
                "project_unchanged": list(project.iterdir()) == [fixture] and digest(fixture) == original,
                "model_unchanged": digest(model) == expected_model_hash,
            }
            if not all(report["preservation"].values()):
                raise ValueError("Package removal or project/model preservation failed")
            if gate.returncode != 0 or not report.get("qualification", {}).get("read_gate_passed"):
                stage = "qualification"
                raise ValueError("Packaged read gate failed")
        report["status"] = "passed"
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        report["failed_stage"] = stage
        print(f"{stage}: {error}", file=sys.stderr)
    finally:
        (output / "windows-acceptance.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Windows acceptance {report['status']}: {output / 'windows-acceptance.json'}")
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
