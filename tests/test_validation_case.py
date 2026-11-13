"""Pure scenario controls: these tests do not invoke PHP, Composer or Ollama."""

import tempfile
import unittest
from pathlib import Path

from benchmarks.validation_case import (
    BAD_ROUTE, REFERENCE_ROUTE, VALIDATION_HIDDEN_PATH, VALIDATION_PATH,
    VALIDATION_READ_TASK, VALIDATION_WRITE_TASK, hidden_validation_test,
    reference_fixed_route, seed_validation,
)


class ValidationFixtureTests(unittest.TestCase):
    def test_bad_seed_and_reference_fix_are_distinct_and_reviewable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original = "<?php\nRoute::get('/', fn () => view('welcome'));\n"
            source = seed_validation(root, original)
            self.assertEqual(source.count(BAD_ROUTE), 1)
            self.assertIn("'accepted' => true", source)
            self.assertNotIn("$request->validate(", source)
            self.assertIn("assertUnprocessable()", (root / VALIDATION_PATH).read_text())
            fixed = reference_fixed_route(source)
            self.assertEqual(fixed, original + REFERENCE_ROUTE)
            self.assertIn("request()->validate(", fixed)
            self.assertIn("'required'", fixed)
            self.assertIn("'min:3'", fixed)
            self.assertNotIn(BAD_ROUTE, fixed)
            self.assertEqual((root / VALIDATION_PATH).read_text().count("test_invalid_contact_input"), 1)

    def test_hidden_assertions_cover_positive_negative_and_preservation(self):
        hidden = hidden_validation_test("tinybuilder-preserve-abc", "marker-123")
        for fragment in ("test_valid_input_returns_expected_response", "test_missing_fields_are_rejected",
                         "test_invalid_email_is_rejected", "test_short_message_is_rejected",
                         "test_existing_home_route_survives", "test_unrelated_sibling_route_survives",
                         "marker-123", "assertExactJson(['accepted' => true])"):
            self.assertIn(fragment, hidden)
        self.assertNotIn("marker-123", VALIDATION_READ_TASK + VALIDATION_WRITE_TASK)
        self.assertIn("BEFORE editing", VALIDATION_WRITE_TASK)
        self.assertTrue(VALIDATION_HIDDEN_PATH.endswith("ValidationHiddenTest.php"))

    def test_duplicate_seed_and_missing_reference_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = seed_validation(root, "<?php\n")
            with self.assertRaisesRegex(ValueError, "already has validation"):
                seed_validation(root, first)
            with self.assertRaisesRegex(ValueError, "exactly one"):
                reference_fixed_route("<?php\n")
            with self.assertRaisesRegex(ValueError, "marker"):
                hidden_validation_test("sibling", None)

    def test_reference_fix_preserves_windows_crlf_source(self):
        original = "<?php\r\nRoute::get('/', fn () => view('welcome'));\r\n"
        seeded = original + BAD_ROUTE.replace("\n", "\r\n")
        fixed = reference_fixed_route(seeded)
        self.assertEqual(fixed, original + REFERENCE_ROUTE.replace("\n", "\r\n"))
        self.assertNotIn("\n", fixed.replace("\r\n", ""))


if __name__ == "__main__":
    unittest.main()
