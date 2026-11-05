"""Scientific adequacy challenge engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from ..core.statuses import AssuranceStatus, ClaimClass, status_record


@dataclass
class ChallengeResult:
    family: str
    outcome: str  # OBSERVED_FAILURE | UNKNOWN | PASS | SKIPPED
    detail: dict[str, Any]

    def to_status(self) -> dict[str, Any]:
        if self.outcome == "OBSERVED_FAILURE":
            st = AssuranceStatus.REFUTED
        elif self.outcome == "PASS":
            st = AssuranceStatus.COMPUTATIONALLY_TESTED
        elif self.outcome == "SKIPPED":
            st = AssuranceStatus.SKIPPED
        else:
            st = AssuranceStatus.OPEN
        return status_record(
            st,
            claim_class=ClaimClass.SCIENTIFIC_CLAIM,
            reason=f"{self.family}: {self.outcome}",
            limitations=[self.detail.get("note", "")],
            evidence_ids=list(self.detail.get("evidence_ids", [])),
        )


def challenge_unit_error(model: dict[str, Any]) -> ChallengeResult:
    clearance = model.get("clearance")
    unit = model.get("clearance_unit")
    if clearance is None:
        return ChallengeResult("unit_errors", "UNKNOWN", {"note": "no clearance field"})
    if unit not in {"L/h", "mL/min", "mL/h", "L/min", "1/h"}:
        return ChallengeResult(
            "unit_errors",
            "OBSERVED_FAILURE",
            {"note": f"unsupported or missing clearance unit: {unit!r}", "evidence_ids": ["model.clearance_unit"]},
        )
    if unit == "1/h" and model.get("volume_unit") not in {None, "L"}:
        return ChallengeResult(
            "unit_errors",
            "OBSERVED_FAILURE",
            {"note": "clearance unit 1/h inconsistent with volume-bearing PK parameterization"},
        )
    # Scale sanity: with volume in L (or volume_unit L), mL/min clearance of order ~1 with V~10 L
    # yields k = CL/V that is tiny vs typical L/h teaching examples — not a hard refute alone.
    # Pair with unit-aware prediction checks in adapters.units for numeric consistency.
    return ChallengeResult("unit_errors", "PASS", {"note": "units within supported fragment"})


def challenge_data_leakage(train_ids: list[str], test_ids: list[str]) -> ChallengeResult:
    overlap = sorted(set(train_ids) & set(test_ids))
    if overlap:
        return ChallengeResult(
            "data_leakage",
            "OBSERVED_FAILURE",
            {"note": f"train/test id overlap: {overlap[:10]}", "overlap_count": len(overlap)},
        )
    return ChallengeResult("data_leakage", "PASS", {"note": "no id overlap"})


def challenge_causal_overclaim(claim_text: str, evidence_kind: str) -> ChallengeResult:
    text = claim_text.lower()
    causal = any(w in text for w in ("causes", "causal", "because of treatment"))
    if causal and evidence_kind in {"association", "observational", "correlation"}:
        return ChallengeResult(
            "unsupported_causal_interpretation",
            "OBSERVED_FAILURE",
            {"note": "causal language with only associational evidence"},
        )
    if causal and evidence_kind == "unknown":
        return ChallengeResult("unsupported_causal_interpretation", "UNKNOWN", {"note": "evidence kind unknown"})
    return ChallengeResult("unsupported_causal_interpretation", "PASS", {"note": "no causal overclaim detected"})


def challenge_numerical_instability(values: list[float]) -> ChallengeResult:
    if not values:
        return ChallengeResult("numerical_instability", "UNKNOWN", {"note": "empty"})
    if any(v != v or v in (float("inf"), float("-inf")) for v in values):  # NaN/Inf
        return ChallengeResult("numerical_instability", "OBSERVED_FAILURE", {"note": "NaN/Inf present"})
    # simple relative jump check
    for a, b in zip(values, values[1:]):
        if a == 0:
            continue
        if abs(b - a) / abs(a) > 1e6:
            return ChallengeResult(
                "numerical_instability",
                "OBSERVED_FAILURE",
                {"note": "relative jump exceeds 1e6 between adjacent points"},
            )
    return ChallengeResult("numerical_instability", "PASS", {"note": "no extreme jumps in series"})


def challenge_wrong_assumption(model: dict[str, Any], required: list[str]) -> ChallengeResult:
    missing = [k for k in required if k not in model]
    if missing:
        return ChallengeResult(
            "incorrect_assumptions",
            "OBSERVED_FAILURE",
            {"note": f"missing required assumptions/fields: {missing}"},
        )
    return ChallengeResult("incorrect_assumptions", "PASS", {"note": "required fields present"})


DEFAULT_SUITE: list[tuple[str, Callable[..., ChallengeResult]]] = [
    ("unit_errors", challenge_unit_error),
    ("data_leakage", challenge_data_leakage),
    ("unsupported_causal_interpretation", challenge_causal_overclaim),
    ("numerical_instability", challenge_numerical_instability),
    ("incorrect_assumptions", challenge_wrong_assumption),
]


def run_pk_suite(model: dict[str, Any], predictions: list[float], claim_text: str) -> list[dict[str, Any]]:
    results = [
        challenge_unit_error(model).to_status(),
        challenge_wrong_assumption(model, ["clearance", "volume", "dose"]).to_status(),
        challenge_numerical_instability(predictions).to_status(),
        challenge_causal_overclaim(claim_text, model.get("evidence_kind", "unknown")).to_status(),
    ]
    return results


def negative_result_report(results: list[dict[str, Any]]) -> dict[str, Any]:
    refuted = [r for r in results if r["status"] == AssuranceStatus.REFUTED.value]
    return {
        "format": "pcs-next-negative-result-v1",
        "refuted_count": len(refuted),
        "refuted": refuted,
        "note": "PCS values informative rejection; acceptance rate is not an optimization target.",
    }
