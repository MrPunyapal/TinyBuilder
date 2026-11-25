import hashlib
import tempfile
import unittest
from pathlib import Path

from verify_runtime import verify


class RuntimeVerificationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.server = self.root / "llama-server"
        self.server.write_bytes(b"fixture")
        self.server.chmod(0o755)
        self.inventory = self.root / "SHA256SUMS"
        self.inventory.write_text(hashlib.sha256(b"fixture").hexdigest() + "  llama-server\n")

    def test_valid(self):
        verify(self.root)

    def test_modified(self):
        self.server.write_bytes(b"changed")
        with self.assertRaises(ValueError):
            verify(self.root)

    def test_unlisted(self):
        (self.root / "extra").touch()
        with self.assertRaises(ValueError):
            verify(self.root)

    def test_symlink(self):
        (self.root / "link").symlink_to(self.server)
        with self.assertRaises(ValueError):
            verify(self.root)

    def test_traversal(self):
        self.inventory.write_text("0" * 64 + "  ../llama-server\n")
        with self.assertRaises(ValueError):
            verify(self.root)

    def test_duplicate(self):
        self.inventory.write_text(self.inventory.read_text() * 2)
        with self.assertRaises(ValueError):
            verify(self.root)

    def test_executable(self):
        self.server.chmod(0o644)
        with self.assertRaises(ValueError):
            verify(self.root)


if __name__ == "__main__":
    unittest.main()
