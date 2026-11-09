"""Differential exact-rational check against a separate Node.js implementation."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from research.evidencekernel_fsm_v21.kernel import audit, attempt_commitment
from research.evidencekernel_fsm_v21.test_fsm import protocol
from research.evidencekernel_selective_v17.kernel import digest

HERE=Path(__file__).parent

class DifferentialTests(unittest.TestCase):
    def test_eighteen_exact_cross_language_cases(self):
        p=protocol()
        pin=digest(p)
        for first in range(6):
            for terminal in (0, 2, 5):
                import itertools
                space=list(itertools.combinations(range(4),2))
                ids=[first,first,terminal]
                z=space[terminal]
                for binary in (False,True):
                    e={"attempts":[list(space[i]) for i in ids],
                       "selected_assignment":list(z),
                       "observed_intervals":(["1" if i in z else "0" for i in range(4)]
                                             if binary else ["01"]*4)}
                    apin=attempt_commitment(pin,e["attempts"])
                    py=audit(p,e,protocol_pin=pin,attempts_pin=apin)
                    with tempfile.TemporaryDirectory() as td:
                        root=Path(td)
                        (root/"p.json").write_text(json.dumps(p),encoding="utf-8")
                        (root/"e.json").write_text(json.dumps(e),encoding="utf-8")
                        run=subprocess.run(["node",str(HERE/"independent.js"),
                                            str(root/"p.json"),str(root/"e.json"),pin,apin],
                                           text=True,capture_output=True,timeout=30)
                    self.assertEqual(run.returncode,0,run.stderr)
                    self.assertEqual(json.loads(run.stdout),py,(first,terminal,binary))

    def test_external_pin_is_required_in_both_languages(self):
        import itertools
        p=protocol()
        a=list(itertools.combinations(range(4),2))
        e={"attempts":[list(a[i]) for i in [0,0,1]],
           "selected_assignment":list(a[1]),
           "observed_intervals":["01"]*4}
        pin=digest(p)
        ap=attempt_commitment(pin,e["attempts"])
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            (root/"p.json").write_text(json.dumps(p),encoding="utf-8")
            (root/"e.json").write_text(json.dumps(e),encoding="utf-8")
            for pp,aa in [("0"*64,ap),(pin,"0"*64)]:
                run=subprocess.run(["node",str(HERE/"independent.js"),
                                    str(root/"p.json"),str(root/"e.json"),pp,aa],
                                   text=True,capture_output=True,timeout=30)
                self.assertNotEqual(run.returncode,0)

if __name__=="__main__":
    unittest.main()
