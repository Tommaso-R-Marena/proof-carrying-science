"""Statistical estimation — architecturally separate from identification."""

from pcs_causal.estimation.estimators import (
    EstimationResult,
    ate_difference_in_means,
    ate_doubly_robust,
    ate_gcomputation,
    ate_ipw,
)
from pcs_causal.estimation.positivity import positivity_report

__all__ = [
    "EstimationResult",
    "ate_difference_in_means",
    "ate_ipw",
    "ate_gcomputation",
    "ate_doubly_robust",
    "positivity_report",
]
