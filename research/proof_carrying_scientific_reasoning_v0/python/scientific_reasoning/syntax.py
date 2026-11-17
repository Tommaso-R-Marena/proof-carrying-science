from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple, Union


class Authority(str, Enum):
    disputed = "disputed"
    hypothesis = "hypothesis"
    empiricalAsserted = "empiricalAsserted"
    assumption = "assumption"
    derived = "derived"
    mathVerified = "mathVerified"


Formula = Union[Tuple[str, int], Tuple[str, "Formula"], Tuple[str, "Formula", "Formula"]]


def atom(i: int) -> Formula:
    return ("atom", i)


def lnot(φ: Formula) -> Formula:
    return ("not", φ)


def land(φ: Formula, ψ: Formula) -> Formula:
    return ("and", φ, ψ)


@dataclass(frozen=True)
class Premise:
    id: int
    formula: Formula
    authority: Authority


@dataclass(frozen=True)
class Context:
    premises: Tuple[Premise, ...]

    def ids(self) -> List[int]:
        return [p.id for p in self.premises]

    def find(self, i: int) -> Premise | None:
        for p in self.premises:
            if p.id == i:
                return p
        return None

    def unique_ids(self) -> bool:
        ids = self.ids()
        return len(ids) == len(set(ids))
