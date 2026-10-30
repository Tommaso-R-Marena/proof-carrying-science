"""Backdoor adjustment criterion (Pearl) for DAGs with causal sufficiency.

Under the stated assumptions, if Z satisfies the backdoor criterion relative
to (X, Y), then:

    P(Y | do(X=x)) = Σ_z P(Y | X=x, Z=z) P(Z=z)

whenever the observational conditional probabilities are defined (positivity).

This module checks the graphical criterion and emits an identification formula
with explicit assumption obligations. It does not claim the assumptions hold
empirically.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import chain, combinations
from typing import FrozenSet, Iterable, List, Optional, Sequence, Set, Tuple

from pcs_causal.graphs.dag import CausalDAG, GraphError
from pcs_causal.graphs.d_separation import find_backdoor_paths, path_blocked
from pcs_causal.hypothesis.states import ScientificStatus


@dataclass(frozen=True, slots=True)
class BackdoorResult:
    treatment: str
    outcome: str
    adjustment_set: FrozenSet[str]
    valid: bool
    reasons: Tuple[str, ...]
    formula: Optional[str]
    assumptions: Tuple[str, ...]
    status: ScientificStatus
    positivity_obligation: str

    def to_dict(self) -> dict:
        return {
            "treatment": self.treatment,
            "outcome": self.outcome,
            "adjustment_set": sorted(self.adjustment_set),
            "valid": self.valid,
            "reasons": list(self.reasons),
            "formula": self.formula,
            "assumptions": list(self.assumptions),
            "status": self.status.value,
            "positivity_obligation": self.positivity_obligation,
        }


_ASSUMPTIONS = (
    "dag_is_correct_causal_graph",
    "causal_sufficiency_no_latent_confounders_among_modeled_vars",
    "acyclicity",
    "consistency_Yx_equals_Y_when_X_x",
    "graphical_markov_condition",
    "positivity_P(X=x|Z=z)>0_for_all_z_with_P(Z=z)>0",
)


def verify_backdoor_set(
    graph: CausalDAG,
    treatment: str,
    outcome: str,
    z: Iterable[str],
) -> BackdoorResult:
    """Check whether Z satisfies the backdoor criterion for (treatment, outcome)."""
    if treatment not in graph.nodes or outcome not in graph.nodes:
        raise GraphError("unknown treatment or outcome")
    Z = frozenset(z)
    if treatment in Z or outcome in Z:
        return BackdoorResult(
            treatment=treatment,
            outcome=outcome,
            adjustment_set=Z,
            valid=False,
            reasons=("adjustment set must not contain treatment or outcome",),
            formula=None,
            assumptions=_ASSUMPTIONS,
            status=ScientificStatus.UNSUPPORTED,
            positivity_obligation=_ASSUMPTIONS[-1],
        )

    reasons: List[str] = []

    # (i) no node in Z is a descendant of treatment
    desc = graph.descendants(treatment)
    bad = Z & desc
    if bad:
        reasons.append(f"adjustment set contains descendants of treatment: {sorted(bad)}")

    # (ii) Z blocks every backdoor path from treatment to outcome.
    # A backdoor path is a path X — … — Y that begins with an arrow into X (Pearl).
    # NOTE: Do NOT equate this with "X ⊥ Y | Z in G_underline{X}"; that check is
    # incorrect for adjustment because directed causal paths X→…→Y remain open there.
    # The do-calculus Rule-2 reading uses a different sequential derivation.
    backdoors = find_backdoor_paths(graph, treatment, outcome)
    open_paths = [p for p in backdoors if not path_blocked(graph, p, Z)]
    if open_paths:
        reasons.append(
            "unblocked backdoor paths remain: "
            + "; ".join("–".join(p) for p in open_paths[:5])
        )

    valid = (not bad) and (not open_paths) and treatment not in Z and outcome not in Z
    if valid:
        if Z:
            formula = (
                f"P({outcome} | do({treatment}=x)) = "
                f"Σ_{{{','.join(sorted(Z))}}} "
                f"P({outcome} | {treatment}=x, {','.join(sorted(Z))}) "
                f"P({','.join(sorted(Z))})"
            )
        else:
            formula = f"P({outcome} | do({treatment}=x)) = P({outcome} | {treatment}=x)"
        status = ScientificStatus.IDENTIFIED_UNDER_ASSUMPTIONS
        reasons = ("backdoor criterion satisfied under declared assumptions",)
    else:
        formula = None
        status = ScientificStatus.NOT_IDENTIFIABLE
        if not reasons:
            reasons = ("backdoor criterion not satisfied",)

    return BackdoorResult(
        treatment=treatment,
        outcome=outcome,
        adjustment_set=Z,
        valid=valid,
        reasons=tuple(reasons),
        formula=formula,
        assumptions=_ASSUMPTIONS,
        status=status,
        positivity_obligation=_ASSUMPTIONS[-1],
    )


def find_backdoor_adjustment_sets(
    graph: CausalDAG,
    treatment: str,
    outcome: str,
    candidates: Optional[Iterable[str]] = None,
    max_size: Optional[int] = None,
) -> List[BackdoorResult]:
    """Enumerate adjustment sets from a candidate pool that satisfy backdoor."""
    if candidates is None:
        pool = sorted(
            n
            for n in graph.nodes
            if n not in {treatment, outcome} and n not in graph.descendants(treatment)
        )
    else:
        pool = sorted(set(candidates) - {treatment, outcome})
    if max_size is None:
        max_size = len(pool)
    results: List[BackdoorResult] = []
    for r in range(0, max_size + 1):
        for subset in combinations(pool, r):
            res = verify_backdoor_set(graph, treatment, outcome, subset)
            if res.valid:
                results.append(res)
    # Prefer smaller sets first
    results.sort(key=lambda r: (len(r.adjustment_set), sorted(r.adjustment_set)))
    return results


def apply_backdoor_to_distribution(
    obs: "FiniteDistribution",
    treatment: str,
    outcome: str,
    treatment_value: object,
    z: Iterable[str],
) -> "Fraction | None":
    """Compute the backdoor functional on an exact observational distribution.

    Returns None if positivity fails (zero-probability cells needed by the formula).
    """
    from fractions import Fraction
    from pcs_causal.probability.rational_pmf import ConditioningError, FiniteDistribution

    Z = list(z)
    # E[Y | do(X=x)] for binary/numeric Y via Σ_z E[Y|X=x,Z=z] P(Z=z)
    # Here return P(Y=1 | do(X=x)) if Y binary {0,1}, else expectation if numeric.
    y_domain = obs.domains[outcome]
    z_marg = obs.marginal(Z) if Z else None
    total = Fraction(0)

    def ey_given(evidence: dict) -> Fraction:
        # expectation of outcome under conditional
        try:
            cond = obs.condition(evidence)
        except ConditioningError:
            raise
        return cond.expectation(
            lambda a: Fraction(a[outcome])
            if isinstance(a[outcome], (int, Fraction))
            else Fraction(1 if a[outcome] else 0)
        )

    try:
        if not Z:
            return ey_given({treatment: treatment_value})
        assert z_marg is not None
        for za, pz in z_marg.mass.items():
            if pz == 0:
                continue
            ev = dict(za)
            ev[treatment] = treatment_value
            # positivity: need P(X=x,Z=z)>0 which condition checks
            total += ey_given(ev) * pz
        return total
    except ConditioningError:
        return None
