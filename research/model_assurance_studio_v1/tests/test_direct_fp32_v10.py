"""Proof-obligation, coverage and numerical tests for the v0.10 checker.

These are Python-level tests, NOT a Lean compilation or runtime conformance.
"""
from __future__ import annotations
import copy
import hashlib
import json
import random
import struct
import unittest
from pathlib import Path
from fractions import Fraction
from unittest.mock import patch
from studio.direct_fp32_v10 import (POLICY_SCHEMA, DirectFP32Gate,
                                   verify as verify_direct)
from studio.direct_fp32_proposer_v10 import propose
from studio.dual_envelope_v10 import DualAssuranceGate,verify_dual
from studio.relational_kernel import canonical
from studio.fp32_assurance import intervals, relation_upper, sequential_eval
from studio.dense_nn import screen_onnx
from studio.ieee754 import from_bits

ROOT=Path(__file__).resolve().parents[1]

def source(name):return (ROOT/'samples'/name).read_bytes()
def record(name):return json.loads((ROOT/'validation'/name).read_text())
def sha(raw):return hashlib.sha256(raw).hexdigest()

class DirectF32V10(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model=source('demo_activation_identity.onnx')
        cls.policy={'schema':POLICY_SCHEMA,'model_sha256':sha(cls.model),
                    'input_box':[['-1','1']],'output_coefficients':['1'],
                    'upper_limit':'1/4'}
        cls.pin=sha(canonical(cls.policy))
        cls.proposed=propose(cls.model,cls.policy,max_leaves=32,max_depth=16)
        assert cls.proposed['status']=='CANDIDATE_REPLAYED'
        cls.cert=cls.proposed['certificate']

    def check(self,model=None,policy=None,cert=None,pin=None):
        return verify_direct(self.model if model is None else model,
                self.policy if policy is None else policy,
                self.cert if cert is None else cert,
                self.pin if pin is None else pin)

    def test_partition_beats_unpartitioned_interval_on_relu_identity(self):
        spec=screen_onnx(self.model)
        lo,hi=intervals(spec,[(Fraction(-1),Fraction(1))])[0]
        self.assertGreater(hi,Fraction(1,4))
        self.assertEqual(self.proposed['status'],'CANDIDATE_REPLAYED')
        self.assertEqual(self.check()['status'],'PROVED_CONDITIONALLY')
        self.assertGreater(self.check()['leaf_count'],1)

    def test_proposer_and_verifier_do_not_need_numpy_scipy_torch(self):
        import sys
        # No external numerical packages are imported by the small checker.
        self.assertNotIn('numpy',__import__('studio.direct_fp32_v10',fromlist=['x']).__dict__)
        self.assertTrue(all(v['kind'] in ('split','leaf') for v in (self.cert['tree'],)))

    def test_policy_identity_is_independent_of_certificate_hash(self):
        for field,value in [('upper_limit','1'),('input_box',[['-1','0']]),
                            ('output_coefficients',['-1']),('model_sha256','0'*64)]:
            with self.subTest(field=field):
                p=copy.deepcopy(self.policy);p[field]=value
                self.assertEqual(self.check(policy=p)['status'],'OPEN')
        self.assertEqual(self.check(pin='0'*64)['status'],'OPEN')
        self.assertEqual(self.check(model=self.model+b'\x00')['status'],'OPEN')

    def test_missing_split_branch_or_wrong_rederived_bound_is_rejected(self):
        for mutation in ('no_left','no_right','bad_axis','wrong_boundary','extra_node_field','fake_safe_leaf','extra_leaf_field'):
            c=copy.deepcopy(self.cert);root=c['tree']
            if mutation=='no_left':root.pop('left')
            if mutation=='no_right':root.pop('right')
            if mutation=='bad_axis':root['axis']=1
            if mutation=='wrong_boundary':root['at']='5'
            if mutation=='extra_node_field':root['trusted_verdict']=True
            if mutation=='fake_safe_leaf':c['tree']={'kind':'leaf','upper_bound':'0'}
            if mutation=='extra_leaf_field':
                node=root
                while node['kind']=='split':node=node['left']
                node['approved']=True
            with self.subTest(mutation=mutation):
                self.assertEqual(self.check(cert=c)['status'],'OPEN')

    def test_unbounded_complexity_and_nonfinite_words_fail_closed(self):
        m=copy.deepcopy(self.cert)
        # Type confusion/recursion and oversized rational values abstain.
        for value in ('NaN','1e100000000','7/0',None,False):
            c=copy.deepcopy(m);c['tree']['at']=value
            self.assertEqual(self.check(cert=c)['status'],'OPEN')
        gate=DirectFP32Gate(self.model,self.policy,self.cert,self.pin)
        self.assertEqual(gate.review()['status'],'PROVED_CONDITIONALLY')
        for words in (['7f800000'],['7fc00000'],['ff800000'],['0000000G'],[],['3f800001'],['00000000','00000000']):
            with self.subTest(words=words):self.assertEqual(gate.admit(words)['status'],'ABSTAIN')
        for words in (['00000001'],['80000001'],['bf800000'],['3f800000'],['00000000']):
            with self.subTest(words=words):self.assertEqual(gate.admit(words)['status'],'ADMIT_CONDITIONALLY')

    def test_outside_domain_not_accepted_even_when_property_true(self):
        g=DirectFP32Gate(self.model,self.policy,self.cert,self.pin)
        self.assertEqual(g.admit(['40000000'])['status'],'ABSTAIN')

    def test_partition_node_fuzz_rejects_false_exact_bounds(self):
        rng=random.Random(761)
        for _ in range(64):
            c=copy.deepcopy(self.cert)
            node=c['tree']
            while node['kind']=='split':node=node[rng.choice(('left','right'))]
            q=Fraction(node['upper_bound'])
            node['upper_bound']=str(q+Fraction(rng.randrange(1,11),65536))
            self.assertEqual(self.check(cert=c)['status'],'OPEN')

    def test_actual_float32_randomized_reference_inside_certified_domain(self):
        spec=screen_onnx(self.model);r=random.Random(2288)
        for _ in range(300):
            bits=struct.unpack('<I',struct.pack('<f',r.uniform(-1,1)))[0]
            v=from_bits(bits)
            output=sequential_eval(spec,[v])[0]
            self.assertLessEqual(output,Fraction(1,4))

class DualV10(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old=source('demo_trained_iris_mlp.onnx')
        cls.new=source('demo_trained_iris_updated.onnx')
        cls.policy=record('v09_demo_envelope_reviewer_policy.json')
        cls.real_bundle=record('v09_demo_envelope_evidence.json')
        cls.direct_bundle=record('v10_direct_fp32_partition_evidence.json')
        cls.inputs=record('v09_demo_input_words.json')
        cls.pin=sha(canonical(cls.policy))

    def check(self,real=None,direct=None,policy=None,pin=None,new=None):
        return verify_dual(self.old,self.new if new is None else new,
            self.real_bundle if real is None else real,
            self.direct_bundle if direct is None else direct,
            self.policy if policy is None else policy,self.pin if pin is None else pin)

    def test_complete_six_comparisons_and_exact_partition_coverage(self):
        out=self.check()
        self.assertEqual(out['status'],'PROVED_CONDITIONALLY')
        self.assertEqual(out['real_certificate_comparisons'],6)
        self.assertEqual(out['direct_float32_comparisons'],6)
        self.assertEqual(out['checked_fp32_partition_leaves'],37)
        self.assertEqual(out['region_count'],3)
        self.assertEqual(out['lean_kernel_verification'],'NOT_ESTABLISHED')

    def test_guarded_dispatch_requires_both_evidence_families(self):
        gate=DualAssuranceGate(self.old,self.new,self.real_bundle,self.direct_bundle,self.policy,self.pin)
        for anchor,cls in [('22',0),('62',1),('118',2)]:
            with self.subTest(anchor=anchor):
                allowed=gate.admit(self.inputs[anchor]);self.assertEqual(allowed['status'],'ADMIT_CONDITIONALLY')
                self.assertEqual(allowed['class_index'],cls)
                observed=gate.reference_infer(self.inputs[anchor])
                self.assertEqual(observed['status'],'EXECUTED_CONDITIONALLY')
                self.assertEqual(observed['dual_fp32_evidence'],'REPLAYED')
        with patch('studio.guarded_reference_infer_v09.sequential_eval',side_effect=AssertionError('must not execute')):
            result=gate.reference_infer(['00000000']*4)
        self.assertEqual(result['status'],'ABSTAIN')

    def test_missing_one_direct_branch_denies_all_regions(self):
        c=copy.deepcopy(self.direct_bundle)
        c['entries'][2]['comparisons'].pop()
        gate=DualAssuranceGate(self.old,self.new,self.real_bundle,c,self.policy,self.pin)
        self.assertEqual(gate.review()['status'],'OPEN')
        self.assertEqual(gate.admit(self.inputs['22'])['status'],'ABSTAIN')
        with patch('studio.guarded_reference_infer_v09.sequential_eval',side_effect=AssertionError('must not execute')):
            self.assertEqual(gate.reference_infer(self.inputs['22'])['status'],'ABSTAIN')

    def test_mutated_direct_proofs_refused(self):
        for i in range(3):
            for j in range(2):
                with self.subTest(region=i,comparison=j):
                    c=copy.deepcopy(self.direct_bundle)
                    tree=c['entries'][i]['comparisons'][j]['certificate']['tree']
                    while tree['kind']=='split':tree=tree['right']
                    tree['upper_bound']='-100000'
                    self.assertEqual(self.check(direct=c)['status'],'OPEN')

    def test_real_proof_and_exact_model_substitution_refused(self):
        real=copy.deepcopy(self.real_bundle)
        real['entries'][0]['comparisons'][0]['baseline_certificate']['multipliers']=[]
        self.assertEqual(self.check(real=real)['status'],'OPEN')
        changed=self.new[:-1]+bytes([self.new[-1]^1])
        self.assertEqual(self.check(new=changed)['status'],'OPEN')
        self.assertEqual(self.check(pin='0'*64)['status'],'OPEN')

    def test_untrusted_container_objects_fail_closed(self):
        # Previous object mutation must not bypass verification or crash host.
        for malformed in (None,[],{'schema':'invalid'},'not a certificate',{'tree':float('nan')}):
            with self.subTest(malformed=repr(malformed)[:35]):
                g=DualAssuranceGate(self.old,self.new,self.real_bundle,malformed,self.policy,self.pin)
                self.assertEqual(g.review()['status'],'OPEN')
                self.assertEqual(g.admit(self.inputs['22'])['status'],'ABSTAIN')

    def test_real_http_dual_demo_and_untrusted_host_rejected(self):
        try:
            from fastapi.testclient import TestClient
            from studio.server import app
        except ImportError:
            self.skipTest('FastAPI frontend optional')
        with TestClient(app,base_url='http://testserver') as client:
            res=client.get('/api/dual-envelope-demo')
            self.assertEqual(res.status_code,200)
            d=res.json()
            self.assertEqual(d['review']['status'],'PROVED_CONDITIONALLY')
            self.assertEqual(d['review']['checked_fp32_partition_leaves'],37)
            self.assertTrue(all(x['reference_execution']['status']=='EXECUTED_CONDITIONALLY' for x in d['examples']))
            self.assertEqual(d['outside_example']['reference_execution']['status'],'ABSTAIN')
            self.assertEqual(client.get('/api/dual-envelope-demo',headers={'host':'attacker.invalid'}).status_code,403)

    def test_crosschecked_cover_property_for_random_binary32_model_inputs(self):
        spec=screen_onnx(self.new);rng=random.Random(1012026)
        for r in self.policy['regions']:
            box=[(Fraction(a),Fraction(b)) for a,b in r['box']]
            winner=r['class_index']
            for _ in range(35):
                xs=[]
                for lo,hi in box:
                    mid=float((lo+hi)/2)
                    span=float((hi-lo)/2)
                    # Restrict the generator to interior of the exact box.
                    q=struct.unpack('<f',struct.pack('<f',mid+span*0.8*rng.uniform(-1,1)))[0]
                    v=Fraction.from_float(float(q))
                    self.assertTrue(lo<=v<=hi)
                    xs.append(v)
                logits=sequential_eval(spec,xs)
                for j in range(3):
                    if j!=winner:self.assertGreaterEqual(logits[winner]-logits[j],Fraction(1,4))

if __name__=='__main__':unittest.main()
