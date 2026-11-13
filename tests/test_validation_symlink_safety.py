"""Symlink escape regressions for disposable Laravel fixtures (no PHP/Ollama)."""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from benchmarks.evaluate import prepare_route_variant, validate_laravel_baseline
from benchmarks.validation_case import (
    VALIDATION_HIDDEN_PATH, VALIDATION_PATH, fresh_fixture_path, seed_validation,
)
from test_laravel_harness import HarnessTest


class ValidationSymlinkSafetyTests(unittest.TestCase):
    def link(self, link: Path, target: Path, directory=False):
        try:
            link.symlink_to(target, target_is_directory=directory)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"Creating test symlinks is unsupported here: {type(exc).__name__}")

    def commit(self, home):
        subprocess.run(["git", "add", "-A"], cwd=home, check=True,
                       stdout=subprocess.DEVNULL)
        subprocess.run(["git", "-c", "user.name=FixtureTest",
                        "-c", "user.email=fixture@example.invalid",
                        "commit", "-qm", "track symlink fixture"], cwd=home, check=True)

    def test_clean_tracked_route_symlink_is_rejected_before_any_fixture_write(self):
        with tempfile.TemporaryDirectory() as directory:
            top = Path(directory)
            home, output, outside = top / "baseline", top / "results", top / "private.php"
            HarnessTest().seed_repo(home)
            outside.write_text("PRIVATE: MUST STAY", encoding="utf-8")
            (home / "routes/web.php").unlink()
            self.link(home / "routes/web.php", outside)
            self.commit(home)
            # This is the original escape: is_file and git status both pass.
            self.assertTrue((home / "routes/web.php").is_file())
            self.assertEqual(subprocess.run(
                ["git", "status", "--porcelain"], cwd=home, capture_output=True,
                text=True, check=True).stdout, "")
            with self.assertRaisesRegex(ValueError, "symlinked benchmark path"):
                validate_laravel_baseline(home, output)
            self.assertEqual(outside.read_text(encoding="utf-8"), "PRIVATE: MUST STAY")
            self.assertFalse(output.exists())

    def test_symlinked_tests_directory_is_rejected_before_php_fixture_write(self):
        with tempfile.TemporaryDirectory() as directory:
            top = Path(directory)
            home, outside = top / "baseline", top / "outside-tests"
            HarnessTest().seed_repo(home)
            outside.mkdir()
            (home / "tests/Feature/.gitkeep").unlink()
            (home / "tests/Feature").rmdir()
            self.link(home / "tests/Feature", outside, directory=True)
            self.commit(home)
            with self.assertRaisesRegex(ValueError, "symlinked benchmark path"):
                validate_laravel_baseline(home, top / "out")
            self.assertEqual(list(outside.iterdir()), [])

    def test_ignored_env_symlink_is_rejected_even_when_git_status_is_clean(self):
        with tempfile.TemporaryDirectory() as directory:
            top = Path(directory)
            home, outside = top / "baseline", top / "outside-env"
            HarnessTest().seed_repo(home)
            outside.write_text("PRIVATE", encoding="utf-8")
            self.link(home / ".env", outside)
            self.assertEqual(subprocess.run(
                ["git", "status", "--porcelain"], cwd=home, capture_output=True,
                text=True, check=True).stdout, "")
            with self.assertRaisesRegex(ValueError, "symlinked benchmark path"):
                validate_laravel_baseline(home, top / "out")
            self.assertEqual(outside.read_text(encoding="utf-8"), "PRIVATE")

    def test_dangling_hidden_test_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            top = Path(directory)
            root = top / "disposable"
            (root / "tests/Feature").mkdir(parents=True)
            hidden = root / VALIDATION_HIDDEN_PATH
            outside = top / "missing-private.php"
            self.link(hidden, outside)
            self.assertFalse(hidden.exists())  # Existing is false for dangling symlinks.
            self.assertTrue(hidden.is_symlink())
            with self.assertRaisesRegex(ValueError, "symlink"):
                fresh_fixture_path(root, VALIDATION_HIDDEN_PATH)
            self.assertFalse(outside.exists())

    def test_visible_validation_test_cannot_escape_via_parent_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            top = Path(directory)
            root, outside = top / "disposable", top / "outside-tests"
            (root / "tests").mkdir(parents=True)
            outside.mkdir()
            self.link(root / "tests/Feature", outside, directory=True)
            with self.assertRaisesRegex(ValueError, "symlink"):
                seed_validation(root, "<?php\n")
            self.assertFalse((outside / Path(VALIDATION_PATH).name).exists())

    def test_direct_route_seed_cannot_follow_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            top = Path(directory)
            root, outside = top / "disposable", top / "outside.php"
            (root / "routes").mkdir(parents=True)
            outside.write_text("PRIVATE", encoding="utf-8")
            self.link(root / "routes/web.php", outside)
            with self.assertRaisesRegex(ValueError, "symlink"):
                prepare_route_variant(root, scenario="validation")
            self.assertEqual(outside.read_text(encoding="utf-8"), "PRIVATE")

    def test_normal_fresh_fixture_path_remains_usable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "tests/Feature").mkdir(parents=True)
            p = fresh_fixture_path(root, VALIDATION_HIDDEN_PATH)
            self.assertEqual(p, root / VALIDATION_HIDDEN_PATH)


if __name__ == "__main__":
    unittest.main()
