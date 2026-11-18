"""Proof-carrying causal claim certificates and independent checker.

Epistemic non-escalation: a valid identification certificate establishes
identification *under declared assumptions*. It never upgrades to empirical
causation, scientific truth, or production PCS authority.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from fractions import Fraction
from typing import FrozenSet, List, Optional, Sequence, Tuple

from .backdoor import (
    verify_backdoor_set,
    find_minimal_backdoor_sets,
    ASSUMPTIONS as BACKDOOR_ASSUMPTIONS,
)
from .frontdoor import verify_frontdoor_set, ASSUMPTIONS as FRONTDOOR_ASSUMPTIONS
from .instrument import (
    verify_instrument,
    balke_pearl_bounds,
    ASSUMPTIONS as INSTRUMENT_ASSUMPTIONS,
)
from .dag import CausalDAG, GraphError
from .scm import BinarySCM


CLAIM_SCHEMA_VERSION = 1

ALLOWED_VERDICTS = (
    "identified_under_assumptions",
    "not_identifiable",
    "invalid_claim",
    "malformed",
    "positivity_failure",
    "intervention_mismatch",
    "bounds_certified",
)

ALLOWED_STRATEGIES = ("backdoor", "frontdoor", "instrument")

# Concrete Lean theorem names bound to suite graph instances (not general soundness).
FORMAL_BINDINGS = {
    "backdoor": (
        "PcsPccr.ConfounderInd.Z_satisfies_backdoor",
        "PcsPccr.DoCalc.confounder_pack_backdoor",
        "PcsPccr.SCMConfounder.backdoor_matches_do_X1_Y1",
    ),
    "frontdoor": (
        "PcsPccr.FrontDoorInd.m_frontdoor_intercepts",
        "PcsPccr.FrontDoorInd.m_frontdoor_no_direct",
        "PcsPccr.FrontDoorInd.m_frontdoor_U_not_to_M",
    ),
    "instrument": (
        "PcsPccr.InstrumentInd.z_instrument_relevance",
        "PcsPccr.InstrumentInd.exclusion_no_Z_Y",
        "PcsPccr.InstrumentInd.Z_not_parent_Y_after_doX",
        "PcsPccr.InstrumentInd.u_not_instrument_exclusion",
    ),
}


def _assumptions_for(strategy: str) -> Tuple[str, ...]:
    if strategy == "frontdoor":
        return FRONTDOOR_ASSUMPTIONS
    if strategy == "instrument":
        return INSTRUMENT_ASSUMPTIONS
    return BACKDOOR_ASSUMPTIONS


# Backward-compatible alias used by older call sites / tests.
ASSUMPTIONS = BACKDOOR_ASSUMPTIONS

@dataclass(frozen=True, slots=True)
class CausalClaim:
    """Structured causal claim emitted by a model or authored control."""

    task_id: str
    treatment: str
    outcome: str
    asserts_identifiable: bool
    adjustment_set: FrozenSet[str]
    claimed_p_do: Optional[str]
    asserts_association_equals_effect: Optional[bool]
    strategy: Optional[str] = None  # "backdoor" | "frontdoor" | None→backdoor
    raw_text: str = ""

    def to_dict(self) -> dict:
        return {
            "schema_version": CLAIM_SCHEMA_VERSION,
            "task_id": self.task_id,
            "treatment": self.treatment,
            "outcome": self.outcome,
            "asserts_identifiable": self.asserts_identifiable,
            "adjustment_set": sorted(self.adjustment_set),
            "claimed_p_do": self.claimed_p_do,
            "asserts_association_equals_effect": self.asserts_association_equals_effect,
            "strategy": self.strategy or "backdoor",
        }


@dataclass(frozen=True, slots=True)
class CertificateVerdict:
    task_id: str
    accepted: bool
    verdict: str
    reasons: Tuple[str, ...]
    backdoor: Optional[dict]
    intervention: Optional[dict]
    ground_truth: dict
    claim: dict
    assumptions: Tuple[str, ...]
    certificate_sha256: str
    epistemic_ceiling: str
    frontdoor: Optional[dict] = None
    instrument: Optional[dict] = None
    bounds: Optional[dict] = None
    formal_bindings: Tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "accepted": self.accepted,
            "verdict": self.verdict,
            "reasons": list(self.reasons),
            "backdoor": self.backdoor,
            "frontdoor": self.frontdoor,
            "instrument": self.instrument,
            "bounds": self.bounds,
            "intervention": self.intervention,
            "ground_truth": self.ground_truth,
            "claim": self.claim,
            "assumptions": list(self.assumptions),
            "formal_bindings": list(self.formal_bindings),
            "certificate_sha256": self.certificate_sha256,
            "epistemic_ceiling": self.epistemic_ceiling,
            "production_authority": False,
            "empirical_causation_established": False,
        }

def parse_model_claim(task_id: str, text: str) -> CausalClaim:
    """Parse a JSON causal claim from model output; fail closed on malformation."""
    payload = _extract_json_object(text)
    if payload is None:
        return _malformed(task_id, text)
    try:
        treatment = str(payload["treatment"])
        outcome = str(payload["outcome"])
        asserts = bool(payload["asserts_identifiable"])
        adj = payload.get("adjustment_set", [])
        if not isinstance(adj, list) or not all(isinstance(x, str) for x in adj):
            raise ValueError("adjustment_set must be a list of strings")
        claimed = payload.get("claimed_p_do", None)
        if claimed is not None:
            claimed = str(claimed)
            Fraction(claimed)
        assoc_eq = payload.get("asserts_association_equals_effect", None)
        if assoc_eq is not None:
            assoc_eq = bool(assoc_eq)
        strategy = payload.get("strategy", None)
        if strategy is not None:
            strategy = str(strategy)
            if strategy not in ALLOWED_STRATEGIES:
                raise ValueError("unknown strategy")
        return CausalClaim(
            task_id=task_id,
            treatment=treatment,
            outcome=outcome,
            asserts_identifiable=asserts,
            adjustment_set=frozenset(adj),
            claimed_p_do=claimed,
            asserts_association_equals_effect=assoc_eq,
            strategy=strategy,
            raw_text=text,
        )
    except Exception:
        return _malformed(task_id, text)


def _malformed(task_id: str, text: str) -> CausalClaim:
    return CausalClaim(
        task_id=task_id,
        treatment="",
        outcome="",
        asserts_identifiable=False,
        adjustment_set=frozenset(),
        claimed_p_do=None,
        asserts_association_equals_effect=None,
        strategy=None,
        raw_text=text,
    )


def check_claim(
    claim: CausalClaim,
    graph: CausalDAG,
    scm: Optional[BinarySCM] = None,
    *,
    true_identifiable: bool,
    minimal_sets: Optional[Sequence[FrozenSet[str]]] = None,
    allowed_strategies: Sequence[str] = ("backdoor",),
) -> CertificateVerdict:
    """Independently check a causal claim against graph (+ optional executable SCM)."""
    reasons: List[str] = []
    empty = dict(
        backdoor=None, frontdoor=None, instrument=None, bounds=None, intervention=None
    )
    if not claim.treatment or not claim.outcome:
        return _verdict(
            claim,
            accepted=False,
            verdict="malformed",
            reasons=("could not parse structured causal claim JSON",),
            ground_truth={"identifiable": true_identifiable},
            **empty,
        )

    if claim.treatment not in graph.nodes or claim.outcome not in graph.nodes:
        return _verdict(
            claim,
            accepted=False,
            verdict="invalid_claim",
            reasons=("treatment or outcome not in declared graph",),
            ground_truth={"identifiable": true_identifiable},
            **empty,
        )

    strategy = claim.strategy or "backdoor"
    if strategy not in allowed_strategies:
        return _verdict(
            claim,
            accepted=False,
            verdict="invalid_claim",
            reasons=(
                f"strategy {strategy!r} not allowed for this task "
                f"(allowed: {list(allowed_strategies)})",
            ),
            ground_truth={"identifiable": true_identifiable},
            **empty,
        )

    if strategy == "instrument":
        return _check_instrument(claim, graph, scm, true_identifiable=true_identifiable)

    bd = verify_backdoor_set(graph, claim.treatment, claim.outcome, claim.adjustment_set)
    fd = verify_frontdoor_set(graph, claim.treatment, claim.outcome, claim.adjustment_set)
    mins = list(minimal_sets) if minimal_sets is not None else [
        r.adjustment_set
        for r in find_minimal_backdoor_sets(graph, claim.treatment, claim.outcome)
    ]
    id_ok = bd.valid if strategy == "backdoor" else fd.valid
    gt = {
        "identifiable": true_identifiable,
        "strategy": strategy,
        "minimal_adjustment_sets": [sorted(s) for s in mins],
        "proposed_set_valid": id_ok,
        "backdoor_valid": bd.valid,
        "frontdoor_valid": fd.valid,
    }

    intervention_info: Optional[dict] = None
    if scm is not None:
        analysis = scm.analyze_effect(claim.treatment, claim.outcome, treatment_value=1)
        intervention_info = analysis.to_dict()
        gt["ate"] = _frac(scm.ate(claim.treatment, claim.outcome))
        gt["p_do_1"] = _frac(
            scm.interventional_expectation(claim.outcome, {claim.treatment: 1})
        )
        if id_ok:
            if strategy == "backdoor":
                est = scm.backdoor_estimate(
                    claim.treatment, claim.outcome, 1, claim.adjustment_set
                )
                label = "backdoor_estimate"
            else:
                est = scm.frontdoor_estimate(
                    claim.treatment, claim.outcome, 1, claim.adjustment_set
                )
                label = "frontdoor_estimate"
            if est is None:
                reasons.append(f"positivity failure for proposed {strategy} set")
                return _verdict(
                    claim,
                    accepted=False,
                    verdict="positivity_failure",
                    reasons=tuple(reasons),
                    backdoor=bd.to_dict(),
                    frontdoor=fd.to_dict(),
                    instrument=None,
                    bounds=None,
                    intervention=intervention_info,
                    ground_truth=gt,
                )
            true_p = scm.interventional_expectation(
                claim.outcome, {claim.treatment: 1}
            )
            gt[label] = _frac(est)
            if est != true_p:
                reasons.append(
                    f"{strategy} estimate {_frac(est)} ≠ interventional {_frac(true_p)}"
                )
                return _verdict(
                    claim,
                    accepted=False,
                    verdict="intervention_mismatch",
                    reasons=tuple(reasons),
                    backdoor=bd.to_dict(),
                    frontdoor=fd.to_dict(),
                    instrument=None,
                    bounds=None,
                    intervention=intervention_info,
                    ground_truth=gt,
                )

    if claim.asserts_association_equals_effect is True and scm is not None:
        analysis = scm.analyze_effect(claim.treatment, claim.outcome)
        if analysis.observational_association is not None:
            ate = scm.ate(claim.treatment, claim.outcome)
            if analysis.observational_association != ate:
                reasons.append(
                    "claim asserts association equals effect, but executable SCM "
                    f"shows association {_frac(analysis.observational_association)} "
                    f"≠ ATE {_frac(ate)}"
                )
                return _verdict(
                    claim,
                    accepted=False,
                    verdict="invalid_claim",
                    reasons=tuple(reasons) + tuple(analysis.notes),
                    backdoor=bd.to_dict(),
                    frontdoor=fd.to_dict(),
                    instrument=None,
                    bounds=None,
                    intervention=intervention_info,
                    ground_truth=gt,
                )

    crit_reasons = bd.reasons if strategy == "backdoor" else fd.reasons

    if claim.asserts_identifiable:
        if not true_identifiable:
            reasons.append("target is not identifiable; claim overreached")
            return _verdict(
                claim,
                accepted=False,
                verdict="not_identifiable",
                reasons=tuple(reasons) + crit_reasons,
                backdoor=bd.to_dict(),
                frontdoor=fd.to_dict(),
                instrument=None,
                bounds=None,
                intervention=intervention_info,
                ground_truth=gt,
            )
        if not id_ok:
            reasons.append(f"proposed set fails the {strategy} criterion")
            return _verdict(
                claim,
                accepted=False,
                verdict="invalid_claim",
                reasons=tuple(reasons) + crit_reasons,
                backdoor=bd.to_dict(),
                frontdoor=fd.to_dict(),
                instrument=None,
                bounds=None,
                intervention=intervention_info,
                ground_truth=gt,
            )
        if claim.claimed_p_do is not None and scm is not None:
            claimed = Fraction(claim.claimed_p_do)
            true_p = scm.interventional_expectation(
                claim.outcome, {claim.treatment: 1}
            )
            if claimed != true_p:
                reasons.append(
                    f"claimed P(Y|do(X=1))={claim.claimed_p_do} ≠ exact {_frac(true_p)}"
                )
                return _verdict(
                    claim,
                    accepted=False,
                    verdict="intervention_mismatch",
                    reasons=tuple(reasons),
                    backdoor=bd.to_dict(),
                    frontdoor=fd.to_dict(),
                    instrument=None,
                    bounds=None,
                    intervention=intervention_info,
                    ground_truth=gt,
                )
        reasons.append(
            f"{strategy} identification certificate accepted under declared assumptions"
        )
        return _verdict(
            claim,
            accepted=True,
            verdict="identified_under_assumptions",
            reasons=tuple(reasons),
            backdoor=bd.to_dict(),
            frontdoor=fd.to_dict(),
            instrument=None,
            bounds=None,
            intervention=intervention_info,
            ground_truth=gt,
        )

    if true_identifiable:
        reasons.append("target is identifiable; claim incorrectly denied identification")
        return _verdict(
            claim,
            accepted=False,
            verdict="invalid_claim",
            reasons=tuple(reasons),
            backdoor=bd.to_dict(),
            frontdoor=fd.to_dict(),
            instrument=None,
            bounds=None,
            intervention=intervention_info,
            ground_truth=gt,
        )
    reasons.append("correctly recognized non-identifiability")
    return _verdict(
        claim,
        accepted=True,
        verdict="not_identifiable",
        reasons=tuple(reasons) + crit_reasons,
        backdoor=bd.to_dict(),
        frontdoor=fd.to_dict(),
        instrument=None,
        bounds=None,
        intervention=intervention_info,
        ground_truth=gt,
    )


def _check_instrument(
    claim: CausalClaim,
    graph: CausalDAG,
    scm: Optional[BinarySCM],
    *,
    true_identifiable: bool,
) -> CertificateVerdict:
    """Instrument strategy: graphical IV + Balke–Pearl bounds certificate."""
    reasons: List[str] = []
    if len(claim.adjustment_set) != 1:
        return _verdict(
            claim,
            accepted=False,
            verdict="invalid_claim",
            reasons=("instrument strategy requires exactly one instrument in adjustment_set",),
            backdoor=None,
            frontdoor=None,
            instrument=None,
            bounds=None,
            intervention=None,
            ground_truth={"identifiable": true_identifiable, "strategy": "instrument"},
        )
    inst = next(iter(claim.adjustment_set))
    iv = verify_instrument(graph, claim.treatment, claim.outcome, inst)
    gt: dict = {
        "identifiable": true_identifiable,
        "strategy": "instrument",
        "instrument_valid": iv.valid,
    }
    intervention_info = None
    bounds_info = None
    if scm is not None:
        analysis = scm.analyze_effect(claim.treatment, claim.outcome)
        intervention_info = analysis.to_dict()
        true_p = scm.interventional_expectation(claim.outcome, {claim.treatment: 1})
        true_ate = scm.ate(claim.treatment, claim.outcome)
        gt["p_do_1"] = _frac(true_p)
        gt["ate"] = _frac(true_ate)
        if iv.valid:
            try:
                bp = balke_pearl_bounds(scm, claim.treatment, claim.outcome, inst)
            except GraphError as exc:
                return _verdict(
                    claim,
                    accepted=False,
                    verdict="positivity_failure",
                    reasons=(str(exc),),
                    backdoor=None,
                    frontdoor=None,
                    instrument=iv.to_dict(),
                    bounds=None,
                    intervention=intervention_info,
                    ground_truth=gt,
                )
            bounds_info = bp.to_dict()
            gt["bounds"] = bounds_info
            if not (bp.p_do_lower <= true_p <= bp.p_do_upper):
                reasons.append(
                    f"true P(Y|do(X=1))={_frac(true_p)} outside Balke–Pearl "
                    f"[{_frac(bp.p_do_lower)}, {_frac(bp.p_do_upper)}]"
                )
                return _verdict(
                    claim,
                    accepted=False,
                    verdict="intervention_mismatch",
                    reasons=tuple(reasons),
                    backdoor=None,
                    frontdoor=None,
                    instrument=iv.to_dict(),
                    bounds=bounds_info,
                    intervention=intervention_info,
                    ground_truth=gt,
                )

    if not iv.valid:
        reasons.append("proposed instrument fails graphical IV conditions")
        return _verdict(
            claim,
            accepted=False,
            verdict="invalid_claim",
            reasons=tuple(reasons) + iv.reasons,
            backdoor=None,
            frontdoor=None,
            instrument=iv.to_dict(),
            bounds=bounds_info,
            intervention=intervention_info,
            ground_truth=gt,
        )

    # Point-identification claim only if bounds collapse.
    if claim.asserts_identifiable:
        point = bool(bounds_info and bounds_info.get("point_identified"))
        if not point:
            reasons.append(
                "instrument does not point-identify under this law; "
                "use asserts_identifiable=false to accept Balke–Pearl bounds"
            )
            return _verdict(
                claim,
                accepted=False,
                verdict="not_identifiable",
                reasons=tuple(reasons),
                backdoor=None,
                frontdoor=None,
                instrument=iv.to_dict(),
                bounds=bounds_info,
                intervention=intervention_info,
                ground_truth=gt,
            )
        reasons.append("instrument point-identified; bounds collapsed")
        return _verdict(
            claim,
            accepted=True,
            verdict="identified_under_assumptions",
            reasons=tuple(reasons),
            backdoor=None,
            frontdoor=None,
            instrument=iv.to_dict(),
            bounds=bounds_info,
            intervention=intervention_info,
            ground_truth=gt,
        )

    reasons.append(
        "instrument valid; Balke–Pearl bounds certified (partial identification)"
    )
    return _verdict(
        claim,
        accepted=True,
        verdict="bounds_certified",
        reasons=tuple(reasons) + iv.reasons,
        backdoor=None,
        frontdoor=None,
        instrument=iv.to_dict(),
        bounds=bounds_info,
        intervention=intervention_info,
        ground_truth=gt,
    )


def _verdict(
    claim: CausalClaim,
    *,
    accepted: bool,
    verdict: str,
    reasons: Tuple[str, ...],
    backdoor: Optional[dict],
    frontdoor: Optional[dict],
    instrument: Optional[dict],
    bounds: Optional[dict],
    intervention: Optional[dict],
    ground_truth: dict,
) -> CertificateVerdict:
    assert verdict in ALLOWED_VERDICTS
    strategy = claim.strategy or "backdoor"
    assumptions = _assumptions_for(strategy)
    bindings = FORMAL_BINDINGS.get(strategy, ())
    body = {
        "claim": claim.to_dict(),
        "accepted": accepted,
        "verdict": verdict,
        "reasons": list(reasons),
        "backdoor": backdoor,
        "frontdoor": frontdoor,
        "instrument": instrument,
        "bounds": bounds,
        "intervention": intervention,
        "ground_truth": ground_truth,
        "assumptions": list(assumptions),
        "formal_bindings": list(bindings),
        "epistemic_ceiling": "identified_under_assumptions_only",
    }
    digest = hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return CertificateVerdict(
        task_id=claim.task_id,
        accepted=accepted,
        verdict=verdict,
        reasons=reasons,
        backdoor=backdoor,
        frontdoor=frontdoor,
        instrument=instrument,
        bounds=bounds,
        intervention=intervention,
        ground_truth=ground_truth,
        claim=claim.to_dict(),
        assumptions=assumptions,
        certificate_sha256=digest,
        epistemic_ceiling="identified_under_assumptions_only",
        formal_bindings=bindings,
    )

def _extract_json_object(text: str) -> Optional[dict]:
    text = text.strip()
    if not text:
        return None
    candidates: List[str] = []
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence:
        candidates.append(fence.group(1))
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidates.append(text[start : end + 1])
    candidates.append(text)
    for c in candidates:
        try:
            obj = json.loads(c)
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            continue
    return None


def _frac(x: Fraction) -> str:
    return f"{x.numerator}/{x.denominator}"
