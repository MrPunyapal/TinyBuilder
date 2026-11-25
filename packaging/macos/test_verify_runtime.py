import hashlib
import os
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

    def verify(self):
        verify(self.root, hashlib.sha256(self.inventory.read_bytes()).hexdigest())

    def add_file(self, name, contents):
        (self.root / name).write_bytes(contents)
        with self.inventory.open("a") as stream:
            stream.write(hashlib.sha256(contents).hexdigest() + "  " + name + "\n")

    def test_untrusted_inventory(self):
        digest = hashlib.sha256(self.inventory.read_bytes()).hexdigest()
        self.add_file("extra", b"new")
        with self.assertRaisesRegex(ValueError, "trusted inventory digest mismatch"):
            verify(self.root, digest)

    def test_invalid_digest(self):
        with self.assertRaises(ValueError):
            verify(self.root, "")

    def test_model_magic(self):
        self.add_file("weights.bin", b"GGUFfixture")
        with self.assertRaisesRegex(ValueError, "model weights"):
            self.verify()

    def test_private_key(self):
        self.add_file("signing.p12", b"fixture")
        with self.assertRaises(ValueError):
            self.verify()

    def test_hidden_directory(self):
        (self.root / ".git").mkdir()
        with self.assertRaisesRegex(ValueError, "hidden"):
            self.verify()

    @unittest.skipUnless(hasattr(os, "link"), "hard links unavailable")
    def test_hardlink(self):
        os.link(self.server, self.root / "alias")
        with self.assertRaisesRegex(ValueError, "hard-linked"):
            self.verify()

    def test_case_collision(self):
        self.add_file("Library", b"a")
        if (self.root / "library").exists():
            self.skipTest("case-insensitive filesystem")
        self.add_file("library", b"b")
        with self.assertRaisesRegex(ValueError, "collision"):
            self.verify()

    def test_valid(self):
        self.verify()

    def test_modified(self):
        self.server.write_bytes(b"changed")
        with self.assertRaises(ValueError):
            self.verify()

    def test_unlisted(self):
        (self.root / "extra").touch()
        with self.assertRaises(ValueError):
            self.verify()

    def test_symlink(self):
        (self.root / "link").symlink_to(self.server)
        with self.assertRaises(ValueError):
            self.verify()

    def test_traversal(self):
        self.inventory.write_text("0" * 64 + "  ../llama-server\n")
        with self.assertRaises(ValueError):
            self.verify()

    def test_duplicate(self):
        self.inventory.write_text(self.inventory.read_text() * 2)
        with self.assertRaises(ValueError):
            self.verify()

    def test_executable(self):
        self.server.chmod(0o644)
        with self.assertRaises(ValueError):
            self.verify()


if __name__ == "__main__":
    unittest.main()
