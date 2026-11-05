"""Adversarial regression and reproducibility tests for the new v0.3 features."""
import copy
from fractions import Fraction
import json
from pathlib import Path
import struct
import subprocess
import unittest
from unittest.mock import patch
from urllib.parse import quote

from fastapi.testclient import TestClient
from studio.engine import analyze, digest_json
from studio.exact_interval import compute, enclose
from studio.replay import replay_candidate, structural_eligibility
from studio.verify_receipt import verify, replay_verify
from tests.make_samples import fld, onnx_sample

ROOT=Path(__file__).resolve().parents[1]

def st(r,code):return next((x['status'] for x in r['checks'] if x['id']==code),None)

def model_with_attribute():
    node=fld(1,'features')+fld(2,'prediction')+fld(4,'Relu')+fld(5, fld(1,'surprise')+fld(2,1))
    dim=fld(1,1);type_proto=fld(1,fld(1,1)+fld(2,fld(1,dim)))
    vi=lambda name:fld(1,name)+fld(2,type_proto)
    graph=fld(1,node)+fld(2,'wattr')+fld(11,vi('features'))+fld(12,vi('prediction'))
    return fld(1,8)+fld(7,graph)+fld(8,fld(2,13))

def binary_model(op='Add', dtype=1):
    dim=fld(1,1)
    vtype=fld(1, fld(1,dtype)+fld(2,fld(1,dim)))
    vi=lambda name:fld(1,name)+fld(2,vtype)
    n=fld(1,'a')+fld(1,'b')+fld(2,'o')+fld(4,op)
    graph=fld(1,n)+fld(2,'binary')+fld(11,vi('a'))+fld(11,vi('b'))+fld(12,vi('o'))
    return fld(1,8)+fld(7,graph)+fld(8,fld(2,13))

NS='http://www.sbml.org/sbml/level3/version2/core'
FBC='http://www.sbml.org/sbml/level3/version1/fbc/version2'
def charge_model(zreact,zprod,missing=False):
    a=f' fbc:charge="{zreact}"' if not missing else ''
    b=f' fbc:charge="{zprod}"' if not missing else ''
    return (f'<sbml xmlns="{NS}" xmlns:fbc="{FBC}" level="3" version="2"><model id="charged">'
     f'<listOfSpecies><species id="X"{a}/><species id="Y"{b}/></listOfSpecies>'
     '<listOfReactions><reaction id="rx"><listOfReactants><speciesReference species="X"/></listOfReactants>'
     '<listOfProducts><speciesReference species="Y"/></listOfProducts></reaction></listOfReactions>'
     '</model></sbml>').encode()

class TestV03(unittest.TestCase):
    def test_reference_replay_on_real_serialized_relu(self):
        raw=onnx_sample(op='Relu')
        r=analyze('actual.onnx',raw,{'check_output_bounds':True,'enable_reference_replay':True,
                                   'output_min':0,'output_max':.5})
        self.assertEqual(st(r,'ONNX_F32_REPLAY'),'FAIL')
        self.assertEqual(r['decision'],'FAIL')
        self.assertEqual(r['details']['reference_replay']['runtime'],'numpy-float32-allowlisted')
        self.assertEqual(r['details']['reference_replay']['outputs']['prediction'],1.0)
        self.assertEqual(r['details']['reference_replay']['output_bits_hex']['prediction'],struct.pack('<f',1).hex())
        self.assertTrue(replay_verify(r,raw)[0])

    def test_reference_replay_identity_float32_bits(self):
        raw=onnx_sample()
        r=analyze('identity.onnx',raw,{'check_output_bounds':True,'enable_reference_replay':True,
                                     'output_min':-.5,'output_max':.5})
        self.assertEqual(st(r,'ONNX_F32_REPLAY'),'FAIL')
        self.assertEqual(r['details']['reference_replay']['outputs']['prediction'],-1.)

    def test_reference_replay_default_off(self):
        r=analyze('x.onnx',onnx_sample(),{'check_output_bounds':True,'output_max':0.2})
        self.assertIsNone(st(r,'ONNX_F32_REPLAY'))
        self.assertEqual(st(r,'ONNX_WITNESS'),'OPEN')

    def test_no_counterexample_no_replay_no_safe_claim(self):
        r=analyze('x.onnx',onnx_sample(op='Relu'),{'check_output_bounds':True,
                'enable_reference_replay':True,'output_min':0,'output_max':1})
        self.assertNotIn('candidate_counterexample',r['details'])
        self.assertEqual(st(r,'ONNX_F32_REPLAY'),'OPEN')
        self.assertEqual(r['decision'],'OPEN')

    def test_replay_rejects_node_attributes_and_search_abstains(self):
        r=analyze('x.onnx',model_with_attribute(),{'check_output_bounds':True,
                'enable_reference_replay':True,'output_min':0,'output_max':.5})
        self.assertEqual(r['metrics']['node_attributes'],1)
        self.assertEqual(st(r,'ONNX_WITNESS'),'OPEN')
        self.assertEqual(st(r,'ONNX_INTERVAL'),'OPEN')
        self.assertNotIn('reference_replay',r['details'])

    def test_float64_graph_not_mistaken_for_float32(self):
        r=analyze('x.onnx',binary_model(dtype=11),{'check_output_bounds':True,
                  'enable_reference_replay':True,'output_min':-.5,'output_max':.5})
        self.assertNotIn('reference_replay',r['details']) if 'candidate_counterexample' not in r['details'] else \
          self.assertEqual(r['details']['reference_replay']['status'],'INDETERMINATE')

    def test_binary_add_replay_works(self):
        r=analyze('b.onnx',binary_model('Add'),{'check_output_bounds':True,
                  'enable_reference_replay':True,'output_min':-.5,'output_max':.5})
        self.assertEqual(st(r,'ONNX_F32_REPLAY'),'FAIL')
        self.assertEqual(r['details']['reference_replay']['status'],'VIOLATION_REPRODUCED')
        self.assertTrue(replay_verify(r,binary_model('Add'))[0])

    def test_division_crossing_zero_abstains(self):
        r=analyze('b.onnx',binary_model('Div'),{'check_output_bounds':True,
                  'enable_reference_replay':True,'output_min':-.25,'output_max':.25})
        self.assertEqual(st(r,'ONNX_INTERVAL'),'OPEN')
        self.assertEqual(r['decision'],'OPEN') if 'reference_replay' not in r['details'] else \
          self.assertIn(r['decision'],('OPEN','FAIL'))

    def test_precise_rational_interval_bounds(self):
        p={'input_min':-.1,'input_max':.2,'output_min':-.2,'output_max':.4}
        result=enclose([(['x','x'],['y'],'Add','',0)],['x'],['y'],{},p)
        self.assertEqual(result['exact_fractions'],['-1/5','2/5'])
        self.assertEqual(result['conclusion'],'WITHIN')
        self.assertEqual(compute('Abs',[(Fraction(-3,5),Fraction(1,5))]),(Fraction(0),Fraction(3,5)))

    def test_rational_complexity_cap(self):
        huge=Fraction(2**600,1)
        from studio.exact_interval import compute
        with self.assertRaises(ArithmeticError):compute('Identity',[(huge,huge)])

    def test_division_interval_zero_guard(self):
        with self.assertRaises(ValueError):compute('Div',[(Fraction(1),Fraction(2)),(Fraction(-1),Fraction(1))])

    def test_charge_balance_positive(self):
        r=analyze('balanced.sbml',charge_model(1,1))
        self.assertEqual(st(r,'SBML_CHARGE_BALANCE'),'PASS')
        self.assertEqual(r['details']['charge_balance']['balanced_reactions'],1)

    def test_charge_balance_failure(self):
        r=analyze('wrong.sbml',charge_model(1,0))
        self.assertEqual(st(r,'SBML_CHARGE_BALANCE'),'FAIL')
        self.assertEqual(r['details']['charge_balance']['unbalanced_sample'][0]['signed_charge_imbalance'],'-1')
        self.assertEqual(r['decision'],'FAIL')

    def test_charge_missing_never_assumed_neutral(self):
        r=analyze('unknown.sbml',charge_model(1,1,missing=True))
        self.assertEqual(st(r,'SBML_CHARGE_BALANCE'),'OPEN')

    def test_charge_corrupt_annotation_fails_closed(self):
        r=analyze('unknown.sbml',charge_model('1e300',0))
        self.assertEqual(st(r,'SBML_CHARGE_BALANCE'),'OPEN')

    def test_disguised_pickle_and_zip_not_parsed_as_onnx(self):
        for payload in [b'PK\x03\x04not really an ONNX model',b'\x80\x04\x95\x00malicious',b'\x89HDF\r\n\x1a\ntrash']:
            for ext in ['onnx','safetensors']:
                with self.subTest(ext=ext,payload=payload[:4]):
                    r=analyze('notreal.'+ext,payload)
                    self.assertEqual(st(r,'UNTRUSTED_CODE_FORMAT'),'FAIL')

    def test_replay_receipt_tamper_changed_metrics_and_updated_hash(self):
        raw=onnx_sample()
        r=analyze('x.onnx',raw,{'check_output_bounds':True})
        forged=copy.deepcopy(r);forged['metrics']['nodes']=10**5
        forged['receipt_sha256']=digest_json({k:v for k,v in forged.items() if k!='receipt_sha256'})
        self.assertTrue(verify(forged,raw)[0])  # hashes alone are NOT authentication
        self.assertFalse(replay_verify(forged,raw)[0])
        self.assertTrue(replay_verify(r,raw)[0])

    def test_embedded_policy_tamper_rejected_even_if_receipt_rehashed(self):
        raw=onnx_sample()
        r=analyze('x.onnx',raw,{'check_output_bounds':True})
        r['policy']['input_max']=99
        r['receipt_sha256']=digest_json({k:v for k,v in r.items() if k!='receipt_sha256'})
        self.assertFalse(verify(r,raw)[0])

    def test_legacy_receipt_still_verifiable_but_not_replayable(self):
        path=ROOT/'validation/relu_violation_receipt.json'
        r=json.loads(path.read_text())
        raw=(ROOT/'samples/demo_relu_violation.onnx').read_bytes()
        self.assertTrue(verify(r,raw)[0])
        self.assertFalse(replay_verify(r,raw)[0])

    def test_worker_failure_open_not_pass(self):
        from studio.replay import replay_candidate
        with patch('studio.replay.subprocess.run',side_effect=subprocess.TimeoutExpired(['python'],3)):
            r=replay_candidate([(['x'],['y'],'Identity','',0)],['x'],['y'],
                  {'x':1,'y':1},{'x':(1,),'y':(1,)},0,0,
                  {'inputs':{'x':-1}}, {'output_min':-.5,'output_max':.5})
        self.assertEqual(r['status'],'INDETERMINATE')

    def test_api_reference_replay(self):
        from studio.server import app
        client=TestClient(app)
        p={'check_output_bounds':True,'enable_reference_replay':True,'output_min':0,'output_max':.5}
        response=client.post('/api/analyze',content=onnx_sample(op='Relu'),headers={
            'x-pcs-filename':quote('test.onnx'),'x-pcs-policy':quote(json.dumps(p))})
        self.assertEqual(response.status_code,200)
        self.assertEqual(st(response.json(),'ONNX_F32_REPLAY'),'FAIL')
        self.assertTrue(replay_verify(response.json(),onnx_sample(op='Relu'))[0])

    def test_unsafe_policy_toggle_rejected(self):
        from studio.engine import parse_policy, IntakeError
        with self.assertRaises(IntakeError):parse_policy({'enable_reference_replay':'yes'})

if __name__=='__main__':unittest.main()
