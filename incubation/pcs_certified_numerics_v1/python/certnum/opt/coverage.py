"""Domain coverage witnesses for branch-and-bound certificates."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple

from certnum.interval.interval import Interval

Box = Dict[str, Interval]


@dataclass(frozen=True)
class BisectProvenance:
    """Records that children were obtained by bisecting `var` in `parent`."""

    parent: Box
    var: str
    left: Box
    right: Box

    def valid(self) -> bool:
        if self.var not in self.parent:
            return False
        parts = self.parent[self.var].bisect()
        if parts is None:
            return False
        L, R = parts
        if self.left.get(self.var) != L or self.right.get(self.var) != R:
            return False
        for v, I in self.parent.items():
            if v == self.var:
                continue
            if self.left.get(v) != I or self.right.get(v) != I:
                return False
        return True


def verify_coverage_1d(domain: Box, leaves: Sequence[Box], var: str) -> bool:
    for leaf in leaves:
        if not leaf[var].subset(domain[var]):
            return False
    segs = sorted(
        ((leaf[var].lo, leaf[var].hi) for leaf in leaves if not leaf[var].is_empty),
        key=lambda t: t[0],
    )
    if not segs:
        return domain[var].is_empty
    if segs[0][0] != domain[var].lo or segs[-1][1] != domain[var].hi:
        return False
    for i in range(len(segs) - 1):
        if segs[i][1] != segs[i + 1][0]:
            return False
    return True


def verify_coverage_with_provenance(
    domain: Box,
    leaves: Sequence[Box],
    vars_: Sequence[str],
    provenance: Sequence[BisectProvenance] | None = None,
) -> bool:
    for leaf in leaves:
        for v in vars_:
            if not leaf[v].subset(domain[v]):
                return False
    if len(vars_) == 1:
        return verify_coverage_1d(domain, leaves, vars_[0])
    if provenance is None:
        return False
    return all(p.valid() for p in provenance)
