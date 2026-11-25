import hashlib
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
import zipfile

from runtime_payload import prepare
from test_payload import fake_pe


class RuntimePayloadTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name).resolve()
        self.runtime = root / "runtime"
        self.runtime.mkdir()
        self.archive = root / "fixture.zip"
        self.selection = {"llama-server.exe": "bundle/llama-server.exe",
                          "ggml.dll": "bundle/ggml.dll"}
        with zipfile.ZipFile(self.archive, "w") as source:
            for name, member in self.selection.items():
                blob = fake_pe()
                source.writestr(member, blob)
                (self.runtime / name).write_bytes(blob)
        license_bytes = b"synthetic license fixture"
        (self.runtime / "LICENSE").write_bytes(license_bytes)
        self.extra = {"LICENSE": hashlib.sha256(license_bytes).hexdigest()}
        self.catalog = SimpleNamespace(
            REVISION="fixture",
            CPU_ARCHIVES={("windows", "x64"): (
                self.archive.name, hashlib.sha256(self.archive.read_bytes()).hexdigest())})

    def prepare(self):
        return prepare(self.runtime, self.archive, self.selection,
                       self.extra, self.catalog)

    def test_manifest_contract(self):
        result = self.prepare()
        self.assertEqual(result["schema"], 1)
        self.assertEqual(result["revision"], "fixture")
        self.assertEqual(result["os"], "windows")
        self.assertEqual(result["architecture"], "x64")
        self.assertEqual(result["backend"], "cpu")
        self.assertEqual(result["executable"], "llama-server.exe")
        self.assertEqual(result["native_dependencies"], ["ggml.dll"])
        self.assertEqual(set(result["files"]), {"llama-server.exe", "ggml.dll", "LICENSE"})

    def test_wrong_archive_hash(self):
        self.archive.write_bytes(self.archive.read_bytes() + b"x")
        with self.assertRaisesRegex(ValueError, "digest mismatch"):
            self.prepare()

    def test_staged_binary_tampered(self):
        file = self.runtime / "ggml.dll"
        blob = bytearray(file.read_bytes())
        blob[2] = 42
        file.write_bytes(blob)
        with self.assertRaisesRegex(ValueError, "differs"):
            self.prepare()

    def test_extra_license_tampered(self):
        (self.runtime / "LICENSE").write_bytes(b"wrong")
        with self.assertRaisesRegex(ValueError, "digest mismatch"):
            self.prepare()

    def test_unlisted_file(self):
        (self.runtime / "unexpected.txt").write_text("unexpected")
        with self.assertRaisesRegex(ValueError, "inventory"):
            self.prepare()

    def test_wrong_member(self):
        self.selection["ggml.dll"] = "bundle/llama-server.exe"
        with self.assertRaises(ValueError):
            self.prepare()

    def test_server_must_come_from_archive(self):
        self.selection.pop("llama-server.exe")
        self.extra["llama-server.exe"] = hashlib.sha256(fake_pe()).hexdigest()
        with self.assertRaisesRegex(ValueError, "server must originate"):
            self.prepare()

    def test_existing_manifest_rejected(self):
        (self.runtime / "runtime-manifest.json").write_text("{}")
        with self.assertRaises(ValueError):
            self.prepare()


if __name__ == "__main__":
    unittest.main()
