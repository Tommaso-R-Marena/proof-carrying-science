"""Simulated experimental design (computational, not real-world interventions)."""

from pcs_causal.experiments.design import (
    ExperimentProposal,
    distinguish_by_intervention,
    select_best_intervention,
)

__all__ = [
    "ExperimentProposal",
    "distinguish_by_intervention",
    "select_best_intervention",
]
