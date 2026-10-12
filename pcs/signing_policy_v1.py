"""Optional authenticated key policy. This does not confer PCS scientific authority.

Trust anchors, a monotone revision floor, and the verifier clock are operator
configuration, never fields supplied by an artifact's producer. Historical
acceptance needs a separately signed observation of the exact envelope bytes.
Existing certificate signing/verification formats remain unchanged.
"""
from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from .canonical_json import canonicalize_jcs_bytes
from .jsonio import strict_json_loads
from .key_lifecycle import KeyLifecycleError, assess_signer, validate_registry
from .signing import public_key_fingerprint

POLICY_FORMAT = "pcs-signing-policy-v1"
OBJECT_FORMAT = "pcs-policy-bound-object-v1"
OBSERVATION_FORMAT = "pcs-signature-observation-v1"
MAX_BYTES = 1_048_576


class SigningPolicyError(ValueError):
    pass


def _time(value: Any) -> datetime:
    if not isinstance(value, str) or not value or len(value) > 64:
        raise SigningPolicyError("invalid timestamp")
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SigningPolicyError("invalid timestamp") from exc
    if stamp.tzinfo is None:
        raise SigningPolicyError("timestamp requires timezone")
    return stamp.astimezone(timezone.utc)


def _canonical(value: Any) -> bytes:
    try:
        encoded = canonicalize_jcs_bytes(value)
    except (ValueError, TypeError, RecursionError) as exc:
        raise SigningPolicyError("invalid canonical object") from exc
    if len(encoded) > MAX_BYTES:
        raise SigningPolicyError("policy object exceeds size limit")
    return encoded


def _fields(value: Any, expected: set[str]) -> None:
    if not isinstance(value, dict) or set(value) != expected:
        raise SigningPolicyError("unexpected policy object fields")


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _public(raw: str) -> Ed25519PublicKey:
    try:
        data = base64.b64decode(raw, validate=True)
        return Ed25519PublicKey.from_public_bytes(data)
    except (ValueError, TypeError) as exc:
        raise SigningPolicyError("invalid Ed25519 public key") from exc


def public_key_b64(key: Ed25519PublicKey) -> str:
    return base64.b64encode(key.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)).decode("ascii")


def _signed(payload: Mapping[str, Any], key: Ed25519PrivateKey) -> dict[str, Any]:
    raw = _canonical(dict(payload))
    return {"payload": dict(payload), "signer_fingerprint": public_key_fingerprint(key.public_key()),
            "signature": base64.b64encode(key.sign(b"PCS-SIGNING-POLICY-V1\0" + raw)).decode("ascii")}


def _verify(envelope: Any, public: Ed25519PublicKey) -> dict[str, Any]:
    _fields(envelope, {"payload", "signer_fingerprint", "signature"})
    if envelope["signer_fingerprint"] != public_key_fingerprint(public):
        raise SigningPolicyError("pinned public key fingerprint mismatch")
    if not isinstance(envelope["signature"], str) or len(envelope["signature"]) != 88:
        raise SigningPolicyError("invalid signature encoding")
    try:
        signature = base64.b64decode(envelope["signature"], validate=True)
        public.verify(signature, b"PCS-SIGNING-POLICY-V1\0" + _canonical(envelope["payload"]))
    except (ValueError, TypeError, InvalidSignature) as exc:
        raise SigningPolicyError("signature verification failed") from exc
    if not isinstance(envelope["payload"], dict):
        raise SigningPolicyError("signed payload must be an object")
    return envelope["payload"]


@dataclass(frozen=True)
class TrustAnchors:
    """Installed by a human-controlled verifier deployment, not the request."""
    root_public_key: Ed25519PublicKey
    observation_public_key: Ed25519PublicKey
    registry_id: str
    minimum_revision: int

    def __post_init__(self) -> None:
        if not isinstance(self.root_public_key, Ed25519PublicKey) or not isinstance(self.observation_public_key, Ed25519PublicKey):
            raise SigningPolicyError("trust anchors must be Ed25519")
        if public_key_fingerprint(self.root_public_key) == public_key_fingerprint(self.observation_public_key):
            raise SigningPolicyError("root and observation authorities must be distinct")
        if not isinstance(self.registry_id, str) or not self.registry_id.strip():
            raise SigningPolicyError("registry identity required")
        if type(self.minimum_revision) is not int or not 1 <= self.minimum_revision <= 2**31 - 1:
            raise SigningPolicyError("positive revision floor required")


@dataclass(frozen=True)
class AuthenticatedPolicy:
    """Canonical bytes prevent a caller mutating a checked dictionary in place."""
    canonical_envelope: bytes
    anchors: TrustAnchors

    @property
    def digest(self) -> str:
        return _sha(self.canonical_envelope)


def sign_policy(payload: Mapping[str, Any], root_key: Ed25519PrivateKey) -> dict[str, Any]:
    """Offline operator authoring helper; authentication/validation is separate."""
    return _signed(payload, root_key)


def authenticate_policy(envelope: Any, anchors: TrustAnchors, *, now: str) -> AuthenticatedPolicy:
    payload = _verify(envelope, anchors.root_public_key)
    _fields(payload, {"format", "revision", "issued_at", "valid_until", "registry", "authorities"})
    if payload["format"] != POLICY_FORMAT:
        raise SigningPolicyError("unsupported policy format")
    if type(payload["revision"]) is not int or not anchors.minimum_revision <= payload["revision"] <= 2**31 - 1:
        raise SigningPolicyError("policy revision rollback or invalid revision")
    moment, issued, until = _time(now), _time(payload["issued_at"]), _time(payload["valid_until"])
    if not issued <= moment < until:
        raise SigningPolicyError("policy not yet valid or expired")
    try:
        registry = validate_registry(payload["registry"])
    except (KeyLifecycleError, TypeError) as exc:
        raise SigningPolicyError("invalid lifecycle registry") from exc
    if registry["registry_id"] != anchors.registry_id:
        raise SigningPolicyError("registry identity mismatch")
    authorities = payload["authorities"]
    if not isinstance(authorities, list) or len(authorities) != len(registry["keys"]):
        raise SigningPolicyError("authority list does not cover registry exactly")
    seen: set[str] = set()
    root_fp = public_key_fingerprint(anchors.root_public_key)
    observer_fp = public_key_fingerprint(anchors.observation_public_key)
    entries = {item["public_key_fingerprint"]: item for item in registry["keys"]}
    for authority in authorities:
        _fields(authority, {"public_key", "fingerprint", "expires_at", "purpose"})
        key = _public(authority["public_key"])
        fingerprint = public_key_fingerprint(key)
        if authority["fingerprint"] != fingerprint or fingerprint not in entries or fingerprint in seen:
            raise SigningPolicyError("authority key substitution or duplicate")
        if fingerprint in {root_fp, observer_fp}:
            raise SigningPolicyError("producer cannot share root or observation authority")
        if not isinstance(authority["purpose"], str) or not 1 <= len(authority["purpose"]) <= 128:
            raise SigningPolicyError("bounded signing purpose required")
        entry = entries[fingerprint]
        spki = key.public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
        if entry["public_key_spki_sha256"] != _sha(spki):
            raise SigningPolicyError("authority SPKI mismatch")
        if _time(authority["expires_at"]) <= _time(entry["activated_at"]):
            raise SigningPolicyError("signing authority expiry must follow activation")
        for event in ("retired_at", "revoked_at"):
            if entry[event] is not None and _time(entry[event]) < _time(entry["activated_at"]):
                raise SigningPolicyError("lifecycle event predates activation")
        seen.add(fingerprint)
    return AuthenticatedPolicy(_canonical(envelope), anchors)


def _policy(policy: AuthenticatedPolicy, now: str) -> dict[str, Any]:
    # Reauthenticate even if a caller directly constructs the dataclass.
    value = strict_json_loads(policy.canonical_envelope.decode("utf-8"))
    authenticate_policy(value, policy.anchors, now=now)
    return value["payload"]


def _eligible(payload: dict[str, Any], fingerprint: str, *, moment: str, purpose: str, current: bool) -> dict[str, Any]:
    authority = next((item for item in payload["authorities"] if item["fingerprint"] == fingerprint), None)
    if authority is None or authority["purpose"] != purpose:
        raise SigningPolicyError("unknown signer or signing purpose mismatch")
    try:
        lifecycle = assess_signer(payload["registry"], fingerprint, signed_at=moment)
    except KeyLifecycleError as exc:
        raise SigningPolicyError("signer is not registered") from exc
    if not lifecycle["valid"] or (current and lifecycle["status"] != "ACTIVE"):
        raise SigningPolicyError("retired or revoked signing authority")
    if _time(moment) >= _time(authority["expires_at"]):
        raise SigningPolicyError("expired signing authority")
    return authority


def sign_object(content: bytes, private_key: Ed25519PrivateKey, policy: AuthenticatedPolicy, *, purpose: str, now: str) -> dict[str, Any]:
    """Signs exact content digest after current eligibility; not a checker call."""
    payload = _policy(policy, now)
    _eligible(payload, public_key_fingerprint(private_key.public_key()), moment=now, purpose=purpose, current=True)
    return _signed({"format": OBJECT_FORMAT, "content_sha256": _sha(content), "purpose": purpose,
                    "policy_revision": payload["revision"], "signed_at": now}, private_key)


def observe_object(envelope: Mapping[str, Any], observer_key: Ed25519PrivateKey, *, observed_at: str) -> dict[str, Any]:
    """Witness existence only. Operator must supply the real trusted clock."""
    _time(observed_at)
    return _signed({"format": OBSERVATION_FORMAT, "envelope_sha256": _sha(_canonical(dict(envelope))),
                    "observed_at": observed_at}, observer_key)


def verify_object(content: bytes, envelope: Any, policy: AuthenticatedPolicy, *, purpose: str, now: str,
                  historical_observation: Any = None) -> dict[str, Any]:
    """Returns cryptographic/policy eligibility only, never semantic correctness."""
    try:
        payload = _policy(policy, now)
        _fields(envelope, {"payload", "signer_fingerprint", "signature"})
        fingerprint = envelope["signer_fingerprint"]
        authority = next((item for item in payload["authorities"] if item["fingerprint"] == fingerprint), None)
        if authority is None:
            raise SigningPolicyError("signer is not registered")
        signed = _verify(envelope, _public(authority["public_key"]))
        _fields(signed, {"format", "content_sha256", "purpose", "policy_revision", "signed_at"})
        if signed["format"] != OBJECT_FORMAT or signed["content_sha256"] != _sha(content) or signed["purpose"] != purpose:
            raise SigningPolicyError("signed content or purpose mismatch")
        if type(signed["policy_revision"]) is not int or not 1 <= signed["policy_revision"] <= payload["revision"]:
            raise SigningPolicyError("signature policy revision is invalid")
        if _time(signed["signed_at"]) > _time(now):
            raise SigningPolicyError("future signature timestamp")
        moment = now
        mode = "current"
        if historical_observation is not None:
            observation = _verify(historical_observation, policy.anchors.observation_public_key)
            _fields(observation, {"format", "envelope_sha256", "observed_at"})
            if observation["format"] != OBSERVATION_FORMAT or observation["envelope_sha256"] != _sha(_canonical(envelope)):
                raise SigningPolicyError("historical observation binds different envelope")
            moment = observation["observed_at"]
            if not _time(signed["signed_at"]) <= _time(moment) <= _time(now):
                raise SigningPolicyError("historical observation time is inconsistent")
            mode = "historical_observed_existence"
        # Both the claimed signing time and trusted observation must lie in the
        # approved window. A claimed timestamp alone never enables history.
        _eligible(payload, fingerprint, moment=signed["signed_at"], purpose=purpose, current=False)
        _eligible(payload, fingerprint, moment=moment, purpose=purpose, current=historical_observation is None)
        return {"valid": True, "errors": [], "mode": mode, "policy_sha256": policy.digest,
                "policy_revision": payload["revision"], "content_sha256": _sha(content),
                "signer_fingerprint": fingerprint, "pcs_authority": False}
    except (SigningPolicyError, ValueError, TypeError, KeyError, AttributeError, RecursionError) as exc:
        return {"valid": False, "errors": [str(exc)], "pcs_authority": False}
