"""Call platform-owned checks only when their actual inputs are present."""
import argparse
import importlib.metadata
import os
from pathlib import Path
import re
import subprocess
import sys

TESTS = {
    "windows": ("packaging/windows/verification", "test_payload.py"),
    "macos": ("packaging/macos", "test_verify_runtime.py"),
    "linux": ("packaging/linux", "test_verify_runtime.py"),
}
MAC_FIXTURE = Path("packaging/macos/native_fixture_smoke.sh")
MAC_LOCK = Path("acceptance/locks/macos-arm64-py312.txt")
MAC_PIN = "6.22.2"


def run_tests(root, target):
    relative, sentinel = TESTS[target]
    folder = root / relative
    if not (folder / sentinel).is_file():
        return "BLOCKED (owner test files absent)"
    command = [sys.executable, "-m", "unittest", "discover", "-s", relative]
    if target != "windows":
        command += ["-p", "test_*.py"]
    result = subprocess.run(command + ["-v"], cwd=root, check=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, encoding="utf-8", errors="replace", timeout=600)
    print(result.stdout)
    count = re.search(r"^Ran (\d+) tests? in ", result.stdout, re.MULTILINE)
    if not count or int(count.group(1)) == 0:
        raise RuntimeError("Packaging suite ran no tests")
    if re.search(r"^OK \(skipped=", result.stdout, re.MULTILINE):
        return "PARTIAL (unit suite contains skips; see counts above)"
    return "PASS (deterministic packaging unit tests only; " + count.group(1) + " executed)"


def run_fixture(root):
    if not (root / MAC_FIXTURE).is_file():
        return "BLOCKED (owner fixture absent)"
    if not (root / MAC_LOCK).is_file():
        return "BLOCKED (reviewed hash-locked build dependencies absent)"
    subprocess.run([sys.executable, "-m", "pip", "--isolated", "install",
                    "--index-url", "https://pypi.org/simple", "--require-hashes",
                    "--only-binary=:all:", "-r", str(MAC_LOCK)],
                   cwd=root, check=True, timeout=600)
    if importlib.metadata.version("pyinstaller") != MAC_PIN:
        raise RuntimeError("macOS fixture requires owner's exact PyInstaller pin")
    subprocess.run(["bash", str(MAC_FIXTURE)], cwd=root, check=True, timeout=900)
    return "PASS (test-double DMG/relocation only; NOT real runtime or release)"


def run(root, target):
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    rows = [("Candidate", sha), ("Platform", target)]
    try:
        rows.append(("Packaging unit tests", run_tests(root, target)))
        rows.append(("macOS native fixture", run_fixture(root) if target == "macos" else "NOT APPLICABLE"))
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        rows.append(("Packaging checks", "FAIL (see job log)"))
        raise
    finally:
        rows.extend([("Real standalone artifact", "BLOCKED (integrated trusted inputs required)"),
                     ("Gate A / B / C", "NOT QUALIFIED by hosted deterministic checks")])
        summary = "\n".join(f"- {name}: {status}" for name, status in rows) + "\n"
        print(summary)
        if os.environ.get("GITHUB_STEP_SUMMARY"):
            with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as stream:
                stream.write("## Native packaging evidence\n" + summary)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", choices=TESTS)
    run(Path.cwd(), parser.parse_args().target)
