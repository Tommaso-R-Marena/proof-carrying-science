"""Second-environment reviewer workflow."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..core.canonical import canonical_hash, canonicalize, loads_strict
from ..core.errors import ErrorCode, PcsNextError
from ..core.statuses import AssuranceStatus
from ..pilot.intake import verify_lock_integrity
from ..trust.crypto import require_pinned_signer, verify_bytes
from ..trust.policy import AcceptancePolicy, pin_policy, reject_producer_verdict, verify_policy_binding


def load_package(dir_path: str | Path) -> dict[str, Any]:
    root = Path(dir_path)
    required = ["intake.lock.json", "evidence_bundle.json", "acceptance_policy.json"]
    missing = [n for n in required if not (root / n).is_file()]
    if missing:
        raise PcsNextError(ErrorCode.ADVERSARIAL_PACKAGE, f"missing package members: {missing}")
    lock = loads_strict((root / "intake.lock.json").read_bytes())
    bundle = loads_strict((root / "evidence_bundle.json").read_bytes())
    policy_raw = loads_strict((root / "acceptance_policy.json").read_bytes())
    if not all(isinstance(x, dict) for x in (lock, bundle, policy_raw)):
        raise PcsNextError(ErrorCode.ADVERSARIAL_PACKAGE, "package members must be objects")
    return {"lock": lock, "bundle": bundle, "policy_raw": policy_raw, "root": root}


def review_package(
    dir_path: str | Path,
    *,
    receiver_policy: dict[str, Any] | AcceptancePolicy | None = None,
    signed: dict[str, Any] | None = None,
) -> dict[str, Any]:
    pkg = load_package(dir_path)
    policy = (
        receiver_policy
        if isinstance(receiver_policy, AcceptancePolicy)
        else pin_policy(receiver_policy or pkg["policy_raw"])
    )
    # Receiver policy must match pinned file if both provided
    if receiver_policy is None:
        pass
    else:
        file_policy = pin_policy(pkg["policy_raw"])
        if file_policy.content_hash != policy.content_hash:
            raise PcsNextError(ErrorCode.POLICY_SUBSTITUTION, "package policy differs from receiver pin")

    verify_lock_integrity(pkg["lock"])
    verify_policy_binding(
        receiver_policy=policy,
        claimed_policy=pkg["lock"].get("acceptance_policy"),
        claimed_policy_hash=pkg["lock"].get("acceptance_policy_hash"),
    )
    bundle = pkg["bundle"]
    if bundle.get("producer_claimed_pass") is not None:
        ignored = reject_producer_verdict(bundle.get("producer_claimed_pass"))
    else:
        ignored = reject_producer_verdict(None)

    if bundle.get("lock_hash") != canonical_hash(pkg["lock"]):
        raise PcsNextError(ErrorCode.HASH_MISMATCH, "bundle/lock hash mismatch")
    if bundle.get("policy_hash") != policy.content_hash:
        raise PcsNextError(ErrorCode.POLICY_SUBSTITUTION, "bundle policy hash mismatch")

    if signed is not None:
        pub = bytes.fromhex(signed["public_der_hex"])
        sig = bytes.fromhex(signed["signature_hex"])
        msg = canonicalize({"lock_hash": canonical_hash(pkg["lock"]), "bundle_hash": canonical_hash(bundle)})
        require_pinned_signer(pub, policy.pinned_signer_fingerprints)
        verify_bytes(pub, msg, sig)

    receipt = {
        "format": "pcs-next-independent-receipt-v1",
        "receiver_policy_hash": policy.content_hash,
        "lock_hash": canonical_hash(pkg["lock"]),
        "bundle_hash": canonical_hash(bundle),
        "producer_verdict_handling": ignored,
        "status": AssuranceStatus.INDEPENDENTLY_REPRODUCED.value,
        "package_root": str(pkg["root"]),
        "limitations": [
            "Synthetic or second-process independence only unless an external lab ran this.",
        ],
    }
    out = Path(dir_path) / "reviewer_receipt.json"
    out.write_bytes(canonicalize(receipt) + b"\n")
    return receipt
