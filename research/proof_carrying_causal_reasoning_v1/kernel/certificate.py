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
from typing import Any, FrozenSet, List, Optional, Sequence, Tuple

from .backdoor import verify_backdoor_set, find_minimal_backdoor_sets, ASSUMPTIONS
from .dag import CausalDAG
from .scm import BinarySCM


CLAIM_SCHEMA_VERSION = 1

ALLOWED_VERDICTS = (
    "identified_under_assumptions",
    "not_identifiable",
    "invalid_claim",
    "malformed",
    "positivity_failure",
    "intervention_mismatch",
)


@dataclass(frozen=True, slots=True)
class CausalClaim:
    """Structured causal claim emitted by a model or authored control."""

    task_id: str
    treatment: str
    outcome: str
    # What the proposer asserts about the causal query.
    asserts_identifiable: bool
    adjustment_set: FrozenSet[str]
    # Optional numeric claim: P(Y=1|do(X=1)) as rational string "a/b" or null.
    claimed_p_do: Optional[str]
    # Optional: asserts that observational association equals causal effect.
    asserts_association_equals_effect: Optional[bool]
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

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "accepted": self.accepted,
            "verdict": self.verdict,
            "reasons": list(self.reasons),
            "backdoor": self.backdoor,
            "intervention": self.intervention,
            "ground_truth": self.ground_truth,
            "claim": self.claim,
            "assumptions": list(self.assumptions),
            "certificate_sha256": self.certificate_sha256,
            "epistemic_ceiling": self.epistemic_ceiling,
            "production_authority": False,
            "empirical_causation_established": False,
        }


def parse_model_claim(task_id: str, text: str) -> CausalClaim:
    """Parse a JSON causal claim from model output; fail closed on malformation."""
    payload = _extract_json_object(text)
    if payload is None:
        return CausalClaim(
            task_id=task_id,
            treatment="",
            outcome="",
            asserts_identifiable=False,
            adjustment_set=frozenset(),
            claimed_p_do=None,
            asserts_association_equals_effect=None,
            raw_text=text,
        )
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
            Fraction(claimed)  # validate rational
        assoc_eq = payload.get("asserts_association_equals_effect", None)
        if assoc_eq is not None:
            assoc_eq = bool(assoc_eq)
        return CausalClaim(
            task_id=task_id,
            treatment=treatment,
            outcome=outcome,
            asserts_identifiable=asserts,
            adjustment_set=frozenset(adj),
            claimed_p_do=claimed,
            asserts_association_equals_effect=assoc_eq,
            raw_text=text,
        )
    except Exception:
        return CausalClaim(
            task_id=task_id,
            treatment="",
            outcome="",
            asserts_identifiable=False,
            adjustment_set=frozenset(),
            claimed_p_do=None,
            asserts_association_equals_effect=None,
            raw_text=text,
        )


def check_claim(
    claim: CausalClaim,
    graph: CausalDAG,
    scm: Optional[BinarySCM] = None,
    *,
    true_identifiable: bool,
    minimal_sets: Optional[Sequence[FrozenSet[str]]] = None,
) -> CertificateVerdict:
    """Independently check a causal claim against graph (+ optional executable SCM)."""
    reasons: List[str] = []
    if not claim.treatment or not claim.outcome:
        return _verdict(
            claim,
            accepted=False,
            verdict="malformed",
            reasons=("could not parse structured causal claim JSON",),
            backdoor=None,
            intervention=None,
            ground_truth={"identifiable": true_identifiable},
        )

    if claim.treatment not in graph.nodes or claim.outcome not in graph.nodes:
        return _verdict(
            claim,
            accepted=False,
            verdict="invalid_claim",
            reasons=("treatment or outcome not in declared graph",),
            backdoor=None,
            intervention=None,
            ground_truth={"identifiable": true_identifiable},
        )

    bd = verify_backdoor_set(graph, claim.treatment, claim.outcome, claim.adjustment_set)
    mins = list(minimal_sets) if minimal_sets is not None else [
        r.adjustment_set
        for r in find_minimal_backdoor_sets(graph, claim.treatment, claim.outcome)
    ]
    gt = {
        "identifiable": true_identifiable,
        "minimal_adjustment_sets": [sorted(s) for s in mins],
        "proposed_set_valid": bd.valid,
    }

    intervention_info: Optional[dict] = None
    if scm is not None:
        analysis = scm.analyze_effect(claim.treatment, claim.outcome, treatment_value=1)
        intervention_info = analysis.to_dict()
        gt["ate"] = _frac(scm.ate(claim.treatment, claim.outcome))
        gt["p_do_1"] = _frac(scm.interventional_expectation(claim.outcome, {claim.treatment: 1}))
        if bd.valid:
            est = scm.backdoor_estimate(
                claim.treatment, claim.outcome, 1, claim.adjustment_set
            )
            if est is None:
                reasons.append("positivity failure for proposed adjustment set")
                return _verdict(
                    claim,
                    accepted=False,
                    verdict="positivity_failure",
                    reasons=tuple(reasons),
                    backdoor=bd.to_dict(),
                    intervention=intervention_info,
                    ground_truth=gt,
                )
            true_p = scm.interventional_expectation(
                claim.outcome, {claim.treatment: 1}
            )
            gt["backdoor_estimate"] = _frac(est)
            if est != true_p:
                # Should not happen if backdoor + positivity hold for this SCM class.
                reasons.append(
                    f"backdoor estimate {_frac(est)} ≠ interventional {_frac(true_p)}"
                )
                return _verdict(
                    claim,
                    accepted=False,
                    verdict="intervention_mismatch",
                    reasons=tuple(reasons),
                    backdoor=bd.to_dict(),
                    intervention=intervention_info,
                    ground_truth=gt,
                )

    # --- decision logic ---
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
                    intervention=intervention_info,
                    ground_truth=gt,
                )

    if claim.asserts_identifiable:
        if not true_identifiable:
            reasons.append("target is not identifiable; claim overreached")
            return _verdict(
                claim,
                accepted=False,
                verdict="not_identifiable",
                reasons=tuple(reasons) + bd.reasons,
                backdoor=bd.to_dict(),
                intervention=intervention_info,
                ground_truth=gt,
            )
        if not bd.valid:
            reasons.append("proposed adjustment set fails the backdoor criterion")
            return _verdict(
                claim,
                accepted=False,
                verdict="invalid_claim",
                reasons=tuple(reasons) + bd.reasons,
                backdoor=bd.to_dict(),
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
                    intervention=intervention_info,
                    ground_truth=gt,
                )
        reasons.append("identification certificate accepted under declared assumptions")
        return _verdict(
            claim,
            accepted=True,
            verdict="identified_under_assumptions",
            reasons=tuple(reasons),
            backdoor=bd.to_dict(),
            intervention=intervention_info,
            ground_truth=gt,
        )

    # Claim says not identifiable
    if true_identifiable:
        reasons.append("target is identifiable; claim incorrectly denied identification")
        return _verdict(
            claim,
            accepted=False,
            verdict="invalid_claim",
            reasons=tuple(reasons),
            backdoor=bd.to_dict(),
            intervention=intervention_info,
            ground_truth=gt,
        )
    reasons.append("correctly recognized non-identifiability")
    return _verdict(
        claim,
        accepted=True,
        verdict="not_identifiable",
        reasons=tuple(reasons) + bd.reasons,
        backdoor=bd.to_dict(),
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
    intervention: Optional[dict],
    ground_truth: dict,
) -> CertificateVerdict:
    assert verdict in ALLOWED_VERDICTS
    body = {
        "claim": claim.to_dict(),
        "accepted": accepted,
        "verdict": verdict,
        "reasons": list(reasons),
        "backdoor": backdoor,
        "intervention": intervention,
        "ground_truth": ground_truth,
        "assumptions": list(ASSUMPTIONS),
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
        intervention=intervention,
        ground_truth=ground_truth,
        claim=claim.to_dict(),
        assumptions=ASSUMPTIONS,
        certificate_sha256=digest,
        epistemic_ceiling="identified_under_assumptions_only",
    )


def _extract_json_object(text: str) -> Optional[dict]:
    text = text.strip()
    if not text:
        return None
    # Prefer fenced or raw JSON object.
    candidates: List[str] = []
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence:
        candidates.append(fence.group(1))
    # First balanced {...}
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
