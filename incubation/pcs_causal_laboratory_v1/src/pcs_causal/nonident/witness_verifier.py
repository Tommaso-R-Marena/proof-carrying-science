"""Independent verifier for non-identifiability witnesses.

A valid witness is stronger than failure to find an identification formula:
two models in the allowed class agree on all permitted observational quantities
but disagree on the target causal quantity.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Any, Mapping, Optional, Tuple

from pcs_causal.hypothesis.states import ScientificStatus
from pcs_causal.probability.rational_pmf import FiniteDistribution
from pcs_causal.scm.finite_scm import FiniteSCM


@dataclass(frozen=True, slots=True)
class NonIdentWitness:
    """Pair of finite SCMs witnessing non-identifiability of a query."""

    model_a: FiniteSCM
    model_b: FiniteSCM
    treatment: str
    outcome: str
    treatment_value: object
    observed_vars: Tuple[str, ...]
    label: str = "nonidentifiability_witness"

    def observational_a(self) -> FiniteDistribution:
        return self.model_a.observational_distribution().marginal(self.observed_vars)

    def observational_b(self) -> FiniteDistribution:
        return self.model_b.observational_distribution().marginal(self.observed_vars)

    def interventional_a(self) -> FiniteDistribution:
        return self.model_a.interventional_distribution(
            {self.treatment: self.treatment_value}
        ).marginal([self.outcome])

    def interventional_b(self) -> FiniteDistribution:
        return self.model_b.interventional_distribution(
            {self.treatment: self.treatment_value}
        ).marginal([self.outcome])


@dataclass(frozen=True, slots=True)
class WitnessVerdict:
    accepted: bool
    status: ScientificStatus
    reasons: Tuple[str, ...]
    obs_tv: Fraction
    interv_tv: Fraction
    scope: str

    def to_dict(self) -> dict:
        return {
            "accepted": self.accepted,
            "status": self.status.value,
            "reasons": list(self.reasons),
            "observational_total_variation": [
                self.obs_tv.numerator,
                self.obs_tv.denominator,
            ],
            "interventional_outcome_total_variation": [
                self.interv_tv.numerator,
                self.interv_tv.denominator,
            ],
            "scope": self.scope,
        }


def verify_witness(witness: NonIdentWitness) -> WitnessVerdict:
    """Independently recompute observational agreement and interventional disagreement.

    Does not trust producer-supplied PASS fields.
    """
    reasons = []
    scope = (
        "Conclusion scoped to the finite SCM model class with the declared "
        "endogenous/exogenous structure of the two witness models. "
        "A finite witness does not prove non-identifiability in every causal formalism."
    )

    # Well-formedness already enforced by FiniteSCM constructors; re-check domains
    for name, m in (("A", witness.model_a), ("B", witness.model_b)):
        if witness.treatment not in m.endogenous:
            reasons.append(f"model {name}: treatment not endogenous")
        if witness.outcome not in m.endogenous:
            reasons.append(f"model {name}: outcome not endogenous")
        if not set(witness.observed_vars) <= set(m.endogenous):
            reasons.append(f"model {name}: observed_vars not subset of endogenous")

    if reasons:
        return WitnessVerdict(
            accepted=False,
            status=ScientificStatus.UNSUPPORTED,
            reasons=tuple(reasons),
            obs_tv=Fraction(1),
            interv_tv=Fraction(0),
            scope=scope,
        )

    obs_a = witness.observational_a()
    obs_b = witness.observational_b()
    try:
        obs_tv = obs_a.total_variation(obs_b)
    except ValueError as e:
        return WitnessVerdict(
            accepted=False,
            status=ScientificStatus.UNSUPPORTED,
            reasons=(f"observational domain mismatch: {e}",),
            obs_tv=Fraction(1),
            interv_tv=Fraction(0),
            scope=scope,
        )

    int_a = witness.interventional_a()
    int_b = witness.interventional_b()
    interv_tv = int_a.total_variation(int_b)

    if obs_tv != 0:
        reasons.append(
            f"observational distributions differ (TV={obs_tv}); not a valid witness"
        )
    if interv_tv == 0:
        reasons.append(
            "interventional outcome distributions agree; witness does not show disagreement"
        )

    accepted = obs_tv == 0 and interv_tv != 0
    if accepted:
        reasons = (
            "models agree exactly on permitted observational margins",
            "models disagree on target interventional outcome distribution",
            "therefore the target is not uniquely identified from those observations "
            "within this finite model class",
        )
        status = ScientificStatus.NOT_IDENTIFIABLE
    else:
        status = ScientificStatus.UNSUPPORTED

    return WitnessVerdict(
        accepted=accepted,
        status=status,
        reasons=tuple(reasons),
        obs_tv=obs_tv,
        interv_tv=interv_tv,
        scope=scope,
    )
