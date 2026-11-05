"""ONNX model with exact-real identity ReLU(x)-ReLU(-x)-x = 0.

The global LP relaxation can be inconclusive even when identity holds for
all x; exhaustive activation splits plus exact Farkas leaves can close it.
"""
from pathlib import Path
import struct
from tests.make_samples import fld

def demo():
    def vi(name,shape):
        dims=b''.join(fld(1,fld(1,n)) for n in shape)
        return fld(1,name)+fld(2,fld(1,fld(1,1)+fld(2,dims)))
    def tensor(name,shape,values):
        return (b''.join(fld(1,n) for n in shape)+fld(2,1)+fld(8,name)+
                fld(9,b''.join(struct.pack('<f',float(v)) for v in values)))
    def node(op,ins,out):return b''.join(fld(1,v) for v in ins)+fld(2,out)+fld(4,op)
    nodes=[('MatMul',['features','wplus'],'p'),
           ('MatMul',['features','wminus'],'n'),
           ('Relu',['p'],'rp'),('Relu',['n'],'rn'),
           ('MatMul',['rn','wminus'],'neg_rn'),
           ('Add',['rp','neg_rn'],'a'),
           ('Add',['a','n'],'prediction')]
    graph=b''.join(fld(1,node(*a)) for a in nodes)+fld(2,'activation_case_demo')
    graph+=fld(5,tensor('wplus',[1,1],[1]))+fld(5,tensor('wminus',[1,1],[-1]))
    graph+=fld(11,vi('features',[1,1]))+fld(12,vi('prediction',[1,1]))
    return fld(1,8)+fld(7,graph)+fld(8,fld(2,13))

if __name__=='__main__':
    out=Path(__file__).resolve().parents[1]/'samples/demo_activation_identity.onnx'
    out.write_bytes(demo());print(out, len(demo()))
