"""Manual Laravel controls are opt-in and never request model weights."""
import unittest
from pathlib import Path


class WorkflowPolicyTests(unittest.TestCase):
    def test_manual_real_laravel_controls_are_not_default_ci(self):
        root = Path(__file__).resolve().parents[1]
        workflow = (root / ".github/workflows/laravel-controls.yml").read_text()
        self.assertIn("workflow_dispatch:", workflow)
        self.assertNotIn("\n  push:", workflow)
        self.assertNotIn("\n  pull_request:", workflow)
        self.assertIn("--scenario validation --controls-only", workflow)
        self.assertIn("--scenario parameter --controls-only", workflow)
        self.assertIn("composer create-project", workflow)
        self.assertIn("php artisan test", workflow)
        self.assertNotIn("ollama pull", workflow)
        self.assertNotIn("--models", workflow)
        self.assertNotIn("--allow-write", workflow)
        self.assertNotIn("upload-artifact", workflow)


if __name__ == "__main__":
    unittest.main()
