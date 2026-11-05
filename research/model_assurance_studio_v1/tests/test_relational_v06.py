"""Scoped mathematical verification, independent reviewer policy, and adversarial tests."""
import copy
from fractions import Fraction
import json
from pathlib import Path
import random
import subprocess
import sys
import unittest

from fastapi.testclient import TestClient
from tests.make_relational_sample import demo
from tests.test_dense_v04 import dense_sample
from studio.dense_nn import screen_onnx,_execute_intervals
from studio.engine import analyze,parse_policy,IntakeError
from studio.relational_kernel import build,check,canonical,digest, Unsupported
from studio.relational_prover import propose
from studio.verify_relational import POLICY_SCHEMA,verify_with_policy
from studio.verify_receipt import replay_verify
from studio.server import app

RAW=demo()
BOX=[['-1','1']]
COEFFS=['-1','1']
LIMIT='-1/4'
POLICY={'schema':POLICY_SCHEMA,'input_box':BOX,'output_coefficients':COEFFS,'upper_limit':LIMIT}

class RelationalCertificateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.answer=propose(RAW,BOX,COEFFS,LIMIT)
        assert cls.answer['status']=='PROVED_CONDITIONALLY',cls.answer
        cls.proof=cls.answer['certificate']
    def copy(self):return copy.deepcopy(self.proof)
    def rehash(self,x):x['certificate_sha256']=digest(canonical({k:v for k,v in x.items() if k!='certificate_sha256'}))
    def test_exact_margin_proven_with_four_multipliers(self):
        yes,info=check(RAW,self.proof)
        self.assertTrue(yes,info)
        self.assertEqual(Fraction(info['verified_upper_bound']),-Fraction(1,4))
        self.assertEqual(len(self.proof['multipliers']),4)
        self.assertEqual(verify_with_policy(RAW,self.proof,POLICY)[0],True)
    def test_interval_bounds_cannot_establish_same_margin(self):
        bounds=_execute_intervals(screen_onnx(RAW),[(Fraction(-1),Fraction(1))])
        independent_upper=bounds[1][1]-bounds[0][0]
        self.assertGreater(independent_upper,Fraction(-1,4))
        self.assertEqual(independent_upper,Fraction(3,4))
    def test_bad_claim_not_proved(self):
        p=propose(RAW,BOX,COEFFS,'-1/2')
        self.assertEqual(p['status'],'OPEN')
        self.assertNotIn('certificate',p)
    def test_modified_weights_rejected(self):
        import struct
        altered=RAW.replace(struct.pack('<f',0.25),struct.pack('<f',0.0))
        self.assertNotEqual(altered,RAW)
        self.assertFalse(check(altered,self.proof)[0])
    def test_changed_certificate_scope_rejected_even_if_rehashed(self):
        x=self.copy();x['scope']='IEEE_FLOAT32_FULL_RUNTIME_CERTIFIED';self.rehash(x)
        self.assertFalse(check(RAW,x)[0])
    def test_reviewer_domain_cannot_shrink(self):
        x=self.copy();x['input_box']=[['0','0']];self.rehash(x)
        self.assertFalse(verify_with_policy(RAW,x,POLICY)[0])
    def test_reviewer_cannot_be_swapped_to_weaker_output_limit(self):
        x=self.copy();x['relation']['upper_limit']='1';self.rehash(x)
        self.assertFalse(verify_with_policy(RAW,x,POLICY)[0])
    def test_reviewer_cannot_be_swapped_to_other_property(self):
        x=self.copy();x['relation']['output_coefficients']=['1','-1'];self.rehash(x)
        self.assertFalse(verify_with_policy(RAW,x,POLICY)[0])
    def test_multiplier_mutations_rejected_after_rehash(self):
        modes=['minus','neg','omit','double','duplicate','out_of_range','zero','extra','nan','huge']
        for mode in modes:
            with self.subTest(mode=mode):
                x=self.copy()
                if mode=='minus':x['multipliers'][0][1]='100'
                elif mode=='neg':x['multipliers'][0][1]='-1'
                elif mode=='omit':x['multipliers'].pop()
                elif mode=='double':x['multipliers'][0][1]=str(Fraction(x['multipliers'][0][1])*2)
                elif mode=='duplicate':x['multipliers'].append(x['multipliers'][0][:])
                elif mode=='out_of_range':x['multipliers'][0][0]=99999
                elif mode=='zero':x['multipliers'][0][1]='0'
                elif mode=='extra':x['extra_claim']='safe for all possible inputs'
                elif mode=='nan':x['multipliers'][0][1]='nan'
                else:x['multipliers'][0][1]='1/'+'9'*400
                self.rehash(x)
                self.assertFalse(check(RAW,x)[0])
    def test_certificate_digest_forgery_without_math_fails(self):
        x=self.copy();x['certificate_sha256']='0'*64
        self.assertFalse(check(RAW,x)[0])
    def test_wrong_policy_schema_fails(self):
        x=copy.deepcopy(POLICY);x['schema']='unknown'
        self.assertFalse(verify_with_policy(RAW,self.proof,x)[0])
    def test_no_numercial_optimizer_inside_checker(self):
        p=Path('validation/v06_relational_margin_certificate.json')
        pol=Path('validation/v06_relational_reviewer_policy.json')
        output=subprocess.run([sys.executable,'-S','-m','studio.verify_relational',
                               'samples/demo_relational_margin.onnx',str(p),str(pol)],
                              capture_output=True,text=True,timeout=8)
        self.assertEqual(output.returncode,0,output.stderr+output.stdout)
        self.assertIn('VERIFIED CONDITIONAL',output.stdout)
    def test_external_policy_changes_fail_cli(self):
        p=Path('validation/v06_relational_margin_certificate.json')
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            pol=Path(tmp)/'policy.json'
            pol.write_text(json.dumps(POLICY|{'upper_limit':'-1/2'}))
            result=subprocess.run([sys.executable,'-S','-m','studio.verify_relational',
                                    'samples/demo_relational_margin.onnx',str(p),str(pol)],
                                   capture_output=True,text=True,timeout=8)
            self.assertNotEqual(result.returncode,0)
    def test_numeric_row_constraints_enclose_real_exec_points(self):
        spec=screen_onnx(RAW)
        pol=build(spec,BOX)
        rng=random.Random(886)
        for x in [Fraction(-1),Fraction(0),Fraction(1)]+[Fraction(rng.randint(-1000,1000),1000) for _ in range(70)]:
            env=_execute_intervals(spec,[(x,x)],return_env=True)
            values=[Fraction(0)]*pol['variable_count']
            for name,ids in pol['variables'].items():
                for i,idx in enumerate(ids):
                    a,b=env[name][i];self.assertEqual(a,b)
                    values[idx]=a
            for row,rhs in pol['rows']:
                self.assertLessEqual(sum((v*values[k] for k,v in row.items()),Fraction(0)),rhs)
    def test_random_dense_models_polytope_contains_real_execution(self):
        rng=random.Random(877)
        for k in range(16):
            w=tuple(rng.choice([-2,-1,0,1,2]) for _ in range(4))
            b=tuple(rng.choice([-.5,0,.5]) for _ in range(2))
            raw=dense_sample(weights=w,bias=b)
            spec=screen_onnx(raw);poly=build(spec,[['-1','1'],['-1','1']])
            for x,y in [(Fraction(-1),Fraction(1)),(Fraction(0),Fraction(0)),(Fraction(1,2),Fraction(-1,2))]:
                env=_execute_intervals(spec,[(x,x),(y,y)],return_env=True)
                vals=[Fraction(0)]*poly['variable_count']
                for name,ids in poly['variables'].items():
                    for j,idx in enumerate(ids):vals[idx]=env[name][j][0]
                for row,rhs in poly['rows']:
                    self.assertLessEqual(sum((v*vals[i] for i,v in row.items()),Fraction(0)),rhs)
    def test_zero_wrong_width_and_nonfinite_policy_rejected(self):
        for coeffs in [[],['0','0'],['1'],['-1','nan'],['-1','1/0']]:
            self.assertEqual(propose(RAW,BOX,coeffs,LIMIT)['status'],'OPEN')
    def test_invalid_input_box_rejected(self):
        for box in [[['1','-1']], [['-1','1'],['-1','1']], [['nan','1']]]:
            self.assertEqual(propose(RAW,box,COEFFS,LIMIT)['status'],'OPEN')
    def test_unsupported_onnx_fails_closed(self):
        from tests.make_samples import onnx_sample
        self.assertEqual(propose(onnx_sample(op='Sigmoid'),BOX,['1'],'1')['status'],'OPEN')
    def test_full_report_and_replay(self):
        p={'enable_relational_certificate':True,'relational_coefficients':COEFFS,
           'relational_upper_limit':LIMIT,'input_min':-1,'input_max':1}
        r=analyze('demo_relational_margin.onnx',RAW,p)
        self.assertEqual(r['decision'],'OPEN')
        self.assertEqual(r['details']['relational_proof']['status'],'PROVED_CONDITIONALLY')
        self.assertEqual(next(c['status'] for c in r['checks'] if c['id']=='ONNX_RELATIONAL_FARKAS'),'PASS')
        self.assertTrue(replay_verify(r,RAW)[0])
    def test_api_real_upload(self):
        p={'enable_relational_certificate':True,'relational_coefficients':COEFFS,
           'relational_upper_limit':LIMIT}
        c=TestClient(app);res=c.post('/api/analyze',content=RAW,headers={'x-pcs-filename':'demo_relational_margin.onnx',
                                                                         'x-pcs-policy':json.dumps(p)})
        self.assertEqual(res.status_code,200,res.text[:300])
        self.assertEqual(res.json()['details']['relational_proof']['status'],'PROVED_CONDITIONALLY')
    def test_policy_malformed_rejected(self):
        cases=[{'enable_relational_certificate':True,'relational_coefficients':[]},
               {'enable_relational_certificate':'yes'},
               {'relational_upper_limit':'nan'},
               {'relational_coefficients':['1']*17}]
        for extra in cases:
            with self.assertRaises(IntakeError):parse_policy(extra)

if __name__=='__main__':unittest.main()
