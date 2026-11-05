"""Seeded differential/property tests over screened ONNX networks.

Actual RN-even results must lie within the affine enclosure for every sampled
FP32 input. Samples are NOT a proof of the transformer's universal soundness.
"""
from fractions import Fraction
from pathlib import Path
import random
import unittest
from studio.affine_fp32_v13 import _derive
from studio.dense_nn import screen_onnx
from studio.fp32_assurance import sequential_eval
from studio.ieee754 import from_bits,float_to_bits
from tests.test_strict_onnx_v11 import dense_sample

class RandomizedAffineV13(unittest.TestCase):
    def test_seeded_weighted_relu_graphs_contain_executions(self):
        rng=random.Random(0x132026)
        checked=0
        for g in range(80):
            weights=tuple(rng.randrange(-8,9)/4 for _ in range(4))
            bias=tuple(rng.randrange(-8,9)/4 for _ in range(2))
            raw=dense_sample(weights=weights,bias=bias)
            spec=screen_onnx(raw)
            box=[(Fraction(-2),Fraction(2))]*2
            forms,_=_derive(spec,box)
            bounds=[form.bound() for form in forms]
            for i in range(24):
                p=[]
                for j in range(2):
                    f=rng.uniform(-2,2)
                    q=from_bits(float_to_bits(f))
                    if not -2<=q<=2:q=Fraction(0)
                    p.append(q)
                actual=sequential_eval(spec,p)
                for y,(low,high) in zip(actual,bounds):
                    self.assertLessEqual(low,y,(g,i,weights,bias,p))
                    self.assertLessEqual(y,high,(g,i,weights,bias,p))
                checked+=1
        self.assertEqual(checked,80*24)

    def test_seeded_pure_gemm_graphs_contain_executions(self):
        rng=random.Random(0x13FACE)
        for g in range(40):
            weights=tuple(rng.randrange(-8,9)/4 for _ in range(4))
            bias=tuple(rng.randrange(-8,9)/4 for _ in range(2))
            spec=screen_onnx(dense_sample(weights=weights,bias=bias,use_gemm=True))
            forms,_=_derive(spec,[(Fraction(-4),Fraction(4))]*2)
            bd=[x.bound() for x in forms]
            for i in range(16):
                p=[from_bits(float_to_bits(rng.uniform(-4,4))) for _ in range(2)]
                outputs=sequential_eval(spec,p)
                for y,(a,b) in zip(outputs,bd):
                    self.assertLessEqual(a,y)
                    self.assertLessEqual(y,b)

if __name__=='__main__':unittest.main()
