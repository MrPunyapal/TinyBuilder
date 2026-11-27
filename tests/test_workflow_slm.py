import unittest
from dataclasses import replace

from benchmarks.laravel_pilot import patch_category
from benchmarks.workflow_slm import FIXTURES, reference_trajectory, validate_fixtures


class WorkflowSlmTests(unittest.TestCase):
    def test_fixture_splits_and_safe_reference_controls(self):
        validate_fixtures()
        for fixture in FIXTURES:
            case = fixture.case
            for replacement in (case.reference, fixture.wrong):
                with self.subTest(case=case.name, replacement=replacement):
                    self.assertIsNone(patch_category(case, case.source.replace(case.broken, replacement)))

    def test_cross_split_family_is_rejected(self):
        fixtures = (*FIXTURES[:-1], replace(FIXTURES[-1], family=FIXTURES[0].family))
        with self.assertRaises(ValueError):
            validate_fixtures(fixtures)

    def test_training_export_fails_closed_and_excludes_eval(self):
        controls = {"broken": [1, 0], "reference": [0, 0], "verified": "pass", "wrong": "reasoning"}
        trace = reference_trajectory(FIXTURES[0], controls)
        self.assertEqual(trace["split"], "train")
        self.assertEqual(trace["workflow"], "repair_single_line_v1")
        self.assertIn("not a model-generated", trace["origin"])
        self.assertNotIn(FIXTURES[0].case.test, str(trace))
        for fixture in FIXTURES:
            if fixture.split != "train":
                with self.assertRaises(ValueError):
                    reference_trajectory(fixture, controls)
        for key in controls:
            with self.assertRaises(ValueError):
                reference_trajectory(FIXTURES[0], {k: v for k, v in controls.items() if k != key})

    def test_wrong_repair_must_really_fail(self):
        with self.assertRaises(ValueError):
            reference_trajectory(FIXTURES[0], {"broken": [1, 0], "reference": [0, 0],
                                              "verified": "pass", "wrong": "pass"})
