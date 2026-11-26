from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from benchmarks.coding_intelligence import FIXTURES, validate_fixtures
from benchmarks.laravel_pilot import digest, main, patch_category


class CodingIntelligenceTests(unittest.TestCase):
    def test_original_cross_file_controls(self):
        validate_fixtures()
        for fixture in FIXTURES:
            case = fixture.case
            with self.subTest(case=case.name):
                self.assertNotIn(case.path, fixture.related)
                self.assertIn(fixture.companion, case.task)
                self.assertIn(fixture.companion, case.reference)
                self.assertNotIn(case.reference, case.task)
                for replacement in (case.reference, fixture.wrong):
                    self.assertIsNone(patch_category(case, case.source.replace(case.broken, replacement)))
                self.assertEqual(patch_category(case, case.source.replace(case.broken, "return helper();")),
                                 "outside_safe_subset")

    def test_exact_retrieval_campaign_preserves_both_arms_and_missing_trials(self):
        def infer(_lab, _runtime, _model, plan):
            jobs = json.loads(plan.read_text())
            self.assertEqual([job["case"] for job in jobs], [fixture.case.name for fixture in FIXTURES])
            for job in jobs:
                self.assertTrue(job["cross_file"])
                self.assertTrue(job["exact_retrieval"])
                self.assertFalse(job["compare_v1"])
            return [{"case": job["case"], "arm": "L", "category": "replacement_match"}
                    for job in jobs], {"driver_failure": None}

        def controls(_case, _base, _project, _revision, _php, _related):
            return {"broken": [1, 0], "reference": [0, 0]}

        def score(row, _case, _project, _php):
            if "preview" in row:
                row.update(category="reasoning")

        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "runtime-manifest.json").write_text("{}")
            model = root / "smoke.gguf"
            model.write_bytes(b"model stub")
            output = root / "result"
            argv = ["laravel_pilot", "--suite", "coding-retrieval-exact", "--baseline", str(root / "baseline"),
                    "--runtime", str(root), "--lab", str(model), "--php", "unused",
                    "--output", str(output), "--model", "stub", str(model), digest(model)]
            with (patch("sys.argv", argv),
                  patch("benchmarks.laravel_pilot.validate_laravel_baseline", return_value="test"),
                  patch("benchmarks.laravel_pilot.prepare", side_effect=controls),
                  patch("benchmarks.laravel_pilot.evaluate_preview", side_effect=score),
                  patch("benchmarks.laravel_pilot.infer", side_effect=infer),
                  redirect_stdout(StringIO())):
                self.assertEqual(main(), 1)
            report = json.loads((output / "pilot.json").read_text(encoding="utf-8"))
            self.assertEqual(report["configuration"]["arms"], ["L", "S"])
            self.assertEqual(report["requested_per_model"], 6)
            self.assertEqual(report["models"][0]["counts"], {"replacement_match": 3, "not_run": 3})
