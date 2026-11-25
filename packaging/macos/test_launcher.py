"""Portable launcher behavior using a fake executable; no inference claims."""
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent


@unittest.skipUnless(os.name == "posix" and shutil.which("bash"), "POSIX bash required")
class LauncherTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        self.app = root / "TinyBuilder space é"
        self.app.mkdir()
        self.home = root / "home"
        self.home.mkdir()
        self.project = root / "project space"
        self.project.mkdir()
        self.launcher = self.app / "TinyBuilder.command"
        shutil.copy2(HERE / "TinyBuilder.command", self.launcher)
        binary = self.app / "tinybuilder" / "tinybuilder"
        binary.parent.mkdir()
        binary.write_text('#!/bin/bash\nprintf "%s\\n" "$PWD" "$@"\nexit 23\n')
        binary.chmod(0o755)

    def invoke(self, *args):
        return subprocess.run(["bash", str(self.launcher), *args],
                              cwd=self.project, env={**os.environ, "HOME": str(self.home)},
                              text=True, capture_output=True, check=False)

    def test_no_arguments_uses_home_and_guided_app(self):
        result = self.invoke()
        self.assertEqual(result.returncode, 23)
        cwd, *args = result.stdout.splitlines()
        self.assertEqual(Path(cwd).resolve(strict=True), self.home.resolve(strict=True))
        self.assertEqual(args, ["app"])

    def test_explicit_arguments_keep_cwd_and_literal_values(self):
        result = self.invoke("doctor", "--project", "folder with spaces", "$(touch unwanted)")
        self.assertEqual(result.returncode, 23)
        cwd, *args = result.stdout.splitlines()
        self.assertEqual(Path(cwd).resolve(strict=True), self.project.resolve(strict=True))
        self.assertEqual(args, ["doctor", "--project", "folder with spaces", "$(touch unwanted)"])
        self.assertFalse((self.project / "unwanted").exists())


if __name__ == "__main__":
    unittest.main()
