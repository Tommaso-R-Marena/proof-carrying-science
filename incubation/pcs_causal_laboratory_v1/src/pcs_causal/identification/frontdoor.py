"""Frontdoor identification criterion (Pearl) — restricted, assumption-explicit.

Frontdoor conditions for mediator set M relative to (X, Y):
1. M intercepts all directed paths from X to Y.
2. No unblocked backdoor path from X to M.
3. All backdoor paths from M to Y are blocked by X.

When these hold (and positivity), the frontdoor formula identifies P(Y|do(X)).
Pattern-matching alone is not a proof; we check each graphical condition and
emit obligations. Soundness for general SCMs is established separately (Lean /
exact finite checks).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import FrozenSet, Iterable, List, Tuple

from pcs_causal.graphs.dag import CausalDAG, GraphError
from pcs_causal.graphs.d_separation import d_separated, find_backdoor_paths, path_blocked
from pcs_causal.hypothesis.states import ScientificStatus
from pcs_causal.identification.backdoor import verify_backdoor_set


@dataclass(frozen=True, slots=True)
class FrontdoorResult:
    treatment: str
    outcome: str
    mediators: FrozenSet[str]
    valid: bool
    reasons: Tuple[str, ...]
    formula: str | None
    assumptions: Tuple[str, ...]
    status: ScientificStatus

    def to_dict(self) -> dict:
        return {
            "treatment": self.treatment,
            "outcome": self.outcome,
            "mediators": sorted(self.mediators),
            "valid": self.valid,
            "reasons": list(self.reasons),
            "formula": self.formula,
            "assumptions": list(self.assumptions),
            "status": self.status.value,
        }


_ASSUMPTIONS = (
    "dag_is_correct_causal_graph",
    "causal_sufficiency_among_modeled_vars",
    "acyclicity",
    "consistency",
    "graphical_markov_condition",
    "positivity_for_frontdoor_formula",
)


def check_frontdoor(
    graph: CausalDAG,
    treatment: str,
    outcome: str,
    mediators: Iterable[str],
) -> FrontdoorResult:
    if treatment not in graph.nodes or outcome not in graph.nodes:
        raise GraphError("unknown treatment or outcome")
    M = frozenset(mediators)
    reasons: List[str] = []
    if not M:
        reasons.append("mediator set empty")
    if treatment in M or outcome in M:
        reasons.append("mediators must not include treatment or outcome")
    if not M <= graph.nodes:
        raise GraphError("unknown mediator")

    # (1) M intercepts all directed paths X → ... → Y
    directed = graph.directed_paths(treatment, outcome)
    for p in directed:
        # path nodes excluding endpoints must hit M
        interior = set(p[1:-1])
        if not (interior & M):
            reasons.append(
                f"directed path not intercepted by M: {'→'.join(p)}"
            )

    # (2) no unblocked backdoor from X to M (empty adjustment)
    for m in sorted(M):
        bd = verify_backdoor_set(graph, treatment, m, set())
        # Actually need: no backdoor paths from X to M at all (unblocked by empty set)
        paths = find_backdoor_paths(graph, treatment, m)
        open_p = [p for p in paths if not path_blocked(graph, p, set())]
        if open_p:
            reasons.append(
                f"backdoor path from treatment to mediator {m}: "
                + "; ".join("–".join(p) for p in open_p[:3])
            )

    # (3) all backdoor paths from M to Y blocked by X
    for m in sorted(M):
        paths = find_backdoor_paths(graph, m, outcome)
        open_p = [p for p in paths if not path_blocked(graph, p, {treatment})]
        if open_p:
            reasons.append(
                f"backdoor from mediator {m} to outcome not blocked by treatment: "
                + "; ".join("–".join(p) for p in open_p[:3])
            )

    valid = not reasons
    if valid:
        formula = (
            f"P({outcome}|do({treatment}=x)) = "
            f"Σ_m P(m|{treatment}=x) Σ_{{x'}} P({outcome}|{treatment}=x', m) P({treatment}=x')"
        )
        status = ScientificStatus.IDENTIFIED_UNDER_ASSUMPTIONS
        reasons = ("frontdoor graphical conditions satisfied under declared assumptions",)
    else:
        formula = None
        status = ScientificStatus.NOT_IDENTIFIABLE

    return FrontdoorResult(
        treatment=treatment,
        outcome=outcome,
        mediators=M,
        valid=valid,
        reasons=tuple(reasons),
        formula=formula,
        assumptions=_ASSUMPTIONS,
        status=status,
    )
