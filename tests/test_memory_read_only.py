"""Preference reads and absence must not write a persistent database."""
import tempfile
import unittest
from pathlib import Path
from tinybuilder.memory import MemoryStore


class ReadOnlyMemoryTests(unittest.TestCase):
    def test_missing_get_list_delete_do_not_create_memory_database(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / "nested" / "prefs.sqlite"
            memory = MemoryStore(db)
            self.assertIsNone(memory.get("project", "absent"))
            self.assertEqual(memory.all("project"), {})
            memory.delete("project", "absent")
            self.assertFalse(db.exists())
            self.assertFalse(db.parent.exists())

    def test_only_set_creates_store_and_keeps_existing_functions(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / "nested" / "prefs.sqlite"
            memory = MemoryStore(db)
            self.assertFalse(db.exists())
            memory.set("project", "runner", "Pest")
            self.assertTrue(db.is_file())
            self.assertEqual(MemoryStore(db).get("project", "runner"), "Pest")
            self.assertEqual(MemoryStore(db).all("project"), {"runner": "Pest"})
            memory.delete("project", "runner")
            self.assertEqual(memory.all("project"), {})


if __name__ == "__main__":
    unittest.main()
