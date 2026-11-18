from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence, Tuple

from .authority import meet
from .syntax import Authority, Context, Formula, Premise


@dataclass(frozen=True)
class Judgment:
    support: Tuple[int, ...]
    authority: Authority
    formula: Formula
    rule: str


class EvalError(ValueError):
    pass


def derive_hyp(Γ: Context, premise_id: int) -> Judgment:
    if not Γ.unique_ids():
        raise EvalError("duplicate premise ids")
    p = Γ.find(premise_id)
    if p is None:
        raise EvalError(f"unknown premise {premise_id}")
    return Judgment(support=(p.id,), authority=p.authority, formula=p.formula, rule="hyp")


def derive_and_i(j1: Judgment, j2: Judgment) -> Judgment:
    return Judgment(
        support=tuple(j1.support) + tuple(j2.support),
        authority=meet(j1.authority, j2.authority),
        formula=("and", j1.formula, j2.formula),
        rule="andI",
    )


def derive_and_e1(j: Judgment) -> Judgment:
    if not (isinstance(j.formula, tuple) and j.formula[0] == "and"):
        raise EvalError("andE1 requires conjunction")
    return Judgment(support=j.support, authority=j.authority, formula=j.formula[1], rule="andE1")


def derive_and_e2(j: Judgment) -> Judgment:
    if not (isinstance(j.formula, tuple) and j.formula[0] == "and"):
        raise EvalError("andE2 requires conjunction")
    return Judgment(support=j.support, authority=j.authority, formula=j.formula[2], rule="andE2")


def formula_atoms(φ: Formula) -> List[int]:
    if φ[0] == "atom":
        return [φ[1]]  # type: ignore[index]
    if φ[0] == "not":
        return formula_atoms(φ[1])  # type: ignore[index]
    if φ[0] == "and":
        return formula_atoms(φ[1]) + formula_atoms(φ[2])  # type: ignore[index]
    raise EvalError(f"bad formula {φ}")


def can_derive_unrelated(Γ: Context, target_atom: int) -> bool:
    """True only if some premise formula mentions target_atom (Hyp/And fragment)."""
    for p in Γ.premises:
        if target_atom in formula_atoms(p.formula):
            return True
    return False
