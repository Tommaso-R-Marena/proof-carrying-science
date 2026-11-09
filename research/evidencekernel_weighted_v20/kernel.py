"""Exact heterogeneous binary weak-null inference under preregistered nonstationary weighted rejection sampling.

Research-only. Physical randomness, outcome blindness, custody, truthful calibration,
independent timestamps and integrity of recorded attempts remain external premises.
"""
from __future__ import annotations
import json
from fractions import Fraction
from itertools import combinations, product
from pathlib import Path
from research.evidencekernel_selective_v17.kernel import (
    Reject, insist, exact_keys, digest, load_strict, effect_stat, parse_fraction,
)

FORMAT = 'pcs-evidencekernel-weighted-stopping-v20'
RULE = 'first_acceptable_else_last'
RANK = 'weighted_conditional_rejected_prefix_right_cdf'
PFIELDS = ('format','n','k','baseline_covariate','max_attempts','accept_if_score_le',
           'selection_rule','candidate_law','candidate_weights_by_step','null_ate_upper',
           'max_interval_misses','confidence_alpha','tie_rule')
EFIELDS = ('attempts','selected_assignment','observed_intervals')


def design(p):
    exact_keys(p, PFIELDS, 'weighted protocol')
    insist(p['format']==FORMAT and p['selection_rule']==RULE and p['tie_rule']==RANK,
           'unsupported weighted stopping rule')
    insist(p['candidate_law']=='registered_independent_weighted_by_step',
           'dependent or post-outcome candidate draws unsupported')
    n,k,H=p['n'],p['k'],p['max_attempts']
    insist(type(n) is int and 2<=n<=8 and type(k) is int and 1<=k<n, 'trial size cap')
    insist(type(H) is int and 1<=H<=128, 'attempt horizon cap')
    x=p['baseline_covariate']
    insist(type(x) is list and len(x)==n and all(type(v) is int and -16<=v<=16 for v in x),
           'invalid baseline vector')
    cutoff=p['accept_if_score_le']
    insist(type(cutoff) is int and 0<=cutoff<=10000, 'invalid cutoff')
    K=p['max_interval_misses']
    insist(type(K) is int and 0<=K<=n, 'invalid miss budget')
    alpha=parse_fraction(p['confidence_alpha']); null=parse_fraction(p['null_ate_upper'])
    insist(Fraction(0)<alpha<1 and -1<=null<=1, 'invalid alpha/null')
    space=list(combinations(range(n),k));N=len(space)
    insist(N*4**n<=5_000_000, 'bounded potential-outcome budget exceeded')
    schedule=p['candidate_weights_by_step']
    insist(type(schedule) is list and len(schedule)==H, 'missing weighted schedule')
    weights=[]; W=[]
    for row in schedule:
        insist(type(row) is list and len(row)==N and
               all(type(v) is int and 0<=v<=10000 for v in row), 'invalid weight row')
        insist(sum(row)>0,'zero-weight candidate draw')
        weights.append(row);W.append(sum(row))
    scores=[abs(n*sum(x[i] for i in z)-k*sum(x)) for z in space]
    accepted=[s<=cutoff for s in scores]
    R=[sum(row[i] for i in range(N) if not accepted[i]) for row in weights]
    D=1
    for s in W:D*=s
    insist(D.bit_length()<=32768,'oversized design denominator')
    mass=[0]*N
    prefix=1
    for t in range(H):
        suffix=1
        for w in W[t+1:]: suffix*=w
        for i in range(N):
            if t==H-1 or accepted[i]:
                mass[i]+=prefix*weights[t][i]*suffix
        prefix*=R[t]
    insist(sum(mass)==D,'selection distribution fails normalization')
    return {'n':n,'k':k,'H':H,'N':N,'space':space,'weights':weights,'W':W,'R':R,
            'accepted':accepted,'mass':mass,'total':D,'K':K,'alpha':alpha,'null':null}


def attempt_commitment(protocol_pin, attempts):
    return digest({'domain':'pcs-evidencekernel-v20-registered-weighted-attempts',
                   'protocol_sha256':protocol_pin,'attempts':attempts})


def validate(p,e,d,protocol_pin,attempts_pin):
    insist(type(protocol_pin) is str and len(protocol_pin)==64 and
           all(v in '0123456789abcdef' for v in protocol_pin), 'external protocol pin required')
    insist(type(attempts_pin) is str and len(attempts_pin)==64 and
           all(v in '0123456789abcdef' for v in attempts_pin), 'external attempt pin required')
    insist(digest(p)==protocol_pin, 'protocol pin mismatch')
    exact_keys(e,EFIELDS,'weighted evidence')
    attempts=e['attempts'];labels=e['observed_intervals'];z=e['selected_assignment']
    insist(type(attempts) is list and 1<=len(attempts)<=d['H'],'incomplete attempts')
    insist(type(labels) is list and len(labels)==d['n'] and
           all(type(v) is str and v in ('0','1','01') for v in labels),'bad intervals')
    insist(type(z) is list and tuple(z) in d['space'],'bad selected assignment')
    index={z:i for i,z in enumerate(d['space'])};ids=[]
    for j,a in enumerate(attempts):
        insist(type(a) is list and tuple(a) in index,'invalid candidate assignment')
        i=index[tuple(a)]
        insist(d['weights'][j][i]>0,'zero-probability recorded candidate')
        ids.append(i)
    insist(all(not d['accepted'][i] for i in ids[:-1]), 'early accepted allocation concealed')
    insist(len(ids)==d['H'] or d['accepted'][ids[-1]], 'premature stopping')
    insist(z==attempts[-1], 'selected allocation disagrees with recorded terminal')
    insist(attempt_commitment(protocol_pin,attempts)==attempts_pin,
           'attempt history does not match independently pinned commitment')
    return ids,labels


def prefix_cdf(d,ids):
    """Right CDF of rejected prefix conditional on (terminal assignment, stop time).

    For independent, not-identically-distributed registered draws, at each
    prefix step j, an allocation i has conditional weight q[j,i]/R[j].
    Returns integer numerator, integer denominator, exact probability.
    """
    L=len(ids)-1
    if L==0:return 1,1
    denominator=1
    for j in range(L):
        insist(d['R'][j]>0,'zero-probability rejection step')
        denominator*=d['R'][j]
    left=0;prev=1
    for j in range(L):
        current=ids[j]
        smaller=sum(d['weights'][j][i] for i in range(current) if not d['accepted'][i])
        suffix=1
        for h in range(j+1,L): suffix*=d['R'][h]
        left+=prev*smaller*suffix
        prev*=d['weights'][j][current]
    numerator=left+prev
    insist(0<numerator<=denominator,'invalid conditional right CDF')
    return numerator,denominator


def audit(p,e,*,protocol_pin,attempts_pin):
    d=design(p)
    indices,labels=validate(p,e,d,protocol_pin,attempts_pin)
    zid=indices[-1];z=d['space'][zid];rank,M=prefix_cdf(d,indices)
    best={};witnesses={};compatible=0
    zset=set(z)
    for digits in product(range(4),repeat=d['n']):
        world=tuple(((v>>1)&1,v&1) for v in digits)
        misses=sum(v!='01' and v!=str(world[i][int(i in zset)]) for i,v in enumerate(labels))
        if misses>d['K']:continue
        compatible+=1;ate=sum(b-a for a,b in world)
        stats=[effect_stat(world,alt,d['n'],d['k']) for alt in d['space']]
        observed=stats[zid]
        gt=sum(m for m,s in zip(d['mass'],stats) if s>observed)
        eq=sum(m for m,s in zip(d['mass'],stats) if s==observed)
        numerator=gt*M+eq*rank
        if numerator>best.get(ate,-1):
            best[ate]=numerator
            witnesses[ate]=[''.join(map(str,v)) for v in world]
    insist(compatible>0,'no compatible binary outcomes')
    curve=[];peak=-1
    for h in range(-d['n'],d['n']+1):
        peak=max(peak,best.get(h,-1))
        curve.append({'ate_upper':str(Fraction(h,d['n'])),'null_feasible':peak>=0,
                      'max_p':str(Fraction(peak,d['total']*M)) if peak>=0 else None})
    # At the tautological upper endpoint, no discovery is possible.
    curve[-1]['max_p']='1';curve[-1]['null_feasible']=True
    relevant=[row for row in curve if Fraction(row['ate_upper'])<=d['null']][-1]
    lower=next((row['ate_upper'] for row in curve if row['null_feasible'] and
                Fraction(row['max_p'])>d['alpha']),None)
    possibilities=[a for a in best if Fraction(a,d['n'])<=d['null']]
    witness=(witnesses[max(possibilities,key=best.__getitem__)] if possibilities else None)
    return {'status':'CONDITIONALLY_VERIFIED' if relevant['null_feasible'] else 'INCONSISTENT_NULL',
            'conditional_p':relevant['max_p'],'conditional_lower_ate':lower,
            'confidence_alpha':str(d['alpha']),'compatible_worlds':compatible,
            'design_denominator':str(d['total']),'selected_assignment_mass':str(d['mass'][zid]),
            'stopping_time':len(indices),'weighted_prefix_right_numerator':str(rank),
            'weighted_prefix_right_denominator':str(M),
            'null_curve':curve,'maximizing_world':witness,
            'protocol_sha256':protocol_pin,'attempts_sha256':attempts_pin,
            'warning':'Conditional statistical result only. Candidate draw probabilities must follow the preregistered outcome-blind and independently controlled per-step weights; attempted allocations and final observations require independent custody. Signed bytes alone cannot establish these premises.'}


def main():
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('protocol');parser.add_argument('evidence')
    parser.add_argument('--protocol-pin',required=True)
    parser.add_argument('--attempts-pin',required=True)
    args=parser.parse_args()
    try: report=audit(load_strict(args.protocol),load_strict(args.evidence),
                      protocol_pin=args.protocol_pin,attempts_pin=args.attempts_pin)
    except (Reject,TypeError,ValueError,OverflowError,KeyError,OSError) as err:
        parser.exit(2,'REJECTED: '+str(err)+'\n')
    print(json.dumps(report,indent=2,sort_keys=True))

if __name__=='__main__':main()
