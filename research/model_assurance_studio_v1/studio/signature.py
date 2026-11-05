"""Optional local Ed25519 publisher signatures for *unsigned research receipts*.

This authenticates a report to an independently pinned key, not scientific
adequacy, a complete audit trail, a runtime sandbox, or PCS Lean authority.
Keys are generated only on the user's machine, NEVER bundled in releases.
"""
from __future__ import annotations
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
from .verify_receipt import verify,replay_verify
from .engine import digest_json

SCHEMA='pcs-studio-receipt-signature-v0.5'


def _deps():
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey,Ed25519PublicKey
        from cryptography.hazmat.primitives.serialization import Encoding,PrivateFormat,PublicFormat,NoEncryption,load_pem_private_key
        from cryptography.exceptions import InvalidSignature
    except ImportError as exc:raise RuntimeError('Install cryptography>=44 first') from exc
    return Ed25519PrivateKey,Ed25519PublicKey,Encoding,PrivateFormat,PublicFormat,NoEncryption,load_pem_private_key,InvalidSignature


def fingerprint(raw_pub):return hashlib.sha256(raw_pub).hexdigest()


def generate_keypair(private_path:Path, public_path:Path):
    Ed25519PrivateKey,_,Encoding,PrivateFormat,PublicFormat,NoEncryption,*_=_deps()
    if private_path.resolve()==public_path.resolve():raise ValueError('private and public paths must differ')
    key=Ed25519PrivateKey.generate()
    private=key.private_bytes(Encoding.PEM,PrivateFormat.PKCS8,NoEncryption())
    public=key.public_key().public_bytes(Encoding.Raw,PublicFormat.Raw)
    # Exclusive creation: never silently overwrite existing keys.
    fd=os.open(private_path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    try:
        with os.fdopen(fd,'wb') as f:f.write(private)
        with public_path.open('xb') as f:f.write(key.public_key().public_bytes(Encoding.PEM,PublicFormat.SubjectPublicKeyInfo))
    except BaseException:
        # If public key creation failed, do not leave an unexpected private key.
        private_path.unlink(missing_ok=True)
        raise
    return fingerprint(public)


def signature_payload(receipt):
    return json.dumps(receipt,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('utf8')


def sign(receipt,artifact,key_pem):
    ok,msg=replay_verify(receipt,artifact)
    if not ok:raise ValueError('Refusing to sign receipt without fresh successful replay: '+msg)
    *_,load_pem_private_key,_=_deps()
    key=load_pem_private_key(key_pem,password=None)
    # No generic key types permitted: Ed25519 only.
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives.serialization import Encoding,PublicFormat
    if not isinstance(key,Ed25519PrivateKey):raise ValueError('Only Ed25519 private keys supported')
    pub=key.public_key().public_bytes(Encoding.Raw,PublicFormat.Raw)
    signature=key.sign(signature_payload(receipt))
    return {'schema':SCHEMA,'algorithm':'Ed25519',
            'public_key_raw_b64':base64.b64encode(pub).decode('ascii'),
            'public_key_sha256':fingerprint(pub),
            'receipt_sha256':receipt['receipt_sha256'],
            'artifact_sha256':receipt['sha256'],
            'signature_b64':base64.b64encode(signature).decode('ascii'),
            'limits':'Producer signature over exact unsigned research receipt; not a Lean verification certificate'}


def verify_signature(envelope,receipt,artifact,expected_fingerprint,*,replay=True):
    if not isinstance(expected_fingerprint,str) or len(expected_fingerprint)!=64:
        return False,'expected public-key fingerprint required (obtain out of band)'
    try:
        _,Ed25519PublicKey,*other=_deps()
        if not isinstance(envelope,dict) or set(envelope)!={'schema','algorithm','public_key_raw_b64','public_key_sha256',
                       'receipt_sha256','artifact_sha256','signature_b64','limits'}:
            return False,'signature envelope schema mismatch'
        if envelope['schema']!=SCHEMA or envelope['algorithm']!='Ed25519':
            return False,'unknown signature algorithm/schema'
        pub=base64.b64decode(envelope['public_key_raw_b64'],validate=True)
        sig=base64.b64decode(envelope['signature_b64'],validate=True)
        if len(pub)!=32 or len(sig)!=64:return False,'invalid Ed25519 sizes'
        actual=fingerprint(pub)
        import hmac
        if not hmac.compare_digest(actual,expected_fingerprint.lower()):return False,'signer fingerprint does not match independent trust pin'
        if envelope['public_key_sha256']!=actual:return False,'envelope fingerprint inconsistent'
        if envelope['receipt_sha256']!=receipt.get('receipt_sha256') or envelope['artifact_sha256']!=receipt.get('sha256'):
            return False,'envelope mismatches report or artifact'
        Ed25519PublicKey.from_public_bytes(pub).verify(sig,signature_payload(receipt))
        correct,msg=(replay_verify if replay else verify)(receipt,artifact)
        if not correct:return False,'receipt verification failed: '+msg
        return True,'Ed25519 signature valid for independently pinned key; '+msg
    except Exception as e:
        # Avoid publishing key material/exception details in output.
        return False,'signature verification failed: '+type(e).__name__


def main():
    ap=argparse.ArgumentParser(description='PCS Studio v0.5 publisher signatures (NOT Lean certificates)')
    sub=ap.add_subparsers(dest='command',required=True)
    init=sub.add_parser('init');init.add_argument('--private-key',required=True);init.add_argument('--public-key',required=True)
    sig=sub.add_parser('sign');sig.add_argument('receipt');sig.add_argument('artifact');sig.add_argument('--private-key',required=True);sig.add_argument('--output',required=True)
    ver=sub.add_parser('verify');ver.add_argument('envelope');ver.add_argument('receipt');ver.add_argument('artifact');ver.add_argument('--expected-fingerprint',required=True);ver.add_argument('--digest-only',action='store_true')
    args=ap.parse_args()
    if args.command=='init':
        print('Public key SHA-256 fingerprint (pin out of band):',generate_keypair(Path(args.private_key),Path(args.public_key)))
    elif args.command=='sign':
        receipt=json.loads(Path(args.receipt).read_text('utf8'))
        sidecar=sign(receipt,Path(args.artifact).read_bytes(),Path(args.private_key).read_bytes())
        with Path(args.output).open('x',encoding='utf8') as f:json.dump(sidecar,f,sort_keys=True,indent=2)
        print('Publisher signature sidecar created; pin fingerprint independently:',sidecar['public_key_sha256'])
    else:
        envelope=json.loads(Path(args.envelope).read_text('utf8'))
        receipt=json.loads(Path(args.receipt).read_text('utf8'))
        ok,msg=verify_signature(envelope,receipt,Path(args.artifact).read_bytes(),args.expected_fingerprint,replay=not args.digest_only)
        print(('ACCEPTED: ' if ok else 'REJECTED: ')+msg)
        return 0 if ok else 1
    return 0

if __name__=='__main__':raise SystemExit(main())
