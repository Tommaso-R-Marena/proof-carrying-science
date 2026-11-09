"""Exact checks, cross-version regression, closed-form null attacks, finite-model validity."""
from __future__ import annotations
import copy
from fractions import Fraction as F
from itertools import product
from math import comb
from pathlib import Path
import json
import unittest
from . import kernel as m
from . import make_demo

ROOT=Path(__file__).parent
V24=ROOT.parent/'evidencekernel_anytime_v24'

class PropensityUpperTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p=json.loads((ROOT/'example_protocol.json').read_text())
        cls.e=json.loads((ROOT/'example_evidence.json').read_text())

    def audit(self,p,e):
        pin=m.digest(p)
        return m.audit(p,e,protocol_pin=pin,evidence_pin=m.evidence_digest(pin,e))

    def test_signed_synthetic_and_independent_known_answer(self):
        pp=(ROOT/'example_protocol_pin.txt').read_text().strip()
        ep=(ROOT/'example_evidence_pin.txt').read_text().strip()
        answer=m.audit(self.p,self.e,protocol_pin=pp,evidence_pin=ep)
        self.assertEqual(answer,json.loads((ROOT/'example_report.json').read_text()))
        self.assertEqual(answer['enrolled_units'],457)
        self.assertEqual(answer['anytime_lower_ate'],'8515174471273905593/19000741375306629120')
        self.assertEqual(answer['status'],'CONDITIONALLY_REJECTED')
        self.assertTrue(any(F(c['propensity_upper_bias_penalty'])==0 for c in answer['tuning_results']))
        self.assertTrue(any(F(c['propensity_upper_bias_penalty'])>0 for c in answer['tuning_results']))

    def test_exact_v24_equivalence_when_upper_is_true_reference(self):
        import importlib.util,sys
        previous=V24/'kernel.py'
        spec=importlib.util.spec_from_file_location('v24_checked_kernel',previous)
        old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
        p=json.loads((V24/'example_protocol.json').read_text())
        e=json.loads((V24/'example_evidence.json').read_text())
        old_pin=old.digest(p)
        baseline=old.audit(p,e,protocol_pin=old_pin,evidence_pin=old.evidence_digest(old_pin,e))
        refs=p['allocation_weights_by_state']
        caps=[str(F(w[1],sum(w))) for w in refs]
        newer=make_demo.convert(p,upper=caps,reference_only=True)
        got=self.audit(newer,e)
        self.assertEqual(got['anytime_lower_ate'],baseline['anytime_lower_ate'])
        for fresh,prev in zip(got['tuning_results'],baseline['tuning_results']):
            self.assertEqual(fresh['ate_lower_bound'],prev['ate_lower_bound'])
            self.assertEqual(fresh['martingale_boundary'],prev['martingale_boundary'])
            self.assertEqual(fresh['propensity_upper_bias_penalty'],'0')

    def test_one_sided_conditional_bias_bound_exact(self):
        for q in [F(1,10), F(2,5),F(1,2),F(3,4),F(9,10)]:
            width=1/q+1/(1-q)
            for cap in [F(1,10),F(1,2),F(3,4),F(1)]:
                bias=max(F(0),cap-q)*width
                for actual in [F(0),cap/2,cap]:
                    for y0,y1 in product((0,1),repeat=2):
                        expected=actual*F(y1,q)-(1-actual)*F(y0,1-q)
                        tau=y1-y0
                        self.assertLessEqual(expected-tau,bias)

    def test_interval_miss_budget_same_pathwise_falsification(self):
        # Supports exact robustness to *up to K* wrong intervals for any assignment path.
        for q in (F(1,3),F(1,2),F(4,5)):
            for a,truth,labels in product(product((0,1),repeat=2),
                                           product((0,1),repeat=2),
                                           product(('0','1','01'),repeat=2)):
                mismatches=sum(lab!='01' and int(lab)!=y for lab,y in zip(labels,truth))
                if mismatches>1:continue
                real=F(0);lower=F(0);cost=[]
                for A,y,lab in zip(a,truth,labels):
                    real+=F(y,q) if A else -F(y,1-q)
                    low=int(lab=='1');high=int(lab!='0')
                    lower+=F(low,q) if A else -F(high,1-q)
                    cost.append(F(low,q) if A else F(1-high,1-q))
                self.assertLessEqual(lower-max(cost),real)

    def test_unsupported_or_forged_upper_bounds_fail_closed(self):
        p=copy.deepcopy(self.p);e=copy.deepcopy(self.e)
        pp=m.digest(p);ep=m.evidence_digest(pp,e)
        p['propensity_upper_by_state'][0]='1/2'
        with self.assertRaisesRegex(m.Reject,'registration commitment'):
            m.audit(p,e,protocol_pin=pp,evidence_pin=ep)
        p=copy.deepcopy(self.p);p['propensity_upper_by_state'][0]='0'
        with self.assertRaises(m.Reject):self.audit(p,e)
        p=copy.deepcopy(self.p);p['propensity_upper_by_state'][0]='101/100'
        with self.assertRaises(m.Reject):self.audit(p,e)
        p=copy.deepcopy(self.p);p['propensity_upper_by_state'][0]='62/100'
        with self.assertRaises(m.Reject):self.audit(p,e)
        p=copy.deepcopy(self.p);p['tuning'][0]['reference_weights_by_state']=[[1,0],[1,1],[1,1]]
        with self.assertRaises(m.Reject):self.audit(p,e)
        p=copy.deepcopy(self.p);p['tuning'][0]['alpha_spend']='1/20'
        with self.assertRaises(m.Reject):self.audit(p,e)

    def test_evidence_pin_stop_and_calibration_budget_fail_closed(self):
        e=copy.deepcopy(self.e);e['true_intervals'][9]='01'
        pp=m.digest(self.p);ep=m.evidence_digest(pp,self.e)
        with self.assertRaisesRegex(m.Reject,'observed-prefix'):
            m.audit(self.p,e,protocol_pin=pp,evidence_pin=ep)
        e=copy.deepcopy(self.e)
        e['assignments'].pop();e['reports'].pop();e['true_intervals'].pop()
        with self.assertRaisesRegex(m.Reject,'terminal length'):self.audit(self.p,e)
        p=copy.deepcopy(self.p);p['calibration_failure_bound']='1'
        with self.assertRaises(m.Reject):self.audit(p,self.e)

    def test_actual_propensity_misspecification_attack_vs_upper_valid(self):
        # Research-only exact binomial enumeration of the *fixed-time* v24
        # counterexample. Truth is Y0=Y1=1; sample A~Bernoulli(0.9).
        n=64;actual=F(9,10);c=F(3);lam=F(1,8)
        self.assertGreaterEqual(m.taylor_lower(c,16)*F(1,20),1)
        def rejection_probability(q,cap):
            width=1/q+1/(1-q)
            boundary=c/lam+lam*n*width*width/8
            bias=max(F(0),cap-q)*width*n
            rejected=[k for k in range(n+1)
                      if F(k,q)-F(n-k,1-q)>boundary+bias]
            risk=sum((F(comb(n,k))*actual**k*(1-actual)**(n-k)
                      for k in rejected),F(0))
            return rejected,risk
        bad,risk=rejection_probability(F(1,2),F(1,2))
        self.assertEqual(bad,list(range(43,65)))
        self.assertGreater(risk,F(999999,1000000))
        safe,risk2=rejection_probability(F(1,2),F(9,10))
        self.assertEqual(safe,[]);self.assertEqual(risk2,0)
        safe,risk3=rejection_probability(F(9,10),F(9,10))
        self.assertEqual(safe,[]);self.assertEqual(risk3,0)

    def test_every_binary_world_conditional_coverage_with_adaptive_stop(self):
        # Enumerate true response worlds, adaptive feedback r=a, and all
        # treatment paths under actual probabilities beneath two upper bounds.
        from fractions import Fraction
        original=json.loads((V24/'example_protocol.json').read_text())
        for actual_pair,caps in [((F(2,5),F(3,5)),('1/2','2/3')),
                                 ((F(1,10),F(1,4)),('1/2','1/2'))]:
            p=make_demo.convert(original,upper=(caps[0],caps[1],caps[1]),reference_only=True)
            p['registered_units']=4;p['states']=2;p['initial_state']=0
            p['min_enrollment']=2;p['max_interval_misses']=0
            p['propensity_upper_by_state']=list(caps)
            p['next_state_by_state_action_report']=[[[0,0],[1,1]],[[0,0],[1,1]]]
            p['stop_after_by_state_action_report']=[[[False,False],[False,True]] for _ in range(2)]
            p['tuning']=[{'lambda':'1/2','alpha_spend':'1/2','log_upper':'1',
                         'taylor_terms':8,'reference_weights_by_state':[[1,1],[1,1]]}]
            p['confidence_alpha']='1/2';p['calibration_failure_bound']='0'
            for world in product(range(4),repeat=4):
                ys=[(v>>1,v&1) for v in world]
                true_ate=F(sum(b-a for a,b in ys),4)
                fail=F(0)
                def walk(a_hist,r_hist,l_hist,state,mass):
                    nonlocal fail
                    i=len(a_hist)
                    for a in (0,1):
                        q=actual_pair[state] if a else 1-actual_pair[state]
                        y=ys[i][a];A=a_hist+[a];R=r_hist+[a];L=l_hist+[str(y)]
                        if i+1==4 or (i+1>=2 and a==1):
                            rep=self.audit(p,{'assignments':A,'reports':R,'true_intervals':L})
                            if F(rep['anytime_lower_ate'])>true_ate:fail+=mass*q
                        else:walk(A,R,L,a,mass*q)
                walk([],[],[],0,F(1))
                self.assertLessEqual(fail,F(1,2),(actual_pair,caps,world,fail))

    def test_canonical_reader_rejects_duplicate_json_keys(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'x.json';path.write_text('{"x":1,"x":2}')
            with self.assertRaisesRegex(m.Reject,'duplicate JSON key'):m.read(path)

if __name__=='__main__':unittest.main()

class FrontierTests(unittest.TestCase):
    def test_exact_frontier_is_supremum_of_strict_rejections(self):
        p=json.loads((ROOT/'example_protocol.json').read_text())
        e=json.loads((ROOT/'example_evidence.json').read_text())
        def replay(epsilon):
            x=copy.deepcopy(p)
            x['propensity_upper_by_state']=[str(min(F(1),F(cap)+epsilon)) for cap in p['propensity_upper_by_state']]
            pin=m.digest(x)
            return m.audit(x,e,protocol_pin=pin,evidence_pin=m.evidence_digest(pin,e))
        base=replay(F(0))
        threshold=F(base['common_upper_slack_supremum'])
        self.assertEqual(base['status'],'CONDITIONALLY_REJECTED')
        self.assertGreater(threshold,F(1,10))
        self.assertLess(threshold,F(1,5))
        self.assertEqual(replay(threshold/2)['status'],'CONDITIONALLY_REJECTED')
        self.assertEqual(replay(threshold)['status'],'INSUFFICIENT_EVIDENCE')
        self.assertEqual(replay(min(F(1),threshold+F(1,1000)))['status'],'INSUFFICIENT_EVIDENCE')
        self.assertFalse(base['strict_rejection_at_supremum'])
