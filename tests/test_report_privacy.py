"""Deterministic report-privacy regression, no real PHP or local model."""

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from benchmarks.evaluate import laravel
from test_laravel_harness import HarnessTest


class TestReportPrivacy(unittest.TestCase):
    def test_laravel_report_uses_relative_worktree_label(self):
        with tempfile.TemporaryDirectory() as directory:
            home, output = Path(directory) / "base", Path(directory) / "output"
            output.mkdir()
            HarnessTest().seed_repo(home)
            # A failed model run is sufficient: report privacy must hold even on failure.
            with patch("benchmarks.evaluate.ChatModel") as model:
                model.return_value.complete.return_value = {
                    "content": json.dumps({"type": "final", "content": "Unable to finish"})}
                with contextlib.redirect_stdout(io.StringIO()) as stdout:
                    result = laravel(home, output, ["fake-model"], sys.executable,
                                     tool_protocol="strict-json")[0]
            self.assertEqual(result["worktree"], "laravel-0")
            self.assertFalse(result["passed"])
            self.assertNotIn(str(output.resolve()), json.dumps(result))
            self.assertNotIn(str(output.resolve()), stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
