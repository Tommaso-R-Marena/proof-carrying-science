"""Noisy experiments: exact (rational) evaluation of adaptive sequential procedures.

Mirrors PRISM/Probabilistic/AnytimeValid.lean.  A procedure is given by a
`chooser(history) -> experiment index or None (stop)`; the induced decision tree
is explored exhaustively and probabilities are computed exactly with Fractions,
so the reported error probabilities are exact numbers, not Monte-Carlo estimates.

Rejection rules compared:
  mixture   reject m at h iff P_m(h) <= alpha * sum_m' pi(m') P_m'(h)   (proved valid)
  posthoc   reject m at h iff P_m(h) <= alpha * max_m' P_m'(h)          (proved invalid in general)
"""
from __future__ import annotations

from fractions import Fraction
from typing import Callable, Dict, List, Optional, Sequence


class NoisyModelSpace:
    def __init__(self, lik: Sequence[Sequence[Sequence[Fraction]]], q: Sequence[Fraction]):
        """lik[m][e][o] exact rational likelihoods (rows sum to 1)."""
        self.lik = lik
        self.q = list(q)
        self.n = len(lik)
        self.k = len(lik[0])
        for m in range(self.n):
            for e in range(self.k):
                row = lik[m][e]
                if any(x < 0 for x in row) or sum(row, Fraction(0)) != 1:
                    raise ValueError("likelihood rows must be nonnegative and sum to 1")


def noisy_from_deterministic(P, models: List[int], delta: Fraction) -> NoisyModelSpace:
    """Each assay reports the model's predicted outcome w.p. 1-delta, otherwise a
    uniformly random *other* outcome (exact rational noise model)."""
    lik = []
    for m in models:
        rows = []
        for e in range(P.k):
            r = len(P.outcomes[e])
            if r == 1:
                rows.append([Fraction(1)])
                continue
            row = [delta / (r - 1)] * r
            row[P.obs[m][e]] = 1 - delta
            rows.append(row)
        lik.append(rows)
    return NoisyModelSpace(lik, [P.q[m] for m in models])


def hist_prob(S: NoisyModelSpace, m: int, h) -> Fraction:
    p = Fraction(1)
    for e, o in h:
        p *= S.lik[m][e][o]
    return p


def rejected(S, m, h, alpha, pi, rule) -> bool:
    pm = hist_prob(S, m, h)
    if rule == "mixture":
        ref = sum((pi[j] * hist_prob(S, j, h) for j in range(S.n)), Fraction(0))
    elif rule == "posthoc":
        ref = max(hist_prob(S, j, h) for j in range(S.n))
    else:
        raise ValueError(rule)
    return pm <= alpha * ref


def evaluate(S: NoisyModelSpace, chooser: Callable, alpha: Fraction, pi: Sequence[Fraction],
             rule: str, claim: Callable[[int], bool], max_depth: int) -> Dict:
    """Exact probabilities, for every true model, that the procedure (with optional
    stopping as soon as the claim is certified) certifies `claim` (i.e. rejects every
    model violating it at some time).  Returns per-model certification probability."""
    violators = [m for m in range(S.n) if not claim(m)]
    res = {m: Fraction(0) for m in range(S.n)}
    leaves = [0]

    def rec(h, ever, prob):
        # ever: set of models rejected at some prefix
        if all(v in ever for v in violators):
            for m in range(S.n):
                res[m] += prob[m]
            leaves[0] += 1
            return
        e = None if len(h) >= max_depth else chooser(h, ever)
        if e is None:
            leaves[0] += 1
            return
        for o in range(len(S.lik[0][e])):
            h2 = h + [(e, o)]
            ever2 = set(ever) | {m for m in range(S.n) if rejected(S, m, h2, alpha, pi, rule)}
            prob2 = [prob[m] * S.lik[m][e][o] for m in range(S.n)]
            if all(p == 0 for p in prob2):
                continue
            rec(h2, ever2, prob2)

    ever0 = {m for m in range(S.n) if rejected(S, m, [], alpha, pi, rule)}
    rec([], ever0, [Fraction(1)] * S.n)
    return {"certify_prob": res, "leaves": leaves[0]}
