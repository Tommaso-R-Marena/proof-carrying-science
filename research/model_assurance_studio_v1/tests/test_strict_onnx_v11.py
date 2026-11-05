"""Malicious protobuf ambiguity regression tests for screened ONNX authority.

No official ONNX Runtime or ONNX library is required. These cases demonstrate
malformed bytes previously accepted by the subset decoder and prevent later
proof/checker releases from re-admitting those ambiguous encodings.
"""
from __future__ import annotations
import copy
import hashlib
import json
import unittest
from pathlib import Path
from tests.make_samples import fld
import struct
from studio.engine import wire_fields
from studio.dense_nn import screen_onnx, Unsupported
from studio.direct_fp32_v10 import POLICY_SCHEMA, verify as verify_direct
from studio.direct_fp32_proposer_v10 import propose
from studio.relational_kernel import canonical


def dense_sample(weights=(1.,0.,0.,1.),bias=(.25,-.25),use_gemm=False,combine_dynamic=False):
    def vi(name,shape):
        dims=b''.join(fld(1,fld(1,d)) for d in shape)
        return fld(1,name)+fld(2,fld(1,fld(1,1)+fld(2,dims)))
    def tensor(name,shape,values):
        return b''.join(fld(1,d) for d in shape)+fld(2,1)+fld(8,name)+fld(9,b''.join(struct.pack('<f',v) for v in values))
    def node(op,inputs,output):
        return b''.join(fld(1,i) for i in inputs)+fld(2,output)+fld(4,op)
    if use_gemm:
        operations=[node('Gemm',['features','W','b'],'h'),node('Relu',['h'],'prediction')]
    elif combine_dynamic:
        operations=[node('MatMul',['features','W'],'h'),node('Relu',['h'],'a'),node('Add',['h','a'],'prediction')]
    else:
        operations=[node('MatMul',['features','W'],'h'),node('Add',['h','b'],'pre'),node('Relu',['pre'],'prediction')]
    graph=(b''.join(fld(1,n) for n in operations)+fld(2,'dense')+
        fld(5,tensor('W',[2,2],weights))+fld(5,tensor('b',[2],bias))+
        fld(11,vi('features',[1,2]))+fld(12,vi('prediction',[1,2])))
    return fld(1,8)+fld(7,graph)+fld(8,fld(2,13))


def replace_graph(raw,graph_transform):
    fields=[]
    for f,w,v in wire_fields(memoryview(raw)):
        if f==7 and w==2:v=graph_transform(bytes(v))
        fields.append(fld(f,bytes(v)) if w==2 else fld(f,v))
    return b''.join(fields)


def mutate_graph(graph,target_field,modifier):
    out=[];done=False
    for f,w,v in wire_fields(memoryview(graph)):
        if f==target_field and not done:
            v=modifier(bytes(v));done=True
        out.append(fld(f,bytes(v)) if w==2 else fld(f,v))
    assert done
    return b''.join(out)


def corrupt_tensor_oneof(vi):
    def add_sequence_proto(typ):
        # TypeProto has a oneof: tensor_type=1 vs sequence_type=4.
        # A normal protobuf parser selects the last oneof branch; the old
        # subset decoder silently used the preceding tensor_type instead.
        return typ+fld(4, fld(1, fld(1, fld(1,1))))
    return mutate_graph(vi,2,add_sequence_proto)


def malformed_models():
    m=dense_sample()
    graph=next(bytes(v) for f,w,v in wire_fields(memoryview(m)) if f==7)
    return {
        'duplicate singular GraphProto':m+fld(7,graph),
        'oneof tensor then sequence':replace_graph(m,lambda g:mutate_graph(g,11,corrupt_tensor_oneof)),
        'duplicate graph input type':replace_graph(m,lambda g:mutate_graph(g,11,lambda vi:vi+next(fld(2,bytes(v)) for f,w,v in wire_fields(memoryview(vi)) if f==2))),
        'unsupported local functions':m+fld(25,b'\x00'),
        'unsupported training metadata':m+fld(20,b'\x00'),
        'node overload':replace_graph(m,lambda g:mutate_graph(g,1,lambda node:node+fld(8,'custom_overload'))),
        'duplicate node operator':replace_graph(m,lambda g:mutate_graph(g,1,lambda node:node+fld(4,'Relu'))),
        'contradictory symbolic dimension':replace_graph(m,lambda g:mutate_graph(g,11,lambda vi:mutate_graph(vi,2,lambda typ:typ+fld(6,'X')))),
        'tensor unknown value encoding':replace_graph(m,lambda g:mutate_graph(g,5,lambda tensor:tensor+fld(5,7))),
        'duplicate tensor raw data':replace_graph(m,lambda g:mutate_graph(g,5,lambda tensor:tensor+next(fld(9,bytes(v)) for f,w,v in wire_fields(memoryview(tensor)) if f==9))),
        'duplicate opset semantic field':m+fld(8,fld(2,13)+fld(2,19)),
    }

class StrictWireV11(unittest.TestCase):
    def test_baseline_valid_screened_fixtures_still_accepted(self):
        root=Path(__file__).resolve().parents[1]
        samples=['demo_dense_neural_violation.onnx','demo_hidden_spike.onnx',
                 'demo_activation_identity.onnx','demo_trained_iris_mlp.onnx',
                 'demo_trained_iris_updated.onnx','demo_trained_iris_bad_update.onnx',
                 'demo_relational_margin.onnx','demo_partition_abs.onnx']
        for name in samples:
            with self.subTest(name=name):
                obj=screen_onnx((root/'samples'/name).read_bytes())
                self.assertGreater(obj['input_width'],0)

    def test_semantically_ambiguous_protobuf_is_rejected(self):
        for name,raw in malformed_models().items():
            with self.subTest(name=name):
                with self.assertRaises((Unsupported,ValueError)):
                    screen_onnx(raw)

    def test_ambiguous_model_never_gets_conditional_proof_even_with_rebound_hash(self):
        # An attacker can recompute every untrusted hash, but not alter the
        # independently pinned model grammar or its reviewer requirements.
        good=dense_sample()
        policy={'schema':POLICY_SCHEMA,'model_sha256':hashlib.sha256(good).hexdigest(),
                'input_box':[['-1','1'],['-1','1']],
                'output_coefficients':['1','-1'],'upper_limit':'20'}
        candidate=propose(good,policy,max_leaves=8)
        self.assertEqual(candidate['status'],'CANDIDATE_REPLAYED')
        cert=candidate['certificate']
        for name,raw in malformed_models().items():
            with self.subTest(name=name):
                p=copy.deepcopy(policy);p['model_sha256']=hashlib.sha256(raw).hexdigest()
                c=copy.deepcopy(cert);c['model_sha256']=p['model_sha256']
                c['policy_sha256']=hashlib.sha256(canonical(p)).hexdigest()
                result=verify_direct(raw,p,c,c['policy_sha256'])
                self.assertEqual(result['status'],'OPEN')

    def test_model_size_preflight(self):
        with self.assertRaises(Unsupported):
            screen_onnx(b'\x00'*(8*1024*1024+1))
        with self.assertRaises(Unsupported):
            screen_onnx(bytearray(dense_sample()))

if __name__=='__main__':unittest.main()
