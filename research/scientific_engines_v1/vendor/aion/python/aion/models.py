"""Benchmark model families (all mass-action, exact rational rates)."""
from __future__ import annotations

from fractions import Fraction as Q

from .crn import CRN


def birth_death(lam=Q(1), mu=Q(2)) -> CRN:
    """Example A: X -> 2X (lam x), X -> 0 (mu x)."""
    c = CRN(["X"])
    c.add([1], [2], lam, "birth")
    c.add([1], [0], mu, "death")
    return c


def gene_expression(k_m=Q(1, 2), g_m=Q(2), k_p=Q(10), g_p=Q(1)) -> CRN:
    """Example B: bursty gene expression.  0 -> M, M -> 0, M -> M + P, P -> 0.
    Infinite in both species; protein bursts give geometric tails."""
    c = CRN(["mRNA", "P"])
    c.add([0, 0], [1, 0], k_m, "transcription")
    c.add([1, 0], [0, 0], g_m, "mRNA decay")
    c.add([1, 0], [1, 1], k_p, "translation")
    c.add([0, 1], [0, 0], g_p, "protein decay")
    return c


def degradation_modulated_growth(b=Q(1), d=Q(1), alpha=Q(10), beta=Q(1), k=Q(1, 10)) -> CRN:
    """Example C ("signalling"/enzymatic): a self-replicating species X whose
    degradation is catalysed by an independently fluctuating enzyme Y.
    X -> 2X, X -> 0, 0 -> Y, Y -> 0, X + Y -> Y.  Infinite in Y."""
    c = CRN(["X", "Y"])
    c.add([1, 0], [2, 0], b, "X birth")
    c.add([1, 0], [0, 0], d, "X death")
    c.add([0, 0], [0, 1], alpha, "Y production")
    c.add([0, 1], [0, 0], beta, "Y decay")
    c.add([1, 1], [0, 1], k, "Y degrades X")
    return c


def immigration_death(lam=Q(1), mu=Q(1)) -> CRN:
    """Recurrent chain used for negative results: 0 -> X, X -> 0."""
    c = CRN(["X"])
    c.add([0], [1], lam, "immigration")
    c.add([1], [0], mu, "death")
    return c


def schlogl_explosive() -> CRN:
    """Explosive network 2X -> 3X used for adversarial tests (no nonexplosion needed)."""
    c = CRN(["X"])
    c.add([2], [3], Q(1), "autocatalysis")
    c.add([1], [0], Q(5), "death")
    return c
