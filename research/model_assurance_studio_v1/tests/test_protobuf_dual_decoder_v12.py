"""Independent protobuf semantic matching and fail-closed gate regressions.

A protobuf decoder is NOT an official ONNX validator, Lean kernel, or executor.
"""
from __future__ import annotations
import copy
import hashlib
import json
import subprocess
import random
from studio.engine import wire_fields
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from tests.make_samples import fld
from tests.test_strict_onnx_v11 import dense_sample, replace_graph, mutate_graph
from studio.protobuf_dual_decoder_v12 import crosscheck, DualDecoderAssuranceGate
from studio.dense_nn import screen_onnx, Unsupported
from studio.relational_kernel import canonical

ROOT=Path(__file__).resolve().parents[1]
SAMPLES=ROOT/'samples'
VALID=['demo_dense_neural_violation.onnx','demo_trained_iris_mlp.onnx',
       'demo_trained_iris_updated.onnx','demo_activation_identity.onnx',
       'demo_relational_margin.onnx','demo_hidden_spike.onnx',
       'demo_partition_abs.onnx']


def record(name):return json.loads((ROOT/'validation'/name).read_text())


class DualDecoderV12(unittest.TestCase):
    def test_valid_screened_onnx_models_agree(self):
        for name in VALID:
            with self.subTest(name=name):
                raw=(SAMPLES/name).read_bytes()
                result=crosscheck(raw)
                self.assertEqual(result['status'],'AGREE',result)
                self.assertEqual(result['model_sha256'],hashlib.sha256(raw).hexdigest())
                self.assertEqual(len(result['semantic_digest_sha256']),64)
                self.assertEqual(result['official_onnx_checker'],'NOT_RUN')

    def test_float_data_packed_and_negative_zero_round_trip(self):
        base=dense_sample(weights=(-0.0,0.5,-0.25,1.0),bias=(-0.0,0.25))
        self.assertEqual(crosscheck(base)['status'],'AGREE')
        def change_graph(graph):
            out=[]
            for f,w,val in wire_fields(memoryview(graph)):
                if f==5:
                    tensor=[]
                    for k,t,x in wire_fields(val):
                        # FLOAT32 raw_data and packed float_data have the same
                        # numeric meaning; both independently decoded streams
                        # must preserve all finite value bits including -0.
                        if k==9:tensor.append(fld(4,bytes(x)))
                        else:tensor.append(fld(k,bytes(x) if t==2 else x))
                    out.append(fld(5,b''.join(tensor)))
                else:out.append(fld(f,bytes(val) if w==2 else val))
            return b''.join(out)
        packed=replace_graph(base,change_graph)
        self.assertEqual(crosscheck(packed)['status'],'AGREE')
        from studio.protobuf_dual_decoder_v12 import _from_custom,_from_protobuf
        manual=_from_custom(screen_onnx(packed));standard=_from_protobuf(packed)
        self.assertEqual(manual,standard)
        self.assertIn('00000080',[b for t in manual['weights'].values() for b in t['bits']])

    def test_deterministic_wire_mutation_fuzz_has_no_silent_disagreement(self):
        rng=random.Random(20261104)
        original=dense_sample()
        accepted=0
        def mutate(raw,level):
            fields=list(wire_fields(memoryview(raw)))
            idx=rng.randrange(len(fields))
            f,w,val=fields[idx]
            if level<3 and w==2 and rng.randrange(3)!=0:
                try:fields[idx]=(f,w,mutate(bytes(val),level+1))
                except (ValueError,IndexError):pass
            else:
                mode=rng.randrange(7)
                if mode==0:fields.append((rng.randrange(1,35),2,b'GARBAGE'))
                elif mode==1:fields.insert(rng.randrange(len(fields)+1),(f,w,val))
                elif mode==2 and w==2:fields[idx]=(f,w,bytes(val)+bytes([rng.randrange(256)]))
                elif mode==3:fields.pop(idx)
                elif mode==4 and w==0:fields[idx]=(f,w,rng.randrange(24))
                elif mode==5 and w==2:fields[idx]=(f,w,bytes(val)[:rng.randrange(len(val)+1)])
                elif mode==6:fields[idx]=(rng.randrange(1,35),w,val)
            return b''.join(fld(k,bytes(x) if t==2 else int(x)) for k,t,x in fields)
        for _ in range(384):
            candidate=mutate(original,0)
            try:screen_onnx(candidate)
            except (Unsupported,ValueError,TypeError,IndexError):continue
            accepted+=1
            self.assertEqual(crosscheck(candidate)['status'],'AGREE')
        self.assertGreater(accepted,30)

    def test_sparse_initializer_was_silently_ignored_and_now_fails_closed(self):
        raw=dense_sample()
        mutated=replace_graph(raw,lambda graph:graph+fld(16,fld(1,b'ignored-sparse-initializer')))
        self.assertNotEqual(mutated,raw)
        with self.assertRaisesRegex(Unsupported,'GraphProto: unknown/mistyped'):
            screen_onnx(mutated)
        self.assertEqual(crosscheck(mutated)['status'],'DISAGREEMENT')

    def test_duplicate_graph_oneof_and_unsupported_model_fields_refuse(self):
        valid=dense_sample()
        graph1=replace_graph(valid,lambda g:g+fld(16,b'fake'))
        variants=[valid+fld(7, b''),graph1,valid+fld(25,b'local-function')]
        for raw in variants:
            with self.subTest(length=len(raw)):
                self.assertEqual(crosscheck(raw)['status'],'DISAGREEMENT')

    def test_independent_semantics_catches_wrong_custom_model(self):
        model=dense_sample()
        self.assertEqual(crosscheck(model)['status'],'AGREE')
        from studio import protobuf_dual_decoder_v12 as m
        original=m._from_custom
        def wrong(spec):
            d=original(spec)
            d['weights']['W']['bits'][0]='0000803f' if d['weights']['W']['bits'][0]!='0000803f' else '00000000'
            return d
        with patch.object(m,'_from_custom',side_effect=wrong):
            self.assertEqual(crosscheck(model)['status'],'DISAGREEMENT')

    def test_independent_decoder_is_fail_closed_when_missing(self):
        script=("from studio.protobuf_dual_decoder_v12 import crosscheck;"
                "from pathlib import Path;"
                "print(crosscheck(Path('samples/demo_trained_iris_mlp.onnx').read_bytes())['status'])")
        p=subprocess.run([sys.executable,'-S','-c',script],cwd=str(ROOT),
                         capture_output=True,text=True,timeout=15)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual(p.stdout.strip(),'NOT_RUN')


class DualDecoderGateV12(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old=(SAMPLES/'demo_trained_iris_mlp.onnx').read_bytes()
        cls.new=(SAMPLES/'demo_trained_iris_updated.onnx').read_bytes()
        cls.real=record('v09_demo_envelope_evidence.json')
        cls.direct=record('v10_direct_fp32_partition_evidence.json')
        cls.policy=record('v09_demo_envelope_reviewer_policy.json')
        cls.pin=hashlib.sha256(canonical(cls.policy)).hexdigest()
        cls.words=record('v09_demo_input_words.json')

    def create(self,old=None,new=None,real=None,direct=None,policy=None,pin=None):
        return DualDecoderAssuranceGate(
            self.old if old is None else old,self.new if new is None else new,
            self.real if real is None else real,self.direct if direct is None else direct,
            self.policy if policy is None else policy,self.pin if pin is None else pin)

    def test_three_class_admission_and_inference(self):
        gate=self.create()
        review=gate.review()
        self.assertEqual(review['status'],'PROVED_CONDITIONALLY',review)
        self.assertEqual(review['checked_fp32_partition_leaves'],37)
        self.assertEqual(review['verified_regions'],3)
        for i,cls in [('22',0),('62',1),('118',2)]:
            with self.subTest(i=i):
                result=gate.admit(self.words[i])
                self.assertEqual(result['status'],'ADMIT_CONDITIONALLY')
                self.assertEqual(result['class_index'],cls)
                inferred=gate.reference_infer(self.words[i])
                self.assertEqual(inferred['status'],'EXECUTED_CONDITIONALLY')
        self.assertEqual(gate.admit(['00000000']*4)['status'],'ABSTAIN')
        self.assertEqual(gate.reference_infer(['00000000']*4)['status'],'ABSTAIN')

    def test_recalculated_model_hash_with_spurious_graph_is_still_denied(self):
        corrupted=replace_graph(self.new,lambda g:g+fld(16,b'unsupported-sparse'))
        altered_policy=copy.deepcopy(self.policy)
        altered_policy['new_model_sha256']=hashlib.sha256(corrupted).hexdigest()
        altered_direct=copy.deepcopy(self.direct)
        altered_direct['model_sha256']=altered_policy['new_model_sha256']
        pin=hashlib.sha256(canonical(altered_policy)).hexdigest()
        altered_direct['policy_sha256']=pin
        gate=self.create(new=corrupted,policy=altered_policy,pin=pin,direct=altered_direct)
        self.assertEqual(gate.review()['status'],'OPEN')
        with patch('studio.guarded_reference_infer_v09.sequential_eval',side_effect=AssertionError('execution forbidden')):
            self.assertEqual(gate.reference_infer(self.words['22'])['status'],'ABSTAIN')

    def test_untrusted_policy_and_missing_branch_are_rejected(self):
        gate=self.create(pin='0'*64)
        self.assertEqual(gate.review()['status'],'OPEN')
        d=copy.deepcopy(self.direct);d['entries'][0]['comparisons'].pop()
        self.assertEqual(self.create(direct=d).review()['status'],'OPEN')

    def test_http_demo_has_exactly_three_replayed_conditional_cases(self):
        try:
            from fastapi.testclient import TestClient
            from studio.server import app
        except ImportError:
            self.skipTest('FastAPI is optional')
        with TestClient(app,base_url='http://testserver') as client:
            res=client.get('/api/dual-decoder-demo')
            self.assertEqual(res.status_code,200)
            d=res.json()
            self.assertEqual(d['review']['status'],'PROVED_CONDITIONALLY')
            self.assertEqual(len(d['examples']),3)
            self.assertEqual(d['outside_example']['reference_execution']['status'],'ABSTAIN')
            self.assertEqual(client.get('/api/dual-decoder-demo',headers={'host':'attacker.invalid'}).status_code,403)

if __name__=='__main__':unittest.main()
