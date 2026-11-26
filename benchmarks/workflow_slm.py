"""Original Laravel workflow fixtures and verified reference-trajectory export.

Research only. No inference, training, network retrieval or model downloads.
Run on a trusted offline disposable Laravel checkout with installed dependencies.
"""
import argparse
from dataclasses import dataclass
import json
from pathlib import Path

from .evaluate import command, require, validate_laravel_baseline
from .laravel_pilot import Case, evaluate_preview, prepare, patch_category


@dataclass(frozen=True)
class Fixture:
    split: str
    family: str
    case: Case
    wrong: str


# Each family is assigned wholly to one split. These public held-out fixtures
# are development controls, not a secret final evaluation.
FIXTURES = (
    Fixture("train", "quantity_validation", Case(
        "quantity_validation", "QuantityRules", "Reject non-integer quantities and quantities below one; accept positive integers.",
        "rules", "", "return ['required', 'integer'];", "return ['required', 'integer', 'min:1'];",
        r"""return\s+\[\s*['"](?:required|integer|min:1|string|nullable)['"](?:\s*,\s*['"](?:required|integer|min:1|string|nullable)['"]){0,4}\s*,?\s*\]\s*;""",
        r"$v = \Illuminate\Support\Facades\Validator::make(['q'=>0], ['q'=>QuantityRules::rules()]); $this->assertTrue($v->fails()); "
        r"$this->assertTrue(\Illuminate\Support\Facades\Validator::make(['q'=>'abc'], ['q'=>QuantityRules::rules()])->fails());",
        r"$this->assertFalse(\Illuminate\Support\Facades\Validator::make(['q'=>2], ['q'=>QuantityRules::rules()])->fails());",
    ), "return ['required', 'integer', 'nullable'];"),
    Fixture("train", "money_calculation", Case(
        "invoice_total", "InvoiceTotal", "Calculate subtotal plus tax minus credit. Preserve behavior when both adjustments are zero.",
        "total", "int $subtotal, int $tax, int $credit", "return $subtotal + $tax + $credit;", "return $subtotal + $tax - $credit;",
        r"return\s+\$(?:subtotal|tax|credit)(?:\s*[+\-]\s*\$(?:subtotal|tax|credit)){0,2}\s*;",
        "$this->assertSame(105, InvoiceTotal::total(100, 15, 10)); $this->assertSame(40, InvoiceTotal::total(50, 0, 10));",
        "$this->assertSame(80, InvoiceTotal::total(80, 0, 0));",
    ), "return $subtotal - $tax - $credit;"),
    Fixture("dev", "ownership_policy", Case(
        "ownership_policy", "OwnershipPolicy", "Allow an edit only if the user owns the record and is active.",
        "allows", "int $user, int $owner, bool $active", "return $user === $owner;", "return $user === $owner && $active;",
        r"return\s+\$user\s*(?:===|!==)\s*\$owner(?:\s*(?:&&|\|\|)\s*!?\$active)?\s*;",
        "$this->assertFalse(OwnershipPolicy::allows(1, 1, false)); $this->assertFalse(OwnershipPolicy::allows(2, 1, true));",
        "$this->assertTrue(OwnershipPolicy::allows(1, 1, true));",
    ), "return $user === $owner || $active;"),
    Fixture("eval", "collection_filter", Case(
        "collection_filter", "ActiveItems", "Return only active records as a zero-indexed Laravel collection. Preserve empty results.",
        "select", "array $items", "return collect($items)->where('active', false)->values();", "return collect($items)->where('active', true)->values();",
        r"return\s+collect\(\$items\)->where\('active',\s*(?:true|false)\)(?:->values\(\))?\s*;",
        "$items = [['id'=>1,'active'=>false], ['id'=>2,'active'=>true]]; $this->assertSame([['id'=>2,'active'=>true]], ActiveItems::select($items)->all());",
        "$this->assertSame([], ActiveItems::select([])->all());",
    ), "return collect($items)->where('active', true);"),
    Fixture("eval", "string_normalization", Case(
        "string_normalization", "ContactLabel", "Return a label with surrounding whitespace removed and letters lowercased.",
        "normalize", "string $label", "return strtolower($label);", "return strtolower(trim($label));",
        r"return\s+(?:strtolower\(\$label\)|trim\(\$label\)|strtolower\(trim\(\$label\)\)|trim\(strtolower\(\$label\)\))\s*;",
        "$this->assertSame('hello', ContactLabel::normalize(' HELLO ')); $this->assertSame('a b', ContactLabel::normalize(' A B '));",
        "$this->assertSame('', ContactLabel::normalize(''));",
    ), "return trim($label);"),
)


def validate_fixtures(fixtures=FIXTURES):
    families, names = {}, set()
    for fixture in fixtures:
        case = fixture.case
        if fixture.split not in ("train", "dev", "eval"):
            raise ValueError("Unknown split")
        if case.name in names or families.setdefault(fixture.family, fixture.split) != fixture.split:
            raise ValueError("Duplicate case or cross-split family leakage")
        names.add(case.name)
        if case.source.count(case.broken) != 1:
            raise ValueError("Ambiguous replacement anchor")
        if len({case.broken, case.reference, fixture.wrong}) != 3:
            raise ValueError("Controls must differ")
        for replacement in (case.reference, fixture.wrong):
            if patch_category(case, case.source.replace(case.broken, replacement)) is not None:
                raise ValueError("Control falls outside safe subset")
    if set(families.values()) != {"train", "dev", "eval"}:
        raise ValueError("All splits required")


def reference_trajectory(fixture, controls):
    """Export only a train reference with actual evaluator success evidence."""
    if fixture.split != "train":
        raise ValueError("Only training split may be exported")
    if controls != {"broken": [1, 0], "reference": [0, 0], "verified": "pass", "wrong": "reasoning"}:
        raise ValueError("Reference or negative control not verified")
    case = fixture.case
    return {
        "case": case.name, "family": fixture.family, "split": "train",
        "origin": "original deterministic reference; not a model-generated trace",
        "workflow": "repair_single_line_v1",
        "controls": controls,
        "messages": [
            {"role": "system", "content": "repair_single_line_v1"},
            {"role": "user", "content": case.task + "\nTarget: " + case.path},
            {"role": "assistant", "content": json.dumps({"action": "read", "path": case.path})},
            {"role": "user", "content": "TOOL_RESULT: " + case.source},
            {"role": "assistant", "content": json.dumps({"action": "propose", "path": case.path,
                                                        "old": case.broken, "new": case.reference})},
            {"role": "user", "content": "EVALUATOR_RESULT: repair and regression tests passed"},
            {"role": "assistant", "content": json.dumps({"action": "finish", "status": "verified"})},
        ],
    }


def run(base, output, php):
    validate_fixtures()
    base, output = base.resolve(), output.resolve()
    revision = validate_laravel_baseline(base, output)
    output.mkdir()
    report = {"kind": "reference_controls_only", "model_trials": 0, "baseline": revision,
              "status": "incomplete", "cases": []}
    traces = []
    try:
        for fixture in FIXTURES:
            case = fixture.case
            root = output / case.name
            result = {"case": case.name, "family": fixture.family, "split": fixture.split}
            report["cases"].append(result)
            try:
                result.update(prepare(case, base, root, revision, php))
                if result["broken"] != [1, 0] or result["reference"] != [0, 0]:
                    raise ValueError("Invalid baseline/reference controls")
                for label, replacement in (("verified", case.reference), ("wrong", fixture.wrong)):
                    row = {"preview": case.source.replace(case.broken, replacement)}
                    evaluate_preview(row, case, root, php)
                    result[label] = row["category"]
                controls = {key: result[key] for key in ("broken", "reference", "verified", "wrong")}
                if controls != {"broken": [1, 0], "reference": [0, 0], "verified": "pass", "wrong": "reasoning"}:
                    raise ValueError("Independent evaluator did not distinguish reference from wrong repair")
                if fixture.split == "train":
                    traces.append(reference_trajectory(fixture, controls))
            finally:
                if root.exists():
                    require(["git", "worktree", "remove", "--force", str(root)], base)
        with (output / "train.jsonl").open("x", encoding="utf-8") as stream:
            for trace in traces:
                stream.write(json.dumps(trace) + "\n")
        report["status"] = "reference_controls_passed"
        report["training_rows"] = len(traces)
    finally:
        (output / "controls.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--php", required=True)
    args = parser.parse_args()
    return run(args.baseline, args.output, args.php)


if __name__ == "__main__":
    raise SystemExit(main())
