"""Finite-state Markov chains with exact rational probabilities."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import List, Sequence


Vector = List[Fraction]
Matrix = List[List[Fraction]]


def _q(x) -> Fraction:
    return x if isinstance(x, Fraction) else Fraction(x)


@dataclass
class ProbDist:
    probs: Vector

    def __post_init__(self) -> None:
        if any(p < 0 for p in self.probs):
            raise ValueError("negative probability")
        s = sum(self.probs)
        if s != 1:
            raise ValueError(f"probabilities must sum to 1, got {s}")

    def expect(self, values: Sequence[Fraction]) -> Fraction:
        return sum(p * _q(v) for p, v in zip(self.probs, values))

    def to_json(self) -> dict:
        return {"probs": [str(p) for p in self.probs]}


@dataclass
class StochasticMatrix:
    rows: Matrix

    def __post_init__(self) -> None:
        n = len(self.rows)
        for row in self.rows:
            if len(row) != n:
                raise ValueError("matrix must be square")
            if any(x < 0 for x in row):
                raise ValueError("negative transition probability")
            if sum(row) != 1:
                raise ValueError("rows must sum to 1")

    @property
    def n(self) -> int:
        return len(self.rows)

    def apply(self, dist: ProbDist) -> ProbDist:
        # row-stochastic: π' = π P
        n = self.n
        out = [Fraction(0)] * n
        for j in range(n):
            out[j] = sum(dist.probs[i] * self.rows[i][j] for i in range(n))
        return ProbDist(out)

    def power(self, k: int) -> "StochasticMatrix":
        if k < 0:
            raise ValueError("k >= 0")
        n = self.n
        # identity
        R = [[Fraction(1 if i == j else 0) for j in range(n)] for i in range(n)]
        base = [row[:] for row in self.rows]
        e = k
        while e > 0:
            if e & 1:
                R = _matmul(R, base)
            e >>= 1
            if e:
                base = _matmul(base, base)
        return StochasticMatrix(R)

    def to_json(self) -> dict:
        return {"rows": [[str(x) for x in row] for row in self.rows]}


def _matmul(A: Matrix, B: Matrix) -> Matrix:
    n = len(A)
    out = [[Fraction(0) for _ in range(n)] for _ in range(n)]
    for i in range(n):
        for k in range(n):
            for j in range(n):
                out[i][j] += A[i][k] * B[k][j]
    return out


def total_variation(p: ProbDist, q: ProbDist) -> Fraction:
    return sum(abs(a - b) for a, b in zip(p.probs, q.probs)) / 2


def reachability_prob(P: StochasticMatrix, start: ProbDist, targets: Sequence[int], steps: int) -> Fraction:
    """Probability of being in `targets` after exactly `steps` transitions."""
    dist = start
    for _ in range(steps):
        dist = P.apply(dist)
    return sum(dist.probs[i] for i in targets)
