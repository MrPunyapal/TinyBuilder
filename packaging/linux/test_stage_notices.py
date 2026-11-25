import json
import tempfile
import unittest
from pathlib import Path

from stage_notices import stage


class NoticeTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        self.bundle = root / "bundle"
        (self.bundle / "app").mkdir(parents=True)
        (self.bundle / "runtime").mkdir()
        (self.bundle / "licenses").mkdir()
        (self.bundle / "runtime/LICENSE").write_text("llama fixture")
        for path in ("app/tinybuilder", "runtime/llama-server"):
            (self.bundle / path).write_bytes(b"\x7fELFfixture")
        self.source = root / "notices"
        self.source.mkdir()
        for name in ("CPython.txt", "PyInstaller.txt", "llama.cpp.txt"):
            (self.source / name).write_text("llama fixture" if name == "llama.cpp.txt" else "notice fixture")
        self.mapping = {"app/tinybuilder": ["PyInstaller.txt", "CPython.txt"],
                        "runtime/llama-server": ["llama.cpp.txt"]}
        self.write_mapping()

    def write_mapping(self):
        (self.source / "elf-notices.json").write_text(json.dumps(self.mapping))

    def test_complete_inventory(self):
        stage(self.bundle, self.source)
        self.assertTrue((self.bundle / "licenses/reviewed/CPython.txt").is_file())

    def test_unmapped_elf(self):
        (self.bundle / "app/extra.so").write_bytes(b"\x7fELFfixture")
        with self.assertRaises(ValueError):
            stage(self.bundle, self.source)

    def test_missing_reference(self):
        self.mapping["app/tinybuilder"] = ["missing.txt"]
        self.write_mapping()
        with self.assertRaises(ValueError):
            stage(self.bundle, self.source)

    def test_license_mismatch(self):
        (self.source / "llama.cpp.txt").write_text("different")
        with self.assertRaises(ValueError):
            stage(self.bundle, self.source)

    def test_symlink_notice(self):
        path = self.source / "CPython.txt"
        path.unlink()
        path.symlink_to(self.source / "PyInstaller.txt")
        with self.assertRaises(ValueError):
            stage(self.bundle, self.source)
