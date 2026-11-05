"""Fresh ordinary-kernel regression and sharp sensitivity certificates.

Optimizers are untrusted proposers. Mathematical support concerns the exact
parsed finite arrays; physical validity and measurement precision remain OPEN.
"""
from __future__ import annotations

import csv
import io
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time

from .canonical_json import canonicalize_jcs_bytes as encode
from .scientific_contracts_v1 import rational, rational_text
from . import transport_kernel_v1 as infrastructure

ROOT = Path(__file__).resolve().parents[1]
FORMAL = ROOT/'formal/real/PCSReal/Calibration.lean'
FORMAT = 'pcs-calibration-kernel-v1'
GENERAL = ['PCSReal.Calibration.'+s for s in (
    'normal_orthogonal','loss_decomposition','global_minimum','model_exclusion',
    'reproduction_prediction','dual_prediction','response_perturbation_bound',
    'sharp_perturbation_attained','sharp_radius_iff','physical_enclosure',
    'fit_check_sound','cast_loss','dual_check_sound','dual_gain_lower_bound',
    'minimax_weights_optimal','minimax_radius_lower_bound','minimax_check_sound',
    'any_estimator_radius_lower_bound','minimax_over_all_estimators_iff','uniform_error_exclusion')]
MAX_BYTES = 2*1024*1024
NEGATIVE = 'PCSCalibrationRejected.certificate_rejected'


def sha(raw):
    return infrastructure.sha(raw)


def inventory(output,names):
    # Lean wraps long axiom messages. Normalize only complete quoted reports;
    # the existing strict validator still rejects duplicates, extra identities,
    # missing targets, and every unapproved axiom.
    reports=re.findall(r"'[^'\r\n]+' (?:depends on axioms: \[[^\]]*\]|does not depend on any axioms)",output)
    return infrastructure._inventory('\n'.join(re.sub(r'\s+',' ',r) for r in reports),names)


def sources():
    names = ['pcs/calibration_kernel_v1.py','pcs/transport_kernel_v1.py',
             'pcs/scientific_contracts_v1.py','pcs/canonical_json.py']
    return {'PCSReal/Calibration.lean':FORMAL.read_bytes(),
            **{n:(ROOT/n).read_bytes() for n in names}}


def load_json(raw):
    if not isinstance(raw,bytes) or len(raw)>MAX_BYTES:
        raise ValueError('bounded JSON bytes required')
    def pairs(xs):
        d={}
        for k,v in xs:
            if k in d:raise ValueError('duplicate JSON key')
            d[k]=v
        return d
    return json.loads(raw,object_pairs_hook=pairs,
        parse_constant=lambda _:(_ for _ in ()).throw(ValueError('finite JSON required')))


def exact(d,fields):
    if not isinstance(d,dict) or set(d)!=set(fields):
        raise ValueError('exact declared object fields required')


def scalar(value):
    q=rational(value,'calibration scalar')
    if rational_text(q)!=value:raise ValueError('canonical rational string required')
    return q


def prepare(data_raw,contract_raw,certificate_raw):
    if not isinstance(data_raw,bytes) or len(data_raw)>MAX_BYTES:
        raise ValueError('bounded CSV required')
    reader=csv.reader(io.StringIO(data_raw.decode('utf-8'),newline=''))
    if next(reader,None)!=['x','y']:raise ValueError('exact x,y CSV header required')
    data=[]
    for row in reader:
        if len(row)!=2 or len(data)>=64:raise ValueError('complete bounded calibration rows required')
        data.append([rational_text(rational(v,'data scalar')) for v in row])
    if not 2<=len(data)<=64:raise ValueError('2..64 data rows required')
    contract=load_json(contract_raw);cert=load_json(certificate_raw)
    exact(contract,{'format','data_sha256','models'})
    exact(cert,{'format','contract_sha256','models'})
    if contract['format']!=FORMAT or cert['format']!=FORMAT:
        raise ValueError('unsupported calibration format')
    if contract['data_sha256']!=sha(data_raw) or cert['contract_sha256']!=sha(contract_raw):
        raise ValueError('current data/contract identity mismatch')
    if (not isinstance(contract['models'],list) or not 1<=len(contract['models'])<=6
            or not isinstance(cert['models'],list) or len(cert['models'])!=len(contract['models'])):
        raise ValueError('1..6 complete model certificates required')
    models=[]
    for spec,witness in zip(contract['models'],cert['models']):
        exact(spec,{'degree','fit_rows','queries'})
        exact(witness,{'coefficients','sse','queries'})
        degree=spec['degree'];rows=spec['fit_rows'];queries=spec['queries']
        if type(degree) is not int or not 1<=degree<=3:raise ValueError('degree 1..3 required')
        if (not isinstance(rows,list) or not degree+1<=len(rows)<=len(data)
                or any(type(i) is not int or not 0<=i<len(data) for i in rows)
                or rows!=sorted(set(rows))):raise ValueError('distinct sorted declared fitting rows required')
        if (not isinstance(queries,list) or not 0<=len(queries)<=8
                or any(not isinstance(q,str) for q in queries)):
            raise ValueError('bounded query list required')
        for q in queries:scalar(q)
        if not isinstance(witness['coefficients'],list) or len(witness['coefficients'])!=degree+1:
            raise ValueError('complete polynomial coefficients required')
        for b in witness['coefficients']:scalar(b)
        if scalar(witness['sse'])<0:raise ValueError('nonnegative claimed SSE required')
        if not isinstance(witness['queries'],list) or len(witness['queries'])!=len(queries):
            raise ValueError('complete dual query witnesses required')
        for w in witness['queries']:
            exact(w,{'weights','dual','gain','minimax'})
            if (not isinstance(w['weights'],list) or len(w['weights'])!=len(rows)
                    or not isinstance(w['dual'],list) or len(w['dual'])!=degree+1):
                raise ValueError('complete bounded dual dimensions required')
            for v in w['weights']+w['dual']:scalar(v)
            if scalar(w['gain'])<0:raise ValueError('nonnegative sensitivity gain required')
            mm=w['minimax'];exact(mm,{'weights','dual','gain'})
            if (not isinstance(mm['weights'],list) or len(mm['weights'])!=len(rows)
                    or not isinstance(mm['dual'],list) or len(mm['dual'])!=degree+1):
                raise ValueError('complete minimax dimensions required')
            for v in mm['weights']+mm['dual']:scalar(v)
            if scalar(mm['gain'])<0:raise ValueError('nonnegative minimax gain required')
        models.append({'degree':degree,'data':[data[i] for i in rows],
                       'query_x':queries,**witness})
    return {'format':FORMAT,'data_sha256':sha(data_raw),'contract_sha256':sha(contract_raw),
            'certificate_sha256':sha(certificate_raw),'models':models}


def render(prepared):
    # This low-level function consumes only prepare() output; never submitted Lean.
    text='import PCSReal.Calibration\nset_option autoImplicit false\nset_option format.width 1000000\nopen Finset PCSReal.Calibration\n'
    names=[]
    vec=lambda xs:'['+', '.join(infrastructure._literal(v) for v in xs)+']'
    for k,m in enumerate(prepared['models']):
        n=len(m['data']);p=m['degree']+1;ns=f'PCSCalibrationReplay.M{k}'
        xs=[r[0] for r in m['data']];ys=[r[1] for r in m['data']]
        text+=f'''\nnamespace {ns}
def abscissa (i : Fin {n}) : ℚ := ({vec(xs)} : List ℚ).getD i.val 0
def x (i : Fin {n}) (j : Fin {p}) : ℚ := abscissa i ^ j.val
def y (i : Fin {n}) : ℚ := ({vec(ys)} : List ℚ).getD i.val 0
def b (j : Fin {p}) : ℚ := ({vec(m['coefficients'])} : List ℚ).getD j.val 0
def xr (i : Fin {n}) (j : Fin {p}) : ℝ := (x i j : ℝ)
def yr (i : Fin {n}) : ℝ := (y i : ℝ)
def br (j : Fin {p}) : ℝ := (b j : ℝ)
theorem normal_checked : fitCheck x y b = true := by decide +kernel
theorem residual_checked : loss x y b = {infrastructure._literal(m['sse'])} := by decide +kernel
theorem global_optimum : ∀ c : Fin {p} → ℝ,
    ({infrastructure._literal(m['sse'])} : ℝ) ≤ loss xr yr c := by
  have hs : loss xr yr br = ({infrastructure._literal(m['sse'])} : ℝ) := by
    calc
      loss xr yr br = ((loss x y b : ℚ) : ℝ) := (cast_loss x y b).symm
      _ = ({infrastructure._literal(m['sse'])} : ℝ) := by
        simpa only [Rat.cast_div, Rat.cast_intCast, Rat.cast_ofNat, Rat.cast_neg]
          using congrArg (fun a : ℚ => (a : ℝ)) residual_checked
  simpa only [hs] using global_minimum xr yr br (fit_check_sound normal_checked)
theorem excludes_every_better_model (threshold : ℝ)
    (h : threshold < ({infrastructure._literal(m['sse'])} : ℝ)) :
    ∀ c : Fin {p} → ℝ, threshold < loss xr yr c := by
  intro c
  exact h.trans_le (global_optimum c)
theorem uniform_error_exclusion (ε : ℝ) (he : 0 ≤ ε)
    (hgap : ({n} : ℝ) * ε ^ 2 < ({infrastructure._literal(m['sse'])} : ℝ)) :
    ¬ (∃ c : Fin {p} → ℝ, ∀ i, |yr i - prediction xr c i| ≤ ε) :=
  PCSReal.Calibration.uniform_error_exclusion xr yr ({infrastructure._literal(m['sse'])} : ℝ) ε
    global_optimum he (by simpa using hgap)
'''
        names.extend(ns+'.'+s for s in ['normal_checked','residual_checked','global_optimum',
            'excludes_every_better_model','uniform_error_exclusion'])
        for j,(query,w) in enumerate(zip(m['query_x'],m['queries'])):
            text+=f'''namespace Q{j}
def q (j : Fin {p}) : ℚ := ({infrastructure._literal(query)} : ℚ) ^ j.val
def w (i : Fin {n}) : ℚ := ({vec(w['weights'])} : List ℚ).getD i.val 0
def d (j : Fin {p}) : ℚ := ({vec(w['dual'])} : List ℚ).getD j.val 0
def wr (i : Fin {n}) : ℝ := (w i : ℝ)
def qr (j : Fin {p}) : ℝ := (q j : ℝ)
theorem dual_checked : dualCheck x w q d = true := by decide +kernel
theorem gain_checked : (∑ i, |w i|) = ({infrastructure._literal(w['gain'])} : ℚ) := by decide +kernel
theorem real_gain : (∑ i, |wr i|) = ({infrastructure._literal(w['gain'])} : ℝ) := by
  have h := congrArg (fun a : ℚ => (a : ℝ)) gain_checked
  simpa only [wr, Rat.cast_sum, Rat.cast_abs, Rat.cast_div, Rat.cast_intCast,
    Rat.cast_ofNat, Rat.cast_neg] using h
theorem fitted_query : dot wr yr = dot qr br :=
  dual_prediction xr yr wr qr br (fun j => (d j : ℝ))
    (fit_check_sound normal_checked) (dual_check_sound dual_checked).1
    (dual_check_sound dual_checked).2
theorem sharp_radius (ε radius : ℝ) (he : 0 ≤ ε) :
    (∀ z : Fin {n} → ℝ, (∀ i, |z i - yr i| ≤ ε) → |dot wr z - dot wr yr| ≤ radius) ↔
      ε * ({infrastructure._literal(w['gain'])} : ℝ) ≤ radius := by
  simpa only [real_gain] using sharp_radius_iff wr yr ε radius he
theorem conditional_physical_enclosure (truth : Fin {p} → ℝ) (ε : ℝ)
    (hm : ∀ i, |yr i - prediction xr truth i| ≤ ε) :
    |dot wr yr - dot qr truth| ≤ ε * ({infrastructure._literal(w['gain'])} : ℝ) := by
  simpa only [real_gain] using physical_enclosure xr yr wr qr truth ε
    (dual_check_sound dual_checked).1 hm
end Q{j}
'''
            names.extend(ns+f'.Q{j}.'+s for s in ['dual_checked','gain_checked','real_gain','fitted_query','sharp_radius','conditional_physical_enclosure'])
            mm=w['minimax']
            text+=f'''namespace Q{j}.Minimax
def w (i : Fin {n}) : ℚ := ({vec(mm['weights'])} : List ℚ).getD i.val 0
def a (j : Fin {p}) : ℚ := ({vec(mm['dual'])} : List ℚ).getD j.val 0
def wr (i : Fin {n}) : ℝ := (w i : ℝ)
def ar (j : Fin {p}) : ℝ := (a j : ℝ)
theorem optimality_checked : minimaxCheck x w Q{j}.q a {infrastructure._literal(mm['gain'])} = true := by decide +kernel
theorem gain_checked : (∑ i, |w i|) = ({infrastructure._literal(mm['gain'])} : ℚ) := by decide +kernel
theorem real_gain : (∑ i, |wr i|) = ({infrastructure._literal(mm['gain'])} : ℝ) := by
  have h := congrArg (fun a : ℚ => (a : ℝ)) gain_checked
  simpa only [wr, Rat.cast_sum, Rat.cast_abs, Rat.cast_div, Rat.cast_intCast,
    Rat.cast_ofNat, Rat.cast_neg] using h
theorem globally_minimal_gain (v : Fin {n} → ℝ) (hv : Reproduces xr v Q{j}.qr) :
    ({infrastructure._literal(mm['gain'])} : ℝ) ≤ ∑ i, |v i| := by
  have h := minimax_check_sound optimality_checked
  have hm := minimax_weights_optimal xr wr Q{j}.qr ar h.2.1 h.2.2 v hv
  simpa only [real_gain] using hm
theorem sharp_radius (ε radius : ℝ) (he : 0 ≤ ε) :
    (∀ z : Fin {n} → ℝ, (∀ i, |z i - yr i| ≤ ε) → |dot wr z - dot wr yr| ≤ radius) ↔
      ε * ({infrastructure._literal(mm['gain'])} : ℝ) ≤ radius := by
  simpa only [real_gain] using sharp_radius_iff wr yr ε radius he
theorem no_reproducing_estimator_has_smaller_radius (ε radius : ℝ) (he : 0 ≤ ε)
    (v : Fin {n} → ℝ) (hv : Reproduces xr v Q{j}.qr)
    (hr : ∀ z, (∀ i, |z i - yr i| ≤ ε) → |dot v z - dot v yr| ≤ radius) :
    ε * ({infrastructure._literal(mm['gain'])} : ℝ) ≤ radius := by
  have h := minimax_check_sound optimality_checked
  have hm := minimax_radius_lower_bound xr yr wr Q{j}.qr ar h.2.1 h.2.2 ε radius he v hv hr
  simpa only [real_gain] using hm
theorem conditional_physical_enclosure (truth : Fin {p} → ℝ) (ε : ℝ)
    (hm : ∀ i, |yr i - prediction xr truth i| ≤ ε) :
    |dot wr yr - dot Q{j}.qr truth| ≤ ε * ({infrastructure._literal(mm['gain'])} : ℝ) := by
  simpa only [real_gain] using physical_enclosure xr yr wr Q{j}.qr truth ε
    (minimax_check_sound optimality_checked).1 hm
theorem uniform_minimax_over_all_prediction_functions (ε radius : ℝ) (he : 0 ≤ ε) :
    (∃ estimator : (Fin {n} → ℝ) → ℝ,
      ∀ truth observed, (∀ i, |observed i - prediction xr truth i| ≤ ε) →
        |estimator observed - dot Q{j}.qr truth| ≤ radius) ↔
      ε * ({infrastructure._literal(mm['gain'])} : ℝ) ≤ radius := by
  have h := minimax_check_sound optimality_checked
  simpa only [real_gain] using
    minimax_over_all_estimators_iff xr wr Q{j}.qr ar h.1 h.2.1 h.2.2 ε radius he
end Q{j}.Minimax
'''
            names.extend(ns+f'.Q{j}.Minimax.'+s for s in ['optimality_checked','gain_checked','real_gain',
                'globally_minimal_gain','sharp_radius','no_reproducing_estimator_has_smaller_radius',
                'conditional_physical_enclosure','uniform_minimax_over_all_prediction_functions'])
        text+=f'end {ns}\n'
    text+='\n'+'\n'.join('#print axioms '+n for n in names)+'\n'
    return text.encode(),names


def render_rejection(prepared):
    """A separate ordinary-kernel proof of falsity of the finite witness checks."""
    text='import PCSReal.Calibration\nset_option autoImplicit false\nopen Finset PCSReal.Calibration\nnamespace PCSCalibrationRejected\n'
    checks=[]
    vec=lambda xs:'['+', '.join(infrastructure._literal(v) for v in xs)+']'
    for k,m in enumerate(prepared['models']):
        n=len(m['data']);p=m['degree']+1
        text+=f'''def u{k} (i : Fin {n}) : ℚ := ({vec([r[0] for r in m['data']])} : List ℚ).getD i.val 0
def x{k} (i : Fin {n}) (j : Fin {p}) : ℚ := u{k} i ^ j.val
def y{k} (i : Fin {n}) : ℚ := ({vec([r[1] for r in m['data']])} : List ℚ).getD i.val 0
def b{k} (j : Fin {p}) : ℚ := ({vec(m['coefficients'])} : List ℚ).getD j.val 0
'''
        checks.extend([f'(fitCheck x{k} y{k} b{k} = true)',
                       f'(loss x{k} y{k} b{k} = {infrastructure._literal(m["sse"])})'])
        for j,(qx,w) in enumerate(zip(m['query_x'],m['queries'])):
            mm=w['minimax'];tag=f'{k}_{j}'
            text+=f'''def q{tag} (j : Fin {p}) : ℚ := ({infrastructure._literal(qx)} : ℚ) ^ j.val
def w{tag} (i : Fin {n}) : ℚ := ({vec(w['weights'])} : List ℚ).getD i.val 0
def d{tag} (j : Fin {p}) : ℚ := ({vec(w['dual'])} : List ℚ).getD j.val 0
def m{tag} (i : Fin {n}) : ℚ := ({vec(mm['weights'])} : List ℚ).getD i.val 0
def a{tag} (j : Fin {p}) : ℚ := ({vec(mm['dual'])} : List ℚ).getD j.val 0
'''
            checks.extend([f'(dualCheck x{k} w{tag} q{tag} d{tag} = true)',
                f'((∑ i, |w{tag} i|) = {infrastructure._literal(w["gain"])})',
                f'(minimaxCheck x{k} m{tag} q{tag} a{tag} {infrastructure._literal(mm["gain"])} = true)'])
    text+='def allChecks : Bool := decide ('+' ∧ '.join(checks)+')\n'
    text+='theorem certificate_rejected : allChecks = false := by decide +kernel\n'
    text+='end PCSCalibrationRejected\n#print axioms '+NEGATIVE+'\n'
    return text.encode()


def kernel_replay(prepared,*,timeout=180):
    if type(timeout) not in {int,float} or not 0<timeout<=300:
        raise ValueError('kernel budget must lie in (0,300] seconds')
    frozen=sources();hashes={n:sha(b) for n,b in frozen.items()};proof,names=render(prepared)
    started=time.monotonic();deadline=started+timeout
    result={'status':'UNAVAILABLE_OR_EXHAUSTED','kernel_checked':False,'negative_kernel_checked':False,'source_sha256':hashes,
            'proof_sha256':sha(proof),'prepared_sha256':sha(encode(prepared)),
            'kernel_theorems':{},'executions':[]}
    def remaining():
        left=deadline-time.monotonic()
        if left<=0:raise subprocess.TimeoutExpired('calibration replay',timeout)
        return left
    try:
        lean,env,version=infrastructure._environment(min(30,remaining()))
        with tempfile.TemporaryDirectory(prefix='pcs-calibration-') as folder:
            private=Path(folder);(private/'PCSReal').mkdir()
            env['LEAN_PATH']=str(private)+os.pathsep+env['LEAN_PATH']
            source=private/'PCSReal/Calibration.lean'
            source.write_bytes(frozen['PCSReal/Calibration.lean']+('\n'+'\n'.join('#print axioms '+n for n in GENERAL)+'\n').encode())
            driver=private/'Replay.lean';driver.write_bytes(proof)
            for path,theorem_names in [(source,GENERAL),(driver,names)]:
                command=[lean,'-j1','-M2048','-D','Elab.async=false','--root='+str(private)]
                if path==source:command+=['-o',str(path.with_suffix('.olean'))]
                command+=[str(path)]
                p=subprocess.run(command,cwd=private,env=env,capture_output=True,text=True,timeout=remaining())
                result['executions'].append({'command':command,'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
                if p.returncode:
                    result['status']='CERTIFICATE_OR_SOURCE_REJECTED'
                    if path==source:return result
                    negative=private/'Rejected.lean';negative.write_bytes(render_rejection(prepared))
                    command=[lean,'-j1','-M2048','-D','Elab.async=false','--root='+str(private),str(negative)]
                    neg=subprocess.run(command,cwd=private,env=env,capture_output=True,text=True,timeout=remaining())
                    result['executions'].append({'command':command,'returncode':neg.returncode,'stdout':neg.stdout,'stderr':neg.stderr})
                    if neg.returncode==0:
                        result.update(status='CERTIFICATE_FALSIFIED',negative_kernel_checked=True,
                            negative_kernel_theorems=inventory(neg.stdout,[NEGATIVE]),
                            negative_proof_sha256=sha(render_rejection(prepared)))
                    break
                result['kernel_theorems'].update(inventory(p.stdout,theorem_names))
            else:
                result.update(status='KERNEL_CHECKED',kernel_checked=True)
        if hashes!={n:sha(b) for n,b in sources().items()}:
            raise ValueError('receiving sources changed during calibration replay')
        return {**result,'lean_version':version,'elapsed_seconds':round(time.monotonic()-started,6)}
    except (OSError,subprocess.SubprocessError,ValueError) as e:
        return {**result,'kernel_checked':False,'negative_kernel_checked':False,
                'status':'UNAVAILABLE_OR_EXHAUSTED','error':str(e)}


def replay(data_raw,contract_raw,certificate_raw,*,timeout=180):
    base={'format':FORMAT,'accepted':False,'mathematical_support':False,
          'acceptance_scope':'FINITE_ARRAY_OLS_AND_POINTWISE_LINEAR_MINIMAX',
          'scientific_acceptance':False,'pcs_authority':False,
          'implementation_correspondence':'OPEN','physical_model_validity':'OPEN',
          'measurement_error_bound':'ASSUMED_SCENARIO_ONLY','external_domain_review':'NOT_OBTAINED'}
    try:
        prepared=prepare(data_raw,contract_raw,certificate_raw)
        kernel=kernel_replay(prepared,timeout=timeout)
        supported=kernel['kernel_checked'] is True
        queries=sum(len(m['queries']) for m in prepared['models'])
        query_status=('KERNEL_SUPPORTED' if supported else 'OPEN') if queries else 'NOT_REQUESTED'
        return {**base,'accepted':supported,'mathematical_support':supported,'prepared':prepared,'kernel':kernel,
            'claims':[{'kind':'global_real_least_squares_optimality','models':len(prepared['models']),
                       'status':'KERNEL_SUPPORTED' if supported else 'OPEN'},
                      {'kind':'sharp_response_perturbation_radius','queries':queries,'status':query_status},
                      {'kind':'globally_minimax_polynomial_reproducing_linear_estimator',
                       'queries':queries,'status':query_status},
                      {'kind':'uniform_minimax_over_all_prediction_functions',
                       'queries':queries,'status':query_status}]+
                [{'kind':kind,'status':'OPEN'} for kind in
                 ['implementation_correspondence','physical_model_validity','empirical_coverage']]}
    except (ValueError,KeyError,TypeError,UnicodeError,OSError,RecursionError) as e:
        return {**base,'errors':[f'{type(e).__name__}: {e}']}


def export(output,result,data_raw,contract_raw,certificate_raw):
    prepared=prepare(data_raw,contract_raw,certificate_raw)
    if result.get('prepared')!=prepared:
        if result.get('prepared') or result.get('accepted'):raise ValueError('input/proof export substitution')
        frozen={};proof=None
    else:
        frozen=sources();proof,_=render(prepared);k=result['kernel']
        if (k['source_sha256']!={n:sha(b) for n,b in frozen.items()}
                or k['prepared_sha256']!=sha(encode(prepared)) or k['proof_sha256']!=sha(proof)):
            raise ValueError('source/certificate/proof export substitution')
        if k['negative_kernel_checked'] and k['negative_proof_sha256']!=sha(render_rejection(prepared)):
            raise ValueError('negative proof export substitution')
    output.mkdir(parents=True,exist_ok=False)
    for name,raw in [('report.json',encode(result)),('data.csv',data_raw),('contract.json',contract_raw),('certificate.json',certificate_raw)]:
        (output/name).write_bytes(raw)
    if proof:
        (output/'Replay.lean').write_bytes(proof)
        if result['kernel']['negative_kernel_checked']:
            (output/'Rejected.lean').write_bytes(render_rejection(prepared))
        for name,raw in frozen.items():
            p=output/'receiving-source'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
    (output/'SHA256.json').write_bytes(encode({str(p.relative_to(output)):sha(p.read_bytes())
        for p in sorted(output.rglob('*')) if p.is_file()}))


def command(args):
    try:
        def read(path):
            with Path(path).open('rb') as f:raw=f.read(MAX_BYTES+1)
            if len(raw)>MAX_BYTES:raise ValueError('input size exceeded')
            return raw
        data=read(args.data);contract=read(args.contract);cert=read(args.certificate)
        result=replay(data,contract,cert,timeout=args.timeout)
        if result.get('prepared'):export(Path(args.output),result,data,contract,cert)
        else:
            out=Path(args.output);out.mkdir(parents=True,exist_ok=False)
            (out/'report.json').write_bytes(encode(result))
        print(json.dumps({'accepted':result['accepted'],'scientific_acceptance':False,'output':str(Path(args.output).resolve())}))
        return 0 if result['accepted'] else 1
    except (ValueError,OSError,KeyError,TypeError,UnicodeError) as e:
        print(json.dumps({'accepted':False,'error':str(e)}));return 1


def register(subparsers):
    p=subparsers.add_parser('calibration-kernel-v1',help='kernel-check regression and sharp sensitivity witnesses')
    p.add_argument('--data',required=True);p.add_argument('--contract',required=True)
    p.add_argument('--certificate',required=True);p.add_argument('--output',required=True)
    p.add_argument('--timeout',type=float,default=180);p.set_defaults(func=command)
