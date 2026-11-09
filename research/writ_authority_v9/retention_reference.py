"""Independent, offline checker for fresh Writ/16 readback challenges.

The expected ACK fields, receiver key and challenge MUST come from the
independent verifier, never be adopted from the response under test.
This checker verifies a statement by the receiver; it does not make the
receiver honest, nor guarantee the file remains present after the challenge.
"""
from __future__ import annotations
import hashlib
import json
import re
from .destination_reference import check_ack, canonical, DestinationProofError

PROOF_DOMAIN=b'writ-v16/retention-proof\x00'
HEX32=re.compile('[0-9a-f]{32}\Z')
REQUIRED={'version','challenge','ack_hash','policy_hash','effect_id',
          'route_id','payload_digest','size','lease_nonce',
          'directory_identity','outcome'}

def check_fresh_readback(proof, signed_ack, pinned_public:bytes,
                         issued_nonce:str, expected:dict):
    """Check a fresh independent receiver signature and full source binding."""
    if type(issued_nonce) is not str or not HEX32.fullmatch(issued_nonce):
        raise DestinationProofError('untrusted verifier nonce')
    check_ack(signed_ack,pinned_public,expected)
    if type(proof) is not dict or set(proof)!={'body','signature'}:
        raise DestinationProofError('invalid readback proof envelope')
    body=proof['body']
    if type(body) is not dict or set(body)!=REQUIRED or \
       type(proof['signature']) is not str or len(proof['signature'])!=128:
        raise DestinationProofError('malformed retention proof')
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    from cryptography.exceptions import InvalidSignature
    try:
        Ed25519PublicKey.from_public_bytes(pinned_public).verify(
            bytes.fromhex(proof['signature']), PROOF_DOMAIN+canonical(body))
    except (ValueError,InvalidSignature,TypeError) as exc:
        raise DestinationProofError('receiver readback signature invalid') from exc
    ack=signed_ack['body']
    digest=hashlib.sha256(canonical(signed_ack)).hexdigest()
    expected_body={
        'version':'writ/retention-proof/1','challenge':issued_nonce,
        'ack_hash':digest,'policy_hash':ack['policy_hash'],
        'effect_id':ack['effect_id'],'route_id':ack['route_id'],
        'payload_digest':ack['digest'],'size':ack['size'],
        'lease_nonce':ack['nonce'],
        'directory_identity':ack['directory_identity'],
        'outcome':'present_at_challenge',
    }
    if any(type(body[k]) is not type(expected_body[k]) or
           body[k]!=expected_body[k] for k in REQUIRED):
        raise DestinationProofError('old nonce, changed bytes, or wrong acknowledgment')
    return True
