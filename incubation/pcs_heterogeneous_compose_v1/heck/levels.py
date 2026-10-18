"""Assurance levels for heterogeneous evidence composition."""

from __future__ import annotations

from enum import Enum
from typing import Iterable


class Level(str, Enum):
    FORMAL = "formal"
    COMPUTATIONAL = "computational"
    EMPIRICAL = "empirical"
    PROVENANCE = "provenance"
    OPEN = "open"

    @property
    def rank(self) -> int:
        return {
            Level.FORMAL: 4,
            Level.COMPUTATIONAL: 3,
            Level.EMPIRICAL: 2,
            Level.PROVENANCE: 1,
            Level.OPEN: 0,
        }[self]

    def le(self, other: "Level") -> bool:
        return self.rank <= other.rank

    def at_most_empirical(self) -> bool:
        return self in {Level.EMPIRICAL, Level.PROVENANCE, Level.OPEN}


def meet(a: Level, b: Level) -> Level:
    """Weakest-link meet."""
    return a if a.rank <= b.rank else b


def meet_list(levels: Iterable[Level]) -> Level:
    """Folded meet; empty fold is Formal (vacuous strongest identity)."""
    acc = Level.FORMAL
    seen = False
    for level in levels:
        acc = meet(acc, level) if seen else level
        seen = True
    return acc if seen else Level.FORMAL


def parse_level(value: str) -> Level:
    try:
        return Level(value)
    except ValueError as exc:
        raise ValueError(f"unsupported assurance level: {value!r}") from exc
