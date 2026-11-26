import hashlib
import io
from pathlib import Path
import tarfile
import tempfile
import unittest
from runtime_upgrade_evidence import inspect_tar

class UpgradeEvidenceTests(unittest.TestCase):
    def fixture(self, root, members):
        path=root/"fixture.tar.gz"
        with tarfile.open(path,"w:gz") as archive:
            for name,kind in members:
                item=tarfile.TarInfo(name)
                if kind=="file":
                    data=b"fixture"
                    item.size=len(data)
                    archive.addfile(item,io.BytesIO(data))
                elif kind=="link":
                    item.type=tarfile.SYMTYPE
                    item.linkname="lib-real.so"
                    archive.addfile(item)
                else:
                    item.type=tarfile.FIFOTYPE
                    archive.addfile(item)
        return path,hashlib.sha256(path.read_bytes()).hexdigest()
    def test_regular_and_link_inventory(self):
        with tempfile.TemporaryDirectory() as tmp:
            p,h=self.fixture(Path(tmp),[("bin/llama-server","file"),("bin/lib.so","link")])
            records=inspect_tar(p,h)
            self.assertEqual([r["kind"] for r in records],["regular","symlink"])
            self.assertEqual(records[1]["target"],"lib-real.so")
            self.assertEqual(list(p.parent.iterdir()),[p])
            with self.assertRaises(ValueError):
                inspect_tar(p,"0"*64)
    def test_unsafe_entries(self):
        with tempfile.TemporaryDirectory() as tmp:
            for members in [[("../x","file")],[("/x","file")],[("A","file"),("a","file")],[("fifo","fifo")]]:
                with self.subTest(members=members):
                    p,h=self.fixture(Path(tmp),members)
                    with self.assertRaises(ValueError):
                        inspect_tar(p,h)
