from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .package_v06 import (
    MAX_PACKAGE_FILES_V06,
    MAX_PACKAGE_SINGLE_FILE_V06,
    MAX_PACKAGE_TOTAL_BYTES_V06,
    validate_package_namespace_v06,
    V06PackageError,
)
from .signing import public_key_fingerprint
from .verifier_v06 import verify_end_to_end_v06


CONTROL_FILES_V06 = {
    "certificate_signature.json",
    "package_manifest.json",
    "package_signature.json",
}


class V06VerifierIOError(ValueError):
    pass


def load_public_key_v06(path: str | Path) -> Ed25519PublicKey:
    try:
        raw = Path(path).read_bytes()
        key = serialization.load_pem_public_key(raw)
    except (OSError, ValueError, TypeError) as exc:
        raise V06VerifierIOError(
            f"cannot load Ed25519 public key: {type(exc).__name__}: {exc}"
        ) from exc
    if not isinstance(key, Ed25519PublicKey):
        raise V06VerifierIOError("public key is not Ed25519")
    return key


def _read_control_file(root: Path, name: str, *, max_bytes: int) -> bytes:
    path = root / name
    if not path.exists():
        raise V06VerifierIOError(f"missing required v0.6 control file: {name}")
    if path.is_symlink():
        raise V06VerifierIOError(f"refusing symlinked v0.6 control file: {name}")
    if not path.is_file():
        raise V06VerifierIOError(f"v0.6 control path is not a regular file: {name}")
    size = path.stat().st_size
    if size > max_bytes:
        raise V06VerifierIOError(
            f"v0.6 control file exceeds byte limit: {name}: {size} > {max_bytes}"
        )
    return path.read_bytes()


def load_package_directory_v06(root: str | Path) -> dict[str, Any]:
    """Load a v0.6 package directory without trusting its manifest.

    Namespace, count and byte limits are enforced before package member bytes are
    handed to the cryptographic verifier.
    """
    package_root = Path(root).resolve()
    if not package_root.is_dir():
        raise V06VerifierIOError(
            f"v0.6 package path is not a directory: {package_root}"
        )

    certificate_bytes = _read_control_file(
        package_root, "certificate.json", max_bytes=10 * 1024 * 1024
    )
    certificate_signature_bytes = _read_control_file(
        package_root, "certificate_signature.json", max_bytes=16 * 1024 * 1024
    )
    package_manifest_bytes = _read_control_file(
        package_root, "package_manifest.json", max_bytes=10 * 1024 * 1024
    )
    package_signature_bytes = _read_control_file(
        package_root, "package_signature.json", max_bytes=16 * 1024 * 1024
    )

    all_paths = sorted(package_root.rglob("*"))
    symlinks = [
        path.relative_to(package_root).as_posix()
        for path in all_paths
        if path.is_symlink()
    ]
    if symlinks:
        raise V06VerifierIOError(f"refusing symlinks in v0.6 package: {symlinks}")

    package_files: dict[str, bytes] = {}
    total = 0
    count = 0
    for path in all_paths:
        if not path.is_file():
            continue
        rel = path.relative_to(package_root).as_posix()
        if rel in CONTROL_FILES_V06:
            continue

        count += 1
        if count > MAX_PACKAGE_FILES_V06:
            raise V06VerifierIOError(
                f"v0.6 package exceeds file-count limit: {count} > {MAX_PACKAGE_FILES_V06}"
            )
        size = path.stat().st_size
        if size > MAX_PACKAGE_SINGLE_FILE_V06:
            raise V06VerifierIOError(
                f"v0.6 package member exceeds byte limit: {rel}: "
                f"{size} > {MAX_PACKAGE_SINGLE_FILE_V06}"
            )
        total += size
        if total > MAX_PACKAGE_TOTAL_BYTES_V06:
            raise V06VerifierIOError(
                f"v0.6 package exceeds total byte limit: "
                f"{total} > {MAX_PACKAGE_TOTAL_BYTES_V06}"
            )
        package_files[rel] = path.read_bytes()

    try:
        validate_package_namespace_v06(
            {name: {} for name in package_files}
        )
    except V06PackageError as exc:
        raise V06VerifierIOError(str(exc)) from exc

    return {
        "root": package_root,
        "certificate_bytes": certificate_bytes,
        "certificate_signature_bytes": certificate_signature_bytes,
        "package_manifest_bytes": package_manifest_bytes,
        "package_signature_bytes": package_signature_bytes,
        "package_files": package_files,
    }


def verify_package_directory_end_to_end_v06(
    root: str | Path,
    public_key_path: str | Path,
    *,
    expected_fingerprint: str | None = None,
) -> dict[str, Any]:
    loaded = load_package_directory_v06(root)
    public_key = load_public_key_v06(public_key_path)
    result = verify_end_to_end_v06(
        certificate_bytes=loaded["certificate_bytes"],
        certificate_signature_bytes=loaded["certificate_signature_bytes"],
        package_manifest_bytes=loaded["package_manifest_bytes"],
        package_signature_bytes=loaded["package_signature_bytes"],
        package_files=loaded["package_files"],
        public_key=public_key,
        expected_fingerprint=expected_fingerprint,
    )
    receipt = dict(result)
    receipt["package_root"] = str(loaded["root"])
    receipt["public_key_fingerprint"] = result.get(
        "public_key_fingerprint", public_key_fingerprint(public_key)
    )
    return receipt


def write_verification_receipt_v06(
    receipt: dict[str, Any],
    output: str | Path,
) -> Path:
    path = Path(output).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(receipt, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return path
