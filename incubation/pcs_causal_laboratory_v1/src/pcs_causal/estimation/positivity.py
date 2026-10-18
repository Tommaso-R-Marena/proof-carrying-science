"""Positivity / overlap diagnostics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Tuple

import numpy as np

from pcs_causal.estimation.estimators import _logistic_propensity


@dataclass(frozen=True, slots=True)
class PositivityReport:
    n: int
    propensity_min: float
    propensity_max: float
    extreme_weight_count: int
    effective_sample_size: float
    trimming_threshold: float
    notes: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "n": self.n,
            "propensity_min": self.propensity_min,
            "propensity_max": self.propensity_max,
            "extreme_weight_count": self.extreme_weight_count,
            "effective_sample_size": self.effective_sample_size,
            "trimming_threshold": self.trimming_threshold,
            "notes": list(self.notes),
        }


def positivity_report(
    t: np.ndarray,
    x: np.ndarray,
    extreme_threshold: float = 10.0,
    trim: float = 0.05,
) -> PositivityReport:
    t = np.asarray(t, dtype=int)
    ps = _logistic_propensity(t, x)
    w = t / ps + (1 - t) / (1 - ps)
    ess = float((w.sum() ** 2) / (np.square(w).sum()))
    extreme = int(np.sum(w > extreme_threshold))
    notes = []
    if ps.min() < trim or ps.max() > 1 - trim:
        notes.append(
            "Propensity mass near 0/1 detected; identified estimands may be "
            "practically unestimable without extrapolation."
        )
    if extreme:
        notes.append(f"{extreme} units have IPW weights > {extreme_threshold}.")
    notes.append("Lack of positivity is not repaired by regularization.")
    return PositivityReport(
        n=len(t),
        propensity_min=float(ps.min()),
        propensity_max=float(ps.max()),
        extreme_weight_count=extreme,
        effective_sample_size=ess,
        trimming_threshold=trim,
        notes=tuple(notes),
    )
