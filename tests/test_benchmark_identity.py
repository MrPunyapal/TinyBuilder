import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from benchmarks.identity import sha256_file
from benchmarks.rust_patch_validation import verify_model


class BenchmarkIdentityTests(unittest.TestCase):
    def test_identity_without_python_311_file_digest(self):
        data = b"known bytes" * 100_000
        expected = hashlib.sha256(data).hexdigest()
        with TemporaryDirectory() as temporary:
            model = Path(temporary) / "test.gguf"
            model.write_bytes(data)
            with patch.object(hashlib, "file_digest", side_effect=AssertionError, create=True):
                self.assertEqual(sha256_file(model), expected)
                verify_model(model, expected)
                with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                    verify_model(model, "0" * 64)
