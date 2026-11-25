"""Synthetic ELF fixtures; no inference server or model needed."""
import platform
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


@unittest.skipUnless(platform.system() == "Linux" and platform.machine() == "x86_64"
                     and shutil.which("gcc") and shutil.which("readelf"),
                     "requires Linux x64 gcc and binutils")
class AuditTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name) / "bundle space"
        (self.root / "app").mkdir(parents=True)
        (self.root / "runtime").mkdir()
        self.compile(self.root / "app/tinybuilder", "$ORIGIN")
        self.compile(self.root / "runtime/llama-server", "$ORIGIN")

    def compile(self, output, runpath):
        subprocess.run(["gcc", "-x", "c", "-shared", "-nostdlib", "-fPIC",
                        "-Wl,-rpath," + runpath, "-o", str(output), "-"],
                       input=b"int fixture(void) { return 0; }\n", check=True)

    def audit(self):
        return subprocess.run(["bash", str(Path(__file__).with_name("audit.sh")),
                               str(self.root)], capture_output=True, text=True)

    def test_relocatable_fixture(self):
        result = self.audit()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_unsafe_runpaths(self):
        for path in ("/tmp/build", ".", "$ORIGIN/..", "$ORIGIN:", ":$ORIGIN"):
            with self.subTest(path=path):
                self.compile(self.root / "runtime/llama-server", path)
                self.assertNotEqual(self.audit().returncode, 0)

    def test_non_elf_server(self):
        (self.root / "runtime/llama-server").write_text("not ELF")
        self.assertNotEqual(self.audit().returncode, 0)

    def test_missing_executable_permission(self):
        (self.root / "runtime/llama-server").chmod(0o644)
        self.assertNotEqual(self.audit().returncode, 0)

    def test_escaping_link(self):
        (self.root / "app/escape").symlink_to("/etc/passwd")
        self.assertNotEqual(self.audit().returncode, 0)

    def test_absolute_internal_link_is_not_relocatable(self):
        (self.root / "app/absolute").symlink_to(self.root / "app/tinybuilder")
        self.assertNotEqual(self.audit().returncode, 0)

    def test_relative_internal_link(self):
        (self.root / "app/relative").symlink_to("tinybuilder")
        self.assertEqual(self.audit().returncode, 0)
