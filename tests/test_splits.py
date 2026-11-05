import tempfile
import unittest
from pathlib import Path
from pcs.checks.splits import csv_key_disjoint

class SplitTests(unittest.TestCase):
    def test_disjoint(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); (p/'a.csv').write_text('id,x\n1,a\n2,b\n'); (p/'b.csv').write_text('id,x\n3,c\n')
            ok, detail = csv_key_disjoint(p/'a.csv', p/'b.csv', 'id')
            self.assertTrue(ok); self.assertEqual(detail['overlap_count'],0)

    def test_overlap_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); (p/'a.csv').write_text('id\n1\n2\n'); (p/'b.csv').write_text('id\n2\n3\n')
            ok, detail = csv_key_disjoint(p/'a.csv', p/'b.csv', 'id')
            self.assertFalse(ok); self.assertEqual(detail['overlap_sample'],['2'])
