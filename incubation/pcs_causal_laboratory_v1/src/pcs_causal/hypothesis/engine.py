"""Hypothesis generation as untrusted proposals subordinate to checking."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from pcs_causal.graphs.dag import CausalDAG
from pcs_causal.hypothesis.states import ScientificStatus
from pcs_causal.identification.backdoor import find_backdoor_adjustment_sets, verify_backdoor_set
from pcs_causal.identification.frontdoor import check_frontdoor


@dataclass
class CausalHypothesis:
    variables: Tuple[str, ...]
    claimed_edge: Optional[Tuple[str, str]]
    graph: CausalDAG
    treatment: str
    outcome: str
    assumptions: Tuple[str, ...]
    status: ScientificStatus = ScientificStatus.OPEN
    identification_formula: Optional[str] = None
    competing: List[str] = field(default_factory=list)
    falsification_notes: List[str] = field(default_factory=list)
    unresolved_obligations: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "variables": list(self.variables),
            "claimed_edge": list(self.claimed_edge) if self.claimed_edge else None,
            "graph": self.graph.to_dict(),
            "treatment": self.treatment,
            "outcome": self.outcome,
            "assumptions": list(self.assumptions),
            "status": self.status.value,
            "identification_formula": self.identification_formula,
            "competing": list(self.competing),
            "falsification_notes": list(self.falsification_notes),
            "unresolved_obligations": list(self.unresolved_obligations),
            "trust": "UNTRUSTED_PROPOSAL",
        }


class HypothesisEngine:
    """Propose and check causal hypotheses; never treat proposals as facts."""

    def propose_from_graph(
        self,
        graph: CausalDAG,
        treatment: str,
        outcome: str,
    ) -> CausalHypothesis:
        hyp = CausalHypothesis(
            variables=tuple(sorted(graph.nodes)),
            claimed_edge=(treatment, outcome)
            if (treatment, outcome) in graph.edges
            else None,
            graph=graph,
            treatment=treatment,
            outcome=outcome,
            assumptions=(
                "dag_correct",
                "causal_sufficiency",
                "consistency",
                "positivity_if_estimating",
            ),
            unresolved_obligations=[
                "Empirical validation of graph assumptions",
                "Positivity in any finite sample used for estimation",
            ],
        )
        sets = find_backdoor_adjustment_sets(graph, treatment, outcome)
        if sets:
            hyp.status = ScientificStatus.IDENTIFIED_UNDER_ASSUMPTIONS
            hyp.identification_formula = sets[0].formula
            hyp.unresolved_obligations.append(
                f"Backdoor set {sorted(sets[0].adjustment_set)} depends on unvalidated assumptions"
            )
        else:
            # try trivial empty / parents
            res = verify_backdoor_set(graph, treatment, outcome, graph.parents(treatment))
            if res.valid:
                hyp.status = ScientificStatus.IDENTIFIED_UNDER_ASSUMPTIONS
                hyp.identification_formula = res.formula
            else:
                hyp.status = ScientificStatus.NOT_IDENTIFIABLE
                hyp.falsification_notes.append(
                    "No backdoor adjustment set found in candidate enumeration"
                )
                hyp.falsification_notes.append(
                    "Non-identifiability not yet witnessed; status may be OPEN pending witness search"
                )
                hyp.status = ScientificStatus.OPEN
        return hyp

    def try_frontdoor(
        self, hyp: CausalHypothesis, mediators: Sequence[str]
    ) -> CausalHypothesis:
        res = check_frontdoor(hyp.graph, hyp.treatment, hyp.outcome, mediators)
        if res.valid:
            hyp.status = ScientificStatus.IDENTIFIED_UNDER_ASSUMPTIONS
            hyp.identification_formula = res.formula
            hyp.assumptions = hyp.assumptions + res.assumptions
        else:
            hyp.falsification_notes.extend(res.reasons)
        return hyp

    def refute_with_ci_violation(
        self, hyp: CausalHypothesis, note: str
    ) -> CausalHypothesis:
        hyp.status = ScientificStatus.MODEL_REFUTED
        hyp.falsification_notes.append(note)
        return hyp
