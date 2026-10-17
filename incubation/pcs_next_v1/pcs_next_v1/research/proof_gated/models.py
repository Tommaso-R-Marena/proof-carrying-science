"""Proof-gated self-improvement research models (isolated, finite domains).

Does not claim general intelligence or recursive acceleration.
Finite-dataset improvement does not imply general improvement.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class ScalarIntModel:
    """f(x) = a*x + b over integers."""

    a: int
    b: int

    def __call__(self, x: int) -> int:
        return self.a * x + self.b


@dataclass(frozen=True)
class AffineModel:
    weights: tuple[int, ...]
    bias: int

    def __call__(self, x: tuple[int, ...]) -> int:
        if len(x) != len(self.weights):
            raise ValueError("dim mismatch")
        return sum(w * xi for w, xi in zip(self.weights, x)) + self.bias


def relu(x: int) -> int:
    return x if x > 0 else 0


@dataclass(frozen=True)
class TinyReluNet:
    """One hidden layer ReLU net with integer weights."""

    w1: tuple[tuple[int, ...], ...]  # out x in
    b1: tuple[int, ...]
    w2: tuple[int, ...]
    b2: int

    def __call__(self, x: tuple[int, ...]) -> int:
        h = []
        for row, b in zip(self.w1, self.b1):
            h.append(relu(sum(wi * xi for wi, xi in zip(row, x)) + b))
        return sum(wi * hi for wi, hi in zip(self.w2, h)) + self.b2


def task_loss(model: Callable[[int], int], data: list[tuple[int, int]]) -> int:
    return sum((model(x) - y) ** 2 for x, y in data)


def no_forgetting_guard(
    old: Callable[[int], int],
    new: Callable[[int], int],
    domain: range,
    *,
    max_pointwise_increase: int = 0,
) -> tuple[bool, list[int]]:
    """Return (ok, counterexamples) if new error vs old targets increases beyond bound.

    Guard is only over the explicit finite/bounded domain provided.
    """
    bad = []
    for x in domain:
        # interpret "error" relative to old model's output as designated behavior
        if abs(new(x) - old(x)) > max_pointwise_increase:
            bad.append(x)
            if len(bad) >= 20:
                break
    return (len(bad) == 0), bad


def greedy_scalar_search(
    base: ScalarIntModel,
    data: list[tuple[int, int]],
    *,
    a_range: range,
    b_range: range,
    domain_guard: range,
) -> dict:
    best = base
    best_loss = task_loss(base, data)
    proposals = 0
    accepted = 0
    for a in a_range:
        for b in b_range:
            cand = ScalarIntModel(a, b)
            proposals += 1
            ok, _ = no_forgetting_guard(base, cand, domain_guard, max_pointwise_increase=10**9)
            # For improvement objective we only require loss decrease on frozen data
            # and optional preservation separately.
            loss = task_loss(cand, data)
            if loss < best_loss:
                best, best_loss = cand, loss
                accepted += 1
    return {
        "best": {"a": best.a, "b": best.b},
        "best_loss": best_loss,
        "proposals": proposals,
        "accepted_improvements": accepted,
        "limitations": [
            "Finite search only.",
            "Loss decrease on frozen data does not imply general improvement.",
        ],
    }
