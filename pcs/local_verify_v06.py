from __future__ import annotations

from pathlib import Path
from typing import Any

from .jsonio import strict_json_load
from .verifier_io_v06 import write_verification_receipt_v06
from .verifier_zip_v06 import verify_package_zip_end_to_end_v06


TRUST_PROFILE_FORMAT_V06 = "pcs-verifier-trust-v1"


class V06LocalVerifyError(ValueError):
    pass


def load_trust_profile_v06(path: str | Path) -> dict[str, Any]:
    source = Path(path).resolve()
    value = strict_json_load(source)
    if not isinstance(value, dict) or value.get("format") != TRUST_PROFILE_FORMAT_V06:
        raise V06LocalVerifyError(f"trust profile must use {TRUST_PROFILE_FORMAT_V06!r}")
    public_key = value.get("public_key")
    fingerprint = value.get("expected_signer_fingerprint")
    if not isinstance(public_key, str) or not public_key:
        raise V06LocalVerifyError("trust profile public_key must be a non-empty string")
    if not isinstance(fingerprint, str) or len(fingerprint) != 64:
        raise V06LocalVerifyError("trust profile expected_signer_fingerprint must be a 64-hex SHA-256")
    try:
        int(fingerprint, 16)
    except ValueError as exc:
        raise V06LocalVerifyError("trust profile signer fingerprint must be lowercase/uppercase hex") from exc
    base = source.parent
    resolved = {
        "format": TRUST_PROFILE_FORMAT_V06,
        "public_key": str((base / public_key).resolve()),
        "expected_signer_fingerprint": fingerprint.lower(),
        "policy": None,
        "lean_authority": None,
        "expected_build_provenance_fingerprint": None,
        "expected_build_subject_sha256": [],
        "profile": str(source),
    }
    policy = value.get("policy")
    if policy is not None:
        if not isinstance(policy, str) or not policy:
            raise V06LocalVerifyError("trust profile policy must be a relative path string")
        resolved["policy"] = str((base / policy).resolve())
    lean_authority = value.get("lean_authority")
    if lean_authority is not None:
        if not isinstance(lean_authority, str) or not lean_authority:
            raise V06LocalVerifyError("trust profile lean_authority must be a relative path string")
        resolved["lean_authority"] = str((base / lean_authority).resolve())

    build_fingerprint = value.get("expected_build_provenance_fingerprint")
    if build_fingerprint is not None:
        if not isinstance(build_fingerprint, str) or len(build_fingerprint) != 64:
            raise V06LocalVerifyError(
                "trust profile expected_build_provenance_fingerprint must be a 64-hex SHA-256"
            )
        try:
            int(build_fingerprint, 16)
        except ValueError as exc:
            raise V06LocalVerifyError(
                "trust profile build-provenance fingerprint must be hex"
            ) from exc
        resolved["expected_build_provenance_fingerprint"] = build_fingerprint.lower()

    build_subjects = value.get("expected_build_subject_sha256", [])
    if (
        not isinstance(build_subjects, list)
        or not all(isinstance(item, str) and len(item) == 64 for item in build_subjects)
        or len(build_subjects) != len(set(build_subjects))
    ):
        raise V06LocalVerifyError(
            "trust profile expected_build_subject_sha256 must be a unique array of 64-hex SHA-256 strings"
        )
    normalized_subjects: list[str] = []
    for digest in build_subjects:
        try:
            int(digest, 16)
        except ValueError as exc:
            raise V06LocalVerifyError(
                "trust profile build-provenance subject SHA-256 must be hex"
            ) from exc
        normalized_subjects.append(digest.lower())
    resolved["expected_build_subject_sha256"] = sorted(normalized_subjects)

    if (build_fingerprint is None) != (len(normalized_subjects) == 0):
        raise V06LocalVerifyError(
            "trust profile build provenance requires both "
            "expected_build_provenance_fingerprint and at least one "
            "expected_build_subject_sha256"
        )

    for key in ("public_key", "policy", "lean_authority"):
        candidate = resolved.get(key)
        if candidate and not Path(candidate).is_file():
            raise V06LocalVerifyError(f"trust profile {key} does not exist: {candidate}")
    return resolved


def verify_local_bundle_v06(
    bundle: str | Path,
    trust_profile: str | Path,
    *,
    receipt: str | Path | None = None,
    overwrite_receipt: bool = False,
    lean_authority_path: str | Path | None = None,
) -> dict[str, Any]:
    trust = load_trust_profile_v06(trust_profile)
    result = verify_package_zip_end_to_end_v06(
        bundle,
        trust["public_key"],
        expected_fingerprint=trust["expected_signer_fingerprint"],
        policy_path=trust["policy"],
        lean_authority_path=(lean_authority_path or trust["lean_authority"]),
        expected_build_provenance_fingerprint=trust[
            "expected_build_provenance_fingerprint"
        ],
        expected_build_subject_sha256=trust[
            "expected_build_subject_sha256"
        ],
    )
    out = dict(result)
    out["trust_profile"] = trust["profile"]
    if receipt is not None:
        written = write_verification_receipt_v06(
            result,
            receipt,
            overwrite=overwrite_receipt,
        )
        out["receipt_written"] = str(written)
    return out
