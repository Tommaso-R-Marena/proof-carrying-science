from __future__ import annotations
from typing import Any, Mapping

FORMAL = "FORMALLY_VERIFIED_UNDER_ASSUMPTIONS"
COMPUTATIONAL = "COMPUTATIONALLY_SUPPORTED"
EMPIRICAL = "EMPIRICALLY_VALIDATED_WITHIN_SCOPE"
MIXED = "MIXED_SUPPORT_UNDER_ASSUMPTIONS"
OPEN = "OPEN"
FAILED = "FALSIFIED_OR_CHECK_FAILED"


def assess_claim(claim: Mapping[str, Any], evidence_map: Mapping[str, Mapping[str, Any]]) -> dict[str, str]:
    """Pure claim assessment after evidence has been independently established."""
    required_ids = list(claim.get("required_evidence", []))
    required = [evidence_map[eid] for eid in required_ids if eid in evidence_map]
    if len(required) != len(required_ids):
        return {"status": OPEN, "reason": "required evidence missing"}
    if any(e.get("outcome") == "FAIL" for e in required):
        return {"status": FAILED, "reason": "at least one required check failed"}
    if any(e.get("outcome") == "UNVERIFIED" for e in required):
        return {"status": OPEN, "reason": "at least one required evidence object is not independently verified"}
    if not required:
        return {"status": OPEN, "reason": "no evidence supplied"}

    kind = claim.get("kind", "computational")
    kinds = {e.get("kind") for e in required}
    if kind == "formal":
        if kinds <= {"formal_proof"} and all(e.get("outcome") == "PASS" for e in required):
            return {"status": FORMAL, "reason": "all declared formal obligations independently accepted"}
        return {"status": OPEN, "reason": "formal claim lacks independently accepted formal evidence"}
    if kind == "empirical":
        if kinds & {"empirical_validation", "statistical_validation"}:
            return {"status": EMPIRICAL, "reason": "declared empirical/statistical evidence passed"}
        return {"status": OPEN, "reason": "empirical claim lacks empirical/statistical evidence"}
    if kind == "mixed":
        if ("formal_proof" in kinds) and (kinds & {"empirical_validation", "statistical_validation"}):
            return {"status": MIXED, "reason": "formal and empirical evidence classes present"}
        return {"status": OPEN, "reason": "mixed claim still lacks formal or empirical evidence class"}
    if kinds & {"computational_test", "formal_proof"}:
        return {"status": COMPUTATIONAL, "reason": "all declared computational checks passed"}
    return {"status": OPEN, "reason": "computational claim lacks computational/formal correctness evidence"}
