import unittest
from audit_cargo import packages,evaluate

class AuditTests(unittest.TestCase):
    def test_lock_inventory(self):
        lock=b'[[package]]\nname="app"\nversion="1.0.0"\n[[package]]\nname="dep"\nversion="2.0.0"\nsource="registry+https://github.com/rust-lang/crates.io-index"\n'
        self.assertEqual(packages(lock),[("dep","2.0.0")])
        with self.assertRaises(ValueError):
            packages(lock.replace(b"registry+https://github.com/rust-lang/crates.io-index",b"git+https://example.org"))
    def test_fail_closed(self):
        rows=[("dep","2.0.0")]
        for data in [{},{"results":[]},{"results":[{"next_page_token":"more"}]}]:
            with self.assertRaises(ValueError):
                evaluate(rows,data)
        self.assertEqual(evaluate(rows,{"results":[{}]}),[])
        self.assertEqual(evaluate(rows,{"results":[{"vulns":[{"id":"RUSTSEC-2026-0001"}]}]}),
            [{"name":"dep","version":"2.0.0","id":"RUSTSEC-2026-0001"}])
