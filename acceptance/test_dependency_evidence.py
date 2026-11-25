import hashlib
from pathlib import Path
import tempfile
import unittest
import zipfile

from dependency_evidence import collect, wheel_record


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.path = self.root / "pyinstaller-6.22.2-py3-none-any.whl"
        with zipfile.ZipFile(self.path, "w") as wheel:
            wheel.writestr("pyinstaller-6.22.2.dist-info/METADATA",
                           "Metadata-Version: 2.1\nName: PyInstaller\nVersion: 6.22.2\n")
        self.digest = hashlib.sha256(self.path.read_bytes()).hexdigest()

    def lookup(self, name, version):
        self.assertEqual((name, version), ("pyinstaller", "6.22.2"))
        return {"info": {"version": version}, "urls": [{
            "filename": self.path.name, "packagetype": "bdist_wheel",
            "yanked": False, "digests": {"sha256": self.digest}}]}

    def test_exact_candidate(self):
        self.assertEqual(collect(self.root, "macos", self.lookup),
                         {"pyinstaller": ("6.22.2", self.digest)})

    def test_nested_vendored_metadata_is_not_distribution_identity(self):
        with zipfile.ZipFile(self.path, "a") as wheel:
            wheel.writestr("pkg/_vendor/example-1.dist-info/METADATA",
                           "Name: Example\nVersion: 1\n")
        self.digest = hashlib.sha256(self.path.read_bytes()).hexdigest()
        self.assertEqual(wheel_record(self.path, self.lookup),
                         ("pyinstaller", "6.22.2", self.digest))

    def test_multiple_top_level_metadata_is_rejected(self):
        with zipfile.ZipFile(self.path, "a") as wheel:
            wheel.writestr("other-1.dist-info/METADATA", "Name: Other\nVersion: 1\n")
        with self.assertRaises(ValueError):
            wheel_record(self.path, self.lookup)

    def test_wrong_hash(self):
        original = self.digest
        self.digest = "0" * 64
        with self.assertRaises(ValueError):
            wheel_record(self.path, self.lookup)
        self.digest = original

    def test_yanked(self):
        def lookup(name, version):
            result = self.lookup(name, version)
            result["urls"][0]["yanked"] = True
            return result
        with self.assertRaises(ValueError):
            collect(self.root, "macos", lookup)

    def test_wrong_target_and_nonwheel(self):
        with self.assertRaises(ValueError):
            collect(self.root, "linux", self.lookup)
        (self.root / "unexpected.tar.gz").touch()
        with self.assertRaises(ValueError):
            collect(self.root, "macos", self.lookup)
