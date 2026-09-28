from __future__ import annotations

import json
from pathlib import Path

POLICY_VERSION = "pcs-acceptance-policy-v1"


class PolicyError(ValueError):
    pass


def validate_policy(policy: dict) -> dict:
    if not isinstance(policy, dict):
        raise PolicyError("acceptance policy must be a JSON object")
    if policy.get("policy_version") != POLICY_VERSION:
        raise PolicyError("unsupported acceptance policy version")
    required = policy.get("required_claims")
    if not isinstance(required, dict) or not required:
        raise PolicyError("acceptance policy requires a non-empty required_claims object")
    for cid, statuses in required.items():
        if not isinstance(cid, str) or not cid:
            raise PolicyError("acceptance policy contains invalid claim id")
        if not isinstance(statuses, list) or not statuses or not all(isinstance(x, str) and x for x in statuses):
            raise PolicyError(f"acceptance policy claim {cid} requires a non-empty status list")
    fp = policy.get("expected_signer_fingerprint")
    if fp is not None and (not isinstance(fp, str) or len(fp) != 64):
        raise PolicyError("expected_signer_fingerprint must be a 64-character SHA-256 hex string")
    return policy


def load_policy(path: str | Path) -> dict:
    return validate_policy(json.loads(Path(path).read_text(encoding="utf-8")))


def evaluate_policy(certificate: dict, policy: dict, *, signature_valid: bool | None = None, signer_fingerprint: str | None = None) -> dict:
    statuses = {c.get("id"): c.get("assessment", {}).get("status") for c in certificate.get("claims", [])}
    failures: list[dict[str, object]] = []
    for cid, allowed in policy["required_claims"].items():
        actual = statuses.get(cid, "MISSING")
        if actual not in allowed:
            failures.append({"type": "claim_status", "claim_id": cid, "actual": actual, "allowed": allowed})
    require_signature = bool(policy.get("require_signature", False))
    if require_signature and signature_valid is not True:
        failures.append({"type": "signature", "reason": "valid package signature required"})
    expected = policy.get("expected_signer_fingerprint")
    if expected is not None:
        if signer_fingerprint is None or signer_fingerprint.lower() != expected.lower():
            failures.append({"type": "signer", "reason": "signer fingerprint does not match policy", "expected": expected, "actual": signer_fingerprint})
    return {"pass": not failures, "failures": failures, "required_claims": policy["required_claims"]}


def evaluate_policy_file(certificate: dict, policy_path: str | Path, **kwargs) -> dict:
    return evaluate_policy(certificate, load_policy(policy_path), **kwargs)
