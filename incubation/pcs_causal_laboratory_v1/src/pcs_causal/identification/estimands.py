"""Supported causal estimands with explicit assumption hooks."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import FrozenSet, Optional, Tuple


class EstimandKind(str, Enum):
    INTERVENTIONAL_PROB = "P(Y|do(X))"
    INTERVENTIONAL_EXPECTATION = "E[Y|do(X)]"
    ATE = "ATE"
    CATE = "CATE"
    ATT = "ATT"
    CONTROLLED_DIRECT_EFFECT = "CDE"


@dataclass(frozen=True, slots=True)
class CausalQuery:
    """A precisely scoped causal query.

    Identification status answers whether the query is uniquely determined by
    the observational distribution under the declared model class — not whether
    the assumptions hold in nature.
    """

    kind: EstimandKind
    treatment: str
    outcome: str
    treatment_value: object = 1
    control_value: object = 0
    covariates: Tuple[str, ...] = ()
    mediators: Tuple[str, ...] = ()
    observed: Tuple[str, ...] = ()
    assumptions: Tuple[str, ...] = ()

    def required_assumptions_template(self) -> Tuple[str, ...]:
        base = (
            "acyclicity",
            "consistency",
            "graphical_markov_relative_to_declared_dag",
        )
        if self.kind in {EstimandKind.ATE, EstimandKind.INTERVENTIONAL_PROB, EstimandKind.INTERVENTIONAL_EXPECTATION}:
            return base + ("positivity_for_adjustment_formula",)
        if self.kind == EstimandKind.ATT:
            return base + (
                "positivity_for_treated_support",
                "exchangeability_for_ATT_under_declared_adjustment",
            )
        if self.kind == EstimandKind.CONTROLLED_DIRECT_EFFECT:
            return base + (
                "no_unmeasured_intermediate_confounding_for_supported_CDE",
                "positivity",
            )
        return base
