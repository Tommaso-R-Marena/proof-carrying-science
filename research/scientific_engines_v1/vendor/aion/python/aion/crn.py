"""Exact mass-action reaction networks (mirrors `RequestProject/AION/MassAction.lean`).

All rate constants are `fractions.Fraction`.  States are tuples of naturals.
Propensity of reaction r at x:  k_r * prod_i (x_i)_(alpha_ri)  (falling factorials),
update: x - alpha_r + beta_r  (exact whenever the propensity is positive).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from typing import List, Sequence, Tuple


def desc_fact(x: int, k: int) -> int:
    """Falling factorial x (x-1) ... (x-k+1); equals 0 when x < k."""
    r = 1
    for j in range(k):
        r *= (x - j)
        if r == 0:
            return 0
    return r


def to_frac(v) -> Fraction:
    if isinstance(v, Fraction):
        return v
    if isinstance(v, str):
        return Fraction(v)
    if isinstance(v, int):
        return Fraction(v)
    raise TypeError(f"rates must be exact (int/str/Fraction), got {type(v)}: {v!r}")


@dataclass
class Reaction:
    inp: Tuple[int, ...]
    out: Tuple[int, ...]
    k: Fraction
    name: str = ""


@dataclass
class CRN:
    species: List[str]
    reactions: List[Reaction] = field(default_factory=list)

    @property
    def d(self) -> int:
        return len(self.species)

    def add(self, inp: Sequence[int], out: Sequence[int], k, name: str = "") -> "CRN":
        k = to_frac(k)
        assert len(inp) == self.d and len(out) == self.d
        self.reactions.append(Reaction(tuple(inp), tuple(out), k, name))
        return self

    def validate(self) -> List[str]:
        errs = []
        for i, r in enumerate(self.reactions):
            if not isinstance(r.k, Fraction):
                errs.append(f"reaction {i}: rate constant is not an exact rational")
            elif r.k < 0:
                errs.append(f"reaction {i}: negative rate constant {r.k}")
            if any((not isinstance(a, int)) or a < 0 for a in r.inp + r.out):
                errs.append(f"reaction {i}: stoichiometry must be natural numbers")
        return errs

    def prop(self, r: int, x: Sequence[int]) -> Fraction:
        R = self.reactions[r]
        p = 1
        for xi, a in zip(x, R.inp):
            p *= desc_fact(xi, a)
            if p == 0:
                return Fraction(0)
        return R.k * p

    def propf(self, r: int, x: Sequence[int]) -> float:
        R = self.reactions[r]
        p = float(R.k)
        for xi, a in zip(x, R.inp):
            p *= desc_fact(xi, a)
        return p

    def nxt(self, r: int, x: Sequence[int]) -> Tuple[int, ...]:
        R = self.reactions[r]
        return tuple(max(xi - a, 0) + b for xi, a, b in zip(x, R.inp, R.out))

    def to_json(self):
        return {
            "species": self.species,
            "reactions": [
                {"name": R.name, "inp": list(R.inp), "out": list(R.out), "k": str(R.k)}
                for R in self.reactions
            ],
        }

    @staticmethod
    def from_json(j) -> "CRN":
        c = CRN(list(j["species"]))
        for R in j["reactions"]:
            c.add(R["inp"], R["out"], Fraction(R["k"]), R.get("name", ""))
        return c
