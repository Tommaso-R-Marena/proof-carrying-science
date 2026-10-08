"""PCS v3 receipt envelopes — construction, signing and an independent validity oracle.

This module is **not** part of the authority.  The authority is the Lean binary
``pcs-semantic-check --v3`` whose decision is proved (``PCS.V2.Semantic.V3.decideV3_certified_iff``)
to equal the declarative v3 contract.  This module provides:

* ``context_json`` / ``confirmation_statement`` / ``elaboration_statement`` /
  ``proof_statement`` — the exact canonical statements a receipt of each role must attest,
  re-implemented independently from the Lean definitions (``PCS.V2.ReceiptAuthorityV3``);
* ``sign_envelope`` — Ed25519 signing with the ``cryptography`` package (an implementation
  independent of the Lean verifier, used for fixtures and tests);
* ``test_key`` — the PUBLIC test seeds used for fixtures.  A receipt signed with a test key is
  evidence of nothing: it only exercises the verification path.  In particular a test-key
  "proof" receipt is **not** evidence that the Lean kernel checked anything;
* ``oracle_receipts_valid`` — an independent Python implementation of the declarative
  ``ReceiptsValid`` specification, used as a differential oracle against the binary.
"""

from __future__ import annotations

import base64
from typing import Any, Dict, Iterable, List, Optional, Tuple

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives import serialization

from .semantic_translation_v1 import canonical_json

PROTOCOL_VERSION = "pcs-receipt-v2"
ENVELOPE_TAG = b"pcs-semantic-receipt-v2\n"
KERNEL_CHECKER_ID = "lean4-kernel-check"
REQUEST_V3_SCHEMA = "pcs-semantic-translation-v3"
AUTHORITY_V3_SCHEMA = "pcs-semantic-authority-v3"
LEDGER_STATE_SCHEMA = "pcs-receipt-ledger-state-v3"
DECISION_V3_SCHEMA = "pcs-semantic-decision-v3"
ROLES = ("confirmation", "elaboration", "proof")


# --------------------------------------------------------------------------- keys

def seed_of(tag: str) -> bytes:
    """Same derivation as the Lean fixture writers: tag bytes, zero padded to 32 bytes."""
    return (tag.encode("latin-1") + bytes(32))[:32]


class TestKey:
    """A PUBLIC test key (fixtures only)."""

    def __init__(self, tag: str):
        self.tag = tag
        self._sk = Ed25519PrivateKey.from_private_bytes(seed_of(tag))
        pk = self._sk.public_key().public_bytes(serialization.Encoding.Raw,
                                                serialization.PublicFormat.Raw)
        self.public = base64.b64encode(pk).decode("ascii")

    def sign(self, msg: bytes) -> str:
        return base64.b64encode(self._sk.sign(msg)).decode("ascii")


def test_key(tag: str) -> TestKey:
    return TestKey(tag)


def verify(public_b64: str, msg: bytes, sig_b64: str) -> bool:
    try:
        pk = Ed25519PublicKey.from_public_bytes(base64.b64decode(public_b64, validate=True))
        pk.verify(base64.b64decode(sig_b64, validate=True), msg)
        return True
    except (InvalidSignature, ValueError, TypeError):
        return False


# --------------------------------------------------------------------------- statements

def context_json(authority: Dict[str, Any]) -> Dict[str, Any]:
    ctx = authority["context"]
    return {"env_fingerprint": ctx["env_fingerprint"], "registry": authority["registry"],
            "scope": ctx["scope"], "toolchain": ctx["toolchain"]}


def confirmation_statement(authority: Dict[str, Any], interpretation: Dict[str, Any]) -> Dict[str, Any]:
    return {"ambiguities": interpretation["ambiguities"], "context": context_json(authority),
            "purpose": "confirmation", "selected": interpretation["selected"],
            "source_text": interpretation["source_text"]}


def elaboration_statement(authority: Dict[str, Any], candidate: Dict[str, Any]) -> Dict[str, Any]:
    return {"context": context_json(authority), "decl_name": candidate["decl_name"],
            "lean_source": candidate["lean_source"], "purpose": "elaboration"}


def proof_statement(authority: Dict[str, Any], candidate: Dict[str, Any],
                    axioms: List[str]) -> Dict[str, Any]:
    return {"axioms": list(axioms), "checker": KERNEL_CHECKER_ID,
            "context": context_json(authority), "decl_name": candidate["decl_name"],
            "lean_source": candidate["lean_source"], "purpose": "kernel-proof-check"}


def strengthening_statement(authority: Dict[str, Any], interpretation: Dict[str, Any],
                            candidate: Dict[str, Any]) -> Dict[str, Any]:
    """Explicit authorization of a deliberate STRENGTHENING (``--v3-strengthen``); domain separated
    from an ordinary confirmation by its purpose and by binding the exact candidate claim."""
    return {"ambiguities": interpretation["ambiguities"], "candidate": candidate["claim"],
            "context": context_json(authority), "purpose": "strengthening-authorization",
            "selected": interpretation["selected"], "source_text": interpretation["source_text"]}


def expected_statement(authority: Dict[str, Any], request_v3: Dict[str, Any], role: str,
                       mode: str = "translation") -> Dict[str, Any]:
    base = request_v3["request"]["request"]
    if role == "confirmation" and mode == "strengthening":
        return strengthening_statement(authority, base["interpretation"], base["candidate"])
    if role == "confirmation":
        return confirmation_statement(authority, base["interpretation"])
    if role == "elaboration":
        return elaboration_statement(authority, base["candidate"])
    if role == "proof":
        return proof_statement(authority, base["candidate"], request_v3["proof_axioms"])
    raise ValueError(role)


# --------------------------------------------------------------------------- envelopes

def envelope_payload(env: Dict[str, Any]) -> Dict[str, Any]:
    return {k: env[k] for k in ("expires_at", "issued_at", "issuer", "nonce", "role",
                                "statement", "version")}


def envelope_bytes(env: Dict[str, Any]) -> bytes:
    """The signed bytes: domain tag followed by the canonical payload (all fields but the
    signature)."""
    return ENVELOPE_TAG + canonical_json(envelope_payload(env))


def sign_envelope(key: TestKey, role: str, statement: Dict[str, Any], nonce: str,
                  issued_at: int, expires_at: int, version: str = PROTOCOL_VERSION,
                  issuer: Optional[str] = None) -> Dict[str, Any]:
    env = {"expires_at": expires_at, "issued_at": issued_at,
           "issuer": key.public if issuer is None else issuer, "nonce": nonce, "role": role,
           "statement": statement, "version": version}
    env["signature"] = key.sign(envelope_bytes(env))
    return env


def resign(key: TestKey, env: Dict[str, Any]) -> Dict[str, Any]:
    env = dict(env)
    env["signature"] = key.sign(envelope_bytes(env))
    return env


# --------------------------------------------------------------------------- independent oracle

def active_keys(authority: Dict[str, Any], now: int, role: str) -> List[str]:
    return [k["key"] for k in authority["keys"]
            if k["role"] == role and k["not_before"] <= now < k["not_after"]]


def quorum(authority: Dict[str, Any], role: str) -> int:
    if role == "confirmation":
        return max(1, authority["confirmation_quorum"])
    if role == "elaboration":
        return max(1, authority["elaboration_quorum"]) if authority["require_elaboration"] else 0
    return max(1, authority["proof_quorum"]) if authority["require_proof"] else 0


def oracle_receipts_valid(authority: Dict[str, Any], request_v3: Dict[str, Any],
                          state: Dict[str, Any]) -> Tuple[bool, str]:
    """Independent implementation of the declarative ``ReceiptsValid`` predicate.

    Returns ``(valid, reason)``.  Used only as a test oracle; never as an authority."""
    now = state["now"]
    revoked = set(authority["revoked"]) | set(state["revoked"])
    consumed = set(state["consumed"])
    for ax in request_v3["proof_axioms"]:
        if ax not in authority["allowed_axioms"]:
            return False, "AXIOM_NOT_ALLOWED"
    envs = request_v3["receipts"]
    nonces = [e["nonce"] for e in envs]
    for e in envs:
        if e["issued_at"] < state["genesis"]:
            return False, "BEFORE_GENESIS"
        if e["version"] != PROTOCOL_VERSION:
            return False, "UNKNOWN_VERSION"
        if e["role"] not in ROLES:
            return False, "MALFORMED"
        if e["issuer"] not in active_keys(authority, now, e["role"]):
            return False, "UNAUTHORIZED_KEY"
        if e["issuer"] in revoked:
            return False, "REVOKED_KEY"
        if canonical_json(e["statement"]) != canonical_json(expected_statement(authority, request_v3, e["role"])):
            return False, "STATEMENT_MISMATCH"
        if not (e["issued_at"] <= now < e["expires_at"]):
            return False, "OUTSIDE_VALIDITY_WINDOW"
        if e["nonce"] in consumed:
            return False, "REPLAY"
        if not verify(e["issuer"], envelope_bytes(e), e["signature"]):
            return False, "BAD_SIGNATURE"
    if len(set(nonces)) != len(nonces):
        return False, "REPLAY"
    for role in ROLES:
        issuers = {e["issuer"] for e in envs if e["role"] == role}
        if len(issuers) < quorum(authority, role):
            return False, "QUORUM_NOT_MET"
    return True, "VALID"


def legacy_free(request_v2: Dict[str, Any]) -> Dict[str, Any]:
    """A v2 request with its stateless v1 receipts removed (v3 rejects them)."""
    r = dict(request_v2)
    base = dict(r["request"])
    base["confirmation"] = None
    base["elaboration"] = None
    base["proof"] = None
    r["request"] = base
    return r
