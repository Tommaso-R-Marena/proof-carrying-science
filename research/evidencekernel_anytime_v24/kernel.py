"""V24 exact-rational anytime-safe inference for a fixed ordered finite cohort.

The theorem relies on sequentially correct *predictable* propensities, stable
binary potential outcomes, and a pre-fixed cohort. Reports may be stochastic,
noisy or adversarial, so long as next-treatment randomness is conditionally fresh.

This research implementation checks arithmetic, registered policy consistency,
and SHA256 bindings; it cannot attest chronology, real probabilities, or biology.
"""
from __future__ import annotations
import argparse
from fractions import Fraction
from hashlib import sha256
import json
from pathlib import Path

FORMAT = 'pcs-evidencekernel-predictable-anytime-v24'
RESULT = 'pcs-evidencekernel-predictable-anytime-audit-v24'
FIELDS = {'format','registered_units','states','initial_state',
          'allocation_weights_by_state','next_state_by_state_action_report',
          'stop_after_by_state_action_report','min_enrollment',
          'confidence_alpha','calibration_failure_bound','null_ate_upper',
          'max_interval_misses','tuning','estimand','assignment_model',
          'interval_model','stopping_rule'}
EVIDENCE = {'assignments','reports','true_intervals'}
TUNE = {'lambda','alpha_spend','log_upper','taylor_terms'}

class Reject(ValueError):
    pass

def check(ok, message):
    if not ok:
        raise Reject(message)

def exact_keys(value, fields, label):
    check(type(value) is dict and set(value) == fields, 'invalid fields in '+label)

def rational(value):
    check(type(value) is str and 1 <= len(value) <= 48, 'invalid rational string')
    try:
        x = Fraction(value)
    except (ValueError, ZeroDivisionError) as exc:
        raise Reject('malformed rational') from exc
    check(str(x) == value, 'rational must use reduced canonical form')
    return x

def digest(value):
    encoded=json.dumps(value,ensure_ascii=True,sort_keys=True,
                       separators=(',',':'),allow_nan=False).encode('ascii')
    return sha256(encoded).hexdigest()

def read(path):
    raw=Path(path).read_bytes()
    check(len(raw)<=8_000_000, 'input exceeds byte budget')
    def pairs(items):
        answer={}
        for k,v in items:
            check(k not in answer,'duplicate JSON key')
            answer[k]=v
        return answer
    def reject_number(_):
        raise Reject('only JSON integers are supported')
    return json.loads(raw.decode('utf-8'),object_pairs_hook=pairs,
                      parse_float=reject_number,parse_constant=reject_number)

def verify_pin(pin):
    check(type(pin) is str and len(pin)==64 and
          all(c in '0123456789abcdef' for c in pin),'external SHA256 pin is required')

def evidence_digest(protocol_pin,evidence):
    return digest({'domain':'pcs-evidencekernel-v24-observed-prefix',
                   'protocol_sha256':protocol_pin,'evidence':evidence})

def taylor_lower(c,terms):
    """Exact nonnegative partial Taylor sum, always <= exp(c) for c>=0."""
    s=Fraction(1)
    item=Fraction(1)
    for i in range(1,terms+1):
        item *= c / i
        s += item
    return s

def design(p):
    exact_keys(p,FIELDS,'registration')
    check(p['format']==FORMAT and
          p['estimand']=='fixed_registered_cohort_binary_ate' and
          p['assignment_model']=='predictable_bernoulli_fresh_randomness' and
          p['interval_model']=='binary_labels_with_max_misses' and
          p['stopping_rule']=='registered_feedback_fsm','unsupported contract')
    n=p['registered_units'];states=p['states'];initial=p['initial_state']
    minimum=p['min_enrollment'];K=p['max_interval_misses']
    check(type(n) is int and 2<=n<=100_000,'registered_units outside 2..100000')
    check(type(states) is int and 1<=states<=16,'states outside 1..16')
    check(type(initial) is int and 0<=initial<states,'invalid initial state')
    check(type(minimum) is int and 2<=minimum<=n,'invalid minimum enrollment')
    check(type(K) is int and 0<=K<=n,'invalid interval-miss budget')
    alpha=rational(p['confidence_alpha']);delta=rational(p['calibration_failure_bound'])
    null=rational(p['null_ate_upper'])
    check(0<alpha<1 and 0<=delta<=1-alpha and -1<=null<=1,
          'invalid confidence/miscoverage/null premise')
    weights=p['allocation_weights_by_state'];trans=p['next_state_by_state_action_report']
    stop=p['stop_after_by_state_action_report']
    check(all(type(x) is list and len(x)==states for x in (weights,trans,stop)),
          'invalid state table lengths')
    probs=[]
    for s in range(states):
        w=weights[s]
        check(type(w) is list and len(w)==2 and all(type(x) is int and 1<=x<=1000 for x in w),
              'both treatment arms must have positive bounded probabilities')
        probs.append(Fraction(w[1],sum(w)))
        for table,cell_type,what in ((trans,int,'transition'),(stop,bool,'stopping')):
            row=table[s]
            check(type(row) is list and len(row)==2 and
                  all(type(v) is list and len(v)==2 and
                      all(type(a) is cell_type for a in v) for v in row),
                  'invalid '+what+' table')
        check(all(0<=v<states for branch in trans[s] for v in branch),
              'transition outside state domain')
    tune=p['tuning']
    check(type(tune) is list and 1<=len(tune)<=16,'invalid tuning count')
    registered=[];spent=Fraction(0)
    for t in tune:
        exact_keys(t,TUNE,'tuning')
        lam=rational(t['lambda']);part=rational(t['alpha_spend']);c=rational(t['log_upper'])
        terms=t['taylor_terms']
        check(0<lam<=1 and 0<part<=alpha and 0<=c<=20 and
              type(terms) is int and 1<=terms<=32,'invalid tuning parameters')
        lower=taylor_lower(c,terms)
        check(lower*part>=1,'log upper-bound certificate failed')
        registered.append({'lambda':lam,'alpha_spend':part,'log_upper':c,
                           'taylor_terms':terms,'exp_lower':lower})
        spent+=part
    check(spent<=alpha,'alpha spending exceeds registered familywise alpha')
    return dict(n=n,S=states,initial=initial,min=minimum,K=K,
                alpha=alpha,delta=delta,null=null,probs=probs,
                trans=trans,stop=stop,tune=registered)

def audit(protocol,evidence,*,protocol_pin,evidence_pin):
    verify_pin(protocol_pin);verify_pin(evidence_pin)
    check(digest(protocol)==protocol_pin,'registration commitment mismatch')
    check(evidence_digest(protocol_pin,evidence)==evidence_pin,
          'observed-prefix commitment mismatch')
    d=design(protocol)
    exact_keys(evidence,EVIDENCE,'evidence')
    acts=evidence['assignments'];reports=evidence['reports'];labels=evidence['true_intervals']
    check(type(acts) is list and type(reports) is list and type(labels) is list,
          'evidence arrays required')
    t=len(acts)
    check(d['min']<=t<=d['n'] and len(reports)==t and len(labels)==t,
          'truncated or invalid enrollment records')
    check(all(type(a) is int and a in (0,1) for a in acts+reports),
          'treatment and feedback must be bits')
    check(all(type(lab) is str and lab in ('0','1','01') for lab in labels),
          'invalid binary measurement interval')
    s=d['initial'];H=Fraction(0);W2=Fraction(0)
    # Every observed label contributes a lower bound on the corresponding HT term.
    misses=[];p_trace=[];state_counts=[0]*d['S']
    for i,(a,r,label) in enumerate(zip(acts,reports,labels),start=1):
        state_counts[s]+=1
        p=d['probs'][s]
        p_trace.append(str(p))
        lower=0 if label=='01' or label=='0' else 1
        upper=1 if label=='01' or label=='1' else 0
        H += (Fraction(lower,p) if a else -Fraction(upper,1-p))
        # If one interval is false, this is the maximum upward error in its
        # interval-based *lower* HT contribution, irrespective of the true bit.
        misses.append(Fraction(lower,p) if a else Fraction(1-upper,1-p))
        width=1/p+1/(1-p)
        W2+=width*width
        stop=i==d['n'] or (i>=d['min'] and protocol['stop_after_by_state_action_report'][s][a][r])
        check(stop==(i==t), 'terminal length inconsistent with the registered stopping policy')
        s=protocol['next_state_by_state_action_report'][s][a][r]
    correction=sum(sorted(misses,reverse=True)[:d['K']],Fraction(0))
    bounds=[];best=None
    for cfg in d['tune']:
        lam=cfg['lambda'];c=cfg['log_upper']
        boundary=c/lam+lam*W2/8
        lower=(H-correction-boundary-(d['n']-t))/d['n']
        bounds.append({'lambda':str(lam),'alpha_spend':str(cfg['alpha_spend']),
                       'log_upper':str(c),'taylor_terms':cfg['taylor_terms'],
                       'exact_exp_lower':str(cfg['exp_lower']),
                       'martingale_boundary':str(boundary),
                       'ate_lower_bound':str(lower)})
        best=lower if best is None or lower>best else best
    check(best is not None,'no confidence bound')
    return {'format':RESULT,'status':('CONDITIONALLY_REJECTED' if best>d['null']
             else 'INSUFFICIENT_EVIDENCE'),
            'registered_units':d['n'],'enrolled_units':t,
            'null_ate_upper':str(d['null']),'anytime_lower_ate':str(best),
            'interval_based_lower_ht':str(H),
            'worst_case_interval_miss_penalty':str(correction),
            'sum_predictable_width_squared':str(W2),
            'conditional_confidence_alpha':str(d['alpha']),
            'asserted_joint_calibration_failure_bound':str(d['delta']),
            'unconditional_miscoverage_bound_if_calibration_valid':str(d['alpha']+d['delta']),
            'propensity_trace_sha256':digest(p_trace),
            'state_visit_counts':state_counts,'tuning_results':bounds,
            'protocol_sha256':protocol_pin,'evidence_sha256':evidence_pin,
            'warning':('Research-only conditional confidence sequence. Real assignment propensities, '
                       'freshness of randomization, fixed cohort/potential outcomes, chronology, '
                       'measurement calibration, custody, and no interference remain unverified. '
                       'Reported calibration delta is a premise, not measured evidence.')}

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('protocol');ap.add_argument('evidence')
    ap.add_argument('--protocol-pin',required=True)
    ap.add_argument('--evidence-pin',required=True)
    args=ap.parse_args()
    try:
        report=audit(read(args.protocol),read(args.evidence),
                     protocol_pin=args.protocol_pin,evidence_pin=args.evidence_pin)
    except (Reject,KeyError,TypeError,ValueError,OSError,OverflowError) as exc:
        ap.exit(2,'REJECTED: '+str(exc)+'\n')
    print(json.dumps(report,sort_keys=True,indent=2))

if __name__=='__main__':
    main()
