"""Exact twin-network counterfactuals on finite binary Markovian SCMs.

Implements Pearl's abduction–action–prediction with shared exogenous noise:

  For each endogenous V with mechanism p(pa)=P(V=1|pa), take U_V ~ Unif[0,1]
  and set V = 1[U_V < p(pa)]. Factual evidence constrains each U_V to an
  interval; the counterfactual world reuses the same U_V under a mutilated
  graph (do). All probabilities remain exact rationals.

This is identification under the standard SCM/Markovian assumptions for the
*declared* finite model — not empirical causation or production PCS authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from itertools import product
from typing import Dict, Mapping, Optional, Tuple

from .dag import CausalDAG, GraphError
from .scm import BinarySCM


ASSUMPTIONS = (
    "dag_is_correct_causal_graph",
    "markovian_independent_exogenous_noises",
    "consistency_Yx_equals_Y_when_X_x",
    "positivity_for_observed_evidence",
    "counterfactual_twin_network_shared_noise",
)


@dataclass(frozen=True, slots=True)
class CounterfactualResult:
    treatment: str
    treatment_value: int
    outcome: str
    evidence: Tuple[Tuple[str, int], ...]
    probability: Fraction
    evidence_mass: Fraction
    notes: Tuple[str, ...]

    def to_dict(self) -> dict:
        return {
            "treatment": self.treatment,
            "treatment_value": self.treatment_value,
            "outcome": self.outcome,
            "evidence": {k: v for k, v in self.evidence},
            "probability": _f(self.probability),
            "evidence_mass": _f(self.evidence_mass),
            "notes": list(self.notes),
            "criterion": "counterfactual_twin_network",
        }


def counterfactual_probability(
    scm: BinarySCM,
    *,
    outcome: str,
    treatment: str,
    treatment_value: int,
    evidence: Mapping[str, int],
) -> CounterfactualResult:
    """Exact P(Y_{do(treatment=treatment_value)}=1 | evidence)."""
    if outcome not in scm.graph.nodes or treatment not in scm.graph.nodes:
        raise GraphError("unknown outcome or treatment")
    if treatment_value not in (0, 1):
        raise GraphError("binary treatment_value required")
    for k, v in evidence.items():
        if k not in scm.graph.nodes:
            raise GraphError(f"unknown evidence variable {k!r}")
        if v not in (0, 1):
            raise GraphError("binary evidence required")

    ev_mass = scm.p_obs(evidence)
    if ev_mass == 0:
        raise GraphError("counterfactual conditioning on zero-probability evidence")

    nodes = scm.graph.topological_order()
    numer = Fraction(0)
    # Enumerate factual worlds consistent with evidence.
    for bits in product([0, 1], repeat=len(nodes)):
        factual = dict(zip(nodes, bits))
        if any(factual[k] != v for k, v in evidence.items()):
            continue
        w_f = scm.joint(factual)
        if w_f == 0:
            continue
        # Given factual world, sum counterfactual outcome probability.
        p_y = _cf_outcome_given_factual(
            scm,
            factual=factual,
            treatment=treatment,
            treatment_value=treatment_value,
            outcome=outcome,
        )
        numer += w_f * p_y

    prob = numer / ev_mass
    ev_tuple = tuple(sorted((k, int(v)) for k, v in evidence.items()))
    return CounterfactualResult(
        treatment=treatment,
        treatment_value=treatment_value,
        outcome=outcome,
        evidence=ev_tuple,
        probability=prob,
        evidence_mass=ev_mass,
        notes=(
            "exact twin-network abduction–action–prediction on finite binary SCM",
            "shared Unif[0,1] exogenous noise per endogenous variable",
        ),
    )


def _cf_outcome_given_factual(
    scm: BinarySCM,
    *,
    factual: Mapping[str, int],
    treatment: str,
    treatment_value: int,
    outcome: str,
) -> Fraction:
    """P(Y_{x*}=1 | factual world) by enumerating counterfactual assignments."""
    nodes = scm.graph.topological_order()
    # Non-intervened nodes that can vary in the CF world.
    free = [n for n in nodes if n != treatment]
    total = Fraction(0)
    for bits in product([0, 1], repeat=len(free)):
        cf = {treatment: treatment_value}
        cf.update(zip(free, bits))
        w = _cf_assignment_weight(scm, factual=factual, counterfactual=cf, treatment=treatment)
        if cf[outcome] == 1:
            total += w
    return total


def _cf_assignment_weight(
    scm: BinarySCM,
    *,
    factual: Mapping[str, int],
    counterfactual: Mapping[str, int],
    treatment: str,
) -> Fraction:
    """Probability of a full CF assignment given factual, via shared-noise bridges."""
    w = Fraction(1)
    for node in scm.graph.topological_order():
        if node == treatment:
            # Action: forced; weight 1 if matches intervention value already set.
            continue
        f_parents = {p: factual[p] for p in scm.graph.parents(node)}
        c_parents = {p: counterfactual[p] for p in scm.graph.parents(node)}
        p_f = scm.mechanisms[node](f_parents)
        p_c = scm.mechanisms[node](c_parents)
        q = _bridge_prob_one(factual_bit=factual[node], p_factual=p_f, p_counterfactual=p_c)
        bit = counterfactual[node]
        w *= q if bit == 1 else (1 - q)
    return w


def _bridge_prob_one(
    *,
    factual_bit: int,
    p_factual: Fraction,
    p_counterfactual: Fraction,
) -> Fraction:
    """P(C=1 | F, p_f, p_c) for shared U~Unif[0,1], F=1[U<p_f], C=1[U<p_c]."""
    if not (Fraction(0) <= p_factual <= 1 and Fraction(0) <= p_counterfactual <= 1):
        raise GraphError("mechanism probability outside [0,1]")
    if factual_bit == 1:
        if p_factual == 0:
            raise GraphError("inconsistent factual bit with zero probability")
        # U ~ Unif[0, p_f) ⇒ P(U < p_c) = min(p_f, p_c) / p_f
        return min(p_factual, p_counterfactual) / p_factual
    # factual_bit == 0: U ~ Unif[p_f, 1]
    if p_factual == 1:
        raise GraphError("inconsistent factual bit with probability one")
    if p_counterfactual <= p_factual:
        return Fraction(0)
    return (p_counterfactual - p_factual) / (1 - p_factual)


def _f(x: Fraction) -> str:
    return f"{x.numerator}/{x.denominator}"
