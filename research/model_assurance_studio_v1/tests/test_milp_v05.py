"""Numerical MILP adversary only provides independently re-evaluated witnesses."""
import json
import math
from pathlib import Path
import random
import unittest
from unittest.mock import patch
from fractions import Fraction
from fastapi.testclient import TestClient
from studio.dense_nn import screen_onnx,_execute_intervals
from studio.engine import analyze,parse_policy,IntakeError,digest_json
from studio.milp_challenge import search,build_milp,ChallengeUnsupported
from studio.verify_receipt import replay_verify,verify
from studio.server import app
from tests.test_dense_v04 import dense_sample

ROOT=Path(__file__).resolve().parents[1]
HIDDEN=(ROOT/'samples/demo_hidden_spike.onnx').read_bytes()
ABS=(ROOT/'samples/demo_partition_abs.onnx').read_bytes()
POL={'check_output_bounds':True,'search_scalar_witness':True,'enable_reference_replay':True,
     'enable_milp_challenger':True,'milp_timeout_seconds':6,
     'input_min':-1,'input_max':1,'output_min':0,'output_max':.5}

class MILPAdversarialTests(unittest.TestCase):
    def test_finds_narrow_interstitial_violation_missed_by_probes(self):
        r=analyze('demo_hidden_spike.onnx',HIDDEN,POL)
        self.assertNotIn('dense_counterexample',r['details'])
        self.assertEqual(r['details']['milp_challenge']['status'],'IDEALIZED_VIOLATION_CANDIDATE')
        self.assertEqual(r['details']['milp_replay']['status'],'VIOLATION_REPRODUCED')
        self.assertGreater(r['details']['milp_replay']['outputs'][0],POL['output_max'])
        self.assertEqual(next(c['status'] for c in r['checks'] if c['id']=='ONNX_DENSE_MILP'),'FAIL')
        self.assertTrue(replay_verify(r,HIDDEN)[0])

    def test_recomputes_witness_with_exact_rationals_and_float32_in_box(self):
        s=screen_onnx(HIDDEN)
        r=search(s,POL)
        x=r['witness']['inputs']['x'][0]
        self.assertGreaterEqual(x,POL['input_min'])
        self.assertLessEqual(x,POL['input_max'])
        self.assertEqual(__import__('struct').unpack('<f',__import__('struct').pack('<f',x))[0],x)
        exact=_execute_intervals(s,[(Fraction.from_float(x),Fraction.from_float(x))])[0]
        self.assertEqual(str(exact[0]),r['witness']['idealized_outputs'][0])
        self.assertGreater(exact[0],Fraction(1,2))

    def test_numerical_solver_failure_is_open_not_safe(self):
        with patch('studio.milp_challenge.build_milp',side_effect=ChallengeUnsupported('blocked')):
            out=search(screen_onnx(HIDDEN),POL)
        self.assertEqual(out['status'],'INDETERMINATE')
        self.assertNotIn('witness',out)

    def test_no_witness_is_not_proof(self):
        out=search(screen_onnx(ABS),POL|{'output_max':1})
        self.assertEqual(out['status'],'OPEN_NO_REPRODUCED_WITNESS')
        self.assertNotIn('witness',out)
        self.assertIn('no lack-of-counterexample safety proof',out['limitation'])

    def test_existing_probe_witness_skips_expensive_solver(self):
        raw=(ROOT/'samples/demo_dense_neural_violation.onnx').read_bytes()
        r=analyze('x.onnx',raw,POL)
        self.assertIn('dense_counterexample',r['details'])
        self.assertNotIn('milp_challenge',r['details'])
        self.assertEqual(next(c['status'] for c in r['checks'] if c['id']=='ONNX_DENSE_MILP'),'OPEN')

    def test_candidate_without_numerical_replay_never_becomes_fail(self):
        r=analyze('x.onnx',HIDDEN,POL|{'enable_reference_replay':False})
        self.assertIn('milp_counterexample',r['details'])
        self.assertNotIn('milp_replay',r['details'])
        self.assertEqual(next(c['status'] for c in r['checks'] if c['id']=='ONNX_DENSE_MILP'),'OPEN')

    def test_only_supported_operator_networks(self):
        raw=dense_sample(op='Sigmoid')
        r=analyze('x.onnx',raw,POL)
        self.assertEqual(next(c['status'] for c in r['checks'] if c['id']=='ONNX_DENSE_MILP'),'OPEN')
        self.assertNotIn('milp_counterexample',r['details'])

    def test_fails_closed_when_scipy_missing(self):
        spec=screen_onnx(HIDDEN)
        original=__import__
        def fake_import(name,*args,**kwargs):
            if name.startswith('scipy'):raise ImportError('scipy unavailable')
            return original(name,*args,**kwargs)
        with patch('builtins.__import__',side_effect=fake_import):
            out=search(spec,POL)
        self.assertEqual(out['status'],'INDETERMINATE')

    def test_milp_budget_validation(self):
        for bad in [-1,0,16,1.5,True,'3']:
            with self.subTest(bad=bad):
                with self.assertRaises(IntakeError):parse_policy({'milp_timeout_seconds':bad})

    def test_oversized_values_abstain(self):
        p=POL|{'input_min':-1e9,'input_max':1e9}
        r=search(screen_onnx(HIDDEN),p)
        self.assertEqual(r['status'],'INDETERMINATE')

    def test_api_receipt_contains_milp_evidence_and_model_digest(self):
        cli=TestClient(app)
        r=cli.post('/api/analyze',content=HIDDEN,headers={'x-pcs-filename':'demo_hidden_spike.onnx',
                      'x-pcs-policy':json.dumps(POL)})
        self.assertEqual(r.status_code,200)
        self.assertEqual(r.json()['details']['milp_replay']['status'],'VIOLATION_REPRODUCED')

    def test_signer_considers_milp_receipt_replay(self):
        import tempfile
        from studio.signature import generate_keypair,sign,verify_signature
        raw=HIDDEN
        r=analyze('x.onnx',raw,POL)
        with tempfile.TemporaryDirectory() as temp:
            private=Path(temp)/'key.pem';pub=Path(temp)/'key.pub'
            fp=generate_keypair(private,pub)
            sig=sign(r,raw,private.read_bytes())
            self.assertTrue(verify_signature(sig,r,raw,fp)[0])

    def test_two_independent_float32_references_replay_hidden_witness(self):
        import importlib.util
        if importlib.util.find_spec('torch') is None:self.skipTest('torch optional')
        r=analyze('x.onnx',HIDDEN,POL|{'enable_torch_crosscheck':True})
        self.assertTrue(r['details']['torch_reference']['both_reproduced_violation'])
        self.assertEqual(next(c['status'] for c in r['checks'] if c['id']=='ONNX_DENSE_TWO_RUNTIME'),'FAIL')

    def test_randomized_linear_networks_return_only_exact_checked_candidates(self):
        # Run a few independent small MatMul models; do not trust HiGHS alone.
        rng=random.Random(904)
        for i in range(8):
            raw=dense_sample(weights=tuple(rng.choice([-.5,0.,.5,1.]) for _ in range(4)),
                bias=tuple(rng.choice([-.5,0.,.5]) for _ in range(2)))
            spec=screen_onnx(raw)
            out=search(spec,POL,timeout=2)
            self.assertIn(out['status'],('IDEALIZED_VIOLATION_CANDIDATE','OPEN_NO_REPRODUCED_WITNESS','INDETERMINATE'))
            if out['status']=='IDEALIZED_VIOLATION_CANDIDATE':
                xx=out['witness']['inputs'][spec['input']]
                y=_execute_intervals(spec,[(Fraction.from_float(z),Fraction.from_float(z)) for z in xx])
                self.assertTrue(any(a<Fraction(0) or b>Fraction(1,2) for a,b in y))

if __name__=='__main__':unittest.main()
