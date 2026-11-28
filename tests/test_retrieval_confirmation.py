import tempfile
import unittest
from pathlib import Path

from benchmarks.retrieval_confirmation import expected_inventory, prepare, snapshot
from benchmarks.retrieval_confirmation_measure import grade
from benchmarks.retrieval_confirmation_tasks import cases


class RetrievalConfirmationTests(unittest.TestCase):
    def test_pristine_inventory_and_separate_scoring_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "source"
            prepare(root)
            self.assertEqual(snapshot(root), expected_inventory())
            records = list(cases())
            self.assertEqual(len(records), 56)
            self.assertEqual(len({repo for repo, *_ in records}), 8)
            self.assertEqual(sum(not required for *_, required in records), 11)
            self.assertEqual(len({task for _, task, *_ in records}), len(records))
            self.assertTrue(all(Path(path).suffix in (".php", ".py", ".rs") for path in snapshot(root)))
            self.assertFalse((root / "public-plan.json").exists())

    def test_partial_read_counts_only_when_it_contains_a_required_span(self):
        repo, task, _, required = next(case for case in cases() if case[1] == "aisle")
        path, marker = next(iter(required.items()))
        file = {"path": path, "complete": False, "bytes": 1200, "first_line": 1, "last_line": marker - 1}
        observation = {"files": [file], "incomplete": True}
        missed = grade(repo, task, required, observation)
        self.assertEqual(missed["delivered_paths"], [path])
        self.assertEqual(missed["delivered_evidence"], [])
        file["last_line"] = marker
        self.assertEqual(grade(repo, task, required, observation)["delivered_evidence"], [path])
        self.assertEqual(grade(repo, task, {path: None}, observation)["delivered_evidence"], [])

    def test_separates_support_from_marked_distractors(self):
        repo, task, _, required = next(case for case in cases() if case[1] == "hold-path")
        irrelevant = "app/billing/payment.php"
        file = {"complete": True, "bytes": 100, "first_line": 1, "last_line": 5}
        row = grade(repo, task, required,
                    {"files": [{"path": path, **file} for path in ("routes/web.php", irrelevant)]})
        self.assertEqual(row["support_delivered"], 1)
        self.assertEqual(row["edit_loci_delivered"], 0)
        self.assertEqual(row["known_distractors"], [irrelevant])
