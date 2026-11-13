"""Counterexamples for paired benchmark comparisons; no PHP or model access."""
import json
import tempfile
import unittest
from pathlib import Path

from benchmarks.compare import compare


def report(path, models=("model-A", "model-B"), commit="base-revision", lock="lock-hash"):
    document = {
        "configuration": {"trials_requested": 2, "scenario": "repair", "preserve_sibling_route": True,
                          "tool_protocol": "strict-json", "strict_json_profile": "constrained",
                          "progress_guidance": "off", "paired_fixture_id": "same-seed-hash"},
        "trials": [
            {"trial": index,
             "smoke": [{"model": model, "passed": True} for model in models],
             "laravel": [{"model": model, "passed": True, "baseline_commit": commit,
                          "composer_lock_sha256": lock} for model in models]}
            for index in (1, 2)],
    }
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


class TestCompareIntegrity(unittest.TestCase):
    def test_mismatched_model_order_cannot_claim_paired_sibling_fixtures(self):
        with tempfile.TemporaryDirectory() as directory:
            a = report(Path(directory) / "base.json")
            b = report(Path(directory) / "candidate.json", models=("model-B", "model-A"))
            with self.assertRaisesRegex(ValueError, "Model order differs"):
                compare(a, b)

    def test_different_laravel_baseline_commit_and_lock_are_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            a = report(Path(directory) / "base.json")
            b = Path(directory) / "candidate.json"
            report(b, commit="different-revision")
            with self.assertRaisesRegex(ValueError, "baseline_commit"):
                compare(a, b)
            report(b, lock="different-lock")
            with self.assertRaisesRegex(ValueError, "composer_lock_sha256"):
                compare(a, b)

    def test_missing_baseline_identity_is_not_labeled_paired(self):
        with tempfile.TemporaryDirectory() as directory:
            a = report(Path(directory) / "base.json")
            b = report(Path(directory) / "candidate.json")
            data = json.loads(b.read_text())
            for trial in data["trials"]:
                for result in trial["laravel"]:
                    result.pop("composer_lock_sha256")
            b.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "composer_lock_sha256"):
                compare(a, b)

    def test_duplicate_trial_rows_and_model_rows_are_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            a = report(Path(directory) / "base.json")
            b = report(Path(directory) / "candidate.json")
            data = json.loads(b.read_text())
            data["trials"][1]["trial"] = 1
            b.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "trial identifiers"):
                compare(a, b)
            data = json.loads(a.read_text())
            data["trials"][0]["smoke"][1]["model"] = "model-A"
            b.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Duplicate model"):
                compare(a, b)

    def test_matching_models_baseline_and_seed_stay_paired(self):
        with tempfile.TemporaryDirectory() as directory:
            a = report(Path(directory) / "base.json")
            b = report(Path(directory) / "candidate.json")
            self.assertTrue(compare(a, b)["paired_inputs"])


if __name__ == "__main__":
    unittest.main()
