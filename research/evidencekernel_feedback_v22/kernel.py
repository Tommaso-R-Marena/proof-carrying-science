"""Exact potential-report-aware response-adaptive inference.

Research-only: finite-population, binary outcomes, deterministic potential reports,
externally committed response-adaptive treatment policy. Not a PCS authority.

For every compatible pair (Y,R), Y is the binary scientific potential-outcome
schedule and R is a distinct binary potential-report schedule, whose realized
reports drive the randomization policy. The exact distribution of assignments
is reconstructed under R, *not* silently reconstructed under Y.
"""
from __future__ import annotations
import argparse
from functools import lru_cache
from fractions import Fraction
from itertools import product
import json
from hashlib import sha256
from pathlib import Path

FORMAT = 'pcs-evidencekernel-feedback-v22'
FIELDS = {'format','n','states','initial_state','allocation_weights_by_state',
          'next_state_by_state_action_report','observation_model',
          'null_ate_upper','confidence_alpha','max_interval_misses',
          'statistic','inference_rule'}
EVIDENCE_FIELDS = {'assignments','reports','true_intervals'}
MODEL = 'unrestricted_deterministic_binary_potential_reports'
STAT = 'sample_mean_difference_integer'
RULE = 'exact_robust_potential_report_randomization'

class Reject(ValueError):
    pass

def insist(ok: bool, msg: str) -> None:
    if not ok: raise Reject(msg)

def exact_keys(x, fields, label):
    insist(type(x) is dict and set(x)==set(fields), f'{label}: unexpected/missing fields')

def digest(x):
    return sha256(json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False,
                             ensure_ascii=True).encode('utf-8')).hexdigest()

def load_strict(path):
    raw=Path(path).read_bytes()
    insist(len(raw)<=1_000_000,'oversized JSON')
    def pairs(ps):
        out={}
        for k,v in ps:
            insist(k not in out,'duplicate JSON key')
            out[k]=v
        return out
    def bad_float(_):raise Reject('JSON decimals prohibited')
    return json.loads(raw.decode('utf-8'),object_pairs_hook=pairs,
                      parse_float=bad_float,parse_constant=bad_float)

def rational(x):
    insist(type(x) is str and len(x)<=32,'invalid rational string')
    try: v=Fraction(x)
    except (ValueError,ZeroDivisionError) as e: raise Reject('invalid rational') from e
    insist(str(v)==x,'noncanonical rational')
    return v

def design(p):
    exact_keys(p,FIELDS,'protocol')
    insist(p['format']==FORMAT and p['observation_model']==MODEL and
           p['statistic']==STAT and p['inference_rule']==RULE,'unsupported policy')
    n=p['n']; S=p['states']; init=p['initial_state']; K=p['max_interval_misses']
    insist(type(n) is int and 2<=n<=5,'bounded research units: 2-5')
    insist(type(S) is int and 1<=S<=6,'invalid states')
    insist(type(init) is int and 0<=init<S,'invalid initial state')
    insist(type(K) is int and 0<=K<=n,'invalid missed interval budget')
    alpha=rational(p['confidence_alpha']); null=rational(p['null_ate_upper'])
    insist(0<alpha<1 and -1<=null<=1,'invalid alpha or null')
    weights=p['allocation_weights_by_state']
    transitions=p['next_state_by_state_action_report']
    insist(type(weights) is list and len(weights)==S and
           type(transitions) is list and len(transitions)==S,'invalid state rows')
    w=[]
    for s in range(S):
        row=weights[s]; tr=transitions[s]
        insist(type(row) is list and len(row)==2 and
               all(type(v) is int and 0<=v<=10000 for v in row) and sum(row)>0,
               'invalid treatment weights')
        insist(type(tr) is list and len(tr)==2 and
               all(type(v) is list and len(v)==2 and
                   all(type(t) is int and 0<=t<S for t in v) for v in tr),
               'invalid state transition')
        w.append((Fraction(row[0],sum(row)),Fraction(row[1],sum(row))))
    return dict(n=n,S=S,init=init,w=w,trans=transitions,K=K,alpha=alpha,null=null)

def validate(p,e,d,protocol_pin,evidence_pin):
    for pin in (protocol_pin,evidence_pin):
        insist(type(pin) is str and len(pin)==64 and
               all(c in '0123456789abcdef' for c in pin),'externally supplied hash pin required')
    insist(digest(p)==protocol_pin,'protocol pin mismatch')
    insist(digest({'domain':'pcs-evidencekernel-v22-outcome-feedback-evidence',
                   'protocol_sha256':protocol_pin,'evidence':e})==evidence_pin,
           'evidence pin mismatch')
    exact_keys(e,EVIDENCE_FIELDS,'evidence')
    n=d['n']
    a=e['assignments']; r=e['reports']; y=e['true_intervals']
    insist(type(a) is list and len(a)==n and all(type(v) is int and v in (0,1) for v in a),
           'invalid assigned treatments')
    insist(type(r) is list and len(r)==n and all(type(v) is int and v in (0,1) for v in r),
           'invalid policy-driving reports')
    insist(type(y) is list and len(y)==n and all(type(v) is str and v in ('0','1','01') for v in y),
           'invalid scientific outcome intervals')
    s=d['init']
    states=[];prob=Fraction(1)
    for i in range(n):
        states.append(s)
        insist(d['w'][s][a[i]]>0,'impossible treatment under reported state')
        prob*=d['w'][s][a[i]]
        s=d['trans'][s][a[i]][r[i]]
    return tuple(a),tuple(r),tuple(y),states,prob

def evidence_commitment(protocol_pin,evidence):
    return digest({'domain':'pcs-evidencekernel-v22-outcome-feedback-evidence',
                   'protocol_sha256':protocol_pin,'evidence':evidence})

def world_law(d,report_world):
    """Exact distribution of full treatment allocations conditional on fixed R."""
    output={}
    def rec(i,state,vector,prob):
        if i==d['n']:
            output[vector]=prob;return
        for action in (0,1):
            q=d['w'][state][action]
            if q:
                r=report_world[i][action]
                next_state=d['trans'][state][action][r]
                rec(i+1,next_state,vector+(action,),prob*q)
    rec(0,d['init'],(),Fraction(1))
    insist(sum(output.values(),Fraction(0))==1,'report-world design does not normalize')
    return output

def score(true_world,vector):
    """n0*n1 times treated-minus-control sample-mean difference; zero on empty arm."""
    n=len(vector);n1=sum(vector);n0=n-n1
    if not n0 or not n1:return 0
    a=sum(true_world[i][1] for i in range(n) if vector[i])
    b=sum(true_world[i][0] for i in range(n) if not vector[i])
    return n0*a - n1*b

def compatible_reports(observed_a,observed_r):
    """All fixed potential reporter schedules consistent with observed reports."""
    n=len(observed_a)
    for hidden in product((0,1),repeat=n):
        yield tuple((observed_r[i],hidden[i]) if observed_a[i]==0 else
                    (hidden[i],observed_r[i]) for i in range(n))

def compatible_truth(observed_a,labels,K):
    n=len(observed_a)
    for code in product(range(4),repeat=n):
        y=tuple((x//2,x%2) for x in code)
        misses=sum(labels[i]!='01' and labels[i]!=str(y[i][observed_a[i]])
                   for i in range(n))
        if misses<=K:yield y

def null_curve(d,a,labels,reports):
    n=d['n']; null_max={};witnesses={};model_count=0
    obs_ate_values=set()
    true_models=list(compatible_truth(a,labels,d['K']))
    insist(true_models,'no scientific potential outcomes compatible with intervals')
    for reports_world in compatible_reports(a,reports):
        law=world_law(d,reports_world)
        mass=law.get(a,Fraction(0))
        insist(mass>0,'observed assignment impossible for potential-report completion')
        for true_world in true_models:
            h=sum(v1-v0 for v0,v1 in true_world)
            actual=score(true_world,a)
            tail=sum((prob for z,prob in law.items() if score(true_world,z)>=actual),
                     Fraction(0))
            if tail>null_max.get(h,Fraction(-1)):
                null_max[h]=tail
                witnesses[h]={'report_world':[list(x) for x in reports_world],
                              'true_world':[list(x) for x in true_world]}
            model_count+=1
            obs_ate_values.add(h)
    worst=Fraction(-1);curve=[];achieved=None
    for h in range(-n,n+1):
        worst=max(worst,null_max.get(h,Fraction(-1)))
        feasible=worst>=0
        if feasible and worst>d['alpha'] and achieved is None:
            achieved=Fraction(h,n)
        curve.append({'ate_upper':str(Fraction(h,n)),
                      'null_feasible':feasible,
                      'max_p':str(worst) if feasible else None})
    return curve,achieved,model_count,witnesses

def audit(p,e,*,protocol_pin,evidence_pin):
    d=design(p)
    a,reports,labels,states,prob=validate(p,e,d,protocol_pin,evidence_pin)
    curve,lower,models,witnesses=null_curve(d,a,labels,reports)
    target=max(i for i,v in enumerate(curve) if Fraction(v['ate_upper'])<=d['null'])
    selected=curve[target]
    return {'format':'pcs-evidencekernel-response-adaptive-audit-v22',
            'status':'CONDITIONALLY_VERIFIED' if selected['null_feasible'] else 'NULL_INCOMPATIBLE',
            'conditional_p':selected['max_p'],
            'conditional_lower_ate':str(lower) if lower is not None else None,
            'null_ate_upper':str(d['null']),
            'confidence_alpha':str(d['alpha']),
            'compatible_joint_worlds':models,
            'actual_assignment_probability_given_observed_feedback':str(prob),
            'state_trace':states,'null_curve':curve,
            'protocol_sha256':protocol_pin,'evidence_sha256':evidence_pin,
            'warning':('Research-only. Inference conditions on fixed complete potential-outcome and '
                       'potential-report schedules, sequential independent assignment randomness, '
                       'protocol pin before enrollment, and complete retained reports; physical '
                       'authenticity and potential-outcome stability are not established by hashes.')}

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('protocol');ap.add_argument('evidence')
    ap.add_argument('--protocol-pin',required=True);ap.add_argument('--evidence-pin',required=True)
    args=ap.parse_args()
    try:
        result=audit(load_strict(args.protocol),load_strict(args.evidence),
                     protocol_pin=args.protocol_pin,evidence_pin=args.evidence_pin)
    except (Reject,ValueError,TypeError,KeyError,OverflowError,OSError) as exc:
        ap.exit(2,'REJECTED: '+str(exc)+'\n')
    print(json.dumps(result,sort_keys=True,indent=2))
