"""Reference solutions and baselines (NOT part of the trusted checker).

* `birth_death_exact`   closed-form gambler's-ruin probability (exact rational)
* `fsp_bounds`          classical finite-state-projection style bounds for a hitting
                        probability on a box:  L = P(hit B before leaving box / A),
                        U = L + P(leave box before B / A).  (Float computation; this
                        is the standard "probability mass leaving the projection"
                        bound, used here as the strongest simple truncation baseline.)
* `ssa_estimate`        direct Gillespie simulation with a rule-of-three / Wilson
                        upper confidence bound.
"""
from __future__ import annotations

import math
import random
from fractions import Fraction

from .crn import CRN
from . import checker as ck
from .synth import gauss_seidel


def birth_death_exact(lam: Fraction, mu: Fraction, N: int, x: int) -> Fraction:
    r = Fraction(mu) / Fraction(lam)
    if r == 1:
        return Fraction(x, N)
    return (r ** x - 1) / (r ** N - 1)


def fsp_bounds(crn: CRN, jB: int, lvl: int, zero, box, x0, tol=1e-13):
    interior = [x for x in ck.box_states(box) if x[jB] < lvl and not ck.taboo(zero, x)]

    def hit_val(y):
        return 1.0 if y[jB] >= lvl else 0.0

    def exit_val(y):
        if y[jB] >= lvl:
            return 0.0
        if ck.in_box(y, box):
            return 0.0  # taboo state inside the box
        return 1.0

    h = gauss_seidel(crn, interior, hit_val, 1.0, tol=tol)
    e = gauss_seidel(crn, interior, exit_val, 1.0, tol=tol)
    x0 = tuple(x0)
    return h[x0], h[x0] + e[x0], e[x0]


def ssa_estimate(crn: CRN, jB: int, lvl: int, zero, x0, n_traj: int, seed: int = 0,
                 max_steps: int = 10 ** 7):
    """Estimate P(reach level before taboo) by direct simulation of the jump chain."""
    rng = random.Random(seed)
    hits = 0
    R = len(crn.reactions)
    for _ in range(n_traj):
        x = tuple(x0)
        steps = 0
        while True:
            if x[jB] >= lvl:
                hits += 1
                break
            if ck.taboo(zero, x):
                break
            props = [crn.propf(r, x) for r in range(R)]
            a = sum(props)
            if a <= 0:
                break
            u = rng.random() * a
            acc = 0.0
            for r in range(R):
                acc += props[r]
                if u < acc:
                    break
            x = crn.nxt(r, x)
            steps += 1
            if steps > max_steps:
                break
    p_hat = hits / n_traj
    # 95% upper confidence bound (rule of three when no hits; Wilson otherwise)
    if hits == 0:
        ucb = 3.0 / n_traj
    else:
        z = 1.96
        den = 1 + z * z / n_traj
        centre = p_hat + z * z / (2 * n_traj)
        rad = z * math.sqrt(p_hat * (1 - p_hat) / n_traj + z * z / (4 * n_traj ** 2))
        ucb = (centre + rad) / den
    return {"hits": hits, "n": n_traj, "estimate": p_hat, "ucb95": ucb}
