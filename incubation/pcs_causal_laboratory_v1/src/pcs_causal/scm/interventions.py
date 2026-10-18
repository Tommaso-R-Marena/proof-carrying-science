"""Hard intervention semantics (do-operator).

An intervention replaces structural mechanisms; it is not conditioning.
Soft interventions and stochastic policies are out of scope for v1.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from pcs_causal.graphs.dag import CausalDAG
from pcs_causal.probability.rational_pmf import FiniteDistribution
from pcs_causal.scm.finite_scm import FiniteSCM, SCMError


@dataclass(frozen=True, slots=True)
class Intervention:
    """Hard intervention do(X_i = x_i for i in I)."""

    assignment: Mapping[str, object]

    def __post_init__(self) -> None:
        if not self.assignment:
            raise SCMError("empty intervention is not permitted; use observational query")
        # Freeze as dict copy
        object.__setattr__(self, "assignment", dict(self.assignment))

    def mutilated_graph(self, dag: CausalDAG) -> CausalDAG:
        return dag.mutilate(self.assignment.keys())


def intervene(scm: FiniteSCM, intervention: Intervention) -> FiniteDistribution:
    """Return the interventional distribution P(V | do(intervention))."""
    return scm.interventional_distribution(intervention.assignment)


def conditioning_is_not_intervention_witness(
    scm: FiniteSCM,
    treatment: str,
    treatment_value: object,
    outcome: str,
) -> dict:
    """Demonstrate numerically that P(Y|X=x) may differ from P(Y|do(X=x)).

    Returns both distributions' marginals on outcome and whether they differ.
    """
    obs = scm.observational_distribution()
    try:
        cond = obs.condition({treatment: treatment_value}).marginal([outcome])
        cond_ok = True
        cond_err = None
    except Exception as e:  # ConditioningError or other
        cond = None
        cond_ok = False
        cond_err = str(e)
    interv = scm.interventional_distribution({treatment: treatment_value}).marginal(
        [outcome]
    )
    differ = True
    if cond_ok and cond is not None:
        differ = not cond.equals_exact(interv)
    return {
        "conditioning_defined": cond_ok,
        "conditioning_error": cond_err,
        "conditional_outcome": None if cond is None else cond.to_dict(),
        "interventional_outcome": interv.to_dict(),
        "distributions_differ": differ,
        "interpretation": (
            "Hard intervention mutilates mechanisms; conditioning does not. "
            "Equality may hold in special cases (e.g., randomization) but is not identity."
        ),
    }
