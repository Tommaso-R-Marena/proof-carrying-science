"""Python ↔ independently authored Node.js exact-inference comparison."""
import json
import random
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from kernel import FORMAT, digest, design_distribution, robust_test

HERE=Path(__file__).parent

class DifferentialTests(unittest.TestCase):
    def test_cross_language_60_deterministic_cases(self):
        rng=random.Random(20261109)
        for case in range(60):
            n=rng.randint(3,6)
            k=rng.randint(1,n-1)
            law=rng.choice(['iid_with_replacement','ordered_without_replacement'])
            b=2
            x=[rng.randint(-2,2) for _ in range(n)]
            p={'format':FORMAT,'n':n,'k':k,'candidate_draws':b,
               'candidate_law':law,'baseline_covariate':x,
               'selection_rule':'minimum_absolute_baseline_imbalance_first_tie',
               'null_ate_upper':rng.choice(['-1/3','0','1/3']),
               'max_interval_misses':rng.randint(0,1)}
            A,s,m,_=design_distribution(p)
            ii=rng.sample(range(len(A)),b) if law=='ordered_without_replacement' else [rng.randrange(len(A)) for _ in range(b)]
            winner=min(ii,key=lambda j:s[j])
            zz=list(A[winner]);labels=[rng.choice(['0','1','01']) for _ in range(n)]
            e={'attempts':[list(A[j]) for j in ii], 'selected_assignment':zz,'observed_intervals':labels}
            expected=robust_test(p,e,external_pin=digest(p))
            with tempfile.TemporaryDirectory() as d:
                d=Path(d)
                (d/'protocol.json').write_text(json.dumps(p))
                (d/'evidence.json').write_text(json.dumps(e))
                cmd=['node',str(HERE/'independent.js'),str(d/'protocol.json'),str(d/'evidence.json'),digest(p)]
                res=subprocess.run(cmd,capture_output=True,text=True,timeout=20)
                self.assertEqual(res.returncode,0,f'case {case}: {res.stderr}')
                actual=json.loads(res.stdout)
                self.assertEqual(actual,expected,f'case {case}')

    def test_independent_rejects_noncanonical_json(self):
        p={'format':FORMAT,'n':3,'k':1,'baseline_covariate':[0,1,2],
           'candidate_draws':2,'candidate_law':'iid_with_replacement',
           'selection_rule':'minimum_absolute_baseline_imbalance_first_tie',
           'null_ate_upper':'0','max_interval_misses':0}
        e={'attempts':[[0],[0]],'selected_assignment':[0],'observed_intervals':['1','0','0']}
        with tempfile.TemporaryDirectory() as td:
            td=Path(td)
            (td/'p.json').write_text(json.dumps(p))
            (td/'e.json').write_text('{"attempts":[[0],[0]],"attempts":[[0],[0]],"selected_assignment":[0],"observed_intervals":["1","0","0"]}')
            cmd=['node',str(HERE/'independent.js'),str(td/'p.json'),str(td/'e.json'),digest(p)]
            r=subprocess.run(cmd,capture_output=True,text=True,timeout=20)
            self.assertNotEqual(r.returncode,0)
            self.assertIn('duplicate JSON key',r.stderr)

if __name__=='__main__':unittest.main()
