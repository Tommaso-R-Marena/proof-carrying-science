"""Experimental causal calculus proposal fragments.

Each step records rule, premises, graph context, and resulting expression.
Derivation.check only inspects declared flags; it is not a receiving verifier.
Completeness and general implementation refinement are not claimed.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Sequence, Tuple

from pcs_causal.graphs.dag import CausalDAG
from pcs_causal.graphs.d_separation import d_separated


class DoRule(str, Enum):
    INSERT_OBS = "insert_observation"
    DELETE_OBS = "delete_observation"
    ACTION_EXCHANGE = "action_observation_exchange"
    ACTION_DELETE = "delete_action"
    BACKDOOR_EXPAND = "backdoor_expand"
    REWRITE = "algebraic_rewrite"


@dataclass(frozen=True, slots=True)
class Expr:
    """Lightweight interventional expression string form for v1."""

    text: str

    def __str__(self) -> str:
        return self.text


@dataclass(frozen=True, slots=True)
class DerivationStep:
    rule: DoRule
    original: Expr
    result: Expr
    graph_condition: str
    justified: bool
    detail: str

    def to_dict(self) -> dict:
        return {
            "rule": self.rule.value,
            "original": self.original.text,
            "result": self.result.text,
            "graph_condition": self.graph_condition,
            "justified": self.justified,
            "detail": self.detail,
        }


@dataclass
class Derivation:
    steps: List[DerivationStep]

    def check(self) -> Tuple[bool, Tuple[str, ...]]:
        bad = [s.detail for s in self.steps if not s.justified]
        return (len(bad) == 0, tuple(bad))


def try_delete_observation(
    graph: CausalDAG,
    y: str,
    x: str,
    z: Sequence[str],
) -> DerivationStep:
    """Rule 1 fragment: Y ⊥ X | Z in G ⇒ P(Y|X,Z)=P(Y|Z)."""
    sep = d_separated(graph, [y], [x], list(z))
    orig = Expr(f"P({y}|{x},{','.join(z)})" if z else f"P({y}|{x})")
    result = Expr(f"P({y}|{','.join(z)})" if z else f"P({y})")
    return DerivationStep(
        rule=DoRule.DELETE_OBS,
        original=orig,
        result=result,
        graph_condition=f"d_separated({y} ⊥ {x} | {list(z)}) in G",
        justified=sep,
        detail="ok" if sep else "graphical condition failed",
    )


def try_action_exchange(
    graph: CausalDAG,
    y: str,
    x: str,
    z: Sequence[str],
) -> DerivationStep:
    r"""Rule 2 fragment: Y ⊥ X | Z in G_{\underline{X}} ⇒ P(Y|do(X),Z)=P(Y|X,Z)."""
    # Rule 2 uses G_underlined_X (remove OUTGOING arrows from X).
    # Hard intervention mutilate() removes incoming arrows and is not this graph.
    gm = CausalDAG(nodes=graph.nodes,
                   edges=frozenset((u, v) for u, v in graph.edges if u != x))
    sep = d_separated(gm, [y], [x], list(z))
    orig = Expr(f"P({y}|do({x}),{','.join(z)})" if z else f"P({y}|do({x}))")
    result = Expr(f"P({y}|{x},{','.join(z)})" if z else f"P({y}|{x})")
    return DerivationStep(
        rule=DoRule.ACTION_EXCHANGE,
        original=orig,
        result=result,
        graph_condition=f"d_separated in G_remove_outgoing({x})",
        justified=sep,
        detail="ok" if sep else "exchange condition failed",
    )
