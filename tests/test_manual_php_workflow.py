"""Manual Laravel controls are opt-in and never request model weights."""
import unittest
import shlex
from pathlib import Path


class WorkflowPolicyTests(unittest.TestCase):
    def test_skeleton_creation_defers_scripts_until_dependencies_are_installed(self):
        root = Path(__file__).resolve().parents[1]
        workflow = (root / ".github/workflows/laravel-controls.yml").read_text()
        create = next(line.strip() for line in workflow.splitlines()
                      if line.strip().startswith("composer create-project "))
        arguments = shlex.split(create)
        # --no-install alone still fires Laravel's post-create artisan scripts.
        self.assertIn("--no-install", arguments)
        self.assertIn("--no-scripts", arguments,
                      "Do not invoke artisan before vendor/autoload.php exists")
        install = next(line.strip() for line in workflow.splitlines()
                       if line.strip().startswith("composer install "))
        self.assertNotIn("--no-scripts", shlex.split(install),
                         "Normal dependency installation must discover Laravel packages")
        self.assertLess(workflow.index(install), workflow.index("php artisan key:generate"))

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
