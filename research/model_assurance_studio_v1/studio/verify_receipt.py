"""Validate unsigned PCS Studio v0.2–v0.6 receipts and optionally rerun checks.

Cryptographic digest agreement does not authenticate the producer. Replaying with
this package detects fabricated or stale findings but isn't an independent theorem
prover, a cryptographic signature, or a PCS v0.6 Lean-authoritative receipt.
"""
import argparse
import hashlib
import json
from pathlib import Path
from .engine import analyze, digest_json, parse_policy, VERSION

def verify(receipt: dict, artifact: bytes) -> tuple[bool,str]:
    if receipt.get('schema') not in ('pcs-model-intake-receipt-v0.2','pcs-model-intake-receipt-v0.3','pcs-model-intake-receipt-v0.4','pcs-model-intake-receipt-v0.5','pcs-model-intake-receipt-v0.6'):
        return False, 'unknown schema'
    claimed=receipt.get('receipt_sha256')
    if not isinstance(claimed,str) or len(claimed)!=64:
        return False,'receipt digest absent'
    payload={k:v for k,v in receipt.items() if k!='receipt_sha256'}
    try:
        if digest_json(payload)!=claimed:return False,'receipt digest mismatch'
        if receipt.get('sha256')!=hashlib.sha256(artifact).hexdigest():return False,'artifact digest mismatch'
        if receipt.get('bytes')!=len(artifact):return False,'artifact byte count mismatch'
        if receipt['schema'].endswith(('v0.3','v0.4','v0.5','v0.6')):
            policy=parse_policy(receipt.get('policy'))
            if digest_json(policy)!=receipt.get('policy_sha256'):
                return False,'embedded policy and policy digest disagree'
    except (TypeError,KeyError,ValueError) as exc:
        return False,'invalid receipt: '+type(exc).__name__
    return True,'artifact and unsigned receipt digests match; issuer/checker correctness NOT authenticated'

def replay_verify(receipt: dict, artifact: bytes) -> tuple[bool,str]:
    valid, msg=verify(receipt,artifact)
    if not valid:return False,msg
    if receipt['schema'] not in ('pcs-model-intake-receipt-v0.3','pcs-model-intake-receipt-v0.4','pcs-model-intake-receipt-v0.5','pcs-model-intake-receipt-v0.6'):
        return False,'legacy receipt has no embedded policy; cannot replay'
    if receipt.get('version')!=VERSION:
        return False,'different inspector version; reproducible replay requires matching code'
    try:
        fresh=analyze(receipt['filename'],artifact,receipt['policy'])
    except (ValueError,TypeError,KeyError) as exc:
        return False, 'reanalysis failed: '+type(exc).__name__
    if digest_json(fresh)!=digest_json(receipt):
        return False,'reanalysis differs from saved receipt; compare runtime and installed dependency versions'
    return True,'local reanalysis matches byte-for-byte canonical findings; this is NOT independent trusted verification'

def main():
    parser=argparse.ArgumentParser(description='Validate unsigned PCS model assessment')
    parser.add_argument('receipt')
    parser.add_argument('artifact')
    parser.add_argument('--replay',action='store_true',help='rerun all local checks under embedded policy')
    args=parser.parse_args()
    receipt=json.loads(Path(args.receipt).read_text())
    original=Path(args.artifact).read_bytes()
    ok,msg=(replay_verify if args.replay else verify)(receipt,original)
    print(('MATCH: ' if ok else 'FAILED: ')+msg)
    return 0 if ok else 1
if __name__=='__main__':raise SystemExit(main())
