import tempfile
import unittest
from pathlib import Path

from tinybuilder.tools import LocalTools


class TestLocalTools(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "project"
        self.root.mkdir()
        (self.root / "hello.php").write_text("<?php echo 'hello';\n", encoding="utf-8")
        self.local = LocalTools(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def test_read_and_search(self):
        self.assertIn("hello", self.local.call("read_file", {"path": "hello.php"}))
        self.assertIn("hello.php:1", self.local.call("search_files", {"query": "hello"}))

    def test_path_cannot_escape_project(self):
        self.assertIn("outside project", self.local.call("read_file", {"path": "../../etc/passwd"}))
        writer = LocalTools(self.root, allow_write=True)
        self.assertIn("outside project", writer.call("write_file", {"path": "../bad", "content": "bad"}))

    def test_write_requires_opt_in(self):
        self.assertIn("Permission denied", self.local.call("write_file", {"path": "new.php", "content": "hi"}))
        self.assertFalse((self.root / "new.php").exists())
        self.assertIn("Wrote", LocalTools(self.root, allow_write=True).call("write_file", {"path": "new.php", "content": "hi"}))

    def test_exec_requires_opt_in(self):
        self.assertIn("Permission denied", self.local.call("run_command", {"argv": ["python", "-c", "print(1)"]}))

    def test_symlink_escape(self):
        other = Path(self.temp.name) / "secret.txt"
        other.write_text("hidden")
        (self.root / "link.txt").symlink_to(other)
        self.assertIn("outside project", self.local.call("read_file", {"path": "link.txt"}))
