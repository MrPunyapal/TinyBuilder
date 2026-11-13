"""Deterministic report comparison tests; no local model or Laravel required."""
import json
import tempfile
import unittest
from pathlib import Path

from benchmarks.compare import compare


class CompareTests(unittest.TestCase):
    def report(self, path, seed="paired", guidance="off", success=(False, True), scenario="health"):
        cfg = {"trials_requested": 2, "scenario": scenario, "preserve_sibling_route": True,
               "tool_protocol": "strict-json", "strict_json_profile": "constrained",
               "progress_guidance": guidance, "paired_fixture_id": seed}
        doc = {"configuration": cfg, "trials": [
            {"trial": i, "smoke": [{"model": "3b", "passed": success[i-1]}],
             "laravel": [{"model": "3b", "passed": success[i-1],
                          "baseline_commit": "disposable-commit", "composer_lock_sha256": "lock-sha"}]}
            for i in (1, 2)]}
        path.write_text(json.dumps(doc))
        return path

    def test_reports_counts_without_project_or_hidden_content(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            a = self.report(root / "base.json", success=(False, True))
            b = self.report(root / "candidate.json", guidance="checklist", success=(True, True))
            result = compare(a, b)
            self.assertTrue(result["paired_inputs"])
            self.assertEqual(result["observed_counts"]["3b"]["smoke"],
                             {"baseline": 1, "candidate": 2, "total": 2, "delta": 1})
            self.assertNotIn("paired_fixture_id", json.dumps(result))  # No seed values or IDs.

    def test_mismatched_scenarios_and_seed_ids_refused(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            a = self.report(root / "base.json")
            b = self.report(root / "candidate.json", scenario="repair")
            with self.assertRaisesRegex(ValueError, "scenario"):
                compare(a, b)
            self.report(b, seed="different")
            with self.assertRaisesRegex(ValueError, "IDs differ"):
                compare(a, b)

    def test_unpaired_is_honestly_labeled(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            a = self.report(root / "base.json", seed=None)
            b = self.report(root / "candidate.json", seed=None)
            result = compare(a, b)
            self.assertFalse(result["paired_inputs"])
            self.assertIn("Unpaired", result["interpretation"])

    def test_incomplete_report_refused(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            a = self.report(root / "base.json")
            b = self.report(root / "candidate.json")
            payload = json.loads(b.read_text())
            payload["trials"].pop()
            b.write_text(json.dumps(payload))
            with self.assertRaisesRegex(ValueError, "incomplete"):
                compare(a, b)


if __name__ == "__main__":
    unittest.main()
