"""Deterministic synthetic demonstration, not independent randomized evidence."""
from __future__ import annotations
import json
from pathlib import Path
from research.evidencekernel_propensity_v25 import kernel as k

ROOT=Path(__file__).parent
PREV=ROOT.parent/'evidencekernel_anytime_v24'

def convert(p, *, upper=('31/50','21/50','13/25'), reference_only=False):
    p=json.loads(json.dumps(p))
    nominal=p.pop('allocation_weights_by_state')
    p['format']=k.FORMAT
    p['assignment_model']='predictable_bernoulli_upper_bounded_fresh_randomness'
    p['propensity_upper_by_state']=list(upper)
    if reference_only:
        p['tuning']=[{**t,'reference_weights_by_state':nominal} for t in p['tuning']]
    else:
        alt=[[19,31],[29,21],[12,13]]
        p['tuning']=[
          {**{**t,'alpha_spend':'1/160','log_upper':'26/5'},'reference_weights_by_state':strategy}
          for strategy in [nominal,alt] for t in p['tuning']
        ]
    return p

def main(root=ROOT):
    source=PREV
    p=convert(json.loads((source/'example_protocol.json').read_text()))
    e=json.loads((source/'example_evidence.json').read_text())
    pp=k.digest(p);ep=k.evidence_digest(pp,e)
    result=k.audit(p,e,protocol_pin=pp,evidence_pin=ep)
    files={'example_protocol.json':p,'example_evidence.json':e,'example_report.json':result}
    root.mkdir(parents=True,exist_ok=True)
    for name,value in files.items():
        (root/name).write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
    (root/'example_protocol_pin.txt').write_text(pp+'\n')
    (root/'example_evidence_pin.txt').write_text(ep+'\n')
    return result

if __name__=='__main__':
    print(json.dumps(main(),indent=2))
