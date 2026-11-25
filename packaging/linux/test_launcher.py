import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


@unittest.skipUnless(os.name == "posix" and shutil.which("realpath"), "requires POSIX realpath")
class LauncherTests(unittest.TestCase):
    def test_relocation_arguments_cwd_and_loader_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = root / "bundle with spaces"
            (bundle / "app").mkdir(parents=True)
            launcher = bundle / "tinybuilder"
            shutil.copyfile(Path(__file__).with_name("launch.sh"), launcher)
            launcher.chmod(0o755)
            stub = bundle / "app/tinybuilder"
            stub.write_text('#!/bin/sh\nprintf "%s\\n" "$PWD" "${LD_LIBRARY_PATH-unset}" "${LD_LIBRARY_PATH_ORIG-unset}" "$@"\nexit 7\n')
            stub.chmod(0o755)
            project = root / "project with spaces"
            project.mkdir()
            link = root / "tinybuilder-link"
            link.symlink_to(launcher)
            for executable in (launcher, link):
                for original in (None, "/opt/user libs"):
                    with self.subTest(executable=executable, original=original):
                        env = os.environ.copy()
                        env.pop("LD_LIBRARY_PATH", None)
                        if original is not None:
                            env["LD_LIBRARY_PATH"] = original
                        env["LD_LIBRARY_PATH_ORIG"] = "/stale"
                        result = subprocess.run([str(executable), "doctor", "--project", "a b"],
                                                cwd=project, env=env, capture_output=True, text=True)
                        self.assertEqual(result.returncode, 7, result.stderr)
                        self.assertEqual(result.stdout.splitlines(),
                                         [str(project), original or "unset", "unset", "doctor", "--project", "a b"])
