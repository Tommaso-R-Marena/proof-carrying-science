from __future__ import annotations

import hashlib
import os
import tempfile
import zipfile
from pathlib import Path
from typing import Any

from .byte_contract_v06 import (
    V06ByteContractError,
    parse_package_manifest_bytes_v06,
)
from .package_v06 import (
    MAX_PACKAGE_SINGLE_FILE_V06,
    MAX_PACKAGE_TOTAL_BYTES_V06,
    validate_package_namespace_v06,
    V06PackageError,
)
from .verifier_io_v06 import (
    CONTROL_FILES_V06,
    V06VerifierIOError,
    load_package_directory_v06,
    verify_package_directory_end_to_end_v06,
)
from .verifier_zip_v06 import (
    V06BundleVerificationError,
    verify_package_zip_end_to_end_v06,
)
from .lean_authority_v06 import V06LeanAuthorityError
from .canonical_zip_v06 import canonical_zip_bytes_v06


BUNDLE_FORMAT_V06 = "pcs-v06-zip-stored-v1"
FIXED_ZIP_TIME_V06 = (1980, 1, 1, 0, 0, 0)
_PRIVATE_KEY_MARKERS_V06 = (
    b"-----BEGIN PRIVATE KEY-----",
    b"-----BEGIN ENCRYPTED PRIVATE KEY-----",
    b"-----BEGIN OPENSSH PRIVATE KEY-----",
    b"-----BEGIN RSA PRIVATE KEY-----",
    b"-----BEGIN EC PRIVATE KEY-----",
)


class V06BundleBuildError(ValueError):
    pass


def _sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(1024 * 1024)
            if not chunk:
                return digest.hexdigest()
            digest.update(chunk)


def _inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def create_verified_bundle_v06(
    package_root: str | Path,
    output: str | Path,
    public_key_path: str | Path,
    *,
    expected_fingerprint: str | None = None,
    overwrite: bool = False,
    lean_authority_path: str | Path | None = None,
) -> dict[str, Any]:
    """Create a deterministic ZIP from an already-valid v0.6 package directory.

    The package is end-to-end verified first. The archive then contains exactly
    the manifest-signed members plus the three signature/manifest control files.
    """
    root = Path(package_root).resolve()
    out = Path(output).resolve()

    if not root.is_dir():
        raise V06BundleBuildError(f"v0.6 package root is not a directory: {root}")
    if _inside(out, root):
        raise V06BundleBuildError(
            "v0.6 bundle output must be outside the package directory"
        )
    if out.exists() and not overwrite:
        raise V06BundleBuildError(
            f"refusing to overwrite existing v0.6 bundle: {out}"
        )

    try:
        loaded = load_package_directory_v06(root)
        verification = verify_package_directory_end_to_end_v06(
            root,
            public_key_path,
            expected_fingerprint=expected_fingerprint,
            lean_authority_path=lean_authority_path,
        )
    except (V06VerifierIOError, V06LeanAuthorityError) as exc:
        raise V06BundleBuildError(str(exc)) from exc

    if not verification["valid"]:
        raise V06BundleBuildError(
            "refusing to bundle a v0.6 package that does not pass end-to-end "
            f"verification: stage={verification.get('failed_stage')} "
            f"errors={verification.get('errors', [])}"
        )

    try:
        manifest = parse_package_manifest_bytes_v06(
            loaded["package_manifest_bytes"]
        )
    except V06ByteContractError as exc:
        raise V06BundleBuildError(str(exc)) from exc

    signed_names = list(manifest["files"].keys())
    expected_signed = set(signed_names)
    actual_signed = set(loaded["package_files"])
    if actual_signed != expected_signed:
        missing = sorted(expected_signed - actual_signed)
        unexpected = sorted(actual_signed - expected_signed)
        raise V06BundleBuildError(
            "v0.6 package directory does not exactly match manifest before bundling: "
            f"missing={missing} unexpected={unexpected}"
        )

    try:
        validate_package_namespace_v06(
            {name: manifest["files"][name] for name in signed_names}
        )
    except V06PackageError as exc:
        raise V06BundleBuildError(str(exc)) from exc

    control_bytes = {
        "certificate_signature.json": loaded["certificate_signature_bytes"],
        "package_manifest.json": loaded["package_manifest_bytes"],
        "package_signature.json": loaded["package_signature_bytes"],
    }

    members: dict[str, bytes] = {
        **{name: loaded["package_files"][name] for name in signed_names},
        **control_bytes,
    }

    total = 0
    for name, raw in members.items():
        if len(raw) > MAX_PACKAGE_SINGLE_FILE_V06 and name not in CONTROL_FILES_V06:
            raise V06BundleBuildError(
                f"v0.6 bundle member exceeds byte limit: {name!r}"
            )
        if any(marker in raw for marker in _PRIVATE_KEY_MARKERS_V06):
            raise V06BundleBuildError(
                f"refusing apparent private-key material in v0.6 bundle member: {name!r}"
            )
        total += len(raw)
    if total > MAX_PACKAGE_TOTAL_BYTES_V06 + sum(len(x) for x in control_bytes.values()):
        raise V06BundleBuildError("v0.6 bundle members exceed aggregate byte limit")

    out.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=f".{out.name}.",
            suffix=".pcs-tmp",
            dir=out.parent,
            delete=False,
        ) as tmp:
            temp_path = Path(tmp.name)

        # The single canonical PCS STORED encoding, decoded by the verified Lean
        # authority directly from the raw bytes (formal/PCS/V2/Zip.lean).
        temp_path.write_bytes(canonical_zip_bytes_v06(members))

        post_build = verify_package_zip_end_to_end_v06(
            temp_path,
            public_key_path,
            expected_fingerprint=expected_fingerprint,
            lean_authority_path=lean_authority_path,
        )
        if not post_build["valid"]:
            raise V06BundleBuildError(
                "refusing to publish v0.6 bundle that failed post-build "
                f"verification: stage={post_build.get('failed_stage')} "
                f"errors={post_build.get('errors', [])}"
            )

        candidate_sha256 = _sha256_path(temp_path)
        if post_build.get("bundle_sha256") != candidate_sha256:
            raise V06BundleBuildError(
                "post-build verifier bundle SHA-256 disagrees with candidate bytes"
            )

        os.replace(temp_path, out)
        temp_path = None

    except (OSError, zipfile.BadZipFile, V06BundleVerificationError, V06LeanAuthorityError) as exc:
        raise V06BundleBuildError(
            f"cannot create or verify v0.6 bundle: {type(exc).__name__}: {exc}"
        ) from exc
    finally:
        if temp_path is not None:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass

    final_sha256 = _sha256_path(out)
    if final_sha256 != candidate_sha256:
        raise V06BundleBuildError(
            "published v0.6 bundle bytes differ from the post-build verified candidate"
        )

    return {
        "format": BUNDLE_FORMAT_V06,
        "bundle": str(out),
        "bundle_sha256": final_sha256,
        "archive_bytes": out.stat().st_size,
        "member_count": len(members),
        "members": sorted(members),
        "certificate_semantic_hash": verification["certificate_semantic_hash"],
        "certificate_integrity_hash": verification["certificate_integrity_hash"],
        "normalized_index_semantic_hash": verification[
            "normalized_index_semantic_hash"
        ],
        "public_key_fingerprint": verification["public_key_fingerprint"],
        "post_build_verified": True,
    }
