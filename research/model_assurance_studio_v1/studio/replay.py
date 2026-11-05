"""Screened scalar-graph replay boundary; not a security sandbox.

Only allowlisted parsed scalar graphs with no attributes, initializers, external
files or unsupported types are sent to a local process containing trusted code.
The worker receives *JSON*, never raw ONNX, pickle, or model-defined functions.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ALLOWED = {'Identity':1,'Neg':1,'Relu':1,'Abs':1,'Add':2,'Sub':2,'Mul':2,'Div':2}
WORKER = Path(__file__).with_name('scalar_worker.py')

def structural_eligibility(nodes, inputs, outputs, types, shapes, initializer_count, node_attribute_count):
    if initializer_count or node_attribute_count:
        return 'Scalar reference replay excludes initializers and operator attributes'
    if not 1<=len(inputs)<=3 or not 1<=len(outputs)<=8 or len(nodes)>512:
        return 'Scalar replay supports 1–3 inputs, 1–8 outputs, and no more than 512 operators'
    if not all(types.get(x)==1 and shapes.get(x) in ((),(1,)) for x in inputs+outputs):
        return 'Only explicit FLOAT32 scalar/[1] input and output shapes are replayable'
    known=set(inputs)
    for ins,outs,op,domain,nested in nodes:
        if op not in ALLOWED or domain not in ('','ai.onnx') or nested or len(outs)!=1 or not outs[0]:
            return 'Operator not in tightly scoped reference-replay allowlist'
        if len(ins)!=ALLOWED[op] or any(not x or x not in known for x in ins):
            return 'Operator arity/input not supported for replay'
        if outs[0] in known:return 'Output name collision'
        known.add(outs[0])
    if any(x not in known for x in outputs):return 'Unbound output name'
    return None

def replay_candidate(nodes, inputs, outputs, types, shapes, initializer_count, node_attribute_count, witness, policy):
    why=structural_eligibility(nodes,inputs,outputs,types,shapes,initializer_count,node_attribute_count)
    if why:return {'status':'INDETERMINATE','reason':why}
    spec={'schema':'pcs-scalar-replay-v0.3','nodes':[{'inputs':ins,'output':outs[0],'op':op} for ins,outs,op,_,_ in nodes],
          'inputs':witness['inputs'],'outputs':outputs,
          'target':[policy['output_min'],policy['output_max']]}
    payload=json.dumps(spec,separators=(',',':'),allow_nan=False).encode('utf8')
    if len(payload)>65536:return {'status':'INDETERMINATE','reason':'Screened instruction budget exceeded'}
    env={k:v for k,v in os.environ.items() if k in ('SYSTEMROOT','WINDIR','PATH','LD_LIBRARY_PATH')}
    env.update({'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1','MKL_NUM_THREADS':'1','PYTHONNOUSERSITE':'1',
                'PYTHONDONTWRITEBYTECODE':'1'})
    try:
        with tempfile.TemporaryDirectory(prefix='pcs-replay-') as wd:
            env['HOME']=wd
            result=subprocess.run([sys.executable,'-I',str(WORKER)],input=payload,capture_output=True,
                 timeout=7,check=False,cwd=wd,env=env)
        if result.returncode or len(result.stdout)>16384:
            return {'status':'INDETERMINATE','reason':f'Worker failed or exceeded output budget (exit {result.returncode})'}
        obj=json.loads(result.stdout)
        if obj.get('status') not in ('VIOLATION_REPRODUCED','CANDIDATE_NOT_REPRODUCED','INDETERMINATE'):
            return {'status':'INDETERMINATE','reason':'Worker returned unexpected status'}
        return obj
    except (subprocess.TimeoutExpired, OSError, ValueError, json.JSONDecodeError) as exc:
        return {'status':'INDETERMINATE','reason':type(exc).__name__}
