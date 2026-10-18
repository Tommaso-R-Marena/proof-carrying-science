"""Interval Newton operator for certified root refinement.

N(I) = m - f(m)/F'(I)  (extended division when 0 ∈ F'(I) is rejected).

If N(I) ∩ I is nonempty and properly contained, uniqueness/existence follow
under standard hypotheses (f continuous, F' excludes 0 ⇒ f strictly monotone).
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Optional

from certnum.ad.forward import differentiate
from certnum.expr.ast import Expr
from certnum.expr.eval import EvalError, eval_exact, eval_interval
from certnum.interval.interval import Interval
from certnum.root.isolation import RootCertificate, RootStatus, classify_interval


@dataclass(frozen=True)
class NewtonStep:
    before: Interval
    after: Interval
    contracted: bool
    unique: bool
    notes: str

    def to_json(self) -> dict:
        return {
            "before": self.before.to_json(),
            "after": self.after.to_json(),
            "contracted": self.contracted,
            "unique": self.unique,
            "notes": self.notes,
        }


def interval_newton_step(e: Expr, var: str, I: Interval) -> Optional[NewtonStep]:
    if I.is_empty:
        return None
    m = I.midpoint()
    assert m is not None
    try:
        fm = eval_exact(e, {var: m})
    except EvalError:
        return None
    try:
        de = differentiate(e, var)
    except ValueError:
        return None
    denc = eval_interval(de, {var: I})
    if not denc.is_ok or not denc.interval.excludes_zero():
        return NewtonStep(I, I, False, False, "derivative does not exclude 0")
    quot = Interval.singleton(fm).div(denc.interval)
    if not quot.is_ok:
        return None
    N = Interval.singleton(m).sub(quot.interval)
    after = N.inter(I)
    if after.is_empty:
        # No root in I (under f'≠0 continuity hypotheses)
        return NewtonStep(I, after, True, False, "Newton intersection empty ⇒ no root")
    contracted = after.width() < I.width()
    unique = contracted and denc.interval.excludes_zero()
    return NewtonStep(I, after, contracted, unique, "interval Newton step")


def refine_root(e: Expr, var: str, I: Interval, *, max_steps: int = 20) -> RootCertificate:
    cur = I
    for _ in range(max_steps):
        step = interval_newton_step(e, var, cur)
        if step is None:
            break
        if step.after.is_empty:
            return RootCertificate(I, RootStatus.EXCLUDED, notes="Newton empty intersection")
        if step.unique and step.after.width() <= cur.width():
            cur = step.after
            # Sign change still needed for EXISTS; combine with classify
            base = classify_interval(e, var, cur)
            if base.status in (RootStatus.EXISTS, RootStatus.UNIQUE):
                return RootCertificate(
                    cur, RootStatus.UNIQUE, base.f_lo, base.f_hi, True, "Newton + monotone"
                )
            return RootCertificate(cur, RootStatus.POSSIBLE, notes="Newton contracted")
        if step.after == cur:
            break
        cur = step.after
    return classify_interval(e, var, cur)
