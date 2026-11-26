import hashlib
import io
import json
from pathlib import Path
import stat
import tarfile
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from package_native import CPU_ARCHIVES, stage, source_notice, resolve_alias

class NativePackageTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)

    def fixture(self,platform,*,bad_link=False):
        if platform=="windows":
            path=self.root/"runtime.zip"
            names=["llama-server.exe","ggml.dll","llama.dll","llama-server-impl.dll",
                "llama-common.dll","mtmd.dll","libomp.dll","LICENSE-LLVM-OpenMP"]
            with zipfile.ZipFile(path,"w") as z:
                for name in names:
                    if bad_link and name=="ggml.dll":
                        info=zipfile.ZipInfo(name)
                        info.create_system=3
                        info.external_attr=(stat.S_IFLNK|0o777)<<16
                        z.writestr(info,"other")
                    else:
                        z.writestr(name,b"fixture")
                z.writestr("llama-cli.exe",b"excluded")
        else:
            path=self.root/"runtime.tar.gz"
            prefix="llama-b12359/"
            extension=".dylib" if platform=="macos" else ".so"
            def versioned(stem,version):
                return f"{stem}.{version}{extension}" if platform=="macos" else f"{stem}{extension}.{version}"
            with tarfile.open(path,"w:gz") as z:
                for stem in ["libggml","libllama","libllama-common","libmtmd"]:
                    real=versioned(stem,"1.0.0")
                    item=tarfile.TarInfo(prefix+real)
                    data=stem.encode()
                    item.size=len(data)
                    z.addfile(item,io.BytesIO(data))
                    link=tarfile.TarInfo(prefix+versioned(stem,"1"))
                    link.type=tarfile.SYMTYPE
                    link.linkname="../escape" if bad_link and stem=="libggml" else real
                    z.addfile(link)
                for name,data in [("llama-server",b"fixture server"),("libllama-server-impl"+extension,b"fixture library"),
                    ("LICENSE",source_notice("LICENSE")),("llama-cli",b"excluded")]:
                    item=tarfile.TarInfo(prefix+name)
                    item.size=len(data)
                    z.addfile(item,io.BytesIO(data))
        return path,hashlib.sha256(path.read_bytes()).hexdigest()

    def test_platform_stage_and_manifest(self):
        for platform,arch,target in [
            ("windows","x64","x86_64-pc-windows-msvc"),
            ("macos","arm64","aarch64-apple-darwin"),
            ("linux","x64","x86_64-unknown-linux-gnu")]:
            with self.subTest(platform=platform):
                archive,expected=self.fixture(platform)
                dest=self.root/platform
                with patch.dict(CPU_ARCHIVES,{(platform,arch):(archive.name,expected)}):
                    h=stage(archive,target,dest)
                raw=(dest/"runtime-manifest.json").read_bytes()
                self.assertEqual(h,hashlib.sha256(raw).hexdigest())
                manifest=json.loads(raw)
                self.assertEqual(manifest["revision"],"b12359")
                self.assertEqual(manifest["archive_sha256"],expected)
                self.assertEqual(set(manifest["files"]),{p.name for p in dest.iterdir()}-{"runtime-manifest.json"})
                self.assertIn("LICENSE-httplib",manifest["files"])
                self.assertIn("LICENSE-jsonhpp",manifest["files"])
                self.assertTrue(all(not p.is_symlink() for p in dest.iterdir()))
                self.assertFalse(any("llama-cli" in n for n in manifest["files"]))
                for name,sha in manifest["files"].items():
                    self.assertEqual(hashlib.sha256((dest/name).read_bytes()).hexdigest(),sha)
                if platform=="linux":
                    self.assertEqual((dest/"libggml.so.1").read_bytes(),(dest/"libggml.so.1.0.0").read_bytes())
                if platform=="macos":
                    self.assertEqual((dest/"libggml.1.dylib").read_bytes(),(dest/"libggml.1.0.0.dylib").read_bytes())

    def test_reject_selected_links(self):
        for platform,arch,target in [
            ("windows","x64","x86_64-pc-windows-msvc"),("linux","x64","x86_64-unknown-linux-gnu")]:
            archive,expected=self.fixture(platform,bad_link=True)
            with patch.dict(CPU_ARCHIVES,{(platform,arch):(archive.name,expected)}):
                with self.assertRaises(ValueError):
                    stage(archive,target,self.root/("bad-"+platform))

    def test_alias_cycles_and_missing_targets(self):
        for inventory in [
            {"a":{"kind":"symlink","target":"b"},"b":{"kind":"symlink","target":"a"}},
            {"a":{"kind":"symlink","target":"b"}},
            {"a":{"kind":"hardlink","target":"b"},"b":{"kind":"regular"}},
        ]:
            with self.assertRaises(ValueError):
                resolve_alias("a",inventory)
