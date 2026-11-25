import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from prepare_manifest import digest, prepare


class ManifestTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        base = Path(tmp.name)
        self.root = base / "runtime"
        self.root.mkdir()
        for name in ("llama-server", "libggml.so.1", "LICENSE"):
            (self.root / name).write_bytes(name.encode())
        self.sums = base / "SHA256SUMS"
        self.inventory()
        self.archive = base / "fixture.zip"
        with zipfile.ZipFile(self.archive, "w") as z:
            for p in self.root.iterdir():
                z.write(p, "nested/" + p.name)
        self.pin = (self.archive.name, digest(self.archive))

    def inventory(self):
        self.sums.write_text("".join(f"{digest(p)}  {p.name}\n" for p in self.root.iterdir()))

    def test_manifest(self):
        prepare(self.root, self.sums, self.archive, self.pin, "fixture-revision")
        data = json.loads((self.root / "runtime-manifest.json").read_text())
        self.assertEqual(data["native_dependencies"], ["libggml.so.1"])
        self.assertEqual(data["archive_sha256"], self.pin[1])
        self.assertEqual(data["files"]["llama-server"], digest(self.root / "llama-server"))
        self.assertEqual(data["revision"], "fixture-revision")

    def test_wrong_pin(self):
        with self.assertRaises(ValueError):
            prepare(self.root, self.sums, self.archive, (self.archive.name, "0" * 64), "fixture")

    def test_rehashed_modified_binary(self):
        (self.root / "llama-server").write_bytes(b"replacement")
        self.inventory()
        with self.assertRaises(ValueError):
            prepare(self.root, self.sums, self.archive, self.pin, "fixture")

    def test_ambiguous_binary(self):
        with zipfile.ZipFile(self.archive, "a") as z:
            z.writestr("other/llama-server", b"duplicate")
        with self.assertRaises(ValueError):
            prepare(self.root, self.sums, self.archive, (self.archive.name, digest(self.archive)), "fixture")
