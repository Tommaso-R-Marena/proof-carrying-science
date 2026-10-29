"""Canonical, bounded data-only witness wire and receiver-pinned signatures."""
from __future__ import annotations

import hashlib
import json

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from research.authorization_history_v1 import history

PROTOCOL = "PCS-SCI-WITNESS-V1"
DOMAIN = b"PCS-SCI-WITNESS-V1\x00"
MAX_INTENT = 40000
MAX_REQUEST = 2 * MAX_INTENT + 1024
MAX_RESPONSE = 4 << 20
MAX_EVENTS = 32
MAX_DATABASE = 16 << 20
MAX_ARTIFACT = 8192


class Rejected(ValueError):
    pass


def canonical(value) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=True, allow_nan=False).encode("ascii")
    except (TypeError, ValueError, RecursionError) as exc:
        raise Rejected("Unencodable bounded JSON") from exc


def parse(raw: bytes, maximum=MAX_RESPONSE):
    if type(raw) is not bytes or len(raw) > maximum:
        raise Rejected("Bounded immutable wire required")
    # Bound nesting before invoking the JSON C parser, independently of any
    # imported package's process-global Python recursion limit.
    depth, quoted, escaped = 0, False, False
    for byte in raw:
        if quoted:
            if escaped: escaped = False
            elif byte == 92: escaped = True
            elif byte == 34: quoted = False
        elif byte == 34: quoted = True
        elif byte in (91, 123):
            depth += 1
            if depth > 32: raise Rejected("JSON nesting exceeds witness budget")
        elif byte in (93, 125): depth -= 1
    try:
        value = json.loads(raw)
        if canonical(value) != raw:
            raise Rejected("Noncanonical JSON")
        return value
    except (ValueError, TypeError, UnicodeError, RecursionError) as exc:
        raise Rejected("Invalid canonical JSON") from exc


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def unhex(value, *, length=None, maximum=MAX_INTENT) -> bytes:
    if (type(value) is not str or len(value) % 2 or len(value) > maximum * 2
            or any(c not in "0123456789abcdef" for c in value)):
        raise Rejected("Invalid bounded lowercase hex")
    raw = bytes.fromhex(value)
    if length is not None and len(raw) != length:
        raise Rejected("Wrong byte length")
    return raw


def root_id(root: history.Root) -> str:
    return digest(b"PCS-SCI-WITNESS-ROOT-V1\x00" + root.encode())


def anchor_json(anchor: history.Anchor) -> dict:
    return {"generation": anchor.generation, "incumbent": anchor.incumbent.hex(),
            "tip": anchor.tip.hex(), "chain_digest": anchor.chain_digest.hex()}


encode_anchor = anchor_json


def decode_anchor(value: dict) -> history.Anchor:
    if type(value) is not dict or set(value) != {"generation", "incumbent", "tip", "chain_digest"}:
        raise Rejected("Wrong checkpoint shape")
    if type(value["generation"]) is not int:
        raise Rejected("Generation must be an integer")
    return history.Anchor(value["generation"], unhex(value["incumbent"], maximum=MAX_ARTIFACT),
                          unhex(value["tip"]), unhex(value["chain_digest"], length=32))


def root_from_json(value: dict) -> history.Root:
    fields = {"format", "authority", "witness", "policy", "checker", "genesis_id",
              "genesis_incumbent", "genesis_generation"}
    if type(value) is not dict or set(value) != fields or value["format"] != "pcs-authorization-root-v1":
        raise Rejected("Wrong trusted root configuration")
    return history.Root(*(unhex(value[n]) for n in ("authority", "witness", "policy", "checker",
                                                   "genesis_id", "genesis_incumbent")),
                        value["genesis_generation"])


def sign(key, root: history.Root, kind: str, payload: dict, nonce=b"") -> dict:
    statement = {"protocol": PROTOCOL, "kind": kind, "root_id": root_id(root),
                 "checker": root.checker.hex(), "witness_key": key.public_key().public_bytes_raw().hex(),
                 "nonce": nonce.hex(), "payload": payload}
    return {"statement": statement, "signature": key.sign(DOMAIN + canonical(statement)).hex()}


def verify(envelope: dict, root: history.Root, public_key: bytes, *, kind: str,
           nonce: bytes = b"") -> dict:
    if type(envelope) is not dict or set(envelope) != {"statement", "signature"}:
        raise Rejected("Wrong signed response shape")
    s = envelope["statement"]
    if (type(s) is not dict or set(s) != {"protocol", "kind", "root_id", "checker", "witness_key", "nonce", "payload"}
            or s["protocol"] != PROTOCOL or s["kind"] != kind or s["root_id"] != root_id(root)
            or s["checker"] != root.checker.hex() or s["witness_key"] != public_key.hex()
            or s["nonce"] != nonce.hex() or type(s["payload"]) is not dict):
        raise Rejected("Wrong pinned response domain/root/profile/key/nonce")
    try:
        Ed25519PublicKey.from_public_bytes(public_key).verify(
            unhex(envelope["signature"], length=64), DOMAIN + canonical(s))
    except (InvalidSignature, ValueError) as exc:
        raise Rejected("Invalid witness signature") from exc
    return s["payload"]


def verify_statement(envelope, expected_pk, root, config=None, *, kind, nonce=b""):
    if config is not None:
        from research.scientific_history_v1.receiver import checker_identity
        if root.checker != checker_identity(config):
            raise Rejected("Verifier configuration does not match pinned root")
    return verify(envelope, root, expected_pk, kind=kind, nonce=nonce)


def checked_intent(raw: bytes) -> history.Envelope:
    if type(raw) is not bytes or len(raw) > MAX_INTENT:
        raise Rejected("Intent exceeds witness wire budget")
    try:
        e = history.Envelope.decode(raw)
        if (e.payload.certificate or len(e.payload.candidate) > MAX_ARTIFACT
                or len(e.payload.expected_incumbent) > MAX_ARTIFACT or len(e.payload.event_id) > 256):
            raise Rejected("Reserved certificate or oversized artifact")
        return e
    except history.Rejected as exc:
        raise Rejected("Invalid canonical intent") from exc


def advance(root, anchor, envelope, seen):
    """Fenced reuse of unchanged V1 signed-intent transition, not new authority.

    This research adapter intentionally depends on history._advance; its exact
    source is preserved and independently regression-tested. No V1 edit occurs.
    """
    try:
        return history._advance(root, anchor, envelope, seen)
    except history.Rejected as exc:
        raise Rejected(str(exc)) from exc
