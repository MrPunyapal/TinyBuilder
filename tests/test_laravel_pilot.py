import unittest

from benchmarks.laravel_pilot import CASES, patch_category


class LaravelPilotPatchTests(unittest.TestCase):
    def test_reference_edits_and_wrong_arithmetic_reach_behavioral_oracle(self):
        for case in CASES:
            with self.subTest(case=case.name):
                self.assertIsNone(patch_category(case, case.source.replace(case.broken, case.reference)))
        case = CASES[1]
        wrong = case.source.replace(case.broken, "return $discount - $subtotal;")
        self.assertIsNone(patch_category(case, wrong))

    def test_changes_outside_the_line_and_calls_are_not_executed(self):
        for case in CASES:
            with self.subTest(case=case.name):
                changed = case.source.replace("final class", "class")
                self.assertEqual(patch_category(case, changed), "out_of_scope")
                unsafe = case.source.replace(case.broken, "return helper();")
                self.assertEqual(patch_category(case, unsafe), "outside_safe_subset")
