"""Compare two local multi-trial evaluation reports without reading model content.

Use paired --fixture-seed runs for matched hidden-name/sibling-route conditions.
This tool reports observed counts, not confidence intervals or model reliability.
"""

import argparse
import json
from pathlib import Path


def _load(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("configuration"), dict):
        raise ValueError("Both reports must use --trials 2 or more")
    trials = data.get("trials")
    requested = data["configuration"].get("trials_requested")
    if not isinstance(trials, list) or not isinstance(requested, int) or len(trials) != requested:
        raise ValueError("Report is incomplete or has an invalid trial count")
    if not 2 <= requested <= 10:
        raise ValueError("Unsupported trial count")
    layout = None
    for expected_number, trial in enumerate(trials, 1):
        if (not isinstance(trial, dict) or trial.get("trial") != expected_number or
                not isinstance(trial.get("smoke"), list)):
            raise ValueError("Malformed trial data or trial identifiers")
        current_layout = []
        for label in ("smoke", "laravel"):
            if label in trial and not isinstance(trial[label], list):
                raise ValueError("Malformed trial data")
            names = []
            for item in trial.get(label, []):
                if (not isinstance(item, dict) or not isinstance(item.get("model"), str) or
                        not item["model"] or type(item.get("passed")) is not bool):
                    raise ValueError("Malformed or missing result signal")
                names.append(item["model"])
            if len(names) != len(set(names)):
                raise ValueError("Duplicate model result in trial")
            current_layout.append(tuple(names))
        if current_layout[1] and current_layout[0] != current_layout[1]:
            raise ValueError("Smoke and Laravel model order differs")
        if layout is None:
            layout = current_layout
        elif current_layout != layout:
            raise ValueError("Model order differs across trials")
    return data


def _counts(data):
    names = sorted({item["model"] for trial in data["trials"]
                    for label in ("smoke", "laravel") for item in trial.get(label, [])})
    return {model: {label: {"passed": sum(item["passed"] for trial in data["trials"]
                                                  for item in trial.get(label, []) if item["model"] == model),
                            "total": sum(1 for trial in data["trials"]
                                         for item in trial.get(label, []) if item["model"] == model)}
                    for label in ("smoke", "laravel")}
            for model in names}


def compare(baseline_path, candidate_path):
    baseline, candidate = _load(baseline_path), _load(candidate_path)
    bcfg, ccfg = baseline["configuration"], candidate["configuration"]
    for key in ("trials_requested", "scenario", "preserve_sibling_route", "tool_protocol", "strict_json_profile"):
        if bcfg.get(key) != ccfg.get(key):
            raise ValueError("Cannot compare mismatched configuration: " + key)
    # Reports created before the flag all used eight tool rounds.
    if bcfg.get("max_steps", 8) != ccfg.get("max_steps", 8):
        raise ValueError("Cannot compare mismatched configuration: max_steps")
    bcounts, ccounts = _counts(baseline), _counts(candidate)
    if set(bcounts) != set(ccounts):
        raise ValueError("Model sets differ")
    for model in bcounts:
        if any(bcounts[model][task]["total"] != ccounts[model][task]["total"]
               for task in ("smoke", "laravel")):
            raise ValueError("Task counts differ")
    bid, cid = bcfg.get("paired_fixture_id"), ccfg.get("paired_fixture_id")
    if bid and cid and bid != cid:
        raise ValueError("Paired fixture IDs differ; repeat both runs with the same --fixture-seed")
    paired = bool(bid and cid and bid == cid)
    # Sibling route identities are derived from (seed, trial, MODEL INDEX).
    # Sorting model sets alone would mislabel swapped model orders as paired.
    # Likewise the same seed against different Laravel baselines is not a
    # matched fixture comparison. Refuse both before reporting any deltas.
    for btrial, ctrial in zip(baseline["trials"], candidate["trials"]):
        for label in ("smoke", "laravel"):
            bnames = [item["model"] for item in btrial.get(label, [])]
            cnames = [item["model"] for item in ctrial.get(label, [])]
            if bnames != cnames:
                raise ValueError("Model order differs between reports")
        for bitem, citem in zip(btrial.get("laravel", []), ctrial.get("laravel", [])):
            for key in ("baseline_commit", "composer_lock_sha256"):
                bvalue, cvalue = bitem.get(key), citem.get(key)
                if not isinstance(bvalue, str) or not bvalue or bvalue != cvalue:
                    raise ValueError("Laravel baseline identity missing or differs: " + key)
    delta = {model: {task: {"baseline": bcounts[model][task]["passed"],
                            "candidate": ccounts[model][task]["passed"],
                            "total": bcounts[model][task]["total"],
                            "delta": ccounts[model][task]["passed"] - bcounts[model][task]["passed"]}
                     for task in ("smoke", "laravel") if bcounts[model][task]["total"]}
             for model in sorted(bcounts)}
    return {"paired_inputs": paired, "trials": bcfg["trials_requested"],
            "baseline_guidance": bcfg.get("progress_guidance", "off"),
            "candidate_guidance": ccfg.get("progress_guidance", "off"),
            "observed_counts": delta,
            "interpretation": ("Matched fixture inputs (not matched model randomness or cache state)" if paired
                               else "Unpaired inputs: do not attribute differences solely to guidance")}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True, help="results.json of the original profile")
    parser.add_argument("--candidate", type=Path, required=True, help="results.json of the experimental profile")
    args = parser.parse_args(argv)
    try:
        result = compare(args.baseline, args.candidate)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
