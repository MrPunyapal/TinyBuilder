"""Compare model-free, warm in-process operations; no real project is touched."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tinybuilder.tools import LocalTools


def measure(count, operation):
    durations = []
    for _ in range(count):
        start = time.perf_counter_ns()
        operation()
        durations.append(time.perf_counter_ns() - start)
    durations.sort()
    return {"trials": count, "p50": durations[(count - 1) // 2],
            "p95": durations[(count * 95 + 99) // 100 - 1]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rust_benchmark", type=Path)
    args = parser.parse_args()
    binary = args.rust_benchmark.resolve(strict=True)
    with tempfile.TemporaryDirectory(prefix="tinybuilder-file-bench-") as directory:
        root = Path(directory)
        for i in range(20):
            folder = root / f"folder-{i:02}"
            folder.mkdir()
            for j in range(50):
                (folder / f"source-{j:02}.txt").write_text(
                    "ordinary source line\n" * 128, encoding="utf-8")
        (root / "probe.txt").write_bytes(b"tinybuilder-bench-marker\n")
        (root / "patch.txt").write_bytes(b"original\n")
        python = LocalTools(root)
        expected = "probe.txt:1: tinybuilder-bench-marker"
        assert python.call("read_file", {"path": "probe.txt"}) == "tinybuilder-bench-marker\n"
        assert python.call("search_files", {"query": "tinybuilder-bench-marker"}).replace("\\", "/") == expected
        result = {"unit": "ns", "files": 1002, "cache": "warm; OS cache not controlled",
                  "python": {"read": measure(1000, lambda: python.call("read_file", {"path": "probe.txt"})),
                             "search": measure(20, lambda: python.call("search_files", {"query": "tinybuilder-bench-marker"}))}}
        completed = subprocess.run([str(binary), str(root)], check=True, text=True,
                                   capture_output=True, timeout=180)
        result["rust"] = json.loads(completed.stdout)
        assert (root / "patch.txt").read_bytes() == b"original\n"
        assert (root / "probe.txt").read_bytes() == b"tinybuilder-bench-marker\n"
        # Patch+restore is native-only: Python whole-file replacement has
        # different safety semantics and is not a comparable latency number.
        print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
