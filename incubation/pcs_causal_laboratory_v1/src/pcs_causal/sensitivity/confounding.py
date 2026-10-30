"""Unobserved confounding sensitivity (assumption-explicit, not a proof of no confounding)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

import numpy as np


@dataclass(frozen=True, slots=True)
class SensitivityResult:
    method: str
    value: float
    assumptions: Tuple[str, ...]
    interpretation: str

    def to_dict(self) -> dict:
        return {
            "method": self.method,
            "value": self.value,
            "assumptions": list(self.assumptions),
            "interpretation": self.interpretation,
        }


def linear_confounding_bias(
    treated_mean: float,
    control_mean: float,
    delta: float,
) -> SensitivityResult:
    """Bias-parameter sensitivity: observed association ± delta for confounding.

    Observed difference may be shifted by an additive bias parameter delta.
    """
    obs = treated_mean - control_mean
    return SensitivityResult(
        method="additive_bias_parameter",
        value=float(obs),
        assumptions=(
            "observed_means_correctly_estimated",
            "confounding_bias_bounded_by_delta_in_additive_scale",
        ),
        interpretation=(
            f"Observed contrast={obs:.6g}. Under |bias|≤{delta}, ATE lies in "
            f"[{obs-delta:.6g}, {obs+delta:.6g}]. This does not prove confounding is absent."
        ),
    )


def evalue_rr(risk_ratio: float) -> SensitivityResult:
    """E-value for a risk ratio (VanderWeele & Ding).

    Assumptions specific to the E-value derivation for RR; not universal.
    """
    rr = abs(float(risk_ratio))
    if rr < 1:
        rr = 1 / rr if rr > 0 else np.inf
    if rr == 1:
        ev = 1.0
    else:
        ev = float(rr + np.sqrt(rr * (rr - 1)))
    return SensitivityResult(
        method="evalue_risk_ratio",
        value=ev,
        assumptions=(
            "risk_ratio_is_the_correct_effect_scale",
            "evalue_derivation_assumptions_vanderweele_ding",
            "no_measurement_error_considered",
        ),
        interpretation=(
            f"E-value≈{ev:.4g}: an unmeasured confounder associated with treatment and "
            "outcome by RR≥E each could explain away the observed association. "
            "Not evidence that such a confounder is absent."
        ),
    )
