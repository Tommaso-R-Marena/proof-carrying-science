"""Independent Writ/18 reference for first-claim-bound live evidence.

Review slice only. The offline verifier accepts a receiver statement about its
claimed journal, not proof that a dishonest receiver actually checked the
physical file. For local testing it can ALSO independently inspect original
first-claim bytes, ACK journal and current regular file.

None of these routines is imported by PCS production authority.
"""
from __future__ import annotations
import base64
import hashlib
import os
import re
import stat
from pathlib import Path
from .destination_reference import check_ack, canonical, hash_struct, DestinationProofError
from .receiver_readback_v16 import readback

DOMAIN18=b'writ-v18/retention-proof\x00'
HEX64=re.compile(r'[0-9a-f]{64}\Z')
FIELDS={'version','challenge','ack_hash','policy_hash','effect_id',
        'route_id','payload_digest','size','lease_nonce','directory_identity',
        'outcome','claim_link'}
ACK_FIELDS=('policy_hash','effect_id','action','sink','endpoint','route_id',
            'digest','size','nonce')

def claim_link(ack_body:dict)->str:
    return hash_struct({'kind':'writ/readback-claim-link/1',
                        'request':{k:ack_body[k] for k in ACK_FIELDS}})

def verify_claim_readback(proof:dict,ack:dict,receiver_public:bytes,
                          expected:dict,challenge:str)->dict:
    """Authenticity + canonical exact fields, with independently pinned intent."""
    check_ack(ack,receiver_public,expected)
    if type(proof) is not dict or set(proof)!={'body','signature'}:
        raise DestinationProofError('invalid claim-readback envelope')
    body=proof['body']
    if type(body) is not dict or set(body)!=FIELDS:
        raise DestinationProofError('invalid strict claim-readback fields')
    if type(proof['signature']) is not str or len(proof['signature'])!=128:
        raise DestinationProofError('receiver claim-readback signature missing')
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    from cryptography.exceptions import InvalidSignature
    try:
        Ed25519PublicKey.from_public_bytes(receiver_public).verify(
            bytes.fromhex(proof['signature']),DOMAIN18+canonical(body))
    except (ValueError,TypeError,InvalidSignature) as exc:
        raise DestinationProofError('receiver claim-readback signature invalid') from exc
    a=ack['body']
    required={'version':'writ/retention-proof/2',
              'challenge':challenge,'ack_hash':hash_struct(ack),
              'policy_hash':a['policy_hash'],'effect_id':a['effect_id'],
              'route_id':a['route_id'],'payload_digest':a['digest'],
              'size':a['size'],'lease_nonce':a['nonce'],
              'directory_identity':a['directory_identity'],
              'outcome':'present_at_challenge','claim_link':claim_link(a)}
    if any(type(body[k]) is not type(v) or body[k]!=v for k,v in required.items()):
        raise DestinationProofError('wrong challenge, claim, ACK or payload binding')
    return body

def check_current_local_claim(directory:str|Path,ack:dict,pub:bytes,
                              expected:dict,payload:bytes)->bool:
    """Independently verify exact persisted first claim and current bytes.

    Caller holds trusted bytes and the original receiver key; the receiver's
    private directory must remain protected from concurrent untrusted writers.
    """
    readback(directory,ack,pub,expected)
    if type(payload) is not bytes or hashlib.sha256(payload).hexdigest()!=ack['body']['digest']:
        raise DestinationProofError('payload bytes do not match signed ACK')
    request={k:ack['body'][k] for k in ACK_FIELDS}
    request.update(version='writ/destination-request/1',
                   payload_b64=base64.b64encode(payload).decode('ascii'))
    claim={'version':'writ/receiver-claim/1',
           'effect_id':request['effect_id'],
           'request_hash':hash_struct(request),
           'digest':request['digest'],'lease_nonce':request['nonce']}
    name=f"writ-{request['effect_id']:012d}.claim.json"
    if not getattr(os,'O_NOFOLLOW',0) or not getattr(os,'O_DIRECTORY',0):
        raise DestinationProofError('strict no-follow POSIX filesystem required')
    d=os.open(Path(directory).resolve(strict=True),
              os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:
        fd=os.open(name,os.O_RDONLY|os.O_NOFOLLOW,dir_fd=d)
        with os.fdopen(fd,'rb') as f:
            info=os.fstat(f.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size>2048:
                raise DestinationProofError('claim is not a bounded regular file')
            raw=f.read(2049)
        if raw!=canonical(claim):
            raise DestinationProofError('first claim absent or differs from ACK')
    except OSError as exc:
        raise DestinationProofError('first claim missing or unsafe') from exc
    finally:
        os.close(d)
    return True
