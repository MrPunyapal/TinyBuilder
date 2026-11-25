import errno
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from tinybuilder.runtime import RuntimeFailure
from tinybuilder.runtime.processes import spawn, spawn_owned, terminate_owned


class ProcessTests(unittest.TestCase):
    def test_spawn_arguments_and_credentials(self):
        exe = Path(sys.executable).resolve()
        model = exe.parent / "private model.gguf"
        with patch("tinybuilder.runtime.processes.spawn_owned") as owned:
            spawn(exe, model, 12345, "test-alias", "secret-session")
        argv, cwd, env = owned.call_args.args
        self.assertEqual(argv[0], str(exe))
        self.assertEqual(argv[argv.index("--model") + 1], str(model))
        self.assertEqual(argv[argv.index("--host") + 1], "127.0.0.1")
        self.assertEqual(argv[argv.index("--device") + 1], "none")
        self.assertEqual(argv[argv.index("--n-gpu-layers") + 1], "0")
        self.assertIn("--no-webui", argv)
        self.assertIn("--no-slots", argv)
        self.assertNotIn("secret-session", argv)
        self.assertEqual(env["LLAMA_API_KEY"], "secret-session")
        self.assertEqual(cwd, str(exe.parent))

    @unittest.skipIf(os.name == "nt", "POSIX wrapper spawn error test")
    def test_spawn_errors_are_sanitized(self):
        exe = Path(sys.executable).resolve()
        for code, expected in ((errno.ENOENT, "process_spawn"), (errno.ENOEXEC, "native_loader")):
            with patch("tinybuilder.runtime.posix_supervisor.subprocess.Popen",
                       side_effect=OSError(code, "private model path")):
                with self.assertRaises(RuntimeFailure) as err:
                    spawn(exe, exe, 12345, "alias", "key")
            self.assertEqual(err.exception.kind, expected)
            self.assertEqual(err.exception.os_code, code)
            self.assertNotIn("private", str(err.exception))

    def test_owned_child_terminates(self):
        child = spawn_owned([sys.executable, "-c", "import time; time.sleep(60)"],
                            str(Path(sys.executable).resolve().parent), dict(os.environ))
        try:
            terminate_owned(child, grace=2)
            self.assertIsNotNone(child.poll())
        finally:
            if child.poll() is None:
                terminate_owned(child)

    def test_exit_code(self):
        child = spawn_owned([sys.executable, "-c", "raise SystemExit(17)"],
                            str(Path(sys.executable).resolve().parent), dict(os.environ))
        try:
            deadline = time.monotonic() + 8
            while child.poll() is None and time.monotonic() < deadline:
                time.sleep(0.05)
            self.assertEqual(child.poll(), 17)
        finally:
            terminate_owned(child)

    def test_parent_death_stops_descendant_heartbeat(self):
        # Parent exits abruptly after the owned tree is actually running.
        # No PID lookup or signals to unrelated processes; observe a private file.
        with tempfile.TemporaryDirectory() as directory:
            heartbeat = Path(directory) / "heartbeat"
            leaf = ("import pathlib,sys,time; p=pathlib.Path(sys.argv[1]); "
                    "f=p.open('ab', buffering=0); "
                    "exec('while True:\\n f.write(b\"x\")\\n time.sleep(.05)')")
            server = ("import subprocess,sys,time; "
                      "p=subprocess.Popen([sys.executable,'-c',sys.argv[1],sys.argv[2]]); "
                      "time.sleep(60)")
            parent = ("import os,sys,time,pathlib; "
                      "from tinybuilder.runtime.processes import spawn_owned; "
                      "p=spawn_owned([sys.executable,'-c',sys.argv[1],sys.argv[2],sys.argv[3]],"
                      "os.getcwd(),dict(os.environ)); "
                      "f=pathlib.Path(sys.argv[3]); end=time.monotonic()+8; "
                      "exec('while not f.exists() and time.monotonic()<end:\\n time.sleep(.05)'); "
                      "os._exit(0 if f.exists() else 2)")
            result = subprocess.run([sys.executable, "-c", parent, server, leaf, str(heartbeat)],
                                    timeout=12, capture_output=True)
            self.assertEqual(result.returncode, 0)
            self.assertTrue(heartbeat.exists())
            time.sleep(2.5)
            size = heartbeat.stat().st_size
            time.sleep(0.4)
            self.assertEqual(heartbeat.stat().st_size, size)
