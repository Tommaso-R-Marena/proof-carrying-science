"""Create an actual, tiny serialized ONNX ReLU network with correlated logits.

For x in [-1,1]: logit_0 = relu(x)+1/4; logit_1 = relu(x).
Hence logit_1-logit_0 = -1/4 uniformly. Per-logit interval bounds
are insufficient to establish this exact classification margin.
"""
from pathlib import Path
import struct
from tests.make_samples import fld

def demo():
    def vi(name,shape):
        dims=b''.join(fld(1,fld(1,k)) for k in shape)
        return fld(1,name)+fld(2,fld(1,fld(1,1)+fld(2,dims)))
    def tensor(name,shape,values):
        return (b''.join(fld(1,n) for n in shape)+fld(2,1)+fld(8,name)+
                fld(9,b''.join(struct.pack('<f',v) for v in values)))
    def node(op,ins,out):
        return b''.join(fld(1,txt) for txt in ins)+fld(2,out)+fld(4,op)
    graph=(fld(1,node('MatMul',['features','win'],'z'))+
           fld(1,node('Relu',['z'],'h'))+
           fld(1,node('MatMul',['h','wout'],'both'))+
           fld(1,node('Add',['both','bias'],'logits'))+
           fld(2,'pcs_relational_margin')+
           fld(5,tensor('win',[1,1],[1.0]))+
           fld(5,tensor('wout',[1,2],[1.0,1.0]))+
           fld(5,tensor('bias',[2],[0.25,0.0]))+
           fld(11,vi('features',[1,1]))+fld(12,vi('logits',[1,2])))
    return fld(1,8)+fld(7,graph)+fld(8,fld(2,13))

if __name__=='__main__':
    dest=Path(__file__).resolve().parents[1]/'samples'/'demo_relational_margin.onnx'
    dest.write_bytes(demo());print(dest, len(demo()))
