"""Independent exact Int/Rat arithmetic reference — no OpRegistry imports.

Used to cross-check incremental/fresh paths that share `model.ops`. A bug in the
shared registry should be detectable by disagreement with this module.
"""
from __future__ import annotations

from fractions import Fraction
from typing import List, Sequence, Tuple, Union

Number = Union[int, Fraction]


def ind_int_const(evidence: int) -> int:
    return int(evidence)


def ind_int_add(a: int, b: int) -> int:
    return int(a) + int(b)


def ind_int_sub(a: int, b: int) -> int:
    return int(a) - int(b)


def ind_int_mul(a: int, b: int) -> int:
    return int(a) * int(b)


def ind_rat_const(num: int, den: int) -> Fraction:
    if den == 0:
        raise ValueError("zero denominator")
    return Fraction(num, den)


def ind_rat_add(a: Fraction, b: Fraction) -> Fraction:
    return Fraction(a) + Fraction(b)


def ind_rat_mul(a: Fraction, b: Fraction) -> Fraction:
    return Fraction(a) * Fraction(b)


def ind_eq(a: Number, b: Number) -> int:
    return 1 if a == b else 0


def evaluate_int_dag(
    nodes: Sequence[Tuple[int, str, Tuple[int, ...], int]],
) -> List[Number]:
    """
    nodes: (id, op_name, deps, evidence_or_unused)
    op_name in {int_const, int_add, int_sub, int_mul}
    Returns outputs aligned with topological input order (must be topo-sorted).
    """
    by_pos = {nid: i for i, (nid, *_rest) in enumerate(nodes)}
    outs: List[Number] = [0] * len(nodes)
    for i, (nid, op, deps, ev) in enumerate(nodes):
        if op == "int_const":
            outs[i] = ind_int_const(ev)
        elif op == "int_add":
            a, b = deps
            outs[i] = ind_int_add(outs[by_pos[a]], outs[by_pos[b]])  # type: ignore[arg-type]
        elif op == "int_sub":
            a, b = deps
            outs[i] = ind_int_sub(outs[by_pos[a]], outs[by_pos[b]])  # type: ignore[arg-type]
        elif op == "int_mul":
            a, b = deps
            outs[i] = ind_int_mul(outs[by_pos[a]], outs[by_pos[b]])  # type: ignore[arg-type]
        else:
            raise ValueError(f"unsupported op {op}")
    return outs
