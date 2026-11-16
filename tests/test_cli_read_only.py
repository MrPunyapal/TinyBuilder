"""Normal read-only chat must not initialize persistent preferences."""
import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from tinybuilder.cli import main


class ReadOnlyChatTests(unittest.TestCase):
    def test_chat_with_missing_memory_store_leaves_disk_untouched(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            db = root / "not-created" / "prefs.sqlite"
            with patch("tinybuilder.cli.ChatModel") as model, \
                 contextlib.redirect_stdout(io.StringIO()):
                model.return_value.complete.return_value = {"content": "No action"}
                self.assertEqual(main(["chat", "Inspect", "--project", str(root),
                                       "--memory-db", str(db)]), 0)
            self.assertFalse(db.exists())
            self.assertFalse(db.parent.exists())


if __name__ == "__main__":
    unittest.main()
