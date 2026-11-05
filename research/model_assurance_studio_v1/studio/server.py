"""Local-only FastAPI upload surface. Raw upload bodies are processed in memory.

No multipart temp spooling, archive extraction, model deserialization, or code execution.
Use only on a trusted local machine. Never bind this development server publicly.
"""
from __future__ import annotations
import json
from pathlib import Path
from urllib.parse import unquote, urlsplit
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from .engine import analyze, parse_policy, IntakeError, MAX_FILE, VERSION

ROOT = Path(__file__).resolve().parent
app = FastAPI(title='PCS Model Assurance Studio', version=VERSION, docs_url=None, redoc_url=None)

@app.middleware('http')
async def local_origin_only(request: Request, call_next):
    # Reject DNS-rebinding Host names. TestClient uses 'testserver'. The launchers
    # bind the service to 127.0.0.1:8765, never to a public interface.
    allowed = ('127.0.0.1:8765','localhost:8765','127.0.0.1','localhost','testserver')
    if request.headers.get('host','').lower() not in allowed:
        return JSONResponse({'detail':'Only local Host headers allowed'},status_code=403)
    origin=request.headers.get('origin')
    if origin:
        expected = f'{request.url.scheme}://{request.url.netloc}'
        if origin != expected or request.url.hostname not in ('127.0.0.1','localhost'):
            return JSONResponse({'detail':'Only same-origin local requests allowed'},status_code=403)
    return await call_next(request)

@app.get('/')
async def index():
    return FileResponse(ROOT / 'index.html', headers={'Cache-Control':'no-store',
             'Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; object-src 'none'; frame-ancestors 'none'"})

@app.get('/app.js')
async def js():
    return FileResponse(ROOT/'app.js', media_type='application/javascript',
                       headers={'Cache-Control':'no-store'})

@app.get('/api/status')
async def status():
    try: import onnx; onnx_version = onnx.__version__
    except ImportError: onnx_version = None
    return {'ok':True,'version':VERSION,'extension_version':'0.7.0','onnx_checker_version':onnx_version,
            'max_file_bytes':MAX_FILE,'storage':'RAM; no upload persistence','model_execution':'screened NumPy reference; optional PyTorch CPU crosscheck; optional SciPy MILP challenger; conditional real partition checks (NOT ONNX Runtime)' 
            ,'numpy_reference_worker_available':__import__('importlib').util.find_spec('numpy') is not None,
            'pytorch_reference_worker_available':__import__('importlib').util.find_spec('torch') is not None,
            'exact_partition_proof_available':True,
            'exact_relational_dual_checker_available':True,
            'proof_gated_model_update_available':True,
            'fp32_exact_rounding_intervals_available':True,
            'fp32_model_update_error_lifting_available':True,
            'onnxruntime_cpu_available':__import__('importlib').util.find_spec('onnxruntime') is not None,
            'lean_executable_available':__import__('shutil').which('lean') is not None,
            'milp_solver_available':__import__('importlib').util.find_spec('scipy') is not None}

@app.get('/api/iris-demo-profile')
async def iris_demo_profile():
    # This is a fixed local published-dataset demonstration, not uploaded data.
    return JSONResponse(json.loads((ROOT.parent/'validation/v06_iris_profile.json').read_text()),
                        headers={'Cache-Control':'no-store'})

@app.post('/api/analyze')
async def submit(request: Request):
    try:
        filename=unquote(request.headers.get('x-pcs-filename', 'unnamed'))
        if len(filename)>300:raise IntakeError('Filename too long')
        p = parse_policy(json.loads(unquote(request.headers.get('x-pcs-policy', '{}'))))
    except (json.JSONDecodeError, IntakeError) as exc:
        raise HTTPException(400, f'Invalid metadata/policy: {exc}')
    content=bytearray()
    async for part in request.stream():
        if len(content)+len(part)>MAX_FILE:raise HTTPException(413,'File too large (128 MiB limit)')
        content.extend(part)
    if not content:raise HTTPException(400,'Empty file')
    return JSONResponse(analyze(filename,bytes(content),p),
                        headers={'Cache-Control':'no-store'})

@app.post('/api/compare-update')
async def compare_update(request: Request):
    """Two uploaded models, length-prefixed and screened; no model code executed.

    Body: unsigned little-endian 32-bit old model length, then old/new bytes.
    Caller controls the proposed policy; actual trust requires separate reviewer
    verification with independently pinned source hashes and thresholds.
    """
    from .model_update import compare,parse_update_policy,MAX_PAIR_BYTES,ModelUpdateError
    from .verify_relational import strict_pairs
    try:
        encoded=request.headers.get('x-pcs-update-policy','')
        if len(encoded)>8000:raise ModelUpdateError('policy header length budget')
        policy=parse_update_policy(json.loads(unquote(encoded),object_pairs_hook=strict_pairs,
               parse_constant=lambda _:(_ for _ in ()).throw(ValueError('nonfinite JSON'))))
        content=bytearray()
        async for part in request.stream():
            if len(content)+len(part)>MAX_PAIR_BYTES+4:raise ModelUpdateError('combined models exceed 8 MiB')
            content.extend(part)
        if len(content)<6:raise ModelUpdateError('truncated update envelope')
        oldlen=int.from_bytes(content[:4],'little')
        if not 0<oldlen<len(content)-4:raise ModelUpdateError('invalid model boundaries')
        result=compare(bytes(content[4:4+oldlen]),bytes(content[4+oldlen:]),policy)
        return JSONResponse(result,headers={'Cache-Control':'no-store'})
    except (ValueError,KeyError,TypeError,ModelUpdateError) as exc:
        raise HTTPException(400,'Invalid update request: '+str(exc)[:180])

@app.post('/api/compare-update-fp32')
async def compare_update_fp32(request: Request):
    """Same-input model-update real certificate + conditional binary32 rounding lift.

    An auto-generated proposed policy is NOT reviewer authority, and the app
    never sends model bytes into the native ONNX Runtime execution engine.
    """
    from .model_update import compare,parse_update_policy,MAX_PAIR_BYTES
    from .fp32_lift_v07 import lift_update
    from .verify_relational import strict_pairs
    try:
        encoded=request.headers.get('x-pcs-fp32-update-policy','')
        if len(encoded)>8000:raise ValueError('claim length budget')
        request_policy=json.loads(unquote(encoded),object_pairs_hook=strict_pairs,
            parse_constant=lambda _:(_ for _ in ()).throw(ValueError('nonfinite JSON')))
        if not isinstance(request_policy,dict) or set(request_policy)!={'input_box','output_coefficients',
                'baseline_upper_limit','drift_upper_limit','required_new_upper_limit','fp32_required_new_upper_limit'}:
            raise ValueError('update claim fields')
        float_limit=request_policy.pop('fp32_required_new_upper_limit')
        p=parse_update_policy(request_policy)
        data=bytearray()
        async for chunk in request.stream():
            if len(data)+len(chunk)>MAX_PAIR_BYTES+4:raise ValueError('model length budget')
            data.extend(chunk)
        if len(data)<6:raise ValueError('truncated model envelope')
        n=int.from_bytes(data[:4],'little')
        if not 0<n<len(data)-4:raise ValueError('model envelope lengths')
        old=bytes(data[4:4+n]);new=bytes(data[4+n:])
        exact=compare(old,new,p)
        lift={'status':'OPEN','reason':'No two-model independently checkable exact-real certificates'}
        if exact['status']=='PROVED_CONDITIONALLY':
            lift=lift_update(old,new,exact['baseline']['certificate'],exact['baseline_reviewer_policy'],
                  exact['update']['certificate'],exact['update_reviewer_policy'],float_limit)
        return JSONResponse({'schema':'pcs-fp32-model-update-intake-v0.7',
            'exact_real':exact,'binary32_lift':lift,
            'reviewer_authority':'NOT_ESTABLISHED; independent policy/model SHA256 pins required',
            'runtime_equivalence':'NOT_ESTABLISHED',
            'lean_kernel_verification':'NOT_ESTABLISHED'},headers={'Cache-Control':'no-store'})
    except (ValueError,KeyError,TypeError,OverflowError) as exc:
        raise HTTPException(400,'Invalid binary32 update request: '+str(exc)[:180])

@app.post('/api/fp32-assure')
async def fp32_assure(request: Request):
    """Drag/drop restricted IEEE-754 interval claim; no uploaded execution.

    The browser's claim is a *suggestion*. A separate reviewer must pin model
    SHA-256 and the true acceptance policy before considering the result.
    """
    from .fp32_assurance import issue, POLICY_SCHEMA, digest
    from .dense_nn import screen_onnx
    from .verify_relational import strict_pairs
    try:
        encoded=request.headers.get('x-pcs-fp32-claim','')
        if len(encoded)>8000:raise ValueError('claim header budget')
        claim=json.loads(unquote(encoded),object_pairs_hook=strict_pairs,
                         parse_constant=lambda _:(_ for _ in ()).throw(ValueError('invalid JSON constant')))
        if not isinstance(claim,dict) or set(claim)!={'input_box','input_min','input_max','output_coefficients','upper_limit'}:
            raise ValueError('claim fields')
        content=bytearray()
        async for part in request.stream():
            if len(content)+len(part)>8*1024*1024:raise ValueError('8 MiB model size budget')
            content.extend(part)
        if not content:raise ValueError('empty model')
        data=bytes(content)
        spec=screen_onnx(data)
        box=claim['input_box'] or [[claim['input_min'],claim['input_max']]]*spec['input_width']
        suggested={'schema':POLICY_SCHEMA,'model_sha256':digest(data),'input_box':box,
                   'output_coefficients':claim['output_coefficients'],'upper_limit':claim['upper_limit']}
        result=issue(data,suggested)
        return JSONResponse({'assessment':result,'suggested_reviewer_policy':suggested,
             'independent_reviewer_acceptance':'NOT_ESTABLISHED',
             'note':'The upload itself cannot establish reviewer authority; pin this policy independently.'},
             headers={'Cache-Control':'no-store'})
    except (ValueError,TypeError,KeyError) as exc:
        raise HTTPException(400,'Invalid FP32 request: '+str(exc)[:180])
    except Exception as exc:
        raise HTTPException(400,'Unsupported FP32 model/claim: '+type(exc).__name__)

@app.get('/api/samples')
async def samples():
    samples_dir=ROOT.parent / 'samples'
    return sorted(p.name for p in samples_dir.iterdir() if p.is_file() and not p.name.startswith('.'))

@app.get('/api/sample/{sample_name}')
async def sample(sample_name: str):
    available=(ROOT.parent/'samples'/sample_name).resolve()
    if available.parent != (ROOT.parent/'samples').resolve() or not available.is_file():
        raise HTTPException(404,'Sample not found')
    return FileResponse(available,headers={'Cache-Control':'no-store'})

@app.post('/api/guarded-demo')
async def guarded_demo(request: Request):
    """Run model proposals ONLY against an isolated in-memory synthetic backend."""
    from .guard_runtime import evaluate_demo_trace,GuardError
    content=bytearray()
    async for part in request.stream():
        if len(content)+len(part)>2*1024*1024:raise HTTPException(413,'Agent demo trace too large')
        content.extend(part)
    try:return JSONResponse(evaluate_demo_trace(bytes(content)),headers={'Cache-Control':'no-store'})
    except GuardError as exc:raise HTTPException(400,str(exc))

@app.post('/api/attack-campaign')
async def attack_campaign():
    """Run bounded local synthetic metamorphic attacks. No user input or tools."""
    from .adversarial_campaign import run_campaign
    return JSONResponse(run_campaign(),headers={'Cache-Control':'no-store'})
