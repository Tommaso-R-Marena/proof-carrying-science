"""Defensible causal estimators with explicit assumption qualifications.

An identified parameter may still have high uncertainty. A precise estimator
may target the wrong causal quantity if identification assumptions fail.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional, Sequence, Tuple

import numpy as np

from pcs_causal.hypothesis.states import ScientificStatus


@dataclass(frozen=True, slots=True)
class EstimationResult:
    estimand: str
    estimate: float
    std_error: Optional[float]
    ci95: Optional[Tuple[float, float]]
    method: str
    assumptions: Tuple[str, ...]
    status: ScientificStatus
    notes: Tuple[str, ...]
    n: int

    def to_dict(self) -> dict:
        return {
            "estimand": self.estimand,
            "estimate": self.estimate,
            "std_error": self.std_error,
            "ci95": list(self.ci95) if self.ci95 else None,
            "method": self.method,
            "assumptions": list(self.assumptions),
            "status": self.status.value,
            "notes": list(self.notes),
            "n": self.n,
        }


def _ci(est: float, se: float) -> Tuple[float, float]:
    return (est - 1.96 * se, est + 1.96 * se)


def ate_difference_in_means(
    y: np.ndarray,
    t: np.ndarray,
) -> EstimationResult:
    """ATE under randomization / no confounding: E[Y|T=1]-E[Y|T=0]."""
    y = np.asarray(y, dtype=float)
    t = np.asarray(t, dtype=int)
    y1, y0 = y[t == 1], y[t == 0]
    if len(y1) == 0 or len(y0) == 0:
        raise ValueError("both treatment arms required")
    est = float(y1.mean() - y0.mean())
    se = float(np.sqrt(y1.var(ddof=1) / len(y1) + y0.var(ddof=1) / len(y0)))
    return EstimationResult(
        estimand="ATE",
        estimate=est,
        std_error=se,
        ci95=_ci(est, se),
        method="difference_in_means",
        assumptions=(
            "randomization_or_unconfoundedness",
            "consistency",
            "positivity",
            "iid_sampling",
            "ci_uses_asymptotic_normal_approximation",
        ),
        status=ScientificStatus.ESTIMATED_WITH_UNCERTAINTY,
        notes=(
            "CI coverage is asymptotic under stated assumptions; not exact finite-sample.",
        ),
        n=len(y),
    )


def _logistic_propensity(t: np.ndarray, x: np.ndarray) -> np.ndarray:
    """Simple L2-logistic propensity via IRLS (no sklearn dependency)."""
    x = np.asarray(x, dtype=float)
    if x.ndim == 1:
        x = x.reshape(-1, 1)
    n, p = x.shape
    X = np.column_stack([np.ones(n), x])
    beta = np.zeros(p + 1)
    for _ in range(50):
        eta = X @ beta
        p_hat = 1 / (1 + np.exp(-np.clip(eta, -30, 30)))
        w = p_hat * (1 - p_hat) + 1e-6
        z = eta + (t - p_hat) / w
        # ridge
        W = np.diag(w)
        A = X.T @ W @ X + 1e-4 * np.eye(p + 1)
        b = X.T @ W @ z
        beta_new = np.linalg.solve(A, b)
        if np.max(np.abs(beta_new - beta)) < 1e-8:
            beta = beta_new
            break
        beta = beta_new
    p_hat = 1 / (1 + np.exp(-np.clip(X @ beta, -30, 30)))
    return np.clip(p_hat, 1e-6, 1 - 1e-6)


def _linear_outcome(y: np.ndarray, t: np.ndarray, x: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """μ1(x), μ0(x) from linear regression Y ~ 1 + T + X."""
    x = np.asarray(x, dtype=float)
    if x.ndim == 1:
        x = x.reshape(-1, 1)
    n = len(y)
    X = np.column_stack([np.ones(n), t, x])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    mu1 = np.column_stack([np.ones(n), np.ones(n), x]) @ beta
    mu0 = np.column_stack([np.ones(n), np.zeros(n), x]) @ beta
    return mu1, mu0


def ate_ipw(y: np.ndarray, t: np.ndarray, x: np.ndarray) -> EstimationResult:
    y = np.asarray(y, dtype=float)
    t = np.asarray(t, dtype=int)
    ps = _logistic_propensity(t, x)
    w = t / ps - (1 - t) / (1 - ps)
    est = float(np.mean(w * y))
    se = float(np.std(w * y, ddof=1) / np.sqrt(len(y)))
    return EstimationResult(
        estimand="ATE",
        estimate=est,
        std_error=se,
        ci95=_ci(est, se),
        method="ipw_logistic_propensity",
        assumptions=(
            "unconfoundedness_given_x",
            "consistency",
            "positivity",
            "correct_logistic_propensity_model",
            "iid_sampling",
            "se_is_crude_not_sandwich",
        ),
        status=ScientificStatus.ESTIMATED_WITH_UNCERTAINTY,
        notes=(
            "Not doubly robust. Biased if propensity model misspecified.",
            "Does not prove unconfoundedness.",
        ),
        n=len(y),
    )


def ate_gcomputation(y: np.ndarray, t: np.ndarray, x: np.ndarray) -> EstimationResult:
    y = np.asarray(y, dtype=float)
    t = np.asarray(t, dtype=int)
    mu1, mu0 = _linear_outcome(y, t, x)
    est = float(np.mean(mu1 - mu0))
    # crude SE via influence of predicted contrast
    se = float(np.std(mu1 - mu0, ddof=1) / np.sqrt(len(y)))
    return EstimationResult(
        estimand="ATE",
        estimate=est,
        std_error=se,
        ci95=_ci(est, se),
        method="gcomputation_linear_outcome",
        assumptions=(
            "unconfoundedness_given_x",
            "consistency",
            "positivity",
            "correct_linear_outcome_model",
            "iid_sampling",
        ),
        status=ScientificStatus.ESTIMATED_WITH_UNCERTAINTY,
        notes=("Biased if outcome model misspecified.",),
        n=len(y),
    )


def ate_doubly_robust(y: np.ndarray, t: np.ndarray, x: np.ndarray) -> EstimationResult:
    """AIPW with logistic propensity + linear outcome.

    Consistent if either nuisance model is correct (under unconfoundedness/positivity).
    """
    y = np.asarray(y, dtype=float)
    t = np.asarray(t, dtype=int)
    ps = _logistic_propensity(t, x)
    mu1, mu0 = _linear_outcome(y, t, x)
    psi = (
        (mu1 - mu0)
        + t * (y - mu1) / ps
        - (1 - t) * (y - mu0) / (1 - ps)
    )
    est = float(np.mean(psi))
    se = float(np.std(psi, ddof=1) / np.sqrt(len(y)))
    return EstimationResult(
        estimand="ATE",
        estimate=est,
        std_error=se,
        ci95=_ci(est, se),
        method="aipw_logistic_propensity_linear_outcome",
        assumptions=(
            "unconfoundedness_given_x",
            "consistency",
            "positivity",
            "either_propensity_or_outcome_model_correct",
            "iid_sampling",
            "asymptotic_normality_for_ci",
        ),
        status=ScientificStatus.ESTIMATED_WITH_UNCERTAINTY,
        notes=(
            "Doubly robust only under the stated nuisance correctness disjunction.",
            "Finite-sample unbiasedness is not claimed.",
        ),
        n=len(y),
    )
