"""Experiment selection among competing finite SCMs (simulated only)."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Iterable, List, Mapping, Optional, Sequence, Tuple

from pcs_causal.hypothesis.states import ScientificStatus
from pcs_causal.scm.finite_scm import FiniteSCM


@dataclass(frozen=True, slots=True)
class ExperimentProposal:
    intervention: Mapping[str, object]
    measure_vars: Tuple[str, ...]
    tv_distance: Fraction
    cost: float
    score: float
    status: ScientificStatus
    assumptions: Tuple[str, ...]
    notes: Tuple[str, ...]
    prediction_a: dict
    prediction_b: dict

    def to_dict(self) -> dict:
        return {
            "intervention": dict(self.intervention),
            "measure_vars": list(self.measure_vars),
            "tv_distance": [self.tv_distance.numerator, self.tv_distance.denominator],
            "cost": self.cost,
            "score": self.score,
            "status": self.status.value,
            "assumptions": list(self.assumptions),
            "notes": list(self.notes),
            "prediction_a": self.prediction_a,
            "prediction_b": self.prediction_b,
            "simulated_only": True,
        }


def distinguish_by_intervention(
    model_a: FiniteSCM,
    model_b: FiniteSCM,
    intervention: Mapping[str, object],
    measure: Sequence[str],
    cost: float = 1.0,
    min_tv: Fraction = Fraction(0),
) -> ExperimentProposal:
    pa = model_a.interventional_distribution(intervention).marginal(measure)
    pb = model_b.interventional_distribution(intervention).marginal(measure)
    tv = pa.total_variation(pb)
    distinguished = tv > min_tv
    score = float(tv) / max(cost, 1e-12)
    return ExperimentProposal(
        intervention=dict(intervention),
        measure_vars=tuple(measure),
        tv_distance=tv,
        cost=cost,
        score=score,
        status=ScientificStatus.EXPERIMENT_PROPOSED
        if distinguished
        else ScientificStatus.EMPIRICALLY_INCONCLUSIVE,
        assumptions=(
            "competing_models_exhaust_hypothesis_class_under_consideration",
            "intervention_is_hard_do_semantics",
            "simulated_predictions_equal_real_world_mechanisms_NOT_ASSUMED",
        ),
        notes=(
            "SIMULATED computational design only — no real experiment performed.",
            "Distinguishing two models ≠ distinguishing an entire equivalence class.",
            f"TV={tv}; distinguished={distinguished}.",
        ),
        prediction_a=pa.to_dict(),
        prediction_b=pb.to_dict(),
    )


def select_best_intervention(
    model_a: FiniteSCM,
    model_b: FiniteSCM,
    candidates: Sequence[Mapping[str, object]],
    measure: Sequence[str],
    costs: Optional[Sequence[float]] = None,
) -> ExperimentProposal:
    costs = list(costs) if costs is not None else [1.0] * len(candidates)
    if len(costs) != len(candidates):
        raise ValueError("costs length must match candidates")
    best: Optional[ExperimentProposal] = None
    for interv, c in zip(candidates, costs):
        prop = distinguish_by_intervention(model_a, model_b, interv, measure, cost=c)
        if best is None or prop.score > best.score:
            best = prop
    assert best is not None
    return best
