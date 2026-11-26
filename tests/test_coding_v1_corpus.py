import unittest

from benchmarks.coding_v1_corpus import REPOSITORIES, test_source as render_verifier, valid_controls


class CorpusControlTests(unittest.TestCase):
    def test_policy_and_feedback_must_discriminate_narrow_repairs(self):
        row = {
            "broken": [1, 0], "reference": [0, 0], "wrong": [1, 0],
            "with_one_file_reverted": {"Policy": 1, "Consumer": 1},
            "narrow_witness": [1, 0],
            "policy_variation": {
                "reference_under_variant": 0,
                "hardcoded_under_default": [0, 0],
                "hardcoded_under_variant": 1,
            },
            "public_feedback": [1, 0],
            "public_feedback_narrow": 0,
        }
        self.assertTrue(valid_controls(row))
        for name, bypass in (
            ("policy_variation", {**row["policy_variation"], "hardcoded_under_variant": 0}),
            ("narrow_witness", [0, 0]),
            ("narrow_witness", [2, 0]),
            ("with_one_file_reverted", {"Policy": 0, "Consumer": 1}),
            ("public_feedback", [1, 1]),
            ("public_feedback_narrow", 1),
        ):
            with self.subTest(name=name, bypass=bypass):
                self.assertFalse(valid_controls({**row, name: bypass}))

    def test_public_challenge_and_verifier_filters_remain_separate(self):
        split, classes, dispatch_tasks = REPOSITORIES["dispatch"]
        self.assertEqual(split, "public-challenge")
        feedback_task = next(task for task in dispatch_tasks if task.feedback)
        php = render_verifier(classes, feedback_task)
        self.assertIn("function test_public_feedback()", php)
        self.assertIn("function test_repair()", php)
        self.assertNotIn("function test_policy_variant()", php)
        policy_task = next(task for task in dispatch_tasks if task.policy)
        php = render_verifier(classes, policy_task)
        self.assertIn("function test_policy_variant()", php)
        self.assertNotIn("function test_public_feedback()", php)
