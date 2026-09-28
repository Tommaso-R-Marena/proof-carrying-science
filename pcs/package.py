from __future__ import annotations

import base64
import json
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from .hashing import canonical_json_bytes, sha256_file
from .signing import _load_private, _load_public, public_key_fingerprint

PACKAGE_FORMAT = "pcs-package-v1"
PACKAGE_SIGNATURE_FORMAT = "pcs-package-ed25519-v1"
EXCLUDED_PACKAGE_FILES = {"package_manifest.json", "package_signature.json"}


class PackageError(ValueError):
    pass


def build_package_manifest(root: str | Path, output_path: str | Path | None = None) -> dict:
    root = Path(root).resolve()
    if not root.is_dir():
        raise PackageError(f"package root is not a directory: {root}")
    entries: dict[str, dict[str, int | str]] = {}
    for p in sorted(x for x in root.rglob("*") if x.is_file()):
        rel = p.relative_to(root).as_posix()
        if rel in EXCLUDED_PACKAGE_FILES:
            continue
        entries[rel] = {"sha256": sha256_file(p), "size": p.stat().st_size}
    cert_path = root / "certificate.json"
    if not cert_path.is_file():
        raise PackageError("package lacks certificate.json")
    cert = json.loads(cert_path.read_text(encoding="utf-8"))
    manifest = {
        "package_format": PACKAGE_FORMAT,
        "certificate_semantic_hash": cert.get("semantic_hash"),
        "certificate_integrity_hash": cert.get("integrity_hash"),
        "files": entries,
    }
    out = Path(output_path).resolve() if output_path else root / "package_manifest.json"
    out.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return manifest


def verify_package_manifest(root: str | Path, manifest_path: str | Path | None = None) -> dict:
    root = Path(root).resolve()
    path = Path(manifest_path).resolve() if manifest_path else root / "package_manifest.json"
    errors: list[str] = []
    if not path.is_file():
        return {"valid": False, "errors": ["package_manifest.json is missing"]}
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        return {"valid": False, "errors": [f"invalid package manifest: {type(e).__name__}: {e}"]}
    if manifest.get("package_format") != PACKAGE_FORMAT:
        errors.append("unsupported package manifest format")
    files = manifest.get("files")
    if not isinstance(files, dict):
        errors.append("package manifest files must be an object")
        files = {}
    expected_names = set(files)
    actual_names = {
        p.relative_to(root).as_posix()
        for p in root.rglob("*")
        if p.is_file() and p.relative_to(root).as_posix() not in EXCLUDED_PACKAGE_FILES
    }
    missing = sorted(expected_names - actual_names)
    unexpected = sorted(actual_names - expected_names)
    if missing:
        errors.append(f"package files missing: {missing}")
    if unexpected:
        errors.append(f"unexpected package files not bound by manifest: {unexpected}")
    for rel, meta in files.items():
        p = (root / rel).resolve()
        try:
            p.relative_to(root)
        except ValueError:
            errors.append(f"unsafe package manifest path: {rel!r}")
            continue
        if not p.is_file():
            continue
        got_hash = sha256_file(p)
        got_size = p.stat().st_size
        if not isinstance(meta, dict):
            errors.append(f"invalid package metadata for {rel}")
            continue
        if meta.get("sha256") != got_hash:
            errors.append(f"package hash mismatch: {rel}")
        if meta.get("size") != got_size:
            errors.append(f"package size mismatch: {rel}")
    cert_path = root / "certificate.json"
    if cert_path.is_file():
        try:
            cert = json.loads(cert_path.read_text(encoding="utf-8"))
            if manifest.get("certificate_semantic_hash") != cert.get("semantic_hash"):
                errors.append("package manifest certificate semantic hash mismatch")
            if manifest.get("certificate_integrity_hash") != cert.get("integrity_hash"):
                errors.append("package manifest certificate integrity hash mismatch")
        except Exception as e:
            errors.append(f"cannot read package certificate: {type(e).__name__}: {e}")
    return {"valid": not errors, "errors": errors, "manifest": manifest}


def sign_package_manifest(manifest_path: str | Path, private_key_path: str | Path, output_path: str | Path) -> dict:
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    if manifest.get("package_format") != PACKAGE_FORMAT:
        raise PackageError("refusing to sign unsupported package manifest")
    key = _load_private(private_key_path)
    pub = key.public_key()
    signature = key.sign(canonical_json_bytes(manifest))
    record = {
        "signature_format": PACKAGE_SIGNATURE_FORMAT,
        "algorithm": "Ed25519",
        "public_key_fingerprint": public_key_fingerprint(pub),
        "package_manifest_sha256": sha256_file(manifest_path),
        "signature": base64.b64encode(signature).decode("ascii"),
    }
    Path(output_path).write_text(json.dumps(record, indent=2, sort_keys=True), encoding="utf-8")
    return record


def verify_package_signature(
    manifest_path: str | Path,
    signature_path: str | Path,
    public_key_path: str | Path,
    *,
    expected_fingerprint: str | None = None,
) -> dict:
    errors: list[str] = []
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    record = json.loads(Path(signature_path).read_text(encoding="utf-8"))
    if record.get("signature_format") != PACKAGE_SIGNATURE_FORMAT:
        errors.append("unsupported package signature format")
    try:
        pub = _load_public(public_key_path)
        fingerprint = public_key_fingerprint(pub)
        if record.get("public_key_fingerprint") != fingerprint:
            errors.append("package signature public key fingerprint mismatch")
        if expected_fingerprint is not None and fingerprint.lower() != expected_fingerprint.lower():
            errors.append("signer fingerprint does not match pinned expected fingerprint")
        if record.get("package_manifest_sha256") != sha256_file(manifest_path):
            errors.append("signed package manifest hash mismatch")
        sig = base64.b64decode(record.get("signature", ""), validate=True)
        pub.verify(sig, canonical_json_bytes(manifest))
    except Exception as e:
        errors.append(f"package signature verification failed: {type(e).__name__}: {e}")
        fingerprint = record.get("public_key_fingerprint")
    return {"valid": not errors, "errors": errors, "public_key_fingerprint": fingerprint}
