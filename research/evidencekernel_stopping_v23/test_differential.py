"""Independent Node.js BigInt differential exact replay against Python."""
import copy
import json
import random
import subprocess
import tempfile
from pathlib import Path
import unittest
from . import kernel as k

HERE=Path(__file__).parent

class CrossLanguageTests(unittest.TestCase):
    def audit_node(self,p,e,pin,epin,folder):
        (folder/'p.json').write_text(json.dumps(p,sort_keys=True))
        (folder/'e.json').write_text(json.dumps(e,sort_keys=True))
        proc=subprocess.run(['node',str(HERE/'independent.js'),str(folder/'p.json'),
                str(folder/'e.json'),pin,epin],capture_output=True,text=True,timeout=30)
        if proc.returncode:
            self.fail('Node independently rejected a Python-valid experiment: '+proc.stderr)
        return json.loads(proc.stdout)

    def test_demo_exact_cross_language(self):
        p=k.read(HERE/'example_protocol.json');e=k.read(HERE/'example_evidence.json')
        pin=k.digest(p);epin=k.commitment(pin,e)
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(k.audit(p,e,protocol_pin=pin,evidence_pin=epin),
                             self.audit_node(p,e,pin,epin,Path(tmp)))

    def test_25_seeded_stopping_policies(self):
        rng=random.Random(20261109)
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            for iteration in range(25):
                n=3 if iteration%2 else 4
                S=2
                p={'format':k.FORMAT,'registered_units':n,'states':S,
                   'initial_state':rng.randrange(S),'min_enrollment':2,
                   'allocation_weights_by_state':[[rng.randint(1,5),rng.randint(1,5)] for _ in range(S)],
                   'next_state_by_state_action_report':[[[rng.randrange(S) for r in range(2)]
                                              for a in range(2)] for s in range(S)],
                   'stop_after_by_state_action_report':[[[rng.choice([False,True]) for r in range(2)]
                                              for a in range(2)] for s in range(S)],
                   'potential_schedule_model':k.MODEL,'statistic':k.STAT,
                   'inference_rule':k.RULE,'max_interval_misses':0,
                   'null_ate_upper':'0','confidence_alpha':'1/20'}
                d=k.design(p)
                Y=[(rng.randrange(2),rng.randrange(2)) for _ in range(n)]
                R=[(rng.randrange(2),rng.randrange(2)) for _ in range(n)]
                actions=[];reports=[];labels=[];state=d['initial']
                for t in range(1,n+1):
                    a=int(rng.random()>=float(d['w'][state][0]));r=R[t-1][a]
                    actions.append(a);reports.append(r);labels.append(str(Y[t-1][a]))
                    stop=k.must_stop(d,t,state,a,r)
                    state=d['next'][state][a][r]
                    if stop:break
                e={'assignments':actions,'reports':reports,'true_intervals':labels}
                pin=k.digest(p);epin=k.commitment(pin,e)
                py=k.audit(p,e,protocol_pin=pin,evidence_pin=epin)
                js=self.audit_node(p,e,pin,epin,folder)
                self.assertEqual(py,js,(iteration,p,e))

    def test_nodes_reject_tampered_record(self):
        p=k.read(HERE/'example_protocol.json');e=k.read(HERE/'example_evidence.json')
        pin=k.digest(p);epin=k.commitment(pin,e)
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);e['reports'][0]=1
            (folder/'p.json').write_text(json.dumps(p))
            (folder/'e.json').write_text(json.dumps(e))
            proc=subprocess.run(['node',str(HERE/'independent.js'),str(folder/'p.json'),
                str(folder/'e.json'),pin,epin],capture_output=True,text=True,timeout=30)
            self.assertEqual(proc.returncode,2)
            self.assertIn('REJECTED',proc.stderr)

if __name__=='__main__':unittest.main()
