"""v0.5 adversarial tests: exact-cover proof, second numerical evaluator and signer pinning."""
import copy
import json
import os
from pathlib import Path
import random
import stat
import struct
import tempfile
import unittest
from unittest.mock import patch
from fractions import Fraction
from fastapi.testclient import TestClient
from studio.engine import analyze,parse_policy,digest_json,IntakeError
from studio.partition_proof import make_certificate,verify_certificate
from studio.dense_nn import screen_onnx,_execute_intervals
from studio.verify_receipt import verify,replay_verify
from studio.verify_partition import verify_proof_from_receipt
from studio.signature import generate_keypair,sign,verify_signature
from studio.multiruntime import crosscheck_torch
from studio.server import app
from tests.test_dense_v04 import dense_sample

ROOT=Path(__file__).resolve().parents[1]
ABS=(ROOT/'samples'/'demo_partition_abs.onnx').read_bytes()
DENSE=(ROOT/'samples'/'demo_dense_neural_violation.onnx').read_bytes()
PROOF_POLICY={'check_output_bounds':True,'enable_partition_proof':True,'max_partition_leaves':16,
              'input_min':-1,'input_max':1,'output_min':0,'output_max':1,'search_scalar_witness':False}

class ExactCoverTests(unittest.TestCase):
    def setUp(self):
        self.spec=screen_onnx(ABS)
        self.r=analyze('demo_partition_abs.onnx',ABS,PROOF_POLICY)
        self.result=self.r['details']['partition_proof']
        self.proof=self.result['certificate']

    def test_genuine_nontrivial_certificate(self):
        self.assertEqual(self.result['status'],'PROVED_CONDITIONALLY')
        self.assertEqual(self.result['leaves'],2)
        self.assertEqual(next(c['status'] for c in self.r['checks'] if c['id']=='ONNX_DENSE_REAL_BOX'),'OPEN')
        self.assertEqual(next(c['status'] for c in self.r['checks'] if c['id']=='ONNX_DENSE_PARTITION'),'PASS')
        self.assertEqual(self.r['decision'],'OPEN')
        self.assertTrue(verify_certificate(self.spec,PROOF_POLICY,self.proof)[0])
        self.assertTrue(verify_proof_from_receipt(self.r,ABS)[0])
        self.assertTrue(replay_verify(self.r,ABS)[0])

    def test_one_leaf_budget_does_not_claim_proof(self):
        r=make_certificate(self.spec,PROOF_POLICY,max_leaves=1)
        self.assertEqual(r['status'],'OPEN')
        self.assertNotIn('certificate',r)

    def test_changed_target_not_accepted(self):
        self.assertFalse(verify_certificate(self.spec,PROOF_POLICY|{'output_max':0.5},self.proof)[0])

    def test_changed_model_not_accepted(self):
        tampered=ABS.replace(struct.pack('<f',-1),struct.pack('<f',-2))
        self.assertFalse(verify_proof_from_receipt(self.r,tampered)[0])

    def test_missing_branch_cannot_pass_even_with_recomputed_digest(self):
        broken=copy.deepcopy(self.proof)
        broken['tree']['right']=broken['tree']['left']
        broken['tree']['at']='1/2'  # leaves no longer cover valid alleged enclosures
        self.assertFalse(self._rehashed_valid(broken))

    def test_false_leaf_claim_rejected(self):
        broken=copy.deepcopy(self.proof)
        broken['tree']['left']['bounds'][0][1]='0'
        self.assertFalse(self._rehashed_valid(broken))

    def test_noncovering_split_rejected(self):
        broken=copy.deepcopy(self.proof)
        broken['tree']['at']='-1'
        self.assertFalse(self._rehashed_valid(broken))

    def test_split_axis_invalid(self):
        broken=copy.deepcopy(self.proof)
        broken['tree']['axis']=8
        self.assertFalse(self._rehashed_valid(broken))

    def test_missing_leaf_rejected(self):
        broken=copy.deepcopy(self.proof)
        broken['tree'].pop('right')
        self.assertFalse(self._rehashed_valid(broken))

    def test_leaf_count_forgery_rejected(self):
        broken=copy.deepcopy(self.proof)
        broken['leaves']=1
        self.assertFalse(self._rehashed_valid(broken))

    def test_leaves_only_check_idealized_real_arithmetic(self):
        self.assertIn('real',self.proof['scope'].lower())
        self.assertNotEqual(self.r['decision'],'PASS')

    def test_random_points_inside_certified_input_box(self):
        rng=random.Random(509)
        for i in range(130):
            x=Fraction(rng.randint(-1_000_000,1_000_000),1_000_000)
            result=_execute_intervals(self.spec,[(x,x)])
            self.assertGreaterEqual(result[0][0],0)
            self.assertLessEqual(result[0][1],1)

    def test_digest_and_cover_tamper_fuzz(self):
        rng=random.Random(510)
        for _ in range(40):
            broken=copy.deepcopy(self.proof)
            choices=['left','right','split','count','scope','hash']
            case=rng.choice(choices)
            if case in ('left','right'):
                broken['tree'][case]['bounds'][0][rng.randint(0,1)]=str(rng.randint(2,8))
            elif case=='split':broken['tree']['at']=str(rng.randint(2,8))
            elif case=='count':broken['leaves']=rng.randint(3,9)
            elif case=='scope':broken['scope']='invented assurance'
            else:broken['certificate_sha256']='0'*64
            if case!='hash':broken['certificate_sha256']=digest_json({k:v for k,v in broken.items() if k!='certificate_sha256'})
            # digest_json canonical matches certificate digest generation.
            self.assertFalse(verify_certificate(self.spec,PROOF_POLICY,broken)[0])

    def test_claim_inventory_carries_box_assumption(self):
        inv=self.r['pcs_claim_inventory']
        for c in inv['claims']:
            ev=next(e for e in inv['evidence'] if e['id']==c['required_evidence'][0])
            if ev['details']['check_id']=='ONNX_DENSE_PARTITION':
                self.assertIn('conditional-real-arithmetic-input-range',c['assumptions'])
                break
        else:self.fail('partition claim missing')

    def test_api_responds_with_cert(self):
        c=TestClient(app)
        res=c.post('/api/analyze',content=ABS,headers={'x-pcs-filename':'demo_partition_abs.onnx',
           'x-pcs-policy':json.dumps(PROOF_POLICY)})
        self.assertEqual(res.status_code,200)
        self.assertEqual(res.json()['details']['partition_proof']['status'],'PROVED_CONDITIONALLY')

    def test_policy_invalid_budget_rejected(self):
        for budget in [-1,0,129,1.5,True,'10']:
            with self.subTest(budget=budget):
                with self.assertRaises(IntakeError):parse_policy({'max_partition_leaves':budget})

    def test_unproved_region_not_accepted(self):
        bad=PROOF_POLICY|{'output_max':-0.2,'output_min':-1}
        result=make_certificate(self.spec,bad,max_leaves=8)
        self.assertEqual(result['status'],'OPEN')

    def _rehashed_valid(self,proof):
        proof['certificate_sha256']=digest_json({k:v for k,v in proof.items() if k!='certificate_sha256'})
        return verify_certificate(self.spec,PROOF_POLICY,proof)[0]

class NumericalCrosscheckTests(unittest.TestCase):
    def setUp(self):
        self.p={'check_output_bounds':True,'enable_reference_replay':True,
                'enable_torch_crosscheck':True,'search_scalar_witness':True,
                'output_min':0,'output_max':1}

    def test_two_real_engines_reproduce_scoped_violation(self):
        import importlib.util
        if importlib.util.find_spec('torch') is None:self.skipTest('PyTorch optional')
        r=analyze('demo_dense_neural_violation.onnx',DENSE,self.p)
        self.assertEqual(r['details']['torch_reference']['status'],'VIOLATION_REPRODUCED')
        self.assertTrue(r['details']['torch_reference']['both_reproduced_violation'])
        self.assertEqual(r['details']['torch_reference']['agreement'],'WITHIN_TOLERANCE')
        self.assertEqual(next(c['status'] for c in r['checks'] if c['id']=='ONNX_DENSE_TWO_RUNTIME'),'FAIL')
        self.assertTrue(replay_verify(r,DENSE)[0])

    def test_no_unjustified_claim_when_reference_worker_times_out(self):
        spec=screen_onnx(DENSE)
        witness={'inputs':{spec['input']:[1.,1.]}}
        with patch('studio.multiruntime.subprocess.run',side_effect=__import__('subprocess').TimeoutExpired('cmd',18)):
            out=crosscheck_torch(spec,witness,(Fraction(0),Fraction(1)),None)
        self.assertEqual(out['status'],'INDETERMINATE')

    def test_no_crosscheck_when_not_requested(self):
        r=analyze('x.onnx',DENSE,self.p|{'enable_torch_crosscheck':False})
        self.assertNotIn('torch_reference',r['details'])

    def test_wrong_proposed_numerical_outputs_become_disagreement(self):
        import importlib.util
        if importlib.util.find_spec('torch') is None:self.skipTest('PyTorch optional')
        spec=screen_onnx(DENSE)
        witness={'inputs':{spec['input']:[1.,1.]}}
        out=crosscheck_torch(spec,witness,(Fraction(0),Fraction(1)),{'status':'VIOLATION_REPRODUCED','outputs':[-100.,100.]})
        self.assertEqual(out['agreement'],'DISAGREE')
        self.assertFalse(out['both_reproduced_violation'])

    def test_unknown_network_opt_in_stays_open(self):
        r=analyze('x.onnx',dense_sample(op='Sigmoid'),self.p)
        self.assertNotIn('torch_reference',r['details'])
        self.assertEqual(next(c['status'] for c in r['checks'] if c['id']=='ONNX_DENSE_TWO_RUNTIME'),'OPEN')

class PublisherTrustTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        d=Path(self.temp.name)
        self.private=d/'test-secret.pem';self.public=d/'test-public.pem'
        self.fp=generate_keypair(self.private,self.public)
        self.receipt=analyze('demo_partition_abs.onnx',ABS,PROOF_POLICY)
        self.envelope=sign(self.receipt,ABS,self.private.read_bytes())

    def test_valid_pinned_publisher_signed_replay(self):
        ok,msg=verify_signature(self.envelope,self.receipt,ABS,self.fp)
        self.assertTrue(ok,msg)
        self.assertIn('NOT independent trusted verification',msg)

    def test_wrong_signer_fingerprint_rejects(self):
        self.assertFalse(verify_signature(self.envelope,self.receipt,ABS,'0'*64)[0])
        self.assertFalse(verify_signature(self.envelope,self.receipt,ABS,'')[0])

    def test_unsigned_issuer_authentication_not_inferred(self):
        self.assertTrue(verify(self.receipt,ABS)[0])
        self.assertFalse(verify_signature({},self.receipt,ABS,self.fp)[0])

    def test_mutating_findings_invalidates_original_signature(self):
        fake=copy.deepcopy(self.receipt)
        fake['decision']='FAIL'
        fake['receipt_sha256']=digest_json({k:v for k,v in fake.items() if k!='receipt_sha256'})
        self.assertFalse(verify_signature(self.envelope,fake,ABS,self.fp)[0])

    def test_mutating_model_invalidates_original_signature(self):
        self.assertFalse(verify_signature(self.envelope,self.receipt,ABS+b'evil',self.fp)[0])

    def test_attacker_key_cannot_impersonate_trust_pin(self):
        d=Path(self.temp.name)
        newpriv=d/'attacker.pem';newpub=d/'attacker.pub'
        newfp=generate_keypair(newpriv,newpub)
        env=sign(self.receipt,ABS,newpriv.read_bytes())
        self.assertNotEqual(newfp,self.fp)
        self.assertFalse(verify_signature(env,self.receipt,ABS,self.fp)[0])

    def test_modified_signature_rejected(self):
        env=copy.deepcopy(self.envelope)
        env['signature_b64']='AAAA'+env['signature_b64'][4:]
        self.assertFalse(verify_signature(env,self.receipt,ABS,self.fp)[0])

    def test_missing_signature_field_rejected(self):
        env=copy.deepcopy(self.envelope)
        env.pop('signature_b64')
        self.assertFalse(verify_signature(env,self.receipt,ABS,self.fp)[0])

    def test_refuses_to_sign_forged_unsigned_report_even_if_digest_recomputed(self):
        fake=copy.deepcopy(self.receipt)
        fake['decision']='FAIL'
        fake['receipt_sha256']=digest_json({k:v for k,v in fake.items() if k!='receipt_sha256'})
        with self.assertRaises(ValueError):sign(fake,ABS,self.private.read_bytes())

    def test_refuses_overwrite_key(self):
        with self.assertRaises(FileExistsError):generate_keypair(self.private,self.public)
        self.assertTrue(verify_signature(self.envelope,self.receipt,ABS,self.fp)[0])

    @unittest.skipIf(os.name=='nt','mode bits not portable to Windows')
    def test_private_key_not_world_readable(self):
        self.assertEqual(stat.S_IMODE(self.private.stat().st_mode)&0o077,0)

if __name__=='__main__':unittest.main()
