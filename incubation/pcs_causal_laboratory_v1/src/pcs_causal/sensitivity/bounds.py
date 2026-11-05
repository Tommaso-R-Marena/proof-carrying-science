"""Partial identification bounds for restricted problems."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np

from pcs_causal.hypothesis.states import ScientificStatus


@dataclass(frozen=True, slots=True)
class BoundResult:
    lower: float
    upper: float
    sharp_claimed: bool
    status: ScientificStatus
    assumptions: Tuple[str, ...]
    notes: Tuple[str, ...]

    def to_dict(self) -> dict:
        return {
            "lower": self.lower,
            "upper": self.upper,
            "sharp_claimed": self.sharp_claimed,
            "status": self.status.value,
            "assumptions": list(self.assumptions),
            "notes": list(self.notes),
        }


def manski_ate_bounds(
    y: np.ndarray,
    t: np.ndarray,
    y_min: Optional[float] = None,
    y_max: Optional[float] = None,
) -> BoundResult:
    """Manski no-assumption bounds for ATE with bounded outcomes.

    Uses only the observed arm outcomes and outcome bounds — no unconfoundedness.
    """
    y = np.asarray(y, dtype=float)
    t = np.asarray(t, dtype=int)
    if y_min is None:
        y_min = float(np.min(y))
    if y_max is None:
        y_max = float(np.max(y))
    p = float(np.mean(t))
    if p <= 0 or p >= 1:
        raise ValueError("need both treated and control units")
    ey_t = float(y[t == 1].mean())
    ey_c = float(y[t == 0].mean())
    # E[Y1] ∈ [p*EY|T=1 + (1-p)*y_min, p*EY|T=1 + (1-p)*y_max]
    ey1_lo = p * ey_t + (1 - p) * y_min
    ey1_hi = p * ey_t + (1 - p) * y_max
    ey0_lo = (1 - p) * ey_c + p * y_min
    ey0_hi = (1 - p) * ey_c + p * y_max
    lower = ey1_lo - ey0_hi
    upper = ey1_hi - ey0_lo
    return BoundResult(
        lower=float(lower),
        upper=float(upper),
        sharp_claimed=True,
        status=ScientificStatus.PARTIALLY_IDENTIFIED,
        assumptions=(
            "outcome_bounded_in_[y_min,y_max]",
            "consistency",
            "no_unconfoundedness_assumed",
            "iid_sampling_for_observed_conditionals",
        ),
        notes=(
            "Sharp under the stated bounded-outcome / no-assumption setting (Manski).",
            "Interval may be wide; width is scientifically informative.",
        ),
    )
