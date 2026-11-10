"""Create deterministic SYNTHETIC fixed-cohort examples; never authenticates randomness."""
from __future__ import annotations
import json
from pathlib import Path
from random import Random
from .kernel import FORMAT, digest, evidence_digest, audit

TUNING = [dict(lambda_=x) for x in ('1/64','1/32','1/16','1/8')]

def protocol(n=512, min_enrollment=448, *, stop_enabled=True):
    states=3
    transitions=[[[ (s+a+r+1)%states for r in (0,1)] for a in (0,1)]
                 for s in range(states)]
    stop=[[[bool(stop_enabled and s==2 and a==1 and r==1)
            for r in (0,1)] for a in (0,1)] for s in range(states)]
    return {
        'format':FORMAT,'registered_units':n,'states':states,'initial_state':0,
        'allocation_weights_by_state':[[2,3],[3,2],[1,1]],
        'next_state_by_state_action_report':transitions,
        'stop_after_by_state_action_report':stop,'min_enrollment':min_enrollment,
        'confidence_alpha':'1/20','calibration_failure_bound':'1/100',
        'null_ate_upper':'0','max_interval_misses':2,
        'tuning':[{'lambda':v['lambda_'],'alpha_spend':'1/80',
                   'log_upper':'22/5','taylor_terms':16} for v in TUNING],
        'estimand':'fixed_registered_cohort_binary_ate',
        'assignment_model':'predictable_bernoulli_fresh_randomness',
        'interval_model':'binary_labels_with_max_misses',
        'stopping_rule':'registered_feedback_fsm'}

def generate(p,seed=153):
    rng=Random(seed)
    s=p['initial_state'];A=[];R=[];L=[]
    for i in range(p['registered_units']):
        w=p['allocation_weights_by_state'][s]
        a=int(rng.randrange(sum(w))>=w[0])
        # Deliberately noisy/unreliable reports that do not equal the true
        # synthetic outcome in general; only *prior* reports affect next p.
        r=int(rng.randrange(7)<(5 if a else 2))
        A.append(a);R.append(r);L.append('1' if a else '0')
        if i+1==p['registered_units'] or (i+1>=p['min_enrollment'] and
              p['stop_after_by_state_action_report'][s][a][r]):
            break
        s=p['next_state_by_state_action_report'][s][a][r]
    return {'assignments':A,'reports':R,'true_intervals':L}

def save(root, n=512, min_enrollment=448, stop_enabled=True, label='example'):
    root=Path(root)
    p=protocol(n,min_enrollment,stop_enabled=stop_enabled)
    e=generate(p)
    pp=digest(p);ep=evidence_digest(pp,e)
    (root/f'{label}_protocol.json').write_text(json.dumps(p,sort_keys=True,indent=2)+'\n')
    (root/f'{label}_evidence.json').write_text(json.dumps(e,sort_keys=True,indent=2)+'\n')
    (root/f'{label}_protocol_pin.txt').write_text(pp+'\n')
    (root/f'{label}_evidence_pin.txt').write_text(ep+'\n')
    report=audit(p,e,protocol_pin=pp,evidence_pin=ep)
    (root/f'{label}_report.json').write_text(json.dumps(report,sort_keys=True,indent=2)+'\n')
    return report

if __name__=='__main__':
    here=Path(__file__).parent
    print('Early stop:', save(here))
    print('Full horizon:', save(here,n=4096,min_enrollment=4096,stop_enabled=False,label='scale'))
