import tempfile
import unittest
from pathlib import Path
from verify import architecture, inspect


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
