import tempfile
import unittest
from pathlib import Path
from verify import architecture, inspect, smoke, native_architectures, check_provenance, required_metadata
import hashlib
import json
from unittest.mock import patch
import subprocess


class VerificationTests(unittest.TestCase):
    def test_inventory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "LICENSE").write_bytes(b"abc")
            report = inspect(root, "x64", ["LICENSE"])
            self.assertEqual(report["installed_file_bytes"], 3)
            self.assertEqual(len(report["files"]["LICENSE"]["sha256"]), 64)

    def test_missing_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                inspect(Path(tmp), "x64", ["LICENSE"])

    def test_forbidden(self):
        for name, data in [("MODEL.GGUF", b""), ("renamed.dat", b"GGUF"), (".env", b""), ("renamed.db", b"")]:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                (root / name).write_bytes(data)
                with self.assertRaises(ValueError):
                    inspect(root, "x64", [])

    def test_elf_arch(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "app"
            header = bytearray(64)
            header[:6] = b"\x7fELF\x02\x01"
            header[18:20] = (62).to_bytes(2, "little")
            path.write_bytes(header)
            self.assertEqual(architecture(path), "x64")
            path.write_bytes(b"not executable")
            self.assertIsNone(architecture(path))

    def test_wrong_arch_library(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            header = bytearray(64)
            header[:6] = b"\x7fELF\x02\x01"
            header[18:20] = (183).to_bytes(2, "little")
            (root / "library.so").write_bytes(header)
            with self.assertRaises(ValueError):
                inspect(root, "x64", [])

    def test_contained_link_policy(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "actual").write_text("safe")
            try:
                (root / "alias").symlink_to("actual")
            except OSError:
                self.skipTest("Symlink creation unavailable on this runner")
            with self.assertRaises(ValueError):
                inspect(root, "x64", [])
            self.assertEqual(inspect(root, "x64", [], allow_contained_links=True)["links"], {"alias": "actual"})
            (root / "alias").unlink()
            (root / "directory").mkdir()
            (root / "alias").symlink_to("directory", target_is_directory=True)
            with self.assertRaises(ValueError):
                inspect(root, "x64", [], allow_contained_links=True)
            (root / "alias").unlink()
            (root / "alias").symlink_to("../outside")
            with self.assertRaises(ValueError):
                inspect(root, "x64", [], allow_contained_links=True)

    def test_smoke_commands_are_bounded_and_explicit(self):
        with tempfile.TemporaryDirectory() as tmp, patch("verify.subprocess.run") as run:
            result = smoke(Path(tmp), "app", "server")
            self.assertEqual(len(result), 4)
            self.assertEqual(run.call_count, 4)
            for call in run.call_args_list:
                self.assertFalse(call.kwargs["shell"])
                self.assertTrue(call.kwargs["check"])
                self.assertEqual(call.kwargs["timeout"], 30)

    def test_smoke_failure_is_not_success(self):
        with tempfile.TemporaryDirectory() as tmp, patch("verify.subprocess.run", side_effect=subprocess.TimeoutExpired("private", 30)):
            with self.assertRaisesRegex(ValueError, "^Smoke check failed: app_help$"):
                smoke(Path(tmp), "app", "server")

    def test_unsupported_native_header_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for data in (b"MZ", b"\x7fELF\x01\x01", b"\xcf\xfa\xed\xfe"):
                with self.subTest(data=data):
                    (root / "native").write_bytes(data)
                    with self.assertRaises(ValueError):
                        inspect(root, "x64", [])

    def test_universal_mach_o_validates_slices(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            binary = root / "lib.dylib"
            data = bytearray(128)
            data[:8] = b"\xca\xfe\xba\xbe" + (2).to_bytes(4, "big")
            for index, cpu in enumerate((0x0100000C, 0x01000007)):
                offset = 64 + 32 * index
                entry = 8 + 20 * index
                data[entry:entry+4] = cpu.to_bytes(4, "big")
                data[entry+8:entry+12] = offset.to_bytes(4, "big")
                data[entry+12:entry+16] = (32).to_bytes(4, "big")
                data[offset:offset+8] = b"\xcf\xfa\xed\xfe" + cpu.to_bytes(4, "little")
            binary.write_bytes(data)
            self.assertEqual(native_architectures(binary), {"arm64", "x64"})
            self.assertEqual(inspect(root, "arm64", [])["files"]["lib.dylib"]["architectures"], ["arm64", "x64"])
            data[96:100] = b"fake"
            binary.write_bytes(data)
            with self.assertRaises(ValueError):
                inspect(root, "arm64", [])

    def test_reviewed_inventory_matches_candidate_and_contents(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            inventory = root / "reviewed.json"
            report = {"candidate_sha": "a" * 40, "artifact_sha256": "b" * 64,
                      "compressed_bytes": 10, "expected_arch": "x64",
                      "installed_file_bytes": 20, "files": {"app": {"bytes": 20}},
                      "links": {}, "required_metadata": {"license": "LICENSE"}}
            inventory.write_text(json.dumps(report), encoding="utf-8")
            digest = hashlib.sha256(inventory.read_bytes()).hexdigest()
            check_provenance(report, "b" * 64, inventory, digest)
            self.assertTrue(report["trusted_inventory_checked"])
            for changed in ({"candidate_sha": "c" * 40}, {"files": {}}, {"links": {"alias": "app"}}):
                with self.subTest(changed=changed), self.assertRaises(ValueError):
                    check_provenance(dict(report, **changed), "b" * 64, inventory, digest)
            with self.assertRaises(ValueError):
                check_provenance(report, "b" * 64, inventory, "c" * 64)
            with self.assertRaises(ValueError):
                check_provenance(report, "c" * 64, inventory, digest)
            with self.assertRaises(ValueError):
                check_provenance(report, "b" * 64, inventory)

    def test_metadata_must_be_nonempty_and_distinct(self):
        report = {"files": {name: {"bytes": 1} for name in ("LICENSE", "NOTICE", "SBOM")}}
        self.assertEqual(required_metadata(report, ["LICENSE", "NOTICE", "SBOM"])["sbom"], "SBOM")
        with self.assertRaises(ValueError):
            required_metadata(report, ["LICENSE", "LICENSE", "SBOM"])
        report["files"]["SBOM"]["bytes"] = 0
        with self.assertRaises(ValueError):
            required_metadata(report, ["LICENSE", "NOTICE", "SBOM"])

    def test_forbidden_directory_is_not_traversed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            bad = root / "private"
            bad.mkdir()
            original = Path.iterdir

            def guarded(path):
                if path == bad:
                    self.fail("Forbidden directory was traversed")
                return original(path)

            with patch.object(Path, "iterdir", guarded), self.assertRaises(ValueError):
                inspect(root, "x64", [])
