#!/usr/bin/env python3
"""Recheck explicit authored training labels; no final benchmark solutions."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pcs.experimental.prover.mathlib_environment_v4 import MathlibEnvironmentV4
from pcs.experimental.prover.premise_learning_v4 import collect_checked_training
from pcs.experimental.prover.benchmark_mathlib_v4 import check_partitions, read_json

def tasks():
    a=lambda k,x=None:{'kind':k,'argument':x}
    intro=lambda n:[a('intro','h'+str(i)) for i in range(n)]
    source=lambda family:{'repository':'Tommaso-R-Marena/proof-carrying-science','base_revision':'b59badd68cedba3dcc9c72a6d5148e7986545ebd','source_file':'scripts/collect_mathlib_training_v4.py','source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'authorship':'New PCS-authored supervised labels for existing mathematical facts; uncommitted source overlay','module':'Mathlib.Data.Set.Function' if family=='set_function' else 'Mathlib.Logic.Function.Basic'}
    rows=[]
    for op,lemma in [('∩','Set.preimage_inter'),('∪','Set.preimage_union'),('\\','Set.preimage_diff')]:
        statement=f"∀ (f : Nat → Nat) (s t : Set Nat), f ⁻¹' (s {op} t) = (f ⁻¹' s) {op} (f ⁻¹' t)"
        rows.append({'id':'train-'+lemma,'statement':statement,'actions':intro(3)+[a('apply_lemma',lemma)],'family':'set_function'})
    for statement,lemma,n in [("∀ (f : Nat → Nat) (s : Set Nat), f ⁻¹' sᶜ = (f ⁻¹' s)ᶜ",'Set.preimage_compl',2),("∀ (f : Nat → Nat), f ⁻¹' (∅ : Set Nat) = ∅",'Set.preimage_empty',1),("∀ (f : Nat → Nat), f ⁻¹' (Set.univ : Set Nat) = Set.univ",'Set.preimage_univ',1)]:
        rows.append({'id':'train-'+lemma,'statement':statement,'actions':intro(n)+[a('apply_lemma',lemma)],'family':'set_function'})
    rows.append({'id':'train-logic-projection','statement':'∀ (P Q R : Prop), (P ∧ Q) ∧ R → Q ∧ P','actions':intro(4)+[a('constructor'),a('exact_local','h3.1.2'),a('exact_local','h3.1.1')],'family':'logic'})
    rows.append({'id':'train-logic-composition','statement':'∀ (P Q R : Prop), (P → Q) → (Q → R) → P → R','actions':intro(6)+[a('apply_local','h4'),a('apply_local','h3'),a('exact_local','h5')],'family':'logic'})
    for row in rows:row.update({'split':'train','source':source(row['family']),'license':'CC0-1.0'})
    return rows

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);args=p.parse_args();out=Path(args.output)
    if out.exists():raise ValueError('Training evidence generation is immutable; choose a new output')
    out.mkdir(parents=True);inputs=tasks();(out/'authored-training-tasks.json').write_text(json.dumps(inputs,indent=2)+'\n')
    env=MathlibEnvironmentV4(timeout=12)
    try:
        print(json.dumps({'catalog':len(env.catalog),'source':env.source_sha256}),flush=True)
        before=env.calls;before_requests=env.worker_requests
        episodes=collect_checked_training(env,inputs)
        for task,episode in zip(inputs,episodes):task['expression']=episode['receipt']['kernel']['expression']
        with gzip.open(out/'checked-episodes-before-firewall.json.gz','wt') as f:json.dump(episodes,f)
        firewall=check_partitions(read_json(Path('benchmarks/mathlib-v4/tasks.json')),inputs)
        with gzip.open(out/'checked-episodes.json.gz','wt') as f:json.dump(episodes,f)
        with gzip.open(out/'catalog.json.gz','wt') as f:json.dump(env.catalog,f)
        (out/'firewall.json').write_text(json.dumps(firewall,indent=2)+'\n')
        (out/'collection.json').write_text(json.dumps({'episodes':len(episodes),'transitions':sum(len(e['records']) for e in episodes),'compiler_invocations':env.calls-before,'structured_worker_requests':env.worker_requests-before_requests,'catalog_sha256':env.catalog_sha256,'source_sha256':env.source_sha256,'public_authored_supervised_labels':True},indent=2)+'\n')
        print(json.dumps({'episodes':len(episodes),'transitions':sum(len(e['records']) for e in episodes),'firewall':firewall}),flush=True)
    finally:env.close()

if __name__=='__main__':main()
