"""Offline tests of the prospective-evaluation statistics."""
import unittest

from research.claimcheck_v1_1.prospective.stats import (design_effect, intraclass_correlation, lower_bound, papers_needed_for_zero_events,
                                                         proportion, upper_bound)


class Stats(unittest.TestCase):
    def test_exact_bounds(self):
        self.assertAlmostEqual(upper_bound(0, 59), 0.0495, places=3)          # rule of three, exactly
        self.assertAlmostEqual(upper_bound(0, 300), 0.00994, places=4)
        self.assertAlmostEqual(upper_bound(3, 100), 0.0757, places=3)
        self.assertEqual(upper_bound(0, 0), 1.0)
        self.assertAlmostEqual(lower_bound(30, 100), 0.2249, places=3)
        self.assertEqual(papers_needed_for_zero_events(0.05), 59)
        self.assertEqual(papers_needed_for_zero_events(0.01), 299)

    def test_clustering_makes_bounds_wider(self):
        independent = [(1, 10)] * 10                      # 10 % in every paper: no clustering
        clustered = [(10, 10)] + [(0, 10)] * 9            # the same 10 %, all in one paper
        self.assertAlmostEqual(intraclass_correlation(independent), 0.0, places=6)
        self.assertGreater(intraclass_correlation(clustered), 0.9)
        self.assertGreater(design_effect(clustered), 9)
        a, b = proportion(independent), proportion(clustered)
        self.assertEqual(a["estimate"], b["estimate"])
        self.assertGreater(b["conservative_upper_bound"], a["upper_bound_ignoring_clustering"])
        self.assertEqual(b["papers_with_at_least_one_event"], 1)

    def test_zero_events_fall_back_to_paper_level(self):
        p = proportion([(0, 12)] * 20)
        self.assertEqual(p["events"], 0)
        self.assertAlmostEqual(p["paper_level_upper_bound"], upper_bound(0, 20), places=9)
        self.assertGreater(p["paper_level_upper_bound"], p["upper_bound_ignoring_clustering"])    # 20 papers bound less than 240 claims would


if __name__ == "__main__":
    unittest.main()
