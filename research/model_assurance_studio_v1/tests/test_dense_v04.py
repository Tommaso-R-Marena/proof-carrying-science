"""Independent numeric and adversarial regression checks of dense ONNX subset."""
import copy
import json
import math
from pathlib import Path
import random
import struct
import subprocess
import sys
import unittest
from fractions import Fraction
from urllib.parse import quote

from fastapi.testclient import TestClient
from studio.dense_nn import screen_onnx,check_dense,Unsupported,_execute_intervals
from studio.engine import analyze,parse_policy,digest_json
from studio.verify_receipt import replay_verify, verify
from studio.server import app
from tests.make_samples import fld

ROOT=Path(__file__).resolve().parents[1]

def dense_sample(weights=(1.,0.,0.,1.), bias=(.25,-.25),input_dim=2, use_gemm=False, op='Relu', external=False,custom=False, weight_dtype=1):
    def vi(name,shape):
        dims=b''.join(fld(1, fld(1,d)) for d in shape)
        return fld(1,name)+fld(2,fld(1, fld(1,1)+fld(2,dims)))
    def tensor(name, shape, values):
        return (b''.join(fld(1,d) for d in shape)+fld(2,weight_dtype)+fld(8,name)+
                fld(9,b''.join(struct.pack('<f',v) for v in values))+(fld(14,1) if external else b''))
    layer=fld(1,'features')+fld(1,'W')+fld(2,'h')+fld(4,'MatMul' if not use_gemm else 'Gemm')
    if use_gemm:layer=fld(1,'features')+fld(1,'W')+fld(1,'b')+fld(2,'h')+fld(4,'Gemm')
    if custom:layer+=fld(7,'some.custom')
    badd=fld(1,'h')+fld(1,'b')+fld(2,'pre')+fld(4,'Add')
    act=fld(1,'pre' if not use_gemm else 'h')+fld(2,'prediction')+fld(4,op)
    graph=(fld(1,layer)+(b'' if use_gemm else fld(1,badd))+fld(1,act)+fld(2,'dense')+
           fld(5,tensor('W',[input_dim,2],weights))+fld(5,tensor('b',[2],bias))+
           fld(11,vi('features',[1,input_dim]))+fld(12,vi('prediction',[1,2])))
    return fld(1,8)+fld(7,graph)+fld(8,fld(2,13))

class DenseTests(unittest.TestCase):
    def setUp(self):
        self.data=dense_sample()
        self.p={'check_output_bounds':True,'search_scalar_witness':True,
                'enable_reference_replay':True,'input_min':-1,'input_max':1,
                'output_min':0,'output_max':1}
    def status(self,report,key):return next((c['status'] for c in report['checks'] if c['id']==key),None)
    def test_real_dense_network_violation(self):
        r=analyze('mlp.onnx',self.data,self.p)
        self.assertEqual(self.status(r,'ONNX_DENSE_F32_REPLAY'),'FAIL')
        self.assertEqual(self.status(r,'ONNX_DENSE_WITNESS'),'OPEN')
        self.assertEqual(r['decision'],'FAIL')
        self.assertEqual(r['details']['dense_replay']['runtime'],'numpy-float32-dense-reference')
        self.assertTrue(r['details']['dense_replay']['violating_indices'])
        self.assertTrue(replay_verify(r,self.data)[0])
    def test_conditional_pass_exact_enclosure(self):
        p=self.p|{'output_min':0,'output_max':1.25}
        r=analyze('mlp.onnx',self.data,p)
        self.assertEqual(self.status(r,'ONNX_DENSE_REAL_BOX'),'PASS')
        self.assertEqual(self.status(r,'ONNX_DENSE_F32_REPLAY'),'OPEN')
        self.assertEqual(r['decision'],'OPEN') # never SAFE
        self.assertTrue(replay_verify(r,self.data)[0])
    def test_gemm_supported_with_default_attributes(self):
        r=analyze('model.onnx',dense_sample(use_gemm=True),self.p)
        self.assertEqual(self.status(r,'ONNX_DENSE_F32_REPLAY'),'FAIL')
    def test_unsupported_abstains_instead_of_passes(self):
        bads=[dense_sample(op='Sigmoid'),dense_sample(custom=True),dense_sample(external=True),
              dense_sample(weight_dtype=11),dense_sample(weights=(float('nan'),0,0,1)),dense_sample(weights=(float('inf'),0,0,1))]
        for i,b in enumerate(bads):
            with self.subTest(i=i):
                r=analyze('x.onnx',b,self.p)
                self.assertEqual(self.status(r,'ONNX_DENSE_REAL_BOX'),'OPEN')
                self.assertNotIn('dense_replay',r['details'])
    def test_candidate_is_bound_to_exact_model_and_policy(self):
        r=analyze('model.onnx',self.data,self.p)
        w=r['details']['dense_counterexample']
        self.assertEqual(w['artifact_sha256'],r['sha256'])
        self.assertEqual(w['policy_sha256'],r['policy_sha256'])
    def test_weight_tampering_breaks_receipt(self):
        r=analyze('x.onnx',self.data,self.p)
        modified=self.data.replace(struct.pack('<f',.25),struct.pack('<f',.75))
        self.assertFalse(verify(r,modified)[0])
    def test_forged_unsigned_receipt_detected_by_replay(self):
        r=analyze('x.onnx',self.data,self.p)
        fake=copy.deepcopy(r)
        fake['details']['dense_replay']['outputs']=[0.,0.]
        fake['receipt_sha256']=digest_json({k:v for k,v in fake.items() if k!='receipt_sha256'})
        self.assertTrue(verify(fake,self.data)[0])
        self.assertFalse(replay_verify(fake,self.data)[0])
    def test_deterministic(self):
        a=analyze('x.onnx',self.data,self.p)
        b=analyze('x.onnx',self.data,self.p)
        self.assertEqual(digest_json(a),digest_json(b))
    def test_api_end_to_end(self):
        res=TestClient(app).post('/api/analyze',content=self.data,headers={'x-pcs-filename':quote('mlp.onnx'),'x-pcs-policy':quote(json.dumps(self.p))})
        self.assertEqual(res.status_code,200)
        self.assertEqual(self.status(res.json(),'ONNX_DENSE_F32_REPLAY'),'FAIL')
    def test_random_exact_enclosures_are_sound_over_dense_probe_points(self):
        # 30 independent real-number matrices checked against exact point evaluation.
        rng=random.Random(44)
        for _ in range(30):
            w=tuple(rng.choice([-2,-1,-.5,0,.5,1,2]) for i in range(4))
            b=tuple(rng.choice([-1,0,1]) for i in range(2))
            raw=dense_sample(weights=w,bias=b)
            spec=screen_onnx(raw)
            box=_execute_intervals(spec,[(Fraction(-1),Fraction(1))]*2)
            for x in [-1,0,1]:
                for y in [-1,0,1]:
                    exact=_execute_intervals(spec,[(Fraction(x),Fraction(x)),(Fraction(y),Fraction(y))])
                    for (a,c),(lo,hi) in zip(exact,box):
                        self.assertEqual(a,c)
                        self.assertLessEqual(lo,a)
                        self.assertLessEqual(a,hi)
    def test_output_not_risk_free_when_target_wide(self):
        r=analyze('ok.onnx',self.data,self.p|{'output_min':-100,'output_max':100})
        self.assertEqual(r['decision'],'OPEN')
        self.assertEqual(self.status(r,'ONNX_BEHAVIOR'),'OPEN')

if __name__=='__main__':unittest.main()

class DenseHardeningTests(unittest.TestCase):
    def test_float32_candidate_never_exceeds_real_input_box(self):
        from studio.dense_nn import candidate_inputs,Unsupported
        spec={'input_width':2}
        pol={'input_min':0.100000001,'input_max':0.10000001}
        for values in candidate_inputs(spec,pol):
            self.assertTrue(all(pol['input_min']<=x<=pol['input_max'] for x in values))

    def test_input_box_without_f32_member_abstains(self):
        from studio.dense_nn import candidate_inputs,Unsupported
        with self.assertRaises(Unsupported):list(candidate_inputs({'input_width':2},{'input_min':.1,'input_max':.1}))

    def test_subprocess_worker_failure_is_open(self):
        from studio.dense_nn import _replay, screen_onnx
        from unittest.mock import patch
        spec=screen_onnx(dense_sample())
        witness={'inputs':{'features':[1.,1.]}}
        with patch('studio.dense_nn.subprocess.run',side_effect=subprocess.TimeoutExpired('cmd',7)):
            out=_replay(spec,witness,(Fraction(0),Fraction(1)))
        self.assertEqual(out['status'],'INDETERMINATE')

    def test_protobuf_random_fuzz_no_unexpected_unhandled_crash(self):
        rng=random.Random(45)
        data=dense_sample()
        for _ in range(80):
            a=bytearray(data)
            for _ in range(rng.randrange(1,5)):
                i=rng.randrange(len(a));a[i]=rng.randrange(256)
            # Some mutations remain technically valid. No malformed input
            # may trigger a process crash or an out-of-bounds trusted claim.
            r=analyze('fuzz.onnx',bytes(a),{'check_output_bounds':True})
            self.assertIn(r['decision'],('OPEN','FAIL'))
            if r['decision']=='OPEN':
                self.assertTrue(any(c['status']=='OPEN' for c in r['checks']))

    def test_optional_independent_pytorch_numerical_crosscheck(self):
        import importlib.util
        if importlib.util.find_spec('torch') is None:self.skipTest('Torch unavailable')
        import numpy as np
        import torch
        rng=random.Random(47)
        for i in range(24):
            weights=tuple(rng.choice([-1.,-.25,0.,.5,1.]) for _ in range(4))
            bias=tuple(rng.choice([-1.,0.,.25]) for _ in range(2))
            raw=dense_sample(weights=weights,bias=bias)
            spec=screen_onnx(raw)
            x=[rng.choice([-1.,-.5,0.,.5,1.]) for _ in range(2)]
            from studio.dense_worker import execute
            run=execute({'schema':spec['schema'],'nodes':spec['nodes'],'weights':spec['weights'],
                         'input':spec['input'],'input_width':2,'output':spec['output'],'output_width':2,
                         'values':x,'target':[-100,100]})
            t=torch.tensor(x,dtype=torch.float32).reshape(1,2)
            w=torch.tensor(weights,dtype=torch.float32).reshape(2,2)
            b=torch.tensor(bias,dtype=torch.float32)
            expected=torch.relu(t@w+b).flatten().tolist()
            self.assertTrue(np.allclose(run['outputs'],expected,rtol=1e-6,atol=1e-6))
