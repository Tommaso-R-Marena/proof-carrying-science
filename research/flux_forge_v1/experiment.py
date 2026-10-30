"""Deterministic bounded policy falsification with an independent Fraction oracle."""
from __future__ import annotations
import argparse
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path
import subprocess
import time

from pcs import scientific_workflow_v3 as model
from pcs.transport_trace_kernel_v1 import prepare
from research.flux_detective_v1.check import capture

ROOT=Path(__file__).resolve().parents[2]
SOURCES=['research/flux_detective_v1/engine.mjs','research/flux_detective_v1/forge.mjs',
 'research/flux_detective_v1/check.py','research/flux_forge_v1/fixtures.mjs',
 'research/flux_forge_v1/Transfer.lean','research/flux_forge_v1/experiment.py',
 'pcs/scientific_workflow_v3.py','pcs/transport_trace_kernel_v1.py',
 'pcs/transport_kernel_v1.py','pcs/scientific_contracts_v1.py','pcs/canonical_json.py','pcs/jsonio.py']


def run(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    started=time.monotonic()
    frozen={name:(ROOT/name).read_bytes() for name in SOURCES}
    source_hashes={name:hashlib.sha256(raw).hexdigest() for name,raw in frozen.items()}
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    fixture_raw=subprocess.check_output(['node',str(Path(__file__).with_name('fixtures.mjs'))],cwd=ROOT,timeout=60)
    (out/'inputs.json').write_bytes(fixture_raw)
    items=json.loads(fixture_raw);assert len(items)==1296
    records=[];unique={}
    policies={name:dict(accepted=0,model_violations_accepted=0) for name in ('summaries','stronger_energy','exact_model')}
    for item in items:
        cbytes,csv=capture(json.dumps(item['bundle']).encode());d=prepare(cbytes,csv)
        c=model.load_contract(cbytes);matrix=model.transition_matrix(c)
        states=[[F(x) for x in row] for row in d['states']]
        assert list(map(F,d['times']))==[k*F(d['dt']) for k in range(c['steps']+1)]
        volumes=[F(x['volume']) for x in c['cells']]
        truth=[[F(x['initial_concentration']) for x in c['cells']]]
        for _ in range(c['steps']):truth.append([sum(p*x for p,x in zip(row,truth[-1])) for row in matrix])
        energy=lambda row:sum(v*x*x for v,x in zip(volumes,row))
        mass=lambda row:sum(v*x for v,x in zip(volumes,row))
        lo,hi=min(truth[0]),max(truth[0])
        summaries=(all(mass(row)==mass(truth[0]) for row in states) and all(lo<=x<=hi for row in states for x in row)
          and all(energy(a)>=energy(b) for a,b in zip(states,states[1:])))
        stronger=summaries and energy(states[-1])<=energy(truth[-1])
        exact=states==truth
        assert stronger==item['summary']['stronger'] and exact==item['summary']['exact_model']
        assert exact==(F(item['summary']['amount'])==0)
        accepted=dict(summaries=summaries,stronger_energy=stronger,exact_model=exact)
        for name,okay in accepted.items():
            policies[name]['accepted']+=okay
            policies[name]['model_violations_accepted']+=okay and not exact
        key=(hashlib.sha256(cbytes).hexdigest(),hashlib.sha256(csv).hexdigest())
        record=dict(seed=item['seed'],level=item['level'],left=item['left'],right=item['right'],
          amount=item['summary']['amount'],contract_sha256=key[0],trajectory_sha256=key[1],
          exact_model=exact,policies=accepted,energy_delta=str(energy(states[-1])-energy(truth[-1])))
        records.append(record);unique[key]=record
    assert source_hashes=={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in SOURCES}
    assert head==subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    for name,source_raw in frozen.items():
        p=out/'sources'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(source_raw)
    unique_policies={name:dict(accepted=sum(r['policies'][name] for r in unique.values()),model_violations_accepted=sum(r['policies'][name] and not r['exact_model'] for r in unique.values())) for name in policies}
    result=dict(format='pcs-flux-forge-policy-experiment-v1',head=head,seeds=[0,20261021,4294967295],
      samples=len(records),unique_model_trajectory_pairs=len(unique),policies=policies,unique_policies=unique_policies,
      oracle='independent Python Fraction matrix evolution',source_sha256=source_hashes,inputs_sha256=hashlib.sha256(fixture_raw).hexdigest(),
      duplicate_samples_are_not_independent=True,kernel_checked=False,pcs_authority=False,empirical_validation=False,
      wall_seconds=time.monotonic()-started,results=records)
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    (out/'REPORT.md').write_text('# Bounded transfer policy falsification\n\n'+
      f"{len(records)} samples; {len(unique)} unique model/trajectory pairs. Seeds: 0, 20261021, 4294967295.\n\n"+
      '| Policy | Accepted samples | Model violations accepted |\n| --- | ---: | ---: |\n'+
      ''.join(f"| {name} | {r['accepted']} | {r['model_violations_accepted']} |\n" for name,r in policies.items())+
      '\nThese are synthetic, bounded, adversarially constructed inputs, with duplicate samples reported separately. '
      'They are not population error rates, independent trials, or kernel verdicts. '
      'A stricter energy threshold still cannot establish model correspondence. '
      'Selected exported controls are separately replayed with Lean in tests.\n')
    return result


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--out',type=Path,required=True);args=p.parse_args()
    r=run(args.out);print(json.dumps({k:r[k] for k in ('samples','unique_model_trajectory_pairs','policies','unique_policies','wall_seconds')}))


if __name__=='__main__':main()
