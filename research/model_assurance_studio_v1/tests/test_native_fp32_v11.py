"""Empirical value-semantics cross-check against a *fixed* compiled C evaluator.

The compiler and CPU remain TCB, not an official ONNX conformance proof.
"""
from __future__ import annotations
import json
import random
import shutil
import unittest
from fractions import Fraction
from pathlib import Path
from unittest.mock import patch
from studio.native_fp32_crosscheck_v11 import compare
from studio.ieee754 import round_bits
from tests.test_strict_onnx_v11 import dense_sample

ROOT=Path(__file__).resolve().parents[1]


def points(width,n=50,seed=2718):
    rng=random.Random(seed)
    base=['00000000','80000000','00000001','80000001','007fffff',
          '807fffff','00800000','80800000','3f800000','bf800000',
          '41200000','c1200000','3f000000','bf000000']
    result=[[base[(i+j*3)%len(base)] for j in range(width)] for i in range(min(len(base),n))]
    for _ in range(max(0,n-len(result))):
        result.append([f'{round_bits(Fraction(rng.randint(-1000,1000),100)):08x}' for _ in range(width)])
    return result

@unittest.skipUnless(shutil.which('cc'),'fixed C crosscheck requires a local C compiler')
class NativeReferenceV11(unittest.TestCase):
    def test_trained_iris_weighted_network_full_range_of_small_inputs(self):
        raw=(ROOT/'samples/demo_trained_iris_updated.onnx').read_bytes()
        r=compare(raw,points(4,90))
        self.assertEqual(r['status'],'AGREE_ON_TESTED_POINTS',r)
        self.assertEqual(r['checked_points'],90)
        self.assertEqual(r['disagreements'],[])

    def test_relu_identity_nonfused_and_subnormal_reference(self):
        for name,width in [('demo_activation_identity.onnx',1),
                           ('demo_hidden_spike.onnx',1),
                           ('demo_relational_margin.onnx',1),
                           ('demo_dense_neural_violation.onnx',2)]:
            with self.subTest(name=name):
                raw=(ROOT/'samples'/name).read_bytes()
                r=compare(raw,points(width,40))
                self.assertEqual(r['status'],'AGREE_ON_TESTED_POINTS',r)

    def test_randomized_supported_gemm_and_dynamic_add_graphs(self):
        rng=random.Random(119973)
        choices=[-4.,-2.,-1.,-.5,0.,.5,1.,2.,4.]
        for i in range(18):
            weights=tuple(rng.choice(choices) for _ in range(4))
            bias=tuple(rng.choice(choices) for _ in range(2))
            raw=dense_sample(weights=weights,bias=bias,use_gemm=(i%3==0),
                             combine_dynamic=(i%3==1))
            with self.subTest(i=i):
                result=compare(raw,points(2,22,seed=i+7))
                self.assertEqual(result['status'],'AGREE_ON_TESTED_POINTS',result)

    def test_native_detects_deliberate_python_interpreter_divergence(self):
        raw=(ROOT/'samples/demo_dense_neural_violation.onnx').read_bytes()
        with patch('studio.native_fp32_crosscheck_v11.sequential_eval',return_value=[Fraction(123),Fraction(456)]):
            r=compare(raw,[['00000000','00000000']])
        self.assertEqual(r['status'],'DISAGREEMENT',r)
        self.assertTrue(r['disagreements'])

    def test_invalid_model_and_input_abstain(self):
        good=(ROOT/'samples/demo_trained_iris_updated.onnx').read_bytes()
        self.assertEqual(compare(good+b'\xff',[['00000000']*4])['status'],'NOT_RUN')
        for bad in ([["7fc00000"]*4],[['00000000']],[['00z00000']*4],[],[['00000000']*4]*513):
            with self.subTest(bad=str(bad)[:35]):
                self.assertEqual(compare(good,bad)['status'],'NOT_RUN')
        self.assertEqual(compare(good,[['00000000']*4],compiler='__missing_cc__')['status'],'NOT_RUN')

if __name__=='__main__':unittest.main()
