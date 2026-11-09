"""Exhaustive finite-model, regression, and adversarial tests for v16."""
import copy
import random
import unittest
from fractions import Fraction
from itertools import product

from kernel import Reject, FORMAT, digest, design_distribution, robust_test, effect_stat


def protocol(n=6, k=3, b=2, law='iid_with_replacement', x=None, K=0):
    return {'format': FORMAT, 'n': n, 'k': k,
            'baseline_covariate': [0,0,0,1,1,1][:n] if x is None else x,
            'candidate_draws': b, 'candidate_law': law,
            'selection_rule': 'minimum_absolute_baseline_imbalance_first_tie',
            'null_ate_upper': '0', 'max_interval_misses': K}


def evidence(z, attempts, world=None):
    if world is None:
        labels = ['1' if i in z else '0' for i in range(6)]
    else:
        zset = set(z)
        labels = [str(y[int(i in zset)]) for i, y in enumerate(world)]
    return {'attempts': [list(a) for a in attempts], 'selected_assignment': list(z),
            'observed_intervals': labels}


class TestExactDesign(unittest.TestCase):
    def test_precommitted_design_mass(self):
        p = protocol()
        space, scores, mass, total = design_distribution(p)
        self.assertEqual(total, 400)
        self.assertEqual(mass[space.index((0,1,2))], 2)
        self.assertEqual(mass[space.index((0,1,3))], 22)
        self.assertEqual(sum(mass), total)

    def test_selective_exact_beats_generic_worst_case_on_declared_example(self):
        p = protocol()
        z = (0,1,2)
        r = robust_test(p, evidence(z, [z,z]), external_pin=digest(p))
        self.assertEqual(r['conditional_robust_p'], '1/200')
        self.assertEqual(r['compatible_worlds'], 1)
        # With 2 IID outcome-peeking retries and uniform allocations:
        self.assertLess(Fraction(r['conditional_robust_p']), Fraction(39,400))
        self.assertEqual(r['maximizing_world'], ['11']*3 + ['00']*3)

    def test_covariate_balanced_assignment(self):
        p = protocol()
        z=(0,1,3)
        r=robust_test(p,evidence(z,[z,z]),external_pin=digest(p))
        self.assertEqual(r['conditional_robust_p'], '11/200')

    def test_without_replacement(self):
        p=protocol(law='ordered_without_replacement')
        s,_,m,denom=design_distribution(p)
        self.assertEqual(denom,380)
        self.assertEqual(sum(m),380)
        z=(0,1,2)
        a=(3,4,5)
        r=robust_test(p,evidence(z,[z,a]),external_pin=digest(p))
        self.assertEqual(r['status'],'CONDITIONALLY_VERIFIED')
        with self.assertRaises(Reject):
            robust_test(p,evidence(z,[z,z]),external_pin=digest(p))

    def test_bad_winner_rejected(self):
        p=protocol()
        with self.assertRaisesRegex(Reject,'selected candidate'):
            robust_test(p,evidence((0,1,2),[(0,1,3),(0,1,2)]),external_pin=digest(p))

    def test_pinned_protocol_tampering_rejected(self):
        p=protocol(); old=digest(p)
        for key,val in [('candidate_draws',3),('null_ate_upper','1/3'),('max_interval_misses',1),
                        ('baseline_covariate',[0,0,0,0,0,0])]:
            t=copy.deepcopy(p);t[key]=val
            with self.subTest(key=key),self.assertRaisesRegex(Reject,'independent pin'):
                robust_test(t,evidence((0,1,2),[(0,1,2)]*2),external_pin=old)

    def test_untrusted_report_tampering_rejected(self):
        p=protocol(); z=(0,1,2)
        base=evidence(z,[z,z]); pin=digest(p)
        cases=[dict(base,attempts=[list(z)]),dict(base,attempts=[list(z),[0,1,3]]),
               dict(base,selected_assignment=[0,1,3]),
               dict(base,observed_intervals=['2']*6),
               dict(base,attempts=[[True,1,2],list(z)]),
               dict(base,extra='unauthorized')]
        for e in cases:
            with self.subTest(e=e),self.assertRaises(Reject):
                robust_test(p,e,external_pin=pin)

    def test_missing_external_pin_rejected(self):
        p=protocol();z=(0,1,2)
        with self.assertRaises(Reject):
            robust_test(p,evidence(z,[z,z]),external_pin='0'*64)

    def test_failure_tolerance_does_not_improve_p(self):
        p=protocol(); z=(0,1,2)
        e=evidence(z,[z,z]);e['observed_intervals'][0]='0'
        tight=robust_test(p,e,external_pin=digest(p))
        self.assertEqual(tight['status'],'CONDITIONALLY_VERIFIED')
        q=protocol(K=1)
        loose=robust_test(q,e,external_pin=digest(q))
        self.assertEqual(loose['status'],'CONDITIONALLY_VERIFIED')
        self.assertGreaterEqual(Fraction(loose['conditional_robust_p']), Fraction(tight['conditional_robust_p']))

    def test_exact_finite_design_validity_every_binary_world_n3(self):
        # Stronger than simulation: every one of 4^3 binary potential tables
        # and all selected allocations are exhaustively covered.
        p=protocol(n=3,k=1,b=2,x=[0,1,2])
        space,_,mass,total=design_distribution(p)
        alphas=[Fraction(1,20),Fraction(1,10),Fraction(1,4),Fraction(1,2),Fraction(3,4)]
        worlds=0
        for inds in product(range(4),repeat=3):
            world=[((i>>1)&1,i&1) for i in inds]
            if sum(y1-y0 for y0,y1 in world)>0:
                continue
            worlds+=1
            pvals={}
            for z,w in zip(space,mass):
                if not w: continue
                # Existence of a syntactically valid transcript selecting z.
                # A 2-copy tuple always selects z for with-replacement designs.
                e=evidence(z,[z,z],world)
                r=robust_test(p,e,external_pin=digest(p))
                self.assertEqual(r['status'],'CONDITIONALLY_VERIFIED')
                pvals[z]=Fraction(r['conditional_robust_p'])
                # The true-world tail is a lower bound on composite p.
                stat=effect_stat(world,z,3,1)
                true_tail=sum(m for zz,m in zip(space,mass) if m and effect_stat(world,zz,3,1)>=stat)
                self.assertGreaterEqual(pvals[z],Fraction(true_tail,total))
            for a in alphas:
                reject_mass=sum(m for z,m in zip(space,mass) if m and pvals[z]<=a)
                self.assertLessEqual(Fraction(reject_mass,total),a)
        self.assertGreater(worlds,0)

    def test_every_null_binary_world_n4_without_replacement(self):
        # All 4^4 potential outcome tables, every supported selected allocation,
        # and every attainable p-value threshold (not just chosen alpha values).
        p=protocol(n=4,k=2,b=2,law='ordered_without_replacement',x=[0,1,1,2])
        space,scores,mass,total=design_distribution(p)
        from itertools import product
        for vals in product(range(4),repeat=4):
            world=[((v>>1)&1,v&1) for v in vals]
            if sum(b-a for a,b in world)>0:continue
            pvals={}
            for z,m in zip(space,mass):
                if m==0:continue
                # Find any two distinct allocations selected by the fixed rule.
                transcript=next(( [list(a),list(b)] for a,b in product(space,repeat=2)
                                 if a!=b and min((a,b),key=lambda t:scores[space.index(t)])==z ),None)
                self.assertIsNotNone(transcript)
                report=evidence(z,transcript,world)
                r=robust_test(p,report,external_pin=digest(p))
                self.assertEqual(r['status'],'CONDITIONALLY_VERIFIED')
                true_stat=effect_stat(world,z,4,2)
                true_tail=sum(w for zz,w in zip(space,mass) if w and effect_stat(world,zz,4,2)>=true_stat)
                reported=Fraction(r['conditional_robust_p'])
                self.assertGreaterEqual(reported,Fraction(true_tail,total))
                pvals[z]=reported
            for alpha in set(pvals.values()):
                false_positive_mass=sum(w for z,w in zip(space,mass) if w and pvals[z]<=alpha)
                self.assertLessEqual(Fraction(false_positive_mass,total),alpha)

    def test_multiple_premise_violations_fail_closed(self):
        p=protocol()
        for change in [('n',8),('candidate_draws',4),('selection_rule','look_at_outcomes'),
                       ('candidate_law','unknown'),('null_ate_upper','0.0'),
                       ('max_interval_misses',True),('baseline_covariate',[0.1]*6)]:
            t=copy.deepcopy(p);t[change[0]]=change[1]
            with self.subTest(change=change),self.assertRaises(Reject):
                design_distribution(t)


if __name__ == '__main__':
    unittest.main()
