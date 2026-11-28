"""Compare the seven frozen strategies on independent public source."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
from statistics import median
import subprocess

from .identity import sha256_file
from .public_retrieval_measure import STRATEGIES
from .retrieval_confirmation import DISTRACTORS, REPOSITORIES, expected_inventory, snapshot
from .retrieval_confirmation_tasks import cases


# Judge the editable loci separately from read-only evidence in cross-file cases.
# These are reviewer designations for retrieval scoring, not prescribed changes.
SUPPORT = {
    "hold-path": ("routes/web.php", "app/Http/Controllers/ReservationController.php"),
    "sweep": ("routes/console.php",),
    "checksum": ("src/observatory/protocol/crc.py",),
    "retention": ("src/observatory/storage/retention.py",),
    "suppression": ("src/observatory/alerts/routing.py",),
    "frame": ("src/net/listener.rs",),
    "order": ("src/worker/scheduler.rs",),
    "retry": ("src/config/defaults.rs",),
    "vault-binding": ("app/Http/Controllers/DepositController.php", "app/Providers/ArchiveServiceProvider.php"),
    "destination": ("app/Storage/ColdVault.php",),
    "dry-job": ("routes/console.php",),
    "humidity-display": ("app/Models/Plant.php", "app/Models/Moisture.php"),
    "withdrawal-policy": ("app/Http/Controllers/WithdrawalController.php",),
    "oversize-charge": ("app/Http/Controllers/QuoteController.php",),
    "closing-time": ("app/Console/Commands/DailyClose.php",),
}

AMBIGUOUS_DISTRACTORS = {
    "charge-count": {"app/Services/Seating/SeatAllocator.php"},
    "args": {"src/observatory/render/options.py"},
    "presentation": {"src/observatory/cli/options.py"},
    "principal": {"src/cache/lease.rs"},
    "stale-cache": {"src/security/lease.rs"},
    "oversize-charge": {"app/Services/Accounting/RateCard.php"},
    "destination": {"app/Storage/LegacyVault.php"},
}


def grade(repo, task, required, observation):
    files = observation["files"]
    support = set(SUPPORT.get(task, ()))
    targets = required.keys() - support
    touched = {file["path"] for file in files}
    unexpected = touched - required.keys()
    known_distractors = unexpected & (DISTRACTORS[repo] | AMBIGUOUS_DISTRACTORS.get(task, set()))
    delivered = {
        file["path"] for file in files
        if file["path"] in required and (
            file["complete"] if required[file["path"]] is None
            else file["first_line"] <= required[file["path"]] <= file["last_line"]
        )
    }
    return {
        "repository": repo, "task": task,
        "required": required, "support": sorted(support),
        "delivered_paths": sorted(required.keys() & touched),
        "delivered_evidence": sorted(delivered),
        "edit_loci_delivered": len(delivered & targets),
        "edit_loci_total": len(targets), "support_delivered": len(delivered & support),
        "first_relevant_rank": next((i for i, file in enumerate(files, 1) if file["path"] in required), None),
        "known_distractors": sorted(known_distractors),
        "unjudged_paths": sorted(unexpected - known_distractors),
        "truncated_paths": [file["path"] for file in files if not file["complete"]],
        "context_bytes": sum(file["bytes"] for file in files),
        "estimated_source_tokens": sum((file["bytes"] + 3) // 4 for file in files),
        "context_incomplete": observation.get("incomplete"),
        "files": files,
    }


def summarize(rows):
    positive = [row for row in rows if row["required"]]
    negative = [row for row in rows if not row["required"]]
    multi = [row for row in positive if len(row["required"]) > 1]
    spans = [(row, path) for row in positive
             for path, line in row["required"].items() if line is not None]
    selected = sum(len(row["files"]) for row in positive)
    hits = sum(len(row["delivered_paths"]) for row in positive)
    return {
        "complete_tasks": sum(len(row["required"]) == len(row["delivered_evidence"]) for row in positive),
        "positive_tasks": len(positive), "file_hits": hits,
        "required_paths": sum(len(row["required"]) for row in positive),
        "delivered_evidence": sum(len(row["delivered_evidence"]) for row in positive),
        "span_hits": sum(path in row["delivered_evidence"] for row, path in spans),
        "required_spans": len(spans),
        "edit_loci_delivered": sum(row["edit_loci_delivered"] for row in positive),
        "edit_loci_total": sum(row["edit_loci_total"] for row in positive),
        "support_delivered": sum(row["support_delivered"] for row in positive),
        "support_total": sum(len(row["support"]) for row in positive),
        "complete_multifile": sum(len(row["required"]) == len(row["delivered_evidence"]) for row in multi),
        "multifile_tasks": len(multi),
        "ranking_precision": hits / selected if selected else None,
        "mean_reciprocal_rank": sum(1 / row["first_relevant_rank"] for row in positive
                                    if row["first_relevant_rank"]) / len(positive),
        "no_evidence_abstentions": sum(not row["files"] for row in negative),
        "no_evidence_tasks": len(negative),
        "positive_abstentions": sum(not row["files"] for row in positive),
        "truncated_files": sum(len(row["truncated_paths"]) for row in rows),
        "explicitly_incomplete": sum(bool(row["context_incomplete"]) for row in rows),
        "essential_files_truncated": sum(
            path in row["required"] for row in positive for path in row["truncated_paths"]
        ),
        "silent_truncations": sum(
            bool(row["truncated_paths"]) and not row["context_incomplete"] for row in rows
        ),
        "unauthorized_paths_returned": sum(len(row["unauthorized_paths_returned"]) for row in rows),
        "known_distractor_files": sum(len(row["known_distractors"]) for row in rows),
        "unjudged_files": sum(len(row["unjudged_paths"]) for row in rows),
        "context_bytes": sum(row["context_bytes"] for row in rows),
        "estimated_source_tokens": sum(row["estimated_source_tokens"] for row in rows),
        "median_latency_us": median(row["median_us"] for row in rows),
        "peak_rss_bytes": max((row["peak_rss_bytes"] for row in rows if row["peak_rss_bytes"] is not None),
                              default=None),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("root", "lab", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve(strict=True)
    output = args.output.resolve()
    if output.is_relative_to(root):
        parser.error("Keep reports outside all confirmation source roots")
    before = snapshot(root)
    if before != expected_inventory():
        parser.error("Confirmation sources differ from the frozen inventory")
    tasks = list(cases())
    labels = {repo: sorted(paths) for repo, paths in DISTRACTORS.items()}
    identity = json.dumps(
        {"inventory": before, "tasks": tasks, "support": SUPPORT, "distractors": labels,
         "ambiguous_distractors": {task: sorted(paths) for task, paths in AMBIGUOUS_DISTRACTORS.items()}},
        sort_keys=True,
    ).encode()
    lab = args.lab.resolve(strict=True)
    report = {"lab_sha256": sha256_file(lab), "confirmation_sha256": sha256(identity).hexdigest(),
              "file_counts": {repo: len(files) for repo, files in REPOSITORIES.items()},
              "suites": {"laravel": [repo for repo in REPOSITORIES if repo not in ("dispatch", "observatory")],
                         "other": ["dispatch", "observatory"]}, "strategies": {}}
    for strategy in STRATEGIES:
        rows = []
        for repo, task, prompt, required in tasks:
            project = root / repo
            samples = json.loads(subprocess.check_output(
                [lab, "--project", project, "--strategy", strategy, "--", prompt],
                cwd=project, stdin=subprocess.DEVNULL, timeout=15,
            ))
            first = samples[0]
            if any((sample["status"], sample["files"], sample.get("incomplete"))
                   != (first["status"], first["files"], first.get("incomplete")) for sample in samples):
                raise ValueError(f"Unstable evidence for {strategy}/{repo}/{task}")
            row = grade(repo, task, required, first)
            row["unauthorized_paths_returned"] = sorted(
                {file["path"] for file in first["files"]} - REPOSITORIES[repo].keys()
            )
            row["samples_us"] = [sample["elapsed_us"] for sample in samples]
            row["median_us"] = median(row["samples_us"])
            row["peak_rss_bytes"] = max(
                (sample["peak_rss_bytes"] for sample in samples if sample["peak_rss_bytes"] is not None),
                default=None,
            )
            rows.append(row)
        report["strategies"][strategy] = {
            "summary": summarize(rows),
            "by_suite": {
                label: summarize([row for row in rows if row["repository"] in repositories])
                for label, repositories in report["suites"].items()
            },
            "tasks": rows,
        }
    report["source_unchanged"] = snapshot(root) == before
    with output.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")
    return int(not report["source_unchanged"])


if __name__ == "__main__":
    raise SystemExit(main())
