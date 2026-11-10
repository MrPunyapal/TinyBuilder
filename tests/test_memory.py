import tempfile
import unittest
from pathlib import Path

from tinybuilder.memory import MemoryStore


class TestMemoryStore(unittest.TestCase):
    def test_project_scoping_and_deletion(self):
        with tempfile.TemporaryDirectory() as d:
            memory = MemoryStore(Path(d) / "memory.sqlite")
            memory.set("/project-a", "style", "pest")
            memory.set("/project-b", "style", "phpunit")
            self.assertEqual(memory.get("/project-a", "style"), "pest")
            self.assertEqual(memory.all("/project-b"), {"style": "phpunit"})
            memory.delete("/project-a", "style")
            self.assertIsNone(memory.get("/project-a", "style"))
            self.assertEqual(memory.get("/project-b", "style"), "phpunit")
