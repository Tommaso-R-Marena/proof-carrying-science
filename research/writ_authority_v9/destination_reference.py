"""Independent reference checker for Writ/15 receiver-signed durable receipts.

Not imported by PCS production or the Writ gateway. A pinned receiver public
key is a separate trusted input, NOT supplied by the operator-signed receipt.
Successful verification attests what the receiver key *asserted*, not physical
truth, remote honesty, or Ed25519 correctness as a Lean theorem.
"""
from __future__ import annotations
import hashlib
import json
import re

DOMAIN = b"writ-v15/destination-receipt\x00"
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
HEX32 = re.compile(r"[0-9a-f]{32}\Z")
FIELDS = frozenset(("version","policy_hash","effect_id","action","sink","endpoint",
                     "route_id","digest","size","nonce","directory_identity","outcome"))

class DestinationProofError(ValueError):
    pass

def canonical(obj):
    return json.dumps(obj,sort_keys=True,separators=(",",":"),ensure_ascii=True,
                      allow_nan=False).encode("utf-8")

def hash_struct(obj):
    return hashlib.sha256(canonical(obj)).hexdigest()

def check_ack(envelope, receiver_public:bytes, expected:dict):
    """Check receiver signature and *all* independently supplied intent fields.

    expected must be derived from independently authenticated admission and
    lease records: policy_hash,effect_id,action,sink,endpoint,route_id,digest,
    size,nonce.  Never derive expected values from the proposed ack itself.
    """
    if not isinstance(envelope,dict) or set(envelope)!={"body","signature"}:
        raise DestinationProofError("invalid receiver envelope")
    body=envelope["body"]
    if not isinstance(body,dict) or set(body)!=FIELDS:
        raise DestinationProofError("noncanonical or incomplete receiver body")
    if type(receiver_public) is not bytes or len(receiver_public)!=32:
        raise DestinationProofError("missing pinned receiver public key")
    if not isinstance(envelope["signature"],str) or len(envelope["signature"])!=128:
        raise DestinationProofError("malformed receiver signature")
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        from cryptography.exceptions import InvalidSignature
        Ed25519PublicKey.from_public_bytes(receiver_public).verify(
            bytes.fromhex(envelope["signature"]),DOMAIN+canonical(body))
    except (ValueError,TypeError,InvalidSignature) as exc:
        raise DestinationProofError("invalid receiver signature") from exc
    if body["version"]!="writ/destination-receipt/1" or body["outcome"]!="durably_written":
        raise DestinationProofError("unrecognized receiver receipt")
    if type(body["effect_id"]) is not int or body["effect_id"]<=0:
        raise DestinationProofError("invalid effect id")
    if type(body["size"]) is not int or body["size"]<0 or body["size"]>262144:
        raise DestinationProofError("invalid byte count")
    if any(type(body[k]) is not str or not HEX64.fullmatch(body[k])
           for k in ("policy_hash","digest","route_id","directory_identity")):
        raise DestinationProofError("invalid digest")
    if type(body["nonce"]) is not str or not HEX32.fullmatch(body["nonce"]):
        raise DestinationProofError("missing lease nonce")
    if any(type(body[k]) is not str or not body[k] for k in ("action","sink","endpoint")):
        raise DestinationProofError("invalid action or endpoint")
    required={"policy_hash","effect_id","action","sink","endpoint","route_id","digest","size","nonce"}
    if not isinstance(expected,dict) or set(expected)!=required:
        raise DestinationProofError("expected trusted record is incomplete")
    for k,v in expected.items():
        if type(v) is not type(body[k]) or v!=body[k]:
            raise DestinationProofError(f"receiver {k} mismatches trusted intent")
    identity=hash_struct({"kind":"writ/destination-route/1","endpoint":body["endpoint"],
                          "receiver":receiver_public.hex(),
                          "directory":body["directory_identity"]})
    binding=hash_struct({"sink":body["sink"],"tool":"file",
                         "endpoint":body["endpoint"],"destination":identity})
    if binding!=body["route_id"]:
        raise DestinationProofError("receiver route/identity binding mismatches")
    return True
