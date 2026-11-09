"""EvidenceKernel v26: exact prestudy Bernoulli calibration -> v25 anytime inference.

Research only. Conditional stationarity/independence and external chronology/custody
are NOT established by the signed/pinned bytes or by the mathematics here.
"""
from __future__ import annotations
from fractions import Fraction
from math import comb
from pathlib import Path
import json
import argparse
from research.evidencekernel_propensity_v25 import kernel as v25

FORMAT='pcs-evidencekernel-prestudy-propensity-calibration-v26'
RESULT='pcs-evidencekernel-calibrated-inference-audit-v26'
CAL_KEYS={'format','state_count','minimum_sample_sizes','maximum_sample_sizes',
          'sample_size_policy','beta_spend_by_state','grid_denominator',
          'sampling_model','require_nontrivial_ceiling'}
EVID_KEYS={'assignment_bits_by_state','stage'}
SAMPLING='prestudy_fixed_size_stationary_statewise_bernoulli'

check=v25.check
Reject=v25.Reject
rational=v25.rational
digest=v25.digest
exact_keys=v25.exact_keys
verify_pin=v25.verify_pin

def calibration_evidence_pin(contract_pin, records):
    return digest({'domain':'pcs-evidencekernel-v26-prestudy-records',
                   'contract_sha256':contract_pin,'records':records})

def binomial_lower_tail_numerator(n, successes, q, denominator):
    """Integer numerator of P_{q/denominator}(Binomial(n,p)<=successes)."""
    check(type(n) is int and 1<=n<=4096,'invalid sample size')
    check(type(successes) is int and 0<=successes<=n,'invalid observed success count')
    check(type(q) is int and 0<=q<=denominator and
          type(denominator) is int and 2<=denominator<=4096,'bad probability grid')
    return sum(comb(n,j)*pow(q,j)*pow(denominator-q,n-j)
               for j in range(successes+1))

def find_upper(n,successes,beta,D):
    """Least exact rational grid ceiling whose one-sided binomial tail <= beta.

    Discrete conservative CP inversion; never rounds a ceiling downward.
    """
    denom=pow(D,n)
    lo,hi=1,D
    while lo<hi:
        mid=(lo+hi)//2
        numerator=binomial_lower_tail_numerator(n,successes,mid,D)
        if numerator*beta.denominator <= denom*beta.numerator:
            hi=mid
        else:
            lo=mid+1
    result=Fraction(lo,D)
    tail=Fraction(binomial_lower_tail_numerator(n,successes,lo,D),denom)
    check(result==1 or tail<=beta,'no nontrivial tail bound')
    if lo>1:
        prev=Fraction(binomial_lower_tail_numerator(n,successes,lo-1,D),denom)
        check(prev>beta,'calibration grid inversion not minimal')
    return result,tail

def calibrate(contract,records,*,contract_pin,records_pin):
    verify_pin(contract_pin);verify_pin(records_pin)
    check(digest(contract)==contract_pin,'calibration contract pin mismatch')
    check(calibration_evidence_pin(contract_pin,records)==records_pin,
          'calibration record pin mismatch')
    exact_keys(contract,CAL_KEYS,'calibration contract')
    exact_keys(records,EVID_KEYS,'calibration records')
    check(contract['format']==FORMAT and contract['sampling_model']==SAMPLING,
          'unsupported calibration model')
    check(records['stage']=='prestudy','calibration records must be pretrial')
    count=contract['state_count'];samples_min=contract['minimum_sample_sizes']
    samples_max=contract['maximum_sample_sizes']
    beta_values=contract['beta_spend_by_state'];D=contract['grid_denominator']
    check(type(count) is int and 1<=count<=16,'invalid state count')
    check(type(D) is int and 16<=D<=4096,'invalid grid')
    check(type(samples_min) is list and len(samples_min)==count and
          type(samples_max) is list and len(samples_max)==count and
          all(type(a) is int and type(b) is int and 16<=a<=b<=4096
              for a,b in zip(samples_min,samples_max)),
          'calibration sample ranges must be preregistered')
    policy=contract['sample_size_policy']
    check(policy in ('fixed_per_state','anytime_within_registered_range'),
          'unsupported calibration stopping policy')
    if policy=='fixed_per_state':
        check(samples_min==samples_max,'fixed calibration sample size must be exact')
    check(type(beta_values) is list and len(beta_values)==count and
          all(type(b) is str for b in beta_values),'invalid beta budget')
    betas=[rational(b) for b in beta_values]
    check(all(0<b<=Fraction(1,4) for b in betas), 'invalid beta spend')
    check(type(contract['require_nontrivial_ceiling']) is bool,'invalid nontrivial policy')
    arrays=records['assignment_bits_by_state']
    check(type(arrays) is list and len(arrays)==count,'calibration state streams')
    caps=[];replayed=[]
    for s,(low,high,beta,arr) in enumerate(zip(samples_min,samples_max,betas,arrays)):
        check(type(arr) is list and low<=len(arr)<=high and
              all(type(a) is int and a in (0,1) for a in arr),
              'invalid or truncated calibration stream')
        m=len(arr)
        successes=sum(arr)
        permitted_looks=high-low+1
        # Union bound across all permitted sample lengths for data-dependent
        # calibration stopping: a fixed-n CP tail alone is NOT anytime safe.
        spend=beta/permitted_looks
        upper,tail=find_upper(m,successes,spend,D)
        if contract['require_nontrivial_ceiling']:
            check(upper<1,'vacuous ceiling forbidden by contract')
        caps.append(str(upper))
        replayed.append({'state':s,'sample_size':m,'treated_count':successes,
                         'beta_spend':str(beta),'permitted_calibration_looks':permitted_looks,
                         'effective_tail_threshold':str(spend),'ceiling':str(upper),
                         'binomial_lower_tail_at_ceiling':str(tail)})
    return {'format':FORMAT,'propensity_ceiling_by_state':caps,
            'statewise_calibration':replayed,
            'total_propensity_failure_budget':str(sum(betas,Fraction(0))),
            'calibration_sample_size_policy':policy,
            'contract_sha256':contract_pin,'records_sha256':records_pin,
            'stationarity_assumption':'fixed-state conditional Bernoulli probabilities carry over from pretrial to study'}

def audit(calibration_contract,calibration_records,study_protocol,study_records,
          *,calibration_contract_pin,calibration_records_pin,study_protocol_pin,
          study_records_pin):
    cal=calibrate(calibration_contract,calibration_records,
                  contract_pin=calibration_contract_pin,records_pin=calibration_records_pin)
    v25.verify_pin(study_protocol_pin);v25.verify_pin(study_records_pin)
    check(v25.digest(study_protocol)==study_protocol_pin,
          'v25 study contract pin mismatch')
    check(study_protocol.get('states')==calibration_contract['state_count'],
          'state count mismatch between pretrial and study')
    check(study_protocol.get('propensity_upper_by_state')==cal['propensity_ceiling_by_state'],
          'v25 propensity ceilings not equal to independently calibrated caps')
    study=v25.audit(study_protocol,study_records,
                    protocol_pin=study_protocol_pin,evidence_pin=study_records_pin)
    alpha=rational(study['conditional_confidence_alpha'])
    measurement_delta=rational(study['asserted_joint_calibration_failure_bound'])
    propensity_beta=rational(cal['total_propensity_failure_budget'])
    check(alpha+measurement_delta+propensity_beta<=1,'error budget exceeds one')
    return {'format':RESULT,'status':study['status'],
            'calibration':cal,'study_v25':study,
            'conditional_statistical_error':str(alpha),
            'asserted_measurement_failure_budget':str(measurement_delta),
            'derived_propensity_calibration_failure_budget':str(propensity_beta),
            'joint_failure_bound_if_all_physical_assumptions_hold':str(alpha+measurement_delta+propensity_beta),
            'warning':('PRESTUDY SEPARATION, STATIONARY STATEWISE PROPENSITIES, HONEST RECORDING, '
                       'independent physical randomness, stable potential outcomes, measurement '
                       'calibration and authenticated timestamps are NOT established by these hashes. '
                       'No real scientific claim is certified by the synthetic demonstration.')}

def main():
    pa=argparse.ArgumentParser(description=__doc__)
    pa.add_argument('calibration_contract')
    pa.add_argument('calibration_records')
    pa.add_argument('study_protocol')
    pa.add_argument('study_records')
    for nm in ('calibration_contract_pin','calibration_records_pin','study_protocol_pin','study_records_pin'):
        pa.add_argument('--'+nm.replace('_','-'),required=True)
    args=pa.parse_args()
    try:
        result=audit(v25.read(args.calibration_contract),v25.read(args.calibration_records),
                     v25.read(args.study_protocol),v25.read(args.study_records),
                     calibration_contract_pin=args.calibration_contract_pin,
                     calibration_records_pin=args.calibration_records_pin,
                     study_protocol_pin=args.study_protocol_pin,
                     study_records_pin=args.study_records_pin)
    except (Reject,KeyError,ValueError,TypeError,OSError,OverflowError) as e:
        pa.exit(2,'REJECTED: '+str(e)+'\n')
    print(json.dumps(result,sort_keys=True,indent=2))

if __name__=='__main__':main()
