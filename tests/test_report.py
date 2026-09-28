import tempfile
import unittest
from pathlib import Path
from pcs.kernel import build_certificate
from pcs.report import write_html

class ReportTests(unittest.TestCase):
    def test_report_contains_claims_and_scope_warning(self):
        root=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as d:
            cert=build_certificate(root/'examples/biopharma_demo/manifest.json', Path(d)/'e')
            p=write_html(cert, Path(d)/'report.html')
            t=p.read_text()
            self.assertIn('C1',t)
            self.assertIn('does not by itself establish biological',t)
