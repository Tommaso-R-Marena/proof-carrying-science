from __future__ import annotations
import base64
import hashlib
import json
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from .hashing import canonical_json_bytes
from .jsonio import strict_json_load, StrictJSONError


class SignatureError(ValueError):
    pass


def generate_keypair(
    private_path: str | Path,
    public_path: str | Path,
    *,
    overwrite: bool = False,
) -> dict[str, str]:
    private_path = Path(private_path).resolve()
    public_path = Path(public_path).resolve()
    if private_path == public_path:
        raise SignatureError("private and public key paths must be different")
    existing = [str(p) for p in (private_path, public_path) if p.exists()]
    if existing and not overwrite:
        raise SignatureError(f"refusing to overwrite existing signing key material: {existing}")
    private_path.parent.mkdir(parents=True, exist_ok=True)
    public_path.parent.mkdir(parents=True, exist_ok=True)
    key = Ed25519PrivateKey.generate()
    pub = key.public_key()
    private_path.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    public_path.write_bytes(pub.public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo))
    try:
        private_path.chmod(0o600)
    except OSError:
        pass
    return {"private_key": str(private_path), "public_key": str(public_path), "fingerprint": public_key_fingerprint(pub)}


def _load_private(path: str | Path) -> Ed25519PrivateKey:
    key = serialization.load_pem_private_key(Path(path).read_bytes(), password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise SignatureError("private key is not Ed25519")
    return key


def _load_public(path: str | Path) -> Ed25519PublicKey:
    key = serialization.load_pem_public_key(Path(path).read_bytes())
    if not isinstance(key, Ed25519PublicKey):
        raise SignatureError("public key is not Ed25519")
    return key


def public_key_fingerprint(key: Ed25519PublicKey) -> str:
    raw = key.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return hashlib.sha256(raw).hexdigest()


def signature_payload(certificate: dict) -> dict:
    integrity = certificate.get("integrity_hash")
    if not isinstance(integrity, str) or len(integrity) != 64:
        raise SignatureError("certificate lacks a valid integrity_hash")
    return {
        "spec_version": certificate.get("spec_version"),
        "checker_version": certificate.get("checker_version"),
        "subject": certificate.get("subject"),
        "integrity_hash": integrity,
        "semantic_hash": certificate.get("semantic_hash"),
    }


def sign_certificate(certificate_path: str | Path, private_key_path: str | Path, output_path: str | Path) -> dict:
    # Import lazily to avoid coupling the module graph while ensuring every direct
    # API caller gets the same integrity/replay gate as the CLI.
    from .kernel import verify_certificate

    verified = verify_certificate(certificate_path)
    if not verified["valid"]:
        raise SignatureError(
            f"refusing to sign invalid certificate: {verified['errors']}"
        )
    try:
        cert = strict_json_load(certificate_path)
    except StrictJSONError as exc:
        raise SignatureError(str(exc)) from exc
    payload = signature_payload(cert)
    key = _load_private(private_key_path)
    pub = key.public_key()
    sig = key.sign(canonical_json_bytes(payload))
    record = {
        "signature_format": "pcs-ed25519-v1",
        "algorithm": "Ed25519",
        "public_key_fingerprint": public_key_fingerprint(pub),
        "payload": payload,
        "signature": base64.b64encode(sig).decode("ascii"),
    }
    Path(output_path).write_text(json.dumps(record, indent=2, sort_keys=True), encoding="utf-8")
    return record


def verify_signature(certificate_path: str | Path, signature_path: str | Path, public_key_path: str | Path) -> dict:
    try:
        cert = strict_json_load(certificate_path)
        record = strict_json_load(signature_path)
    except StrictJSONError as exc:
        return {"valid": False, "errors": [str(exc)], "public_key_fingerprint": None}
    try:
        expected_payload = signature_payload(cert)
    except SignatureError as exc:
        return {"valid": False, "errors": [str(exc)], "public_key_fingerprint": record.get("public_key_fingerprint")}
    errors: list[str] = []
    if record.get("signature_format") != "pcs-ed25519-v1":
        errors.append("unsupported signature format")
    if record.get("payload") != expected_payload:
        errors.append("signature payload does not match certificate")
    try:
        pub = _load_public(public_key_path)
        fingerprint = public_key_fingerprint(pub)
        if record.get("public_key_fingerprint") != fingerprint:
            errors.append("public key fingerprint mismatch")
        sig = base64.b64decode(record.get("signature", ""), validate=True)
        pub.verify(sig, canonical_json_bytes(expected_payload))
    except Exception as e:
        errors.append(f"signature verification failed: {type(e).__name__}: {e}")
    return {"valid": not errors, "errors": errors, "public_key_fingerprint": record.get("public_key_fingerprint")}
