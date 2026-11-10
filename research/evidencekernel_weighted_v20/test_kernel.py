"""Finite exact falsification of v20 weighted stopping and conditional CDF."""
import copy
import itertools
import json
import random
import subprocess
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path
from research.evidencekernel_weighted_v20.kernel import (
    FORMAT,RULE,RANK,Reject,design,digest,audit,attempt_commitment,prefix_cdf,
)
from research.evidencekernel_selective_v17.kernel import effect_stat

HERE=Path(__file__).parent

def make(n=4,k=2,H=3, x=None, cutoff=2, weights=None, K=0):
    from math import comb
    N=comb(n,k)
    return {'format':FORMAT,'n':n,'k':k,'baseline_covariate':x if x is not None else list(range(n)),
            'max_attempts':H,'accept_if_score_le':cutoff,'selection_rule':RULE,
            'candidate_law':'registered_independent_weighted_by_step',
            'candidate_weights_by_step':weights if weights is not None else
                [[((t+1)*i+2)%5+1 for i in range(N)] for t in range(H)],
            'null_ate_upper':'0','max_interval_misses':K,
            'confidence_alpha':'1/20','tie_rule':RANK}

def stopped(d):
    """Enumerate positive-weight histories; exact event weight includes unobserved future draws."""
    for t in range(1,d['H']+1):
        slots=[[i for i in range(d['N']) if not d['accepted'][i] and d['weights'][j][i]]
               for j in range(t-1)]
        end=[i for i in range(d['N']) if d['weights'][t-1][i] and
             (t==d['H'] or d['accepted'][i])]
        for prefix in itertools.product(*slots):
            for last in end:
                seq=prefix+(last,)
                mass=1
                for j,i in enumerate(seq):mass*=d['weights'][j][i]
                for j in range(t,d['H']):mass*=d['W'][j]
                yield seq,mass

def evidence(d,seq,world=None):
    z=d['space'][seq[-1]]
    labels=['01']*d['n'] if world is None else [str(world[i][int(i in z)]) for i in range(d['n'])]
    return {'attempts':[list(d['space'][i]) for i in seq],
            'selected_assignment':list(z),'observed_intervals':labels}

class WeightedStoppingTests(unittest.TestCase):
    def test_exact_distribution_matches_bruteforce_weighted_transcripts(self):
        for p in [make(3,1,2,cutoff=1),make(4,2,3,cutoff=2),
                  make(3,1,3,weights=[[2,1,0],[4,1,0],[0,1,9]],cutoff=0),
                  make(4,2,2,cutoff=10000)]:
            d=design(p)
            sums=[0]*d['N']
            for seq,w in stopped(d):
                sums[seq[-1]]+=w
                a,b=prefix_cdf(d,seq)
                self.assertTrue(0<a<=b)
            self.assertEqual(sums,d['mass'])
            self.assertEqual(sum(sums),d['total'])

    def test_conditional_right_cdf_is_superuniform_exactly(self):
        for p in [make(3,1,3,cutoff=1),make(4,2,2,cutoff=2),
                  make(4,2,3,cutoff=10000)]:
            d=design(p)
            groups={}
            for seq,w in stopped(d):
                r,M=prefix_cdf(d,seq)
                key=(seq[-1],len(seq))
                groups.setdefault(key,[]).append((Fraction(r,M),w))
            for events in groups.values():
                total=sum(w for _,w in events)
                for alpha in sorted(set(v for v,_ in events)):
                    self.assertLessEqual(Fraction(sum(w for v,w in events if v<=alpha),total),alpha)

    def test_exact_superuniformity_every_true_binary_world(self):
        for p in [make(3,1,3,cutoff=1),make(4,2,2,cutoff=2)]:
            d=design(p)
            worlds=[tuple(((v>>1)&1,v&1) for v in digits)
                    for digits in itertools.product(range(4),repeat=d['n'])]
            histories=list(stopped(d))
            for world in worlds:
                stats=[effect_stat(world,z,d['n'],d['k']) for z in d['space']]
                points=[]
                for seq,w in histories:
                    r,M=prefix_cdf(d,seq)
                    observed=stats[seq[-1]]
                    gt=sum(m for m,s in zip(d['mass'],stats) if s>observed)
                    eq=sum(m for m,s in zip(d['mass'],stats) if s==observed)
                    points.append((Fraction(gt*M+eq*r,d['total']*M),w))
                for alpha in set(v for v,_ in points):
                    false=sum(w for v,w in points if v<=alpha)
                    self.assertLessEqual(Fraction(false,d['total']),alpha)

    def test_composite_weak_null_controls_level_in_every_small_world(self):
        p=make(3,1,2,cutoff=1);p['confidence_alpha']='1/10'
        d=design(p);histories=list(stopped(d));pin=digest(p)
        for digits in itertools.product(range(4),repeat=d['n']):
            w=tuple(((v>>1)&1,v&1) for v in digits)
            if sum(b-a for a,b in w)>0:continue
            false=0
            for seq,weight in histories:
                e=evidence(d,seq,w)
                r=audit(p,e,protocol_pin=pin,attempts_pin=attempt_commitment(pin,e['attempts']))
                if r['conditional_p'] is not None and Fraction(r['conditional_p'])<=Fraction(1,10):false+=weight
            self.assertLessEqual(Fraction(false,d['total']),Fraction(1,10))

    def test_unweighted_prefix_rank_can_cause_massive_false_discovery(self):
        p=make(5,2,3,[0,2,3,6,11],1,weights=[[100]+[1]*9,[100]+[1]*9,[1]*10])
        d=design(p)
        # Sharp null: every potential outcome is zero, so statistic always ties.
        correct=naive=0
        for seq,w in stopped(d):
            r,M=prefix_cdf(d,seq)
            if Fraction(r,M)<=Fraction(1,20):correct+=w
            # Invalid v19 unweighted lex rank applied to v20's nonuniform rejected prefix.
            rejected=[i for i,v in enumerate(d['accepted']) if not v]
            rank=0
            for i in seq[:-1]:rank=rank*len(rejected)+rejected.index(i)
            nr=Fraction(rank+1,len(rejected)**(len(seq)-1))
            if nr<=Fraction(1,20):naive+=w
        self.assertLessEqual(Fraction(correct,d['total']),Fraction(1,20))
        self.assertGreater(Fraction(naive,d['total']),Fraction(4,5))
        self.assertEqual(d['R'][:2],[108,108])
        self.assertEqual(d['total'],118810)
        self.assertEqual(correct,0)
        print('COUNTEREXAMPLE correct:',Fraction(correct,d['total']),
              'naive:',Fraction(naive,d['total']))

    def test_dependent_draws_with_correct_marginals_break_level(self):
        # Actual mechanism: draw X uniformly; attempt 2 is X again; attempt 3
        # is independent uniform. Every *unconditional* draw is marginally
        # uniform, but the first two draws are dependent. On the sharp all-zero
        # null, the registered IID prefix right-CDF is no longer calibrated.
        p=make(5,2,3,[0,2,3,6,11],1,weights=[[1]*10]*3)
        d=design(p)
        alpha=Fraction(1,20)
        claimed_null_reject=0
        for seq,w in stopped(d):
            r,M=prefix_cdf(d,seq)
            if Fraction(r,M)<=alpha:claimed_null_reject+=w
        # The precommitted IID mechanism has 4% size in this example.
        self.assertEqual(Fraction(claimed_null_reject,d['total']),Fraction(1,25))
        # In the *different*, dependent mechanism X1=X2, each first choice
        # has probability 1/10; if X is unacceptable, terminal Y~Uniform(10).
        wrong_null_reject=0
        for i in range(d['N']):
            for y in range(d['N']):
                if d['accepted'][i]:seq=(i,)
                else:seq=(i,i,y)
                r,M=prefix_cdf(d,seq)
                if Fraction(r,M)<=alpha:wrong_null_reject+=1
        self.assertEqual(Fraction(wrong_null_reject,100),Fraction(1,10))
        self.assertGreater(Fraction(wrong_null_reject,100),alpha)

    def test_uniform_limit_matches_v19(self):
        from research.evidencekernel_stopping_v19.kernel import design as v19_design, prefix_rank
        for n,k,H,cutoff in [(3,1,2,1),(4,2,3,2),(4,2,2,10000)]:
            p=make(n,k,H,cutoff=cutoff,weights=[[1]*len(list(itertools.combinations(range(n),k)))]*H)
            d=design(p)
            q={k:v for k,v in p.items() if k!='candidate_weights_by_step'}
            q['format']='pcs-evidencekernel-stopping-v19';q['candidate_law']='iid_with_replacement';q['tie_rule']='within_stop_and_selected_rejected_prefix_lex_rank'
            old=v19_design(q)
            self.assertEqual(d['mass'],old['mass'])
            for seq,_ in stopped(d):
                self.assertEqual(prefix_cdf(d,seq),prefix_rank(old,seq))

    def test_reject_invalid_schedule_and_attempts(self):
        p=make();d=design(p)
        seq=next(seq for seq,_ in stopped(d) if len(seq)>=2)
        e=evidence(d,seq);pin=digest(p);ap=attempt_commitment(pin,e['attempts'])
        self.assertTrue(audit(p,e,protocol_pin=pin,attempts_pin=ap))
        for corrupt in [
            {**p,'candidate_weights_by_step':p['candidate_weights_by_step'][:-1]},
            {**p,'candidate_weights_by_step':[[0]*d['N']]+p['candidate_weights_by_step'][1:]},
            {**p,'candidate_weights_by_step':[[True]+p['candidate_weights_by_step'][0][1:]]+p['candidate_weights_by_step'][1:]},
            {**p,'candidate_law':'response_adaptive'},
            {**p,'candidate_weights_by_step':[[20000]+p['candidate_weights_by_step'][0][1:]]+p['candidate_weights_by_step'][1:]},
        ]:
            with self.assertRaises(Reject):design(corrupt)
        with self.assertRaises(Reject):audit(p,e,protocol_pin='0'*64,attempts_pin=ap)
        e2=copy.deepcopy(e);e2['attempts'][0]=list(d['space'][-1])
        with self.assertRaises(Reject):audit(p,e2,protocol_pin=pin,attempts_pin=ap)
        # Zero-probability allocations are rejected even with correctly recomputed self-contained hashes.
        p3=make(n=3,k=1,H=2,weights=[[0,1,1],[0,1,1]])
        d3=design(p3);seq3=(0,1)
        e3=evidence(d3,seq3);pin3=digest(p3)
        with self.assertRaisesRegex(Reject,'zero-probability'):
            audit(p3,e3,protocol_pin=pin3,attempts_pin=attempt_commitment(pin3,e3['attempts']))

    def test_nonstationary_exact_weights_up_to_128_attempts(self):
        p=make(8,4,128,cutoff=10000)
        d=design(p)
        self.assertEqual(sum(d['mass']),d['total'])
        self.assertGreater(len(str(d['total'])),200)
        self.assertEqual(len(d['space']),70)

if __name__=='__main__':unittest.main()
