import unittest
from unittest.mock import patch

from benchmarks.laravel_pilot import CASES, evaluate_preview, patch_category


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

    def test_generated_preview_never_reaches_host_php_even_if_it_matches_subset(self):
        case = CASES[0]
        row = {"category": "proposal", "preview": case.source.replace(case.broken, case.reference)}
        with patch("benchmarks.laravel_pilot.command") as command, patch("benchmarks.laravel_pilot.test") as test:
            evaluate_preview(row, case, None, "unused")
        self.assertEqual(row, {"category": "containment_blocked"})
        command.assert_not_called()
        test.assert_not_called()

    def test_route_validation_old_mode_is_rejected_before_worktree_or_php(self):
        from benchmarks import rust_patch_validation
        argv = ["rust_patch_validation", "--baseline", "unused", "--output", "unused", "--php", "unused"]
        with (patch("sys.argv", argv), patch.object(rust_patch_validation, "require") as run,
              patch.object(rust_patch_validation, "validate_laravel_baseline") as validate,
              self.assertRaises(SystemExit) as error):
            rust_patch_validation.main()
        self.assertEqual(error.exception.code, 2)
        run.assert_not_called()
        validate.assert_not_called()
