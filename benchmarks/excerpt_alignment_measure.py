"""Measure frozen excerpt-alignment development cases without inference."""

import argparse
import json
import subprocess
from pathlib import Path
from statistics import median
from tempfile import TemporaryDirectory

from .excerpt_alignment_cases import fixtures
from .identity import sha256_file


def measure(lab, root, task, relative, expected_line, sources, flags):
    result = json.loads(subprocess.check_output(
        [lab, "--project", root, "--strategy", "normalized", *flags, "--", task],
        cwd=root, stdin=subprocess.DEVNULL, timeout=15,
    ))
    first = result[0]
    assert all(sample["files"] == first["files"] and sample.get("incomplete") == first.get("incomplete")
               for sample in result), "Nondeterministic delivery"
    seen = first["files"]
    assert all(file["path"] in sources and file["bytes"] <= 12 * 1024 for file in seen)
    assert not any(not file["complete"] for file in seen) or first["incomplete"]
    target = next((file for file in seen if file["path"] == relative), None)
    covered = bool(target and target["first_line"] <= expected_line <= target["last_line"])
    required_bytes = len(sources[relative].splitlines(keepends=True)[expected_line - 1].encode())
    size = sum(file["bytes"] for file in seen)
    return {
        "files": seen, "incomplete": first.get("incomplete"),
        "span_delivered": covered, "context_bytes": size,
        "bytes_outside_required_line": size - required_bytes * covered,
        "timings_us": [sample["elapsed_us"] for sample in result],
        "peak_rss_bytes": max((sample["peak_rss_bytes"] for sample in result
                               if sample["peak_rss_bytes"] is not None), default=None),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lab", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    lab = args.lab.resolve(strict=True)
    report = {"lab_sha256": sha256_file(lab), "cases": []}
    with TemporaryDirectory() as directory:
        for index, (name, task, target, expected_line, sources) in enumerate(fixtures()):
            root = Path(directory) / name
            root.mkdir()
            for name_it, text in sources.items():
                (root / name_it).write_bytes(text.encode())
            arms = (("baseline", []), ("aligned", ["--align-excerpts"]),
                    ("code_weighted", ["--align-excerpts", "--prefer-code-anchors"]))
            row = {"case": name, "target": target, "expected_line": expected_line}
            timings = {key: [] for key, _ in arms}
            # Alternate arms and cache order across cases and three process runs.
            for repeat in range(3):
                for key, flags in arms[::1 if (index + repeat) % 2 == 0 else -1]:
                    results = measure(lab, root, task, target, expected_line, sources, flags)
                    timings[key].extend(results.pop("timings_us"))
                    if key in row:
                        assert row[key]["files"] == results["files"]
                        rss = [value for value in (results["peak_rss_bytes"], row[key]["peak_rss_bytes"])
                               if value is not None]
                        results["peak_rss_bytes"] = max(rss, default=None)
                    row[key] = results
            for key, samples in timings.items():
                row[key]["timings_us"] = samples
            before = row["baseline"]
            for key in ("aligned", "code_weighted"):
                after = row[key]
                assert [file["path"] for file in before["files"]] == [file["path"] for file in after["files"]]
                assert [file["complete"] for file in before["files"]] == [file["complete"] for file in after["files"]]
                if all(file["complete"] for file in before["files"]):
                    assert before["files"] == after["files"]
            assert all((root / path).read_bytes() == value.encode() for path, value in sources.items())
            report["cases"].append(row)
    report["summary"] = {
        key: {
            "complete_spans": sum(row[key]["span_delivered"] for row in report["cases"]),
            "context_bytes": sum(row[key]["context_bytes"] for row in report["cases"]),
            "bytes_outside_required_line": sum(row[key]["bytes_outside_required_line"] for row in report["cases"]),
            "median_case_us": median(median(row[key]["timings_us"]) for row in report["cases"]),
        } for key in ("baseline", "aligned", "code_weighted")
    }
    baseline = report["summary"]["baseline"]["median_case_us"]
    report["median_latency_overhead_pct"] = {
        key: 100 * (report["summary"][key]["median_case_us"] / baseline - 1)
        for key in ("aligned", "code_weighted")
    }
    with args.output.open("x", encoding="utf-8") as output:
        json.dump(report, output, indent=2)
        output.write("\n")
    print(json.dumps(report["summary"]))


if __name__ == "__main__":
    main()
