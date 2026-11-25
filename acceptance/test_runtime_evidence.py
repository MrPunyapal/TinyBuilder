import hashlib
from pathlib import Path
import stat
import tempfile
import unittest
import zipfile

from runtime_evidence import inspect


class RuntimeEvidenceTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name) / "runtime.zip"

    def digest(self):
        return hashlib.sha256(self.path.read_bytes()).hexdigest()

    def test_regular_and_symlink_reported_not_extracted(self):
        with zipfile.ZipFile(self.path, "w") as z:
            z.writestr("bin/llama-server", b"not an executable")
            link = zipfile.ZipInfo("bin/libfoo.so")
            link.create_system = 3
            link.external_attr = (stat.S_IFLNK | 0o777) << 16
            z.writestr(link, "libfoo.so.1")
        rows = inspect(self.path, self.digest())
        self.assertEqual([r["kind"] for r in rows], ["regular", "symlink"])
        self.assertEqual(rows[0]["sha256"], hashlib.sha256(b"not an executable").hexdigest())
        self.assertEqual(list(self.path.parent.iterdir()), [self.path])

    def test_wrong_hash_rejected(self):
        with zipfile.ZipFile(self.path, "w") as z:
            z.writestr("llama-server", b"x")
        with self.assertRaises(ValueError):
            inspect(self.path, "0" * 64)

    def test_unsafe_or_ambiguous_paths_rejected(self):
        for names in [("../x",), ("/x",), ("bin/../x",), ("A", "a"), ("a//b",)]:
            with self.subTest(names=names):
                with zipfile.ZipFile(self.path, "w") as z:
                    for name in names:
                        z.writestr(name, b"x")
                with self.assertRaises(ValueError):
                    inspect(self.path, self.digest())
