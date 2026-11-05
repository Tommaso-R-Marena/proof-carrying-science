import json
import math
import struct
import random
import unittest
from studio.engine import analyze, IntakeError, parse_policy
from importlib.util import find_spec
from studio.verify_receipt import verify
from tests.make_samples import onnx_sample,safe_sample,pdb_line

class TestIntake(unittest.TestCase):
    def run_model(self,name,raw,policy=None): return analyze(name,raw,policy)
    def statuses(self, r):return {c['id']:c['status'] for c in r['checks']}
    def test_safetensors_real_binary(self):
        b=safe_sample();r=self.run_model('x.safetensors',b)
        self.assertEqual(r['metrics']['parameters'],4)
        self.assertEqual(self.statuses(r)['SAFETENSORS_OFFSETS'],'PASS')
        self.assertEqual(self.statuses(r)['NONFINITE_WEIGHTS'],'PASS')
        self.assertEqual(r['decision'],'OPEN')
        self.assertTrue(verify(r,b)[0])
        self.assertFalse(verify(r,b+b'altered')[0])
    def test_safetensors_nonfinite(self):
        r=self.run_model('x.safetensors',safe_sample((1.,float('nan'),3.,4.)))
        self.assertEqual(r['decision'],'FAIL')
        self.assertEqual(self.statuses(r)['NONFINITE_WEIGHTS'],'FAIL')
    def test_safetensors_duplicate_json_keys_rejected(self):
        h=b'{"x":{"dtype":"F32","shape":[],"data_offsets":[0,4]},"x":{"dtype":"F32","shape":[],"data_offsets":[0,4]}}'
        r=self.run_model('a.safetensors',struct.pack('<Q',len(h))+h+struct.pack('<f',1.))
        self.assertEqual(self.statuses(r)['PARSE_FAILURE'],'FAIL')
    def test_safetensors_hole_rejected(self):
        h=b'{"x":{"dtype":"F32","shape":[1],"data_offsets":[4,8]}}'
        r=self.run_model('x.safetensors',struct.pack('<Q',len(h))+h+b'abcdefgh')
        self.assertEqual(r['decision'],'FAIL')
    def test_onnx_real_wire(self):
        r=self.run_model('x.onnx',onnx_sample())
        self.assertEqual(r['metrics']['nodes'],1)
        self.assertEqual(r['metrics']['operators'],{'Identity':1})
        self.assertEqual(self.statuses(r)['ONNX_DATAFLOW'],'PASS')
        self.assertEqual(r['decision'],'OPEN')
    def test_onnx_unbound_input(self):
        r=self.run_model('x.onnx',onnx_sample(missing=True))
        self.assertEqual(self.statuses(r)['ONNX_DATAFLOW'],'FAIL')
    def test_onnx_custom_policy(self):
        r=self.run_model('x.onnx',onnx_sample(custom=True),{'forbid_custom_onnx_domains':True})
        self.assertEqual(self.statuses(r)['CUSTOM_DOMAINS'],'FAIL')
    def test_onnx_stochastic_policy(self):
        r=self.run_model('x.onnx',onnx_sample(stochastic=True),{'forbid_stochastic_onnx_ops':True})
        self.assertEqual(self.statuses(r)['STOCHASTIC_OPS'],'FAIL')
    def test_node_cap(self):
        r=self.run_model('x.onnx',onnx_sample(),{'max_onnx_nodes':0})
        self.assertEqual(self.statuses(r)['NODE_BUDGET'],'FAIL')
    def test_pdb_clean(self):
        s=pdb_line(1,'CA','A',1,0,0,0)+pdb_line(2,'CA','A',5,6,0,0)
        r=self.run_model('p.pdb',s.encode())
        self.assertEqual(r['metrics']['atoms'],2)
        self.assertEqual(self.statuses(r)['PDB_CLOSE_CONTACTS'],'PASS')
    def test_pdb_close_pair(self):
        s=pdb_line(1,'CA','A',1,0,0,0)+pdb_line(2,'CA','A',5,.1,.1,.1)
        r=self.run_model('p.pdb',s.encode())
        self.assertEqual(self.statuses(r)['PDB_CLOSE_CONTACTS'],'FAIL')
    def test_fasta(self):
        r=self.run_model('x.fasta',b'>name\nMELTING\n')
        self.assertEqual(r['metrics']['sequences'],1)
        self.assertEqual(self.statuses(r)['FASTA_FORMAT'],'PASS')
    def test_sbml_missing_reference(self):
        xml=b'<sbml level="3"><model><listOfSpecies><species id="a"/></listOfSpecies><listOfReactions><reaction><listOfReactants><speciesReference species="b"/></listOfReactants></reaction></listOfReactions></model></sbml>'
        r=self.run_model('x.sbml',xml)
        self.assertEqual(self.statuses(r)['SBML_REFERENCES'],'FAIL')
    def test_sbml_doctype_rejected(self):
        b=b'<!DOCTYPE sbml [<!ENTITY danger SYSTEM "file:///etc/passwd">]><sbml><model/></sbml>'
        r=self.run_model('x.sbml',b)
        self.assertEqual(self.statuses(r)['PARSE_FAILURE'],'FAIL')
    def test_pt_never_deserialized(self):
        r=self.run_model('unsafe.pt',b'not-safe-untrusted-pickle')
        self.assertEqual(self.statuses(r)['UNTRUSTED_CODE_FORMAT'],'FAIL')
    def test_receipt_tamper(self):
        b=safe_sample();r=self.run_model('x.safetensors',b)
        r['metrics']['tensors']=9000
        self.assertFalse(verify(r,b)[0])
    def test_policy_reject_unknown(self):
        with self.assertRaises(IntakeError):parse_policy({'IGNORE_ALL_CHECKS':True})
        with self.assertRaises(IntakeError):parse_policy({'max_onnx_nodes':True})
    def test_interval_identity_conditional(self):
        p={'check_output_bounds':True, 'input_min':-1, 'input_max':1,
           'output_min':-2, 'output_max':2}
        r=self.run_model('x.onnx',onnx_sample(),p)
        self.assertEqual(self.statuses(r)['ONNX_INTERVAL'],'PASS')
        self.assertEqual(r['details']['conditional_output_enclosure'],[-1,1])
        self.assertEqual(r['decision'],'OPEN')
        p['output_min']=2;p['output_max']=3
        r=self.run_model('x.onnx',onnx_sample(),p)
        self.assertEqual(self.statuses(r)['ONNX_INTERVAL'],'FAIL')
        p['output_min']=-.5;p['output_max']=.5
        r=self.run_model('x.onnx',onnx_sample(),p)
        self.assertEqual(self.statuses(r)['ONNX_INTERVAL'],'OPEN')
    def test_interval_policy_validation(self):
        with self.assertRaises(IntakeError):parse_policy({'input_min':2,'input_max':1})
        with self.assertRaises(IntakeError):parse_policy({'input_min':float('nan')})
    def test_sbml_valid_scoped(self):
        from pathlib import Path
        raw=(Path(__file__).resolve().parent.parent/'samples/demo_reaction.sbml').read_bytes()
        r=self.run_model('model.sbml',raw)
        self.assertEqual(self.statuses(r)['SBML_REFERENCES'],'PASS')
        self.assertEqual(r['decision'],'OPEN')
    def test_pcs_candidate_inventory_is_untrusted(self):
        r=self.run_model("x.onnx",onnx_sample())
        inv=r["pcs_claim_inventory"]
        self.assertFalse(inv["trusted_authority"])
        self.assertEqual(len(inv["claims"]),len(r["checks"]))
        self.assertIn("UNVERIFIED",[e["outcome"] for e in inv["evidence"]])
        self.assertTrue(verify(r,onnx_sample())[0])
    def test_api_raw_upload_and_origin_protection(self):
        from fastapi.testclient import TestClient
        from studio.server import app
        from urllib.parse import quote
        c=TestClient(app)
        headers={'X-PCS-Filename':quote('sample.onnx'), 'Content-Type':'application/octet-stream'}
        res=c.post('/api/analyze',content=onnx_sample(),headers=headers)
        self.assertEqual(res.status_code,200)
        self.assertEqual(res.json()['family'],'onnx')
        denied=c.post('/api/analyze',content=onnx_sample(),headers={**headers,'Origin':'https://malicious.example'})
        self.assertEqual(denied.status_code,403)
    @unittest.skipUnless(find_spec("safetensors"), "Optional safetensors library unavailable")
    def test_safetensors_against_reference_loader(self):
        from safetensors.numpy import load
        raw=safe_sample()
        values=load(raw)['example.weight']
        self.assertEqual(list(values),[0.,1.,-2.,3.5])

    def test_random_bytes_fail_closed(self):
        rng=random.Random(1212)
        for _ in range(80):
            raw=rng.randbytes(rng.randint(1,250))
            r=self.run_model('random.onnx',raw)
            self.assertIn(r['decision'],('OPEN','FAIL'))
            self.assertNotEqual(r['decision'],'PASS')

if __name__=='__main__':unittest.main()
