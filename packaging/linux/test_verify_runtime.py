import hashlib
import tempfile
import unittest
from pathlib import Path
from verify_runtime import verify


class RuntimeInventoryTests(unittest.TestCase):
    def test_inventory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "runtime"
            root.mkdir()
            sums = Path(tmp) / "SHA256SUMS"
            for name in ("llama-server", "LICENSE"):
                (root / name).write_bytes(b"fixture")
            digest = hashlib.sha256(b"fixture").hexdigest()
            sums.write_text(f"{digest}  llama-server\n{digest}  LICENSE\n")
            verify(root, sums)
            (root / "llama-server").write_bytes(b"tampered")
            with self.assertRaises(ValueError):
                verify(root, sums)
            (root / "llama-server").write_bytes(b"fixture")
            (root / "extra").symlink_to(root / "LICENSE")
            with self.assertRaises(ValueError):
                verify(root, sums)
