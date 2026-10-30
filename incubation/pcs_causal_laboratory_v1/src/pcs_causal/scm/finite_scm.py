"""Finite discrete structural causal models with exact exogenous distributions.

An SCM is not a Bayesian network: structural equations define mechanisms that
are mutilated under interventions. The observational distribution is induced
by pushing the exogenous measure through the mechanisms in topological order.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from itertools import product
from typing import Callable, Dict, Iterable, Mapping, Optional, Sequence, Tuple

from pcs_causal.graphs.dag import CausalDAG, GraphError
from pcs_causal.probability.rational_pmf import FiniteDistribution, Rational, _canon


class SCMError(ValueError):
    """Malformed structural causal model."""


Mechanism = Callable[[Mapping[str, object]], object]


@dataclass(frozen=True, slots=True)
class FiniteSCM:
    """Finite SCM M = ⟨U, V, F, P(U)⟩ with endogenous V and exogenous U.

    Endogenous mechanisms are deterministic functions of parents ∪ exogenous
    noise variables assigned to each endogenous node. For exact enumeration we
    represent each endogenous variable V_i as depending on an explicit noise
    U_i (and possibly parent endogenous values).

    Parameters
    ----------
    endogenous:
        Endogenous variable names.
    exogenous:
        Exogenous variable names.
    domains:
        Domains for all endogenous and exogenous variables.
    dag:
        Causal DAG over endogenous variables only (edges encode mechanism deps).
    mechanisms:
        Map endogenous variable → function(assignment) → value.
        The assignment includes all parents and the designated noise variable
        `noise_of[v]` when present.
    noise_of:
        Map endogenous → its private exogenous noise variable (optional if
        mechanism reads exogenous names directly).
    exogenous_dist:
        Joint distribution over exogenous variables (exact rational).
    """

    endogenous: Tuple[str, ...]
    exogenous: Tuple[str, ...]
    domains: Mapping[str, Tuple[object, ...]]
    dag: CausalDAG
    mechanisms: Mapping[str, Mechanism]
    exogenous_dist: FiniteDistribution
    noise_of: Mapping[str, str]

    def __post_init__(self) -> None:
        endo = set(self.endogenous)
        exo = set(self.exogenous)
        if endo & exo:
            raise SCMError("endogenous and exogenous must be disjoint")
        if set(self.dag.nodes) != endo:
            raise SCMError("DAG nodes must equal endogenous variables")
        if set(self.mechanisms) != endo:
            raise SCMError("mechanisms must be defined for all endogenous variables")
        all_vars = endo | exo
        if set(self.domains) != all_vars:
            raise SCMError("domains must cover endogenous and exogenous variables")
        if set(self.exogenous_dist.variables) != exo:
            raise SCMError("exogenous_dist variables must match exogenous set")
        for v, u in self.noise_of.items():
            if v not in endo:
                raise SCMError(f"noise_of key {v!r} not endogenous")
            if u not in exo:
                raise SCMError(f"noise variable {u!r} not exogenous")

    @classmethod
    def from_tables(
        cls,
        dag: CausalDAG,
        exogenous_domains: Mapping[str, Sequence[object]],
        exogenous_probs: Mapping[Mapping[str, object], object],
        tables: Mapping[str, Mapping[Tuple[object, ...], object]],
        parent_order: Optional[Mapping[str, Sequence[str]]] = None,
        noise_name: Optional[Mapping[str, str]] = None,
    ) -> "FiniteSCM":
        """Build an SCM from explicit CPT-like structural tables.

        Each table maps (parent values in declared order +, optional noise) → value.
        If noise_name is omitted, independent noise U_v is created per node with
        a singleton domain {0} (deterministic given parents).
        """
        endo = tuple(sorted(dag.nodes))
        noise_of: Dict[str, str] = {}
        exo_domains = {k: tuple(v) for k, v in exogenous_domains.items()}
        mechanisms: Dict[str, Mechanism] = {}
        po = parent_order or {}

        for v in endo:
            parents = list(po.get(v, sorted(dag.parents(v))))
            u = (noise_name or {}).get(v)
            if u is None:
                u = f"U_{v}"
                if u not in exo_domains:
                    exo_domains[u] = (0,)
            noise_of[v] = u
            table = tables[v]
            keys = parents + [u]

            def make_mech(
                keys=keys, table=table, v=v
            ) -> Mechanism:
                def mech(assign: Mapping[str, object]) -> object:
                    key = tuple(assign[k] for k in keys)
                    if key not in table:
                        raise SCMError(f"mechanism table for {v} missing key {key}")
                    return table[key]

                return mech

            mechanisms[v] = make_mech()

        # Extend exogenous probs if singleton noises were added
        exo_names = tuple(sorted(exo_domains))
        # Rebuild exogenous distribution if needed
        from pcs_causal.probability.rational_pmf import FiniteDistribution

        base = FiniteDistribution.from_mapping(exogenous_domains, exogenous_probs)
        # If we added singleton noises, expand by product
        extra = [u for u in exo_names if u not in base.variables]
        if extra:
            # Each extra is singleton domain — multiply measure
            mass = {}
            for a, p in base.mass.items():
                d = dict(a)
                for u in extra:
                    d[u] = exo_domains[u][0]
                mass[_canon(d)] = p
            exo_dist = FiniteDistribution(
                variables=tuple(sorted(d for d in exo_domains)),
                domains=exo_domains,
                mass=mass,
            )
        else:
            exo_dist = base

        domains = {**{v: _infer_endo_domain(tables[v]) for v in endo}, **exo_domains}
        # Prefer explicit domains from table values
        return cls(
            endogenous=endo,
            exogenous=exo_names,
            domains=domains,
            dag=dag,
            mechanisms=mechanisms,
            exogenous_dist=exo_dist,
            noise_of=noise_of,
        )

    def observational_distribution(self) -> FiniteDistribution:
        """Pushforward of P(U) through structural equations (exact)."""
        return self._pushforward(mechanisms=self.mechanisms, intervened={})

    def interventional_distribution(
        self, do: Mapping[str, object]
    ) -> FiniteDistribution:
        """Distribution under hard intervention do(V_i = v_i).

        Mechanisms for intervened variables are replaced by constants.
        This is not ordinary conditioning.
        """
        for k, v in do.items():
            if k not in self.endogenous:
                raise SCMError(f"intervention on non-endogenous {k!r}")
            if v not in self.domains[k]:
                raise SCMError(f"intervention value {v!r} outside domain of {k}")
        return self._pushforward(mechanisms=self.mechanisms, intervened=dict(do))

    def _pushforward(
        self,
        mechanisms: Mapping[str, Mechanism],
        intervened: Mapping[str, object],
    ) -> FiniteDistribution:
        order = self.dag.topological_order()
        endo_domains = {v: self.domains[v] for v in self.endogenous}
        acc: Dict[Tuple[Tuple[str, object], ...], Rational] = {}

        for u_assign, p in self.exogenous_dist.mass.items():
            env: Dict[str, object] = dict(u_assign)
            for v in order:
                if v in intervened:
                    env[v] = intervened[v]
                else:
                    env[v] = mechanisms[v](env)
                    if env[v] not in self.domains[v]:
                        raise SCMError(
                            f"mechanism for {v} produced out-of-domain value {env[v]!r}"
                        )
            obs = _canon({v: env[v] for v in self.endogenous})
            acc[obs] = acc.get(obs, Fraction(0)) + p

        # Ensure normalization (should already be 1)
        total = sum(acc.values(), Fraction(0))
        if total != 1:
            # Numerical/rational accumulation error would be a bug
            raise SCMError(f"pushforward mass not 1: {total}")
        return FiniteDistribution(
            variables=tuple(sorted(self.endogenous)),
            domains=endo_domains,
            mass=acc,
        )

    def query_interventional_expectation(
        self, outcome: str, do: Mapping[str, object], value_map: Optional[Mapping[object, Rational]] = None
    ) -> Rational:
        dist = self.interventional_distribution(do)
        if value_map is None:
            def fn(a: Mapping[str, object]) -> Rational:
                val = a[outcome]
                if not isinstance(val, (int, Fraction)):
                    raise SCMError("outcome values must be numeric for default expectation")
                return Fraction(val)
        else:
            def fn(a: Mapping[str, object]) -> Rational:
                return Fraction(value_map[a[outcome]])

        return dist.expectation(fn)

    def ate(
        self,
        treatment: str,
        outcome: str,
        a: object = 1,
        b: object = 0,
        value_map: Optional[Mapping[object, Rational]] = None,
    ) -> Rational:
        """Average treatment effect E[Y|do(X=a)] - E[Y|do(X=b)]."""
        ea = self.query_interventional_expectation(outcome, {treatment: a}, value_map)
        eb = self.query_interventional_expectation(outcome, {treatment: b}, value_map)
        return ea - eb

    def to_dict(self) -> dict:
        return {
            "endogenous": list(self.endogenous),
            "exogenous": list(self.exogenous),
            "domains": {k: list(v) for k, v in self.domains.items()},
            "dag": self.dag.to_dict(),
            "noise_of": dict(self.noise_of),
            "exogenous_dist": self.exogenous_dist.to_dict(),
            "note": "mechanisms are not serialized (callables); use tables factory for portable models",
        }


def _infer_endo_domain(table: Mapping[Tuple[object, ...], object]) -> Tuple[object, ...]:
    vals = sorted(set(table.values()), key=lambda x: str(x))
    return tuple(vals)
