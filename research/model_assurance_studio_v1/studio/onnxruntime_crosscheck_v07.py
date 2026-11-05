"""Optional real ONNX Runtime CPU comparison, for locally trusted ONNX files.

This runs the actual official InferenceSession if installed; no mocking is counted
as an ONNX Runtime validation. The worker subprocess is NOT a security sandbox.
CPU provider, one thread, sequential execution and graph optimizations disabled
make runs more reproducible but do not imply mathematically identical FP32 ops.
Never run this command on a hostile model without OS-level sandboxing.
"""
from __future__ import annotations
import json
import hashlib
import math
import struct
import sys
from fractions import Fraction
from pathlib import Path
from .fp32_assurance import sequential_eval
from .dense_nn import screen_onnx


def _word(x):
    return struct.unpack('<I',struct.pack('<f',float(x)))[0]


def ulp_distance(a,b):
    x=_word(a);y=_word(b)
    # Monotone integer encoding across negative and positive numbers.
    def key(bits):return (0x80000000-bits) if bits>>31 else bits+0x80000000
    return abs(key(x)-key(y))


def _probe_vectors(spec, count, seed):
    import random
    r=random.Random(seed)
    base=[]
    n=spec['input_width']
    base.extend([[0.0]*n,[1.0]*n,[-1.0]*n])
    for j in range(n):
        vec=[0.0]*n;vec[j]=1.0;base.append(vec)
        vec=[0.0]*n;vec[j]=-1.0;base.append(vec)
    while len(base)<count:
        base.append([r.uniform(-2,2) for _ in range(n)])
    return base[:count]


def compare(model:bytes,count=48,seed=1771):
    """Actual official runtime comparison: NOT_RUN if the package is unavailable."""
    base={'schema':'pcs-official-onnxruntime-cpu-crosscheck-v0.7',
          'model_sha256':hashlib.sha256(model).hexdigest(),
          'scope':'finite observed CPU vectors only; sequential software reference; NOT universal equivalence',
          'status':'NOT_RUN'}
    try:
        import numpy as np
        import onnxruntime as ort
    except ImportError as exc:
        return dict(base,reason='Official onnxruntime and NumPy must be installed; missing '+str(exc.name))
    try:
        spec=screen_onnx(model)
        opt=ort.SessionOptions();opt.graph_optimization_level=ort.GraphOptimizationLevel.ORT_DISABLE_ALL
        opt.execution_mode=ort.ExecutionMode.ORT_SEQUENTIAL
        opt.intra_op_num_threads=1;opt.inter_op_num_threads=1
        session=ort.InferenceSession(model,sess_options=opt,providers=['CPUExecutionProvider'])
        if session.get_providers()!=['CPUExecutionProvider']:
            return dict(base,reason='CPUExecutionProvider isolation check failed')
        meta_in=session.get_inputs();meta_out=session.get_outputs()
        if len(meta_in)!=1 or len(meta_out)!=1 or meta_in[0].name!=spec['input'] or meta_out[0].name!=spec['output']:
            return dict(base,reason='Runtime graph interface differs from screened interpretation')
        if meta_in[0].type!='tensor(float)' or meta_out[0].type!='tensor(float)':
            return dict(base,reason='Expected only tensor(float) I/O')
        if list(meta_in[0].shape)!=[1,spec['input_width']] or list(meta_out[0].shape)!=[1,spec['output_width']]:
            return dict(base,reason='Runtime shape differs from screened interpretation')
        probes=_probe_vectors(spec,int(count),seed)
        maxulp=0;disagreements=0;worst=None
        for j,vec in enumerate(probes):
            actual_inputs=np.array(vec,dtype=np.float32).reshape((1,-1))
            if not np.all(np.isfinite(actual_inputs)):
                return dict(base,reason='nonfinite input after float32 conversion')
            ref=sequential_eval(spec,[Fraction.from_float(float(a)) for a in actual_inputs[0]])
            got=session.run([spec['output']],{spec['input']:actual_inputs})[0]
            if got.dtype!=np.float32 or got.shape!=(1,spec['output_width']) or not np.all(np.isfinite(got)):
                return dict(base,status='NUMERICAL_MISMATCH',reason='Runtime returned invalid/nonfinite output',case=j)
            for k,(expect,observed) in enumerate(zip(ref,got[0])):
                err=ulp_distance(float(expect),float(observed))
                if err:
                    disagreements+=1
                    if err>maxulp:
                        maxulp=err;worst={'case':j,'output':k,'reference':str(expect),
                            'onnxruntime':float(observed).hex(),'reference_bits':f'{_word(expect):08x}',
                            'onnxruntime_bits':f'{_word(observed):08x}','ulp_difference':err}
        return dict(base,status='OBSERVED_MATCH' if not disagreements else 'OBSERVED_DIFFERENCES',
            official_runtime_version=ort.__version__,execution_provider='CPUExecutionProvider',
            tested_vectors=len(probes),tested_scalar_outputs=len(probes)*spec['output_width'],
            nonidentical_scalar_outputs=disagreements,max_ulp_difference=maxulp,
            worst_case=worst,universal_equivalence_established=False)
    except Exception as exc:
        return dict(base,status='NOT_RUN',reason=f'{type(exc).__name__}: {str(exc)[:180]}')


def main():
    import argparse
    import subprocess
    import os
    p=argparse.ArgumentParser(description='Actual ONNX Runtime CPU cross-check (trusted local files ONLY)')
    p.add_argument('model');p.add_argument('--count',type=int,default=48)
    p.add_argument('--timeout',type=int,default=25);p.add_argument('--output')
    p.add_argument('--worker',action='store_true',help=argparse.SUPPRESS)
    a=p.parse_args()
    if not 1<=a.count<=256 or not 1<=a.timeout<=120:
        p.error('probe count/timeout budget')
    if a.worker:
        result=compare(Path(a.model).read_bytes(),count=a.count)
    else:
        # A subprocess is a crash/time boundary, not a hostile-file sandbox.
        try:
            proc=subprocess.run([sys.executable,'-m','studio.onnxruntime_crosscheck_v07',a.model,'--count',str(a.count),'--worker'],
                cwd=str(Path(__file__).resolve().parent.parent),capture_output=True,text=True,timeout=a.timeout)
            result=json.loads(proc.stdout) if proc.stdout.strip() else {'status':'NOT_RUN','reason':proc.stderr[-300:] or 'Worker did not return a JSON report'}
            if proc.returncode not in (0,2):result={'status':'NOT_RUN','reason':proc.stderr[-300:] or f'worker exit code {proc.returncode}'}
        except (subprocess.TimeoutExpired,json.JSONDecodeError) as exc:
            result={'status':'NOT_RUN','reason':type(exc).__name__}
    if a.output:Path(a.output).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,sort_keys=True,indent=2))
    return 0 if result.get('status') in ('OBSERVED_MATCH','OBSERVED_DIFFERENCES') else 2

if __name__=='__main__':raise SystemExit(main())
