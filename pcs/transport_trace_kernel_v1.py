"""Fresh finite-data Lean proofs, composed with PCS's all-time matrix assurance."""
from __future__ import annotations

import csv
import io
import json
import os
import re
from pathlib import Path
import subprocess
import tempfile
import time

from . import transport_kernel_v1 as model_kernel
from . import scientific_workflow_v3 as workflow
from .canonical_json import canonicalize_jcs_bytes as encode
from .scientific_contracts_v1 import rational, rational_text

ROOT = Path(__file__).resolve().parents[1]
FORMAL = ROOT/'formal/real/PCSReal/TransportTrace.lean'
FORMAT = 'pcs-transport-trace-kernel-v1'
GENERAL = ['PCSReal.TransportTrace.'+s for s in (
    'bounded_recurrence_unique', 'check_sound', 'recorded_invariants',
    'adjacent_quadratic', 'cast_step', 'cast_evolve', 'real_trace_sound')]
LITERAL = ['PCSTransportTraceReplay.'+s for s in (
    'trace_checked', 'recorded_states_and_times', 'recorded_invariants',
    'adjacent_quadratic', 'recorded_real_states')]
NEGATIVE = 'PCSTransportTraceReplay.trace_rejected'


def sources():
    return {**model_kernel._source_files(), 'PCSReal/TransportTrace.lean': FORMAL.read_bytes(),
            'trace-receiver.py.txt': Path(__file__).read_bytes()}


def prepare(contract_raw: bytes, trajectory_raw: bytes) -> dict:
    contract = workflow.load_contract(contract_raw)
    if not isinstance(trajectory_raw, bytes) or len(trajectory_raw) > workflow.MAX_BYTES:
        raise ValueError('bounded trajectory bytes required')
    # Independently parse the current input, then compare every rational scalar.
    reader = csv.reader(io.StringIO(trajectory_raw.decode('utf-8'), newline=''))
    header = ['time_s', *(c['id'] for c in contract['cells'])]
    if next(reader, None) != header:
        raise ValueError('exact declared trajectory header required')
    rows = []
    for row in reader:
        if len(rows) >= contract['steps']+1 or len(row) != len(header):
            raise ValueError('bounded complete trajectory shape required')
        rows.append([rational(x, 'trace scalar') for x in row])
    if len(rows) != contract['steps']+1 or rows != workflow._observations(contract, trajectory_raw):
        raise ValueError('current-input trajectory parser handoff failed')
    return {'format': FORMAT, 'model': model_kernel.prepare(contract_raw),
        'trajectory_sha256': model_kernel.sha(trajectory_raw), 'steps': contract['steps'],
        'dt': rational_text(rational(contract['time_step'], 'time step')),
        'times': [rational_text(r[0]) for r in rows],
        'states': [[rational_text(x) for x in r[1:]] for r in rows]}


def validate(data):
    if not isinstance(data, dict) or set(data) != {'format','model','trajectory_sha256','steps','dt','times','states'} or data['format'] != FORMAT:
        raise ValueError('exact trace certificate fields required')
    model_kernel._validate_model(data['model'])
    if type(data['steps']) is not int or not 1 <= data['steps'] <= workflow.MAX_STEPS:
        raise ValueError('bounded trace step count required')
    if not isinstance(data['trajectory_sha256'], str) or re.fullmatch('[0-9a-f]{64}', data['trajectory_sha256']) is None:
        raise ValueError('exact trajectory digest required')
    n=len(data['model']['volumes']); count=data['steps']+1
    if (not isinstance(data['times'],list) or len(data['times'])!=count
            or not isinstance(data['states'],list) or len(data['states'])!=count
            or any(not isinstance(row,list) or len(row)!=n for row in data['states'])):
        raise ValueError('complete bounded trace dimensions required')
    for value in [data['dt'], *data['times'], *(x for row in data['states'] for x in row)]:
        if not isinstance(value,str) or rational_text(rational(value,'trace scalar'))!=value:
            raise ValueError('canonical rational trace literals required')


def render(data, *, negative=False):
    validate(data)
    n=len(data['model']['volumes']); steps=data['steps']
    vector=lambda xs:'['+', '.join(model_kernel._literal(x) for x in xs)+']'
    rows='['+', '.join(vector(row) for row in data['states'])+']'
    prefix=model_kernel._render(data['model']).decode().replace('import PCSReal.Transport\n','import PCSReal.TransportTrace\n',1)
    text=prefix+f'''
namespace PCSTransportTraceReplay
open PCSReal.Transport PCSTransportReplay
-- Exact trajectory bytes: {data['trajectory_sha256']}
def states (k : Nat) (i : Fin {n}) : ℚ := (({rows} : List (List ℚ)).getD k []).getD i.val 0
def times (k : Nat) : ℚ := ({vector(data['times'])} : List ℚ).getD k 0
def dt : ℚ := {model_kernel._literal(data['dt'])}
'''
    if negative:
        return (text+f'''theorem trace_rejected : PCSReal.TransportTrace.check matrix initial states times dt {steps} = false := by decide +kernel
end PCSTransportTraceReplay
#print axioms {NEGATIVE}
''').encode()
    text+=f'''theorem trace_checked : PCSReal.TransportTrace.check matrix initial states times dt {steps} = true := by
  simp only [PCSReal.TransportTrace.check, decide_eq_true_eq]
  exact ⟨by decide +kernel, by decide +kernel, by decide +kernel⟩
theorem recorded_states_and_times :
    (∀ k, k ≤ {steps} → ∀ i, states k i = evolve matrix initial k i) ∧
    (∀ k, k ≤ {steps} → times k = (k : ℚ) * dt) :=
  PCSReal.TransportTrace.check_sound trace_checked
theorem recorded_invariants (k : Nat) (hk : k ≤ {steps}) :
    amount volume (states k) = amount volume initial ∧
    (∀ i, lower ≤ states k i ∧ states k i ≤ upper) ∧
    quadratic volume (states k) ≤ quadratic volume initial :=
  PCSReal.TransportTrace.recorded_invariants (PCSReal.Transport.check_sound matrix_checked)
    initial lower upper initial_bounds states {steps} recorded_states_and_times.1 k hk
theorem adjacent_quadratic (k : Nat) (hk : k < {steps}) :
    quadratic volume (states (k + 1)) ≤ quadratic volume (states k) :=
  PCSReal.TransportTrace.adjacent_quadratic (PCSReal.Transport.check_sound matrix_checked)
    initial states {steps} recorded_states_and_times.1 k hk
theorem recorded_real_states (k : Nat) (hk : k ≤ {steps}) :
    ∀ i, ((states k i : ℚ) : ℝ) =
      evolve (fun i j => (matrix i j : ℝ)) (fun j => (initial j : ℝ)) k i :=
  PCSReal.TransportTrace.real_trace_sound trace_checked k hk
end PCSTransportTraceReplay
'''
    return (text+'\n'.join('#print axioms '+n for n in LITERAL)+'\n').encode()


def kernel_replay(data, *, timeout=120):
    if type(timeout) not in {int,float} or not 0 < timeout <= 180:
        raise ValueError('kernel stage timeout must lie within (0,180]')
    validate(data)
    started=time.monotonic();deadline=started+timeout
    def remaining():
        value=deadline-time.monotonic()
        if value<=0:raise subprocess.TimeoutExpired('trace kernel',timeout)
        return value
    frozen=sources();hashes={n:model_kernel.sha(raw) for n,raw in frozen.items()}
    proof=render(data)
    result={'kernel_checked':False,'negative_kernel_checked':False,'status':'UNAVAILABLE_OR_EXHAUSTED',
        'source_sha256':hashes,'proof_sha256':model_kernel.sha(proof),
        'trace_certificate_sha256':model_kernel.sha(encode(data)), 'kernel_theorems':{},'executions':[]}
    try:
        lean,env,version=model_kernel._environment(min(30,remaining()))
        with tempfile.TemporaryDirectory(prefix='pcs-trace-kernel-') as folder:
            private=Path(folder);(private/'PCSReal').mkdir()
            env['LEAN_PATH']=str(private)+os.pathsep+env['LEAN_PATH']
            for name,names in [('Transport',model_kernel.GENERAL_THEOREMS),('TransportTrace',GENERAL)]:
                path=private/'PCSReal'/(name+'.lean')
                path.write_bytes(frozen['PCSReal/'+name+'.lean']+('\n'+'\n'.join('#print axioms '+n for n in names)+'\n').encode())
                cmd=[lean,'-j1','-M2048','-D','Elab.async=false','--root='+str(private),'-o',str(path.with_suffix('.olean')),str(path)]
                p=subprocess.run(cmd,cwd=private,env=env,capture_output=True,text=True,timeout=remaining())
                result['executions'].append({'command':cmd,'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
                if p.returncode:return {**result,'status':'FORMAL_SOURCE_REJECTED'}
                result['kernel_theorems'].update(model_kernel._inventory(p.stdout,names))
            driver=private/'TraceReplay.lean';driver.write_bytes(proof)
            cmd=[lean,'-j1','-M2048','-D','Elab.async=false','--root='+str(private),str(driver)]
            p=subprocess.run(cmd,cwd=private,env=env,capture_output=True,text=True,timeout=remaining())
            result['executions'].append({'command':cmd,'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
            if p.returncode:
                driver.write_bytes(render(data,negative=True))
                neg=subprocess.run(cmd,cwd=private,env=env,capture_output=True,text=True,timeout=remaining())
                result['executions'].append({'command':cmd,'returncode':neg.returncode,'stdout':neg.stdout,'stderr':neg.stderr})
                if neg.returncode==0:
                    names=model_kernel._inventory(neg.stdout,model_kernel.REPLAY_THEOREMS+[NEGATIVE])
                    result.update(status='TRACE_FALSIFIED',negative_kernel_checked=True,
                        negative_kernel_theorems=names,negative_proof_sha256=model_kernel.sha(render(data,negative=True)))
                else:result['status']='TRACE_REJECTED'
            else:
                result['kernel_theorems'].update(model_kernel._inventory(p.stdout,model_kernel.REPLAY_THEOREMS+LITERAL))
                result.update(kernel_checked=True,status='KERNEL_CHECKED',lean_version=version)
        if hashes!={n:model_kernel.sha(raw) for n,raw in sources().items()}:
            raise ValueError('receiving sources changed during trace proof replay')
        return {**result,'elapsed_seconds':round(time.monotonic()-started,6)}
    except (OSError,subprocess.SubprocessError,ValueError) as e:
        return {**result,'kernel_checked':False,'negative_kernel_checked':False,
            'status':'UNAVAILABLE_OR_EXHAUSTED','error':f'{type(e).__name__}: {e}'}


def replay(contract_raw, trajectory_raw, *, timeout=120):
    rejected={'format':FORMAT,'accepted':False,'bounded_trajectory_kernel_supported':False,
        'bounded_trajectory_supported':False,'all_time_model_supported':False,
        'scientific_acceptance':False,'pcs_authority':False,
        'implementation_correspondence':'OPEN','continuum_accuracy':'OPEN','empirical_validity':'OPEN'}
    try:
        data=prepare(contract_raw,trajectory_raw)
        base=model_kernel.replay(contract_raw,trajectory_raw,timeout=timeout)
        if (base.get('all_time_model_supported') is not True
                or base.get('model')!=data['model'] or base.get('contract_sha256')!=model_kernel.sha(contract_raw)
                or base.get('bounded_replay',{}).get('data_sha256')!=data['trajectory_sha256']):
            return {**rejected,'model_replay':base,'errors':['model/data proof handoff rejected']}
        kernel=kernel_replay(data,timeout=timeout)
        support=kernel['kernel_checked'] is True
        return {**rejected,'accepted':base['accepted'] is True and support,
            'all_time_model_supported':True,'bounded_trajectory_kernel_supported':support,
            'bounded_trajectory_supported':base['bounded_trajectory_supported'] is True and support,
            'acceptance_scope':'DECLARED_MATRIX_AND_FINITE_LITERAL_TRACE',
            'contract_sha256':model_kernel.sha(contract_raw),'trajectory_sha256':data['trajectory_sha256'],
            'trace_certificate':data,'kernel':kernel,'model_replay':base,
            'obligations':[{'id':'finite_trace_recurrence_and_times','status':'KERNEL_SUPPORTED' if support else 'OPEN'},
                *[{'id':n,'status':'OPEN'} for n in ['implementation_correspondence','continuum_accuracy','empirical_validity']]]}
    except (ValueError,KeyError,TypeError,UnicodeError,OSError,RecursionError) as e:
        return {**rejected,'errors':[f'{type(e).__name__}: {e}']}


def replay_bundle(bundle,public_key_path,*,expected_fingerprint,lean_authority_path=None,timeout=120):
    # Snapshot once before both existing authority replay and literal extraction.
    with Path(bundle).open('rb') as f:raw=f.read(model_kernel.MAX_BUNDLE_BYTES+1)
    if len(raw)>model_kernel.MAX_BUNDLE_BYTES:raise ValueError('bounded signed bundle required')
    with tempfile.TemporaryDirectory(prefix='pcs-trace-signed-') as folder:
        snapshot=Path(folder)/'input.pcs.zip';snapshot.write_bytes(raw)
        existing=model_kernel.replay_bundle(snapshot,public_key_path,expected_fingerprint=expected_fingerprint,
            lean_authority_path=lean_authority_path,timeout=timeout)
        if existing.get('accepted') is not True:
            return {**existing,'format':FORMAT,'accepted':False,'bounded_trajectory_kernel_supported':False,
                    'trace_signed_handoff':'EXISTING_WORKFLOW_REJECTED'}
        package=workflow.load_package_zip_v06(snapshot)
        cert=workflow._json(package['certificate_bytes'])
        artifacts={a['source_path']:package['package_files'][a['path']] for a in cert['artifacts']}
        contract_raw=artifacts['contract.json'];contract=workflow.load_contract(contract_raw)
        trajectory_raw=artifacts[contract['data_path']]
        if (existing.get('bundle_sha256')!=model_kernel.sha(raw)
                or existing.get('contract_sha256')!=model_kernel.sha(contract_raw)
                or existing['existing_workflow']['domain_replay']['data_sha256']!=model_kernel.sha(trajectory_raw)):
            raise ValueError('signed byte identity handoff rejected')
        result=replay(contract_raw,trajectory_raw,timeout=timeout)
        return {**result,'pcs_package_valid':True,'bundle_sha256':model_kernel.sha(raw),
            'existing_signed_replay':existing,'acceptance_scope':'SIGNED_PACKAGE_MATRIX_AND_FINITE_LITERAL_TRACE'}


def export(output,result,contract_raw=None,trajectory_raw=None):
    for raw,field in [(contract_raw,'contract_sha256'),(trajectory_raw,'trajectory_sha256')]:
        if raw is not None and model_kernel.sha(raw)!=result.get(field):
            raise ValueError('exported source bytes differ from verified input')
    if data:=result.get('trace_certificate'):
        if (result['kernel']['trace_certificate_sha256']!=model_kernel.sha(encode(data))
                or result['kernel']['proof_sha256']!=model_kernel.sha(render(data))
                or result.get('contract_sha256')!=data['model']['contract_sha256']
                or result.get('trajectory_sha256')!=data['trajectory_sha256']):
            raise ValueError('exported certificate differs from verified proof')
    frozen=sources() if result.get('trace_certificate') else {}
    if frozen and {n:model_kernel.sha(raw) for n,raw in frozen.items()}!=result['kernel']['source_sha256']:
        raise ValueError('source substitution before trace evidence export')
    output.mkdir(parents=True,exist_ok=False)
    (output/'report.json').write_bytes(encode(result))
    for name,raw in [('contract.json',contract_raw),('trajectory.csv',trajectory_raw)]:
        if raw is not None:(output/name).write_bytes(raw)
    if data:=result.get('trace_certificate'):
        (output/'trace-certificate.json').write_bytes(encode(data))
        (output/'TraceReplay.lean').write_bytes(render(data))
        if result['kernel']['negative_kernel_checked']:
            (output/'TraceRejected.lean').write_bytes(render(data,negative=True))
        for name,raw in frozen.items():
            p=output/'receiving-source'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
    (output/'SHA256.json').write_bytes(encode({str(p.relative_to(output)):model_kernel.sha(p.read_bytes())
        for p in sorted(output.rglob('*')) if p.is_file()}))


def command(args):
    try:
        def read(path):
            with Path(path).open('rb') as f:raw=f.read(workflow.MAX_BYTES+1)
            if len(raw)>workflow.MAX_BYTES:raise ValueError('input byte bound exceeded')
            return raw
        if args.bundle:
            if args.trajectory or not args.public_key or not args.fingerprint:
                raise ValueError('signed replay requires key and fingerprint, without external trajectory')
            result=replay_bundle(args.bundle,args.public_key,expected_fingerprint=args.fingerprint,
                lean_authority_path=args.lean_authority,timeout=args.timeout)
            contract_raw=trajectory_raw=None
        else:
            if not args.trajectory or args.public_key or args.fingerprint or args.lean_authority:
                raise ValueError('raw replay requires trajectory, without signing options')
            contract_raw=read(args.contract);trajectory_raw=read(args.trajectory)
            result=replay(contract_raw,trajectory_raw,timeout=args.timeout)
        export(Path(args.output),result,contract_raw,trajectory_raw)
        print(json.dumps({'accepted':result['accepted'],'bounded_trajectory_kernel_supported':result['bounded_trajectory_kernel_supported'],
            'scientific_acceptance':False,'output':str(Path(args.output).resolve())}))
        return 0 if result['accepted'] else 1
    except (ValueError,OSError,KeyError,TypeError,UnicodeError) as e:
        print(json.dumps({'accepted':False,'scientific_acceptance':False,'error':str(e)}));return 1


def register(subparsers):
    p=subparsers.add_parser('transport-trace-kernel-v1',help='freshly kernel-check every recorded transport state and time')
    group=p.add_mutually_exclusive_group(required=True)
    group.add_argument('--contract');group.add_argument('--bundle')
    p.add_argument('--trajectory');p.add_argument('--public-key');p.add_argument('--fingerprint');p.add_argument('--lean-authority')
    p.add_argument('--timeout',type=float,default=120,help='wall budget per kernel stage, at most 180 seconds')
    p.add_argument('--output',required=True);p.set_defaults(func=command)
