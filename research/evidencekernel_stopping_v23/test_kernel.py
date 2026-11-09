"""Exhaustive finite-model, chronology, and adversarial stopped-path controls."""
from __future__ import annotations
import copy
from fractions import Fraction
from itertools import product
from pathlib import Path
import tempfile
import unittest
from . import kernel as k

HERE=Path(__file__).parent
P=k.read(HERE/'example_protocol.json')
E=k.read(HERE/'example_evidence.json')
PIN=(HERE/'example_protocol_pin.txt').read_text().strip()
EPIN=(HERE/'example_evidence_pin.txt').read_text().strip()


def randomized_small_protocol(n=3):
    p=copy.deepcopy(P)
    p['registered_units']=n
    p['states']=2
    p['allocation_weights_by_state']=[[2,1],[1,2]]
    p['stop_after_by_state_action_report']=[
        [[False, True],[False,True]], [[False,True],[False, True]]]
    p['min_enrollment']=2
    return p


class StoppingDesignTests(unittest.TestCase):
    def test_demo_exact_and_composition(self):
        out=k.audit(P,E,protocol_pin=PIN,evidence_pin=EPIN)
        self.assertEqual(out['conditional_p'],'15/32')
        self.assertEqual(out['registered_units'],4)
        self.assertEqual(out['enrolled_units'],3)
        self.assertEqual(out['compatible_joint_worlds'],1024)
        self.assertEqual(out['compatible_report_schedules'],32)
        self.assertEqual(out['actual_stopped_history_probability_given_observed_reports'],'3/64')
        self.assertEqual(out['conditional_lower_ate'],'0')

    def test_report_and_outcome_completion_includes_unenrolled_units(self):
        a=(0,1,1);r=(0,0,1)
        self.assertEqual(len(list(k.report_models(a,r,4))),32)
        self.assertEqual(len(list(k.true_models(a,('0','1','1'),4,0))),32)
        self.assertEqual(len(list(k.true_models(a,('01','01','01'),4,0))),256)

    def test_world_probability_normalization_many_complete_schedules(self):
        for n in (3,4):
            d=k.design(randomized_small_protocol(n))
            for digit in product(range(4),repeat=n):
                R=tuple((x//2,x%2) for x in digit)
                distribution=k.law(d,R)
                self.assertEqual(sum(distribution.values()),1)
                for path in distribution:
                    self.assertGreaterEqual(len(path),2)
                    self.assertLessEqual(len(path),n)

    def test_all_sharp_null_worlds_superuniform_under_stopping(self):
        # Pure design-based theorem regression: enumerate the WHOLE stopped-path
        # sample space, not a conditional distribution at the observed stop time.
        d=k.design(randomized_small_protocol(4))
        for y in product((0,1),repeat=4):
            Y=tuple((v,v) for v in y)
            for Rcode in product(range(4),repeat=4):
                R=tuple((v//2,v%2) for v in Rcode)
                law=k.law(d,R)
                pv={p:sum((v for path,v in law.items() if k.statistic(Y,path)>=k.statistic(Y,p)),Fraction(0))
                    for p in law}
                for alpha in (Fraction(1,20),Fraction(1,10),Fraction(1,4),Fraction(1,2)):
                    error=sum((mass for path,mass in law.items() if pv[path]<=alpha),Fraction(0))
                    self.assertLessEqual(error,alpha,(Y,R,alpha,error))

    def test_robust_calculation_dominates_true_world_p(self):
        d=k.design(randomized_small_protocol(3))
        for ybits in product((0,1),repeat=3):
            Y=tuple((v,v) for v in ybits)
            for rcode in (0,9,21,42,63):
                R=tuple(((rcode>>(2*i+1))&1,(rcode>>(2*i))&1) for i in range(3))
                dist=k.law(d,R)
                for path in dist:
                    reps=tuple(R[i][a] for i,a in enumerate(path))
                    labels=tuple(str(Y[i][a]) for i,a in enumerate(path))
                    curve,target,lower,count,rmodels=k.inference(d,path,reps,labels)
                    true_tail=sum((mass for z,mass in dist.items()
                                   if k.statistic(Y,z)>=k.statistic(Y,path)),Fraction(0))
                    # True ATE=0; composite weak null always includes true model.
                    idx=d['n']
                    self.assertGreaterEqual(Fraction(curve[idx]['max_p']),true_tail)

    def test_pinned_hash_tamper_and_missing_custody(self):
        for key,modified in (
            ('reports',[0,1,1]),('assignments',[1,1,1]),
            ('true_intervals',['0','0','1'])):
            bad=copy.deepcopy(E);bad[key]=modified
            with self.assertRaises(k.Reject):
                k.audit(P,bad,protocol_pin=PIN,evidence_pin=EPIN)
        with self.assertRaises(k.Reject):
            k.audit(P,E,protocol_pin='0'*64,evidence_pin=EPIN)
        with self.assertRaises(k.Reject):
            k.audit(P,E,protocol_pin=PIN,evidence_pin='0'*64)

    def test_invalid_early_or_late_stop_fails_closed(self):
        cases=[{'assignments':[0,1], 'reports':[0,0], 'true_intervals':['0','1']},
               {'assignments':[1,1,0], 'reports':[0,1,0], 'true_intervals':['1','0','1']},
               {'assignments':[1,1,0,0], 'reports':[0,1,0,0], 'true_intervals':['1','0','0','0']}]
        for e in cases:
            epin=k.commitment(PIN,e)
            with self.assertRaises(k.Reject):
                k.audit(P,e,protocol_pin=PIN,evidence_pin=epin)

    def test_zero_weight_assignment_is_rejected(self):
        p=copy.deepcopy(P);p['allocation_weights_by_state'][0]=[1,0]
        e=copy.deepcopy(E)
        with self.assertRaises(k.Reject):
            k.audit(p,e,protocol_pin=k.digest(p),evidence_pin=k.commitment(k.digest(p),e))

    def test_duplicate_json_keys_and_float_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'invalid.json'
            for body in ('{"n":1,"n":2}', '{"confidence_alpha":0.05}'):
                p.write_text(body)
                with self.assertRaises(k.Reject):k.read(p)

    def test_malformed_stopping_policy_rejected(self):
        for change in (
          ('stop_after_by_state_action_report',[[[0,1],[0,1]],[[0,1],[0,1]]]),
          ('min_enrollment',True),('registered_units',9),
          ('states',False),('confidence_alpha','0.05'),
          ('max_interval_misses',7)):
            bad=copy.deepcopy(P);bad[change[0]]=change[1]
            with self.assertRaises(k.Reject):k.design(bad)

    def test_optional_peeking_sharp_null_counterexample(self):
        # This is a DIFFERENT preregistered stopping policy (peek each t),
        # included as a warning against ignoring stopping. It is not claimed
        # as a bug in an admissible v22 fixed-n registration.
        y=(0,0,0,0,1,0,1);n=len(y)
        def stat(mask,t):
            path=tuple((mask>>i)&1 for i in range(t))
            Y=tuple((v,v) for v in y)
            return k.statistic(Y,path)
        p={}
        for t in range(2,n+1):
            st=[stat(m,t) for m in range(1<<t)]
            p[t]=[Fraction(sum(v>=st[m] for v in st),1<<t) for m in range(1<<t)]
        crossed=0
        for m in range(1<<n):
            for t in range(2,n+1):
                if p[t][m&((1<<t)-1)]<=Fraction(1,20):
                    crossed+=1;break
        self.assertEqual(crossed,8)
        self.assertEqual(Fraction(crossed,1<<n),Fraction(1,16))

if __name__=='__main__':unittest.main()
