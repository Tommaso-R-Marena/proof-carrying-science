"""Adversarial benchmarks where naive causal reasoning fails."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List

from pcs_causal.graphs.dag import CausalDAG
from pcs_causal.identification.backdoor import verify_backdoor_set


@dataclass(frozen=True)
class AdversarialCase:
    name: str
    description: str
    expected: str
    check: Callable[[], bool]


def _confounding_empty_invalid() -> bool:
    g = CausalDAG.from_edges(["Z", "X", "Y"], [("Z", "X"), ("Z", "Y"), ("X", "Y")])
    return not verify_backdoor_set(g, "X", "Y", []).valid


def _confounding_z_valid() -> bool:
    g = CausalDAG.from_edges(["Z", "X", "Y"], [("Z", "X"), ("Z", "Y"), ("X", "Y")])
    return verify_backdoor_set(g, "X", "Y", ["Z"]).valid


def _mediator_invalid() -> bool:
    # X → M → Y; adjusting for M blocks the only directed path — not backdoor
    g = CausalDAG.from_edges(["X", "M", "Y"], [("X", "M"), ("M", "Y")])
    # empty set is valid backdoor (no backdoor paths)
    empty_ok = verify_backdoor_set(g, "X", "Y", []).valid
    med_bad = not verify_backdoor_set(g, "X", "Y", ["M"]).valid
    return empty_ok and med_bad


def _collider_bias() -> bool:
    # X → C ← Y; conditioning on collider creates association — empty is valid for ATE of X on Y? 
    # No causal path X to Y; ATE is 0; empty backdoor OK
    g = CausalDAG.from_edges(["X", "C", "Y"], [("X", "C"), ("Y", "C")])
    return verify_backdoor_set(g, "X", "Y", []).valid and not verify_backdoor_set(
        g, "X", "Y", ["C"]
    ).valid


def _m_bias() -> bool:
    # M-bias: U1 → X, U1 → C, U2 → Y, U2 → C; adjusting C opens bias
    g = CausalDAG.from_edges(
        ["U1", "U2", "X", "Y", "C"],
        [("U1", "X"), ("U1", "C"), ("U2", "Y"), ("U2", "C")],
    )
    empty = verify_backdoor_set(g, "X", "Y", [])
    with_c = verify_backdoor_set(g, "X", "Y", ["C"])
    return empty.valid and not with_c.valid


ADVERSARIAL_SUITE: List[AdversarialCase] = [
    AdversarialCase(
        "confounding_empty_invalid",
        "Empty adjustment fails under classic confounding",
        "invalid",
        _confounding_empty_invalid,
    ),
    AdversarialCase(
        "confounding_z_valid",
        "Adjusting for confounder Z is valid",
        "valid",
        _confounding_z_valid,
    ),
    AdversarialCase(
        "mediator_adjustment_invalid",
        "Adjusting for mediator is not a valid backdoor set",
        "invalid_mediator",
        _mediator_invalid,
    ),
    AdversarialCase(
        "collider_conditioning_invalid",
        "Conditioning on collider is invalid adjustment",
        "invalid_collider",
        _collider_bias,
    ),
    AdversarialCase(
        "m_bias",
        "M-bias: adjusting for C opens noncausal path",
        "empty_ok_C_bad",
        _m_bias,
    ),
]


def run_adversarial_suite() -> Dict[str, bool]:
    return {c.name: c.check() for c in ADVERSARIAL_SUITE}
