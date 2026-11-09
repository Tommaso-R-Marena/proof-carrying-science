"""Reproduce the exact false-discovery rate under feedback misspecification."""
from fractions import Fraction
from pathlib import Path
import json
from research.evidencekernel_feedback_v22.kernel import (
    audit,design,digest,evidence_commitment,world_law,score,load_strict)

HERE=Path(__file__).parent
p=load_strict(HERE/'example_protocol.json')
p['allocation_weights_by_state']=[[19,1],[1,19]]
d=design(p)
Y=((1,1),(0,0),(1,1),(0,0))  # sharp zero-effect null
R=((0,0),(1,1),(0,0),(0,0))  # fixed surrogate reports differ
mu_truth_wrong=world_law(d,Y)
mu_actual=world_law(d,R)
alpha=Fraction(1,20)
naive=Fraction(0);correct=Fraction(0)
for z,pr in mu_actual.items():
    observed=score(Y,z)
    mistaken_p=sum((mass for a,mass in mu_truth_wrong.items()
                   if score(Y,a)>=observed),Fraction(0))
    if mistaken_p<=alpha:
        naive+=pr
    e={'assignments':list(z),'reports':[R[i][z[i]] for i in range(d['n'])],
       'true_intervals':[str(Y[i][z[i]]) for i in range(d['n'])]}
    pin=digest(p)
    report=audit(p,e,protocol_pin=pin,evidence_pin=evidence_commitment(pin,e))
    if report['conditional_p'] is not None and Fraction(report['conditional_p'])<=alpha:
        correct+=pr
assert naive==Fraction(158897,160000),naive
assert correct==Fraction(6859,160000),correct
result={'type':'synthetic_sharp_null_no_treatment_effect',
        'units':d['n'],'true_potential_outcomes':Y,'potential_reports':R,
        'nominal_alpha':str(alpha),'naive_false_positive_probability':str(naive),
        'robust_false_positive_probability':str(correct),
        'robust_at_or_below_nominal':correct<=alpha,
        'warning':'Exact toy-model falsification, not an external trial or a novelty claim.'}
print(json.dumps(result,indent=2))
