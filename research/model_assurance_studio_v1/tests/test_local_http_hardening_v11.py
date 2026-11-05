"""Bounded local upload metadata and duplicate-host header adversarial tests."""
from __future__ import annotations
import json
import unittest
from urllib.parse import quote
from fastapi.testclient import TestClient
from studio.server import app
from studio.engine import DEFAULT_POLICY
from tests.make_samples import onnx_sample

class HTTPHeaderHardeningV11(unittest.TestCase):
    def setUp(self):self.client=TestClient(app)
    def test_valid_upload_retains_open_only(self):
        r=self.client.post('/api/analyze',content=onnx_sample(),headers={
            'x-pcs-filename':'example.onnx','x-pcs-policy':quote(json.dumps(DEFAULT_POLICY))})
        self.assertEqual(r.status_code,200)
        self.assertIn(r.json()['decision'],('FAIL','OPEN'))
    def test_oversized_and_ambiguous_policy_headers_refused(self):
        for policy in (' '*8200,'{"max_pdb_clashes": 1,"max_pdb_clashes": 0}',
                       '{"input_min":NaN}','{"input_min":Infinity}'):
            with self.subTest(policy=policy[:35]):
                r=self.client.post('/api/analyze',content=onnx_sample(),
                    headers={'x-pcs-filename':'x.onnx','x-pcs-policy':quote(policy)})
                self.assertEqual(r.status_code,400)
    def test_duplicate_host_and_origin_abstain(self):
        for headers in (
          [(b'host',b'localhost:8765'),(b'host',b'evil.invalid')],
          [(b'host',b'localhost:8765'),(b'origin',b'http://localhost:8765'),(b'origin',b'http://evil.invalid')],
        ):
            with self.subTest(headers=headers):
                response=self.client.get('/api/status',headers=[(k.decode(),v.decode()) for k,v in headers])
                self.assertEqual(response.status_code,403)

if __name__=='__main__':unittest.main()
