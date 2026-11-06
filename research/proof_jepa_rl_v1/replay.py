"""Verify retained artifact hashes and optionally kernel-replay every proof.

Hash integrity alone grants no mathematical/scientific authority. Replay uses
only existing PCS Lean interfaces, never success labels from the archive.
"""
from __future__ import annotations
import argparse
import gzip
import hashlib
import json
from pathlib import Path, PurePosixPath
from pcs.jsonio import strict_json_loads
from pcs.experimental.prover.ir import digest
from .data import replay_receipt, verifier_identity
from .experiment import LeanEnvironment

LIMIT=16_000_000

def read_json(path):
    opener=gzip.open if str(path).endswith('.gz') else open
    with opener(path,'rb') as stream: raw=stream.read(LIMIT+1)
    if len(raw)>LIMIT: raise ValueError('decoded artifact exceeds bound')
    return strict_json_loads(raw.decode('utf-8'))


def verify_manifest(directory):
    root=Path(directory).resolve()
    manifest=read_json(root/'SHA256.json')
    if manifest['format']!='pcs-proof-jepa-evidence-v1' or manifest['authority']!='NONE':
        raise ValueError('unsupported evidence manifest')
    for name,expected in manifest['files'].items():
        p=PurePosixPath(name)
        if p.is_absolute() or '..' in p.parts or '\\' in name:
            raise ValueError('invalid artifact path')
        target=(root/name).resolve()
        if not target.is_relative_to(root) or not target.is_file():
            raise ValueError('missing or escaping artifact')
        if type(expected['size']) is not int or not 0<=expected['size']<=LIMIT:
            raise ValueError('invalid artifact size')
        with target.open('rb') as stream: raw=stream.read(LIMIT+1)
        if len(raw)!=expected['size'] or hashlib.sha256(raw).hexdigest()!=expected['sha256']:
            raise ValueError('artifact digest/size mismatch: '+name)
    return manifest


def replay_all(directory,cache):
    root=Path(directory)
    verify_manifest(root)
    corpus=read_json(root/'training.json.gz')
    results=read_json(root/'results.json.gz')
    records={r['id']:r for r in read_json(root/'tasks.json')}
    env=LeanEnvironment(cache=cache,timeout=30)
    count=0
    try:
        identity=corpus['verifier']
        if verifier_identity(env)!=identity:
            raise ValueError('replay host verifier identity differs from recorded identity')
        for episode in corpus['episodes']:
            receipt=episode['result']['receipt']
            if receipt is not None:
                replay_receipt(env,episode,receipt,identity); count+=1
        for alternate in corpus['equivalence_evidence']:
            row=next(r for r in records.values() if alternate['goal_sha256']==digest(r['goal']))
            replay_receipt(env,row,alternate['renamed_receipt'],identity); count+=1
        for model in results['evaluations'].values():
            for row in model['test']['rows']:
                if row['receipt'] is not None:
                    replay_receipt(env,records[row['id']],row['receipt'],identity); count+=1
        return {'replayed_proofs':count,'physical_attempts':env.actual_calls,
                'authority':'NONE','scope':'Actual original-goal Lean kernel/axiom replay, not scientific validity'}
    finally: env.close()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--directory',required=True)
    p.add_argument('--cache')
    args=p.parse_args()
    if args.cache:
        print(json.dumps(replay_all(args.directory,args.cache),sort_keys=True))
    else:
        manifest=verify_manifest(args.directory)
        print(json.dumps({'verified_artifact_files':len(manifest['files']),'authority':'NONE'}))
if __name__=='__main__': main()
