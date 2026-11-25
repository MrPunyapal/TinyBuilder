import hashlib
import json
import stat
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import stage_runtime as staging


class StageTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.archive = self.root / staging.ARCHIVE
        self.output = self.root / "runtime"
        self.license = self.root / "LICENSE"
        self.license.write_bytes(b"test license")

    def make_zip(self, members):
        with zipfile.ZipFile(self.archive, "w") as archive:
            for name, value in members:
                archive.writestr(name, value)
        return staging.digest(self.archive)

    def test_manifest_hashes_signed_bytes(self):
        expected = self.make_zip([("bin/llama-server", b"server"),
                                  ("bin/libggml.dylib", b"library"),
                                  ("bin/llama-cli", b"excluded")])
        blob = hashlib.sha1(b"blob 12\0test license").hexdigest()
        def sign(path):
            path.write_bytes(path.read_bytes() + b"signed")
        with patch.object(staging, "ARCHIVE_SHA256", expected), patch.object(staging, "LICENSE_BLOB", blob):
            staging.stage(self.archive, self.license, self.output, sign)
        data = json.loads((self.output / "runtime-manifest.json").read_text())
        self.assertEqual(data["schema"], 1)
        self.assertEqual(data["archive_sha256"], expected)
        self.assertEqual(data["native_dependencies"], ["libggml.dylib"])
        self.assertEqual(set(data["files"]), {"LICENSE", "llama-server", "libggml.dylib"})
        self.assertEqual(data["files"]["llama-server"], hashlib.sha256(b"serversigned").hexdigest())
        self.assertTrue((self.output / "llama-server").stat().st_mode & 0o111)

    def test_bad_digest(self):
        self.make_zip([("llama-server", b"fake")])
        with self.assertRaisesRegex(ValueError, "digest mismatch"):
            staging.extract(self.archive, self.output, "0" * 64)
        self.assertFalse(self.output.exists())

    def test_reject_traversal(self):
        expected = self.make_zip([("../llama-server", b"fake")])
        with self.assertRaisesRegex(ValueError, "unsafe archive path"):
            staging.extract(self.archive, self.output, expected)

    def test_reject_duplicate_flattened_names(self):
        expected = self.make_zip([("a/llama-server", b"a"), ("b/llama-server", b"b")])
        with self.assertRaisesRegex(ValueError, "duplicate"):
            staging.extract(self.archive, self.output, expected)

    def test_reject_native_symlink(self):
        link = zipfile.ZipInfo("lib.dylib")
        link.create_system = 3
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        expected = self.make_zip([("llama-server", b"server"), (link, b"target")])
        with self.assertRaisesRegex(ValueError, "unsafe"):
            staging.extract(self.archive, self.output, expected)

    def test_reject_wrong_license_before_extract(self):
        self.make_zip([("llama-server", b"server")])
        with self.assertRaisesRegex(ValueError, "license blob mismatch"):
            staging.stage(self.archive, self.license, self.output, lambda path: None)
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
