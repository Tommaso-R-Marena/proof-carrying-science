"""EvidenceKernel v27: exact anytime e-mixture calibration + prospective drift alarm.

RESEARCH ONLY. Statistical validity conditional on externally witnessed statewise
stationarity/conditional Bernoulli assignments, independent randomness, complete
custody, valid scientific measurements and prespecified error budgets.
"""
from __future__ import annotations
import argparse
from fractions import Fraction
from pathlib import Path
import json
from research.evidencekernel_propensity_v25 import kernel as v25

F=Fraction
check=v25.check
Reject=v25.Reject
rational=v25.rational
digest=v25.digest
exact_keys=v25.exact_keys
verify_pin=v25.verify_pin
FORMAT='pcs-evidencekernel-anytime-mixture-calibration-v27'
RESULT='pcs-evidencekernel-anytime-mixture-audit-v27'
SAMPLING='prestudy_statewise_stationary_conditional_bernoulli'
KEYS={'format','sampling_model','state_count','minimum_sample_sizes',
      'maximum_sample_sizes','beta_spend_by_state','grid_denominator',
      'e_mixture_ratios','drift_mixture_ratios','drift_alarm_spend_by_state',
      'require_nontrivial_ceiling'}
RKEYS={'stage','assignment_bits_by_state'}

def record_pin(contract_pin,records):
    return digest({'domain':'pcs-evidencekernel-v27-raw-calibration',
                   'contract_sha256':contract_pin,'records':records})

def fraction_pow(a,n):
    return F(pow(a.numerator,n),pow(a.denominator,n))

def e_upper(n,s,u,ratios):
    """Mixture LR evidence against H0:p>=u (fixed u), exact rational.

    Each component compares q=c*u against u, with 0<c<1. Under p>=u
    the conditional expected multiplier is <=1. Valid for optional stopping.
    """
    check(type(n) is int and 0<=n<=4096 and type(s) is int and 0<=s<=n,
          'invalid calibration prefix')
    check(F(0)<u<F(1),'u must lie strictly between zero and one')
    f=n-s
    return sum((fraction_pow(c,s)*fraction_pow((1-c*u)/(1-u),f)
                for c in ratios),F(0))/len(ratios)

def invert_upper(n,s,beta,D,ratios):
    """Minimum rational grid ceiling where E >=1/beta, else 1.

    E is increasing in u for each realized path; hence upper CS is valid.
    """
    lo,hi=1,D
    target=1/beta
    while lo<hi:
        mid=(lo+hi)//2
        if e_upper(n,s,F(mid,D),ratios)>=target: hi=mid
        else:lo=mid+1
    upper=F(lo,D)
    reached=(lo<D)
    value=e_upper(n,s,upper,ratios) if reached else F(1)
    check(not reached or value>=target,'inverted e-process failed')
    if lo>1:
        check(e_upper(n,s,F(lo-1,D),ratios)<target,
              'ceiling is not minimal on grid')
    return upper,value,reached

def params(contract):
    exact_keys(contract,KEYS,'v27 calibration contract')
    check(contract['format']==FORMAT and contract['sampling_model']==SAMPLING,
          'unsupported sampling model')
    S=contract['state_count'];D=contract['grid_denominator']
    check(type(S) is int and 1<=S<=16 and type(D) is int and 16<=D<=4096,
          'unsupported calibration size or grid')
    check(type(contract['require_nontrivial_ceiling']) is bool,
          'invalid vacuous ceiling policy')
    mins=contract['minimum_sample_sizes'];maxs=contract['maximum_sample_sizes']
    beta_raw=contract['beta_spend_by_state'];gamma_raw=contract['drift_alarm_spend_by_state']
    check(all(type(x) is list and len(x)==S for x in (mins,maxs,beta_raw,gamma_raw)),
          'bad statewise registration arrays')
    check(all(type(a) is int and type(b) is int and 16<=a<=b<=4096
              for a,b in zip(mins,maxs)),'invalid calibration stopping range')
    betas=[rational(x) for x in beta_raw]
    gammas=[rational(x) for x in gamma_raw]
    check(all(0<x<=F(1,4) for x in betas+gammas),
          'invalid statewise risk budget')
    ratios=[]
    for key in ('e_mixture_ratios','drift_mixture_ratios'):
        x=contract[key]
        check(type(x) is list and 1<=len(x)<=16 and all(type(v) is str for v in x),
              'invalid finite mixture')
        vals=[rational(v) for v in x]
        check(all(0<c<1 for c in vals) and len(set(vals))==len(vals),
              'non-distinct/out-of-range mixture ratios')
        ratios.append(vals)
    return dict(S=S,D=D,mins=mins,maxs=maxs,betas=betas,gammas=gammas,
                ratios=ratios[0],drift=ratios[1],
                nontrivial=contract['require_nontrivial_ceiling'])

def calibrate(contract,records,*,contract_pin,records_pin):
    verify_pin(contract_pin);verify_pin(records_pin)
    check(digest(contract)==contract_pin,'calibration contract pin mismatch')
    check(record_pin(contract_pin,records)==records_pin,
          'calibration evidence pin mismatch')
    d=params(contract)
    exact_keys(records,RKEYS,'calibration records')
    check(records['stage']=='prestudy','prestudy stage required')
    arrays=records['assignment_bits_by_state']
    check(type(arrays) is list and len(arrays)==d['S'],
          'statewise calibration records required')
    ceilings=[];replays=[]
    for s,arr in enumerate(arrays):
        check(type(arr) is list and d['mins'][s]<=len(arr)<=d['maxs'][s]
              and all(type(x) is int and x in (0,1) for x in arr),
              'truncated, unexpected, or malformed calibration stream')
        n=len(arr);successes=sum(arr)
        ceiling,evalue,cross=invert_upper(n,successes,d['betas'][s],d['D'],d['ratios'])
        if d['nontrivial']:check(ceiling<1,'vacuous calibration ceiling')
        ceilings.append(str(ceiling))
        replays.append({'state':s,'sample_size':n,'treated_count':successes,
                        'calibration_beta':str(d['betas'][s]),
                        'calibration_mixture_e_at_ceiling':str(evalue),
                        'mixture_boundary_crossed':cross,'ceiling':str(ceiling),
                        'per_look_penalty':'none (Ville anytime-valid e-mixture)'})
    return {'format':FORMAT,'propensity_ceiling_by_state':ceilings,
            'statewise_calibration':replays,
            'joint_propensity_failure_budget':str(sum(d['betas'],F(0))),
            'statewise_drift_alarm_budgets':[str(g) for g in d['gammas']],
            'contract_sha256':contract_pin,'records_sha256':records_pin,
            'assurance':'conditional on stable statewise Bernoulli probability carrying from prestudy to trial'}

def drift_replay(study_protocol,study_evidence,ceilings,gammas,ratios):
    """An anytime alarm for assignment rates exceeding registered ceiling.

    A nonalarm is NOT a certificate of correct propensities / stationarity.
    """
    S=len(ceilings)
    capitals=[[F(1) for _ in ratios] for _ in range(S)]
    max_e=[F(1)]*S
    first_alarm=[None]*S
    n_by_state=[0]*S
    state=study_protocol['initial_state']
    for j,(a,r) in enumerate(zip(study_evidence['assignments'],study_evidence['reports']),1):
        cap=ceilings[state]
        n_by_state[state]+=1
        if cap<1:
            for h,c in enumerate(ratios):
                alternative=cap+c*(1-cap)
                multiplier=alternative/cap if a else (1-alternative)/(1-cap)
                capitals[state][h]*=multiplier
            evidence=sum(capitals[state],F(0))/len(ratios)
            max_e[state]=max(max_e[state],evidence)
            if first_alarm[state] is None and evidence>=1/gammas[state]:
                first_alarm[state]=j
        state=study_protocol['next_state_by_state_action_report'][state][a][r]
    return {'alarm':any(v is not None for v in first_alarm),
            'first_alarm_enrollment_by_state':first_alarm,
            'max_e_value_by_state':[str(x) for x in max_e],
            'observations_by_state':n_by_state,
            'calibration_warning':'No alarm does not establish stationarity or correct true assignment probabilities.'}

def audit(contract,records,study_protocol,study_evidence,*,contract_pin,
          records_pin,study_pin,evidence_pin):
    cal=calibrate(contract,records,contract_pin=contract_pin,records_pin=records_pin)
    verify_pin(study_pin);verify_pin(evidence_pin)
    check(digest(study_protocol)==study_pin,'study contract pin mismatch')
    check(study_protocol.get('states')==contract['state_count'],
          'calibration/study state count mismatch')
    check(study_protocol.get('propensity_upper_by_state')==cal['propensity_ceiling_by_state'],
          'study ceilings disagree with independently reconstructed calibration')
    study=v25.audit(study_protocol,study_evidence,
                    protocol_pin=study_pin,evidence_pin=evidence_pin)
    d=params(contract)
    monitor=drift_replay(study_protocol,study_evidence,
                         [F(x) for x in cal['propensity_ceiling_by_state']],
                         d['gammas'],d['drift'])
    alpha=rational(study['conditional_confidence_alpha'])
    delta=rational(study['asserted_joint_calibration_failure_bound'])
    beta=rational(cal['joint_propensity_failure_budget'])
    check(alpha+delta+beta<=1,'unsupported composed confidence budget')
    return {'format':RESULT,
            'status':('DRIFT_ALARM_NO_CLAIM' if monitor['alarm'] else study['status']),
            'calibration':cal,'drift_monitor':monitor,'study_v25':study,
            'scientific_type_i_upper_if_premises_hold':str(alpha+delta+beta),
            'extra_drift_false_alarm_budget_if_stationary_and_calibration_valid':str(sum(d['gammas'],F(0))),
            'warning':'Research only: recorded hashes do not establish chronology, independent custody, physical assignment law, stability, actual endpoint truth, or measurement calibration. No drift alarm NEVER establishes those premises.'}

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for item in ('calibration_contract','calibration_records','study_protocol','study_evidence'):
        ap.add_argument(item)
    for key in ('contract_pin','records_pin','study_pin','evidence_pin'):
        ap.add_argument('--'+key.replace('_','-'),required=True)
    args=ap.parse_args()
    try:
        print(json.dumps(audit(v25.read(args.calibration_contract),v25.read(args.calibration_records),
                              v25.read(args.study_protocol),v25.read(args.study_evidence),
                              contract_pin=args.contract_pin,records_pin=args.records_pin,
                              study_pin=args.study_pin,evidence_pin=args.evidence_pin),
                         sort_keys=True,indent=2))
    except (Reject,KeyError,ValueError,TypeError,OSError,OverflowError) as exc:
        ap.exit(2,'REJECTED: '+str(exc)+'\n')

if __name__=='__main__': main()
