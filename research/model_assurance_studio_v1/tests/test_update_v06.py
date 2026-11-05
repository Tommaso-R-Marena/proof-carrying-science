"""Two-model Farkas proof and composition regression, including dangerous updates."""
import copy
import json
from pathlib import Path
import random
import subprocess
import sys
import unittest
from urllib.parse import quote
from fastapi.testclient import TestClient
from studio.model_update import compare,parse_update_policy,ModelUpdateError
from studio.update_kernel import verify
from studio.update_prover import propose
from studio.verify_update import verify_update_policy,verify_composition,UPDATE_POLICY_SCHEMA
from studio.verify_relational import POLICY_SCHEMA
from studio.relational_kernel import canonical,digest
from studio.server import app

ROOT=Path(__file__).resolve().parents[1]
OLD=(ROOT/'samples/demo_trained_iris_mlp.onnx').read_bytes()
NEW=(ROOT/'samples/demo_trained_iris_updated.onnx').read_bytes()
BAD=(ROOT/'samples/demo_trained_iris_bad_update.onnx').read_bytes()
PROFILE=json.loads((ROOT/'validation/v06_iris_profile.json').read_text())
DOMAIN=PROFILE['reviewer_box'];C=['-1','1','0']
POLICY={'schema':UPDATE_POLICY_SCHEMA,'old_model_sha256':digest(OLD),'new_model_sha256':digest(NEW),
        'input_box':DOMAIN,'output_coefficients':C,'upper_limit':'1/8'}
COMP={'input_box':DOMAIN,'output_coefficients':C,'baseline_upper_limit':'-1/2',
      'drift_upper_limit':'1/8','required_new_upper_limit':'-3/8'}

class UpdateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result=propose(OLD,NEW,DOMAIN,C,'1/8')
        assert cls.result['status']=='PROVED_CONDITIONALLY',cls.result
        cls.proof=cls.result['certificate']
        cls.baseline=json.loads((ROOT/'validation/v06_iris_property_1_certificate.json').read_text())
        cls.baseline_policy=json.loads((ROOT/'validation/v06_iris_property_1_reviewer_policy.json').read_text())
    def rehash(self,x):x['certificate_sha256']=digest(canonical({k:v for k,v in x.items() if k!='certificate_sha256'}))
    def test_exact_sharp_update_bound(self):
        good,info=verify(OLD,NEW,self.proof)
        self.assertTrue(good,info)
        self.assertEqual(info['verified_update_upper_bound'],'1/8')
        self.assertGreaterEqual(info['semantically_matched_nodes'],2)
        self.assertEqual(verify_update_policy(OLD,NEW,self.proof,POLICY)[0],True)
    def test_base_plus_update_proves_new_margin(self):
        ok,r=verify_composition(OLD,NEW,self.baseline,self.baseline_policy,self.proof,POLICY,
                                 required_updated_upper_limit='-3/8')
        self.assertTrue(ok,r)
        self.assertEqual(r['derived_new_model_upper_bound'],'-3/8')
    def test_tighter_requirement_not_inferred(self):
        self.assertFalse(verify_composition(OLD,NEW,self.baseline,self.baseline_policy,self.proof,POLICY,
                     required_updated_upper_limit='-1/2')[0])
    def test_dangerous_update_not_accepted(self):
        r=compare(OLD,BAD,COMP)
        self.assertEqual(r['status'],'OPEN')
        self.assertEqual(r['update']['status'],'OPEN')
    def test_insufficient_sharp_update_limit_not_certified(self):
        r=propose(OLD,NEW,DOMAIN,C,'1/16')
        self.assertEqual(r['status'],'OPEN')
        self.assertNotIn('certificate',r)
    def test_any_new_model_byte_change_breaks_digest(self):
        self.assertFalse(verify(OLD,BAD,self.proof)[0])
        self.assertFalse(verify(NEW,OLD,self.proof)[0])
    def test_forged_dual_rejected_even_if_rehashed(self):
        x=copy.deepcopy(self.proof);x['multipliers'][0][1]='5';self.rehash(x)
        self.assertFalse(verify(OLD,NEW,x)[0])
    def test_removed_multiplier_rejected(self):
        x=copy.deepcopy(self.proof);x['multipliers'].pop();self.rehash(x)
        self.assertFalse(verify(OLD,NEW,x)[0])
    def test_wrong_reviewer_model_anchor_rejected(self):
        p=copy.deepcopy(POLICY);p['old_model_sha256']='0'*64
        self.assertFalse(verify_update_policy(OLD,NEW,self.proof,p)[0])
    def test_reviewer_policy_cannot_shrink_box(self):
        p=copy.deepcopy(POLICY);p['input_box']=[['0','0']]*4
        self.assertFalse(verify_update_policy(OLD,NEW,self.proof,p)[0])
    def test_reviewer_policy_cannot_weaken_limit(self):
        p=copy.deepcopy(POLICY);p['upper_limit']='1'
        self.assertFalse(verify_update_policy(OLD,NEW,self.proof,p)[0])
    def test_composition_requires_matching_claims(self):
        p=copy.deepcopy(self.baseline_policy);p['output_coefficients']=['1','-1','0']
        self.assertFalse(verify_composition(OLD,NEW,self.baseline,p,self.proof,POLICY,
                         required_updated_upper_limit='-3/8')[0])
    def test_composition_requires_matching_domains(self):
        p=copy.deepcopy(self.baseline_policy);p['input_box']=[['0','0']]*4
        self.assertFalse(verify_composition(OLD,NEW,self.baseline,p,self.proof,POLICY,
                         required_updated_upper_limit='-3/8')[0])
    def test_exact_lagrange_dual_recovery_output(self):
        self.assertEqual(len(self.proof['multipliers']),17)
        self.assertTrue(all('/' not in str(v) or len(v)<200 for _,v in self.proof['multipliers']))
    def test_cli_standard_library_no_numerical_solver(self):
        command=[sys.executable,'-S','-m','studio.verify_update','compose',
            'samples/demo_trained_iris_mlp.onnx','samples/demo_trained_iris_updated.onnx',
            'validation/v06_iris_property_1_certificate.json','validation/v06_iris_property_1_reviewer_policy.json',
            'validation/v06_update_drift_certificate.json','validation/v06_update_reviewer_policy.json',
            '--required-new-upper=-3/8']
        p=subprocess.run(command,capture_output=True,text=True,timeout=10)
        self.assertEqual(p.returncode,0,p.stdout+p.stderr)
    def test_cli_negative_control(self):
        command=[sys.executable,'-S','-m','studio.verify_update','drift',
            'samples/demo_trained_iris_mlp.onnx','samples/demo_trained_iris_bad_update.onnx',
            'validation/v06_update_drift_certificate.json','validation/v06_update_reviewer_policy.json']
        p=subprocess.run(command,capture_output=True,text=True,timeout=10)
        self.assertNotEqual(p.returncode,0)
    def test_update_workflow_returns_checkable_package(self):
        r=compare(OLD,NEW,COMP)
        self.assertEqual(r['status'],'PROVED_CONDITIONALLY',r)
        self.assertEqual(r['composition']['derived_new_model_upper_bound'],'-3/8')
        self.assertTrue(verify_update_policy(OLD,NEW,r['update']['certificate'],r['update_reviewer_policy'])[0])
    def test_policy_malformed_abstains(self):
        cases=[{},COMP|{'input_box':[['1','0']]*4},COMP|{'drift_upper_limit':'nan'},
               COMP|{'output_coefficients':[]},COMP|{'extra':'trusted'}]
        for case in cases:
            with self.assertRaises(ModelUpdateError):parse_update_policy(case)
    def test_upload_endpoint_real_binary_pair(self):
        data=len(OLD).to_bytes(4,'little')+OLD+NEW
        r=TestClient(app).post('/api/compare-update',content=data,
                               headers={'x-pcs-update-policy':quote(json.dumps(COMP))})
        self.assertEqual(r.status_code,200,r.text[:400])
        self.assertEqual(r.json()['status'],'PROVED_CONDITIONALLY')
    def test_http_rejects_bad_envelopes_and_foreign_origins(self):
        c=TestClient(app);h={'x-pcs-update-policy':quote(json.dumps(COMP))}
        self.assertEqual(c.post('/api/compare-update',content=b'bad',headers=h).status_code,400)
        self.assertEqual(c.post('/api/compare-update',content=(0).to_bytes(4,'little')+OLD+NEW,headers=h).status_code,400)
        self.assertEqual(c.post('/api/compare-update',content=len(OLD).to_bytes(4,'little')+OLD+NEW,
                      headers=h|{'Host':'evil.example'}).status_code,403)

if __name__=='__main__':unittest.main()
