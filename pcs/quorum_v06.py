from __future__ import annotations

import hashlib
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .jsonio import StrictJSONError, strict_json_load
from .receipt_signature_v06 import verify_verification_receipt_signature_v06


QUORUM_POLICY_FORMAT_V06 = "pcs-review-quorum-policy-v1"
REVIEW_SET_FORMAT_V06 = "pcs-review-set-v1"
QUORUM_RESULT_FORMAT_V06 = "pcs-review-quorum-result-v1"

_HEX64 = re.compile(r"^[a-f0-9]{64}$")
_ROLE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}$")


class V06ReviewQuorumError(ValueError):
    pass


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _load_object(path: str | Path, *, label: str) -> tuple[Path, bytes, dict[str, Any]]:
    p = Path(path).resolve()
    try:
        raw = p.read_bytes()
        obj = strict_json_load(p)
    except (OSError, StrictJSONError) as exc:
        raise V06ReviewQuorumError(
            f"cannot load {label}: {type(exc).__name__}: {exc}"
        ) from exc
    if not isinstance(obj, dict):
        raise V06ReviewQuorumError(f"{label} root must be an object")
    return p, raw, obj


def _validate_quorum_policy(policy: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "policy_version",
        "min_accepted_reviews",
        "required_roles",
        "expected_bundle_sha256",
        "reviewers",
    }
    extra = sorted(set(policy) - allowed)
    if extra:
        raise V06ReviewQuorumError(f"quorum policy has unknown fields: {extra}")
    if policy.get("policy_version") != QUORUM_POLICY_FORMAT_V06:
        raise V06ReviewQuorumError(
            f"unsupported quorum policy version: {policy.get('policy_version')!r}"
        )

    min_reviews = policy.get("min_accepted_reviews")
    if not isinstance(min_reviews, int) or isinstance(min_reviews, bool) or min_reviews < 1:
        raise V06ReviewQuorumError("min_accepted_reviews must be a positive integer")

    required_roles = policy.get("required_roles", {})
    if not isinstance(required_roles, dict):
        raise V06ReviewQuorumError("required_roles must be an object")
    checked_roles: dict[str, int] = {}
    for role, count in required_roles.items():
        if not isinstance(role, str) or not _ROLE.fullmatch(role):
            raise V06ReviewQuorumError(f"invalid required role: {role!r}")
        if not isinstance(count, int) or isinstance(count, bool) or count < 1:
            raise V06ReviewQuorumError(
                f"required role count for {role!r} must be a positive integer"
            )
        checked_roles[role] = count

    expected_bundle = policy.get("expected_bundle_sha256")
    if expected_bundle is not None:
        if not isinstance(expected_bundle, str) or not _HEX64.fullmatch(expected_bundle):
            raise V06ReviewQuorumError(
                "expected_bundle_sha256 must be lowercase 64-hex when present"
            )

    reviewers = policy.get("reviewers")
    if not isinstance(reviewers, list) or not reviewers:
        raise V06ReviewQuorumError("reviewers must be a non-empty array")
    checked_reviewers: list[dict[str, Any]] = []
    seen: set[str] = set()
    for reviewer in reviewers:
        if not isinstance(reviewer, dict):
            raise V06ReviewQuorumError("reviewer entries must be objects")
        reviewer_extra = sorted(
            set(reviewer) - {"fingerprint", "role", "required_policy_sha256"}
        )
        if reviewer_extra:
            raise V06ReviewQuorumError(
                f"reviewer entry has unknown fields: {reviewer_extra}"
            )
        fingerprint = reviewer.get("fingerprint")
        role = reviewer.get("role")
        required_policy = reviewer.get("required_policy_sha256")
        if not isinstance(fingerprint, str) or not _HEX64.fullmatch(fingerprint):
            raise V06ReviewQuorumError(
                f"reviewer fingerprint must be lowercase 64-hex: {fingerprint!r}"
            )
        if fingerprint in seen:
            raise V06ReviewQuorumError(
                f"duplicate reviewer fingerprint in quorum policy: {fingerprint}"
            )
        seen.add(fingerprint)
        if not isinstance(role, str) or not _ROLE.fullmatch(role):
            raise V06ReviewQuorumError(f"invalid reviewer role: {role!r}")
        if required_policy is not None and (
            not isinstance(required_policy, str) or not _HEX64.fullmatch(required_policy)
        ):
            raise V06ReviewQuorumError(
                "required_policy_sha256 must be lowercase 64-hex when present"
            )
        checked_reviewers.append(
            {
                "fingerprint": fingerprint,
                "role": role,
                "required_policy_sha256": required_policy,
            }
        )

    if min_reviews > len(checked_reviewers):
        raise V06ReviewQuorumError(
            "min_accepted_reviews exceeds number of authorized reviewers"
        )

    available_by_role = Counter(x["role"] for x in checked_reviewers)
    for role, count in checked_roles.items():
        if available_by_role[role] < count:
            raise V06ReviewQuorumError(
                f"required role {role!r} needs {count} reviewer(s), "
                f"but policy authorizes only {available_by_role[role]}"
            )

    return {
        "policy_version": QUORUM_POLICY_FORMAT_V06,
        "min_accepted_reviews": min_reviews,
        "required_roles": checked_roles,
        "expected_bundle_sha256": expected_bundle,
        "reviewers": checked_reviewers,
    }


def _validate_review_set(review_set: dict[str, Any]) -> list[dict[str, str]]:
    allowed = {"format", "reviews"}
    extra = sorted(set(review_set) - allowed)
    if extra:
        raise V06ReviewQuorumError(f"review set has unknown fields: {extra}")
    if review_set.get("format") != REVIEW_SET_FORMAT_V06:
        raise V06ReviewQuorumError(
            f"unsupported review-set format: {review_set.get('format')!r}"
        )
    reviews = review_set.get("reviews")
    if not isinstance(reviews, list) or not reviews:
        raise V06ReviewQuorumError("review set must contain at least one review")
    if len(reviews) > 256:
        raise V06ReviewQuorumError("review set exceeds 256-review limit")

    checked: list[dict[str, str]] = []
    for item in reviews:
        if not isinstance(item, dict):
            raise V06ReviewQuorumError("review-set entries must be objects")
        if set(item) != {"receipt", "signature", "public_key"}:
            raise V06ReviewQuorumError(
                "each review-set entry must contain exactly receipt, signature, public_key"
            )
        if not all(isinstance(item[k], str) and item[k] for k in item):
            raise V06ReviewQuorumError("review-set paths must be non-empty strings")
        checked.append(dict(item))
    return checked


def _portable_member(root: Path, relative: str, *, label: str) -> Path:
    candidate_literal = root / relative
    if candidate_literal.is_symlink():
        raise V06ReviewQuorumError(f"{label} must not be a symlink: {relative!r}")
    candidate = candidate_literal.resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise V06ReviewQuorumError(
            f"{label} escapes review-set directory: {relative!r}"
        ) from exc
    if not candidate.is_file():
        raise V06ReviewQuorumError(f"{label} is not a regular file: {relative!r}")
    return candidate


def _subject_key(review: dict[str, Any]) -> tuple[str, str, str, str] | None:
    values = (
        review.get("bundle_sha256"),
        review.get("certificate_semantic_hash"),
        review.get("certificate_integrity_hash"),
        review.get("normalized_index_semantic_hash"),
    )
    if not all(isinstance(x, str) and _HEX64.fullmatch(x) for x in values):
        return None
    return values  # type: ignore[return-value]


def verify_review_quorum_v06(
    quorum_policy_path: str | Path,
    review_set_path: str | Path,
) -> dict[str, Any]:
    policy_file, policy_raw, policy_obj = _load_object(
        quorum_policy_path,
        label="quorum policy",
    )
    review_set_file, review_set_raw, review_set_obj = _load_object(
        review_set_path,
        label="review set",
    )
    policy = _validate_quorum_policy(policy_obj)
    reviews = _validate_review_set(review_set_obj)

    review_root = review_set_file.parent
    authorized = {r["fingerprint"]: r for r in policy["reviewers"]}

    evaluated: list[dict[str, Any]] = []
    fingerprint_counts: Counter[str] = Counter()

    for index, item in enumerate(reviews):
        receipt = _portable_member(
            review_root,
            item["receipt"],
            label=f"review[{index}].receipt",
        )
        signature = _portable_member(
            review_root,
            item["signature"],
            label=f"review[{index}].signature",
        )
        public_key = _portable_member(
            review_root,
            item["public_key"],
            label=f"review[{index}].public_key",
        )

        verified = verify_verification_receipt_signature_v06(
            receipt,
            signature,
            public_key,
        )
        fingerprint = verified.get("reviewer_public_key_fingerprint")
        if isinstance(fingerprint, str):
            fingerprint_counts[fingerprint] += 1

        reviewer_rule = authorized.get(fingerprint) if isinstance(fingerprint, str) else None
        reasons: list[str] = []
        if not verified["valid"]:
            reasons.append("invalid_reviewer_signature")
        if reviewer_rule is None:
            reasons.append("reviewer_not_authorized")
        else:
            required_policy = reviewer_rule["required_policy_sha256"]
            if (
                required_policy is not None
                and verified.get("policy_sha256") != required_policy
            ):
                reasons.append("reviewer_policy_hash_mismatch")
        if verified.get("pcs_valid") is not True:
            reasons.append("pcs_verification_not_valid")
        if verified.get("reviewer_accepted") is not True:
            reasons.append("reviewer_did_not_accept")
        subject = _subject_key(verified)
        if subject is None:
            reasons.append("reviewed_subject_commitments_invalid")
        expected_bundle = policy["expected_bundle_sha256"]
        if (
            subject is not None
            and expected_bundle is not None
            and subject[0] != expected_bundle
        ):
            reasons.append("bundle_does_not_match_quorum_policy")

        evaluated.append(
            {
                "index": index,
                "receipt": item["receipt"],
                "signature": item["signature"],
                "public_key": item["public_key"],
                "reviewer_public_key_fingerprint": fingerprint,
                "role": reviewer_rule["role"] if reviewer_rule else None,
                "required_policy_sha256": (
                    reviewer_rule["required_policy_sha256"] if reviewer_rule else None
                ),
                "policy_sha256": verified.get("policy_sha256"),
                "signature_valid": bool(verified["valid"]),
                "pcs_valid": verified.get("pcs_valid"),
                "reviewer_accepted": verified.get("reviewer_accepted"),
                "subject": (
                    {
                        "bundle_sha256": subject[0],
                        "certificate_semantic_hash": subject[1],
                        "certificate_integrity_hash": subject[2],
                        "normalized_index_semantic_hash": subject[3],
                    }
                    if subject is not None
                    else None
                ),
                "reasons": reasons,
                "_subject_key": subject,
            }
        )

    for review in evaluated:
        fingerprint = review["reviewer_public_key_fingerprint"]
        if isinstance(fingerprint, str) and fingerprint_counts[fingerprint] > 1:
            if "duplicate_reviewer_identity" not in review["reasons"]:
                review["reasons"].append("duplicate_reviewer_identity")

    groups: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for review in evaluated:
        if review["reasons"]:
            continue
        subject = review["_subject_key"]
        if subject is not None:
            groups[subject].append(review)

    subject_results: list[dict[str, Any]] = []
    for subject, subject_reviews in sorted(groups.items()):
        role_counts = Counter(r["role"] for r in subject_reviews)
        total = len(subject_reviews)
        role_failures = {
            role: {"required": required, "actual": role_counts[role]}
            for role, required in sorted(policy["required_roles"].items())
            if role_counts[role] < required
        }
        threshold_met = total >= policy["min_accepted_reviews"]
        quorum_met = threshold_met and not role_failures
        subject_results.append(
            {
                "subject": {
                    "bundle_sha256": subject[0],
                    "certificate_semantic_hash": subject[1],
                    "certificate_integrity_hash": subject[2],
                    "normalized_index_semantic_hash": subject[3],
                },
                "accepted_review_count": total,
                "accepted_reviewer_fingerprints": sorted(
                    r["reviewer_public_key_fingerprint"] for r in subject_reviews
                ),
                "role_counts": dict(sorted(role_counts.items())),
                "threshold_met": threshold_met,
                "role_failures": role_failures,
                "quorum_met": quorum_met,
            }
        )

    passing_subjects = [x for x in subject_results if x["quorum_met"]]
    passed = len(passing_subjects) == 1
    failures: list[dict[str, Any]] = []
    if not passing_subjects:
        failures.append(
            {
                "type": "quorum_not_met",
                "reason": "no single reviewed subject satisfies all thresholds",
            }
        )
    elif len(passing_subjects) > 1:
        failures.append(
            {
                "type": "ambiguous_quorum",
                "reason": "multiple distinct reviewed subjects independently satisfy quorum",
                "count": len(passing_subjects),
            }
        )

    public_reviews = []
    for review in evaluated:
        clean = {k: v for k, v in review.items() if k != "_subject_key"}
        public_reviews.append(clean)

    return {
        "format": QUORUM_RESULT_FORMAT_V06,
        "pass": passed,
        "quorum_policy_sha256": _sha256_bytes(policy_raw),
        "review_set_sha256": _sha256_bytes(review_set_raw),
        "quorum_policy": policy,
        "selected_subject": passing_subjects[0]["subject"] if passed else None,
        "accepted_review_count": (
            passing_subjects[0]["accepted_review_count"] if passed else 0
        ),
        "role_counts": passing_subjects[0]["role_counts"] if passed else {},
        "subject_groups": subject_results,
        "reviews": public_reviews,
        "failures": failures,
    }
