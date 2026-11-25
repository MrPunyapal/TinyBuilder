import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from packaging_checks import MAC_FIXTURE, MAC_LOCK, run_fixture, run_tests


class PackagingChecksTests(unittest.TestCase):
    def test_missing_owner_files_not_qualified(self):
        with tempfile.TemporaryDirectory() as tmp, patch("packaging_checks.subprocess.run") as call:
            for target in ("windows", "macos", "linux"):
                self.assertTrue(run_tests(Path(tmp), target).startswith("BLOCKED"))
            self.assertTrue(run_fixture(Path(tmp)).startswith("BLOCKED"))
            call.assert_not_called()

    def test_actual_owner_commands(self):
        for target, folder, sentinel in (
            ("windows", "packaging/windows/verification", "test_payload.py"),
            ("macos", "packaging/macos", "test_verify_runtime.py"),
            ("linux", "packaging/linux", "test_verify_runtime.py"),
        ):
            with self.subTest(target=target), tempfile.TemporaryDirectory() as tmp, patch("packaging_checks.subprocess.run") as call:
                root = Path(tmp)
                (root / folder).mkdir(parents=True)
                (root / folder / sentinel).touch()
                call.return_value.stdout = "Ran 3 tests in 0.01s\nOK\n"
                self.assertTrue(run_tests(root, target).startswith("PASS"))
                expected = [sys.executable, "-m", "unittest", "discover", "-s", folder]
                if target != "windows":
                    expected += ["-p", "test_*.py"]
                self.assertEqual(call.call_args.args[0], expected + ["-v"])
                self.assertTrue(call.call_args.kwargs["check"])

    def test_empty_or_skipped_suite_is_not_pass(self):
        with tempfile.TemporaryDirectory() as tmp, patch("packaging_checks.subprocess.run") as call:
            root = Path(tmp)
            folder = root / "packaging/linux"
            folder.mkdir(parents=True)
            (folder / "test_verify_runtime.py").touch()
            call.return_value.stdout = "Ran 0 tests in 0.0s\nOK\n"
            with self.assertRaises(RuntimeError):
                run_tests(root, "linux")
            call.return_value.stdout = "Ran 2 tests in 0.01s\nOK (skipped=1)\n"
            self.assertTrue(run_tests(root, "linux").startswith("PARTIAL"))
            call.side_effect = subprocess.CalledProcessError(1, ["unittest"])
            with self.assertRaises(subprocess.CalledProcessError):
                run_tests(root, "linux")

    def test_fixture_requires_lock_and_exact_pin(self):
        with tempfile.TemporaryDirectory() as tmp, patch("packaging_checks.subprocess.run") as call, patch("packaging_checks.importlib.metadata.version") as version:
            root = Path(tmp)
            (root / MAC_FIXTURE).parent.mkdir(parents=True)
            (root / MAC_FIXTURE).touch()
            self.assertTrue(run_fixture(root).startswith("BLOCKED"))
            call.assert_not_called()
            (root / MAC_LOCK).parent.mkdir(parents=True)
            (root / MAC_LOCK).touch()
            version.return_value = "6.0"
            with self.assertRaises(RuntimeError):
                run_fixture(root)
            self.assertIn("--require-hashes", call.call_args.args[0])
            call.reset_mock()
            version.return_value = "6.22.2"
            self.assertTrue(run_fixture(root).startswith("PASS"))
            self.assertEqual(call.call_args_list[1].args[0], ["bash", str(MAC_FIXTURE)])
