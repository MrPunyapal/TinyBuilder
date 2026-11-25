import tempfile
import unittest
from pathlib import Path
from verify import architecture, inspect, smoke
from unittest.mock import patch
import subprocess


class VerificationTests(unittest.TestCase):
    def test_inventory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "LICENSE").write_bytes(b"abc")
            report = inspect(root, "x64", ["LICENSE"])
            self.assertEqual(report["installed_file_bytes"], 3)
            self.assertEqual(len(report["files"]["LICENSE"]["sha256"]), 64)

    def test_missing_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                inspect(Path(tmp), "x64", ["LICENSE"])

    def test_forbidden(self):
        for name, data in [("MODEL.GGUF", b""), ("renamed.dat", b"GGUF"), (".env", b""), ("renamed.db", b"")]:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                (root / name).write_bytes(data)
                with self.assertRaises(ValueError):
                    inspect(root, "x64", [])

    def test_elf_arch(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "app"
            header = bytearray(64)
            header[:6] = b"\x7fELF\x02\x01"
            header[18:20] = (62).to_bytes(2, "little")
            path.write_bytes(header)
            self.assertEqual(architecture(path), "x64")
            path.write_bytes(b"not executable")
            self.assertIsNone(architecture(path))

    def test_wrong_arch_library(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            header = bytearray(64)
            header[:6] = b"\x7fELF\x02\x01"
            header[18:20] = (183).to_bytes(2, "little")
            (root / "library.so").write_bytes(header)
            with self.assertRaises(ValueError):
                inspect(root, "x64", [])

    def test_contained_link_policy(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "actual").write_text("safe")
            try:
                (root / "alias").symlink_to("actual")
            except OSError:
                self.skipTest("Symlink creation unavailable on this runner")
            with self.assertRaises(ValueError):
                inspect(root, "x64", [])
            self.assertEqual(inspect(root, "x64", [], allow_contained_links=True)["links"], {"alias": "actual"})
            (root / "alias").unlink()
            (root / "alias").symlink_to("../outside")
            with self.assertRaises(ValueError):
                inspect(root, "x64", [], allow_contained_links=True)

    def test_smoke_commands_are_bounded_and_explicit(self):
        with tempfile.TemporaryDirectory() as tmp, patch("verify.subprocess.run") as run:
            result = smoke(Path(tmp), "app", "server")
            self.assertEqual(len(result), 4)
            self.assertEqual(run.call_count, 4)
            for call in run.call_args_list:
                self.assertFalse(call.kwargs["shell"])
                self.assertTrue(call.kwargs["check"])
                self.assertEqual(call.kwargs["timeout"], 30)

    def test_smoke_failure_is_not_success(self):
        with tempfile.TemporaryDirectory() as tmp, patch("verify.subprocess.run", side_effect=subprocess.TimeoutExpired("private", 30)):
            with self.assertRaisesRegex(ValueError, "^Smoke check failed: app_help$"):
                smoke(Path(tmp), "app", "server")
