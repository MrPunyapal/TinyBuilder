"""Measure one review-only lab attempt per public source-only campaign task."""
import argparse
from collections import Counter
import json
from pathlib import Path
import subprocess
from threading import Event, Thread
from time import monotonic

from .identity import sha256_file
from .laravel_pilot import monitor
from .public_proposal_campaign import MANIFEST, inspect, plan


METRIC_PREFIX = "Proposal metrics: "
STOP_STATUSES = {"lab_timeout", "approval_boundary_unverified", "startup_failed", "lab_failed"}


def _metrics(output):
    events = {}
    for line in output.splitlines():
        if line.startswith(METRIC_PREFIX):
            event = json.loads(line[len(METRIC_PREFIX):])
            phase = event.pop("phase")
            if phase not in {"retrieval", "startup", "proposal", "approval"} or phase in events:
                raise ValueError("Unexpected lab metric phase")
            events[phase] = event
    return events


def measure(lab, runtime, model, project, task):
    argv = [lab, "--project", project, "--runtime", runtime, "--model", model,
            "edit", "--allow-write", "--selective-context", "--proposal-metrics"]
    for path in task["allowed_edit_paths"]:
        argv.extend(("--allowed-edit-path", path))
    argv.extend(("--", task["prompt"]))
    samples, stop = [], Event()
    start = monotonic()
    # EOF cannot grant the lab's exact-patch confirmation.
    with subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                          stderr=subprocess.DEVNULL, encoding="utf-8") as process:
        sampler = Thread(target=monitor, args=(process, stop, samples), daemon=True)
        sampler.start()
        timed_out = False
        try:
            output, _ = process.communicate(timeout=155)
        except subprocess.TimeoutExpired:
            process.kill()
            output, _ = process.communicate()
            timed_out = True
        finally:
            stop.set()
            sampler.join(timeout=12)
    row = {"task": task["task"], "wall_ms": round((monotonic() - start) * 1000),
           "exit_code": process.returncode, "events": _metrics(output),
           "combined_peak_sampled_bytes": max((sample["combined"] for sample in samples), default=None),
           "server_peak_working_set_bytes": max((sample["server_peak"] for sample in samples), default=None)}
    for phase in ("retrieval", "startup", "proposal"):
        event = row["events"].get(phase)
        if event:
            row["status"] = event["status"]
    row["status"] = "lab_timeout" if timed_out else row.get("status", "lab_failed")
    if row["status"] in ("selected", "ready"):
        row["status"] = "lab_failed"
    selected = {item["path"] for item in row["events"].get("retrieval", {}).get("files", []) if item["complete"]}
    row["allowed_paths_retrieved"] = sorted(selected.intersection(task["allowed_edit_paths"]))
    approval = row["events"].get("approval", {}).get("status")
    if approval == "applied" or (row["status"] == "proposal_ready" and approval != "not_approved"):
        row["status"] = "approval_boundary_unverified"
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("root", "lab", "runtime", "model", "output"):
        parser.add_argument(f"--{key}", type=Path, required=True)
    parser.add_argument("--expected-model-sha256", required=True)
    parser.add_argument("--expected-runtime-manifest-sha256", required=True)
    args = parser.parse_args()
    root = args.root.absolute()
    output = args.output.resolve()
    resolved_root = root.resolve(strict=True)
    if output.is_relative_to(resolved_root) or resolved_root.is_relative_to(output):
        parser.error("Evidence must be outside the campaign source root")
    tasks = plan()["tasks"]
    before = inspect(root)
    if before["counts"]["no_change"] != len(tasks):
        parser.error("Use a pristine public campaign")
    lab, runtime, model = (path.resolve(strict=True) for path in (args.lab, args.runtime, args.model))
    manifest = runtime / "runtime-manifest.json"
    inputs = {"model_sha256": sha256_file(model), "runtime_manifest_sha256": sha256_file(manifest),
              "lab_sha256": sha256_file(lab), "plan_sha256": sha256_file(root / MANIFEST)}
    if (inputs["model_sha256"] != args.expected_model_sha256
            or inputs["runtime_manifest_sha256"] != args.expected_runtime_manifest_sha256):
        parser.error("Model or runtime identity mismatch")
    output.mkdir(exist_ok=False)
    evidence = {"condition": "public-source-only-review", **inputs, "planned_tasks": len(tasks),
                "planned_semantic_observations": before["planned_observations"],
                "attempted_semantic_observations": 0, "patches_applied": 0, "trials": []}
    report = output / "proposal-measurements.json"
    try:
        for task in tasks:
            row = measure(lab, runtime, model, root / task["project"], task)
            evidence["trials"].append(row)
            print(task["task"], row["status"], flush=True)
            if row["status"] in STOP_STATUSES:
                break
            report.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    finally:
        evidence["attempted_tasks"] = len(evidence["trials"])
        evidence["remaining_tasks"] = len(tasks) - len(evidence["trials"])
        evidence["counts"] = dict(Counter(row["status"] for row in evidence["trials"]))
        try:
            evidence["source_unchanged"] = inspect(root) == before
        except (OSError, ValueError):
            evidence["source_unchanged"] = False
        evidence["patches_applied"] = sum(
            row["events"].get("approval", {}).get("status") == "applied" for row in evidence["trials"])
        evidence["model_unchanged"] = sha256_file(model) == inputs["model_sha256"]
        evidence["runtime_manifest_unchanged"] = sha256_file(manifest) == inputs["runtime_manifest_sha256"]
        report.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    return int(evidence["remaining_tasks"] > 0 or not all(evidence[key] for key in (
        "source_unchanged", "model_unchanged", "runtime_manifest_unchanged")) or any(
        row["status"] in STOP_STATUSES for row in evidence["trials"]))


if __name__ == "__main__":
    raise SystemExit(main())
