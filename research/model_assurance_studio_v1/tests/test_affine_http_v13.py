"""Actual local API and claim-intake hardening for optional correlated FP32."""
import hashlib
import json
import unittest
from pathlib import Path
from fastapi.testclient import TestClient
from studio.server import app
from studio.affine_fp32_v13 import POLICY_SCHEMA
from studio.relational_kernel import canonical
from studio.dense_nn import screen_onnx

ROOT=Path(__file__).resolve().parents[1]

class AffineHTTPV13(unittest.TestCase):
    def setUp(self):
        self.client=TestClient(app)
        self.model=(ROOT/'samples/demo_correlated_fp32_margin_v13.onnx').read_bytes()
        self.claim={'input_box':[['-1000','1000']]*2,'input_min':'-1000','input_max':'1000',
                    'output_coefficients':['1','-1'],'upper_limit':'-1/2'}

    def request(self,claim=None,raw=None,extra=None):
        return self.client.post('/api/affine-fp32',content=self.model if raw is None else raw,
             headers={'X-PCS-Affine-Claim':json.dumps(self.claim if claim is None else claim),
                      **(extra or {})})

    def test_genuine_uploaded_model_candidate_is_not_trusted_certification(self):
        r=self.request()
        self.assertEqual(r.status_code,200,r.text)
        x=r.json()
        self.assertEqual(x['candidate']['status'],'CANDIDATE_REPLAYED')
        self.assertEqual(x['candidate']['review']['status'],'PROVED_CONDITIONALLY')
        self.assertEqual(x['independent_reviewer_acceptance'],'NOT_ESTABLISHED')
        self.assertEqual(x['lean_kernel_verification'],'NOT_ESTABLISHED')
        self.assertEqual(x['suggested_reviewer_policy']['schema'],POLICY_SCHEMA)
        self.assertEqual(x['suggested_reviewer_policy']['model_sha256'],hashlib.sha256(self.model).hexdigest())

    def test_fixed_demonstration_replays_all_required_claims(self):
        r=self.client.get('/api/affine-demo');self.assertEqual(r.status_code,200)
        x=r.json()
        self.assertEqual(x['comparison']['old_interval_upper'],'1999')
        self.assertEqual(x['comparison']['affine']['status'],'PROVED_CONDITIONALLY')
        self.assertEqual(x['review']['status'],'PROVED_CONDITIONALLY')
        self.assertEqual(len(x['examples']),3)
        self.assertEqual(x['outside_region']['status'],'ABSTAIN')

    def test_unknown_claim_rejected(self):
        c=dict(self.claim,claimed_lean_proof=True)
        r=self.request(c)
        self.assertEqual(r.status_code,400)

    def test_malformed_and_oversize_upload_refused(self):
        for raw in (b'',b'not a model',self.model+b'\x00'):
            with self.subTest(raw=raw[:12]):
                r=self.request(raw=raw)
                self.assertEqual(r.status_code,400)

    def test_duplicate_policy_keys_rejected(self):
        claim=json.dumps(self.claim).replace('"upper_limit": "-1/2"','"upper_limit": "1000", "upper_limit": "-1/2"')
        r=self.client.post('/api/affine-fp32',content=self.model,headers={'X-PCS-Affine-Claim':claim})
        self.assertEqual(r.status_code,400)

    def test_invalid_user_origin_rejected_before_intake(self):
        r=self.request(extra={'Origin':'https://evil.invalid'})
        self.assertEqual(r.status_code,403)

if __name__=='__main__':unittest.main()
