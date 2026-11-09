"""Black-box, independent-language exact rational correspondence."""
import copy
import json
import random
import subprocess
import unittest
from pathlib import Path
from itertools import combinations

from research.evidencekernel_transcript_v18.kernel import audit, digest, v17_adapter, attempt_commitment
from research.evidencekernel_selective_v17.kernel import design
from research.evidencekernel_transcript_v18.test_kernel import protocol

HERE=Path(__file__).parent

class IndependentVerifierTests(unittest.TestCase):
    def invoke(self,p,e):
        r=subprocess.run(['node',str(HERE/'independent.js'),str(HERE/'dynamic_protocol.json'),
                          str(HERE/'dynamic_evidence.json'),digest(p)],capture_output=True,text=True,timeout=8)
        if r.returncode!=0:raise AssertionError(r.stderr)
        return json.loads(r.stdout)

    def test_80_generated_reports_identical(self):
        # Avoid writing test files on the repository checkout: use tempfile.
        import tempfile
        rng=random.Random(222707)
        for t in range(80):
            n=rng.choice([3,4,5,6])
            k=rng.randint(1,n-1)
            N=len(list(combinations(range(n),k)))
            law=rng.choice(['iid_with_replacement','ordered_without_replacement'])
            b=rng.randint(1,min(3,N))
            p=protocol(n,k,b,law,[rng.randint(-2,2) for _ in range(n)],K=rng.choice([0,1]))
            p['null_ate_upper']=rng.choice(['-1/2','0','1/2','1'])
            space,scores,_,_=design(v17_adapter(p))
            inds=(rng.sample(range(N),b) if law=='ordered_without_replacement'
                  else [rng.randrange(N) for _ in range(b)])
            selected=min(inds,key=lambda i:scores[i])
            e={'attempts':[list(space[i]) for i in inds],
               'selected_assignment':list(space[selected]),
               'observed_intervals':[rng.choice(['0','1','01']) for _ in range(n)]}
            py=audit(p,e,external_pin=digest(p),external_attempts_pin=attempt_commitment(digest(p),e['attempts']))
            with tempfile.TemporaryDirectory() as temp:
                pp=Path(temp)/'p.json';ep=Path(temp)/'e.json'
                pp.write_text(json.dumps(p));ep.write_text(json.dumps(e))
                r=subprocess.run(['node',str(HERE/'independent.js'),str(pp),str(ep),digest(p),attempt_commitment(digest(p),e['attempts'])],
                                 capture_output=True,text=True,timeout=8)
                self.assertEqual(r.returncode,0,r.stderr)
                self.assertEqual(py,json.loads(r.stdout))

    def test_independent_verifier_rejects_forgery_with_pinned_original_attempts(self):
        import tempfile
        p=json.loads((HERE/'example_protocol.json').read_text())
        e=json.loads((HERE/'example_evidence.json').read_text())
        pin=digest(p); attempt_pin=attempt_commitment(pin,e['attempts'])
        tampered=copy.deepcopy(e)
        tampered['attempts']=[[0,1,3],[0,1,2]]
        # Last selection remains the same (the first attempt has worse balance),
        # but the advertised candidate transcript is no longer committed.
        with tempfile.TemporaryDirectory() as temp:
            pp=Path(temp)/'p.json';ep=Path(temp)/'e.json'
            pp.write_text(json.dumps(p));ep.write_text(json.dumps(tampered))
            r=subprocess.run(['node',str(HERE/'independent.js'),str(pp),str(ep),pin,attempt_pin],
                             capture_output=True,text=True,timeout=8)
            self.assertNotEqual(r.returncode,0)
            self.assertIn('externally pinned commitment',r.stderr)

    def test_tampered_protocol_and_attempts_independently_rejected(self):
        import tempfile
        p=json.loads((HERE/'example_protocol.json').read_text())
        e=json.loads((HERE/'example_evidence.json').read_text())
        pin=digest(p)
        cases=[({**p,'tie_rule':'late_favorable_choice'},e,pin),
               (p,{**e,'attempts':e['attempts'][:1]},pin),
               (p,{**e,'selected_assignment':[1,2,3]},pin)]
        for pr,ev,external_pin in cases:
            with tempfile.TemporaryDirectory() as temp:
                pp=Path(temp)/'p.json';ep=Path(temp)/'e.json'
                pp.write_text(json.dumps(pr));ep.write_text(json.dumps(ev))
                r=subprocess.run(['node',str(HERE/'independent.js'),str(pp),str(ep),external_pin,attempt_commitment(external_pin,e['attempts'])],
                                 capture_output=True,text=True,timeout=8)
                self.assertNotEqual(r.returncode,0)

if __name__=='__main__':unittest.main()
