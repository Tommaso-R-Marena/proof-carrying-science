"""Adversarial and numerical regression coverage for v0.7.

These tests DO NOT impersonate Lean compilation or official ONNX Runtime.
"""
import copy
import json
import math
import random
import struct
from fractions import Fraction
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient
from studio.ieee754 import round_bits,round_value,from_bits,float_to_bits,MAX_FINITE,UnsupportedFP32
from studio.fp32_assurance import issue,verify,intervals,sequential_eval,digest,POLICY_SCHEMA
from studio.fp32_lift_v07 import output_errors,lift_single,lift_update,error_contribution
from studio.dense_nn import screen_onnx,_execute_intervals
from studio.lean_export_v07 import export_relational,export_update
from studio.onnxruntime_crosscheck_v07 import compare as ort_compare,ulp_distance
from studio.server import app

ROOT=Path(__file__).resolve().parents[1]
def raw(name):return (ROOT/'samples'/name).read_bytes()
def val(name):return json.loads((ROOT/'validation'/name).read_text())
def policy(name,box,coeffs,bound):
    model=raw(name)
    return dict(schema=POLICY_SCHEMA,model_sha256=digest(model),input_box=box,
                output_coefficients=coeffs,upper_limit=bound)


def test_binary32_edges_and_subnormals():
    assert round_bits(Fraction(0))==0
    assert round_bits(Fraction(1,1<<150))==0  # tie -> even zero
    assert round_bits(Fraction(3,1<<150))==2  # tie -> even mantissa two
    assert from_bits(1)==Fraction(1,1<<149)
    assert from_bits(0x7f7fffff)==MAX_FINITE
    assert round_value(MAX_FINITE+1)==MAX_FINITE
    with pytest.raises(UnsupportedFP32):round_bits(MAX_FINITE+(1<<104))
    with pytest.raises(UnsupportedFP32):from_bits(0x7f800000)
    with pytest.raises(UnsupportedFP32):from_bits(0x7fc00000)
    assert round_bits(-Fraction(1,1<<149))==0x80000001
    assert round_value(Fraction(1,3))==Fraction.from_float(struct.unpack('<f',struct.pack('<f',1/3))[0])


def test_binary32_independent_numpy_random_rounding():
    r=random.Random(873723)
    for _ in range(2500):
        x=(r.random()*2-1)*10**r.randrange(-40,39)
        if not math.isfinite(x) or abs(x)>3e38:continue
        expected=float_to_bits(x)
        assert round_bits(Fraction.from_float(x))==expected
    for _ in range(1000):
        a=r.randrange(1,0x7f7fffff);b=r.randrange(1,0x7f7fffff)
        x=Fraction.from_float(struct.unpack('<f',struct.pack('<I',a))[0])
        y=Fraction.from_float(struct.unpack('<f',struct.pack('<I',b))[0])
        if abs(x+y)>MAX_FINITE:continue
        assert round_bits(x+y)==float_to_bits(float(x+y))

@pytest.mark.parametrize('name,box,coeffs,bound',[
 ('demo_dense_neural_violation.onnx',[['-1','1'],['-1','1']],['1','0'],'5/4'),
 ('demo_relational_margin.onnx',[['-1','1']],['-1','1'],'3/4'),
 ('demo_trained_iris_mlp.onnx',[['-2','2']]*4,['1','0','0'],'1000'),
])
def test_interval_proof_has_many_actual_replays(name,box,coeffs,bound):
    model=raw(name);spec=screen_onnx(model);p=policy(name,box,coeffs,bound)
    assessment=issue(model,p)
    assert assessment['status']=='PROVED_CONDITIONALLY'
    assert verify(model,p,assessment)[0]
    claimed=intervals(spec,[(Fraction(a),Fraction(b)) for a,b in box])
    r=random.Random(7777)
    for _ in range(100):
        point=[]
        for a,b in box:
            q=float(np.float32(r.uniform(float(Fraction(a)),float(Fraction(b)))))
            # input float32 conversion might slightly escape an unrepresentable edge
            if q<float(Fraction(a)) or q>float(Fraction(b)):q=0.0
            point.append(Fraction.from_float(q))
        outputs=sequential_eval(spec,point)
        for (lo,hi),v in zip(claimed,outputs):assert lo<=v<=hi


def test_sequential_interpreter_matches_explicit_numpy_scalar_operations():
    model=raw('demo_trained_iris_mlp.onnx');spec=screen_onnx(model);r=random.Random(811)
    for _ in range(100):
        x=np.asarray([r.uniform(-2,2) for _ in range(spec['input_width'])],dtype=np.float32)
        actual={spec['input']:x}
        weights={k:np.array(v['values'],dtype=np.float32).reshape(v['shape']) for k,v in spec['weights'].items()}
        for node in spec['nodes']:
            op,ins,out=node['op'],node['inputs'],node['out']
            if op in ('MatMul','Gemm'):
                A=actual[ins[0]];W=weights[ins[1]];dy=[]
                for j in range(W.shape[1]):
                    acc=np.float32(0)
                    for i in range(W.shape[0]):
                        term=np.float32(A[i]*W[i,j]);acc=np.float32(acc+term)
                    if op=='Gemm':acc=np.float32(acc+weights[ins[2]][j])
                    dy.append(acc)
                actual[out]=np.array(dy,dtype=np.float32)
            elif op=='Add':
                a=weights.get(ins[0],actual.get(ins[0]))
                b=weights.get(ins[1],actual.get(ins[1]))
                actual[out]=np.float32(a+b)
            elif op=='Relu':actual[out]=np.maximum(actual[ins[0]],np.float32(0))
            elif op=='Identity':actual[out]=actual[ins[0]]
        exact=sequential_eval(spec,[Fraction.from_float(float(v)) for v in x])
        for a,b in zip(exact,actual[spec['output']]):assert a==Fraction.from_float(float(b))


def test_reviewer_tampering_and_model_binding():
    name='demo_dense_neural_violation.onnx';model=raw(name)
    p=policy(name,[['-1','1']]*2,['1','0'],'5/4');a=issue(model,p)
    assert a['status']=='PROVED_CONDITIONALLY'
    for changed in ['upper_limit','output_coefficients','input_box','model_sha256']:
        q=copy.deepcopy(p)
        if changed=='upper_limit':q[changed]='1'
        if changed=='output_coefficients':q[changed]=['-1','0']
        if changed=='input_box':q[changed]=[['-2','2']]*2
        if changed=='model_sha256':q[changed]='0'*64
        assert verify(model,q,a)[0] is False
    bad=copy.deepcopy(a);bad['computed_upper_bound']='0'
    assert not verify(model,p,bad)[0]
    assert issue(model+b'bad-tail',p)['status']=='OPEN'


def test_lift_error_budget_covers_numerical_inputs():
    model=raw('demo_trained_iris_mlp.onnx');spec=screen_onnx(model)
    policy_obj=val('v06_iris_property_1_reviewer_policy.json')
    box=[(Fraction(a),Fraction(b)) for a,b in policy_obj['input_box']]
    E=output_errors(spec,box)
    r=random.Random(142)
    for _ in range(100):
        xs=[]
        for a,b in box:
            v=float(np.float32(r.uniform(float(a),float(b))))
            if Fraction.from_float(v)<a or Fraction.from_float(v)>b:v=float(np.float32((float(a)+float(b))/2))
            xs.append(Fraction.from_float(v))
        exact=_execute_intervals(spec,[(x,x) for x in xs]);actual=sequential_eval(spec,xs)
        for (lo,hi),v,e in zip(exact,actual,E):
            assert lo==hi
            assert abs(v-lo)<=e


def test_lift_iris_real_property_and_proof_gated_update():
    old=raw('demo_trained_iris_mlp.onnx');new=raw('demo_trained_iris_updated.onnx')
    basecert=val('v06_iris_property_1_certificate.json');basepol=val('v06_iris_property_1_reviewer_policy.json')
    delta=val('v06_update_drift_certificate.json');dpol=val('v06_update_reviewer_policy.json')
    b=lift_single(old,basecert,basepol,'-499/1000')
    assert b['status']=='PROVED_CONDITIONALLY'
    assert Fraction(b['verified_float32_rounding_cushion'])<Fraction(1,1000)
    a=lift_update(old,new,basecert,basepol,delta,dpol,'-37/100')
    assert a['status']=='PROVED_CONDITIONALLY'
    assert Fraction(a['derived_float32_upper_bound']) <= Fraction(-37,100)
    assert lift_update(old,new,basecert,basepol,delta,dpol,'-3/8')['status']=='OPEN'
    assert lift_update(old,raw('demo_trained_iris_bad_update.onnx'),basecert,basepol,delta,dpol,'-37/100')['status']=='OPEN'
    altered=copy.deepcopy(dpol);altered['upper_limit']='0'
    assert lift_update(old,new,basecert,basepol,delta,altered,'-37/100')['status']=='OPEN'


def test_lean_sources_are_uncompiled_only_and_reject_fakes():
    model=raw('demo_trained_iris_mlp.onnx');c=val('v06_iris_property_1_certificate.json');p=val('v06_iris_property_1_reviewer_policy.json')
    lean=export_relational(model,c,p)
    assert 'theorem certified_relation' in lean
    assert 'import Mathlib' in lean
    assert 'Status when generated: NOT KERNEL CHECKED' in lean
    assert not any(tok in lean for tok in ['sorry','admit','native_decide','axiom '])
    altered=copy.deepcopy(c);altered['multipliers'][0][1]='11'
    with pytest.raises(ValueError):export_relational(model,altered,p)
    d=val('v06_update_drift_certificate.json');dp=val('v06_update_reviewer_policy.json')
    proof=export_update(model,raw('demo_trained_iris_updated.onnx'),d,dp)
    assert 'theorem certified_update_drift' in proof
    assert 'theorem bounded_update_composition' in proof
    with pytest.raises(ValueError):export_update(model,raw('demo_trained_iris_bad_update.onnx'),d,dp)


def test_official_runtime_must_not_be_faked():
    r=ort_compare(raw('demo_dense_neural_violation.onnx'),count=4)
    if r['status']=='NOT_RUN':
        assert 'reason' in r
        assert 'OBSERVED_MATCH' not in str(r)
    else:
        assert r['status'] in ('OBSERVED_MATCH','OBSERVED_DIFFERENCES')
        assert r['official_runtime_version']
        assert r['execution_provider']=='CPUExecutionProvider'
        assert r['universal_equivalence_established'] is False
    assert ulp_distance(1.,1.)==0
    assert ulp_distance(0.,np.float32(2**-149))==1


def test_local_http_fp32_drag_drop_and_bad_requests():
    model=raw('demo_dense_neural_violation.onnx')
    p={'input_box':[['-1','1'],['-1','1']],'input_min':'-1','input_max':'1',
       'output_coefficients':['1','0'],'upper_limit':'5/4'}
    headers={'host':'testserver','x-pcs-fp32-claim':json.dumps(p)}
    with TestClient(app) as c:
        r=c.post('/api/fp32-assure',content=model,headers=headers)
        assert r.status_code==200,r.text
        result=r.json();assert result['assessment']['status']=='PROVED_CONDITIONALLY'
        assert result['independent_reviewer_acceptance']=='NOT_ESTABLISHED'
        assert verify(model,result['suggested_reviewer_policy'],result['assessment'])[0]
        assert c.post('/api/fp32-assure',content=b'not-onnx',headers=headers).status_code==400
        corrupt={**headers,'host':'example.com'}
        assert c.post('/api/fp32-assure',content=model,headers=corrupt).status_code==403
        malformed={**headers,'x-pcs-fp32-claim':'{}'}
        assert c.post('/api/fp32-assure',content=model,headers=malformed).status_code==400


def test_torch_actual_cpu_network_inside_conditional_rounding_error():
    import torch
    torch.set_num_threads(1)
    model=raw('demo_trained_iris_updated.onnx')
    spec=screen_onnx(model)
    p=val('v06_iris_property_1_reviewer_policy.json')
    box=[(Fraction(a),Fraction(b)) for a,b in p['input_box']]
    errors=output_errors(spec,box)
    r=random.Random(214)
    for _ in range(80):
        vals=[]
        for a,b in box:
            v=float(np.float32(r.uniform(float(a)+.00001,float(b)-.00001)))
            q=Fraction.from_float(v)
            assert a<=q<=b
            vals.append(q)
        env={spec['input']:torch.tensor([float(x) for x in vals],dtype=torch.float32).reshape(1,-1)}
        weights={k:torch.tensor(w['values'],dtype=torch.float32).reshape(w['shape']) for k,w in spec['weights'].items()}
        with torch.no_grad():
            for node in spec['nodes']:
                op,ins,out=node['op'],node['inputs'],node['out']
                if op=='Gemm':y=env[ins[0]]@weights[ins[1]]+weights[ins[2]]
                elif op=='MatMul':y=env[ins[0]]@weights[ins[1]]
                elif op=='Add':y=(env.get(ins[0]) if ins[0] in env else weights[ins[0]])+(env.get(ins[1]) if ins[1] in env else weights[ins[1]])
                elif op=='Relu':y=torch.relu(env[ins[0]])
                elif op=='Identity':y=env[ins[0]]
                else:pytest.fail('unexpected op')
                env[out]=y
            y=env[spec['output']].detach().cpu().numpy().reshape(-1)
        perfect=_execute_intervals(spec,[(q,q) for q in vals])
        for observed,(lo,hi),e in zip(y,perfect,errors):
            assert lo==hi
            assert abs(Fraction.from_float(float(observed))-lo)<=e


def test_http_two_model_fp32_rounding_lift_and_rejected_policies():
    from urllib.parse import quote
    old=raw('demo_trained_iris_mlp.onnx');new=raw('demo_trained_iris_updated.onnx')
    body=len(old).to_bytes(4,'little')+old+new
    p=val('v06_iris_profile.json')
    claim={'input_box':p['reviewer_box'],'output_coefficients':['-1','1','0'],
        'baseline_upper_limit':'-1/2','drift_upper_limit':'1/8',
        'required_new_upper_limit':'-3/8','fp32_required_new_upper_limit':'-37/100'}
    with TestClient(app) as c:
        head={'x-pcs-fp32-update-policy':quote(json.dumps(claim))}
        result=c.post('/api/compare-update-fp32',content=body,headers=head)
        assert result.status_code==200,result.text[:300]
        report=result.json()
        assert report['exact_real']['status']=='PROVED_CONDITIONALLY'
        assert report['binary32_lift']['status']=='PROVED_CONDITIONALLY'
        assert report['lean_kernel_verification']=='NOT_ESTABLISHED'
        assert report['runtime_equivalence']=='NOT_ESTABLISHED'
        fail=copy.deepcopy(claim);fail['fp32_required_new_upper_limit']='-3/8'
        r=c.post('/api/compare-update-fp32',content=body,
                 headers={'x-pcs-fp32-update-policy':quote(json.dumps(fail))})
        assert r.status_code==200
        assert r.json()['binary32_lift']['status']=='OPEN'
        r=c.post('/api/compare-update-fp32',content=b'garbage',headers=head)
        assert r.status_code==400
        r=c.post('/api/compare-update-fp32',content=body,
                 headers={**head,'Origin':'https://evil.example'})
        assert r.status_code==403
