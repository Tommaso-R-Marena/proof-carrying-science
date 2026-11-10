"""Independent exact-rational differential replay against Node.js, including sensitivity frontier."""
from __future__ import annotations
import copy
from fractions import Fraction as F
import json
from pathlib import Path
import random
import shutil
import subprocess
import tempfile
import unittest
from . import kernel as m
from . import make_demo

ROOT=Path(__file__).parent

@unittest.skipUnless(shutil.which('node'),'Node.js is required for cross-language tests')
class IndependentReplay(unittest.TestCase):
    def test_80_randomized_binary_feedback_and_robustness_frontiers(self):
        source=json.loads((ROOT/'example_protocol.json').read_text())
        rng=random.Random(19972026)
        caps=['1/5','2/5','1/2','3/5','4/5','9/10','1']
        references=[[1,1],[1,2],[2,1],[1,3],[3,1],[4,5],[5,4]]
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for case in range(80):
                p=copy.deepcopy(source)
                n=rng.randrange(3,30)
                p['registered_units']=n
                p['min_enrollment']=n # all-prefix paths, adaptive reports preserved
                p['max_interval_misses']=rng.randrange(0,3)
                p['propensity_upper_by_state']=[rng.choice(caps) for _ in range(3)]
                # Two simultaneous candidate lower bounds with Bonferroni alpha spending.
                p['tuning']=[{'reference_weights_by_state':[rng.choice(references) for _ in range(3)],
                              'lambda':rng.choice(('1/16','1/8','1/4')),
                              'alpha_spend':'1/40','log_upper':'4','taylor_terms':20}
                             for _ in range(2)]
                p['stop_after_by_state_action_report']=[[[False,False],[False,False]] for _ in range(3)]
                A=[rng.randrange(2) for _ in range(n)]
                R=[rng.randrange(2) for _ in range(n)]
                L=[rng.choice(('0','1','01')) for _ in range(n)]
                e={'assignments':A,'reports':R,'true_intervals':L}
                pp=m.digest(p);ep=m.evidence_digest(pp,e)
                result=m.audit(p,e,protocol_pin=pp,evidence_pin=ep)
                a=root/'p.json';b=root/'e.json'
                a.write_text(json.dumps(p));b.write_text(json.dumps(e))
                check=subprocess.run(['node',str(ROOT/'independent.js'),str(a),str(b),pp,ep],
                                     capture_output=True,text=True,timeout=15)
                self.assertEqual(check.returncode,0,check.stderr)
                other=json.loads(check.stdout)
                self.assertEqual(result,other,'case='+str(case))
                frontier=F(result['common_upper_slack_supremum'])
                self.assertLessEqual(F(0),frontier)
                self.assertLessEqual(frontier,F(1))

    def test_tamper_rejected_by_both_implementations(self):
        p=json.loads((ROOT/'example_protocol.json').read_text())
        e=json.loads((ROOT/'example_evidence.json').read_text())
        pp=m.digest(p);ep=m.evidence_digest(pp,e)
        with tempfile.TemporaryDirectory() as tmp:
            a=Path(tmp)/'p.json';b=Path(tmp)/'e.json'
            a.write_text(json.dumps(p));b.write_text(json.dumps(e))
            def invoke(x,y):
                return subprocess.run(['node',str(ROOT/'independent.js'),str(a),str(b),x,y],
                                      capture_output=True,text=True,timeout=15)
            self.assertEqual(invoke(pp,ep).returncode,0)
            self.assertNotEqual(invoke('0'*64,ep).returncode,0)
            self.assertNotEqual(invoke(pp,'0'*64).returncode,0)
            p['propensity_upper_by_state'][0]='101/100'
            a.write_text(json.dumps(p))
            self.assertNotEqual(invoke(m.digest(p),m.evidence_digest(m.digest(p),e)).returncode,0)

if __name__=='__main__':unittest.main()
