"""Soundness regression and adversarial evidence checks for affine binary32 route.

All claims remain conditional on the screened ONNX + RN-even software-value
contract, and the independently trusted policy hash is test-fixture only.
"""
from __future__ import annotations
import copy
import hashlib
import json
import random
import struct
import unittest
from fractions import Fraction
from pathlib import Path
from unittest.mock import patch
from studio.affine_fp32_v13 import (POLICY_SCHEMA,propose,verify,_derive,_q)
from studio.affine_envelope_v13 import AffineEnvelopeGate,review
from studio.fp32_assurance import intervals,relation_upper,sequential_eval
from studio.dense_nn import screen_onnx
from studio.ieee754 import float_to_bits,from_bits
from studio.relational_kernel import canonical

ROOT=Path(__file__).resolve().parents[1]
def file(x):return (ROOT/x).read_bytes()
def record(x):return json.loads((ROOT/'validation'/x).read_text())


def correlated_policy(model):
    return {'schema':POLICY_SCHEMA,'model_sha256':hashlib.sha256(model).hexdigest(),
            'input_box':[['-1000','1000']]*2,'output_coefficients':['1','-1'],'upper_limit':'-1/2'}

class CorrelatedFP32V13(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old=file('samples/demo_trained_iris_mlp.onnx')
        cls.new=file('samples/demo_trained_iris_updated.onnx')
        cls.model=file('samples/demo_correlated_fp32_margin_v13.onnx')
        cls.policy=record('v09_demo_envelope_reviewer_policy.json')
        cls.real=record('v09_demo_envelope_evidence.json')
        cls.bundle=record('v13_affine_iris_candidate.json')
        cls.trusted=hashlib.sha256(canonical(cls.policy)).hexdigest()
        cls.cp=correlated_policy(cls.model)
        cls.csha=hashlib.sha256(canonical(cls.cp)).hexdigest()
        cls.cc=record('v13_correlated_margin_candidate.json')

    def test_actual_capability_beyond_plain_intervals(self):
        spec=screen_onnx(self.model)
        ibp=relation_upper(intervals(spec,[(Fraction(-1000),Fraction(1000))]*2),[Fraction(1),Fraction(-1)])
        self.assertEqual(ibp,1999)
        review_result=verify(self.model,self.cp,self.cc,self.csha)
        self.assertEqual(review_result['status'],'PROVED_CONDITIONALLY',review_result)
        self.assertLess(Fraction(review_result['proven_upper_bound']),Fraction(-1,2))
        self.assertEqual(review_result['onnxruntime_equivalence'],'NOT_ESTABLISHED')
        self.assertEqual(review_result['lean_kernel_verification'],'NOT_ESTABLISHED')

    def test_all_six_trained_iris_margin_certificates(self):
        gate=AffineEnvelopeGate(self.old,self.new,self.real,self.bundle,self.policy,self.trusted)
        report=gate.review()
        self.assertEqual(report['status'],'PROVED_CONDITIONALLY',report)
        self.assertEqual(report['affine_class_comparisons'],6)
        for item,words in record('v09_demo_input_words.json').items():
            with self.subTest(sample=item):
                decision=gate.admit(words)
                self.assertEqual(decision['status'],'ADMIT_CONDITIONALLY',decision)
                execution=gate.reference_infer(words)
                self.assertEqual(execution['status'],'EXECUTED_CONDITIONALLY',execution)
        self.assertEqual(gate.reference_infer(['00000000']*4)['status'],'ABSTAIN')

    def test_certificate_modifications_fail_closed(self):
        for change in ['understated','changed_model','changed_policy','unknown_key','missing']:
            with self.subTest(change=change):
                p=copy.deepcopy(self.cp);c=copy.deepcopy(self.cc);sha=self.csha;m=self.model
                if change=='understated':c['upper_bound']='-100000'
                elif change=='changed_model':m=m+b'\x00'
                elif change=='changed_policy':p['upper_limit']='0'
                elif change=='unknown_key':c['forged_authority']='Lean verified'
                else:c.pop('upper_bound')
                self.assertEqual(verify(m,p,c,sha)['status'],'OPEN')

    def test_entire_affine_bundle_required_and_reviewer_controls_it(self):
        for kind in ('dropped_region','dropped_competitor','wrong_index','wrong_source','fake_upper','wrong_trust','bad_policy','unknown_field'):
            with self.subTest(kind=kind):
                bundle=copy.deepcopy(self.bundle)
                policy=copy.deepcopy(self.policy)
                new=self.new;trusted=self.trusted
                if kind=='dropped_region':bundle['entries'].pop()
                elif kind=='dropped_competitor':bundle['entries'][0]['comparisons'].pop()
                elif kind=='wrong_index':bundle['entries'][1]['comparisons'][0]['other_class_index']=2
                elif kind=='wrong_source':new=self.new+b'\x00'
                elif kind=='fake_upper':bundle['entries'][2]['comparisons'][0]['certificate']['upper_bound']='-100000'
                elif kind=='wrong_trust':trusted='0'*64
                elif kind=='bad_policy':policy['regions'][0]['minimum_margin']='100'
                elif kind=='unknown_field':bundle['attestation']='certified by kernel'
                r=review(self.old,new,self.real,bundle,policy,trusted)
                self.assertEqual(r['status'],'OPEN',r)

    def test_denied_when_independent_decoder_unavailable(self):
        with patch('studio.affine_envelope_v13.crosscheck',return_value={'status':'NOT_RUN'}):
            gate=AffineEnvelopeGate(self.old,self.new,self.real,self.bundle,self.policy,self.trusted)
            self.assertEqual(gate.review()['status'],'OPEN')
            self.assertEqual(gate.reference_infer(record('v09_demo_input_words.json')['22'])['status'],'ABSTAIN')

    def test_denied_when_existing_real_update_proof_missing(self):
        bundle=copy.deepcopy(self.real)
        bundle['entries'][0]['comparisons'][0].pop('baseline_certificate')
        r=review(self.old,self.new,bundle,self.bundle,self.policy,self.trusted)
        self.assertEqual(r['status'],'OPEN',r)

    def test_caller_mutation_after_gate_creation_does_not_change_admission(self):
        policy=copy.deepcopy(self.policy);bundle=copy.deepcopy(self.bundle)
        gate=AffineEnvelopeGate(self.old,self.new,self.real,bundle,policy,self.trusted)
        self.assertEqual(gate.review()['status'],'PROVED_CONDITIONALLY')
        bundle['entries'].clear();policy['regions'].clear()
        self.assertEqual(gate.reference_infer(record('v09_demo_input_words.json')['22'])['status'],'EXECUTED_CONDITIONALLY')

    def test_mathematical_affine_enclosures_contain_actual_sequential_fp32(self):
        rng=random.Random(0xA1F1E)
        for name,lo,hi,count in [('demo_correlated_fp32_margin_v13.onnx',-1000,1000,180),
                                 ('demo_trained_iris_updated.onnx',-2,2,120),
                                 ('demo_activation_identity.onnx',-1,1,100)]:
            with self.subTest(model=name):
                model=file('samples/'+name)
                spec=screen_onnx(model)
                forms,engine=_derive(spec,[(Fraction(lo),Fraction(hi))]*spec['input_width'])
                enclosures=[f.bound() for f in forms]
                self.assertLessEqual(engine.symbols,800)
                for iteration in range(count):
                    vals=[]
                    for k in range(spec['input_width']):
                        w=float_to_bits(float(rng.uniform(lo,hi)))
                        q=from_bits(w)
                        if not Fraction(lo)<=q<=Fraction(hi):q=Fraction(0)
                        vals.append(q)
                    actual=sequential_eval(spec,vals)
                    for y,(a,b) in zip(actual,enclosures):
                        self.assertLessEqual(a,y)
                        self.assertLessEqual(y,b)

    def test_proposer_never_grants_independent_policy_authority(self):
        r=propose(self.model,self.cp)
        self.assertEqual(r['status'],'CANDIDATE_REPLAYED')
        self.assertIn('NOT independently',r['warning'])
        self.assertEqual(verify(self.model,self.cp,r['certificate'],'a'*64)['status'],'OPEN')

    def test_oversized_or_infeasible_input_returns_open(self):
        for changed in ['1e100000000','9999999999999999999999999999999999999999999999999', '1/0']:
            with self.subTest(text=changed):
                p=copy.deepcopy(self.cp)
                p['input_box'][0][1]=changed
                self.assertEqual(propose(self.model,p)['status'],'OPEN')
                self.assertEqual(verify(self.model,p,self.cc,hashlib.sha256(canonical(p)).hexdigest())['status'],'OPEN')

if __name__=='__main__':unittest.main()
