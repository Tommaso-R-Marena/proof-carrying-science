"""Independent Python/Node.js exact byte-and-commitment replay."""
from copy import deepcopy
from pathlib import Path
from random import Random
import json, subprocess, tempfile, unittest
from . import kernel as k
from .make_demo import example
from research.evidencekernel_propensity_v25 import kernel as v25

HERE=Path(__file__).parent
class IndependentWitness(unittest.TestCase):
    def test_full_256_draw_example(self):
        self.compare_case(*example(256)[:3])

    def compare_case(self,c,p,e):
        cp=v25.digest(c);sp=v25.digest(p)
        ep=v25.digest({'domain':'pcs-ek-v28-witness-records','contract_pin':cp,
                       'study_pin':sp,'evidence':e})
        python=k.audit(c,p,e,contract_pin=cp,study_pin=sp,evidence_pin=ep)
        with tempfile.TemporaryDirectory() as tmp:
            paths=[]
            for i,content in enumerate((c,p,e)):
                file=Path(tmp)/f'{i}.json'
                file.write_text(json.dumps(content,sort_keys=True))
                paths.append(str(file))
            result=subprocess.run(['node',str(HERE/'independent.js'),*paths,cp,sp,ep],
                                  text=True,capture_output=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stderr)
            js=json.loads(result.stdout)
            self.assertEqual(python,js)

    def test_independent_differential_40_perturbed_outcome_intervals(self):
        c,p,e,*_=example(32)
        rng=Random(20261109)
        for case in range(40):
            ep=deepcopy(e)
            for _ in range(case%13):
                j=rng.randrange(len(ep['true_intervals']))
                ep['true_intervals'][j]=rng.choice(['0','1','01'])
            with self.subTest(case=case):self.compare_case(c,p,ep)

if __name__=='__main__':unittest.main()
