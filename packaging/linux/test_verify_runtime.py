import hashlib
import tempfile
import unittest
from pathlib import Path
from verify_runtime import verify


class RuntimeInventoryTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name) / "runtime"
        self.root.mkdir()
        self.sums = Path(tmp.name) / "SHA256SUMS"
        for name in ("llama-server", "LICENSE", "libggml.so.1"):
            (self.root / name).write_bytes(b"fixture")
        self.inventory()

    def inventory(self):
        self.sums.write_text("".join(
            f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n"
            for p in sorted(self.root.iterdir()) if p.is_file()))

    def test_valid_inventory(self):
        verify(self.root, self.sums)

    def test_tampering(self):
        (self.root / "llama-server").write_bytes(b"tampered")
        with self.assertRaises(ValueError):
            verify(self.root, self.sums)

    def test_symlink_even_if_hash_matches(self):
        (self.root / "libggml.so.1").unlink()
        (self.root / "libggml.so.1").symlink_to(self.root / "LICENSE")
        with self.assertRaises(ValueError):
            verify(self.root, self.sums)

    def test_forbidden_payload_even_with_valid_hash(self):
        for name in (".env", "model.GGUF", "weights.safetensors", "memory.sqlite", "key.pem", "extra.sh"):
            with self.subTest(name=name):
                p = self.root / name
                p.write_bytes(b"fixture")
                self.inventory()
                with self.assertRaises(ValueError):
                    verify(self.root, self.sums)
                p.unlink()

    def test_duplicate_and_traversal(self):
        original = self.sums.read_text()
        for suffix in (original.splitlines()[0], "0" * 64 + "  ../escape"):
            self.sums.write_text(original + suffix + "\n")
            with self.assertRaises(ValueError):
                verify(self.root, self.sums)

    def test_unlisted_file(self):
        (self.root / "NOTICE").write_bytes(b"fixture")
        with self.assertRaises(ValueError):
            verify(self.root, self.sums)

    def test_missing_license(self):
        (self.root / "LICENSE").unlink()
        self.inventory()
        with self.assertRaises(ValueError):
            verify(self.root, self.sums)
