"""Certified finite statistical mechanics (independent of FoldBounds).

For a finite state space with rational energies E_i and inverse temperature β ≥ 0:
  Z = Σ_i exp(-β E_i)

We enclose exp via CertNum's certified series, then sum. For larger spaces we
support energy-bin bounds: if n_k states lie in energy interval [e_lo, e_hi],
their contribution is in [n_k * exp(-β e_hi), n_k * exp(-β e_lo)] for β≥0.

No claim of thermodynamic continuum limits. No FoldBounds code reused.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import List, Sequence, Tuple

from certnum.interval.interval import Enclosure, Interval
from certnum.ode.exp_enclosure import exp_enclosure


@dataclass
class ThermoCertificate:
    beta: Fraction
    Z_enclosure: Interval
    method: str
    n_states_accounted: int
    notes: str

    def to_json(self) -> dict:
        return {
            "beta": str(self.beta),
            "Z": self.Z_enclosure.to_json(),
            "method": self.method,
            "n_states_accounted": self.n_states_accounted,
            "notes": self.notes,
        }


def partition_function_exact_enum(energies: Sequence[Fraction], beta: Fraction) -> ThermoCertificate:
    if beta < 0:
        raise ValueError("beta >= 0 required for monotone energy-bin bounds")
    acc = Interval.singleton(0)
    for E in energies:
        enc = exp_enclosure(-beta * Fraction(E))
        if not enc.is_ok:
            raise RuntimeError(f"exp enclosure failed: {enc.status}")
        acc = acc.add(enc.interval)
    return ThermoCertificate(
        beta=beta,
        Z_enclosure=acc,
        method="exact_state_sum_with_certified_exp",
        n_states_accounted=len(energies),
        notes="each exp(-βE) enclosed independently; Z is sum of enclosures",
    )


def partition_function_energy_bins(
    bins: Sequence[Tuple[int, Fraction, Fraction]],
    beta: Fraction,
) -> ThermoCertificate:
    """bins: list of (count, E_lo, E_hi) with E_lo ≤ E_hi, count ≥ 0."""
    if beta < 0:
        raise ValueError("beta >= 0")
    acc = Interval.singleton(0)
    n = 0
    for count, elo, ehi in bins:
        if count < 0 or elo > ehi:
            raise ValueError("invalid bin")
        n += count
        # contrib ∈ [count*exp(-β ehi), count*exp(-β elo)]
        lo_enc = exp_enclosure(-beta * ehi)
        hi_enc = exp_enclosure(-beta * elo)
        if not lo_enc.is_ok or not hi_enc.is_ok:
            raise RuntimeError("exp failed")
        piece = Interval.mk(
            count * lo_enc.interval.lo,  # type: ignore[operator]
            count * hi_enc.interval.hi,  # type: ignore[operator]
        )
        acc = acc.add(piece)
    return ThermoCertificate(
        beta=beta,
        Z_enclosure=acc,
        method="energy_bin_bounds",
        n_states_accounted=n,
        notes="sound for β≥0; omits no states if bins partition the state space",
    )


def event_probability_bound(
    Z: Interval,
    Z_event: Interval,
) -> Interval:
    """Enclose Z_event / Z for positive Z."""
    if Z.is_empty or Z_event.is_empty:
        return Interval.empty()
    if not (Z.lo > 0):  # type: ignore[operator]
        raise ValueError("Z must be strictly positive for probability bound")
    return Z_event.div(Z).interval
