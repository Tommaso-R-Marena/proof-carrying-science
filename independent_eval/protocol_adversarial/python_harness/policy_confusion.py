"""Reviewer policy confusion scenarios on the same signed evidence."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from .paths import REPO_ROOT, RESULTS


def run_policy_confusion(work: Path) -> dict[str, Any]:
    from pcs.attest_v06 import attest_v06
    from pcs.discover_v06 import confirm_manifest_draft_v06, discover_project_v06, write_discovery_outputs_v06
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    import hashlib
    from pcs.signing import public_key_fingerprint
    from pcs.verifier_zip_v06 import verify_package_zip_end_to_end_v06

    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    lab = work / "lab"
    lab.mkdir()
    src = REPO_ROOT / "examples" / "pkpd_one_compartment"
    for name in ("pk_model.json", "predictions.csv", "pilot_intake.json"):
        shutil.copyfile(src / name, lab / name)
    discovered = discover_project_v06(lab)
    draft = lab / "draft.json"
    write_discovery_outputs_v06(
        discovered, manifest_output=draft, report_output=lab / "discovery.json", overwrite=True
    )
    manifest = lab / "manifest.json"
    confirm_manifest_draft_v06(draft, manifest, project_root=lab, overwrite=True)

    private = Ed25519PrivateKey.from_private_bytes(
        hashlib.sha256(b"pcs-independent-eval-policy-v1").digest()
    )
    public = private.public_key()
    priv = work / "private.pem"
    pub = work / "public.pem"
    priv.write_bytes(
        private.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    pub.write_bytes(
        public.public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    fingerprint = public_key_fingerprint(public)
    authority = REPO_ROOT / "formal" / ".lake" / "build" / "bin" / "pcs-lean-authority"
    bundle = work / "study.pcs.zip"
    attest_v06(
        manifest,
        bundle,
        priv,
        pub,
        expected_fingerprint=fingerprint,
        overwrite=True,
        lean_authority_path=authority if authority.is_file() else None,
    )

    # Two reviewer policies: strict vs permissive placeholders
    strict_policy = {
        "policy_format": "pcs-independent-eval-reviewer-policy-v1",
        "policy_id": "strict-scientific-limits",
        "require_authoritative": True,
        "allow_empirical_overclaim": False,
        "notes": "Computational PASS must not be read as empirical adequacy.",
    }
    permissive_policy = {
        "policy_format": "pcs-independent-eval-reviewer-policy-v1",
        "policy_id": "permissive-accept-all-computational",
        "require_authoritative": True,
        "allow_empirical_overclaim": True,
        "notes": "Dangerous if confused with scientific acceptance.",
    }
    (work / "policy_strict.json").write_text(json.dumps(strict_policy, indent=2) + "\n")
    (work / "policy_permissive.json").write_text(json.dumps(permissive_policy, indent=2) + "\n")

    base = verify_package_zip_end_to_end_v06(
        bundle,
        pub,
        expected_fingerprint=fingerprint,
        lean_authority_path=authority if authority.is_file() else None,
        require_canonical_archive=True,
    )

    # Apply policies as post-hoc overlays (does not change PCS validity)
    def apply_policy(receipt: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
        scientific_acceptance = False
        if policy.get("allow_empirical_overclaim") and receipt.get("valid"):
            # Confusion trap: a buggy consumer might do this — we record it as unsafe.
            scientific_acceptance = True
        return {
            "pcs_valid": receipt.get("valid"),
            "pcs_authoritative": receipt.get("authoritative"),
            "policy_id": policy["policy_id"],
            "unsafe_scientific_acceptance_inference": scientific_acceptance,
            "correct_interpretation": (
                "PCS validity is computational/formal relative to declared claims; "
                "empirical/scientific acceptance remains OPEN unless independently established."
            ),
        }

    report = {
        "format": "pcs-independent-policy-confusion-v1",
        "bundle_sha256": base.get("bundle_sha256"),
        "pcs_valid": base.get("valid"),
        "pcs_authoritative": base.get("authoritative"),
        "reviewers": [
            apply_policy(base, strict_policy),
            apply_policy(base, permissive_policy),
        ],
        "findings": [
            "Same signed evidence yields identical PCS validity for both reviewers.",
            "Permissive policy can dangerously confuse computational PASS with scientific acceptance if consumers misuse policy flags.",
            "PCS validity must not silently become broader scientific acceptance.",
        ],
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "policy_confusion.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report
