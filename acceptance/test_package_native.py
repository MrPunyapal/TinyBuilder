import hashlib
import json
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from package_native import CPU_ARCHIVES, stage


class NativePackageTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.archive = self.root / "runtime.zip"

    def fixture(self, os_name, *, bad_link=False):
        prefix = "" if os_name == "windows" else "build/bin/"
        server = "llama-server.exe" if os_name == "windows" else "llama-server"
        library = {"windows": "ggml.dll", "linux": "libggml.so",
                   "macos": "libggml.dylib"}[os_name]
        with zipfile.ZipFile(self.archive, "w") as z:
            for notice in ("LICENSE-curl", "LICENSE-httplib", "LICENSE-jsonhpp", "LICENSE-linenoise"):
                z.writestr(prefix + notice, "fixture notice")
            if os_name != "windows":
                z.writestr(prefix + "LICENSE", "fixture license")
            z.writestr(prefix + server, "fixture server; never run")
            z.writestr(prefix + "llama-cli", "not included")
            if bad_link:
                info = zipfile.ZipInfo(prefix + library)
                info.create_system = 3
                info.external_attr = (stat.S_IFLNK | 0o777) << 16
                z.writestr(info, "other")
            else:
                z.writestr(prefix + library, "fixture library")
        return hashlib.sha256(self.archive.read_bytes()).hexdigest()

    def test_platform_stage_and_manifest(self):
        for platform, arch, target in [
            ("windows", "x64", "x86_64-pc-windows-msvc"),
            ("macos", "arm64", "aarch64-apple-darwin"),
            ("linux", "x64", "x86_64-unknown-linux-gnu"),
        ]:
            with self.subTest(platform=platform):
                expected = self.fixture(platform)
                dest = self.root / platform
                with patch.dict(CPU_ARCHIVES, {(platform, arch): ("fixture.zip", expected)}):
                    manifest_hash = stage(self.archive, target, dest)
                raw = (dest / "runtime-manifest.json").read_bytes()
                self.assertEqual(manifest_hash, hashlib.sha256(raw).hexdigest())
                manifest = json.loads(raw)
                self.assertEqual(manifest["archive_sha256"], expected)
                self.assertEqual(set(manifest["files"]), {p.name for p in dest.iterdir()} - {"runtime-manifest.json"})
                self.assertNotIn("llama-cli", manifest["files"])
                self.assertIn("LICENSE", manifest["files"])
                for name, sha in manifest["files"].items():
                    self.assertEqual(hashlib.sha256((dest / name).read_bytes()).hexdigest(), sha)

    def test_reject_symlink_in_selected_runtime(self):
        expected = self.fixture("linux", bad_link=True)
        with patch.dict(CPU_ARCHIVES, {("linux", "x64"): ("fixture.zip", expected)}):
            with self.assertRaises(ValueError):
                stage(self.archive, "x86_64-unknown-linux-gnu", self.root / "bad")
