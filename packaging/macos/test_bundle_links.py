import tempfile
import unittest
from pathlib import Path

from check_bundle_links import verify_links


class BundleLinksTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name) / "bundle"
        self.root.mkdir()
        (self.root / "target").write_text("fixture")

    def test_relative_contained(self):
        (self.root / "link").symlink_to("target")
        verify_links(self.root)

    def test_absolute_contained_not_relocatable(self):
        (self.root / "link").symlink_to(self.root / "target")
        with self.assertRaisesRegex(ValueError, "absolute"):
            verify_links(self.root)

    def test_escape(self):
        (self.root.parent / "outside").touch()
        (self.root / "link").symlink_to("../outside")
        with self.assertRaisesRegex(ValueError, "escaping"):
            verify_links(self.root)

    def test_dangling(self):
        (self.root / "link").symlink_to("missing")
        with self.assertRaises(FileNotFoundError):
            verify_links(self.root)


if __name__ == "__main__":
    unittest.main()
