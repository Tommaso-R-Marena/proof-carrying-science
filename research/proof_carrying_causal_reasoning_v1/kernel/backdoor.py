"""Pearl backdoor criterion for finite DAGs (exact graphical check)."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import FrozenSet, Iterable, List, Optional, Tuple

from .dag import CausalDAG, GraphError
from .d_separation import find_backdoor_paths, path_blocked


ASSUMPTIONS = (
    "dag_is_correct_causal_graph",
    "causal_sufficiency_no_latent_confounders_among_modeled_vars",
    "acyclicity",
    "consistency_Yx_equals_Y_when_X_x",
    "graphical_markov_condition",
    "positivity_P(X=x|Z=z)>0_for_all_z_with_P(Z=z)>0",
)


@dataclass(frozen=True, slots=True)
class BackdoorResult:
    treatment: str
    outcome: str
    adjustment_set: FrozenSet[str]
    valid: bool
    reasons: Tuple[str, ...]
    formula: Optional[str]
    assumptions: Tuple[str, ...]

    def to_dict(self) -> dict:
        return {
            "treatment": self.treatment,
            "outcome": self.outcome,
            "adjustment_set": sorted(self.adjustment_set),
            "valid": self.valid,
            "reasons": list(self.reasons),
            "formula": self.formula,
            "assumptions": list(self.assumptions),
        }


def verify_backdoor_set(
    graph: CausalDAG,
    treatment: str,
    outcome: str,
    z: Iterable[str],
) -> BackdoorResult:
    if treatment not in graph.nodes or outcome not in graph.nodes:
        raise GraphError("unknown treatment or outcome")
    Z = frozenset(z)
    unknown = Z - graph.nodes
    if unknown:
        return BackdoorResult(
            treatment=treatment,
            outcome=outcome,
            adjustment_set=Z,
            valid=False,
            reasons=(f"adjustment set contains unknown variables: {sorted(unknown)}",),
            formula=None,
            assumptions=ASSUMPTIONS,
        )
    if treatment in Z or outcome in Z:
        return BackdoorResult(
            treatment=treatment,
            outcome=outcome,
            adjustment_set=Z,
            valid=False,
            reasons=("adjustment set must not contain treatment or outcome",),
            formula=None,
            assumptions=ASSUMPTIONS,
        )

    reasons: List[str] = []
    desc = graph.descendants(treatment)
    bad = Z & desc
    if bad:
        reasons.append(f"adjustment set contains descendants of treatment: {sorted(bad)}")

    backdoors = find_backdoor_paths(graph, treatment, outcome)
    open_paths = [p for p in backdoors if not path_blocked(graph, p, Z)]
    if open_paths:
        reasons.append(
            "unblocked backdoor paths remain: "
            + "; ".join("-".join(p) for p in open_paths[:5])
        )

    valid = (not bad) and (not open_paths)
    if valid:
        if Z:
            znames = ",".join(sorted(Z))
            formula = (
                f"P({outcome}|do({treatment}=x)) = "
                f"Σ_{{{znames}}} P({outcome}|{treatment}=x,{znames}) P({znames})"
            )
        else:
            formula = f"P({outcome}|do({treatment}=x)) = P({outcome}|{treatment}=x)"
        reasons = ("backdoor criterion satisfied under declared assumptions",)
    else:
        formula = None
        if not reasons:
            reasons = ("backdoor criterion not satisfied",)

    return BackdoorResult(
        treatment=treatment,
        outcome=outcome,
        adjustment_set=Z,
        valid=valid,
        reasons=tuple(reasons),
        formula=formula,
        assumptions=ASSUMPTIONS,
    )


def find_minimal_backdoor_sets(
    graph: CausalDAG,
    treatment: str,
    outcome: str,
    max_size: Optional[int] = None,
) -> List[BackdoorResult]:
    pool = sorted(
        n
        for n in graph.nodes
        if n not in {treatment, outcome} and n not in graph.descendants(treatment)
    )
    if max_size is None:
        max_size = len(pool)
    results: List[BackdoorResult] = []
    for r in range(0, max_size + 1):
        for subset in combinations(pool, r):
            res = verify_backdoor_set(graph, treatment, outcome, subset)
            if res.valid:
                results.append(res)
    results.sort(key=lambda x: (len(x.adjustment_set), sorted(x.adjustment_set)))
    return results
