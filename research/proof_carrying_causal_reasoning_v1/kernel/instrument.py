"""Instrumental-variable graphical checks and exact Balke–Pearl-style bounds.

Bounds are computed by optimizing P(Y(1)=1) / P(Y(0)=1) over the finite
binary IV response-type polytope consistent with the observational law
(Balke & Pearl 1997), using exact rational linear programming.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from itertools import product
from typing import Dict, List, Optional, Sequence, Tuple

from .dag import CausalDAG, GraphError
from .d_separation import d_separated
from .scm import BinarySCM


ASSUMPTIONS = (
    "dag_is_correct_causal_graph",
    "instrument_exogeneity_Z_dsep_Y_in_G_underline_X",
    "instrument_relevance_Z_affects_X",
    "exclusion_no_direct_Z_to_Y",
    "consistency",
)


@dataclass(frozen=True, slots=True)
class InstrumentResult:
    treatment: str
    outcome: str
    instrument: str
    valid: bool
    reasons: Tuple[str, ...]
    assumptions: Tuple[str, ...]

    def to_dict(self) -> dict:
        return {
            "treatment": self.treatment,
            "outcome": self.outcome,
            "instrument": self.instrument,
            "valid": self.valid,
            "reasons": list(self.reasons),
            "assumptions": list(self.assumptions),
            "criterion": "instrument",
        }


@dataclass(frozen=True, slots=True)
class BalkePearlBounds:
    treatment: str
    outcome: str
    instrument: str
    p_do_lower: Fraction
    p_do_upper: Fraction
    p_do0_lower: Fraction
    p_do0_upper: Fraction
    ate_lower: Fraction
    ate_upper: Fraction
    point_identified: bool
    notes: Tuple[str, ...]

    def to_dict(self) -> dict:
        return {
            "treatment": self.treatment,
            "outcome": self.outcome,
            "instrument": self.instrument,
            "p_do_1_lower": _f(self.p_do_lower),
            "p_do_1_upper": _f(self.p_do_upper),
            "p_do_0_lower": _f(self.p_do0_lower),
            "p_do_0_upper": _f(self.p_do0_upper),
            "ate_lower": _f(self.ate_lower),
            "ate_upper": _f(self.ate_upper),
            "point_identified": self.point_identified,
            "notes": list(self.notes),
        }


def verify_instrument(
    graph: CausalDAG,
    treatment: str,
    outcome: str,
    instrument: str,
) -> InstrumentResult:
    for n in (treatment, outcome, instrument):
        if n not in graph.nodes:
            raise GraphError(f"unknown node {n!r}")
    reasons: list[str] = []
    if (instrument, outcome) in graph.edges:
        reasons.append("exclusion violated: direct edge instrument→outcome")
    if not _reaches(graph, instrument, treatment):
        reasons.append("relevance failed: no directed path from instrument to treatment")
    g_under = graph.mutilate([treatment])
    try:
        if not d_separated(g_under, [instrument], [outcome], []):
            reasons.append(
                "exogeneity failed: instrument not d-separated from outcome in G_underline{X}"
            )
    except GraphError as exc:
        reasons.append(f"exogeneity check error: {exc}")
    valid = not reasons
    if valid:
        reasons = ("instrumental-variable graphical conditions satisfied",)
    return InstrumentResult(
        treatment=treatment,
        outcome=outcome,
        instrument=instrument,
        valid=valid,
        reasons=tuple(reasons),
        assumptions=ASSUMPTIONS,
    )


def balke_pearl_bounds(
    scm: BinarySCM,
    treatment: str,
    outcome: str,
    instrument: str,
) -> BalkePearlBounds:
    """Sharp bounds on P(Y=1|do(X=x)) via response-type linear programs."""
    check = verify_instrument(scm.graph, treatment, outcome, instrument)
    if not check.valid:
        raise GraphError("instrument invalid; refuse bounds")

    # Observational cells p(x,y|z)
    obs: Dict[Tuple[int, int, int], Fraction] = {}
    for z, x, y in product([0, 1], repeat=3):
        pz = scm.p_obs({instrument: z})
        if pz == 0:
            raise GraphError("instrument positivity failure")
        obs[(z, x, y)] = scm.p_obs({instrument: z, treatment: x, outcome: y}) / pz

    # 16 response types: (x0, x1, y0, y1)
    types = list(product([0, 1], repeat=4))
    # Build equality constraints A q = b for the 8 cells (then drop 2 redundant sum-to-1).
    # For each (z,x,y): sum_{types compatible} q_t = obs[z,x,y]
    rows: List[List[Fraction]] = []
    rhs: List[Fraction] = []
    for z, x, y in product([0, 1], repeat=3):
        row = []
        for x0, x1, y0, y1 in types:
            xz = x0 if z == 0 else x1
            y_of_x = y0 if x == 0 else y1
            # Observed (X=x,Y=y|Z=z) requires X(z)=x and Y(x)=y
            row.append(Fraction(1) if (xz == x and y_of_x == y) else Fraction(0))
        rows.append(row)
        rhs.append(obs[(z, x, y)])

    # Also sum q = 1 (implied by summing either Z slice, but keep for conditioning)
    rows.append([Fraction(1)] * 16)
    rhs.append(Fraction(1))

    # Objectives
    c_y1 = [Fraction(1) if y1 == 1 else Fraction(0) for (_x0, _x1, _y0, y1) in types]
    c_y0 = [Fraction(1) if y0 == 1 else Fraction(0) for (_x0, _x1, y0, _y1) in types]

    lo1, hi1 = _exact_lp_bounds(rows, rhs, c_y1)
    lo0, hi0 = _exact_lp_bounds(rows, rhs, c_y0)

    # Sharp ATE bounds require joint optimization; compute via objective y1 - y0.
    c_ate = [c_y1[i] - c_y0[i] for i in range(16)]
    ate_lo, ate_hi = _exact_lp_bounds(rows, rhs, c_ate)

    point = lo1 == hi1 and lo0 == hi0
    notes = [
        "bounds from exact rational LP over binary IV response types (Balke–Pearl polytope)",
        "ATE bounds are sharp (optimized directly), not Frechet envelopes",
    ]
    if point:
        notes.append("point-identified under this observational law")

    return BalkePearlBounds(
        treatment=treatment,
        outcome=outcome,
        instrument=instrument,
        p_do_lower=lo1,
        p_do_upper=hi1,
        p_do0_lower=lo0,
        p_do0_upper=hi0,
        ate_lower=ate_lo,
        ate_upper=ate_hi,
        point_identified=point,
        notes=tuple(notes),
    )


def _exact_lp_bounds(
    A: Sequence[Sequence[Fraction]],
    b: Sequence[Fraction],
    c: Sequence[Fraction],
) -> Tuple[Fraction, Fraction]:
    """Min/max c·q s.t. A q = b, q ≥ 0 (exact rational revised simplex)."""
    A2, b2 = _row_reduce(A, b)
    m2 = len(A2)
    n = len(c)
    if m2 > n:
        raise GraphError("overconstrained IV observational system")
    # Find one feasible basis, then pivot to opt for max and min.
    basis = _find_feasible_basis(A2, b2)
    if basis is None:
        raise GraphError("empty IV response-type polytope (infeasible observations)")
    hi = _simplex_optimize(A2, b2, c, list(basis), maximize=True)
    lo = _simplex_optimize(A2, b2, c, list(basis), maximize=False)
    return lo, hi


def _find_feasible_basis(
    A: List[List[Fraction]], b: List[Fraction]
) -> Optional[List[int]]:
    from itertools import combinations

    m2 = len(A)
    n = len(A[0])
    # Prefer sparse search: try combinations but stop at first feasible.
    for cols in combinations(range(n), m2):
        B = [[A[i][j] for j in cols] for i in range(m2)]
        inv = _invert(B)
        if inv is None:
            continue
        qB = [_dot(inv[i], b) for i in range(m2)]
        if any(v < 0 for v in qB):
            continue
        return list(cols)
    return None


def _simplex_optimize(
    A: List[List[Fraction]],
    b: List[Fraction],
    c: Sequence[Fraction],
    basis: List[int],
    *,
    maximize: bool,
) -> Fraction:
    """Exact Bland simplex on equality form; `basis` is a feasible column set."""
    m = len(A)
    n = len(c)
    basis = list(basis)
    sign = Fraction(1) if maximize else Fraction(-1)
    for _ in range(10000):
        B = [[A[i][j] for j in basis] for i in range(m)]
        inv = _invert(B)
        if inv is None:
            raise GraphError("singular basis in IV simplex")
        xB = [_dot(inv[i], b) for i in range(m)]
        # Reduced costs for nonbasic vars
        cB = [c[j] for j in basis]
        # π = cB * B^{-1}
        pi = [_dot(cB, [inv[i][k] for i in range(m)]) for k in range(m)]
        # Choose entering variable (Bland: lowest index with favorable reduced cost)
        enter = None
        for j in range(n):
            if j in basis:
                continue
            a_j = [A[i][j] for i in range(m)]
            rc = c[j] - _dot(pi, a_j)
            rc_s = sign * rc
            if rc_s > 0:
                enter = j
                break
        if enter is None:
            return _dot(cB, xB)
        # Direction d = B^{-1} A_enter
        a_e = [A[i][enter] for i in range(m)]
        d = [_dot(inv[i], a_e) for i in range(m)]
        # Ratio test (Bland)
        leave_pos = None
        best_ratio = None
        for i in range(m):
            if d[i] > 0:
                ratio = xB[i] / d[i]
                if best_ratio is None or ratio < best_ratio or (
                    ratio == best_ratio and basis[i] < basis[leave_pos]
                ):
                    best_ratio = ratio
                    leave_pos = i
        if leave_pos is None:
            raise GraphError("unbounded IV response-type polytope")
        basis[leave_pos] = enter
    raise GraphError("IV simplex iteration limit")


def _row_reduce(
    A: Sequence[Sequence[Fraction]], b: Sequence[Fraction]
) -> Tuple[List[List[Fraction]], List[Fraction]]:
    """Remove redundant equality rows via exact Gaussian rank reveal."""
    mat = [list(row) + [bi] for row, bi in zip(A, b)]
    rows = len(mat)
    cols = len(A[0])
    r = 0
    pivots = []
    for c in range(cols):
        pivot = None
        for i in range(r, rows):
            if mat[i][c] != 0:
                pivot = i
                break
        if pivot is None:
            continue
        mat[r], mat[pivot] = mat[pivot], mat[r]
        piv = mat[r][c]
        mat[r] = [v / piv for v in mat[r]]
        for i in range(rows):
            if i == r:
                continue
            factor = mat[i][c]
            if factor == 0:
                continue
            mat[i] = [mat[i][j] - factor * mat[r][j] for j in range(cols + 1)]
        pivots.append(c)
        r += 1
        if r == rows:
            break
    # Check inconsistent 0 = nonzero
    for i in range(r, rows):
        if all(mat[i][j] == 0 for j in range(cols)) and mat[i][cols] != 0:
            raise GraphError("inconsistent observational constraints for IV")
    A_out = [row[:cols] for row in mat[:r]]
    b_out = [row[cols] for row in mat[:r]]
    return A_out, b_out


def _invert(M: List[List[Fraction]]) -> Optional[List[List[Fraction]]]:
    n = len(M)
    aug = [list(M[i]) + [Fraction(1) if i == j else Fraction(0) for j in range(n)] for i in range(n)]
    for col in range(n):
        pivot = None
        for i in range(col, n):
            if aug[i][col] != 0:
                pivot = i
                break
        if pivot is None:
            return None
        aug[col], aug[pivot] = aug[pivot], aug[col]
        piv = aug[col][col]
        aug[col] = [v / piv for v in aug[col]]
        for i in range(n):
            if i == col:
                continue
            factor = aug[i][col]
            aug[i] = [aug[i][j] - factor * aug[col][j] for j in range(2 * n)]
    return [row[n:] for row in aug]


def _dot(a: Sequence[Fraction], b: Sequence[Fraction]) -> Fraction:
    return sum((x * y for x, y in zip(a, b)), Fraction(0))


def _reaches(graph: CausalDAG, src: str, dst: str) -> bool:
    seen = set()
    stack = list(graph.children(src))
    while stack:
        n = stack.pop()
        if n == dst:
            return True
        if n in seen:
            continue
        seen.add(n)
        stack.extend(graph.children(n))
    return False


def _f(x: Fraction) -> str:
    return f"{x.numerator}/{x.denominator}"
