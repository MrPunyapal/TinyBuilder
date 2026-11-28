"""Score the frozen model-free excerpt confirmation against the lab probe."""

import argparse
from dataclasses import asdict
from hashlib import sha256
import json
from math import ceil
from pathlib import Path
from statistics import median
import subprocess
from tempfile import TemporaryDirectory

from .excerpt_confirmation_cases import fixtures
from .identity import sha256_file


ARMS = {
    "baseline": (),
    "aligned": ("--align-excerpts",),
    "code_weighted": ("--align-excerpts", "--prefer-code-anchors"),
}
GATES = {"overall_span_recall_min_pct": 90, "median_overhead_max_pct": 20}
FILE_LIMIT = 4
FILE_BYTE_LIMIT = 12 * 1024


def snapshot(root):
    return {p.relative_to(root).as_posix(): sha256_file(p) for p in sorted(root.rglob("*")) if p.is_file()}


def evidence_bytes(file, source):
    """Expected bytes when the reported line interval is delivered in full."""
    lines = source.splitlines(keepends=True)
    first, last = file["first_line"], file["last_line"]
    if not 1 <= first <= last <= len(lines):
        return None
    return len("".join(lines[first - 1:last]).encode())


def score(first, sources, required):
    violations = []
    files = first["files"]
    if len(files) > FILE_LIMIT or len({file["path"] for file in files}) != len(files):
        violations.append("file_count_or_duplicate")
    if first["status"] != ("selected" if files else "no_context"):
        violations.append("inconsistent_status")
    validated = {}
    for file in files:
        path = file["path"]
        if path not in sources:
            violations.append(f"unauthorized_path:{path}")
            continue
        if not 0 < file["bytes"] <= FILE_BYTE_LIMIT:
            violations.append(f"byte_budget:{path}")
            continue
        if evidence_bytes(file, sources[path]) != file["bytes"]:
            violations.append(f"invalid_full_line_range:{path}")
            continue
        full = (file["first_line"], file["last_line"]) == (1, len(sources[path].splitlines()))
        if file["complete"] != full or (not full and not first.get("incomplete")):
            violations.append(f"inconsistent_completeness:{path}")
            continue
        validated[path] = file
    delivered = []
    for span in required:
        file = validated.get(span.path)
        delivered.append(bool(file and file["first_line"] <= span.first and file["last_line"] >= span.last))
    return {
        "status": first["status"],
        "files": files,
        "context_incomplete": first.get("incomplete"),
        "context_bytes": sum(file["bytes"] for file in files),
        "delivered": delivered,
        "violations": violations,
    }


def run_case(lab, root, case, sources, index):
    samples = {arm: [] for arm in ARMS}
    order = tuple(ARMS)
    for repeat in range(3):
        start = (index + repeat) % len(order)
        for arm in order[start:] + order[:start]:
            # Target annotations, roles and expected source lines stay here.
            output = subprocess.check_output(
                [lab, "--project", root, "--strategy", "normalized", *ARMS[arm], "--", case.prompt],
                cwd=root, stdin=subprocess.DEVNULL, timeout=15,
            )
            batch = json.loads(output)
            if len(batch) != 3:
                raise ValueError(f"Unexpected probe repetition count for {case.name}/{arm}")
            samples[arm].extend(batch)

    row = {"repository": case.repository, "case": case.name, "family": case.family,
           "required": [asdict(span) for span in case.required], "arms": {}}
    for arm, observations in samples.items():
        first = score(observations[0], sources, case.required)
        if any(score(observation, sources, case.required) != first for observation in observations[1:]):
            first["violations"].append("nondeterministic_delivery")
        rss = [observation["peak_rss_bytes"] for observation in observations
               if observation["peak_rss_bytes"] is not None]
        row["arms"][arm] = first | {
            "timings_us": [observation["elapsed_us"] for observation in observations],
            "peak_rss_bytes": max(rss, default=None),
        }
    baseline = row["arms"]["baseline"]["files"]
    paths_and_flags = [(f["path"], f["complete"]) for f in baseline]
    for arm in ("aligned", "code_weighted"):
        trial = row["arms"][arm]
        if [(f["path"], f["complete"]) for f in trial["files"]] != paths_and_flags:
            trial["violations"].append("ranking_or_completeness_changed")
        if [f for f in baseline if f["complete"]] != [f for f in trial["files"] if f["complete"]]:
            trial["violations"].append("complete_file_output_changed")
    return row


def summarise(rows, arm):
    trials = [row["arms"][arm] for row in rows]
    times = sorted(median(trial["timings_us"]) for trial in trials)
    doc_hits, doc_total = 0, 0
    for row, trial in zip(rows, trials):
        for span, hit in zip(row["required"], trial["delivered"]):
            if span["documentation"]:
                doc_hits += hit
                doc_total += 1
    rss = [trial["peak_rss_bytes"] for trial in trials if trial["peak_rss_bytes"] is not None]
    return {
        "complete_tasks": sum(all(trial["delivered"]) for trial in trials),
        "tasks": len(trials),
        "required_spans_delivered": sum(sum(trial["delivered"]) for trial in trials),
        "required_spans": sum(len(trial["delivered"]) for trial in trials),
        "documentation_spans_delivered": doc_hits,
        "documentation_spans": doc_total,
        "context_bytes": sum(trial["context_bytes"] for trial in trials),
        "truncated_excerpts": sum(not file["complete"] for trial in trials for file in trial["files"]),
        "median_us": median(times),
        "p95_us": times[ceil(0.95 * len(times)) - 1],
        "peak_rss_bytes": max(rss, default=None),
        "violations": sum(len(trial["violations"]) for trial in trials),
    }


def decide(rows, summary, source_unchanged, arm):
    before, after = summary["baseline"], summary[arm]
    lost_docs = []
    for row in rows:
        for span, baseline_hit, candidate_hit in zip(
            row["required"], row["arms"]["baseline"]["delivered"], row["arms"][arm]["delivered"]
        ):
            if span["documentation"] and baseline_hit and not candidate_hit:
                lost_docs.append({"case": row["case"], "span": span})
    overhead = 100 * (after["median_us"] / before["median_us"] - 1)
    checks = {
        "overall_required_span_recall": after["required_spans_delivered"] * 100
        >= GATES["overall_span_recall_min_pct"] * after["required_spans"],
        "complete_task_improvement": after["complete_tasks"] > before["complete_tasks"],
        "no_documentation_regression": not lost_docs,
        "short_controls_complete": all(
            all(row["arms"][arm]["delivered"]) and all(row["arms"]["baseline"]["delivered"])
            for row in rows if row["family"] == "short"
        ),
        "scope_completeness_and_budgets_intact": source_unchanged and not before["violations"]
        and not after["violations"],
        "median_latency_overhead": overhead <= GATES["median_overhead_max_pct"],
    }
    return {"passed": all(checks.values()), "checks": checks,
            "lost_documentation_spans": lost_docs, "median_overhead_pct": overhead}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lab", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    lab = args.lab.resolve(strict=True)
    rows, manifest = [], []
    source_unchanged = True
    with TemporaryDirectory() as temporary:
        for repository, sources, cases in fixtures():
            root = Path(temporary) / repository
            for path, text in sources.items():
                dest = root / path
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(text.encode())
            before = snapshot(root)
            manifest.append({"repository": repository, "inventory": before,
                             "cases": [asdict(case) for case in cases]})
            for case in cases:
                rows.append(run_case(lab, root, case, sources, len(rows)))
            source_unchanged &= before == snapshot(root)
    summary = {arm: summarise(rows, arm) for arm in ARMS}
    identity = json.dumps({"manifest": manifest, "arms": ARMS, "gates": GATES}, sort_keys=True)
    report = {
        "lab_sha256": sha256_file(lab),
        "confirmation_sha256": sha256(identity.encode()).hexdigest(),
        "gates": GATES,
        "source_unchanged": source_unchanged,
        "summary": summary,
        "by_family": {
            family: {arm: summarise([row for row in rows if row["family"] == family], arm) for arm in ARMS}
            for family in ("implementation", "documentation", "mixed", "short")
        },
        "decisions": {arm: decide(rows, summary, source_unchanged, arm) for arm in ("aligned", "code_weighted")},
        "cases": rows,
    }
    with args.output.open("x", encoding="utf-8") as output:
        json.dump(report, output, indent=2)
        output.write("\n")
    print(json.dumps({"summary": summary, "decisions": report["decisions"]}))
    return int(not source_unchanged or any(result["violations"] for result in summary.values()))


if __name__ == "__main__":
    raise SystemExit(main())
