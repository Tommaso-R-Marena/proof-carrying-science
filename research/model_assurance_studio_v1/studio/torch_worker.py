"""Optional second CPU float32 reference implementation using PyTorch.

Only screened network instructions arrive here (never uploaded ONNX bytes). This
is not ONNX Runtime, a secure sandbox, or a comprehensive runtime-equivalence test.
"""
from __future__ import annotations
import json,sys,math,struct

def execute(spec):
    import torch
    torch.set_num_threads(1)
    if spec.get('schema')!='pcs-screened-dense-nn-v0.4':raise ValueError('invalid schema')
    nodes=spec['nodes'];weights=spec['weights'];vals=spec['values'];bound=spec['target']
    n=spec['input_width']
    if not 1<=n<=16 or len(vals)!=n or not 1<=len(nodes)<=64 or sum(len(w['values']) for w in weights.values())>1024:
        raise ValueError('instruction budget')
    env={spec['input']:torch.tensor([vals],dtype=torch.float32,device='cpu')}
    for name,w in weights.items():
        if name in env:raise ValueError('duplicate tensor name')
        env[name]=torch.tensor(w['values'],dtype=torch.float32,device='cpu').reshape(w['shape'])
    with torch.no_grad():
        for node in nodes:
            op,ins,out=node['op'],node['inputs'],node['out']
            if out in env or any(k not in env for k in ins):raise ValueError('invalid data flow')
            if op=='MatMul' and len(ins)==2:v=torch.matmul(env[ins[0]],env[ins[1]])
            elif op=='Gemm' and len(ins)==3:v=torch.add(torch.matmul(env[ins[0]],env[ins[1]]),env[ins[2]])
            elif op=='Add' and len(ins)==2:v=torch.add(env[ins[0]],env[ins[1]])
            elif op=='Relu' and len(ins)==1:v=torch.relu(env[ins[0]])
            elif op=='Identity' and len(ins)==1:v=env[ins[0]].clone()
            else:raise ValueError('operator rejected')
            env[out]=v
    output=env[spec['output']]
    if tuple(output.shape)!=(1,spec['output_width']):raise ValueError('output shape')
    values=[float(v) for v in output.reshape(-1).tolist()]
    if not all(math.isfinite(v) for v in values):return {'status':'INDETERMINATE','reason':'nonfinite output'}
    violations=[i for i,v in enumerate(values) if not bound[0]<=v<=bound[1]]
    return {'status':'VIOLATION_REPRODUCED' if violations else 'CANDIDATE_NOT_REPRODUCED',
            'runtime':'pytorch-cpu-float32-reference','torch':torch.__version__,
            'outputs':values,'output_bits_hex':[struct.pack('<f',v).hex() for v in values],
            'violating_indices':violations,
            'scope':'Independent PyTorch CPU implementation of screened ops; not ONNX Runtime equivalence'}

if __name__=='__main__':
    try:
        raw=sys.stdin.buffer.read(65537)
        if len(raw)>65536:raise ValueError('input limit')
        print(json.dumps(execute(json.loads(raw)),allow_nan=False,sort_keys=True))
    except Exception as exc:
        print(json.dumps({'status':'INDETERMINATE','reason':type(exc).__name__},sort_keys=True))
