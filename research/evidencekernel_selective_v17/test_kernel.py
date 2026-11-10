"""Algebraic histogram oracle, exhaustive confidence coverage, and adversarial tests."""
import copy
import random
import unittest
from fractions import Fraction
from itertools import combinations, permutations, product
from math import comb

from kernel import (FORMAT, Reject, audit, design, digest, effect_stat, fall,
                    observed_world_misses)


def protocol(n=6,k=3,b=2,law='iid_with_replacement',x=None,K=0,h='0',alpha='1/20'):
    if x is None:x=[0]*((n+1)//2)+[1]*(n//2)
    return {'format':FORMAT,'n':n,'k':k,'baseline_covariate':x,
            'candidate_draws':b,'candidate_law':law,
            'selection_rule':'minimum_absolute_baseline_imbalance_first_tie',
            'null_ate_upper':h,'max_interval_misses':K,'confidence_alpha':alpha,
            'randomizer_support':16,'randomizer_rule':'independent_right_endpoint_uniform'}


def evidence(z,attempts,world=None):
    if world is None:
        values=['1' if i in z else '0' for i in range(max(z)+1)]
    else:
        values=[str(pair[int(i in z)]) for i,pair in enumerate(world)]
    return {'attempts':[list(a) for a in attempts],
            'selected_assignment':list(z), 'observed_intervals':values}


def brute_mass(n,k,scores,b,law):
    N=comb(n,k);m=[0]*N
    draws=(product(range(N),repeat=b) if law=='iid_with_replacement'
           else permutations(range(N),b))
    for chosen in draws:m[min(chosen,key=lambda i:scores[i])]+=1
    return m


class DesignProofTests(unittest.TestCase):
    def test_complete_histogram_differential(self):
        for n in range(2,7):
            for k in range(1,n):
                N=comb(n,k)
                if N>20:continue
                for seed in range(3):
                    x=[random.Random(1900+n*100+k*10+seed+i).randrange(-2,3) for i in range(n)]
                    for law in ['iid_with_replacement','ordered_without_replacement']:
                        for b in range(1,min(3,N)+1):
                            p=protocol(n,k,b,law,x)
                            space,scores,counts,total=design(p)
                            self.assertEqual(sum(counts),total)
                            self.assertEqual(counts,brute_mass(n,k,scores,b,law))

    def test_v16_regression(self):
        p=protocol()
        space,scores,m,total=design(p)
        self.assertEqual(total,400)
        self.assertEqual(m[space.index((0,1,2))],2)
        self.assertEqual(m[space.index((0,1,3))],22)
        z=[0,1,2]
        e={'attempts':[z,z], 'selected_assignment':z, 'observed_intervals':['1']*3+['0']*3}
        a=audit(p,e,external_pin=digest(p))
        self.assertEqual(a['conditional_robust_p'],'1/200')
        self.assertEqual(a['conditional_lower_ate'],'1/3')
        self.assertEqual(a['maximizing_world'],['11']*3+['00']*3)

    def test_loss_of_support_in_without_replacement(self):
        p=protocol(n=5,k=2,b=9,law='ordered_without_replacement',x=[0,0,0,10,10])
        space,scores,m,total=design(p)
        self.assertEqual(total,fall(len(space),9))
        self.assertTrue(any(w==0 for w in m))

    def test_all_equal_scores_are_uniform(self):
        for law in ['iid_with_replacement','ordered_without_replacement']:
            p=protocol(n=6,k=3,b=4,law=law,x=[1]*6)
            _,scores,m,total=design(p)
            self.assertEqual(len(set(scores)),1)
            self.assertEqual(len(set(m)),1)
            self.assertEqual(sum(m),total)

    def test_more_than_one_septillion_candidate_tuples_without_enumeration(self):
        p=protocol(n=8,k=4,b=16,law='iid_with_replacement')
        space,scores,m,total=design(p)
        self.assertGreater(total,10**29)
        self.assertEqual(total,70**16)
        self.assertEqual(sum(m),total)

    def test_tie_rule_first_candidate(self):
        p=protocol(n=4,k=2,b=2,x=[0,0,1,1])
        z=[0,2];a=[1,2]
        _,scores,m,_=design(p)
        self.assertEqual(scores[list(combinations(range(4),2)).index(tuple(z))],scores[list(combinations(range(4),2)).index(tuple(a))])
        e={'attempts':[a,z],'selected_assignment':z,'observed_intervals':['01']*4}
        with self.assertRaisesRegex(Reject,'selection'):
            audit(p,e,external_pin=digest(p))

    def test_tampering_against_pinned_design(self):
        p=protocol();z=[0,1,2]
        e={'attempts':[z,z],'selected_assignment':z,'observed_intervals':['1']*3+['0']*3}
        pin=digest(p)
        for key,val in [('candidate_draws',10),('null_ate_upper','1/6'),('confidence_alpha','1/4'),
                        ('candidate_law','ordered_without_replacement'),('max_interval_misses',1),
                        ('baseline_covariate',[0]*6)]:
            bad=copy.deepcopy(p);bad[key]=val
            with self.subTest(key=key),self.assertRaisesRegex(Reject,'pin'):
                audit(bad,e,external_pin=pin)

    def test_without_replacement_attempt_replay(self):
        p=protocol(n=5,k=2,b=3,law='ordered_without_replacement')
        z=[0,3];e={'attempts':[z,z,[0,2]],'selected_assignment':z,'observed_intervals':['01']*5}
        with self.assertRaisesRegex(Reject,'duplicate'):
            audit(p,e,external_pin=digest(p))

    def test_reject_unsupported_and_noncanonical(self):
        for key,val in [('n',9),('k',0),('candidate_draws',4097),('confidence_alpha','0.05'),
                        ('null_ate_upper','0/1'),('max_interval_misses',True),
                        ('candidate_law','adversarial'),('baseline_covariate',[0.1]*6)]:
            p=protocol();p[key]=val
            with self.subTest(key=key), self.assertRaises(Reject):design(p)

    def test_unmatched_or_missing_attempts(self):
        p=protocol();z=[0,1,2]
        for attempts in [[],[z],[[0,1,3],z]]:
            e={'attempts':attempts,'selected_assignment':z,'observed_intervals':['01']*6}
            with self.assertRaises(Reject):audit(p,e,external_pin=digest(p))

    def test_compatible_world_sensitivity_monotonicity(self):
        p=protocol(n=4,k=2,b=2,x=[0,1,1,2])
        z=[0,1];e={'attempts':[z,z], 'selected_assignment':z, 'observed_intervals':['1','1','0','0']}
        strict=audit(p,e,external_pin=digest(p))
        tolerant=copy.deepcopy(p);tolerant['max_interval_misses']=1
        loose=audit(tolerant,e,external_pin=digest(tolerant))
        for c0,c1 in zip(strict['null_curve'],loose['null_curve']):
            if c0['null_feasible']:
                self.assertTrue(c1['null_feasible'])
                self.assertGreaterEqual(Fraction(c1['max_p']),Fraction(c0['max_p']))
        self.assertGreaterEqual(loose['compatible_worlds'],strict['compatible_worlds'])


class StatisticalCoverageTests(unittest.TestCase):
    def test_every_true_world_confidence_bound_n3_and_n4(self):
        # Exact finite-sample coverage for all binary worlds, all supported
        # selected assignments, all reported data generated from each world.
        for n,k,b,x in [(3,1,2,[0,1,2]),(4,2,2,[0,0,1,2])]:
            p=protocol(n,k,b,x=x,alpha='1/4')
            space,scores,m,total=design(p)
            for inds in product(range(4),repeat=n):
                world=[((a>>1)&1,a&1) for a in inds]
                true_ate=Fraction(sum(y1-y0 for y0,y1 in world),n)
                violations=0
                for z,weight in zip(space,m):
                    if not weight:continue
                    r=audit(p,evidence(z,[z,z],world),external_pin=digest(p))
                    self.assertEqual(r['status'],'CONDITIONALLY_VERIFIED' if r['null_feasible'] else 'INCONSISTENT_NULL')
                    if r['conditional_lower_ate'] is None or Fraction(r['conditional_lower_ate'])>true_ate:
                        violations+=weight
                    # Exact tail true Y cannot be larger than max composite null at actual ATE.
                    stat=effect_stat(world,z,n,k)
                    truth=Fraction(sum(mm for zz,mm in zip(space,m)
                                       if effect_stat(world,zz,n,k)>=stat),total)
                    c=next(c for c in r['null_curve'] if Fraction(c['ate_upper'])==true_ate)
                    self.assertTrue(c['null_feasible'])
                    self.assertGreaterEqual(Fraction(c['max_p']),truth)
                self.assertLessEqual(Fraction(violations,total),Fraction(1,4))

    def test_inverted_p_curve_monotonic(self):
        p=protocol(n=5,k=2,b=3,x=[0,0,0,1,1]);z=[0,1]
        e={'attempts':[z]*3,'selected_assignment':z,'observed_intervals':['1','1','0','0','0']}
        r=audit(p,e,external_pin=digest(p))
        vals=[Fraction(c['max_p']) for c in r['null_curve'] if c['null_feasible']]
        self.assertEqual(vals,sorted(vals))
        self.assertGreater(len(vals),1)


if __name__=='__main__':unittest.main()

class RandomizedTieInferenceTests(unittest.TestCase):
    def test_independent_uniform_randomizer_exact_superuniform_n4_all_worlds(self):
        # Exhaust every binary potential-outcome table (4^4), every allocation
        # and all 8 independent randomizer outcomes. Cache audits by observable
        # data rather than recomputing for the same dataset under many worlds.
        p=protocol(n=4,k=2,b=2,x=[0,0,1,2],alpha='1/20')
        p['randomizer_support']=8
        space,scores,mass,total=design(p)
        pin=digest(p)
        cache={}
        for z,w in zip(space,mass):
            if not w:continue
            for observed in product(['0','1'],repeat=4):
                e={'attempts':[list(z),list(z)],'selected_assignment':list(z),
                   'observed_intervals':list(observed)}
                for j in range(1,9):
                    cache[(z,observed,j)]=audit(p,e,external_pin=pin,external_uniform_index=j)
        for vals in product(range(4),repeat=4):
            world=tuple(((v>>1)&1,v&1) for v in vals)
            ate=Fraction(sum(a-b for b,a in world),4)
            errors=0
            for z,w in zip(space,mass):
                if w==0:continue
                s=set(z)
                observed=tuple(str(world[i][int(i in s)]) for i in range(4))
                observed_stat=effect_stat(world,z,4,2)
                gt=sum(ww for zz,ww in zip(space,mass) if effect_stat(world,zz,4,2)>observed_stat)
                eq=sum(ww for zz,ww in zip(space,mass) if effect_stat(world,zz,4,2)==observed_stat)
                for j in range(1,9):
                    report=cache[(z,observed,j)]
                    true_p=Fraction(8*gt+j*eq,8*total)
                    candidate=next(t for t in report['randomized_null_curve'] if Fraction(t['ate_upper'])==ate)
                    self.assertTrue(candidate['null_feasible'])
                    self.assertGreaterEqual(Fraction(candidate['max_p']),true_p)
                    lower=report['randomized_conditional_lower_ate']
                    if lower is None or Fraction(lower)>ate:
                        errors+=w
            # Exact probability over selection design and independent uniform J.
            self.assertLessEqual(Fraction(errors,8*total),Fraction(1,20))

    def test_maximum_effect_power_gain_is_valid_conditional_on_independent_uniform(self):
        p=protocol();space,scores,mass,total=design(p)
        alpha=Fraction(1,20);rejections_plain=0;rejections_rand=0
        for z,w in zip(space,mass):
            if w==0:continue
            e={'attempts':[list(z)]*2, 'selected_assignment':list(z),
               'observed_intervals':['1' if i in z else '0' for i in range(6)]}
            for j in range(1,17):
                r=audit(p,e,external_pin=digest(p),external_uniform_index=j)
                if Fraction(r['conditional_robust_p'])<=alpha:
                    rejections_plain+=w
                if Fraction(r['randomized_conditional_p'])<=alpha:
                    rejections_rand+=w
        self.assertEqual(Fraction(rejections_plain,16*total),Fraction(1,100))
        self.assertEqual(Fraction(rejections_rand,16*total),Fraction(701,800))
        # The experimental world here is Y(0)=0, Y(1)=1 for all units,
        # a maximum positive causal effect; this is not a prospective trial.

    def test_uniform_source_must_be_separate_and_in_registered_support(self):
        p=protocol();z=[0,1,2]
        e={'attempts':[z,z],'selected_assignment':z,'observed_intervals':['1']*3+['0']*3}
        baseline=audit(p,e,external_pin=digest(p))
        self.assertIsNone(baseline['randomized_conditional_p'])
        for u in [0,17,-1,True,0.5,'8',None]:
            if u is None:continue
            with self.subTest(u=u),self.assertRaises(Reject):
                audit(p,e,external_pin=digest(p),external_uniform_index=u)
        p2=copy.deepcopy(p);p2['randomizer_support']=32
        with self.assertRaisesRegex(Reject,'pin'):
            audit(p2,e,external_pin=digest(p),external_uniform_index=8)

    def test_randomized_bound_never_worse_than_conservative_at_fixed_dataset(self):
        p=protocol(n=5,k=2,b=4,x=[0,0,0,1,1])
        z=[0,1]
        e={'attempts':[z]*4,'selected_assignment':z,'observed_intervals':['1','1','0','0','0']}
        r=audit(p,e,external_pin=digest(p),external_uniform_index=8)
        self.assertLessEqual(Fraction(r['randomized_conditional_p']),Fraction(r['conditional_robust_p']))
        if r['conditional_lower_ate'] is not None and r['randomized_conditional_lower_ate'] is not None:
            self.assertGreaterEqual(Fraction(r['randomized_conditional_lower_ate']),Fraction(r['conditional_lower_ate']))

class RandomizerThreatModelTests(unittest.TestCase):
    def test_adversarially_picking_favorable_index_breaks_level(self):
        # Exact counterexample: replacing the independent uniform source with
        # researcher-chosen J=1 yields 22.22% false positives for a nominal 5%
        # test in this concrete n=4 selection design.
        p=protocol(n=4,k=2,b=2,x=[0,0,1,2],alpha='1/20')
        p['randomizer_support']=8
        A,_,mass,denom=design(p)
        observed_cache={}
        for z in A:
            for obs in product(['0','1'],repeat=4):
                e={'attempts':[list(z),list(z)],'selected_assignment':list(z),'observed_intervals':list(obs)}
                observed_cache[(z,obs)]=audit(p,e,external_pin=digest(p),external_uniform_index=1)
        null_world=((0,0),(1,1),(0,0),(1,1))
        rejects=0
        for z,m in zip(A,mass):
            obs=tuple(str(null_world[i][int(i in z)]) for i in range(4))
            pp=observed_cache[(z,obs)]['randomized_conditional_p']
            if pp is not None and Fraction(pp)<=Fraction(1,20):
                rejects+=m
        self.assertEqual(Fraction(rejects,denom),Fraction(2,9))
