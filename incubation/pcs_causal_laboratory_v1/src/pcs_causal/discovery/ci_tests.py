"""Conditional independence tests with explicit distributional assumptions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence, Tuple

import numpy as np
from scipy import stats


@dataclass(frozen=True, slots=True)
class CITestResult:
    independent: bool
    statistic: float
    p_value: float
    alpha: float
    method: str
    assumptions: Tuple[str, ...]
    n: int
    conditioning_dim: int
    notes: Tuple[str, ...]


def gaussian_partial_correlation_test(
    data: np.ndarray,
    i: int,
    j: int,
    cond: Sequence[int] = (),
    alpha: float = 0.05,
) -> CITestResult:
    """Partial correlation test under multivariate Gaussian assumptions."""
    x = np.asarray(data, dtype=float)
    n, _ = x.shape
    cond = list(cond)
    if not cond:
        r = np.corrcoef(x[:, i], x[:, j])[0, 1]
    else:
        # residualize
        Z = np.column_stack([np.ones(n), x[:, cond]])
        bi, *_ = np.linalg.lstsq(Z, x[:, i], rcond=None)
        bj, *_ = np.linalg.lstsq(Z, x[:, j], rcond=None)
        ri = x[:, i] - Z @ bi
        rj = x[:, j] - Z @ bj
        r = np.corrcoef(ri, rj)[0, 1]
    r = float(np.clip(r, -0.999999, 0.999999))
    k = len(cond)
    if n - k - 3 <= 0:
        return CITestResult(
            independent=True,
            statistic=0.0,
            p_value=1.0,
            alpha=alpha,
            method="gaussian_partial_correlation",
            assumptions=("multivariate_gaussian", "iid"),
            n=n,
            conditioning_dim=k,
            notes=("insufficient degrees of freedom; test inconclusive → treat as independent conservatively",),
        )
    z = 0.5 * np.log((1 + r) / (1 - r))
    stat = float(np.sqrt(n - k - 3) * z)
    p = float(2 * (1 - stats.norm.cdf(abs(stat))))
    return CITestResult(
        independent=p > alpha,
        statistic=stat,
        p_value=p,
        alpha=alpha,
        method="gaussian_partial_correlation",
        assumptions=("multivariate_gaussian", "iid", "linear_partial_correlation_adequacy"),
        n=n,
        conditioning_dim=k,
        notes=(
            f"alpha={alpha} threshold is a policy choice, not a causal law.",
            "Failure to reject independence ≠ proof of independence.",
        ),
    )


def discrete_g_test(
    data: np.ndarray,
    i: int,
    j: int,
    cond: Sequence[int] = (),
    alpha: float = 0.05,
) -> CITestResult:
    """G² / likelihood-ratio test on contingency tables for discrete data."""
    x = np.asarray(data)
    n = x.shape[0]
    cond = list(cond)
    # Build strata by conditioning values
    if cond:
        keys = [tuple(row) for row in x[:, cond]]
    else:
        keys = [() for _ in range(n)]
    strata: dict = {}
    for idx, key in enumerate(keys):
        strata.setdefault(key, []).append(idx)

    g = 0.0
    dof = 0
    for idxs in strata.values():
        sub = x[idxs][:, [i, j]]
        # contingency
        vals_i = sorted(set(sub[:, 0].tolist()))
        vals_j = sorted(set(sub[:, 1].tolist()))
        table = np.zeros((len(vals_i), len(vals_j)))
        map_i = {v: k for k, v in enumerate(vals_i)}
        map_j = {v: k for k, v in enumerate(vals_j)}
        for a, b in sub:
            table[map_i[a], map_j[b]] += 1
        row = table.sum(axis=1, keepdims=True)
        col = table.sum(axis=0, keepdims=True)
        total = table.sum()
        if total == 0:
            continue
        expected = row @ col / total
        mask = table > 0
        with np.errstate(divide="ignore", invalid="ignore"):
            terms = np.where(mask, table * np.log(table / expected), 0.0)
        g += float(2 * np.nansum(terms))
        dof += max((len(vals_i) - 1) * (len(vals_j) - 1), 0)

    if dof <= 0:
        p = 1.0
    else:
        p = float(1 - stats.chi2.cdf(g, dof))
    return CITestResult(
        independent=p > alpha,
        statistic=float(g),
        p_value=p,
        alpha=alpha,
        method="discrete_g_squared",
        assumptions=("multinomial_sampling", "adequate_cell_counts", "iid"),
        n=n,
        conditioning_dim=len(cond),
        notes=(
            "Sparse tables inflate type-I/II errors.",
            "alpha threshold is a policy choice.",
        ),
    )
