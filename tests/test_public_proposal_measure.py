import json
import subprocess
import unittest
from unittest.mock import patch

from benchmarks.public_proposal_measure import METRIC_PREFIX, _metrics, measure


class PublicProposalMeasurementTests(unittest.TestCase):
    def test_metrics_ignore_model_diff_and_reject_duplicate_events(self):
        event = METRIC_PREFIX + '{"phase":"proposal","status":"proposal_ready"}'
        self.assertEqual(_metrics("| + " + event + "\n" + event),
                         {"proposal": {"status": "proposal_ready"}})
        with self.assertRaisesRegex(ValueError, "Unexpected lab metric phase"):
            _metrics(event + "\n" + event)

    def test_review_runs_never_supply_patch_approval(self):
        task = {"task": "fixture", "allowed_edit_paths": ["app/Case.php"], "prompt": "Repair behavior"}
        for approval, status in (("not_approved", "proposal_ready"),
                                 ("applied", "approval_boundary_unverified")):
            with self.subTest(approval=approval), patch(
                "benchmarks.public_proposal_measure.subprocess.Popen"
            ) as launch, patch("benchmarks.public_proposal_measure.monitor"):
                child = launch.return_value.__enter__.return_value
                events = [
                    {"phase": "retrieval", "status": "selected", "files": [
                        {"path": "app/Case.php", "complete": True}]},
                    {"phase": "proposal", "status": "proposal_ready"},
                    {"phase": "approval", "status": approval},
                ]
                child.communicate.return_value = ("\n".join(METRIC_PREFIX + json.dumps(event) for event in events), None)
                child.returncode = 0
                row = measure("lab", "runtime", "model", "project", task, 4096)
                self.assertEqual(launch.call_args.kwargs["stdin"], subprocess.DEVNULL)
                self.assertIn("--selective-context", launch.call_args.args[0])
                self.assertEqual(row["allowed_paths_retrieved"], ["app/Case.php"])
                self.assertEqual(row["status"], status)
