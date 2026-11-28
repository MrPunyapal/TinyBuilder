from collections import Counter
import unittest

from benchmarks.excerpt_confirmation_cases import Span, fixtures
from benchmarks.excerpt_confirmation_measure import FILE_BYTE_LIMIT, decide, score


class ExcerptConfirmationTests(unittest.TestCase):
    def test_frozen_inventory_and_evidence_labels(self):
        corpus = list(fixtures())
        self.assertEqual(len(corpus), 6)
        cases = [case for _, _, group in corpus for case in group]
        self.assertEqual(Counter(case.family for case in cases), {
            "implementation": 8, "documentation": 8, "mixed": 4, "short": 4,
        })
        self.assertEqual(len({case.name for case in cases}), 24)
        self.assertEqual(sum(len(case.required) for case in cases), 28)
        self.assertEqual(sum(span.documentation for case in cases for span in case.required), 12)
        for _, sources, group in corpus:
            for case in group:
                for span in case.required:
                    lines = sources[span.path].splitlines(keepends=True)
                    self.assertLessEqual(span.last, len(lines))
                    self.assertLess(len("".join(lines[span.first - 1:span.last]).encode()), FILE_BYTE_LIMIT)
                    self.assertNotIn(span.path, case.prompt)
                    if case.family == "short":
                        self.assertLessEqual(len(sources[span.path].encode()), FILE_BYTE_LIMIT)
                    else:
                        self.assertGreater(len(sources[span.path].encode()), FILE_BYTE_LIMIT)

    def test_partial_line_cannot_receive_span_credit(self):
        span = Span("cases.rs", 1, 1, False)
        files = [{"path": "cases.rs", "first_line": 1, "last_line": 1,
                  "complete": False, "bytes": 2}]
        result = score({"status": "selected", "files": files, "incomplete": True},
                       {"cases.rs": "αβ\nsecond\n"}, (span,))
        self.assertEqual(result["delivered"], [False])
        self.assertEqual(result["violations"], ["invalid_full_line_range:cases.rs"])

    def test_gate_rejects_a_lost_documentation_span_despite_net_gain(self):
        span = {"path": "guide.md", "first": 1, "last": 1, "documentation": True}
        rows = [{"case": "guide", "family": "documentation", "required": [span],
                 "arms": {"baseline": {"delivered": [True]}, "aligned": {"delivered": [False]}}}]
        summary = {"baseline": {"median_us": 100, "complete_tasks": 20, "violations": 0},
                   "aligned": {"median_us": 119, "complete_tasks": 22, "violations": 0,
                               "required_spans_delivered": 26, "required_spans": 28}}
        decision = decide(rows, summary, True, "aligned")
        self.assertFalse(decision["passed"])
        self.assertFalse(decision["checks"]["no_documentation_regression"])
        self.assertTrue(decision["checks"]["overall_required_span_recall"])
        self.assertEqual(decision["lost_documentation_spans"], [{"case": "guide", "span": span}])
