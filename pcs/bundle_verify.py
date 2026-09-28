from __future__ import annotations

import json
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

from .kernel import verify_certificate
from .package import verify_package_manifest, verify_package_signature
from .policy import evaluate_policy_file
from .signing import verify_signature


class BundleVerificationError(ValueError):
    pass


MAX_FILES = 1000
MAX_TOTAL_UNCOMPRESSED = 100 * 1024 * 1024
MAX_SINGLE_FILE = 50 * 1024 * 1024


def _safe_member(name: str) -> bool:
    p = PurePosixPath(name)
    return bool(name) and not p.is_absolute() and ".." not in p.parts and "\\" not in name


def verify_bundle(
    bundle_path: str | Path,
    *,
    public_key: str | Path | None = None,
    require_signature: bool = False,
    expected_signer_fingerprint: str | None = None,
    policy: str | Path | None = None,
) -> dict[str, object]:
    bundle_path = Path(bundle_path).resolve()
    errors: list[str] = []
    with zipfile.ZipFile(bundle_path, "r") as zf:
        infos = zf.infolist()
        if len(infos) > MAX_FILES:
            raise BundleVerificationError(f"bundle has too many files: {len(infos)} > {MAX_FILES}")
        total = 0
        for info in infos:
            if not _safe_member(info.filename):
                raise BundleVerificationError(f"unsafe ZIP member: {info.filename!r}")
            mode = (info.external_attr >> 16) & 0o170000
            if mode == 0o120000:
                raise BundleVerificationError(f"symlink ZIP member not allowed: {info.filename!r}")
            if info.file_size > MAX_SINGLE_FILE:
                raise BundleVerificationError(f"bundle member too large: {info.filename!r}")
            total += info.file_size
            if total > MAX_TOTAL_UNCOMPRESSED:
                raise BundleVerificationError("bundle exceeds uncompressed size limit")
        names = {i.filename for i in infos if not i.is_dir()}
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
            if policy is not None:
                cert_obj = json.loads(cert.read_text(encoding="utf-8"))
                policy_result = evaluate_policy_file(
                    cert_obj,
                    policy,
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

            return {
                "valid": not errors,
                "errors": errors,
                "bundle": str(bundle_path),
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
