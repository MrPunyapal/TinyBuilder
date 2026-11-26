import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from zipfile import ZipFile

from windows_acceptance import digest, listeners, unpack


class WindowsAcceptanceTests(unittest.TestCase):
    def test_rejects_wrong_pin_and_unsafe_members_before_extracting(self):
        for member, wrong_pin, message in (
            ("candidate/build.json", True, "archive identity mismatch"),
            ("candidate/../outside", False, "Unsafe package path"),
            ("unrelated/build.json", False, "Unexpected ZIP member"),
        ):
            with self.subTest(member=member, wrong_pin=wrong_pin), TemporaryDirectory() as tmp:
                root = Path(tmp)
                archive = root / "candidate.zip"
                manifest = root / "artifact.json"
                staging = root / "staging"
                staging.mkdir()
                with ZipFile(archive, "w") as zip_file:
                    zip_file.writestr(member, "{}")
                actual = digest(archive)
                commit = "a" * 40
                manifest.write_text(json.dumps({
                    "name": archive.name,
                    "source_commit": commit,
                    "target": "x86_64-pc-windows-msvc",
                    "bytes": archive.stat().st_size,
                    "sha256": actual,
                }), encoding="utf-8")
                with self.assertRaisesRegex(ValueError, message):
                    unpack(archive, manifest, commit, "0" * 64 if wrong_pin else actual, staging)
                self.assertEqual(list(staging.iterdir()), [])


    def test_socket_inventory_includes_ipv4_and_ipv6_listeners(self):
        sockets = (
            b"TCP 127.0.0.1:1234 0.0.0.0:0 LISTENING 42\n"
            b"TCP [::]:5555 [::]:0 LISTENING 42\n"
            b"TCP 127.0.0.1:1234 127.0.0.1:3000 ESTABLISHED 42\n"
            b"TCP 0.0.0.0:5678 0.0.0.0:0 LISTENING 43\n"
        )
        with patch("windows_acceptance.subprocess.check_output", return_value=sockets):
            self.assertEqual(listeners(Path("."), 42), {"127.0.0.1:1234", "[::]:5555"})
            self.assertEqual(listeners(Path(".")), {"127.0.0.1:1234", "[::]:5555", "0.0.0.0:5678"})
