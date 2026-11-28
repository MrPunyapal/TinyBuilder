"""Score Rust lab retrieval against the separate public campaign plan."""
import argparse
import json
from pathlib import Path
from statistics import median
import subprocess

from .identity import sha256_file
from .public_proposal_campaign import MANIFEST, inspect, plan


STRATEGIES = ("baseline", "threshold", "expanded", "caseless", "normalized", "dependencies", "fallback")


def summarize(rows):
    selected = sum(len(row["files"]) for row in rows)
    recalled = sum(row["required_recalled"] for row in rows)
    return {
        "tasks": len(rows),
        "complete_tasks": sum(row["required_recalled"] == row["required_total"] for row in rows),
        "required_recalled": recalled,
        "required_total": sum(row["required_total"] for row in rows),
        "files_selected": selected,
        "target_precision": recalled / selected if selected else None,
        "non_target_files": sum(row["non_target_files"] for row in rows),
        "non_target_bytes": sum(row["non_target_bytes"] for row in rows),
        "context_bytes": sum(row["bytes"] for row in rows),
        "median_task_latency_us": median(row["median_latency_us"] for row in rows),
        "multi_file_complete": sum(row["required_total"] > 1 and row["required_recalled"] == row["required_total"] for row in rows),
        "multi_file_total": sum(row["required_total"] > 1 for row in rows),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--lab", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.absolute()
    output = args.output.resolve()
    resolved = root.resolve(strict=True)
    if output.is_relative_to(resolved):
        parser.error("Keep the evaluator report outside the campaign")
    before = inspect(root)
    tasks = plan()["tasks"]
    if before["counts"]["no_change"] != len(tasks):
        parser.error("Use a pristine public source campaign")
    report = {"condition": "public-source-only-retrieval", "lab_sha256": sha256_file(args.lab),
              "plan_sha256": sha256_file(root / MANIFEST), "strategies": {}}
    for strategy in STRATEGIES:
        rows = []
        for task in tasks:
            # Only repository source and the public task reach the retriever.
            result = subprocess.check_output([args.lab, "--project", root / task["project"],
                                              "--strategy", strategy, "--", task["prompt"]],
                                             stdin=subprocess.DEVNULL, timeout=15)
            samples = json.loads(result)
            files = samples[0]["files"]
            if any(sample["files"] != files for sample in samples):
                raise ValueError("Retrieval selected different files across repetitions")
            expected = set(task["allowed_edit_paths"])
            complete = {file["path"] for file in files if file["complete"]}
            rows.append({"task": task["task"], "files": files, "required_total": len(expected),
                         "required_recalled": len(expected & complete),
                         "missing_targets": sorted(expected - complete),
                         "non_target_files": sum(file["path"] not in expected for file in files),
                         "non_target_bytes": sum(file["bytes"] for file in files if file["path"] not in expected),
                         "bytes": sum(file["bytes"] for file in files),
                         "median_latency_us": median(sample["elapsed_us"] for sample in samples)})
        report["strategies"][strategy] = {"summary": summarize(rows), "tasks": rows}
    report["source_unchanged"] = inspect(root) == before
    with output.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")
    return int(not report["source_unchanged"])


if __name__ == "__main__":
    raise SystemExit(main())
