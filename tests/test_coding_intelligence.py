import unittest

from benchmarks.coding_intelligence import FIXTURES, validate_fixtures
from benchmarks.laravel_pilot import patch_category


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
