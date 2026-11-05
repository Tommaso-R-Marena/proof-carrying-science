"""Differential test of screened ONNX semantics against a fixed native C CPU path.

Never runs model-supplied source. Compiles the *reviewed static C evaluator* into a
private temporary directory and hands it only a screened bounded instruction
stream. This is extra empirical evidence: it neither verifies the parser/host,
nor proves ONNX Runtime/hardware equivalence or creates a secure sandbox.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import struct
import subprocess
import tempfile
from pathlib import Path
from fractions import Fraction
from .dense_nn import screen_onnx
from .fp32_assurance import sequential_eval
from .ieee754 import from_bits, round_bits

SOURCE=Path(__file__).with_name('native_fp32_reference_v11.c')
MAX_POINTS=512


def _f32_bits(x:float)->int:
    return struct.unpack('<I',struct.pack('<f',x))[0]


def _validate_point(spec,points):
    if type(points) is not list or not 1<=len(points)<=MAX_POINTS:
        raise ValueError('test point budget exceeded')
    for point in points:
        if type(point) is not list or len(point)!=spec['input_width'] or any(type(x) is not str or len(x)!=8 or any(ch not in '0123456789abcdef' for ch in x) for x in point):
            raise ValueError('invalid binary32 input bit words')
        for x in point:from_bits(int(x,16))


def _instruction_stream(spec, words):
    # Screened graph only. No paths, source strings, generated C, or code from
    # the submitted model reaches the native evaluator.
    nodes=spec['nodes'];weights=spec['weights']
    slot={spec['input']:0}
    lines=['PCS32V1 %d %d %d %d'%(spec['input_width'],len(nodes),
                   1+next(i for i,n in enumerate(nodes) if n['out']==spec['output']),
                   spec['output_width'])]
    lines.extend(str(int(x,16)) for x in words)
    for i,node in enumerate(nodes):
        op,ins,out=node['op'],node['inputs'],node['out']
        source=slot[ins[0]] if ins[0] in slot else None
        if op in ('MatMul','Gemm'):
            n,m=weights[ins[1]]['shape']
            code=1 if op=='MatMul' else 2
            lines.append(f'{code} {source} 0 {n} {m}')
            lines.extend(str(_f32_bits(x)) for x in weights[ins[1]]['values'])
            if op=='Gemm':lines.extend(str(_f32_bits(x)) for x in weights[ins[2]]['values'])
        elif op=='Add':
            if ins[0] in weights or ins[1] in weights:
                dynamic=ins[1] if ins[0] in weights else ins[0]
                constant=ins[0] if ins[0] in weights else ins[1]
                n=len(weights[constant]['values'])
                lines.append(f'4 {slot[dynamic]} 0 {n} {n}')
                lines.extend(str(_f32_bits(x)) for x in weights[constant]['values'])
            else:
                # Every dynamic width is derived from previous screened nodes.
                # Get it from a parallel width registry, never the model claim.
                n=_widths(spec)[ins[0]]
                lines.append(f'3 {slot[ins[0]]} {slot[ins[1]]} {n} {n}')
        elif op in ('Relu','Identity'):
            n=_widths(spec)[ins[0]]
            lines.append(f'{5 if op=="Relu" else 6} {source} 0 {n} {n}')
        else:
            raise ValueError('unsupported instruction')
        slot[out]=i+1
    return ('\n'.join(lines)+'\n').encode('ascii')


def _widths(spec):
    widths={spec['input']:spec['input_width']}
    for node in spec['nodes']:
        op=node['op'];ins=node['inputs']
        widths[node['out']]=(spec['weights'][ins[1]]['shape'][1]
             if op in ('MatMul','Gemm') else widths[next(x for x in ins if x in widths)])
    return widths


def compare(model:bytes, points:list[list[str]], compiler='cc'):
    report={'schema':'pcs-native-fp32-differential-v0.11','status':'NOT_RUN',
            'lean_kernel_verification':'NOT_ESTABLISHED',
            'official_onnx_runtime_equivalence':'NOT_ESTABLISHED',
            'trusted_isolation':'NOT_ESTABLISHED'}
    try:
        spec=screen_onnx(model)
        _validate_point(spec,points)
        cc=shutil.which(compiler)
        if not cc:raise ValueError('C compiler unavailable')
        with tempfile.TemporaryDirectory(prefix='pcs-native-c-') as tmp:
            exe=Path(tmp)/('reference.exe' if os.name=='nt' else 'reference')
            env={k:v for k,v in os.environ.items() if k in ('PATH','SYSTEMROOT','WINDIR','TMP','TEMP')}
            build=subprocess.run([cc,'-std=c11','-O0','-fno-fast-math','-ffp-contract=off',
                     '-frounding-math','-fexcess-precision=standard',str(SOURCE),'-lm','-o',str(exe)],
                    cwd=tmp,env=env,capture_output=True,timeout=20,check=False)
            if build.returncode:raise ValueError('native compiler rejected fixed evaluator')
            digest=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
            mismatches=[];count=0
            for idx,point in enumerate(points):
                payload=_instruction_stream(spec,point)
                if len(payload)>100_000:raise ValueError('native input protocol budget')
                run=subprocess.run([str(exe)],input=payload,capture_output=True,
                                   cwd=tmp,env=env,timeout=4,check=False)
                if run.returncode or len(run.stdout)>256:
                    raise ValueError('native evaluator refused finite screened graph: '+str(run.returncode))
                native=run.stdout.decode('ascii','strict').strip().split(' ')
                if len(native)!=spec['output_width']:raise ValueError('native result shape')
                native_bits=[int(x,16) for x in native]
                reference=sequential_eval(spec,[from_bits(int(x,16)) for x in point])
                reference_bits=[round_bits(v) for v in reference]
                for j,(a,b) in enumerate(zip(native_bits,reference_bits)):
                    # Signed zero is intentionally omitted from the numeric
                    # value semantics, and -0 and +0 are equal only there.
                    if from_bits(a)!=from_bits(b):
                        mismatches.append({'sample':idx,'output':j,
                                           'native_bits':f'{a:08x}',
                                           'exact_bits':f'{b:08x}'})
                        if len(mismatches)>=12:break
                count+=1
                if len(mismatches)>=12:break
        return dict(report,status='AGREE_ON_TESTED_POINTS' if not mismatches else 'DISAGREEMENT',
                    model_sha256=hashlib.sha256(model).hexdigest(),
                    c_source_sha256=digest,checked_points=count,disagreements=mismatches,
                    scope='screened ONNX translated to fixed C operations; O0 no FMA, RN-even, binary32 on this CPU, finite values only; empirical comparison')
    except (ValueError,TypeError,OverflowError,ArithmeticError,MemoryError,OSError,
            subprocess.TimeoutExpired,StopIteration) as exc:
        return dict(report,reason=type(exc).__name__+': '+str(exc)[:160])


def main(argv=None):
    import argparse
    p=argparse.ArgumentParser(description='Optional fixed C CPU vs exact rational float32 differential check; research only')
    p.add_argument('model');p.add_argument('point_json',help='JSON array of arrays of exact 8-digit lowercase FP32 hex words')
    p.add_argument('--compiler',default='cc')
    args=p.parse_args(argv)
    try:
        model=Path(args.model).read_bytes()
        points=json.loads(Path(args.point_json).read_text())
        result=compare(model,points,compiler=args.compiler)
    except (OSError,UnicodeError,ValueError,json.JSONDecodeError) as exc:
        result={'status':'NOT_RUN','reason':type(exc).__name__}
    print(json.dumps(result,indent=2))
    return 0 if result['status']=='AGREE_ON_TESTED_POINTS' else 2

if __name__=='__main__':raise SystemExit(main())
