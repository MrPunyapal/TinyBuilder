import unittest
from qualify_packaged_read import assess,MARKER,READ,WRITE,safe_path

class PackagedReadTests(unittest.TestCase):
    def test_exact_oracle_and_genuine_event(self):
        summary="Evidence: 1 file(s) read, 0 searches, 0 listings, 0 approved edits."
        good="\n".join([READ,MARKER,"| fixture-a","| desc-b",summary])+"\n"
        self.assertTrue(assess(good,"fixture-a","desc-b",True,0)["passed"])
        for value in [good.replace(READ+"\n",""),good.replace("| desc-b","| desc-c"),
                      good.replace("| fixture-a","|  fixture-a"),good.replace(summary,"| extra\n"+summary),
                      good.replace(READ,"| "+READ),WRITE+"\n"+good]:
            self.assertFalse(assess(value,"fixture-a","desc-b",True,0)["passed"])
        self.assertFalse(assess(good,"fixture-a","desc-b",False,0)["passed"])
        self.assertFalse(assess(good,"fixture-a","desc-b",True,1)["passed"])
    def test_package_path_validation(self):
        self.assertEqual(str(safe_path("runtime/llama-server")),"runtime/llama-server")
        for path in ["../x","/x","x//y","x/./y","C:/x","x\\y"]:
            with self.assertRaises(ValueError):
                safe_path(path)
