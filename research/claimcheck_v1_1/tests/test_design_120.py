"""The committed design tables (protocol 10a) are what design_120.py computes with stats.py."""
import json
import unittest
from pathlib import Path

from research.claimcheck_v1_1.prospective import design_120

COMMITTED = Path(__file__).resolve().parents[1] / "prospective" / "DESIGN_120.json"


class DesignTables(unittest.TestCase):
    def test_committed_tables_are_reproducible(self):
        self.assertEqual(json.loads(COMMITTED.read_text(encoding="utf-8")), json.loads(json.dumps(design_120.tables())))

    def test_the_larger_design_removes_the_zero_tolerance_of_c2(self):
        small, large = design_120.tables()["designs"]
        self.assertEqual(small["statistics"]["C2b_affected_papers_allowed"], 0)
        self.assertEqual(large["statistics"]["C2b_affected_papers_allowed"], 1)
        self.assertEqual(small["statistics"]["C2a_upper_bound_by_exposed_numbers_per_paper"]["4"]["flags_allowed"], -1)
        self.assertEqual(large["costs"]["model_calls"], 480)
        self.assertEqual(large["costs"]["http_requests_worst_case"], 1920)


if __name__ == "__main__":
    unittest.main()
