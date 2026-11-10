"""Cross-language exact rational differential checks, with independent Node.js replay."""
import json
import random
import subprocess
import tempfile
import unittest
from pathlib import Path
from fractions import Fraction
from research.evidencekernel_weighted_v20.kernel import audit, design, digest, attempt_commitment
from research.evidencekernel_weighted_v20.test_kernel import make, stopped, evidence

HERE=Path(__file__).parent

class IndependentVerifierTests(unittest.TestCase):
    def test_demo_two_implementations_identical(self):
        p=json.loads((HERE/'example_protocol.json').read_text())
        e=json.loads((HERE/'example_evidence.json').read_text())
        pin=(HERE/'example_pin.txt').read_text().strip()
        ap=(HERE/'example_attempts_pin.txt').read_text().strip()
        py=audit(p,e,protocol_pin=pin,attempts_pin=ap)
        result=subprocess.run(['node',str(HERE/'independent.js'),str(HERE/'example_protocol.json'),
                               str(HERE/'example_evidence.json'),pin,ap],capture_output=True,text=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(py,json.loads(result.stdout))

    def test_seeded_exact_statistical_and_crypto_cross_checks(self):
        rng=random.Random(20261109)
        with tempfile.TemporaryDirectory() as tmp:
            prot=Path(tmp)/'p.json';ev=Path(tmp)/'e.json'
            for trial in range(24):
                n=3+trial%3;k=1 if n==3 else 2;H=2+trial%3
                from math import comb
                N=comb(n,k)
                weights=[[rng.randint(0,6) for _ in range(N)] for _ in range(H)]
                for row in weights:
                    if not any(row):row[0]=1
                p=make(n,k,H,cutoff=rng.randrange(0,100), weights=weights,K=trial%2)
                d=design(p)
                histories=list(stopped(d))
                seq,_=histories[rng.randrange(len(histories))]
                world=tuple((rng.randrange(2),rng.randrange(2)) for _ in range(n))
                e=evidence(d,seq,world)
                if trial%3==0:e['observed_intervals'][rng.randrange(n)]='01'
                pin=digest(p);ap=attempt_commitment(pin,e['attempts'])
                py=audit(p,e,protocol_pin=pin,attempts_pin=ap)
                prot.write_text(json.dumps(p));ev.write_text(json.dumps(e))
                result=subprocess.run(['node',str(HERE/'independent.js'),str(prot),str(ev),pin,ap],
                                      capture_output=True,text=True,timeout=15)
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertEqual(py,json.loads(result.stdout))

if __name__=='__main__':unittest.main()
