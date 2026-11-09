"""Exact finite response-adaptive allocation AND report-driven stopping inference.

Research-only. This checks bounded calculations conditional on stable binary potential
scientific outcomes Y, stable *distinct* binary potential reports R, sequential
fresh randomization, an externally frozen stopping policy, and data custody.
It does not attest that these premises hold in a physical experiment.
"""
from __future__ import annotations
from fractions import Fraction
from itertools import product
from pathlib import Path
from hashlib import sha256
import json
import argparse

FORMAT = 'pcs-evidencekernel-stopping-v23'
RESULT = 'pcs-evidencekernel-stopping-audit-v23'
MODEL = 'fixed_binary_potential_truth_and_report_schedule'
RULE = 'exact_stopped_path_weak_null_maximization'
STAT = 'stopped_binary_mean_difference_integer'
KEYS = {'format','registered_units','states','initial_state',
        'allocation_weights_by_state','next_state_by_state_action_report',
        'stop_after_by_state_action_report','min_enrollment',
        'potential_schedule_model','statistic','inference_rule',
        'max_interval_misses','null_ate_upper','confidence_alpha'}
EKEYS = {'assignments','reports','true_intervals'}

class Reject(ValueError):pass

def insist(cond, msg):
    if not cond:raise Reject(msg)

def exact(o, fields, label):
    insist(type(o) is dict and set(o)==set(fields),label+': unexpected/missing fields')

def digest(o):
    return sha256(json.dumps(o,ensure_ascii=True,sort_keys=True,
                  separators=(',',':'),allow_nan=False).encode()).hexdigest()

def read(path):
    raw=Path(path).read_bytes()
    insist(len(raw)<=1_000_000,'oversized input')
    def pairs(rows):
        result={}
        for k,v in rows:
            insist(k not in result,'duplicate JSON key')
            result[k]=v
        return result
    def bad(x):raise Reject('noninteger JSON number')
    return json.loads(raw.decode('utf-8'),object_pairs_hook=pairs,
                      parse_float=bad,parse_constant=bad)

def fraction(raw):
    insist(type(raw) is str and 1<=len(raw)<=32,'invalid rational')
    try:x=Fraction(raw)
    except (ValueError,ZeroDivisionError) as exc:raise Reject('invalid rational') from exc
    insist(str(x)==raw,'noncanonical rational')
    return x

def design(p):
    exact(p,KEYS,'registration')
    insist(p['format']==FORMAT and p['potential_schedule_model']==MODEL and
           p['inference_rule']==RULE and p['statistic']==STAT,'unsupported registration')
    n=p['registered_units'];S=p['states'];initial=p['initial_state']
    min_t=p['min_enrollment'];K=p['max_interval_misses']
    insist(type(n) is int and 2<=n<=5,'registered_units must be 2..5')
    insist(type(S) is int and 1<=S<=5,'states must be 1..5')
    insist(type(initial) is int and 0<=initial<S,'invalid initial state')
    insist(type(min_t) is int and 2<=min_t<=n,'invalid minimum enrollment')
    insist(type(K) is int and 0<=K<=n,'invalid interval-miss allowance')
    alpha=fraction(p['confidence_alpha']);h=fraction(p['null_ate_upper'])
    insist(0<alpha<1 and -1<=h<=1,'invalid alpha/null')
    weights=p['allocation_weights_by_state'];transition=p['next_state_by_state_action_report'];stop=p['stop_after_by_state_action_report']
    insist(all(type(v) is list and len(v)==S for v in (weights,transition,stop)),
           'wrong state table size')
    probs=[]
    for s in range(S):
        w=weights[s]
        insist(type(w) is list and len(w)==2 and
               all(type(x) is int and 0<=x<=10000 for x in w) and sum(w)>0,
               'invalid allocation weights')
        probs.append((Fraction(w[0],sum(w)),Fraction(w[1],sum(w))))
        tr=transition[s];st=stop[s]
        insist(all(type(x) is list and len(x)==2 for x in (tr,st)),'invalid action table')
        for a in (0,1):
            insist(type(tr[a]) is list and len(tr[a])==2 and
                   all(type(x) is int and 0<=x<S for x in tr[a]),'invalid state transition')
            insist(type(st[a]) is list and len(st[a])==2 and
                   all(type(x) is bool for x in st[a]),'invalid stop rule')
    return {'n':n,'S':S,'initial':initial,'min':min_t,'K':K,'alpha':alpha,
            'h':h,'w':probs,'next':transition,'stop':stop}

def must_stop(d,t,s,a,r):
    return t==d['n'] or (t>=d['min'] and d['stop'][s][a][r])

def commitment(pin,e):
    return digest({'domain':'pcs-evidencekernel-v23-stopped-evidence',
                   'protocol_sha256':pin,'evidence':e})

def validate(p,e,d,pin,epin):
    for x in (pin,epin):
        insist(type(x) is str and len(x)==64 and all(c in '0123456789abcdef' for c in x),
               'external commitment required')
    insist(digest(p)==pin,'registration hash mismatch')
    insist(commitment(pin,e)==epin,'stopped-evidence hash mismatch')
    exact(e,EKEYS,'evidence')
    actions=e['assignments'];reports=e['reports'];intervals=e['true_intervals']
    t=len(actions) if type(actions) is list else -1
    insist(2<=t<=d['n'],'invalid stopped enrollment length')
    insist(type(reports) is list and len(reports)==t and
           type(intervals) is list and len(intervals)==t,'incomplete stopped records')
    insist(all(type(x) is int and x in (0,1) for x in actions+reports),
           'invalid treatment or report bit')
    insist(all(type(x) is str and x in ('0','1','01') for x in intervals),
           'invalid outcome intervals')
    s=d['initial'];states=[];prob=Fraction(1)
    for i,(a,r) in enumerate(zip(actions,reports),1):
        states.append(s)
        q=d['w'][s][a];insist(q>0,'zero-probability observed treatment')
        prob*=q
        stop=must_stop(d,i,s,a,r)
        if i<t:insist(not stop,'unreported earlier stop')
        else:insist(stop,'unregistered early stopping')
        s=d['next'][s][a][r]
    return tuple(actions),tuple(reports),tuple(intervals),states,prob

def law(d,R):
    """Complete probability distribution of all *terminal* treatment paths."""
    output={}
    def recurse(i,s,path,mass):
        for a in (0,1):
            q=d['w'][s][a]
            if not q:continue
            report=R[i][a];nxt=path+(a,);new=mass*q;t=i+1
            if must_stop(d,t,s,a,report):
                insist(nxt not in output,'duplicate terminal history')
                output[nxt]=new
            else:
                recurse(t,d['next'][s][a][report],nxt,new)
    recurse(0,d['initial'],(),Fraction(1))
    insist(sum(output.values(),Fraction(0))==1,'stopping law not normalized')
    return output

def statistic(Y,path):
    n1=sum(path);n0=len(path)-n1
    if not n1 or not n0:return 0
    treated=sum(Y[i][1] for i,a in enumerate(path) if a)
    controls=sum(Y[i][0] for i,a in enumerate(path) if not a)
    return n0*treated-n1*controls

def report_models(actions,reports,n):
    """No assumption on unobserved counterfactual or unenrolled reports."""
    t=len(actions)
    for digits in product(range(4),repeat=n):
        R=tuple((v//2,v%2) for v in digits)
        if all(R[i][actions[i]]==reports[i] for i in range(t)):
            yield R

def true_models(actions,intervals,n,K):
    t=len(actions)
    for digits in product(range(4),repeat=n):
        Y=tuple((v//2,v%2) for v in digits)
        misses=sum(intervals[i]!='01' and intervals[i]!=str(Y[i][actions[i]])
                   for i in range(t))
        if misses<=K:yield Y

def inference(d,actions,reports,intervals):
    # Fail closed before exponential enumeration exceeds a conservative work budget.
    R=list(report_models(actions,reports,d['n']))
    Y=list(true_models(actions,intervals,d['n'],d['K']))
    insist(R and Y,'no compatible truth or feedback completion')
    insist(len(R)*len(Y)*(1<<d['n'])<=8_000_000,
           'exact inference exceeds registered research work budget')
    observed=tuple(actions)
    scores=[(sum(b-a for a,b in y),statistic(y,observed)) for y in Y]
    best={};count=0;distribution_count=0
    for rep in R:
        p=law(d,rep)
        insist(p.get(observed,Fraction(0))>0,
               'recorded stopped history impossible for compatible reporting world')
        distribution_count+=1
        for y,(ate,obs) in zip(Y,scores):
            tail=sum((mass for path,mass in p.items() if statistic(y,path)>=obs),Fraction(0))
            if tail>best.get(ate,Fraction(-1)):
                best[ate]=tail
            count+=1
    peak=Fraction(-1);curve=[];lower=None
    for h in range(-d['n'],d['n']+1):
        peak=max(peak,best.get(h,Fraction(-1)))
        feasible=peak>=0
        if feasible and peak>d['alpha'] and lower is None:lower=str(Fraction(h,d['n']))
        curve.append({'ate_upper':str(Fraction(h,d['n'])),
                      'null_feasible':feasible,'max_p':str(peak) if feasible else None})
    target=max(i for i,x in enumerate(curve) if Fraction(x['ate_upper'])<=d['h'])
    return curve,curve[target],lower,count,distribution_count

def audit(p,e,*,protocol_pin,evidence_pin):
    d=design(p)
    actions,reports,intervals,states,observed_probability=validate(p,e,d,protocol_pin,evidence_pin)
    curve,target,lower,models,rmodels=inference(d,actions,reports,intervals)
    return {'format':RESULT,
            'status':'CONDITIONALLY_VERIFIED' if target['null_feasible'] else 'NULL_INCOMPATIBLE',
            'conditional_p':target['max_p'],
            'conditional_lower_ate':lower,
            'null_ate_upper':str(d['h']),'confidence_alpha':str(d['alpha']),
            'registered_units':d['n'],'enrolled_units':len(actions),
            'compatible_joint_worlds':models,'compatible_report_schedules':rmodels,
            'actual_stopped_history_probability_given_observed_reports':str(observed_probability),
            'state_trace':states,'null_curve':curve,
            'protocol_sha256':protocol_pin,'evidence_sha256':evidence_pin,
            'warning':('Conditional exact stopped-path inference, not proof of physical randomization, '
                       'external chronology, data authenticity, calibration, independent assignment '
                       'randomness or scientific effects. All potential scientific outcomes and policy '
                       'reports are modeled as fixed and stable across assignments.')}

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('protocol');ap.add_argument('evidence')
    ap.add_argument('--protocol-pin',required=True)
    ap.add_argument('--evidence-pin',required=True)
    arg=ap.parse_args()
    try:
        print(json.dumps(audit(read(arg.protocol),read(arg.evidence),
                              protocol_pin=arg.protocol_pin,evidence_pin=arg.evidence_pin),
                         indent=2,sort_keys=True))
    except (Reject,ValueError,TypeError,KeyError,OSError,OverflowError) as exc:
        ap.exit(2,'REJECTED: '+str(exc)+'\n')
