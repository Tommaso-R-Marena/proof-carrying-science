"""Independent JS BigInt replay across hand-seeded state machines and data."""
from pathlib import Path
from fractions import Fraction
import copy, json, random, shutil, subprocess, tempfile, unittest
from research.evidencekernel_feedback_v22.kernel import audit,digest,evidence_commitment,Reject
from research.evidencekernel_feedback_v22.test_kernel import example

ROOT=Path(__file__).parent
class IndependentTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'),'requires Node.js')
    def test_synthetic_signed_pin_replay_matches_independent_js(self):
        p,e=example();pin=digest(p);epin=evidence_commitment(pin,e)
        cmd=['node',str(ROOT/'independent.js'),str(ROOT/'example_protocol.json'),
             str(ROOT/'example_evidence.json'),pin,epin]
        got=json.loads(subprocess.check_output(cmd,text=True))
        expected=audit(p,e,protocol_pin=pin,evidence_pin=epin)
        self.assertEqual(got,expected)

    @unittest.skipUnless(shutil.which('node'),'requires Node.js')
    def test_independent_differential_randomized_protocols(self):
        r=random.Random(20261109)
        with tempfile.TemporaryDirectory() as td:
            proto=Path(td)/'p.json';evidence=Path(td)/'e.json'
            for i in range(35):
                p,e=example()
                n=r.choice([2,3,4])
                p['n']=n
                p['allocation_weights_by_state']=[[r.randrange(1,15),r.randrange(1,15)] for _ in range(2)]
                p['next_state_by_state_action_report']=[[[r.randrange(2),r.randrange(2)] for a in range(2)] for s in range(2)]
                p['initial_state']=r.randrange(2)
                p['max_interval_misses']=r.randrange(0, min(n,2)+1)
                p['null_ate_upper']=r.choice(['-1/2','0','1/2'])
                p['confidence_alpha']=r.choice(['1/20','1/10','1/2'])
                e={'assignments':[r.randrange(2) for _ in range(n)],
                   'reports':[r.randrange(2) for _ in range(n)],
                   'true_intervals':[r.choice(['0','1','01']) for _ in range(n)]}
                pin=digest(p);epin=evidence_commitment(pin,e)
                proto.write_text(json.dumps(p));evidence.write_text(json.dumps(e))
                out=subprocess.check_output(['node',str(ROOT/'independent.js'),str(proto),str(evidence),pin,epin],text=True)
                got=json.loads(out)
                expected=audit(p,e,protocol_pin=pin,evidence_pin=epin)
                self.assertEqual(got,expected, f'cross-language discrepancy at case {i}')

    @unittest.skipUnless(shutil.which('node'),'requires Node.js')
    def test_node_rejects_noncanonical_or_tampered_custody(self):
        p,e=example();pin=digest(p);epin=evidence_commitment(pin,e)
        with tempfile.TemporaryDirectory() as td:
            proto=Path(td)/'p.json'; ev=Path(td)/'e.json'
            proto.write_text(json.dumps(p));ev.write_text(json.dumps(e))
            def run():return subprocess.run(['node',str(ROOT/'independent.js'),str(proto),str(ev),pin,epin],capture_output=True,text=True)
            self.assertEqual(run().returncode,0)
            ev.write_text('{"assignments": [0,1,1,0],"reports": [0,1,1,0],"reports": [0,1,1,0],"true_intervals": ["0","1","01","0"]}')
            self.assertEqual(run().returncode,2)
            ev.write_text(json.dumps(e));proto.write_text(json.dumps({**p,'states':3}))
            self.assertEqual(run().returncode,2)

if __name__=='__main__':unittest.main()
