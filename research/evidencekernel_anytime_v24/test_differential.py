"""Independent-implementation comparison across randomized adaptive policies."""
from __future__ import annotations
import copy
import json
from pathlib import Path
from random import Random
import subprocess
import tempfile
import unittest
from . import kernel as py
from . import make_demo

HERE=Path(__file__).parent

class ExactDifferential(unittest.TestCase):
    def test_110_adaptive_stopped_trials_python_vs_bigint_js(self):
        rng=Random(20261109)
        for trial in range(110):
            p=json.loads((HERE/'example_protocol.json').read_text())
            n=rng.randrange(5,105)
            S=rng.randrange(1,5)
            p['registered_units']=n;p['states']=S;p['initial_state']=rng.randrange(S)
            p['min_enrollment']=rng.randrange(2,n+1)
            p['allocation_weights_by_state']=[[rng.randrange(1,12),rng.randrange(1,12)] for _ in range(S)]
            p['next_state_by_state_action_report']=[[[rng.randrange(S) for _ in range(2)] for _ in range(2)] for _ in range(S)]
            p['stop_after_by_state_action_report']=[[[bool(rng.randrange(5)==0) for _ in range(2)] for _ in range(2)] for _ in range(S)]
            p['max_interval_misses']=rng.randrange(0,4)
            a=[];r=[];labs=[];state=p['initial_state']
            for i in range(n):
                w=p['allocation_weights_by_state'][state]
                action=int(rng.randrange(sum(w))>=w[0])
                report=rng.randrange(2)
                outcome=rng.randrange(2)
                # If a binary label is wrong, one of the allowed misses
                # absorbs the discrepancy. The verifier cannot know the truth.
                label='01' if rng.randrange(9)==0 else str(outcome)
                a.append(action);r.append(report);labs.append(label)
                stop=i+1==n or (i+1>=p['min_enrollment'] and
                    p['stop_after_by_state_action_report'][state][action][report])
                state=p['next_state_by_state_action_report'][state][action][report]
                if stop:break
            e={'assignments':a,'reports':r,'true_intervals':labs}
            pp=py.digest(p);ep=py.evidence_digest(pp,e)
            expected=py.audit(p,e,protocol_pin=pp,evidence_pin=ep)
            with tempfile.TemporaryDirectory(prefix='ekv24-') as tmp:
                ppfile=Path(tmp)/'protocol.json';epfile=Path(tmp)/'evidence.json'
                ppfile.write_text(json.dumps(p,sort_keys=True))
                epfile.write_text(json.dumps(e,sort_keys=True))
                result=subprocess.run(['node',str(HERE/'independent.js'),str(ppfile),str(epfile),pp,ep],
                                      text=True,capture_output=True,timeout=15)
                self.assertEqual(result.returncode,0,f'trial {trial}: {result.stderr}')
                self.assertEqual(json.loads(result.stdout),expected,f'differential mismatch #{trial}')

    def test_big_report_cross_language(self):
        for name in ('example','scale'):
            with tempfile.TemporaryDirectory(prefix='ekv24-large-') as tmp:
                location=HERE if name=='example' else Path(tmp)
                if name=='scale':
                    make_demo.save(location,n=4096,min_enrollment=4096,
                                   stop_enabled=False,label='scale')
                pin=(location/f'{name}_protocol_pin.txt').read_text().strip()
                epin=(location/f'{name}_evidence_pin.txt').read_text().strip()
                pfile=location/f'{name}_protocol.json';efile=location/f'{name}_evidence.json'
                expected=json.loads((location/f'{name}_report.json').read_text())
                result=subprocess.run(['node',str(HERE/'independent.js'),str(pfile),str(efile),pin,epin],
                                      text=True,capture_output=True,timeout=20)
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertEqual(json.loads(result.stdout),expected)

    def test_strict_independent_js_duplicate_key_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            file=Path(tmp)/'duplicate.json'
            file.write_text('{"registered_units":5,"registered_units":100000}')
            r=subprocess.run(['node',str(HERE/'strict_json.js'),str(file)],
                             capture_output=True,text=True,timeout=5)
            self.assertNotEqual(r.returncode,0)
            self.assertIn('duplicate',r.stderr)

if __name__=='__main__':unittest.main()
