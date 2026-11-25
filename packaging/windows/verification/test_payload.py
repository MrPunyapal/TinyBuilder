import hashlib
from pathlib import Path
import struct
import tempfile
import unittest

from payload import inventory, make_manifest, safe_relative, verify


def fake_pe(machine=0x8664):
    """Header-only test double; never executable or counted as real smoke."""
    blob = bytearray(90)
    blob[:2] = b"MZ"
    struct.pack_into("<I", blob, 60, 64)
    blob[64:68] = b"PE\0\0"
    struct.pack_into("<H", blob, 68, machine)
    struct.pack_into("<H", blob, 84, 2)
    struct.pack_into("<H", blob, 88, 0x20B)
    return blob


class PayloadTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        (self.root / "runtime").mkdir()
        (self.root / "TinyBuilder.exe").write_bytes(fake_pe())
        (self.root / "runtime/llama-server.exe").write_bytes(fake_pe())
        (self.root / "runtime/ggml.dll").write_bytes(fake_pe())
        self.pins = {p: hashlib.sha256((self.root / p).read_bytes()).hexdigest()
                     for p in ("runtime/llama-server.exe", "runtime/ggml.dll")}

    def manifest(self):
        return make_manifest(self.root, "TinyBuilder.exe",
                             "runtime/llama-server.exe", self.pins)

    def test_inventory_and_tamper(self):
        manifest = self.manifest()
        self.assertEqual(verify(self.root, manifest), 270)
        (self.root / "runtime/ggml.dll").write_bytes(fake_pe() + b"x")
        with self.assertRaises(ValueError):
            verify(self.root, manifest)
        with self.assertRaises(ValueError):
            self.manifest()

    def test_extra_runtime_file(self):
        (self.root / "runtime/extra.dll").write_bytes(fake_pe())
        with self.assertRaises(ValueError):
            self.manifest()

    def test_wrong_architecture(self):
        (self.root / "TinyBuilder.exe").write_bytes(fake_pe(0x14C))
        with self.assertRaises(ValueError):
            self.manifest()

    def test_forbidden_paths(self):
        for path in ("../other", "a/../../b", "/a", "C:/a", "a\\b",
                     "a:stream", "NUL.txt", "a/COM1", "CON .txt", "a.", "a ",
                     "a//b", ".env", "a/.env.local", "a/MODEL.GGUF",
                     "a/key.pfx", "a/cache.sqlite"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                safe_relative(path)

    def test_weights_rejected(self):
        (self.root / "weights.gguf").write_bytes(b"not weights")
        with self.assertRaises(ValueError):
            inventory(self.root)

    def test_link_rejected(self):
        link = self.root / "link"
        try:
            link.symlink_to(self.root / "runtime", target_is_directory=True)
        except OSError:
            self.skipTest("symlinks unavailable")
        with self.assertRaises(ValueError):
            inventory(self.root)

    def test_hardlink_rejected(self):
        import os
        try:
            os.link(self.root / "TinyBuilder.exe", self.root / "alias.exe")
        except OSError:
            self.skipTest("hardlinks unavailable")
        with self.assertRaises(ValueError):
            inventory(self.root)

    def test_case_collision(self):
        (self.root / "Foo").write_text("a")
        if (self.root / "foo").exists():
            self.skipTest("case-insensitive filesystem")
        (self.root / "foo").write_text("b")
        with self.assertRaises(ValueError):
            inventory(self.root)

    def test_invalid_pin_mapping(self):
        with self.assertRaises(ValueError):
            make_manifest(self.root, "TinyBuilder.exe",
                          "runtime/llama-server.exe", [])

    def test_invalid_manifest(self):
        with self.assertRaises(ValueError):
            verify(self.root, [])

    def test_missing_pin(self):
        self.pins.pop("runtime/ggml.dll")
        with self.assertRaises(ValueError):
            self.manifest()


if __name__ == "__main__":
    unittest.main()
