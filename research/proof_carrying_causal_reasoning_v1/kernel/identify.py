"""Automatic identification synthesis for simple PCCR query patterns.

Given a DAG and a query kind, choose a sound strategy when one applies:
  - interventional ATE: instrument / frontdoor / backdoor (when criteria hold)
  - counterfactual: twin-network on an explicit finite SCM (caller supplies SCM)

This is a *synthesizer*, not a complete ID algorithm for arbitrary graphs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional, Sequence, Tuple

from .backdoor import find_minimal_backdoor_sets
from .dag import CausalDAG, GraphError
from .frontdoor import find_frontdoor_sets
from .instrument import verify_instrument


QueryKind = Literal["interventional_ate", "counterfactual"]


@dataclass(frozen=True, slots=True)
class IdentificationPlan:
    query_kind: QueryKind
    strategy: str
    treatment: str
    outcome: str
    adjustment_set: Optional[Tuple[str, ...]] = None
    mediators: Optional[Tuple[str, ...]] = None
    instrument: Optional[str] = None
    notes: Tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {
            "query_kind": self.query_kind,
            "strategy": self.strategy,
            "treatment": self.treatment,
            "outcome": self.outcome,
            "adjustment_set": list(self.adjustment_set) if self.adjustment_set else None,
            "mediators": list(self.mediators) if self.mediators else None,
            "instrument": self.instrument,
            "notes": list(self.notes),
        }


def synthesize_identification(
    graph: CausalDAG,
    *,
    treatment: str,
    outcome: str,
    query_kind: QueryKind = "interventional_ate",
    preferred: Optional[Sequence[str]] = None,
) -> IdentificationPlan:
    """Return the first applicable identification plan for the query.

    Preference order for interventional_ate (overridable via ``preferred``):
      instrument → frontdoor → backdoor (minimal sets)
    For counterfactual queries, returns strategy ``counterfactual`` (requires SCM).
    """
    if treatment not in graph.nodes or outcome not in graph.nodes:
        raise GraphError("unknown treatment or outcome")
    if treatment == outcome:
        raise GraphError("treatment and outcome must differ")

    if query_kind == "counterfactual":
        return IdentificationPlan(
            query_kind="counterfactual",
            strategy="counterfactual",
            treatment=treatment,
            outcome=outcome,
            notes=(
                "counterfactual identification via twin-network shared-noise abduction",
                "requires an explicit finite SCM (not observational table alone)",
            ),
        )

    order = list(preferred) if preferred else ["instrument", "frontdoor", "backdoor"]
    for name in order:
        if name == "instrument":
            plan = _try_instrument(graph, treatment, outcome)
            if plan is not None:
                return plan
        elif name == "frontdoor":
            plan = _try_frontdoor(graph, treatment, outcome)
            if plan is not None:
                return plan
        elif name == "backdoor":
            plan = _try_backdoor(graph, treatment, outcome)
            if plan is not None:
                return plan
        else:
            raise GraphError(f"unknown preferred strategy {name!r}")

    raise GraphError(
        f"no simple identification strategy found for ATE of {treatment!r} on {outcome!r}"
    )


def _try_instrument(
    graph: CausalDAG, treatment: str, outcome: str
) -> Optional[IdentificationPlan]:
    candidates = sorted(n for n in graph.nodes if n not in {treatment, outcome})
    for inst in candidates:
        iv = verify_instrument(graph, treatment, outcome, inst)
        if iv.valid:
            return IdentificationPlan(
                query_kind="interventional_ate",
                strategy="instrument",
                treatment=treatment,
                outcome=outcome,
                instrument=inst,
                adjustment_set=(inst,),
                notes=("instrumental-variable criterion satisfied",),
            )
    return None


def _try_frontdoor(
    graph: CausalDAG, treatment: str, outcome: str
) -> Optional[IdentificationPlan]:
    fds = find_frontdoor_sets(graph, treatment, outcome)
    if not fds:
        return None
    best = fds[0]
    meds = tuple(sorted(best.mediators))
    return IdentificationPlan(
        query_kind="interventional_ate",
        strategy="frontdoor",
        treatment=treatment,
        outcome=outcome,
        mediators=meds,
        adjustment_set=meds,
        notes=("front-door criterion satisfied",),
    )


def _try_backdoor(
    graph: CausalDAG, treatment: str, outcome: str
) -> Optional[IdentificationPlan]:
    mins = find_minimal_backdoor_sets(graph, treatment, outcome)
    if not mins:
        return None
    best = mins[0]
    adj = tuple(sorted(best.adjustment_set))
    return IdentificationPlan(
        query_kind="interventional_ate",
        strategy="backdoor",
        treatment=treatment,
        outcome=outcome,
        adjustment_set=adj,
        notes=("back-door criterion satisfied",),
    )
