"""Exact transcript-rank invariance, independent brute-force checks and attacks."""
import copy
import itertools
import json
import random
import unittest
from fractions import Fraction
from pathlib import Path
from research.evidencekernel_selective_v17.kernel import design, digest, effect_stat, Reject
from research.evidencekernel_transcript_v18.kernel import (
    FORMAT, TIE_RULE, audit, lex_before_histogram, selected_histogram_after_prefix, v17_adapter
)


def protocol(n=4,k=2,b=2,law='iid_with_replacement',cov=None,K=0):
    return {'format':FORMAT,'n':n,'k':k,'baseline_covariate':cov if cov is not None else list(range(n)),
            'candidate_draws':b,'candidate_law':law,
            'selection_rule':'minimum_absolute_baseline_imbalance_first_tie',
            'null_ate_upper':'0','max_interval_misses':K,
            'confidence_alpha':'1/20','tie_rule':TIE_RULE}


def possible_sequences(N,b,law):
    if law=='iid_with_replacement':return itertools.product(range(N),repeat=b)
    return itertools.permutations(range(N),b)


def rank_hist_reference(scores, space, seq, law):
    N=len(space)
    prior=[0]*N
    for candidate in possible_sequences(N,len(seq),law):
        if candidate>=tuple(seq):break
        winner=min(candidate,key=lambda i:scores[i])
        prior[winner]+=1
    return prior


class TranscriptRankTests(unittest.TestCase):
    def test_histogram_exhaustive_small_candidate_spaces(self):
        rng=random.Random(91234)
        for n,k,b in [(3,1,2),(4,2,2),(4,2,3),(5,1,2)]:
            for law in ('iid_with_replacement','ordered_without_replacement'):
                for seed in range(3):
                    p=protocol(n,k,b,law,[rng.randint(-2,2) for _ in range(n)])
                    space,scores,mass,total=design(v17_adapter(p))
                    seqs=list(possible_sequences(len(space),b,law))
                    # Different observed transcripts, including first and last.
                    for seq in [seqs[0],seqs[len(seqs)//3],seqs[len(seqs)//2],seqs[-1]]:
                        expected=rank_hist_reference(scores,space,seq,law)
                        attempts=[list(space[i]) for i in seq]
                        self.assertEqual(lex_before_histogram(space,scores,attempts,law),expected)
                        self.assertEqual(sum(expected),seqs.index(seq))

    def test_uniform_rank_every_binary_world_n4(self):
        # Conditional on selected allocation Z=z, transcript rank is uniform;
        # the resulting randomized p-value is superuniform for every world.
        p=protocol(4,2,2,'iid_with_replacement',[0,1,1,2])
        space,scores,mass,total=design(v17_adapter(p))
        seqs=list(possible_sequences(len(space),2,'iid_with_replacement'))
        before={seq:lex_before_histogram(space,scores,[list(space[i]) for i in seq],'iid_with_replacement')
                for seq in seqs}
        for digits in itertools.product(range(4),repeat=4):
            world=tuple(((v>>1)&1,v&1) for v in digits)
            stat=[effect_stat(world,z,4,2) for z in space]
            ranks=[]
            for seq in seqs:
                zidx=min(seq,key=lambda i:scores[i]);t=stat[zidx]
                gt=sum(w for w,s in zip(mass,stat) if s>t)
                eq=sum(w for w,s in zip(mass,stat) if s==t)
                r=before[seq][zidx]+1
                ranks.append(Fraction(gt,total)+Fraction(r*eq,total*mass[zidx]))
            for threshold in [Fraction(i,total) for i in range(1,total+1)]:
                self.assertLessEqual(sum(pv<=threshold for pv in ranks), threshold*total)

    def test_composite_weak_null_finite_level_n3(self):
        p=protocol(3,1,2,'iid_with_replacement',[0,1,2]);p['confidence_alpha']='1/9'
        space,scores,mass,total=design(v17_adapter(p))
        for digits in itertools.product(range(4),repeat=3):
            world=tuple(((v>>1)&1,v&1) for v in digits)
            ate=sum(y1-y0 for y0,y1 in world)
            if ate>0:continue
            rejections=0
            for seq in possible_sequences(len(space),2,'iid_with_replacement'):
                z=space[min(seq,key=lambda i:scores[i])]
                labels=[str(world[i][int(i in z)]) for i in range(3)]
                e={'attempts':[list(space[i]) for i in seq],
                   'selected_assignment':list(z),'observed_intervals':labels}
                result=audit(p,e,external_pin=digest(p))
                if Fraction(result['conditional_rank_p'])<=Fraction(1,9):rejections+=1
            self.assertLessEqual(Fraction(rejections,total),Fraction(1,9))

    def test_example_and_nonrandomized_comparison(self):
        loc=Path(__file__).parent
        p=json.loads((loc/'example_protocol.json').read_text())
        e=json.loads((loc/'example_evidence.json').read_text())
        r=audit(p,e,external_pin=digest(p))
        self.assertEqual(r['conditional_rank_p'],'1/400')
        self.assertEqual(r['conditional_lower_ate'],'1/2')
        self.assertEqual(r['lexicographically_prior_transcripts'],'0')

    def test_tautological_upper_endpoint_avoids_empty_confidence_set(self):
        p=protocol(6,3,2,cov=[0,0,0,1,1,1]);p['null_ate_upper']='1'
        space,scores,_,_=design(v17_adapter(p))
        e={'attempts':[list(space[0])]*2,'selected_assignment':list(space[0]),
           'observed_intervals':['1']*3+['0']*3}
        r=audit(p,e,external_pin=digest(p))
        self.assertEqual(r['conditional_rank_p'],'1')
        self.assertEqual(r['confidence_set_status'],'NONEMPTY')

    def test_malformed_provenance_and_protocol_fail_closed(self):
        p=protocol();space,_,_,_=design(v17_adapter(p))
        z=space[0];e={'attempts':[list(z),list(z)],'selected_assignment':list(z),
                      'observed_intervals':['01']*p['n']}
        pin=digest(p)
        with self.assertRaisesRegex(Reject,'mismatched'): audit({**p,'tie_rule':'bogus'},e,external_pin=pin)
        with self.assertRaises(Reject): audit(p,{**e,'attempts':e['attempts'][:1]},external_pin=pin)
        with self.assertRaises(Reject): audit(p,{**e,'selected_assignment':[1,3]},external_pin=pin)
        q=copy.deepcopy(p);q['tie_rule']='choose_posthoc';
        with self.assertRaises(Reject): audit(q,e,external_pin=digest(q))

    def test_counting_with_many_draws_without_tuple_enumeration(self):
        p=protocol(8,4,128,'iid_with_replacement',[0,0,0,0,1,1,1,1]);
        space,scores,mass,total=design(v17_adapter(p))
        attempts=[list(space[0])]*128
        before=lex_before_histogram(space,scores,attempts,p['candidate_law'])
        self.assertEqual(sum(before),0)
        attempts=[list(space[-1])]*128
        before=lex_before_histogram(space,scores,attempts,p['candidate_law'])
        self.assertEqual(sum(before),total-1)

if __name__ == '__main__':unittest.main()
