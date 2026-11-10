"""V25 propensity-upper-robust anytime-safe inference for a fixed ordered cohort.

The theorem relies on predictable external UPPER BOUNDS for propensities, stable
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

FORMAT = 'pcs-evidencekernel-propensity-upper-v25'
RESULT = 'pcs-evidencekernel-propensity-upper-audit-v25'
FIELDS = {'format','registered_units','states','initial_state',
          'propensity_upper_by_state','next_state_by_state_action_report',
          'stop_after_by_state_action_report','min_enrollment',
          'confidence_alpha','calibration_failure_bound','null_ate_upper',
          'max_interval_misses','tuning','estimand','assignment_model',
          'interval_model','stopping_rule'}
EVIDENCE = {'assignments','reports','true_intervals'}
TUNE = {'lambda','alpha_spend','log_upper','taylor_terms','reference_weights_by_state'}

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
    return digest({'domain':'pcs-evidencekernel-v25-observed-prefix',
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
          p['assignment_model']=='predictable_bernoulli_upper_bounded_fresh_randomness' and
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
    upper=p['propensity_upper_by_state'];trans=p['next_state_by_state_action_report']
    stop=p['stop_after_by_state_action_report']
    check(type(upper) is list and len(upper)==states and
          all(type(v) is str for v in upper) and
          all(0 < rational(v) <= 1 for v in upper), 'invalid propensity upper bounds')
    upper=[rational(v) for v in upper]
    check(all(type(x) is list and len(x)==states for x in (trans,stop)),
          'invalid state table lengths')
    for s in range(states):
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
        refs=t['reference_weights_by_state']
        check(type(refs) is list and len(refs)==states, 'reference strategy state length')
        qs=[]
        for w in refs:
            check(type(w) is list and len(w)==2 and
                  all(type(v) is int and 1<=v<=1000 for v in w),
                  'invalid reference probability weights')
            qs.append(Fraction(w[1],sum(w)))
        registered.append({'lambda':lam,'alpha_spend':part,'log_upper':c,
                           'taylor_terms':terms,'exp_lower':lower,'qs':qs})
        spent+=part
    check(spent<=alpha,'alpha spending exceeds registered familywise alpha')
    return dict(n=n,S=states,initial=initial,min=minimum,K=K,
                alpha=alpha,delta=delta,null=null,upper=upper,
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
    s=d['initial'];states_seen=[];state_counts=[0]*d['S']
    for i,(a,r) in enumerate(zip(acts,reports),start=1):
        states_seen.append(s)
        state_counts[s]+=1
        stop=i==d['n'] or (i>=d['min'] and protocol['stop_after_by_state_action_report'][s][a][r])
        check(stop==(i==t), 'terminal length inconsistent with the registered stopping policy')
        s=d['trans'][s][a][r]
    bounds=[];best=None
    for cfg in d['tune']:
        H=Fraction(0);W2=Fraction(0);bias=Fraction(0)
        miss_penalties=[];q_trace=[]
        for state,a,label in zip(states_seen,acts,labels):
            q=cfg['qs'][state];cap=d['upper'][state]
            q_trace.append(str(q))
            lower=int(label=='1');upper=int(label!='0')
            H+=(Fraction(lower,q) if a else -Fraction(upper,1-q))
            miss_penalties.append(Fraction(lower,q) if a else Fraction(1-upper,1-q))
            width=1/q+1/(1-q)
            W2+=width*width
            # E_p[HT(q)] - ATE_i = (p-q)*(Y1/q + Y0/(1-q)).
            # With 0 <= p <= cap and binary potential outcomes, positive bias
            # is at most max(0, cap-q)*width, even with adaptive reports.
            bias+=max(Fraction(0),cap-q)*width
        correction=sum(sorted(miss_penalties,reverse=True)[:d['K']],Fraction(0))
        lam=cfg['lambda'];c=cfg['log_upper']
        boundary=c/lam+lam*W2/8
        lower=(H-correction-bias-boundary-(d['n']-t))/d['n']
        bounds.append({'reference_q_by_state':[str(x) for x in cfg['qs']],
                       'lambda':str(lam),'alpha_spend':str(cfg['alpha_spend']),
                       'log_upper':str(c),'taylor_terms':cfg['taylor_terms'],
                       'exact_exp_lower':str(cfg['exp_lower']),
                       'interval_based_lower_ht':str(H),
                       'worst_case_interval_miss_penalty':str(correction),
                       'propensity_upper_bias_penalty':str(bias),
                       'sum_reference_width_squared':str(W2),
                       'martingale_boundary':str(boundary),
                       'ate_lower_bound':str(lower),
                       'reference_propensity_trace_sha256':digest(q_trace)})
        best=lower if best is None or lower>best else best
    # Exact (piecewise-affine) robustness frontier for simultaneously relaxing
    # every registered propensity ceiling to min(1, upper_s + epsilon).
    # This is a sensitivity result, NOT a claim of measured/verified ceilings.
    def score_at(cfg, result, eps):
        base=(Fraction(result['interval_based_lower_ht'])
              -Fraction(result['worst_case_interval_miss_penalty'])
              -Fraction(result['martingale_boundary'])
              -(d['n']-t))
        penalty=Fraction(0)
        for state,count in enumerate(state_counts):
            if count:
                q=cfg['qs'][state]
                cap=min(Fraction(1),d['upper'][state]+eps)
                penalty+=count*max(Fraction(0),cap-q)*(1/q+1/(1-q))
        return (base-penalty)/d['n']

    def strategy_frontier(cfg, result):
        if score_at(cfg,result,Fraction(0))<=d['null']:
            return Fraction(0)
        breaks={Fraction(0),Fraction(1)}
        for state in range(d['S']):
            if state_counts[state]:
                cap=d['upper'][state];q=cfg['qs'][state]
                breaks.add(max(Fraction(0),q-cap))
                breaks.add(Fraction(1)-cap)
        ordered=sorted(x for x in breaks if 0<=x<=1)
        for a,b in zip(ordered,ordered[1:]):
            fa=score_at(cfg,result,a)-d['null']
            fb=score_at(cfg,result,b)-d['null']
            if fa>0 and fb<=0:
                return a+(b-a)*fa/(fa-fb)
        return Fraction(1)

    frontiers=[strategy_frontier(cfg,out) for cfg,out in zip(d['tune'],bounds)]
    frontier=max(frontiers)
    frontier_inclusive=any(score_at(cfg,out,frontier)>d['null']
                           for cfg,out in zip(d['tune'],bounds))
    check(best is not None,'no confidence bound')
    return {'format':RESULT,'status':('CONDITIONALLY_REJECTED' if best>d['null']
             else 'INSUFFICIENT_EVIDENCE'),
            'registered_units':d['n'],'enrolled_units':t,
            'null_ate_upper':str(d['null']),'anytime_lower_ate':str(best),
            'propensity_upper_by_state':[str(x) for x in d['upper']],
            'assurance_scope':'conditional_on_true_propensities_not_exceeding_registered_upper_bounds',
            'conditional_confidence_alpha':str(d['alpha']),
            'asserted_joint_calibration_failure_bound':str(d['delta']),
            'unconditional_miscoverage_bound_if_calibration_valid':str(d['alpha']+d['delta']),
            'state_visit_counts':state_counts,'tuning_results':bounds,
            'common_upper_slack_supremum':str(frontier),
            'strict_rejection_at_supremum':frontier_inclusive,
            'upper_slack_semantics':'all upper bounds increased by epsilon and capped at one; valid for epsilon below supremum if originally rejected',
            'protocol_sha256':protocol_pin,'evidence_sha256':evidence_pin,
            'warning':('Research-only conditional confidence sequence. Real propensity UPPER bounds, '
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
