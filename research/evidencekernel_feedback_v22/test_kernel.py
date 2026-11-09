"""Exact all-world validation and adversarial tests for outcome-feedback designs."""
import copy
import itertools
import json
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path
from research.evidencekernel_feedback_v22.kernel import (
    Reject,audit,design,digest,evidence_commitment,load_strict,world_law,score)

ROOT=Path(__file__).parent

def example():
    return load_strict(ROOT/'example_protocol.json'),load_strict(ROOT/'example_evidence.json')

def run(p,e):
    pin=digest(p)
    return audit(p,e,protocol_pin=pin,evidence_pin=evidence_commitment(pin,e))

def worlds(n):
    for v in itertools.product(range(4),repeat=n):
        yield tuple((x//2,x%2) for x in v)

class FeedbackTests(unittest.TestCase):
    def test_independent_exact_assignment_mass(self):
        p,e=example();d=design(p)
        for r in worlds(d['n']):
            mu=world_law(d,r)
            self.assertEqual(sum(mu.values()),1)
            for z,m in mu.items():
                s=d['init'];q=Fraction(1)
                for i,a in enumerate(z):
                    q*=d['w'][s][a]
                    s=d['trans'][s][a][r[i][a]]
                self.assertEqual(m,q)

    def test_true_fixed_world_tail_p_superuniform(self):
        p,e=example();p['n']=3;d=design(p)
        for r in worlds(3):
            mu=world_law(d,r)
            for y in worlds(3):
                scores={z:score(y,z) for z in mu}
                pp={z:sum((v for alt,v in mu.items() if scores[alt]>=scores[z]),Fraction(0)) for z in mu}
                for level in set(pp.values()):
                    self.assertLessEqual(sum((mu[z] for z in mu if pp[z]<=level),Fraction(0)),level)

    def test_robust_composite_null_full_model_census(self):
        p,e=example();p['n']=2;p['confidence_alpha']='1/5';d=design(p)
        for r in worlds(2):
            mu=world_law(d,r)
            for y in worlds(2):
                ate=sum(q[1]-q[0] for q in y)
                if ate>0:continue
                error=Fraction(0)
                for z,pr in mu.items():
                    observed={'assignments':list(z),'reports':[r[i][z[i]] for i in range(2)],
                              'true_intervals':[str(y[i][z[i]]) for i in range(2)]}
                    result=run(p,observed)
                    if result['conditional_p'] is not None and Fraction(result['conditional_p'])<=Fraction(1,5):
                        error+=pr
                self.assertLessEqual(error,Fraction(1,5),(r,y,error))

    def test_naive_report_truth_substitution_is_anti_conservative(self):
        p,e=example();p['allocation_weights_by_state']=[[19,1],[1,19]]
        d=design(p)
        y=((1,1),(0,0),(1,1),(0,0))
        r=((0,0),(1,1),(0,0),(0,0))
        true_mu=world_law(d,r)
        mistaken_mu=world_law(d,y)  # WRONG: inferred allocation law using Y instead of R.
        mistaken={z:sum((v for alt,v in mistaken_mu.items() if score(y,alt)>=score(y,z)),Fraction(0)) for z in true_mu}
        bad=sum((v for z,v in true_mu.items() if mistaken[z]<=Fraction(1,20)),Fraction(0))
        self.assertEqual(bad,Fraction(158897,160000))
        fixed_error=Fraction(0)
        for z,pr in true_mu.items():
            ev={'assignments':list(z),'reports':[r[i][z[i]] for i in range(4)],
                'true_intervals':[str(y[i][z[i]]) for i in range(4)]}
            result=run(p,ev)
            if result['conditional_p'] is not None and Fraction(result['conditional_p'])<=Fraction(1,20):
                fixed_error+=pr
        self.assertEqual(fixed_error,Fraction(6859,160000))
        self.assertLessEqual(fixed_error,Fraction(1,20))

    def test_missing_report_and_unpinned_modification_rejected(self):
        p,e=example();pin=digest(p);epin=evidence_commitment(pin,e)
        self.assertEqual(run(p,e)['format'],'pcs-evidencekernel-response-adaptive-audit-v22')
        for field,value in [('reports',[0,0,0,0]),('assignments',[1,1,1,1]),('true_intervals',['1']*4)]:
            modified=copy.deepcopy(e);modified[field]=value
            with self.assertRaisesRegex(Reject,'evidence pin mismatch'):
                audit(p,modified,protocol_pin=pin,evidence_pin=epin)
        with self.assertRaisesRegex(Reject,'protocol pin mismatch'):
            audit(p,e,protocol_pin='0'*64,evidence_pin=epin)
        with self.assertRaisesRegex(Reject,'externally supplied hash pin'):
            audit(p,e,protocol_pin='wrong',evidence_pin=epin)

    def test_invalid_policy_data_and_zero_probability_assignment_fail_closed(self):
        p,e=example()
        for change in [lambda x:x.update({'observation_model':'assume_report_is_truth'}),
                       lambda x:x.update({'n':True}),
                       lambda x:x.update({'max_interval_misses':-1}),
                       lambda x:x.update({'extra':'something'}),
                       lambda x:x.update({'states':7}),
                       lambda x:x.update({'allocation_weights_by_state':[[0,0],[1,4]]}),
                       lambda x:x.update({'next_state_by_state_action_report':[[[2,1],[0,1]],[[0,1],[0,1]]]}),
                       lambda x:x.update({'confidence_alpha':'0.05'}),
                       lambda x:x.update({'null_ate_upper':'2'})]:
            q=copy.deepcopy(p);change(q)
            with self.assertRaises(Reject):design(q)
        q=copy.deepcopy(p);q['allocation_weights_by_state']=[[10,0],[10,0]]
        with self.assertRaisesRegex(Reject,'impossible treatment'):
            run(q,e)

    def test_cannot_confuse_reported_values_with_truth_intervals(self):
        p,e=example();q=copy.deepcopy(e)
        q['true_intervals']=['01']*4
        loose=run(p,q)
        tight=run(p,e)
        self.assertGreaterEqual(loose['compatible_joint_worlds'],tight['compatible_joint_worlds'])
        for a,b in zip(loose['null_curve'],tight['null_curve']):
            if a['null_feasible'] and b['null_feasible']:
                self.assertGreaterEqual(Fraction(a['max_p']),Fraction(b['max_p']))

    def test_protocol_domains_and_strict_json_parser(self):
        p,e=example()
        self.assertEqual(digest(p), (ROOT/'example_protocol_pin.txt').read_text().strip())
        with tempfile.TemporaryDirectory() as td:
            bad=Path(td)/'x.json'
            for raw in ['{"x":1,"x":2}', '{"bad": 1e9}', '{"foo": NaN}', '{"a": 1.0}']:
                bad.write_text(raw)
                with self.assertRaises((Reject,ValueError)):load_strict(bad)

if __name__=='__main__':unittest.main()
