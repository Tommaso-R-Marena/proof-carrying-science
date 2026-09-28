from __future__ import annotations

import json
import hashlib
import tempfile
import zipfile
import unicodedata
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from .kernel import verify_certificate, CHECKER_VERSION
from .bundle import (
    MAX_BUNDLE_FILES,
    MAX_BUNDLE_TOTAL_UNCOMPRESSED,
    MAX_BUNDLE_SINGLE_FILE,
)
from .package import verify_package_manifest, verify_package_signature
from .policy import evaluate_policy, validate_policy
from .signing import verify_signature
from .schema_validation import validate_verification_receipt_shape, SchemaValidationError
from .jsonio import strict_json_load, strict_json_loads, StrictJSONError


class BundleVerificationError(ValueError):
    pass


_WINDOWS_FORBIDDEN = set('<>:"|?*')
_WINDOWS_RESERVED = {
    "con", "prn", "aux", "nul",
    *(f"com{i}" for i in range(1, 10)),
    *(f"lpt{i}" for i in range(1, 10)),
}


def _safe_member(name: str) -> bool:
    p = PurePosixPath(name)
    return bool(name) and not p.is_absolute() and ".." not in p.parts and "\\" not in name


def _validate_zip_namespace(infos: list[zipfile.ZipInfo]) -> set[str]:
    """Require one canonical, unambiguous filesystem interpretation of the ZIP."""
    kinds: dict[str, str] = {}
    file_names: set[str] = set()

    for info in infos:
        name = info.filename
        if not _safe_member(name):
            raise BundleVerificationError(f"unsafe ZIP member: {name!r}")

        is_dir = info.is_dir()
        raw = name[:-1] if is_dir and name.endswith("/") else name
        canonical = PurePosixPath(raw).as_posix()
        expected = f"{canonical}/" if is_dir else canonical
        if not canonical or name != expected:
            raise BundleVerificationError(f"non-canonical ZIP member: {name!r}")

        # Require a portable namespace: Python/OS extraction can otherwise map
        # distinct ZIP names to the same path on Windows or normalization-sensitive
        # filesystems.
        portable_parts: list[str] = []
        for segment in PurePosixPath(canonical).parts:
            nfc = unicodedata.normalize("NFC", segment)
            if segment != nfc:
                raise BundleVerificationError(
                    f"non-NFC ZIP member segment is not portable: {segment!r}"
                )
            if any(ord(ch) < 32 or ch in _WINDOWS_FORBIDDEN for ch in segment):
                raise BundleVerificationError(
                    f"ZIP member contains non-portable filename characters: {segment!r}"
                )
            if segment.endswith((" ", ".")):
                raise BundleVerificationError(
                    f"ZIP member has non-portable trailing space/dot: {segment!r}"
                )
            stem = segment.split(".", 1)[0].casefold()
            if stem in _WINDOWS_RESERVED:
                raise BundleVerificationError(
                    f"ZIP member uses Windows-reserved filename: {segment!r}"
                )
            portable_parts.append(nfc.casefold())

        portable_key = "/".join(portable_parts)
        for existing, existing_kind in kinds.items():
            existing_key = "/".join(
                unicodedata.normalize("NFC", p).casefold()
                for p in PurePosixPath(existing).parts
            )
            if existing_key == portable_key and existing != canonical:
                raise BundleVerificationError(
                    f"cross-platform ZIP name collision: {existing!r} vs {canonical!r}"
                )

        kind = "directory" if is_dir else "file"
        if canonical in kinds:
            raise BundleVerificationError(
                f"duplicate or file/directory-colliding ZIP member: {name!r}"
            )
        kinds[canonical] = kind
        if not is_dir:
            file_names.add(canonical)

    # A regular file may never also serve as a parent directory for another member.
    for canonical in sorted(kinds):
        parts = PurePosixPath(canonical).parts
        for i in range(1, len(parts)):
            prefix = PurePosixPath(*parts[:i]).as_posix()
            if kinds.get(prefix) == "file":
                raise BundleVerificationError(
                    f"ZIP namespace collision: file {prefix!r} is parent of {canonical!r}"
                )

    return file_names


def verify_bundle(
    bundle_path: str | Path,
    *,
    public_key: str | Path | None = None,
    require_signature: bool = False,
    expected_signer_fingerprint: str | None = None,
    policy: str | Path | None = None,
) -> dict[str, object]:
    bundle_path = Path(bundle_path).resolve()
    bundle_sha256 = hashlib.sha256(bundle_path.read_bytes()).hexdigest()
    errors: list[str] = []
    with zipfile.ZipFile(bundle_path, "r") as zf:
        infos = zf.infolist()
        if len(infos) > MAX_BUNDLE_FILES:
            raise BundleVerificationError(f"bundle has too many files: {len(infos)} > {MAX_BUNDLE_FILES}")
        names = _validate_zip_namespace(infos)
        total = 0
        for info in infos:
            mode = (info.external_attr >> 16) & 0o170000
            if mode == 0o120000:
                raise BundleVerificationError(f"symlink ZIP member not allowed: {info.filename!r}")
            if info.file_size > MAX_BUNDLE_SINGLE_FILE:
                raise BundleVerificationError(f"bundle member too large: {info.filename!r}")
            total += info.file_size
            if total > MAX_BUNDLE_TOTAL_UNCOMPRESSED:
                raise BundleVerificationError("bundle exceeds uncompressed size limit")
        if "certificate.json" not in names:
            raise BundleVerificationError("bundle lacks certificate.json at package root")

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            zf.extractall(root)
            cert = root / "certificate.json"
            integrity = verify_certificate(cert)
            if not integrity["valid"]:
                errors.extend(integrity["errors"])

            package_manifest_result = verify_package_manifest(root)
            if not package_manifest_result["valid"]:
                errors.extend([f"package: {e}" for e in package_manifest_result["errors"]])

            package_sig_result = None
            package_sig_path = root / "package_signature.json"
            package_signature_present = package_sig_path.is_file()
            authentication_requested = bool(
                require_signature or public_key is not None or expected_signer_fingerprint is not None
            )
            if authentication_requested:
                if not package_signature_present:
                    errors.append("required package_signature.json is missing")
                elif public_key is None:
                    errors.append("public key is required to verify package signature")
                else:
                    package_sig_result = verify_package_signature(
                        root / "package_manifest.json",
                        package_sig_path,
                        public_key,
                        expected_fingerprint=expected_signer_fingerprint,
                    )
                    if not package_sig_result["valid"]:
                        errors.extend([f"package signature: {e}" for e in package_sig_result["errors"]])

            if package_sig_result is not None:
                authenticity_status = "VERIFIED" if package_sig_result["valid"] else "INVALID"
            elif package_signature_present:
                authenticity_status = "PRESENT_NOT_VERIFIED"
            elif require_signature:
                authenticity_status = "REQUIRED_MISSING"
            else:
                authenticity_status = "UNSIGNED"

            cert_sig_result = None
            cert_signature_path = root / "signature.json"
            if cert_signature_path.is_file() and public_key is not None:
                cert_sig_result = verify_signature(cert, cert_signature_path, public_key)
                if not cert_sig_result["valid"]:
                    errors.extend([f"certificate signature: {e}" for e in cert_sig_result["errors"]])

            policy_result = None
            policy_sha256 = None
            if policy is not None:
                try:
                    cert_obj = strict_json_load(cert)
                    policy_bytes = Path(policy).read_bytes()
                    policy_sha256 = hashlib.sha256(policy_bytes).hexdigest()
                    policy_obj = validate_policy(strict_json_loads(policy_bytes.decode("utf-8")))
                except (StrictJSONError, UnicodeDecodeError) as exc:
                    raise BundleVerificationError(f"invalid reviewer policy/certificate JSON: {exc}") from exc
                policy_result = evaluate_policy(
                    cert_obj,
                    policy_obj,
                    signature_valid=bool(package_sig_result and package_sig_result["valid"]),
                    signer_fingerprint=(package_sig_result or {}).get("public_key_fingerprint"),
                )
                if not policy_result["pass"]:
                    errors.extend([f"policy: {f}" for f in policy_result["failures"]])

            dimensions = {
                "scientific_replay": "PASS" if integrity["valid"] else "FAIL",
                "package_integrity": "PASS" if package_manifest_result["valid"] else "FAIL",
                "signer_authenticity": authenticity_status,
                "reviewer_policy": (
                    "NOT_APPLIED" if policy_result is None else "PASS" if policy_result["pass"] else "FAIL"
                ),
            }

            receipt = {
                "verification_receipt_format": "pcs-bundle-verification-v1",
                "verifier_version": CHECKER_VERSION,
                "verified_at": datetime.now(timezone.utc).isoformat(),
                "valid": not errors,
                "errors": errors,
                "bundle": str(bundle_path),
                "bundle_sha256": bundle_sha256,
                "verification_inputs": {
                    "require_signature": bool(require_signature),
                    "expected_signer_fingerprint": expected_signer_fingerprint,
                    "policy_sha256": policy_sha256,
                },
                "file_count": len(names),
                "uncompressed_bytes": total,
                "assurance_dimensions": dimensions,
                "certificate": integrity,
                "package_manifest": package_manifest_result,
                "package_signature": package_sig_result,
                "certificate_signature": cert_sig_result,
                "signature": package_sig_result or cert_sig_result,
                "policy": policy_result,
                "interpretation": (
                    "Overall validity reflects only the checks requested in this invocation. "
                    "A replay-valid bundle is not authenticated unless signer_authenticity is VERIFIED, "
                    "and it is not reviewer-approved unless reviewer_policy is PASS."
                ),
            }
            try:
                validate_verification_receipt_shape(receipt)
            except SchemaValidationError as exc:
                raise BundleVerificationError(
                    f"internal verification receipt violated its JSON Schema: {exc}"
                ) from exc
            return receipt
