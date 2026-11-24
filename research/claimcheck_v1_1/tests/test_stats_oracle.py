"""Independent checks of prospective/stats.py.  Exact rational arithmetic and raw-data ANOVA; no code
shared with the module under test.  The point: a deterministic statistic is not thereby a correct one."""
import random
import unittest
from fractions import Fraction
from math import comb

from research.claimcheck_v1_1.prospective import stats


def exact_cdf(k: int, n: int, p: Fraction) -> Fraction:
    return sum(Fraction(comb(n, i)) * p ** i * (1 - p) ** (n - i) for i in range(k + 1))


def anova_icc(clusters):
    """One-way ANOVA estimator computed from the expanded 0/1 observations."""
    groups = [[1] * k + [0] * (n - k) for k, n in clusters if n > 0]
    c, big_n = len(groups), sum(len(g) for g in groups)
    grand = sum(map(sum, groups)) / big_n
    ssb = sum(len(g) * (sum(g) / len(g) - grand) ** 2 for g in groups)
    ssw = sum(sum((x - sum(g) / len(g)) ** 2 for x in g) for g in groups)
    msb, msw = ssb / (c - 1), ssw / (big_n - c)
    n0 = (big_n - sum(len(g) ** 2 for g in groups) / big_n) / (c - 1)
    return (msb - msw) / (msb + (n0 - 1) * msw)


class ExactBounds(unittest.TestCase):
    def test_upper_bound_solves_the_defining_equation(self):
        for n in (1, 2, 5, 29, 59, 60, 150):
            for k in sorted({0, 1, 2, n // 2, n - 1}):
                if not 0 <= k < n:
                    continue
                ub = stats.upper_bound(k, n)
                self.assertAlmostEqual(float(exact_cdf(k, n, Fraction(ub))), 0.05, places=9, msg=(k, n))
                self.assertGreaterEqual(ub, k / n)

    def test_closed_forms(self):
        for n in (1, 3, 59, 60, 149, 299):
            self.assertAlmostEqual(stats.upper_bound(0, n), 1 - 0.05 ** (1 / n), places=10)
            self.assertAlmostEqual(stats.lower_bound(n, n), 0.05 ** (1 / n), places=10)
        self.assertEqual(stats.upper_bound(5, 5), 1.0)
        self.assertEqual(stats.lower_bound(0, 5), 0.0)
        self.assertEqual(stats.upper_bound(0, 0), 1.0)

    def test_lower_bound_is_the_mirror_image_and_rounds_conservatively(self):
        for k, n in ((1, 10), (10, 40), (22, 70), (59, 60)):
            self.assertAlmostEqual(stats.lower_bound(k, n), 1 - stats.upper_bound(n - k, n), places=12)
            self.assertAlmostEqual(float(1 - exact_cdf(k - 1, n, Fraction(stats.lower_bound(k, n)))), 0.05, places=9)
        self.assertLessEqual(stats.lower_bound(10, 40.2), stats.lower_bound(10, 40))      # fractional n rounds up
        self.assertGreaterEqual(stats.upper_bound(3, 40.9), stats.upper_bound(3, 41))     # fractional n rounds down

    def test_sample_size_statements_of_the_protocol(self):
        self.assertEqual(stats.papers_needed_for_zero_events(0.05), 59)
        self.assertLessEqual(stats.upper_bound(0, 59), 0.05)
        self.assertGreater(stats.upper_bound(0, 58), 0.05)
        self.assertEqual(stats.papers_needed_for_zero_events(0.02), 149)
        self.assertEqual([stats.max_events_for_bound(n, 0.05) for n in (58, 60, 90, 120, 180)], [-1, 0, 0, 1, 3])
        self.assertEqual([stats.max_events_for_bound(n, 0.10) for n in (28, 29, 46, 60)], [-1, 0, 1, 1])
        for n, allowed, p in ((60, 0, Fraction(1, 100)), (120, 1, Fraction(1, 200)), (60, 1, Fraction(1, 20))):
            self.assertAlmostEqual(stats.acceptance_probability(n, allowed, float(p)), float(exact_cdf(allowed, n, p)), places=10)


class Clustering(unittest.TestCase):
    def test_icc_agrees_with_raw_data_anova(self):
        rng = random.Random(7)
        for _ in range(200):
            clusters = []
            for _c in range(rng.randrange(2, 12)):
                n = rng.randrange(1, 15)
                clusters.append((rng.randrange(0, n + 1), n))
            k, big_n = sum(c[0] for c in clusters), sum(c[1] for c in clusters)
            if k in (0, big_n) or big_n <= len(clusters):
                continue
            want = max(0.0, min(1.0, anova_icc(clusters)))
            self.assertAlmostEqual(stats.intraclass_correlation(clusters), want, places=10, msg=clusters)

    def test_adversarial_cluster_shapes(self):
        self.assertAlmostEqual(stats.intraclass_correlation([(5, 5), (0, 5), (0, 5)]), 1.0)          # errors come by whole paper
        self.assertEqual(stats.intraclass_correlation([(1, 2), (1, 2), (1, 2)]), 0.0)                # less than chance: clamped
        self.assertEqual(stats.intraclass_correlation([(0, 9), (0, 3)]), 0.0)                        # nothing observed
        self.assertEqual(stats.intraclass_correlation([(2, 9)]), 1.0)                                # one paper: assume the worst
        self.assertEqual(stats.design_effect([(1, 1)] * 30), 1.0)                                    # singletons: no clustering possible
        self.assertAlmostEqual(stats.design_effect([(5, 5), (0, 5), (0, 5)]), 5.0)                   # effective sample = papers

    def test_zero_events_are_not_read_as_no_clustering_when_a_floor_is_assumed(self):
        clusters = [(0, 10)] * 60
        plain = stats.proportion(clusters)
        floored = stats.proportion(clusters, icc_floor=0.25)
        self.assertAlmostEqual(plain["conservative_upper_bound"], stats.upper_bound(0, 600))
        self.assertAlmostEqual(floored["design_effect"], 1 + 9 * 0.25)
        self.assertGreater(floored["conservative_upper_bound"], 3 * plain["conservative_upper_bound"])
        self.assertAlmostEqual(floored["upper_bound_by_assumed_icc"]["1.0"], stats.upper_bound(0, 60))   # worst case: one unit per paper
        self.assertAlmostEqual(floored["paper_level_upper_bound"], stats.upper_bound(0, 60))

    def test_orderings_that_must_hold(self):
        rng = random.Random(11)
        for _ in range(100):
            clusters = [(0, 0)]
            for _c in range(rng.randrange(3, 40)):
                n = rng.randrange(1, 20)
                clusters.append((rng.choice([0, 0, 0, 1, rng.randrange(0, n + 1)]), n))
            for floor in (0.0, 0.25):
                p = stats.proportion(clusters, icc_floor=floor)
                grid = [p["upper_bound_by_assumed_icc"][str(r)] for r in stats.ICC_GRID]
                self.assertEqual(grid, sorted(grid))                                   # more clustering never tightens a bound
                self.assertLessEqual(p["estimate"], p["upper_bound_ignoring_clustering"] + 1e-12)
                self.assertLessEqual(p["upper_bound_ignoring_clustering"], p["upper_bound_design_effect_adjusted"] + 1e-12)
                self.assertLessEqual(p["upper_bound_design_effect_adjusted"], p["conservative_upper_bound"] + 1e-12)
                self.assertLessEqual(p["lower_bound_design_effect_adjusted"], p["estimate"] + 1e-12)
                self.assertGreaterEqual(p["paper_level_upper_bound"], p["paper_level_estimate"])
            self.assertLessEqual(stats.proportion(clusters)["conservative_upper_bound"], stats.proportion(clusters, icc_floor=0.25)["conservative_upper_bound"] + 1e-12)

    def test_bootstrap_is_deterministic_and_degenerate_without_events(self):
        clusters = [(1, 5), (0, 7), (0, 3), (2, 9)]
        self.assertEqual(stats.bootstrap_interval(clusters, reps=500), stats.bootstrap_interval(clusters, reps=500))
        self.assertEqual(stats.bootstrap_interval([(0, 4), (0, 6)], reps=200), (0.0, 0.0))
        lo, hi = stats.bootstrap_interval(clusters, reps=2000)
        self.assertLessEqual(lo, 3 / 24)
        self.assertGreaterEqual(hi, 3 / 24)


if __name__ == "__main__":
    unittest.main()
