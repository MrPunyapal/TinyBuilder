import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from build_grounded_pilot import build,export,FAMILIES

class PilotTests(unittest.TestCase):
    def test_split_and_reproducibility(self):
        rows=build(42,5)
        self.assertEqual(rows,build(42,5))
        self.assertNotEqual(rows,build(43,5))
        groups=[{r["family"] for r in group} for group in rows.values()]
        self.assertFalse(any(a&b for i,a in enumerate(groups) for b in groups[i+1:]))
        self.assertEqual([len(r) for r in rows.values()],[15,5,10])
        for group in rows.values():
            for row in group:
                self.assertNotIn("pyproject.toml",row["input"])
                self.assertTrue(row["instruction"])
                self.assertTrue(row["output"])
    def test_manifest_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/"pilot"
            export(root,42,5)
            manifest=json.loads((root/"manifest.json").read_text())
            self.assertFalse(manifest["training_authorized"])
            for split in FAMILIES:
                data=(root/f"{split}.jsonl").read_bytes()
                self.assertEqual(hashlib.sha256(data).hexdigest(),manifest["splits"][split]["sha256"])
                self.assertTrue(all(set(json.loads(line))=={"instruction","input","output"} for line in data.splitlines()))
            with self.assertRaises(FileExistsError):
                export(root,42,5)
