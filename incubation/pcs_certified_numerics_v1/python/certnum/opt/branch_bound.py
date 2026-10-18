"""Certified branch-and-bound global optimization over rational boxes."""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from typing import Dict, List, Optional, Sequence, Tuple

from certnum.expr.ast import Expr
from certnum.expr.eval import EvalError, eval_exact, eval_interval, mean_value_enclosure
from certnum.interval.interval import Interval
from certnum.opt.coverage import BisectProvenance, verify_coverage_with_provenance

Box = Dict[str, Interval]


@dataclass
class OptCertificate:
    variables: List[str]
    domain: Box
    lower_bound: Fraction
    upper_bound: Fraction
    incumbent: Optional[Dict[str, Fraction]]
    coverage: List[Box]
    provenance: List[BisectProvenance]
    subdivisions: int
    method: str
    notes: str = ""

    @property
    def gap(self) -> Fraction:
        return self.upper_bound - self.lower_bound

    def coverage_ok(self) -> bool:
        return verify_coverage_with_provenance(
            self.domain, self.coverage, self.variables, self.provenance
        )

    def to_json(self) -> dict:
        return {
            "variables": self.variables,
            "domain": {k: v.to_json() for k, v in self.domain.items()},
            "lower_bound": str(self.lower_bound),
            "upper_bound": str(self.upper_bound),
            "incumbent": None
            if self.incumbent is None
            else {k: str(v) for k, v in self.incumbent.items()},
            "coverage": [{k: v.to_json() for k, v in b.items()} for b in self.coverage],
            "provenance_count": len(self.provenance),
            "subdivisions": self.subdivisions,
            "method": self.method,
            "gap": str(self.gap),
            "coverage_ok": self.coverage_ok(),
            "notes": self.notes,
        }


def _box_width(box: Box) -> Fraction:
    return max((I.width() for I in box.values()), default=Fraction(0))


def _widest_var(box: Box, vars_: Sequence[str]) -> str:
    best, best_w = vars_[0], Fraction(-1)
    for v in vars_:
        w = box[v].width()
        if w > best_w:
            best, best_w = v, w
    return best


def _bisect_box(box: Box, var: str) -> Tuple[Box, Box]:
    left_I, right_I = box[var].bisect()  # type: ignore[misc]
    left = dict(box)
    right = dict(box)
    left[var] = left_I
    right[var] = right_I
    return left, right


def _midpoint_env(box: Box) -> Dict[str, Fraction]:
    env = {}
    for k, I in box.items():
        m = I.midpoint()
        if m is None:
            raise ValueError("empty box")
        env[k] = m
    return env


def _lower_enclosure(e: Expr, box: Box, method: str) -> Optional[Fraction]:
    if method == "mean_value":
        enc = mean_value_enclosure(e, box)
    else:
        enc = eval_interval(e, box)
    if not enc.is_ok or enc.interval.is_empty:
        return None
    return enc.interval.lo


def optimize(
    e: Expr,
    domain: Box,
    *,
    tol: Fraction = Fraction(1, 100),
    max_boxes: int = 5000,
    method: str = "natural",
) -> OptCertificate:
    vars_ = sorted(domain.keys())
    for v in e.vars():
        if v not in domain:
            raise ValueError(f"missing domain for {v}")

    try:
        mid = _midpoint_env(domain)
        ub = eval_exact(e, mid)
        incumbent = mid
    except EvalError:
        ub = None
        incumbent = None

    queue: List[Box] = [dict(domain)]
    leaves: List[Box] = []
    provenance: List[BisectProvenance] = []
    subdivisions = 0

    while queue and subdivisions < max_boxes:
        box = queue.pop()
        lo = _lower_enclosure(e, box, method)
        if lo is None:
            leaves.append(box)
            continue
        try:
            m = _midpoint_env(box)
            val = eval_exact(e, m)
            if ub is None or val < ub:
                ub = val
                incumbent = m
        except EvalError:
            pass

        if ub is not None and lo >= ub - tol and _box_width(box) <= tol:
            leaves.append(box)
            continue
        if ub is not None and lo > ub:
            leaves.append(box)
            continue
        if _box_width(box) <= tol:
            leaves.append(box)
            continue

        v = _widest_var(box, vars_)
        left, right = _bisect_box(box, v)
        provenance.append(BisectProvenance(dict(box), v, left, right))
        queue.extend([left, right])
        subdivisions += 1

    leaves.extend(queue)

    lbs = []
    for leaf in leaves:
        lo = _lower_enclosure(e, leaf, method)
        if lo is None:
            raise RuntimeError("incomplete enclosure on coverage leaf")
        lbs.append(lo)
    L = min(lbs) if lbs else Fraction(0)
    if ub is None:
        ups = []
        for leaf in leaves:
            enc = eval_interval(e, leaf)
            if enc.is_ok and not enc.interval.is_empty:
                ups.append(enc.interval.hi)
        ub = max(ups) if ups else L

    return OptCertificate(
        variables=vars_,
        domain=dict(domain),
        lower_bound=L,
        upper_bound=ub,
        incumbent=incumbent,
        coverage=leaves,
        provenance=provenance,
        subdivisions=subdivisions,
        method=method,
        notes="BnB with bisection provenance for multivariate coverage",
    )


# Back-compat for checker
def verify_coverage(domain: Box, leaves: Sequence[Box], vars_: Sequence[str]) -> bool:
    return verify_coverage_with_provenance(domain, leaves, vars_, provenance=None)
