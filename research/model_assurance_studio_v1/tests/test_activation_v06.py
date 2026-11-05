"""Complete activation-cover certificates: both branches independently checked."""
import copy
from fractions import Fraction
import json
from pathlib import Path
import subprocess
import sys
import unittest
from fastapi.testclient import TestClient
from tests.make_activation_sample import demo
from studio.activation_proof import propose,verify
from studio.relational_kernel import digest,canonical
from studio.relational_prover import propose as global_propose
from studio.verify_relational import verify_with_policy,POLICY_SCHEMA
from studio.engine import analyze
from studio.verify_receipt import replay_verify
from studio.server import app

RAW=demo()
DOMAIN=[['-1','1']]
POLICY={'schema':POLICY_SCHEMA,'input_box':DOMAIN,'output_coefficients':['1'],'upper_limit':'0'}

class CaseCoverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result=propose(RAW,DOMAIN,['1'],'0',max_leaves=16,timeout=3)
        assert cls.result['status']=='PROVED_CONDITIONALLY',cls.result
        cls.cert=cls.result['certificate']
    def rehash(self,c):c['certificate_sha256']=digest(canonical({k:v for k,v in c.items() if k!='certificate_sha256'}))
    def test_global_linear_relaxation_is_inconclusive(self):
        self.assertEqual(global_propose(RAW,DOMAIN,['1'],'0')['status'],'OPEN')
    def test_activation_cover_succeeds(self):
        ok,info=verify(RAW,self.cert)
        self.assertTrue(ok,info)
        self.assertEqual(info['fully_checked_cases'],2)
        self.assertEqual(verify_with_policy(RAW,self.cert,POLICY)[0],True)
    def test_opposite_bound_also_succeeds(self):
        res=propose(RAW,DOMAIN,['-1'],'0',max_leaves=16,timeout=3)
        self.assertEqual(res['status'],'PROVED_CONDITIONALLY',res)
        self.assertTrue(verify(RAW,res['certificate'])[0])
    def test_false_claim_fails_closed(self):
        res=propose(RAW,DOMAIN,['1'],'-1/4',max_leaves=16,timeout=3)
        self.assertEqual(res['status'],'OPEN',res)
        self.assertNotIn('certificate',res)
    def test_incomplete_budget_produces_no_certificate(self):
        res=propose(RAW,DOMAIN,['1'],'0',max_leaves=1,timeout=3)
        self.assertEqual(res['status'],'OPEN')
        self.assertNotIn('certificate',res)
    def test_missing_branches_rejected_even_when_rehashed(self):
        x=copy.deepcopy(self.cert);x['tree'].pop('active');self.rehash(x)
        self.assertFalse(verify(RAW,x)[0])
    def test_altered_phase_label_rejected(self):
        x=copy.deepcopy(self.cert);x['tree']['node_name']='not_relu';self.rehash(x)
        self.assertFalse(verify(RAW,x)[0])
    def test_altered_relu_index_rejected(self):
        x=copy.deepcopy(self.cert);x['tree']['unit']=3;self.rehash(x)
        self.assertFalse(verify(RAW,x)[0])
    def test_forged_leaf_algebra_rejected(self):
        x=copy.deepcopy(self.cert);x['tree']['inactive']['multipliers'][0][1]='200';self.rehash(x)
        self.assertFalse(verify(RAW,x)[0])
    def test_swapped_leaf_witnesses_rejected(self):
        x=copy.deepcopy(self.cert)
        x['tree']['inactive']['multipliers'],x['tree']['active']['multipliers']=x['tree']['active']['multipliers'],x['tree']['inactive']['multipliers']
        self.rehash(x);self.assertFalse(verify(RAW,x)[0])
    def test_modified_model_rejected(self):
        from struct import pack
        changed=RAW.replace(pack('<f',-1),pack('<f',-2),1)
        self.assertNotEqual(changed,RAW)
        self.assertFalse(verify(changed,self.cert)[0])
    def test_changed_scope_rejected(self):
        x=copy.deepcopy(self.cert);x['scope']='full IEEE754 guarantee';self.rehash(x)
        self.assertFalse(verify(RAW,x)[0])
    def test_changed_reviewer_domain_rejected(self):
        x=copy.deepcopy(self.cert);x['input_box']=[['0','0']];self.rehash(x)
        self.assertFalse(verify_with_policy(RAW,x,POLICY)[0])
    def test_forged_leaf_count_rejected(self):
        x=copy.deepcopy(self.cert);x['leaves']=1;self.rehash(x)
        self.assertFalse(verify(RAW,x)[0])
    def test_leaf_path_recursion_rejected(self):
        x=copy.deepcopy(self.cert)
        x['tree']['active']=copy.deepcopy(x['tree'])
        self.rehash(x)
        self.assertFalse(verify(RAW,x)[0])
    def test_independent_cli_without_solver_or_numpy(self):
        x=subprocess.run([sys.executable,'-S','-m','studio.verify_relational',
            'samples/demo_activation_identity.onnx','validation/v06_activation_identity_certificate.json',
            'validation/v06_activation_reviewer_policy.json'],capture_output=True,text=True,timeout=8)
        self.assertEqual(x.returncode,0,x.stdout+x.stderr)
    def test_engine_report_scoped_pass_without_safe_verdict(self):
        p={'enable_relational_certificate':True,'enable_activation_case_cover':True,
           'relational_coefficients':['1'],'relational_upper_limit':'0',
           'input_min':-1,'input_max':1}
        report=analyze('demo_activation_identity.onnx',RAW,p)
        self.assertEqual(report['decision'],'OPEN')
        self.assertEqual(report['details']['activation_proof']['status'],'PROVED_CONDITIONALLY')
        self.assertEqual(next(c['status'] for c in report['checks'] if c['id']=='ONNX_RELATIONAL_CASE_COVER'),'PASS')
        self.assertTrue(replay_verify(report,RAW)[0])
    def test_end_to_end_upload(self):
        p={'enable_relational_certificate':True,'enable_activation_case_cover':True,
           'relational_coefficients':['1'],'relational_upper_limit':'0'}
        response=TestClient(app).post('/api/analyze',content=RAW,
           headers={'x-pcs-filename':'demo_activation_identity.onnx','x-pcs-policy':json.dumps(p)})
        self.assertEqual(response.status_code,200,response.text[:300])
        self.assertEqual(response.json()['details']['activation_proof']['status'],'PROVED_CONDITIONALLY')

if __name__=='__main__':unittest.main()
