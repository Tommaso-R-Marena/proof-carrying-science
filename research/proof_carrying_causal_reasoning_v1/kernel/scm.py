"""Exact rational finite binary SCMs with executable do-interventions."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from itertools import product
from typing import Callable, Dict, Iterable, Mapping, Optional, Tuple

from .dag import CausalDAG, GraphError
from .backdoor import verify_backdoor_set


Mechanism = Callable[[Mapping[str, int]], Fraction]
# mechanism returns P(V=1 | parents); V is Bernoulli.


@dataclass(frozen=True, slots=True)
class InterventionResult:
    treatment: str
    treatment_value: int
    outcome: str
    p_outcome_do: Fraction
    p_outcome_obs: Optional[Fraction]
    observational_association: Optional[Fraction]
    effect_exists: bool
    notes: Tuple[str, ...]

    def to_dict(self) -> dict:
        return {
            "treatment": self.treatment,
            "treatment_value": self.treatment_value,
            "outcome": self.outcome,
            "p_outcome_do": _frac(self.p_outcome_do),
            "p_outcome_obs": None if self.p_outcome_obs is None else _frac(self.p_outcome_obs),
            "observational_association": (
                None
                if self.observational_association is None
                else _frac(self.observational_association)
            ),
            "effect_exists": self.effect_exists,
            "notes": list(self.notes),
        }


@dataclass(frozen=True, slots=True)
class BinarySCM:
    """Finite binary SCM: each variable is Bernoulli given parents.

    Exact enumeration over 2^|V| assignments with rational probabilities.
    Interventions mutilate mechanisms for treated variables.
    """

    graph: CausalDAG
    mechanisms: Mapping[str, Mechanism]

    def __post_init__(self) -> None:
        if set(self.mechanisms) != set(self.graph.nodes):
            raise GraphError("mechanisms must cover exactly the graph nodes")

    def joint(self, assignment: Mapping[str, int]) -> Fraction:
        p = Fraction(1)
        for node in self.graph.topological_order():
            parents = {k: assignment[k] for k in self.graph.parents(node)}
            q = self.mechanisms[node](parents)
            if not (Fraction(0) <= q <= Fraction(1)):
                raise GraphError(f"mechanism for {node} outside [0,1]")
            bit = assignment[node]
            p *= q if bit == 1 else (1 - q)
        return p

    def observational_table(self) -> Dict[Tuple[int, ...], Fraction]:
        nodes = self.graph.topological_order()
        table: Dict[Tuple[int, ...], Fraction] = {}
        for bits in product([0, 1], repeat=len(nodes)):
            a = dict(zip(nodes, bits))
            table[bits] = self.joint(a)
        total = sum(table.values(), Fraction(0))
        if total != 1:
            raise GraphError(f"joint does not sum to 1 (got {total})")
        return table

    def p_obs(self, evidence: Mapping[str, int]) -> Fraction:
        nodes = self.graph.topological_order()
        total = Fraction(0)
        for bits, mass in self.observational_table().items():
            a = dict(zip(nodes, bits))
            if all(a[k] == v for k, v in evidence.items()):
                total += mass
        return total

    def conditional(self, query: Mapping[str, int], evidence: Mapping[str, int]) -> Fraction:
        joint_ev = self.p_obs(evidence)
        if joint_ev == 0:
            raise GraphError("conditioning on zero-probability event (positivity failure)")
        merged = dict(evidence)
        merged.update(query)
        return self.p_obs(merged) / joint_ev

    def intervene(self, do: Mapping[str, int]) -> "BinarySCM":
        """Return SCM after do(V=v) for each V in do: fix mechanism to constant."""
        for k in do:
            if k not in self.graph.nodes:
                raise GraphError(f"unknown intervention target {k!r}")
            if do[k] not in (0, 1):
                raise GraphError("binary interventions only")
        new_graph = self.graph.mutilate(do.keys())
        new_mechs: Dict[str, Mechanism] = {}
        for node, mech in self.mechanisms.items():
            if node in do:
                val = do[node]
                new_mechs[node] = (lambda _parents, v=val: Fraction(v))
            else:
                new_mechs[node] = mech
        return BinarySCM(graph=new_graph, mechanisms=new_mechs)

    def interventional_expectation(
        self,
        outcome: str,
        do: Mapping[str, int],
    ) -> Fraction:
        """Exact P(outcome=1 | do(...)) by enumerating the intervened SCM."""
        if outcome not in self.graph.nodes:
            raise GraphError("unknown outcome")
        intervened = self.intervene(do)
        return intervened.p_obs({outcome: 1})

    def observational_expectation(
        self,
        outcome: str,
        evidence: Mapping[str, int],
    ) -> Fraction:
        return self.conditional({outcome: 1}, evidence)

    def ate(self, treatment: str, outcome: str) -> Fraction:
        """Average treatment effect: E[Y|do(X=1)] - E[Y|do(X=0)]."""
        return self.interventional_expectation(outcome, {treatment: 1}) - self.interventional_expectation(
            outcome, {treatment: 0}
        )

    def backdoor_estimate(
        self,
        treatment: str,
        outcome: str,
        treatment_value: int,
        z: Iterable[str],
    ) -> Optional[Fraction]:
        """Compute the backdoor functional on the observational law; None if positivity fails."""
        Z = list(z)
        check = verify_backdoor_set(self.graph, treatment, outcome, Z)
        if not check.valid:
            raise GraphError("backdoor set invalid; refuse estimation")
        try:
            if not Z:
                return self.observational_expectation(outcome, {treatment: treatment_value})
            # Σ_z P(Y=1|X=x,Z=z) P(Z=z)
            total = Fraction(0)
            for bits in product([0, 1], repeat=len(Z)):
                z_assign = dict(zip(Z, bits))
                pz = self.p_obs(z_assign)
                if pz == 0:
                    continue
                ev = dict(z_assign)
                ev[treatment] = treatment_value
                if self.p_obs(ev) == 0:
                    return None  # positivity failure
                total += self.observational_expectation(outcome, ev) * pz
            return total
        except GraphError:
            return None

    def analyze_effect(
        self,
        treatment: str,
        outcome: str,
        treatment_value: int = 1,
    ) -> InterventionResult:
        p_do = self.interventional_expectation(outcome, {treatment: treatment_value})
        p_do0 = self.interventional_expectation(outcome, {treatment: 0})
        notes: list[str] = []
        try:
            p_obs = self.observational_expectation(outcome, {treatment: treatment_value})
        except GraphError as exc:
            p_obs = None
            notes.append(f"observational conditional undefined: {exc}")
        try:
            p_obs0 = self.observational_expectation(outcome, {treatment: 0})
            assoc = (
                None
                if p_obs is None
                else (p_obs - p_obs0)
            )
        except GraphError:
            assoc = None
            notes.append("observational association undefined")
        effect = p_do - p_do0
        if assoc is not None and assoc != effect:
            notes.append(
                f"observational association {_frac(assoc)} differs from ATE {_frac(effect)} "
                "(correlation ≠ causation under this SCM)"
            )
        return InterventionResult(
            treatment=treatment,
            treatment_value=treatment_value,
            outcome=outcome,
            p_outcome_do=p_do,
            p_outcome_obs=p_obs,
            observational_association=assoc,
            effect_exists=effect != 0,
            notes=tuple(notes),
        )


def _frac(x: Fraction) -> str:
    return f"{x.numerator}/{x.denominator}"


def bernoulli(p: Fraction) -> Mechanism:
    return lambda _parents: p


def logistic_from_parents(
    weights: Mapping[str, Fraction],
    bias: Fraction,
) -> Mechanism:
    """Affine-Bernoulli: clip(bias + Σ w_i parent_i) into [0,1] as exact Fraction."""

    def mech(parents: Mapping[str, int]) -> Fraction:
        s = bias
        for k, w in weights.items():
            s += w * parents[k]
        if s < 0:
            return Fraction(0)
        if s > 1:
            return Fraction(1)
        return Fraction(s)

    return mech
