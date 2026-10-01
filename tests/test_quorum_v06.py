from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from pcs.quorum_v06 import verify_review_quorum_v06
from pcs.receipt_signature_v06 import sign_verification_receipt_v06
from pcs.signing import public_key_fingerprint


ROOT = Path(__file__).resolve().parents[1]
SUBJECT_A = {
    "bundle_sha256": "a" * 64,
    "certificate_semantic_hash": "b" * 64,
    "certificate_integrity_hash": "c" * 64,
    "normalized_index_semantic_hash": "d" * 64,
}
SUBJECT_B = {
    "bundle_sha256": "1" * 64,
    "certificate_semantic_hash": "2" * 64,
    "certificate_integrity_hash": "3" * 64,
    "normalized_index_semantic_hash": "4" * 64,
}
POLICY_COMP = "e" * 64
POLICY_DOMAIN = "f" * 64
POLICY_STATS = "0" * 64


def _keypair(tmp_path: Path, name: str, byte: int) -> tuple[Path, Path, str]:
    private = Ed25519PrivateKey.from_private_bytes(bytes([byte]) * 32)
    public = private.public_key()
    private_path = tmp_path / f"{name}.private.pem"
    public_path = tmp_path / f"{name}.public.pem"
    private_path.write_bytes(
        private.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    public_path.write_bytes(
        public.public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    return private_path, public_path, public_key_fingerprint(public)


def _review(
    root: Path,
    name: str,
    private_key: Path,
    public_key: Path,
    *,
    policy_sha256: str,
    subject: dict[str, str] = SUBJECT_A,
    accepted: bool = True,
    valid: bool = True,
) -> dict[str, str]:
    receipt = root / f"{name}.receipt.json"
    signature = root / f"{name}.receipt.sig.json"
    receipt_obj = {
        "format": "pcs-end-to-end-verifier-v06-v1",
        "valid": valid,
        "accepted": accepted,
        **subject,
        "reviewer_policy": {
            "applied": True,
            "pass": accepted,
            "policy_sha256": policy_sha256,
            "failures": [] if accepted else [{"type": "claim_status"}],
        },
    }
    receipt.write_text(
        json.dumps(receipt_obj, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    sign_verification_receipt_v06(
        receipt,
        private_key,
        signature,
    )
    return {
        "receipt": receipt.name,
        "signature": signature.name,
        "public_key": public_key.name,
    }


def _write_review_set(root: Path, reviews: list[dict[str, str]]) -> Path:
    path = root / "review-set.json"
    path.write_text(
        json.dumps(
            {"format": "pcs-review-set-v1", "reviews": reviews},
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def _write_policy(
    root: Path,
    reviewers: list[dict],
    *,
    min_accepted: int = 2,
    required_roles: dict[str, int] | None = None,
    expected_bundle_sha256: str | None = SUBJECT_A["bundle_sha256"],
) -> Path:
    value = {
        "policy_version": "pcs-review-quorum-policy-v1",
        "min_accepted_reviews": min_accepted,
        "required_roles": required_roles or {
            "computational": 1,
            "domain": 1,
        },
        "reviewers": reviewers,
    }
    if expected_bundle_sha256 is not None:
        value["expected_bundle_sha256"] = expected_bundle_sha256
    path = root / "quorum-policy.json"
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "pcs.cli", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_two_of_three_quorum_requires_computational_and_domain_roles(tmp_path):
    comp_priv, comp_pub, comp_fp = _keypair(tmp_path, "comp", 11)
    domain_priv, domain_pub, domain_fp = _keypair(tmp_path, "domain", 12)
    stats_priv, stats_pub, stats_fp = _keypair(tmp_path, "stats", 13)

    reviews = [
        _review(
            tmp_path,
            "comp",
            comp_priv,
            comp_pub,
            policy_sha256=POLICY_COMP,
        ),
        _review(
            tmp_path,
            "domain",
            domain_priv,
            domain_pub,
            policy_sha256=POLICY_DOMAIN,
        ),
        _review(
            tmp_path,
            "stats",
            stats_priv,
            stats_pub,
            policy_sha256=POLICY_STATS,
            accepted=False,
        ),
    ]
    review_set = _write_review_set(tmp_path, reviews)
    policy = _write_policy(
        tmp_path,
        [
            {
                "fingerprint": comp_fp,
                "role": "computational",
                "required_policy_sha256": POLICY_COMP,
            },
            {
                "fingerprint": domain_fp,
                "role": "domain",
                "required_policy_sha256": POLICY_DOMAIN,
            },
            {
                "fingerprint": stats_fp,
                "role": "statistical",
                "required_policy_sha256": POLICY_STATS,
            },
        ],
    )

    result = verify_review_quorum_v06(policy, review_set)

    assert result["pass"] is True
    assert result["selected_subject"] == SUBJECT_A
    assert result["accepted_review_count"] == 2
    assert result["role_counts"] == {
        "computational": 1,
        "domain": 1,
    }
    assert result["failures"] == []


def test_two_reviews_do_not_pass_when_required_domain_role_is_missing(tmp_path):
    comp1_priv, comp1_pub, comp1_fp = _keypair(tmp_path, "comp1", 21)
    comp2_priv, comp2_pub, comp2_fp = _keypair(tmp_path, "comp2", 22)
    domain_priv, domain_pub, domain_fp = _keypair(tmp_path, "domain", 23)

    reviews = [
        _review(tmp_path, "comp1", comp1_priv, comp1_pub, policy_sha256=POLICY_COMP),
        _review(tmp_path, "comp2", comp2_priv, comp2_pub, policy_sha256=POLICY_COMP),
        _review(
            tmp_path,
            "domain",
            domain_priv,
            domain_pub,
            policy_sha256=POLICY_DOMAIN,
            accepted=False,
        ),
    ]
    review_set = _write_review_set(tmp_path, reviews)
    policy = _write_policy(
        tmp_path,
        [
            {"fingerprint": comp1_fp, "role": "computational", "required_policy_sha256": POLICY_COMP},
            {"fingerprint": comp2_fp, "role": "computational", "required_policy_sha256": POLICY_COMP},
            {"fingerprint": domain_fp, "role": "domain", "required_policy_sha256": POLICY_DOMAIN},
        ],
    )

    result = verify_review_quorum_v06(policy, review_set)

    assert result["pass"] is False
    assert result["selected_subject"] is None
    assert result["failures"][0]["type"] == "quorum_not_met"
    group = result["subject_groups"][0]
    assert group["accepted_review_count"] == 2
    assert group["threshold_met"] is True
    assert group["role_failures"]["domain"] == {"required": 1, "actual": 0}


def test_role_specific_policy_hash_is_enforced(tmp_path):
    comp_priv, comp_pub, comp_fp = _keypair(tmp_path, "comp", 31)
    domain_priv, domain_pub, domain_fp = _keypair(tmp_path, "domain", 32)

    reviews = [
        _review(tmp_path, "comp", comp_priv, comp_pub, policy_sha256=POLICY_COMP),
        _review(
            tmp_path,
            "domain",
            domain_priv,
            domain_pub,
            policy_sha256=POLICY_COMP,  # wrong policy for domain role
        ),
    ]
    review_set = _write_review_set(tmp_path, reviews)
    policy = _write_policy(
        tmp_path,
        [
            {"fingerprint": comp_fp, "role": "computational", "required_policy_sha256": POLICY_COMP},
            {"fingerprint": domain_fp, "role": "domain", "required_policy_sha256": POLICY_DOMAIN},
        ],
    )

    result = verify_review_quorum_v06(policy, review_set)

    assert result["pass"] is False
    domain = next(x for x in result["reviews"] if x["role"] == "domain")
    assert "reviewer_policy_hash_mismatch" in domain["reasons"]


def test_reviews_of_different_bundles_can_never_be_combined_into_quorum(tmp_path):
    comp_priv, comp_pub, comp_fp = _keypair(tmp_path, "comp", 41)
    domain_priv, domain_pub, domain_fp = _keypair(tmp_path, "domain", 42)
    stats_priv, stats_pub, stats_fp = _keypair(tmp_path, "stats", 43)

    reviews = [
        _review(
            tmp_path,
            "comp-a",
            comp_priv,
            comp_pub,
            policy_sha256=POLICY_COMP,
            subject=SUBJECT_A,
        ),
        _review(
            tmp_path,
            "domain-b",
            domain_priv,
            domain_pub,
            policy_sha256=POLICY_DOMAIN,
            subject=SUBJECT_B,
        ),
        _review(
            tmp_path,
            "stats-a",
            stats_priv,
            stats_pub,
            policy_sha256=POLICY_STATS,
            subject=SUBJECT_A,
        ),
    ]
    review_set = _write_review_set(tmp_path, reviews)
    policy = _write_policy(
        tmp_path,
        [
            {"fingerprint": comp_fp, "role": "computational", "required_policy_sha256": POLICY_COMP},
            {"fingerprint": domain_fp, "role": "domain", "required_policy_sha256": POLICY_DOMAIN},
            {"fingerprint": stats_fp, "role": "statistical", "required_policy_sha256": POLICY_STATS},
        ],
        expected_bundle_sha256=None,
    )

    result = verify_review_quorum_v06(policy, review_set)

    assert result["pass"] is False
    assert len(result["subject_groups"]) == 2
    assert result["failures"][0]["type"] == "quorum_not_met"


def test_duplicate_reviewer_identity_cannot_count_twice(tmp_path):
    private, public, fingerprint = _keypair(tmp_path, "same", 51)
    domain_priv, domain_pub, domain_fp = _keypair(tmp_path, "domain", 52)

    first = _review(tmp_path, "same-1", private, public, policy_sha256=POLICY_COMP)
    second = _review(tmp_path, "same-2", private, public, policy_sha256=POLICY_COMP)
    domain = _review(
        tmp_path,
        "domain",
        domain_priv,
        domain_pub,
        policy_sha256=POLICY_DOMAIN,
        accepted=False,
    )
    review_set = _write_review_set(tmp_path, [first, second, domain])
    policy = _write_policy(
        tmp_path,
        [
            {"fingerprint": fingerprint, "role": "computational", "required_policy_sha256": POLICY_COMP},
            {"fingerprint": domain_fp, "role": "domain", "required_policy_sha256": POLICY_DOMAIN},
        ],
        min_accepted=2,
    )

    result = verify_review_quorum_v06(policy, review_set)

    assert result["pass"] is False
    duplicates = [
        x for x in result["reviews"]
        if x["reviewer_public_key_fingerprint"] == fingerprint
    ]
    assert len(duplicates) == 2
    assert all("duplicate_reviewer_identity" in x["reasons"] for x in duplicates)


def test_verify_quorum_cli_writes_auditable_result(tmp_path):
    comp_priv, comp_pub, comp_fp = _keypair(tmp_path, "comp", 61)
    domain_priv, domain_pub, domain_fp = _keypair(tmp_path, "domain", 62)
    reviews = [
        _review(tmp_path, "comp", comp_priv, comp_pub, policy_sha256=POLICY_COMP),
        _review(tmp_path, "domain", domain_priv, domain_pub, policy_sha256=POLICY_DOMAIN),
    ]
    review_set = _write_review_set(tmp_path, reviews)
    policy = _write_policy(
        tmp_path,
        [
            {"fingerprint": comp_fp, "role": "computational", "required_policy_sha256": POLICY_COMP},
            {"fingerprint": domain_fp, "role": "domain", "required_policy_sha256": POLICY_DOMAIN},
        ],
    )
    output = tmp_path / "quorum-result.json"

    proc = _run(
        "verify-quorum-v06",
        "--quorum-policy",
        str(policy),
        "--review-set",
        str(review_set),
        "-o",
        str(output),
    )

    assert proc.returncode == 0, proc.stdout + proc.stderr
    cli_result = json.loads(proc.stdout)
    saved = json.loads(output.read_text(encoding="utf-8"))
    assert cli_result["pass"] is True
    assert saved["pass"] is True
    assert saved["selected_subject"] == SUBJECT_A
    assert cli_result["result_written"] == str(output.resolve())
