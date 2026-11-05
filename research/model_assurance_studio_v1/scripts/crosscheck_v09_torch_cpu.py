"""Optional real PyTorch CPU crosscheck of screened v0.9 Iris operating envelope.

Requires torch, numpy, scikit-learn (not required by standard-library reviewer).
Executed numerical observations are NOT universal ONNX Runtime equivalence, proof
of the Python verifier, or independent holdout evaluation. No model code loaded.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from fractions import Fraction
from studio.operating_envelope_v09 import OperatingEnvelopeGate
from studio.dense_nn import screen_onnx
from studio.relational_kernel import canonical
from studio.ieee754 import round_bits,from_bits
from studio.fp32_assurance import sequential_eval

ROOT=Path(__file__).resolve().parents[1]
TRUSTED_DEMO_PIN='aec03cc456c9f6c77e548cffa1dc1503d795c1934d97d114afe4b4a0d7418c6d'


def crosscheck():
    import torch
    from sklearn.datasets import load_iris
    torch.set_num_threads(1)
    old=(ROOT/'samples/demo_trained_iris_mlp.onnx').read_bytes()
    new=(ROOT/'samples/demo_trained_iris_updated.onnx').read_bytes()
    policy=json.loads((ROOT/'validation/v09_demo_envelope_reviewer_policy.json').read_text())
    bundle=json.loads((ROOT/'validation/v09_demo_envelope_evidence.json').read_text())
    profile=json.loads((ROOT/'validation/v06_iris_profile.json').read_text())
    gate=OperatingEnvelopeGate(old,new,bundle,policy,TRUSTED_DEMO_PIN)
    report=gate.review()
    if report['status']!='PROVED_CONDITIONALLY':
        raise ValueError('not all certificate comparisons verified')
    spec=screen_onnx(new)

    # PyTorch is a *different* instruction implementation from the exact RN-even
    # software reference. Its backend is NOT official ONNX Runtime.
    weights={name:torch.tensor(w['values'],dtype=torch.float32,device='cpu').reshape(w['shape'])
             for name,w in spec['weights'].items()}
    def run_cpu(words):
        env={spec['input']:torch.tensor([[float(from_bits(int(w,16))) for w in words]],dtype=torch.float32)}
        env.update(weights)
        with torch.no_grad():
            for node in spec['nodes']:
                op,ins,out=node['op'],node['inputs'],node['out']
                if op=='MatMul':result=env[ins[0]] @ env[ins[1]]
                elif op=='Gemm':result=env[ins[0]] @ env[ins[1]] + env[ins[2]]
                elif op=='Add':result=env[ins[0]] + env[ins[1]]
                elif op=='Relu':result=torch.relu(env[ins[0]])
                elif op=='Identity':result=env[ins[0]].clone()
                else:raise ValueError('unrecognized operator')
                env[out]=result
        return [float(v) for v in env[spec['output']][0].tolist()]

    admits=[];abstains=[];min_margin=None;max_error=0.;violations=[]
    samples=load_iris().data
    for idx,row in enumerate(samples):
        standardized=[(float(v)-mean)/scale for v,mean,scale in zip(row,
            profile['standard_scaler_mean'],profile['standard_scaler_scale'])]
        words=[f'{round_bits(Fraction.from_float(float(v))):08x}' for v in standardized]
        inputs=[from_bits(int(word,16)) for word in words]
        cpu=run_cpu(words)
        soft=sequential_eval(spec,inputs)
        max_error=max(max_error,max(abs(float(a)-float(b)) for a,b in zip(soft,cpu)))
        decision=gate.admit(words)
        if decision['status']=='ADMIT_CONDITIONALLY':
            cls=decision['class_index']
            margin=min(cpu[cls]-v for j,v in enumerate(cpu) if j!=cls)
            min_margin=margin if min_margin is None else min(min_margin,margin)
            admits.append({'index':idx,'class_index':cls})
            if margin<0.25:violations.append(idx)
        else:abstains.append(idx)
    result={'schema':'pcs-v09-pytorch-cpu-observation-v1',
        'model_sha256':hashlib.sha256(new).hexdigest(),
        'policy_sha256':TRUSTED_DEMO_PIN,
        'tested_samples':len(samples),'admitted':len(admits),'abstained':len(abstains),
        'admitted_by_class':[sum(a['class_index']==c for a in admits) for c in range(spec['output_width'])],
        'observed_margin_violations':violations,
        'minimum_observed_pytorch_margin':min_margin,
        'max_abs_cpu_vs_sequential_reference':max_error,
        'pytorch_version':torch.__version__,
        'scope':'Observed PyTorch CPU computations only; same Iris dataset used to choose region anchors, no independent holdout, no official ONNX Runtime or Lean equivalence'}
    return result


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--output',help='optional result JSON file')
    a=p.parse_args()
    try:
        result=crosscheck()
        success=(result['tested_samples']==150 and result['admitted']==27 and
                 result['abstained']==123 and not result['observed_margin_violations'] and
                 result['max_abs_cpu_vs_sequential_reference']<0.0001)
        output=json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+'\n'
        if a.output:Path(a.output).write_text(output,encoding='utf-8')
        print(output,end='')
        return 0 if success else 2
    except Exception as exc:
        print(json.dumps({'status':'NOT_RUN','reason':type(exc).__name__+': '+str(exc)[:150]}))
        return 2

if __name__=='__main__':raise SystemExit(main())
