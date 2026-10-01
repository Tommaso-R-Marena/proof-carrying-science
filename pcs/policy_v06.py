from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from .policy import PolicyError, load_policy, validate_policy


class V06ReviewerPolicyError(ValueError):
    pass


def evaluate_verification_policy_v06(
    verification: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    """Evaluate external reviewer acceptance over a v0.6 verification result.

    Package/replay validity and reviewer acceptance are intentionally separate.
    A valid PCS package may fail reviewer policy because a claim was falsified,
    remains open, or does not meet the reviewer's required assurance class.
    """
    try:
        checked_policy = validate_policy(policy)
    except PolicyError as exc:
        raise V06ReviewerPolicyError(str(exc)) from exc

    failures: list[dict[str, Any]] = []
    if verification.get("valid") is not True:
        failures.append(
            {
                "type": "package_verification",
                "reason": "reviewer policy cannot accept a package that failed PCS verification",
                "failed_stage": verification.get("failed_stage"),
            }
        )

    claims = verification.get("claims")
    if not isinstance(claims, list):
        claims = []
    statuses = {
        claim.get("claim_id"): claim.get("decision")
        for claim in claims
        if isinstance(claim, dict) and isinstance(claim.get("claim_id"), str)
    }

    for claim_id, allowed in checked_policy["required_claims"].items():
        actual = statuses.get(claim_id, "MISSING")
        if actual not in allowed:
            failures.append(
                {
                    "type": "claim_status",
                    "claim_id": claim_id,
                    "actual": actual,
                    "allowed": list(allowed),
                }
            )

    require_signature = bool(checked_policy.get("require_signature", False))
    signer = verification.get("public_key_fingerprint")
    if require_signature and verification.get("valid") is not True:
        failures.append(
            {
                "type": "signature",
                "reason": "valid signed package verification required",
            }
        )

    expected = checked_policy.get("expected_signer_fingerprint")
    if expected is not None:
        if not isinstance(signer, str) or signer.lower() != expected.lower():
            failures.append(
                {
                    "type": "signer",
                    "reason": "signer fingerprint does not match reviewer policy",
                    "expected": expected,
                    "actual": signer,
                }
            )

    return {
        "policy_version": checked_policy["policy_version"],
        "pass": not failures,
        "required_claims": checked_policy["required_claims"],
        "require_signature": require_signature,
        "expected_signer_fingerprint": expected,
        "failures": failures,
    }


def evaluate_verification_policy_file_v06(
    verification: dict[str, Any],
    path: str | Path,
) -> dict[str, Any]:
    policy_path = Path(path)
    try:
        raw = policy_path.read_bytes()
        policy = load_policy(policy_path)
    except (OSError, PolicyError) as exc:
        raise V06ReviewerPolicyError(
            f"cannot load reviewer policy: {type(exc).__name__}: {exc}"
        ) from exc

    result = evaluate_verification_policy_v06(verification, policy)
    result["policy_sha256"] = hashlib.sha256(raw).hexdigest()
    return result


def apply_reviewer_policy_v06(
    verification: dict[str, Any],
    policy_path: str | Path | None,
) -> dict[str, Any]:
    """Attach acceptance state without mutating the underlying PCS validity."""
    out = dict(verification)
    if policy_path is None:
        out["accepted"] = bool(out.get("valid"))
        out["reviewer_policy"] = {
            "applied": False,
            "pass": None,
            "policy_sha256": None,
            "failures": [],
        }
        return out

    policy = evaluate_verification_policy_file_v06(out, policy_path)
    out["accepted"] = bool(out.get("valid") and policy["pass"])
    out["reviewer_policy"] = {
        "applied": True,
        **policy,
    }
    return out
