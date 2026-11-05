"""Optional differential reference execution over independently implemented ops."""
from __future__ import annotations
import os,sys,subprocess,tempfile,json
from pathlib import Path

def crosscheck_torch(spec, witness, target, numpy_replay):
    payload={'schema':spec['schema'],'input':spec['input'],'input_width':spec['input_width'],
             'output':spec['output'],'output_width':spec['output_width'],
             'nodes':spec['nodes'],'weights':spec['weights'],
             'values':witness['inputs'][spec['input']],'target':[float(target[0]),float(target[1])]}
    raw=json.dumps(payload,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
    if len(raw)>65536:return {'status':'INDETERMINATE','reason':'instruction budget'}
    env={k:v for k,v in os.environ.items() if k in ('PATH','WINDIR','SYSTEMROOT','LD_LIBRARY_PATH')}
    env.update({'OMP_NUM_THREADS':'1','MKL_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1',
                'PYTHONNOUSERSITE':'1','PYTHONDONTWRITEBYTECODE':'1','CUDA_VISIBLE_DEVICES':''})
    try:
        with tempfile.TemporaryDirectory(prefix='pcs-torch-') as workdir:
            env['HOME']=workdir
            p=subprocess.run([sys.executable,'-I',str(Path(__file__).with_name('torch_worker.py'))],
                             input=raw,capture_output=True,env=env,cwd=workdir,timeout=18,check=False)
        if p.returncode or len(p.stdout)>16384:raise ValueError('runtime process failed/output exceeded limit')
        result=json.loads(p.stdout)
        if result.get('status') not in ('VIOLATION_REPRODUCED','CANDIDATE_NOT_REPRODUCED','INDETERMINATE'):
            raise ValueError('unexpected runtime result')
        if result['status']=='INDETERMINATE':return result
        previous=numpy_replay
        if not previous or previous.get('status')=='INDETERMINATE':
            result['agreement']='UNVERIFIED_NUMPY_REFERENCE'
            return result
        a=previous.get('outputs');b=result.get('outputs')
        if not isinstance(a,list) or len(a)!=len(b):
            result['agreement']='UNVERIFIED_SHAPE_DIFFERENCE';return result
        # Binary32 BLAS rounding can differ. Use an explicitly approximate
        # tolerance, not a claim of exact numerical equivalence.
        tol=1e-5
        agrees=all(abs(x-y)<=tol+tol*max(abs(x),abs(y)) for x,y in zip(a,b))
        result['agreement']='WITHIN_TOLERANCE' if agrees else 'DISAGREE'
        result['agreement_atol']=tol;result['agreement_rtol']=tol
        result['both_reproduced_violation']=(agrees and result['status']=='VIOLATION_REPRODUCED' and
                                              previous.get('status')=='VIOLATION_REPRODUCED')
        return result
    except (OSError,ValueError,subprocess.TimeoutExpired,TypeError,json.JSONDecodeError) as exc:
        return {'status':'INDETERMINATE','reason':type(exc).__name__}
