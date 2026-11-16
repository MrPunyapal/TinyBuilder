"""Pure PHP fixture tests; never execute PHP, Composer or Ollama."""
import tempfile
import unittest
from pathlib import Path

from benchmarks.parameter_case import (
    BAD_PARAMETER_ROUTE, HIDDEN_PARAMETER_TEST, PARAMETER_HIDDEN_PATH,
    PARAMETER_PATH, PARAMETER_READ_TASK, PARAMETER_WRITE_TASK,
    REFERENCE_PARAMETER_ROUTE, hidden_parameter_test, reference_fixed_parameter,
    seed_parameter,
)


class ParameterFixtureTests(unittest.TestCase):
    def test_negative_seed_and_reference_are_distinct(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original = "<?php\nRoute::get('/', fn () => 'home');\n"
            seeded = seed_parameter(root, original)
            self.assertEqual(seeded, original + BAD_PARAMETER_ROUTE)
            self.assertIn("assertExactJson(['id' => 7])", (root / PARAMETER_PATH).read_text())
            self.assertEqual(reference_fixed_parameter(seeded),
                             original + REFERENCE_PARAMETER_ROUTE)
            self.assertIn("'id' => 0", seeded)
            self.assertNotIn("ctype_digit", seeded)
            with self.assertRaisesRegex(ValueError, "already has parameter"):
                seed_parameter(root, seeded)
            with self.assertRaisesRegex(ValueError, "exactly one"):
                reference_fixed_parameter(original)

    def test_crlf_round_trip(self):
        previous = "<?php\r\nRoute::get('/', fn () => 'home');\r\n"
        seeded = previous + BAD_PARAMETER_ROUTE.replace("\n", "\r\n")
        self.assertEqual(reference_fixed_parameter(seeded),
                         previous + REFERENCE_PARAMETER_ROUTE.replace("\n", "\r\n"))

    def test_integer_contract_rejects_other_numeric_string_forms(self):
        # is_numeric() accepts fractions/exponents, although neither is an
        # integer route identifier. Both need independent negative assertions.
        for invalid in ("7.5", "1e2"):
            self.assertIn(f"getJson('/tinybuilder/items/{invalid}')->assertNotFound()",
                          HIDDEN_PARAMETER_TEST)

    def test_independent_hidden_assertions_and_private_sibling_marker(self):
        hidden = hidden_parameter_test("tinybuilder-preserve-abcd", "private-marker")
        for needle in ("test_positive_id_one", "test_positive_id_forty_two",
                       "test_non_numeric_id_returns_404", "test_zero_id_returns_404",
                       "test_home_route_survives", "test_unrelated_sibling_survives",
                       "private-marker"):
            self.assertIn(needle, hidden)
        self.assertIn("TinyBuilderParameterHiddenTest", HIDDEN_PARAMETER_TEST)
        self.assertTrue(PARAMETER_HIDDEN_PATH.endswith("TinyBuilderParameterHiddenTest.php"))
        self.assertNotIn("private-marker", PARAMETER_READ_TASK + PARAMETER_WRITE_TASK)
        with self.assertRaisesRegex(ValueError, "marker"):
            hidden_parameter_test("x", None)


if __name__ == "__main__":
    unittest.main()
