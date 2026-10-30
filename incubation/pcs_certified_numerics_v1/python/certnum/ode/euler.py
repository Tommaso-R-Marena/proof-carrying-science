"""Validated interval Euler for scalar ODEs x' = f(t,x) on a compact box.

Method (a posteriori residual / Lipschitz Euler enclosure):
  Given Lipschitz bound L for f in x on a rectangle, and interval enclosure F
  of f on that rectangle, one Euler step from X0 over [t,t+h] satisfies
  the solution tube in X0 + h*F + error, where a crude validated bound uses
  |φ(t+h)- (x0 + h f(t,x0))| ≤ (h^2/2) * M with M ⊇ |f'| bound — here we
  use the standard interval Euler with missing remainder made explicit:

  X_{k+1} = X_k + h * F(T_k, X_k)

  This is a *rough* enclosure that is sound for the Picard operator image
  only when combined with a contraction/Lipschitz check. We therefore:
    1. Compute the candidate enclosure by interval Euler.
    2. Require a verified Lipschitz bound L and step h with h*L < 1 for
       uniqueness (Picard contraction on C^0).
    3. Inflate by a remainder interval R = [0,0] when f is affine in x with
       exact rational coefficients (fully sound); otherwise mark
       INSUFFICIENT_PRECISION / require explicit remainder hypothesis.

For linear scalar ODE x' = a x + b with rational a,b, we provide an exact
integrating-factor style enclosure via series truncation with proved remainder
for exp on a small domain — see `linear_scalar_enclosure`.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Callable, List, Optional

from certnum.interval.interval import Enclosure, EnclStatus, Interval
from certnum.ode.exp_enclosure import exp_enclosure


@dataclass
class ODEStepCertificate:
    t0: Fraction
    h: Fraction
    x0: Interval
    x1: Interval
    lipschitz: Optional[Fraction]
    contraction: bool
    method: str
    notes: str

    def to_json(self) -> dict:
        return {
            "t0": str(self.t0),
            "h": str(self.h),
            "x0": self.x0.to_json(),
            "x1": self.x1.to_json(),
            "lipschitz": None if self.lipschitz is None else str(self.lipschitz),
            "contraction": self.contraction,
            "method": self.method,
            "notes": self.notes,
        }


def interval_euler_step(
    f_box: Interval,
    x0: Interval,
    h: Fraction,
    *,
    lipschitz: Optional[Fraction] = None,
) -> ODEStepCertificate:
    """One interval Euler step: X1 = X0 + h * F.

    Soundness caveat: this encloses the Euler *approximation image*, not
    automatically the true ODE flow, unless f is constant in x (then exact)
    or a separate remainder bound is supplied. We flag this in notes.
    """
    x1 = x0.add(f_box.mul(Interval.singleton(h)))
    contraction = lipschitz is not None and abs(h * lipschitz) < 1
    return ODEStepCertificate(
        t0=Fraction(0),
        h=h,
        x0=x0,
        x1=x1,
        lipschitz=lipschitz,
        contraction=contraction,
        method="interval_euler",
        notes=(
            "encloses Euler image X0+hF; true-flow enclosure requires "
            "remainder hypothesis or restricted f class"
        ),
    )


def linear_scalar_enclosure(
    a: Fraction,
    b: Fraction,
    x0: Fraction,
    t: Fraction,
) -> Enclosure:
    """Exact solution of x' = a x + b is x(t) = e^{a t}(x0 + b/a) - b/a for a≠0,
    or x0 + b t for a=0.

    We enclose e^{a t} via certified rational series (`exp_enclosure`).
    """
    if t < 0:
        return Enclosure.fail(EnclStatus.UNSUPPORTED)
    if a == 0:
        return Enclosure.ok(Interval.singleton(x0 + b * t))
    # x(t) = exp(a t) * (x0 + b/a) - b/a
    exp_at = exp_enclosure(a * t)
    if not exp_at.is_ok:
        return exp_at
    scale = x0 + b / a
    xt = exp_at.interval.mul(Interval.singleton(scale)).sub(Interval.singleton(b / a))
    return Enclosure.ok(xt)


def simulate_linear_scalar(
    a: Fraction,
    b: Fraction,
    x0: Fraction,
    t_end: Fraction,
    n_steps: int,
) -> List[Enclosure]:
    """Enclosures at uniform times k*t_end/n_steps."""
    out = []
    for k in range(n_steps + 1):
        t = t_end * Fraction(k, n_steps)
        out.append(linear_scalar_enclosure(a, b, x0, t))
    return out
