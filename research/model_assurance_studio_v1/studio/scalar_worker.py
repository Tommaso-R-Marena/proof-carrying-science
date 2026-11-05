"""Bounded, separate-process NumPy replay for a tiny ONNX scalar operator subset.

No model source/binary or executable code enters this worker: only a screened JSON
operator list and float32 values. This is NOT ONNX Runtime equivalence, a hardened
sandbox, or a result about general neural-network safety.
"""
from __future__ import annotations
import json
import math
import sys
import struct

ALLOWED = {'Identity': 1, 'Neg': 1, 'Relu': 1, 'Abs': 1,
           'Add': 2, 'Sub': 2, 'Mul': 2, 'Div': 2}

def execute(spec):
    import numpy as np
    if not isinstance(spec, dict) or spec.get('schema') != 'pcs-scalar-replay-v0.3':
        raise ValueError('invalid replay instruction schema')
    nodes = spec['nodes']; inputs = spec['inputs']; outputs = spec['outputs']; boundary = spec['target']
    if (not isinstance(nodes, list) or len(nodes) > 512 or
        not isinstance(inputs, dict) or not 1 <= len(inputs) <= 3 or
        not isinstance(outputs, list) or not 1 <= len(outputs) <= 8 or
        not isinstance(boundary, list) or len(boundary) != 2):
        raise ValueError('replay resource limits exceeded')
    env = {}
    for name, value in inputs.items():
        if not isinstance(name,str) or len(name)>256 or not isinstance(value,(int,float)) or not math.isfinite(value):
            raise ValueError('invalid input')
        env[name] = np.float32(value)
    functions = {'Identity':lambda x:np.float32(x[0]),
       'Neg':lambda x:np.negative(x[0]),
       'Relu':lambda x:np.maximum(x[0],np.float32(0)),
       'Abs':lambda x:np.abs(x[0]),
       'Add':lambda x:np.add(x[0],x[1]),
       'Sub':lambda x:np.subtract(x[0],x[1]),
       'Mul':lambda x:np.multiply(x[0],x[1]),
       'Div':lambda x:np.divide(x[0],x[1])}
    with np.errstate(divide='ignore', over='ignore', under='ignore', invalid='ignore'):
        for node in nodes:
            op = node['op']; ins = node['inputs']; out = node['output']
            if op not in ALLOWED or len(ins)!=ALLOWED[op] or any(i not in env for i in ins):
                raise ValueError('unknown op or unavailable operand')
            if out in env or not isinstance(out,str) or not out or len(out)>256:
                raise ValueError('invalid output')
            env[out] = np.float32(functions[op]([env[i] for i in ins]))
    result={}
    for o in outputs:
        if o not in env:raise ValueError('missing model output')
        f=float(env[o]);result[o]=f
        if not math.isfinite(f):
            return {'status':'INDETERMINATE','reason':'Non-finite float32 result',
                    'runtime':'numpy-float32-allowlisted','numpy':np.__version__}
    bad = [o for o in outputs if not (boundary[0] <= result[o] <= boundary[1])]
    return {'status':'VIOLATION_REPRODUCED' if bad else 'CANDIDATE_NOT_REPRODUCED',
            'scope':'Screened ONNX scalar graph evaluated as NumPy float32 primitives; not ONNX Runtime',
            'runtime':'numpy-float32-allowlisted','numpy':np.__version__,
            'python':sys.version.split()[0],
            'model_execution':'screened scalar operations only',
            'outputs':result,'violating_outputs':bad,
            'output_bits_hex':{o:struct.pack('<f',result[o]).hex() for o in outputs}}

if __name__ == '__main__':
    try:
        raw=sys.stdin.buffer.read(65537)
        if len(raw)>65536:raise ValueError('replay instructions too large')
        response=execute(json.loads(raw))
        print(json.dumps(response,allow_nan=False,sort_keys=True))
    except Exception as exc:
        print(json.dumps({'status':'INDETERMINATE','reason':type(exc).__name__+': '+str(exc)[:200]}))
