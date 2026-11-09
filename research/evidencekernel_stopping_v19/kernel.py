"""Finite exact stopping-time rerandomization with ancillary transcript ranks.

Research-only: authenticated bytes do not establish genuinely randomized draws,
independent custody, chronology, or that pre-treatment covariates are genuine.
"""
from __future__ import annotations
import json
from fractions import Fraction
from itertools import combinations, product
from math import comb
from research.evidencekernel_selective_v17.kernel import (
    Reject, insist, exact_keys, digest, load_strict, effect_stat, parse_fraction
)

FORMAT = 'pcs-evidencekernel-stopping-v19'
RULE = 'first_acceptable_else_last'
RANK = 'within_stop_and_selected_rejected_prefix_lex_rank'
PFIELDS = ('format','n','k','baseline_covariate','max_attempts',
           'accept_if_score_le','selection_rule','candidate_law','null_ate_upper',
           'max_interval_misses','confidence_alpha','tie_rule')
EFIELDS = ('attempts','selected_assignment','observed_intervals')


def design(p):
    exact_keys(p,PFIELDS,'v19 protocol')
    insist(p['format']==FORMAT and p['selection_rule']==RULE and p['tie_rule']==RANK,
           'unsupported preregistered rule')
    insist(p['candidate_law']=='iid_with_replacement', 'unsupported candidate law')
    n,k,H=p['n'],p['k'],p['max_attempts']
    insist(type(n) is int and 2<=n<=8 and type(k) is int and 1<=k<n,'trial size cap')
    insist(type(H) is int and 1<=H<=128,'max attempts cap')
    x=p['baseline_covariate']
    insist(type(x) is list and len(x)==n and all(type(v) is int and -16<=v<=16 for v in x),'bad baseline')
    cutoff=p['accept_if_score_le']
    insist(type(cutoff) is int and 0<=cutoff<=10000,'bad acceptance cutoff')
    K=p['max_interval_misses']
    insist(type(K) is int and 0<=K<=n,'bad measurement uncertainty')
    alpha=parse_fraction(p['confidence_alpha']); null=parse_fraction(p['null_ate_upper'])
    insist(0<alpha<1 and -1<=null<=1,'invalid hypothesis or alpha')
    space=list(combinations(range(n),k));N=len(space)
    scores=[abs(n*sum(x[i] for i in z)-k*sum(x)) for z in space]
    accepted=[s<=cutoff for s in scores]
    R=sum(not a for a in accepted)
    insist(N.bit_length()*H<=4096 and 4**n*N<=5_000_000,'computation bound')
    total=N**H
    good_mass=sum(R**(t-1)*N**(H-t) for t in range(1,H+1))
    bad_mass=R**(H-1)
    mass=[good_mass if a else bad_mass for a in accepted]
    insist(sum(mass)==total,'design normalization')
    return dict(space=space,scores=scores,accepted=accepted,rejected=[i for i,v in enumerate(accepted) if not v],
                R=R,N=N,H=H,n=n,k=k,mass=mass,total=total,alpha=alpha,null=null,K=K)


def attempt_commitment(protocol_hash, attempts):
    return digest({'domain':'pcs-evidencekernel-v19-attempts-v1','protocol_sha256':protocol_hash,'attempts':attempts})


def validate(p,e,d,protocol_pin,attempts_pin):
    insist(type(protocol_pin) is str and len(protocol_pin)==64 and all(c in '0123456789abcdef' for c in protocol_pin),
           'external protocol pin required')
    insist(type(attempts_pin) is str and len(attempts_pin)==64 and all(c in '0123456789abcdef' for c in attempts_pin),
           'external attempt commitment required')
    insist(digest(p)==protocol_pin,'protocol differs from externally pinned data')
    exact_keys(e,EFIELDS,'v19 evidence')
    attempts=e['attempts']; labels=e['observed_intervals'];z=e['selected_assignment']
    insist(type(attempts) is list and 1<=len(attempts)<=d['H'],'missing/extra attempts')
    insist(type(labels) is list and len(labels)==d['n'] and all(type(v) is str and v in ('0','1','01') for v in labels),
           'invalid interval')
    insist(type(z) is list and tuple(z) in d['space'],'invalid selected assignment')
    ix={a:i for i,a in enumerate(d['space'])}
    indices=[]
    for a in attempts:
        insist(type(a) is list and tuple(a) in ix,'invalid candidate allocation')
        indices.append(ix[tuple(a)])
    insist(all(not d['accepted'][i] for i in indices[:-1]),'unreported earlier stopping event')
    insist(len(indices)==d['H'] or d['accepted'][indices[-1]],'stopped before accepted or cap')
    insist(z==attempts[-1], 'registered terminal selection violated')
    insist(attempt_commitment(protocol_pin,attempts)==attempts_pin,'attempts not independently pinned')
    return indices,labels


def prefix_rank(d, indices):
    """Rank conditional on observed terminal allocation and stopping time.

    Earlier attempts must all belong to the rejection set and are IID uniform
    conditional on the recorded stopping time and terminal allocation.
    """
    rejected=d['rejected'];R=d['R'];t=len(indices)
    if t==1:return 1,1
    insist(R>0,'impossible rejected prefix')
    rank=1
    lookup={v:i for i,v in enumerate(rejected)}
    for i in indices[:-1]:rank=(rank-1)*R+lookup[i]+1
    return rank,R**(t-1)


def audit(p,e,*,protocol_pin,attempts_pin):
    d=design(p)
    indices,labels=validate(p,e,d,protocol_pin,attempts_pin)
    zidx=indices[-1];z=d['space'][zidx]
    rank,M=prefix_rank(d,indices)
    assert 1<=rank<=M
    by_ate={};witnesses={};compatible=0
    for digits in product(range(4),repeat=d['n']):
        world=tuple(((v>>1)&1,v&1) for v in digits)
        zset=set(z)
        misses=sum(v!='01' and v!=str(world[i][int(i in zset)]) for i,v in enumerate(labels))
        if misses>d['K']:continue
        compatible+=1
        ate=sum(y1-y0 for y0,y1 in world)
        stats=[effect_stat(world, alt, d['n'], d['k']) for alt in d['space']]
        observed=stats[zidx]
        gt=sum(m for m,s in zip(d['mass'],stats) if s>observed)
        eq=sum(m for m,s in zip(d['mass'],stats) if s==observed)
        numerator=gt*M+eq*rank
        if numerator>by_ate.get(ate,-1):
            by_ate[ate]=numerator
            witnesses[ate]=[''.join(map(str,v)) for v in world]
    insist(compatible>0,'no compatible worlds')
    curve=[]; peak=-1
    for a in range(-d['n'],d['n']+1):
        peak=max(peak,by_ate.get(a,-1))
        curve.append({'ate_upper':str(Fraction(a,d['n'])),'null_feasible':peak>=0,
                      'max_p':str(Fraction(peak,d['total']*M)) if peak>=0 else None})
    # ATE<=1 is tautologically true; guard rounding and confidence endpoint.
    curve[-1]['max_p']='1';curve[-1]['null_feasible']=True
    relevant=[a for a in curve if Fraction(a['ate_upper'])<=d['null']][-1]
    lower=next((a['ate_upper'] for a in curve if a['null_feasible'] and Fraction(a['max_p'])>d['alpha']),None)
    candidates=[a for a,v in by_ate.items() if Fraction(a,d['n'])<=d['null']]
    witness=(witnesses[max(candidates,key=lambda a:by_ate[a])] if candidates else None)
    return {'status':'CONDITIONALLY_VERIFIED' if relevant['null_feasible'] else 'INCONSISTENT_NULL',
            'conditional_p':relevant['max_p'],'conditional_lower_ate':lower,
            'confidence_alpha':str(d['alpha']),'compatible_worlds':compatible,
            'design_denominator':str(d['total']), 'selected_assignment_mass':str(d['mass'][zidx]),
            'stopping_time':len(indices),'rejected_prefix_rank':str(rank),
            'rejected_prefix_mass':str(M),'null_curve':curve,'maximizing_world':witness,
            'protocol_sha256':protocol_pin,'attempts_sha256':attempts_pin,
            'warning':'Conditional statistical result, NOT physical authentication. Requires IID candidate draws, preregistered outcome-blind acceptance threshold and stopping cap, immutable attempt history, valid measurement intervals and correct protocol pin.'}


def main():
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('protocol');parser.add_argument('evidence')
    parser.add_argument('--protocol-pin',required=True);parser.add_argument('--attempts-pin',required=True)
    args=parser.parse_args()
    try:report=audit(load_strict(args.protocol),load_strict(args.evidence),
                     protocol_pin=args.protocol_pin,attempts_pin=args.attempts_pin)
    except (Reject,ValueError,TypeError,OverflowError,KeyError,OSError) as err:parser.exit(2,'REJECTED: '+str(err)+'\n')
    print(json.dumps(report,indent=2,sort_keys=True))

if __name__=='__main__':main()
