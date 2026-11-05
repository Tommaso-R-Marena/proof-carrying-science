"""Bounded experimental AI assurance for tiny dense ONNX FLOAT32 networks.

This intentionally supports only a narrow, no-attribute, constant-weight subset:
[1,n] input, 1-D/2-D FLOAT32 embedded weights, MatMul/Gemm/Add/Relu/Identity,
[1,m] output. The range calculation is exact *real* interval arithmetic; a
separate NumPy worker executes a screened float32 graph, NOT ONNX Runtime.
Unknown, ambiguous, or unsupported semantics are OPEN, never a safety PASS.
"""
from __future__ import annotations
import itertools
import json
import math
import os
from fractions import Fraction
from pathlib import Path
import random
import struct
import subprocess
import sys
import tempfile

MAX_WIDTH=16
MAX_NODES=64
MAX_INITIALIZER_VALUES=1024
MAX_BITS=512
MAX_PROBES=256

class Unsupported(Exception): pass


def _finite_fraction(v):
    if not math.isfinite(v):raise Unsupported('Non-finite float weight')
    return Fraction.from_float(float(v))

def _budget(v):
    if v.numerator.bit_length()>MAX_BITS or v.denominator.bit_length()>MAX_BITS:
        raise Unsupported('Exact rational arithmetic budget exceeded')
    return v

# This is a *strict* serialization subset, not a general ONNX loader.  In
# protobuf a repeated singular message is MERGED, while oneof alternatives
# obey last-member-wins. Ignoring those distinctions can prove a claim about
# a different graph from the one parsed by ONNX. Reject ambiguities before
# interpreting numerical semantics.
MAX_SCREENED_MODEL_BYTES = 8 * 1024 * 1024


def _exact_fields(raw, wire_fields, *, level, allowed, context):
    """Reject unexpected field numbers and wire types within accepted grammar."""
    for number, wire, value in wire_fields(raw, level):
        if number not in allowed or wire not in allowed[number]:
            raise Unsupported(f'{context}: unknown/mistyped semantic field {number}/{wire}')
        yield number, wire, value


def _parse_shape(vi, wire_fields):
    name = None
    typ = None
    for f,w,v in _exact_fields(vi,wire_fields,level=2,
                             allowed={1:{2},2:{2},3:{2}},context='ValueInfoProto'):
        if f == 1:
            if name is not None:raise Unsupported('Duplicate ValueInfoProto name')
            name=bytes(v).decode('utf8','strict')
        elif f == 2:
            if typ is not None:raise Unsupported('Repeated TypeProto merges ambiguously')
            typ=v
    if not name or typ is None:raise Unsupported('Missing explicitly typed ONNX graph input/output')
    tensor = None
    for f,w,v in _exact_fields(typ,wire_fields,level=3,
                             allowed={1:{2}},context='TypeProto tensor oneof'):
        if tensor is not None:raise Unsupported('Repeated tensor_type merges ambiguously')
        tensor=v
    if tensor is None:raise Unsupported('Only plain tensor_type is accepted')
    dtype=None;shape=None
    for f,w,v in _exact_fields(tensor,wire_fields,level=4,
                             allowed={1:{0},2:{2}},context='TypeProto.Tensor'):
        if f==1:
            if dtype is not None:raise Unsupported('Duplicate element_type')
            dtype=v
        elif f==2:
            if shape is not None:raise Unsupported('Repeated TensorShapeProto merges ambiguously')
            dims=[]
            for sf,sw,sv in _exact_fields(v,wire_fields,level=5,
                                         allowed={1:{2}},context='TensorShapeProto'):
                n=None
                for df,dw,dv in _exact_fields(sv,wire_fields,level=6,
                                              allowed={1:{0},3:{2}},context='TensorShapeProto.Dimension'):
                    if df==1:
                        if n is not None:raise Unsupported('Duplicate shape dimension')
                        n=dv
                if n is None or not 1<=n<=MAX_WIDTH:
                    raise Unsupported('Unknown, symbolic, or oversized model dimension')
                dims.append(int(n))
            shape=dims
    if dtype!=1 or shape is None:raise Unsupported('Require explicitly typed FLOAT32 tensor dimensions')
    return name,shape


def _tensor(raw,wire_fields,read_varint):
    name=None;dtype=None;dims=[];raw_data=None;packed=[];values=[]
    # segment (3), other typed data (5,6,7,10,11), external_data (13)
    # and data_location (14) are NOT valid for this narrow grammar.
    for f,w,v in _exact_fields(raw,wire_fields,level=2,
                            allowed={1:{0,2},2:{0},4:{2,5},8:{2},9:{2},12:{2}},
                            context='TensorProto'):
        if f==1:
            if w==0:dims.append(int(v))
            else:
                pos=0
                while pos<len(v):
                    num,pos=read_varint(v,pos)
                    dims.append(int(num))
        elif f==2:
            if dtype is not None:raise Unsupported('Duplicate TensorProto data_type')
            dtype=v
        elif f==8:
            if name is not None:raise Unsupported('Duplicate TensorProto name')
            name=bytes(v).decode('utf8','strict')
        elif f==9:
            if raw_data is not None:raise Unsupported('Duplicate singular TensorProto raw_data')
            raw_data=bytes(v)
        elif f==4 and w==5:values.append(struct.unpack('<f',v)[0])
        elif f==4 and w==2:packed.append(bytes(v))
    if not name or dtype!=1 or not 1<=len(dims)<=2 or any(n<1 or n>MAX_WIDTH for n in dims):
        raise Unsupported('Only inline one/two-dimensional FLOAT32 initializer tensors are supported')
    count=math.prod(dims)
    if count>MAX_INITIALIZER_VALUES or (raw_data is not None and (packed or values)) or (packed and values):
        raise Unsupported('Initializer size or overlapping data encodings')
    if raw_data is not None:
        if len(raw_data)!=4*count:raise Unsupported('Invalid FLOAT32 initializer byte count')
        vals=[v[0] for v in struct.iter_unpack('<f',raw_data)]
    elif packed:
        joined=b''.join(packed)
        if len(joined)!=4*count:raise Unsupported('Invalid packed initializer byte count')
        vals=[v[0] for v in struct.iter_unpack('<f',joined)]
    else:vals=values
    if len(vals)!=count:raise Unsupported('Initializer does not contain the exact declared element count')
    for v in vals:_finite_fraction(v)
    return name, dims, vals


def screen_onnx(raw):
    from .engine import wire_fields,read_varint
    if type(raw) is not bytes or not 1<=len(raw)<=MAX_SCREENED_MODEL_BYTES:
        raise Unsupported('Require bounded immutable serialized ONNX model bytes')
    graph=None;opsets=[];ir=None
    for f,w,v in _exact_fields(memoryview(raw),wire_fields,level=0,
                             allowed={1:{0},2:{2},3:{2},4:{2},5:{0},6:{2},7:{2},8:{2},14:{2}},
                             context='ModelProto'):
        if f==7:
            if graph is not None:raise Unsupported('Repeated singular GraphProto: protobuf merge ambiguity')
            graph=v
        elif f==1:
            if ir is not None:raise Unsupported('Duplicate ir_version')
            ir=v
        elif f==8:
            d='';ver=None;seen=set()
            for a,b,c in _exact_fields(v,wire_fields,level=2,
                                       allowed={1:{2},2:{0}},context='OperatorSetIdProto'):
                if a in seen:raise Unsupported('Duplicate opset import field')
                seen.add(a)
                if a==1:d=bytes(c).decode('utf8','strict')
                if a==2:ver=int(c)
            opsets.append((d,ver))
    if graph is None or ir is None or not (6<=ir<=10) or len(opsets)!=1 or opsets[0][0] not in ('','ai.onnx') or opsets[0][1] is None or not (13<=opsets[0][1]<=19):
        raise Unsupported('Requires a single standard ONNX opset 13–19 and supported IR version')
    weights={};nodes=[];inputs=[];outputs=[]
    for f,w,v in _exact_fields(graph,wire_fields,level=1,
                             allowed={1:{2},2:{2},5:{2},10:{2},11:{2},12:{2},13:{2},16:{2}},
                             context='GraphProto'):
        if f==11:inputs.append(_parse_shape(v,wire_fields))
        elif f==12:outputs.append(_parse_shape(v,wire_fields))
        elif f==13:
            # Extra ValueInfo is only annotation in ONNX but can be false or
            # ambiguous. Refuse it until the parser checks consistency.
            raise Unsupported('Intermediate value_info is outside the reviewed grammar')
        elif f==5:
            name,shape,values=_tensor(v,wire_fields,read_varint)
            if name in weights:raise Unsupported('Duplicate initializer names')
            weights[name]={'shape':shape,'values':values}
        elif f==1:
            inp=[];out=[];op=None;domain=None;seen=set()
            for a,b,c in _exact_fields(v,wire_fields,level=2,
                                  allowed={1:{2},2:{2},3:{2},4:{2},5:{2},6:{2},7:{2},8:{2}},
                                  context='NodeProto'):
                if a==1:inp.append(bytes(c).decode('utf8','strict'))
                elif a==2:out.append(bytes(c).decode('utf8','strict'))
                elif a in (4,7):
                    if a in seen:raise Unsupported('Repeated semantic node field')
                    seen.add(a)
                    if a==4:op=bytes(c).decode('utf8','strict')
                    else:domain=bytes(c).decode('utf8','strict')
                elif a==5:raise Unsupported('Node attributes are outside the screened grammar')
                elif a==8:raise Unsupported('Node overloads are outside the screened grammar')
            if (domain not in (None,'','ai.onnx') or
                    op not in ('MatMul','Gemm','Add','Relu','Identity')):
                raise Unsupported('Unsupported operator or operator domain')
            if len(out)!=1 or not out[0] or any(not x for x in inp):
                raise Unsupported('Ambiguous node input or output')
            nodes.append({'op':op,'inputs':inp,'out':out[0]})
    if len(inputs)!=1 or len(outputs)!=1 or len(nodes)>MAX_NODES or not nodes or sum(len(w['values']) for w in weights.values())>MAX_INITIALIZER_VALUES:
        raise Unsupported('Only one-input/one-output models with <=64 nodes and <=1024 weight values')
    in_name,in_shape=inputs[0];out_name,out_shape=outputs[0]
    if len(in_shape)!=2 or in_shape[0]!=1 or len(out_shape)!=2 or out_shape[0]!=1:
        raise Unsupported('Require explicit [1,n] inputs and [1,m] outputs')
    env={in_name:('matrix',in_shape[1])}
    for name,weight in weights.items():
        if name in env:raise Unsupported('Initializer shadows graph input')
        env[name]=('constant',tuple(weight['shape']))
    for node in nodes:
        op=node['op'];ins=node['inputs'];out=node['out']
        if out in env or any(x not in env for x in ins):raise Unsupported('Unbound or multiply defined graph node')
        if op in ('MatMul','Gemm'):
            if len(ins)!=(2 if op=='MatMul' else 3):raise Unsupported('MatMul/Gemm requires fixed inputs and bias for Gemm')
            a,b=env[ins[0]],env[ins[1]]
            if a[0]!='matrix' or b[0]!='constant' or len(b[1])!=2 or a[1]!=b[1][0]:raise Unsupported('Require [1,n] matrix multiplied by constant [n,m] weight')
            if op=='Gemm' and (env[ins[2]]!=('constant',(b[1][1],))):raise Unsupported('Gemm bias must be [m] constant')
            env[out]=('matrix',b[1][1])
        elif op=='Add':
            if len(ins)!=2:raise Unsupported('Add requires exactly two arguments')
            a,b=env[ins[0]],env[ins[1]]
            if a[0]=='matrix' and b in (('constant',(a[1],)),('constant',(1,a[1]))):env[out]=a
            elif b[0]=='matrix' and a in (('constant',(b[1],)),('constant',(1,b[1]))):env[out]=b
            elif a==b and a[0]=='matrix':env[out]=a
            else:raise Unsupported('Add broadcasting outside reviewed [1,n]+[n] subset')
        elif op in ('Identity','Relu'):
            if len(ins)!=1 or env[ins[0]][0]!='matrix':raise Unsupported('Identity/Relu requires [1,n] dynamic input')
            env[out]=env[ins[0]]
    if env.get(out_name)!=('matrix',out_shape[1]):raise Unsupported('Output dimensionality mismatch')
    if sum(n['op'] in ('MatMul','Gemm') for n in nodes)==0:raise Unsupported('Not a dense affine network; use scalar checker')
    return {'schema':'pcs-screened-dense-nn-v0.4','input':in_name,'input_width':in_shape[1],
            'output':out_name,'output_width':out_shape[1], 'weights':weights,'nodes':nodes,
            'opset':opsets[0][1],'ir':ir}

def _matmul(v,weight):
    n,m=weight['shape']; vals=weight['values']
    out=[]
    for j in range(m):
        lo=hi=Fraction(0)
        for i in range(n):
            w=_finite_fraction(vals[i*m+j]);a,b=v[i]
            lo=_budget(lo+min(_budget(a*w),_budget(b*w)))
            hi=_budget(hi+max(_budget(a*w),_budget(b*w)))
        out.append((lo,hi))
    return out

def _execute_intervals(spec,input_bounds, *, return_env=False):
    env={spec['input']:input_bounds}
    weights=spec['weights']
    for node in spec['nodes']:
        op,ins,out=node['op'],node['inputs'],node['out']
        if op in ('MatMul','Gemm'):
            v=_matmul(env[ins[0]],weights[ins[1]])
            if op=='Gemm':
                b=weights[ins[2]]['values']
                v=[(_budget(x+_finite_fraction(b[i])),_budget(y+_finite_fraction(b[i]))) for i,(x,y) in enumerate(v)]
        elif op=='Add':
            if ins[0] in weights:
                const=weights[ins[0]]['values'];dyn=env[ins[1]]
            elif ins[1] in weights:
                const=weights[ins[1]]['values'];dyn=env[ins[0]]
            else:
                a,b=env[ins[0]],env[ins[1]]
                v=[(_budget(x[0]+y[0]),_budget(x[1]+y[1])) for x,y in zip(a,b)]
                env[out]=v;continue
            v=[(_budget(x+_finite_fraction(const[i])),_budget(y+_finite_fraction(const[i]))) for i,(x,y) in enumerate(dyn)]
        elif op=='Relu':v=[(max(x,0),max(y,0)) for x,y in env[ins[0]]]
        else:v=list(env[ins[0]])
        env[out]=v
    return env if return_env else env[spec['output']]

def _f32(v):return struct.unpack('<f',struct.pack('<f',v))[0]

def _next32(x, direction):
    """Next representable IEEE binary32 in the requested numeric direction."""
    if x==0.0:return struct.unpack('<f',struct.pack('<I',1 if direction>0 else 0x80000001))[0]
    u=struct.unpack('<I',struct.pack('<f',x))[0]
    u+=1 if ((x>0)==(direction>0)) else -1
    return struct.unpack('<f',struct.pack('<I',u))[0]

def candidate_inputs(spec,p):
    n=spec['input_width']
    # A float32-rounded sample outside the stipulated *real-number* input box
    # cannot be used as a valid counterexample to that box's claim.
    l0=float(p['input_min']);h0=float(p['input_max'])
    lo=_f32(l0);hi=_f32(h0)
    if lo<l0:lo=_next32(lo,1)
    if hi>h0:hi=_next32(hi,-1)
    if not math.isfinite(lo) or not math.isfinite(hi) or lo>hi:raise Unsupported('No representable float32 sample within assumed input interval')
    center=_f32((lo+hi)/2)
    if center<lo:center=lo
    if center>hi:center=hi
    # Prioritize a deterministic set of corners; prevent 2**n explosion.
    yielded=set()
    for choice in itertools.product((lo,hi), repeat=min(n,8)):
        point=tuple(choice)+tuple([center]*(n-min(n,8)))
        if point not in yielded:yielded.add(point);yield point
    rng=random.Random(0x5C5)
    for _ in range(MAX_PROBES-len(yielded)):
        point=tuple(_f32(rng.uniform(lo,hi)) for _ in range(n))
        if point not in yielded:yielded.add(point);yield point

def check_dense(raw,policy):
    try:
        spec=screen_onnx(raw)
        lower=Fraction.from_float(float(policy['input_min']));upper=Fraction.from_float(float(policy['input_max']))
        target=(Fraction.from_float(float(policy['output_min'])),Fraction.from_float(float(policy['output_max'])))
        bounds=_execute_intervals(spec,[(lower,upper)]*spec['input_width'])
        proven=all(a>=target[0] and b<=target[1] for a,b in bounds)
        reported={'supported':True,'operator_count':len(spec['nodes']),'initializers':len(spec['weights']),
                  'input_width':spec['input_width'],'output_width':spec['output_width'],
                  'enclosure_exact':[[str(a),str(b)] for a,b in bounds],
                  'conditional_real_range':'PROVED_WITHIN_ASSUMED_BOX' if proven else 'NOT_PROVED_WITHIN_ASSUMED_BOX',
                  'assumptions':'Exact rational interpretation of embedded FLOAT32 weights and box inputs; IBP overapproximation; not float32 runtime guarantees.'}
        witness=None;tested=0
        if not proven and policy.get('search_scalar_witness'):
            for point in candidate_inputs(spec,policy):
                tested+=1
                vals=_execute_intervals(spec,[(Fraction.from_float(v),Fraction.from_float(v)) for v in point])
                # singleton exact execution, NOT rounded inference.
                if any(a<target[0] or a>target[1] for a,b in vals):
                    witness={'inputs':{spec['input']:list(point)},'idealized_outputs':[str(a) for a,b in vals],
                             'trials':tested,'status':'IDEALIZED_RATIONAL_VIOLATION'}
                    break
        reported['probes_tested']=tested
        replay=None
        if witness and policy.get('enable_reference_replay'):
            replay=_replay(spec,witness,target)
        return reported,witness,replay,None
    except (Unsupported,ValueError,OverflowError,ArithmeticError,TypeError,UnicodeError) as exc:
        return None,None,None,str(exc)[:220]

def _replay(spec,witness,target):
    # Worker receives only host-screened JSON floats/nodes; NEVER original ONNX bytes.
    safe={'schema':spec['schema'],'input':spec['input'],'input_width':spec['input_width'],
          'output':spec['output'],'output_width':spec['output_width'],'weights':spec['weights'],
          'nodes':spec['nodes'],'values':witness['inputs'][spec['input']],
          'target':[float(target[0]),float(target[1])]}
    payload=json.dumps(safe,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
    if len(payload)>65536:return {'status':'INDETERMINATE','reason':'Worker instruction budget exceeded'}
    env={k:v for k,v in os.environ.items() if k in ('SYSTEMROOT','WINDIR','PATH','LD_LIBRARY_PATH')}
    env.update({'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1','MKL_NUM_THREADS':'1','PYTHONNOUSERSITE':'1','PYTHONDONTWRITEBYTECODE':'1'})
    try:
        with tempfile.TemporaryDirectory(prefix='pcs-dense-') as tmp:
            env['HOME']=tmp
            p=subprocess.run([sys.executable,'-I',str(Path(__file__).with_name('dense_worker.py'))],
                 input=payload,capture_output=True,cwd=tmp,timeout=7,check=False,env=env)
        if p.returncode!=0 or len(p.stdout)>16384:raise ValueError('Worker exit or output budget failure')
        obj=json.loads(p.stdout)
        if obj.get('status') not in ('VIOLATION_REPRODUCED','CANDIDATE_NOT_REPRODUCED','INDETERMINATE'):
            raise ValueError('Invalid worker response')
        return obj
    except (OSError,subprocess.TimeoutExpired,ValueError,TypeError) as e:
        return {'status':'INDETERMINATE','reason':type(e).__name__}
