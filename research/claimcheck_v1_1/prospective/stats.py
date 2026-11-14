"""Statistics for the prospective evaluation: proportions when claims are clustered within papers.

Claims from one paper are not independent (same authors, same data, same writing habits).  Every
proportion is therefore reported three ways, and an acceptance criterion uses the most conservative:

  * exact (Clopper-Pearson) bounds that ignore clustering              -- shown, never used alone
  * the same bounds on the effective sample size n / design effect   -- design effect from the
    between-paper intraclass correlation of the outcome
  * the paper-level proportion (papers with at least one event)       -- exact bounds over papers
  * a paper-level bootstrap percentile interval                       -- resampling whole papers

Standard library only; deterministic given the seed.
"""
from __future__ import annotations

import math
import random
from fractions import Fraction


def _binom_cdf(k: int, n: int, p: float) -> float:
    """P(X <= k) for X ~ Binomial(n, p), summed in log space."""
    if k < 0:
        return 0.0
    if k >= n:
        return 1.0
    if p <= 0:
        return 1.0
    if p >= 1:
        return 0.0
    logs = [math.lgamma(n + 1) - math.lgamma(i + 1) - math.lgamma(n - i + 1) + i * math.log(p) + (n - i) * math.log1p(-p) for i in range(k + 1)]
    top = max(logs)
    return min(1.0, math.exp(top) * sum(math.exp(x - top) for x in logs))


def upper_bound(k: int, n: float, confidence: float = 0.95) -> float:
    """One-sided exact upper confidence bound for a proportion with k events in n trials (n may be fractional)."""
    n = int(math.floor(n))
    if n <= 0:
        return 1.0
    k = min(k, n)
    if k >= n:
        return 1.0
    lo, hi = k / n, 1.0
    for _ in range(80):
        mid = (lo + hi) / 2
        if _binom_cdf(k, n, mid) > 1 - confidence:
            lo = mid
        else:
            hi = mid
    return hi


def lower_bound(k: int, n: float, confidence: float = 0.95) -> float:
    n = int(math.floor(n))
    if n <= 0 or k <= 0:
        return 0.0
    return 1.0 - upper_bound(n - k, n, confidence)


def intraclass_correlation(clusters: list[tuple[int, int]]) -> float:
    """ANOVA estimator of the ICC of a binary outcome; clusters are (events, size).  Clamped to [0, 1]."""
    clusters = [(k, n) for k, n in clusters if n > 0]
    big_n = sum(n for _k, n in clusters)
    c = len(clusters)
    if c < 2 or big_n <= c:
        return 1.0                                   # cannot be estimated: assume the worst
    p = sum(k for k, _n in clusters) / big_n
    if p in (0.0, 1.0):
        return 0.0                                   # no variation observed; see paper-level bounds for the conservative view
    msb = sum(n * (k / n - p) ** 2 for k, n in clusters) / (c - 1)
    msw = sum(k * (1 - k / n) for k, n in clusters) / (big_n - c)
    n0 = (big_n - sum(n * n for _k, n in clusters) / big_n) / (c - 1)
    denom = msb + (n0 - 1) * msw
    return max(0.0, min(1.0, (msb - msw) / denom)) if denom > 0 else 0.0


def design_effect(clusters: list[tuple[int, int]]) -> float:
    clusters = [(k, n) for k, n in clusters if n > 0]
    if not clusters:
        return 1.0
    big_n = sum(n for _k, n in clusters)
    weighted_size = sum(n * n for _k, n in clusters) / big_n       # size experienced by an average claim
    return 1.0 + (weighted_size - 1.0) * intraclass_correlation(clusters)


def bootstrap_interval(clusters: list[tuple[int, int]], *, reps: int = 10000, seed: int = 20261112, confidence: float = 0.95) -> tuple[float, float]:
    clusters = [(k, n) for k, n in clusters if n > 0]
    if not clusters:
        return (0.0, 1.0)
    rng = random.Random(seed)
    stats = []
    for _ in range(reps):
        sample = [clusters[rng.randrange(len(clusters))] for _ in clusters]
        n = sum(x[1] for x in sample)
        stats.append(sum(x[0] for x in sample) / n if n else 0.0)
    stats.sort()
    a = (1 - confidence) / 2
    return stats[int(a * reps)], stats[min(reps - 1, int((1 - a) * reps))]


def proportion(clusters: list[tuple[int, int]], confidence: float = 0.95) -> dict:
    """Everything reported for one proportion.  ``clusters`` holds one (events, opportunities) pair per paper."""
    clusters = [(k, n) for k, n in clusters if n > 0]
    k, n = sum(c[0] for c in clusters), sum(c[1] for c in clusters)
    papers = len(clusters)
    papers_with_event = sum(1 for c in clusters if c[0] > 0)
    deff = design_effect(clusters)
    n_eff = n / deff if deff > 0 else 0
    k_eff = math.ceil(k / deff) if deff > 0 else k
    lo, hi = bootstrap_interval(clusters, confidence=confidence) if clusters else (0.0, 1.0)
    out = {
        "events": k, "opportunities": n, "papers": papers, "papers_with_at_least_one_event": papers_with_event,
        "estimate": (k / n) if n else None,
        "design_effect": round(deff, 3), "effective_opportunities": round(n_eff, 1),
        "upper_bound_ignoring_clustering": upper_bound(k, n, confidence),
        "upper_bound_design_effect_adjusted": upper_bound(k_eff, n_eff, confidence),
        "lower_bound_design_effect_adjusted": lower_bound(max(0, math.floor(k / deff)), n_eff, confidence) if deff > 0 else 0.0,
        "paper_level_estimate": (papers_with_event / papers) if papers else None,
        "paper_level_upper_bound": upper_bound(papers_with_event, papers, confidence),
        "bootstrap_interval_over_papers": [lo, hi],
    }
    out["conservative_upper_bound"] = max(out["upper_bound_design_effect_adjusted"], out["bootstrap_interval_over_papers"][1])
    return out


def papers_needed_for_zero_events(bound: float, confidence: float = 0.95) -> int:
    """Smallest number of independent units with zero events whose exact upper bound is at most ``bound``."""
    return math.ceil(math.log(1 - confidence) / math.log(1 - bound))


__all__ = ["upper_bound", "lower_bound", "intraclass_correlation", "design_effect", "bootstrap_interval", "proportion",
           "papers_needed_for_zero_events", "Fraction"]
