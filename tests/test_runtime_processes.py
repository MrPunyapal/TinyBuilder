import errno
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from tinybuilder.runtime import RuntimeFailure
from tinybuilder.runtime.processes import spawn, terminate_owned


class ProcessTests(unittest.TestCase):
    def test_spawn_arguments_and_credentials(self):
        exe = Path(sys.executable).resolve()
        model = exe.parent / "private model.gguf"
        with patch("tinybuilder.runtime.processes.subprocess.Popen") as popen:
            spawn(exe, model, 12345, "test-alias", "secret-session")
        argv = popen.call_args.args[0]
        kw = popen.call_args.kwargs
        self.assertEqual(argv[0], str(exe))
        self.assertEqual(argv[argv.index("--model") + 1], str(model))
        self.assertEqual(argv[argv.index("--host") + 1], "127.0.0.1")
        self.assertEqual(argv[argv.index("--device") + 1], "none")
        self.assertEqual(argv[argv.index("--n-gpu-layers") + 1], "0")
        self.assertIn("--no-webui", argv)
        self.assertIn("--no-slots", argv)
        self.assertNotIn("secret-session", argv)
        self.assertEqual(kw["env"]["LLAMA_API_KEY"], "secret-session")
        self.assertEqual(kw["cwd"], str(exe.parent))
        self.assertFalse(kw["shell"])
        self.assertEqual(kw["stderr"], subprocess.DEVNULL)
        self.assertEqual(kw["stdout"], subprocess.DEVNULL)

    def test_spawn_errors_are_sanitized(self):
        exe = Path(sys.executable).resolve()
        for code, expected in ((errno.ENOENT, "process_spawn"), (errno.ENOEXEC, "native_loader")):
            with patch("tinybuilder.runtime.processes.subprocess.Popen",
                       side_effect=OSError(code, "private model path")):
                with self.assertRaises(RuntimeFailure) as err:
                    spawn(exe, exe, 12345, "alias", "key")
            self.assertEqual(err.exception.kind, expected)
            self.assertNotIn("private", str(err.exception))

    def test_owned_child_terminates(self):
        # No model or native runtime needed. Native OS termination of a
        # harmless Python child, separate from fake startup HTTP coverage.
        options = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt" else {
            "start_new_session": True}
        child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"], **options)
        try:
            terminate_owned(child, grace=1)
            self.assertIsNotNone(child.poll())
            terminate_owned(child)
        finally:
            if child.poll() is None:
                child.kill()
                child.wait(timeout=5)
