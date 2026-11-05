"""Standalone finite-cover certificate replay for the screened real network subset.

Independent of the original test generator, but relies on the same interpreter,
not on Lean or an independently verified kernel. No general safety verdict.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from .verify_receipt import verify
from .dense_nn import screen_onnx,Unsupported
from .partition_proof import verify_certificate
from .engine import parse_policy

def verify_proof_from_receipt(receipt,artifact):
    ok,msg=verify(receipt,artifact)
    if not ok:return False,msg
    try:
        result=receipt['details']['partition_proof']
        if result['status']!='PROVED_CONDITIONALLY':return False,'report contains no closed partition certificate'
        spec=screen_onnx(artifact)
        policy=parse_policy(receipt['policy'])
        if not policy.get('enable_partition_proof'):return False,'partition not enabled in bound policy'
        return verify_certificate(spec,policy,result['certificate'])
    except (KeyError,TypeError,ValueError,Unsupported) as e:
        return False,'malformed/unsupported proof: '+type(e).__name__

def main():
    ap=argparse.ArgumentParser(description='Recompute proof leaves and cover for a signed or unsigned research receipt')
    ap.add_argument('receipt');ap.add_argument('artifact')
    args=ap.parse_args()
    ok,msg=verify_proof_from_receipt(json.loads(Path(args.receipt).read_text()),Path(args.artifact).read_bytes())
    print(('VALID CONDITIONAL REAL BOX PROOF: ' if ok else 'REJECTED: ')+msg)
    return 0 if ok else 1

if __name__=='__main__':raise SystemExit(main())
