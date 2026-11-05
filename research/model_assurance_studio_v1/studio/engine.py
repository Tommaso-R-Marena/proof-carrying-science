"""PCS Model Assurance Studio v0.5: bounded inspection of untrusted artifacts.

All findings are scoped to static checks, never general safety certification.
Inputs are bytes: no pickle loading, archive extraction, external refs, or model code.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import struct
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any
from .research import value_shape, find_scalar_witness, sbml_conservation, sbml_element_balance, sbml_charge_balance
from .structural import inspect_mmcif
from .replay import replay_candidate
from .exact_interval import enclose

VERSION = '0.6.0'
MAX_FILE = 128 * 1024 * 1024  # deliberately bounded MVP; no uploads persisted
MAX_HEADER = 8 * 1024 * 1024
MAX_MESSAGE_FIELDS = 200_000
MAX_NESTING = 10
MAX_ATOMS = 100_000
MAX_SCAN_FLOATS = 250_000

DEFAULT_POLICY = {
    'forbid_stochastic_onnx_ops': False,
    'forbid_custom_onnx_domains': False,
    'max_onnx_nodes': 100_000,
    'max_pdb_clashes': 0,
    'require_self_contained_onnx': True,
    'require_onnx_official_checker': False,
    'check_output_bounds': False,
    'search_scalar_witness': True,
    'enable_reference_replay': False,
    'enable_partition_proof': False,
    'max_partition_leaves': 64,
    'enable_torch_crosscheck': False,
    'enable_milp_challenger': False,
    'enable_relational_certificate': False,
    'relational_coefficients': [],
    'relational_input_box': [],
    'relational_upper_limit': '0',
    'enable_activation_case_cover': False,
    'max_activation_leaves': 16,
    'milp_timeout_seconds': 6,
    'input_min': -1.0, 'input_max': 1.0,
    'output_min': -10.0, 'output_max': 10.0,
}
DTYPE_BITS = {
    'BOOL': 8, 'U8': 8, 'I8': 8, 'F8_E4M3': 8, 'F8_E5M2': 8,
    'F8_E4M3FN': 8, 'F8_E5M2FNUZ': 8, 'F8_E4M3FNUZ': 8, 'F8_E5M2FN': 8,
    'U16': 16, 'I16': 16, 'F16': 16, 'BF16': 16,
    'U32': 32, 'I32': 32, 'F32': 32,
    'U64': 64, 'I64': 64, 'F64': 64,
    'F4': 4, 'U4': 4, 'I4': 4,
}

class IntakeError(Exception):
    pass

@dataclass
class Check:
    id: str
    status: str
    title: str
    evidence: str
    scope: str = 'static'

    def export(self):
        return vars(self)

class Report:
    def __init__(self, filename: str, data: bytes, family: str, policy: dict):
        self.filename = filename.replace('\\','/').split('/')[-1][:200] or 'unnamed'
        self.data = data
        self.family = family
        self.policy = policy
        self.checks: list[Check] = []
        self.metrics: dict[str, Any] = {}
        self.details: dict[str, Any] = {}
        self.sha256 = hashlib.sha256(data).hexdigest()

    def add(self, code: str, status: str, title: str, evidence: str, scope='static'):
        assert status in ('PASS', 'FAIL', 'OPEN')
        self.checks.append(Check(code, status, title, str(evidence)[:600], scope))

    def finish(self):
        # A PASS for all static checks must NEVER be represented as an overall safety PASS.
        decision = ('FAIL' if any(c.status == 'FAIL' for c in self.checks) else 'OPEN')
        payload = {
            'schema': 'pcs-model-intake-receipt-v0.6', 'version': VERSION,
            'policy': self.policy.copy(),
            'filename': self.filename, 'bytes': len(self.data), 'sha256': self.sha256,
            'family': self.family, 'decision': decision,
            'decision_meaning': ('One or more scoped checks failed' if decision == 'FAIL'
                                 else 'Static inspection alone cannot establish deployment safety'),
            'metrics': self.metrics, 'details': self.details,
            'checks': [c.export() for c in self.checks],
            'limitations': [
                'Static analysis is non-executing; optional replay evaluates screened scalar or small dense ONNX operations in a separate NumPy process, NOT ONNX Runtime or Lean-kernel verification.',
                'No full ONNX model-runtime equivalence, general AI safety, biological validity, misuse resistance, or clinical safety is certified.',
                'The JSON receipt is SHA-256 bound but is not signed, trusted, or PCS v0.6 certified.',
            ],
        }
        payload['pcs_claim_inventory'] = to_pcs_candidate(payload, self.policy)
        payload['policy_sha256'] = digest_json(self.policy)
        payload['receipt_sha256'] = digest_json(payload)
        return payload


def to_pcs_candidate(report, policy):
    """PCS-shaped claim/evidence inventory, NOT an accepted PCS v0.6 verification package."""
    artifact_id='artifact-001'
    assumptions=[{'id':'static-inspection-boundary',
                  'statement':'The untrusted artifact was not executed; tool/parser correctness and source custody are not independently verified.',
                  'rationale':'Explicit boundary for external inspection findings',
                  'scope':[artifact_id]}]
    if policy['check_output_bounds'] and report['family']=='onnx':
        assumptions.append({'id':'conditional-real-arithmetic-input-range',
            'statement':f"All graph inputs are in [{policy['input_min']}, {policy['input_max']}]; supported operators are interpreted with real-number semantics, not validated floating-point runtime semantics.",
            'rationale':'Assumption underlying analytic interval enclosure',
            'scope':[artifact_id]})
    claims=[];evidence=[]
    for idx, ck in enumerate(report['checks'],1):
        cid=f'claim-{idx:03d}';eid=f'evidence-{idx:03d}'
        assumptions_for_claim=['static-inspection-boundary']
        if ck['id'] in ('ONNX_INTERVAL','ONNX_DENSE_REAL_BOX','ONNX_DENSE_PARTITION','ONNX_DENSE_WITNESS','ONNX_DENSE_F32_REPLAY','ONNX_DENSE_TWO_RUNTIME','ONNX_DENSE_MILP') and policy['check_output_bounds']:
            assumptions_for_claim.append('conditional-real-arithmetic-input-range')
        claims.append({'id':cid,'statement':ck['title'], 'kind':'computational',
                       'required_evidence':[eid], 'assumptions':assumptions_for_claim})
        evidence.append({'id':eid,'kind':'untrusted-external-static-inspection',
                         'claim_ids':[cid],'outcome':'UNVERIFIED' if ck['status']=='OPEN' else ck['status'],
                         'checker':f'model-assurance-studio/{VERSION}',
                         'details':{'check_id':ck['id'],'scope':ck['scope'], 'evidence':ck['evidence']},
                         'artifact_ids':[artifact_id]})
    return {'schema':'pcs-candidate-claim-inventory-v0.5', 'trusted_authority':False,
            'source_assessment_schema':'pcs-model-intake-receipt-v0.5',
            'artifacts':[{'id':artifact_id,'path':report['filename'],'role':'untrusted model input',
                          'sha256':report['sha256'],'media_type':'application/octet-stream',
                          'metadata':{'family':report['family'],'bytes':report['bytes']}}],
            'assumptions':assumptions,'claims':claims,'evidence':evidence,
            'warnings':['Candidate PCS-shaped data only; requires separate reviewer acceptance, independent replay, and Lean-authoritative verification.']}


def digest_json(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
                                     allow_nan=False).encode('utf8')).hexdigest()


def parse_policy(value: dict | None):
    if value is None:
        return DEFAULT_POLICY.copy()
    if not isinstance(value, dict):
        raise IntakeError('Policy must be an object')
    unknown = set(value) - set(DEFAULT_POLICY)
    if unknown:
        raise IntakeError('Unknown policy keys: ' + ', '.join(sorted(unknown)))
    result = DEFAULT_POLICY | value
    for key in ('forbid_stochastic_onnx_ops', 'forbid_custom_onnx_domains',
                'require_self_contained_onnx', 'require_onnx_official_checker', 'check_output_bounds', 'search_scalar_witness', 'enable_reference_replay','enable_partition_proof','enable_torch_crosscheck','enable_milp_challenger','enable_relational_certificate','enable_activation_case_cover'):
        if not isinstance(result[key], bool):
            raise IntakeError(f'{key} must be boolean')
    for key in ('max_onnx_nodes', 'max_pdb_clashes'):
        if type(result[key]) is not int or not 0 <= result[key] <= 1_000_000:
            raise IntakeError(f'{key} must be an integer between 0 and 1,000,000')
    if type(result['milp_timeout_seconds']) is not int or not 1<=result['milp_timeout_seconds']<=15:
        raise IntakeError('milp_timeout_seconds must be integer 1..15')
    if type(result['max_activation_leaves']) is not int or not 1<=result['max_activation_leaves']<=64:
        raise IntakeError('max_activation_leaves must be integer 1..64')
    if result['enable_activation_case_cover'] and not result['enable_relational_certificate']:
        raise IntakeError('activation case cover requires a relational claim')
    if type(result['max_partition_leaves']) is not int or not 1<=result['max_partition_leaves']<=128:
        raise IntakeError('max_partition_leaves must be integer 1..128')
    for key in ('input_min','input_max','output_min','output_max'):
        if type(result[key]) not in (float,int) or not math.isfinite(result[key]) or abs(result[key])>1e9:
            raise IntakeError(f'{key} must be finite and within +/- 1e9')
    from .relational_kernel import rational,Unsupported
    if not isinstance(result['relational_input_box'],list) or len(result['relational_input_box'])>16:
        raise IntakeError('relational_input_box must be a list of at most 16 input ranges')
    try:
        for pair in result['relational_input_box']:
            if not isinstance(pair,list) or len(pair)!=2 or rational(pair[0])>rational(pair[1]):
                raise IntakeError('Each relational input range must be [min,max]')
    except (Unsupported,ValueError,ZeroDivisionError) as exc:
        raise IntakeError('malformed rational input domain: '+str(exc)[:80]) from exc
    # Output-coefficient vector and bound are typed, explicitly scoped claims.
    if not isinstance(result['relational_coefficients'],list) or len(result['relational_coefficients'])>16:
        raise IntakeError('relational coefficients must be a list of at most 16 rationals')
    from .relational_kernel import rational,Unsupported
    try:
        for coefficient in result['relational_coefficients']: rational(coefficient)
        rational(result['relational_upper_limit'])
    except (Unsupported,ValueError,ZeroDivisionError) as exc:
        raise IntakeError('invalid relational rational: '+str(exc)[:80]) from exc
    if result['enable_relational_certificate'] and not result['relational_coefficients']:
        raise IntakeError('relational coefficients are required when relational verification is enabled')
    if result['input_min']>result['input_max'] or result['output_min']>result['output_max']:
        raise IntakeError('Invalid interval (minimum exceeds maximum)')
    return result


def sniff(filename: str, data: bytes):
    ext = filename.lower().rsplit('.', 1)[-1]
    # Do not reinterpret a pickle/ZIP/HDF5 payload as a trusted supported model just
    # because its suffix was changed. This is a coarse defensive magic check.
    if ext in ('onnx','safetensors') and (data.startswith((b'PK\x03\x04', b'\x89HDF\r\n\x1a\n')) or (len(data)>2 and data[0]==0x80 and data[1] in (2,3,4,5))):
        return 'unsafe_serialization'
    if filename.lower().endswith('.agenttrace.json'):return 'agent_trace'
    if ext in ('pt', 'pth', 'ckpt', 'pkl', 'pickle', 'joblib', 'h5', 'hdf5'):
        return 'unsafe_serialization'
    if ext == 'onnx': return 'onnx'
    if ext == 'safetensors': return 'safetensors'
    if ext in ('pdb', 'ent'): return 'pdb'
    if ext in ('fa', 'faa', 'fasta', 'fna'): return 'fasta'
    if ext == 'sbml' or (ext == 'xml' and re.search(rb'<(?:[a-z0-9_]+:)?sbml(?:\s|>)', data[:4096].lower())): return 'sbml'
    if ext in ('cif', 'mmcif'): return 'mmcif'
    return 'unknown'


def analyze(filename: str, data: bytes, policy: dict | None = None):
    policy = parse_policy(policy)
    if len(data) > MAX_FILE:
        raise IntakeError('File exceeds 128 MiB prototype limit; no content was analyzed')
    if not data:
        raise IntakeError('Empty file')
    family = sniff(filename, data)
    r = Report(filename, data, family, policy)
    r.add('INTEGRITY_SHA256', 'PASS', 'Exact artifact fingerprint', 'SHA-256: ' + r.sha256)
    try:
        if family == 'onnx': inspect_onnx(r)
        elif family == 'agent_trace':
            from .agent_gate import inspect_trace
            inspect_trace(data,r)
        elif family == 'safetensors': inspect_safetensors(r)
        elif family == 'pdb': inspect_pdb(r)
        elif family == 'fasta': inspect_fasta(r)
        elif family == 'sbml': inspect_sbml(r)
        elif family == 'unsafe_serialization':
            r.add('UNTRUSTED_CODE_FORMAT', 'FAIL', 'Potentially executable model serialization',
                  'Refused to deserialize this file. Export an ONNX graph or safetensors weights instead.')
        elif family == 'mmcif': inspect_mmcif(r)
        else:
            r.add('UNKNOWN_FORMAT', 'OPEN', 'Unsupported or unrecognized format',
                  'No format-specific validation was performed.')
    except (ValueError, UnicodeError, struct.error, OverflowError, IntakeError) as e:
        r.add('PARSE_FAILURE', 'FAIL', 'Artifact parser rejected this input', f'{type(e).__name__}: {str(e)[:240]}')
    except Exception as e:
        # Fail closed on unforeseen parser errors without emitting raw file data.
        r.add('INSPECTOR_ERROR', 'OPEN', 'Parser encountered an internal error', type(e).__name__)
    return r.finish()


def dup_reject(pairs):
    out = {}
    for k, v in pairs:
        if k in out: raise ValueError('duplicate JSON key')
        out[k] = v
    return out


def inspect_safetensors(r: Report):
    data = r.data
    if len(data) < 9: raise ValueError('missing safetensors header')
    header_size = struct.unpack_from('<Q', data)[0]
    if not 1 <= header_size <= min(MAX_HEADER, len(data)-8):
        raise ValueError('invalid or oversized safetensors header')
    if data[8:9] != b'{': raise ValueError('header must begin with {')
    h = json.loads(data[8:8+header_size].decode('utf8'), object_pairs_hook=dup_reject,
                   parse_constant=lambda v: (_ for _ in ()).throw(ValueError('non-finite JSON')))
    if not isinstance(h, dict): raise ValueError('header not an object')
    region_size = len(data) - 8 - header_size
    entries = [(k, v) for k, v in h.items() if k != '__metadata__']
    if '__metadata__' in h:
        m = h['__metadata__']
        if not isinstance(m, dict) or any(not isinstance(x, str) for x in m.values()):
            raise ValueError('invalid __metadata__')
    if len(entries) > 200_000: raise ValueError('too many tensor entries')
    segments = []
    total_params = 0
    types = Counter()
    unknown_types = set()
    scanned = 0
    nonfinite = 0
    for name, info in entries:
        if not isinstance(info, dict) or set(info) != {'dtype','shape','data_offsets'}:
            raise ValueError(f'Invalid tensor descriptor: {name[:60]}')
        dtype, shape, offsets = info['dtype'], info['shape'], info['data_offsets']
        if not isinstance(dtype, str) or dtype not in DTYPE_BITS: unknown_types.add(str(dtype))
        if not isinstance(shape, list) or len(shape)>16 or any(type(x) is not int or x<0 for x in shape):
            raise ValueError('invalid tensor shape')
        if not isinstance(offsets, list) or len(offsets)!=2 or any(type(x) is not int for x in offsets):
            raise ValueError('invalid tensor offsets')
        start, end = offsets
        if not (0 <= start <= end <= region_size): raise ValueError('tensor offset out of bounds')
        count = math.prod(shape)
        total_params += count
        types[str(dtype)] += 1
        if dtype in DTYPE_BITS:
            expected = (count * DTYPE_BITS[dtype] + 7) // 8
            if expected != end - start: raise ValueError('tensor size does not match shape and dtype')
        segments.append((start, end, name))
        if dtype in ('F16','BF16','F32','F64') and count and scanned < MAX_SCAN_FLOATS:
            n = min(count, MAX_SCAN_FLOATS-scanned)
            width = 2 if dtype in ('F16','BF16') else (4 if dtype=='F32' else 8)
            b = memoryview(data)[8+header_size+start:8+header_size+start+n*width]
            if dtype in ('F16','BF16'):
                exponent_mask = 0x7c00 if dtype == 'F16' else 0x7f80
                nonfinite += sum((v[0] & exponent_mask) == exponent_mask
                                 for v in struct.iter_unpack('<H',b))
            else:
                nonfinite += sum(not math.isfinite(v[0]) for v in struct.iter_unpack('<f' if width==4 else '<d', b))
            scanned += n
    occupied = sorted((a,b) for a,b,_ in segments if a != b)
    cursor = 0
    for a,b in occupied:
        if a != cursor: raise ValueError('tensor byte ranges overlap or leave holes')
        cursor = b
    if cursor != region_size: raise ValueError('unreferenced byte region')
    r.metrics = {'tensors':len(entries), 'parameters':total_params,'dtype_counts':dict(types),
                 'float_values_sampled':scanned, 'nonfinite_sampled':nonfinite}
    r.details = {'tensor_names_sample': [n for n,_ in entries[:20]], 'header_bytes':header_size}
    r.add('SAFETENSORS_OFFSETS', 'PASS', 'Tensor boundaries are consistent',
          f'{len(entries)} tensor descriptors; full byte range covered without overlap')
    if unknown_types:
        r.add('UNKNOWN_DTYPES','OPEN','Unrecognized tensor data types', ', '.join(sorted(unknown_types)))
    scanned_family = ('F16','BF16','F32','F64')
    total_float = sum(math.prod(i['shape']) for _,i in entries if i['dtype'] in scanned_family)
    other_float = [i['dtype'] for _,i in entries if isinstance(i['dtype'],str) and
                   i['dtype'].startswith(('F8','F4'))]
    if nonfinite:
        r.add('NONFINITE_WEIGHTS','FAIL','Non-finite floating-point values detected',
              f'{nonfinite} non-finite values in {scanned} examined F16/BF16/F32/F64 prefix elements')
    elif scanned:
        complete = scanned == total_float and not other_float
        r.add('NONFINITE_WEIGHTS', 'PASS' if complete else 'OPEN',
              'Finite-weight prefix scan (F16/BF16/F32/F64)',
              f'No non-finite values among {scanned}/{total_float} covered floats; other float formats: {len(other_float)}. Scan uses bounded tensor prefixes, not random sampling.')
    else:
        r.add('NONFINITE_WEIGHTS','OPEN','Floating-point finiteness not assessed',
              'No supported floating-point elements scanned')
    r.add('WEIGHTS_ONLY','OPEN','Model behavior is unavailable from weights alone',
          'Model architecture, pre/postprocessing and runtime tests are not present in a safetensors file')

# Minimal protobuf wire reader for bounded structural ONNX inspection. No execution.
def wire_fields(buf: memoryview, level=0):
    if level > MAX_NESTING: raise ValueError('protobuf nesting depth exceeded')
    pos, count = 0, 0
    while pos < len(buf):
        count += 1
        if count > MAX_MESSAGE_FIELDS: raise ValueError('too many protobuf fields')
        tag, pos = read_varint(buf, pos)
        field, wire = tag >> 3, tag & 7
        if field == 0: raise ValueError('invalid zero protobuf field')
        if wire == 0:
            val, pos = read_varint(buf, pos)
        elif wire == 1:
            if pos+8 > len(buf): raise ValueError('truncated fixed64')
            val, pos = bytes(buf[pos:pos+8]), pos+8
        elif wire == 2:
            size, pos = read_varint(buf, pos)
            if size > len(buf)-pos: raise ValueError('truncated protobuf length-delimited value')
            val, pos = buf[pos:pos+size], pos+size
        elif wire == 5:
            if pos+4 > len(buf): raise ValueError('truncated fixed32')
            val, pos = bytes(buf[pos:pos+4]), pos+4
        else: raise ValueError('unsupported protobuf wire type')
        yield field, wire, val


def read_varint(buf, pos):
    value = 0
    for i in range(10):
        if pos >= len(buf): raise ValueError('truncated protobuf varint')
        b = int(buf[pos]); pos += 1
        if i==9 and b>1: raise ValueError('protobuf varint overflow')
        value |= (b & 127) << (7*i)
        if not (b & 128): return value, pos
    raise ValueError('protobuf varint too long')


def field_string(raw):
    return bytes(raw).decode('utf8', errors='replace')[:200]


def read_name(message, level=1):
    for f,w,v in wire_fields(message,level):
        if f == 1 and w == 2: return field_string(v)
    return ''


def read_value_info(message):
    """Extract name and top-level tensor scalar data type from ONNX ValueInfoProto."""
    name = ''
    dtype = None
    for f,w,v in wire_fields(message,2):
        if f==1 and w==2:name=field_string(v)
        elif f==2 and w==2:  # TypeProto
            for tf,tw,tv in wire_fields(v,3):
                if tf==1 and tw==2:  # tensor_type: TypeProto.Tensor
                    for ef,ew,ev in wire_fields(tv,4):
                        if ef==1 and ew==0:dtype=ev
    return name,dtype


def tensor_external(message):
    ext, name = False, ''
    for f,w,v in wire_fields(message, 2):
        if f == 8 and w == 2: name = field_string(v)
        if f == 13 and w == 2: ext = True
        if f == 14 and w == 0 and v == 1: ext = True
    return name, ext


def parse_node(message):
    inputs, outputs, op, domain, nested = [], [], '', '', 0
    for f,w,v in wire_fields(message,2):
        if f == 1 and w == 2: inputs.append(field_string(v))
        elif f == 2 and w == 2: outputs.append(field_string(v))
        elif f == 4 and w == 2: op = field_string(v)
        elif f == 7 and w == 2: domain = field_string(v)
        elif f == 5 and w == 2:
            # A node attribute may embed subgraphs: register as not fully inspected.
            for af, aw, av in wire_fields(v,3):
                if af in (6,11) and aw == 2: nested += 1
    return inputs, outputs, op, domain, nested


def tensor_interval(message):
    """Exact raw tensor coverage or refuse. Returns conservative extrema of small numeric data."""
    dims=[]; dtype=None; raw=None; values=[]; field_count=0
    for f,w,v in wire_fields(message,2):
        if f==1:
            if w==0: dims.append(v)
            elif w==2:
                pos=0
                while pos<len(v):
                    d,pos=read_varint(v,pos);dims.append(d)
        elif f==2 and w==0: dtype=v
        elif f==9 and w==2: raw=v
        elif (f,w) in ((4,5),(10,1)):
            values.append(struct.unpack('<f' if f==4 else '<d',v)[0])
        elif f in (4,10) and w==2:
            unit=4 if f==4 else 8
            if len(v)%unit: return None
            if len(v)//unit>MAX_SCAN_FLOATS: return None
            values.extend(x[0] for x in struct.iter_unpack('<f' if unit==4 else '<d',v))
        field_count+=1
    if len(dims)>16: return None
    count=math.prod(dims)
    if count>MAX_SCAN_FLOATS or count==0:return None
    if raw is not None:
        # ONNX tensor data_type enum: FLOAT=1, INT32=6, INT64=7, DOUBLE=11.
        fmts={1:('<f',4),6:('<i',4),7:('<q',8),11:('<d',8)}
        if dtype not in fmts: return None
        fmt,width=fmts[dtype]
        if len(raw)!=count*width:return None
        values=[x[0] for x in struct.iter_unpack(fmt,raw)]
    if len(values)!=count or any(not math.isfinite(x) for x in values):return None
    return (min(values),max(values))


def add_interval(a,b):return (a[0]+b[0],a[1]+b[1])
def neg_interval(a):return (-a[1],-a[0])
def mul_interval(a,b):
    p=[x*y for x in a for y in b]
    return min(p),max(p)

def apply_interval(op,args):
    """Sound-enclosure-inspired real arithmetic for a narrow elementwise ONNX subset.

    Results are not machine-checked IEEE754 semantics; scope remains explicit.
    """
    if op=='Identity' and len(args)==1:return args[0]
    if op=='Neg' and len(args)==1:return neg_interval(args[0])
    if op=='Relu' and len(args)==1:return max(0.,args[0][0]),max(0.,args[0][1])
    if op=='Abs' and len(args)==1:
        a,b=args[0];return 0. if a<=0<=b else min(abs(a),abs(b)),max(abs(a),abs(b))
    if op=='Add' and len(args)==2:return add_interval(*args)
    if op=='Sub' and len(args)==2:return add_interval(args[0],neg_interval(args[1]))
    if op=='Mul' and len(args)==2:return mul_interval(*args)
    if op=='Div' and len(args)==2:
        lo,hi=args[1]
        if lo<=0<=hi:return None
        return mul_interval(args[0],(1./hi,1./lo))
    if op=='Sigmoid' and len(args)==1:
        def f(x):return 1/(1+math.exp(-x)) if x>=0 else math.exp(x)/(1+math.exp(x))
        return f(args[0][0]),f(args[0][1])
    if op=='Tanh' and len(args)==1:return math.tanh(args[0][0]),math.tanh(args[0][1])
    if op=='Exp' and len(args)==1:
        return math.exp(args[0][0]),math.exp(args[0][1])
    return None


def analyze_intervals(r, nodes, inputs, outputs, initializers, structural_block):
    """Exact finite rational enclosure for supported real-arithmetic operators.

    Refuses to extrapolate onto IEEE float32/64 execution or unknown ONNX ops.
    """
    if structural_block or not inputs:
        r.add('ONNX_INTERVAL','OPEN','Exact output enclosure unavailable',
              'Unresolved graph structure, unsupported attributes/initializer semantics, or no inputs')
        return
    try:
        result=enclose(nodes,inputs,outputs,initializers,r.policy)
    except (ValueError,ArithmeticError,OverflowError,ZeroDivisionError,TypeError) as exc:
        r.add('ONNX_INTERVAL','OPEN','Exact real-arithmetic enclosure unavailable',str(exc)[:240])
        return
    lo,hi=result['interval'];target_lo,target_hi=result['target']
    r.details['exact_real_output_enclosure_fractions']=result['exact_fractions']
    r.details['conditional_output_enclosure']=[float(lo),float(hi)]
    conclusion=result['conclusion']
    ck={'WITHIN':'PASS','DISJOINT':'FAIL','OVERLAP':'OPEN'}[conclusion]
    r.add('ONNX_INTERVAL',ck,'Conditional exact rational output enclosure',
          f'Exact rational interval [{lo}, {hi}]. Required real-arithmetic range [{target_lo}, {target_hi}]. '
          f'Result: {conclusion}. No IEEE-754 soundness, complete ONNX semantics, or Lean proof claimed.',
          'bounded exact rational calculation under explicitly stated assumptions')


def inspect_onnx(r: Report):
    fields = list(wire_fields(memoryview(r.data)))
    ir = None; graph = None; opsets = []
    for f,w,v in fields:
        if f == 1 and w == 0: ir = v
        elif f == 7 and w == 2: graph = v
        elif f == 8 and w == 2:
            domain, version = '', None
            for of,ow,ov in wire_fields(v,2):
                if of == 1 and ow == 2: domain = field_string(ov)
                if of == 2 and ow == 0: version = ov
            opsets.append({'domain':domain,'version':version})
    if ir is None or graph is None or not opsets:
        raise ValueError('ModelProto missing ir_version, graph, or opset_import')
    nodes, inputs, outputs, init, ext_count = [],[],[],set(),0
    initializer_intervals = {}
    sparse_initializers = 0
    node_attributes = 0
    tensor_types = {}
    tensor_shapes = {}
    for f,w,v in wire_fields(graph,1):
        if w != 2: continue
        if f == 1:
            if len(nodes) >= 100_000: raise ValueError('too many nodes')
            nodes.append(parse_node(v))
            node_attributes += sum(1 for nf,nw,nv in wire_fields(v,2) if nf==5 and nw==2)
        elif f == 5:
            name, external = tensor_external(v)
            if name in init: raise ValueError('duplicate initializer name')
            init.add(name)
            ext_count += int(external)
            initializer_intervals[name] = tensor_interval(v) if not external else None
        elif f == 15:
            sparse_initializers += 1
            # SparseTensorProto.values (field 1) contains the tensor name.
            for sf,sw,sv in wire_fields(v,2):
                if sf == 1 and sw == 2:
                    sparse_name, _ = tensor_external(sv)
                    if sparse_name in init: raise ValueError('duplicate sparse initializer')
                    init.add(sparse_name)
                    initializer_intervals[sparse_name] = None
                    break
        elif f == 11:
            name,dtype=read_value_info(v)
            inputs.append(name);tensor_types[name]=dtype;tensor_shapes[name]=value_shape(v, wire_fields)
        elif f == 12:
            name,dtype=read_value_info(v)
            outputs.append(name);tensor_types[name]=dtype;tensor_shapes[name]=value_shape(v, wire_fields)
    if not outputs: raise ValueError('graph has no declared outputs')
    # Detect duplicate producer outputs, invalid dataflow ordering.
    defined = set(inputs) | init
    duplicate_outputs = set(); missing = set(); producers = set()
    for ins,outs,op,domain,nested in nodes:
        for name in ins:
            if name and name not in defined: missing.add(name)
        for name in outs:
            if not name: continue
            if name in producers or name in defined: duplicate_outputs.add(name)
            producers.add(name); defined.add(name)
    missing_outputs = sorted(set(outputs)-defined)
    ops = Counter(node[2] for node in nodes)
    customs = sorted(set(node[3] for node in nodes if node[3] not in ('','ai.onnx','ai.onnx.ml')))
    stochastic = {k:v for k,v in ops.items() if k in ('RandomNormal','RandomNormalLike','RandomUniform',
                   'RandomUniformLike','Multinomial','Dropout','Bernoulli')}
    nested = sum(n[4] for n in nodes)
    r.metrics = {'ir_version':ir, 'opsets':opsets, 'nodes':len(nodes), 'initializers':len(init),
                 'inputs':len(inputs), 'outputs':len(outputs), 'operators':dict(ops),
                 'custom_domains':customs, 'external_tensors':ext_count, 'nested_graph_attributes':nested,
                 'sparse_initializers':sparse_initializers, 'node_attributes':node_attributes}
    r.details = {'input_names':inputs[:30], 'output_names':outputs[:30],
                 'missing_inputs_sample':sorted(missing)[:15],
                 'stochastic_ops':stochastic,
                 'io_tensor_types':{name:tensor_types.get(name) for name in (inputs+outputs)},
                 'io_singleton_shape_confirmed':{name:tensor_shapes.get(name) is not None for name in (inputs+outputs)}}
    if missing or duplicate_outputs or missing_outputs:
        r.add('ONNX_DATAFLOW','FAIL','Graph name/dataflow inconsistency',
              f'Unresolved inputs {len(missing)}; duplicate producers {len(duplicate_outputs)}; missing outputs {len(missing_outputs)}. Nested scopes may need full checker.')
    else:
        r.add('ONNX_DATAFLOW','PASS','Top-level graph references are consistent',
              f'{len(nodes)} nodes in serialized order; nested graphs not fully validated')
    if ext_count:
        r.add('ONNX_EXTERNAL', 'FAIL' if r.policy['require_self_contained_onnx'] else 'OPEN',
              'ONNX references external tensor files', f'{ext_count} initializers rely on external data not read by this inspector')
    else:
        r.add('ONNX_EXTERNAL','PASS','No external initializer data detected',
              'Top-level initializers are embedded in this file')
    if len(nodes)>r.policy['max_onnx_nodes']:
        r.add('NODE_BUDGET','FAIL','Graph exceeds configured node cap',
              f"{len(nodes)} nodes > cap {r.policy['max_onnx_nodes']}")
    else:
        r.add('NODE_BUDGET','PASS','Graph within configured node cap',
              f"{len(nodes)} nodes <= cap {r.policy['max_onnx_nodes']}")
    if customs:
        r.add('CUSTOM_DOMAINS','FAIL' if r.policy['forbid_custom_onnx_domains'] else 'OPEN',
              'Custom operator domains require independent semantics', ', '.join(customs[:15]))
    else:
        r.add('CUSTOM_DOMAINS','PASS','No custom operator domains detected', 'Top-level nodes inspected')
    if stochastic:
        r.add('STOCHASTIC_OPS', 'FAIL' if r.policy['forbid_stochastic_onnx_ops'] else 'OPEN',
              'Potentially stochastic operators detected', json.dumps(stochastic))
    else:
        r.add('STOCHASTIC_OPS','PASS','No targeted stochastic operations found', 'Only known top-level op names checked')
    if sparse_initializers:
        r.add('ONNX_SPARSE','OPEN','Sparse initializer contents require separate validation',
              f'{sparse_initializers} sparse initializer tensors were identified, not numerically checked')
    if nested:
        r.add('ONNX_SUBGRAPHS','OPEN','Nested control-flow graphs require deeper validation',
              f'{nested} graph-bearing attributes detected; top-level check is incomplete')
    try:
        import onnx  # optional independent checker, never runtime execution
    except ImportError:
        r.add('ONNX_CHECKER', 'FAIL' if r.policy['require_onnx_official_checker'] else 'OPEN',
              'Official ONNX checker not installed', 'Install optional onnx package; protobuf inspection alone is insufficient')
    else:
        try:
            model = onnx.load_model_from_string(r.data)  # does not execute model operators
            onnx.checker.check_model(model, full_check=False)
        except Exception as exc:
            r.add('ONNX_CHECKER','FAIL','Official ONNX structural validation failed', f'{type(exc).__name__}: {str(exc)[:180]}')
        else:
            r.add('ONNX_CHECKER','PASS','Official ONNX structural validation passed',
                  f'onnx {onnx.__version__} / checker.check_model; not a behavioral guarantee')
    if r.policy['check_output_bounds']:
        analyze_intervals(r, nodes, inputs, outputs, initializer_intervals, bool(missing or duplicate_outputs or missing_outputs or ext_count or nested or customs or stochastic or sparse_initializers or node_attributes or
                   any(tensor_types.get(name) not in (1,11) for name in (inputs+outputs))))
    else:
        r.add('ONNX_INTERVAL','OPEN','Bounded output claim not requested',
              'Enable interval analysis and state both input assumptions and desired output bounds')
    if r.policy['check_output_bounds'] and r.policy['search_scalar_witness']:
        blocked = bool(missing or duplicate_outputs or missing_outputs or ext_count or nested or customs or stochastic or sparse_initializers or node_attributes or init)
        if blocked:
            r.add('ONNX_WITNESS','OPEN','Scalar counterexample search blocked',
                  'Incomplete or unsupported graph semantics; unsafe to generate a witness')
        else:
            witness, reason = find_scalar_witness(nodes, inputs, outputs, initializer_intervals,
                                                   tensor_types, tensor_shapes, r.policy)
            if witness:
                witness['artifact_sha256']=r.sha256
                witness['policy_sha256']=digest_json(r.policy)
                r.details['candidate_counterexample']=witness
                r.add('ONNX_WITNESS','OPEN','Unreplayed rational candidate violating input found',
                      f'Idealized rational scalar interpreter found {len(witness["violating_outputs"])} output violations after {witness["samples_tested"]} trials. Candidate requires independently scoped replay.', 'untrusted research candidate')
                if r.policy['enable_reference_replay']:
                    replay = replay_candidate(nodes,inputs,outputs,tensor_types,tensor_shapes,
                                              len(init)+sparse_initializers,node_attributes,witness,r.policy)
                    r.details['reference_replay']=replay
                    if replay['status']=='VIOLATION_REPRODUCED':
                        witness['reference_replay_status']='REPRODUCED_NUMPY_FLOAT32'
                        r.add('ONNX_F32_REPLAY','FAIL','Output policy violated in NumPy float32 scalar replay',
                              f'Allowlisted parsed graph produced {len(replay["violating_outputs"])} violating outputs. This is a replay of screened operators, NOT official ONNX Runtime validation or proof of general unsafety.', 'independent limited reference computation')
                    elif replay['status']=='CANDIDATE_NOT_REPRODUCED':
                        r.add('ONNX_F32_REPLAY','OPEN','Rational candidate not reproduced by float32 operator replay',
                              'Floating-point evaluation did not reproduce the idealized violation. Do not treat as a model safety guarantee.', 'independent limited reference computation')
                    else:
                        r.add('ONNX_F32_REPLAY','OPEN','Reference replay indeterminate',replay.get('reason','Worker unavailable'), 'independent limited reference computation')
            else:
                r.add('ONNX_WITNESS','OPEN','No reproduced counterexample', reason)
    else:
        r.add('ONNX_WITNESS','OPEN','Scalar witness search not requested',
              'Enable conditional bounds and scalar witness search to try candidate inputs')
    if r.policy['enable_reference_replay'] and not any(c.id=='ONNX_F32_REPLAY' for c in r.checks):
        r.add('ONNX_F32_REPLAY','OPEN','Reference replay not attempted',
              'No eligible scalar candidate was available, or exact scoped graph parsing is unresolved.')
    # Separate dense-network pathway: exact rational interval arithmetic with
    # embedded FLOAT32 weights, plus optional screened NumPy reference replay.
    if r.policy['check_output_bounds']:
        from .dense_nn import check_dense
        dense, dense_witness, dense_replay, why = check_dense(r.data, r.policy)
        if dense:
            r.details['dense_network']=dense
            r.add('ONNX_DENSE_REAL_BOX','PASS' if dense['conditional_real_range']=='PROVED_WITHIN_ASSUMED_BOX' else 'OPEN',
                  'Exact conditional real-number bounds for a screened dense network',
                  f"{dense['conditional_real_range']}; input width {dense['input_width']}, output width {dense['output_width']}; floating-point runtime assurance NOT established",
                  'untrusted bounded exact rational arithmetic')
            if r.policy['enable_partition_proof'] and (missing or duplicate_outputs or missing_outputs or ext_count or nested or customs or stochastic or sparse_initializers or node_attributes):
                r.add('ONNX_DENSE_PARTITION','OPEN','Partition proof withheld due to graph inspection issues',
                      'Complete structural assumptions for the candidate graph are not established')
            elif r.policy['enable_partition_proof']:
                from .dense_nn import screen_onnx
                from .partition_proof import make_certificate, verify_certificate
                try:
                    spec=screen_onnx(r.data)
                    result=make_certificate(spec,r.policy,max_leaves=r.policy['max_partition_leaves'])
                    if result['status']=='PROVED_CONDITIONALLY':
                        certified,verification=verify_certificate(spec,r.policy,result['certificate'])
                        if not certified:raise ValueError('fresh recomputation rejected certificate: '+verification)
                        r.details['partition_proof']=result
                        r.add('ONNX_DENSE_PARTITION','PASS','Finite partition proves conditional real-number output bounds',
                              f"{result['leaves']} exact rational leaves recomputed; input box exhaustively covered. Not an IEEE-754, Lean or ONNX Runtime proof.",'bounded exact rational certificate')
                    else:
                        r.details['partition_proof']=result
                        r.add('ONNX_DENSE_PARTITION','OPEN','Partitioned proof did not close',
                              result.get('reason','budget exhausted'),'bounded exact rational certificate')
                except (ValueError,TypeError,OverflowError) as exc:
                    r.add('ONNX_DENSE_PARTITION','OPEN','Partitioned proof unavailable',
                          f'{type(exc).__name__}: {str(exc)[:160]}','bounded exact rational certificate')
            # Independent numerical solver searches the interior when the
            # deterministic corner/random probe suite found no candidate.
            milp_witness=None;milp_replay=None
            if r.policy['enable_milp_challenger']:
                if dense_witness:
                    r.add('ONNX_DENSE_MILP','OPEN','MILP challenge skipped',
                          'A candidate is already available from bounded probes; solver search is unnecessary')
                else:
                    from .dense_nn import screen_onnx, _replay as replay_dense
                    from .milp_challenge import search
                    from fractions import Fraction
                    spec=screen_onnx(r.data)
                    solver=search(spec,r.policy,timeout=r.policy['milp_timeout_seconds'])
                    r.details['milp_challenge']={k:v for k,v in solver.items() if k!='witness'}
                    if solver['status']=='IDEALIZED_VIOLATION_CANDIDATE':
                        milp_witness=solver['witness']
                        milp_witness['artifact_sha256']=r.sha256
                        milp_witness['policy_sha256']=digest_json(r.policy)
                        r.details['milp_counterexample']=milp_witness
                        if r.policy['enable_reference_replay']:
                            target=(Fraction.from_float(float(r.policy['output_min'])),
                                    Fraction.from_float(float(r.policy['output_max'])))
                            milp_replay=replay_dense(spec,milp_witness,target)
                            r.details['milp_replay']=milp_replay
                        if milp_replay and milp_replay['status']=='VIOLATION_REPRODUCED':
                            r.add('ONNX_DENSE_MILP','FAIL','Interior counterexample reproduced in NumPy float32',
                                  'MILP located an idealized rational violation missed by probes; screened NumPy float32 replay reproduced a scoped violation. Not ONNX Runtime.',
                                  'solver-guided challenge plus numerical replay')
                        else:
                            r.add('ONNX_DENSE_MILP','OPEN','Solver-guided idealized candidate requires numerical corroboration',
                                  'MILP proposed a candidate but runtime violation is not confirmed; does not prove model safety or actual ONNX behavior.',
                                  'solver-guided rational candidate')
                    else:
                        r.add('ONNX_DENSE_MILP','OPEN','Solver-guided search did not yield an exact rational counterexample',
                              solver.get('reason',solver['status']), 'numerical search, not a proof')
            candidate_for_torch=dense_witness or milp_witness
            replay_for_torch=dense_replay or milp_replay
            if candidate_for_torch and r.policy['enable_torch_crosscheck'] and r.policy['enable_reference_replay']:
                from .dense_nn import screen_onnx
                from .multiruntime import crosscheck_torch
                from fractions import Fraction
                target=(Fraction.from_float(float(r.policy['output_min'])), Fraction.from_float(float(r.policy['output_max'])))
                second=crosscheck_torch(screen_onnx(r.data),candidate_for_torch,target,replay_for_torch)
                r.details['torch_reference']=second
                if second.get('both_reproduced_violation'):
                    r.add('ONNX_DENSE_TWO_RUNTIME','FAIL','Policy violation reproduced by NumPy and PyTorch references',
                          'Two independently implemented float32 operator evaluators reproduce a scoped output violation; neither runs ONNX Runtime.',
                          'two numerical references; not an ONNX Runtime proof')
                else:
                    r.add('ONNX_DENSE_TWO_RUNTIME','OPEN','Two-reference comparison did not establish agreement',
                          second.get('agreement',second.get('reason',second['status'])),
                          'two numerical references; not an ONNX Runtime proof')
            if dense_witness:
                dense_witness['artifact_sha256']=r.sha256
                dense_witness['policy_sha256']=digest_json(r.policy)
                r.details['dense_counterexample']=dense_witness
                r.add('ONNX_DENSE_WITNESS','OPEN','Candidate counterexample from exact dense-network calculation',
                      f"A violating candidate was found after {dense_witness['trials']} bounded probes; requires numerical replay",'untrusted rational model')
            else:
                r.add('ONNX_DENSE_WITNESS','OPEN','No counterexample observed in bounded search',
                      'A bounded search cannot establish absence of a counterexample; exact enclosure is separate')
            if dense_replay:
                r.details['dense_replay']=dense_replay
                if dense_replay['status']=='VIOLATION_REPRODUCED':
                    r.add('ONNX_DENSE_F32_REPLAY','FAIL','Dense neural-network policy violation reproduced by NumPy float32',
                        f"Reference worker found violations at output indices {dense_replay['violating_indices']}. This does NOT establish ONNX Runtime behavior.",
                        'limited independent reference computation')
                else:
                    r.add('ONNX_DENSE_F32_REPLAY','OPEN','Dense candidate was not numerically reproduced',
                          dense_replay.get('reason',dense_replay['status']), 'limited independent reference computation')
            elif r.policy['enable_reference_replay']:
                r.add('ONNX_DENSE_F32_REPLAY','OPEN','Dense float32 replay not attempted',
                      'No eligible numerical witness was available; real-number interval result is separate')
        else:
            r.add('ONNX_DENSE_REAL_BOX','OPEN','Dense-network bound checker abstained',why or 'Unsupported ONNX graph')
            if r.policy['enable_partition_proof']:
                r.add('ONNX_DENSE_PARTITION','OPEN','Partition proof not attempted',why or 'Unsupported network')
            if r.policy['enable_milp_challenger']:
                r.add('ONNX_DENSE_MILP','OPEN','Solver challenge not attempted',why or 'Unsupported network')
            if r.policy['enable_torch_crosscheck']:
                r.add('ONNX_DENSE_TWO_RUNTIME','OPEN','Two-reference check not attempted',why or 'Unsupported network')
    if r.policy['enable_relational_certificate']:
        if missing or duplicate_outputs or missing_outputs or ext_count or nested or customs or stochastic or sparse_initializers or node_attributes:
            r.add('ONNX_RELATIONAL_FARKAS','OPEN','Relational certificate withheld',
                  'Static graph inspection did not establish the strict supported graph boundary')
        else:
            from .relational_prover import propose
            from .relational_kernel import check as check_relation, Unsupported as RelationUnsupported
            from .dense_nn import screen_onnx
            try:
                spec=screen_onnx(r.data)
                box=(r.policy['relational_input_box'] or
                     [[r.policy['input_min'],r.policy['input_max']] for _ in range(spec['input_width'])])
                proof=propose(r.data,box,r.policy['relational_coefficients'],r.policy['relational_upper_limit'],timeout=5)
                r.details['relational_proof']=proof
                if proof['status']=='PROVED_CONDITIONALLY':
                    accepted,verdict=check_relation(r.data,proof['certificate'])
                    if not accepted:raise ValueError('certificate was not independently checkable: '+str(verdict))
                    r.add('ONNX_RELATIONAL_FARKAS','PASS','Conditional real-number neural invariant proven by rational dual witness',
                          'An independent exact-rational checker verified an explicit LP-dual identity for all inputs in the assumed box. Not float32, full ONNX, Lean, or generalized AI safety.',
                          'exact rational Farkas witness; strictly scoped')
                else:
                    r.add('ONNX_RELATIONAL_FARKAS','OPEN','Relational property remains unproved',
                          proof.get('reason','Optimizer did not produce a checkable certificate'),
                          'untrusted numerical candidate generation')
                if r.policy['enable_activation_case_cover'] and proof['status']!='PROVED_CONDITIONALLY':
                    from .activation_proof import propose as case_propose,verify as verify_cases
                    cases=case_propose(r.data,box,r.policy['relational_coefficients'],
                                      r.policy['relational_upper_limit'],
                                      max_leaves=r.policy['max_activation_leaves'],timeout=3)
                    r.details['activation_proof']=cases
                    if cases['status']=='PROVED_CONDITIONALLY':
                        verified,info=verify_cases(r.data,cases['certificate'])
                        if not verified:raise ValueError('activation case verifier rejected result: '+str(info))
                        r.add('ONNX_RELATIONAL_CASE_COVER','PASS','Exhaustive ReLU activation-case proof verified',
                              f"{info['fully_checked_cases']} feasible/infeasible cases checked using exact rational constraints and Farkas witnesses. Scope: screened real-arithmetic ONNX only.",
                              'exact rational case cover and dual witnesses')
                    else:
                        r.add('ONNX_RELATIONAL_CASE_COVER','OPEN','Activation-case proof remains incomplete',
                              cases.get('reason','No complete proof obtained'), 'exact real case-cover attempt')
                elif r.policy['enable_activation_case_cover']:
                    r.add('ONNX_RELATIONAL_CASE_COVER','PASS','Activation split not required',
                          'Global Farkas proof already closed the claim; the case-cover search was skipped.',
                          'exact real global dual certificate')
            except (RelationUnsupported,ValueError,TypeError,OverflowError,MemoryError) as exc:
                r.add('ONNX_RELATIONAL_FARKAS','OPEN','Relational verifier abstained',
                      type(exc).__name__+': '+str(exc)[:170], 'bounded exact real property')
    r.add('ONNX_BEHAVIOR','OPEN','Full ONNX model behavior is not established',
          'Optional NumPy scalar replay does not run the actual ONNX Runtime engine; robustness, harmful outputs and deployment threat models require explicit test suites')


def inspect_pdb(r: Report):
    if len(r.data) > 32*1024*1024: raise ValueError('PDB text exceeds parser budget')
    text = r.data.decode('ascii',errors='replace')
    atoms, residues, chains = [], set(), set()
    bad_lines = 0
    nonphysical = 0
    seen_ids = set()
    repeated_atoms = 0
    for line in text.splitlines():
        if not line.startswith(('ATOM  ','HETATM')): continue
        if len(atoms) >= MAX_ATOMS: raise ValueError('too many coordinate atoms')
        try:
            x,y,z = (float(line[i:i+8]) for i in (30,38,46))
            occupancy = float(line[54:60]) if line[54:60].strip() else 1.0
            if not all(math.isfinite(v) for v in (x,y,z,occupancy)): raise ValueError('nonfinite')
            chain, resseq, resname = line[21:22], line[22:27].strip(), line[17:20].strip()
            atomname, alt, elem = line[12:16].strip(), line[16:17], line[76:78].strip().upper()
            if not elem: elem = re.sub('[^A-Za-z]','', atomname)[:1].upper()
            token = (chain,resseq, atomname,alt)
            if token in seen_ids: repeated_atoms += 1
            seen_ids.add(token)
            if occupancy < 0 or occupancy > 1: nonphysical += 1
            residues.add((chain, resseq, resname)); chains.add(chain)
            atoms.append((x,y,z,chain,resseq,elem,alt))
        except (ValueError, IndexError): bad_lines += 1
    if not atoms: raise ValueError('no parseable ATOM/HETATM coordinates')
    # Spatial grid yields linear expected cost, bounded by MAX_ATOMS.
    grid = defaultdict(list)
    clashes = 0; samples=[]
    for i,(x,y,z,chain,resseq,elem,alt) in enumerate(atoms):
        if elem in ('H','D'): continue
        cell = (math.floor(x/1.7),math.floor(y/1.7),math.floor(z/1.7))
        for dx in (-1,0,1):
            for dy in (-1,0,1):
                for dz in (-1,0,1):
                    for j in grid.get((cell[0]+dx,cell[1]+dy,cell[2]+dz), []):
                        xx,yy,zz,cc,rr,ee,aa = atoms[j]
                        if chain==cc and resseq==rr: continue
                        # Exclude likely peptide bonds between adjacent sequence positions.
                        if chain==cc and resseq.lstrip('-').isdigit() and rr.lstrip('-').isdigit() and abs(int(resseq)-int(rr))<=1: continue
                        # Altlocs A/B refer to distinct conformers, not simultaneous atoms.
                        if alt.strip() and aa.strip() and alt!=aa: continue
                        if (x-xx)**2+(y-yy)**2+(z-zz)**2 < 1.7**2:
                            clashes += 1
                            if len(samples)<8: samples.append([j,i])
        grid[cell].append(i)
    r.metrics = {'atoms':len(atoms),'residues':len(residues),'chains':len(chains),
                 'severe_close_pairs_heuristic':clashes, 'bad_atom_records':bad_lines,
                 'occupancy_outside_0_1':nonphysical,'duplicate_atom_ids':repeated_atoms}
    r.details = {'clash_pair_indices_sample':samples}
    if bad_lines or nonphysical or repeated_atoms:
        r.add('PDB_RECORDS','FAIL','Malformed or inconsistent PDB atom records',
              f'{bad_lines} malformed; {nonphysical} invalid occupancies; {repeated_atoms} duplicate atom IDs')
    else:
        r.add('PDB_RECORDS','PASS','PDB coordinate records parsed', f'{len(atoms)} coordinate records')
    if clashes > r.policy['max_pdb_clashes']:
        r.add('PDB_CLOSE_CONTACTS','FAIL','Close-heavy-atom heuristic exceeded policy threshold',
              f'{clashes} pairs < 1.7 Å (different residues); threshold {r.policy["max_pdb_clashes"]}. May include metals or expected contacts.')
    else:
        r.add('PDB_CLOSE_CONTACTS','PASS','Close-heavy-atom heuristic within threshold',
              f'{clashes} pairs below 1.7 Å; not a complete stereochemical validation')
    r.add('PDB_SCIENTIFIC_VALIDITY','OPEN','Structural/biological correctness not established',
          'Missing hydrogens, alternate states, bond geometry, force-field energies and experimental support are outside this check')


def inspect_fasta(r: Report):
    raw = r.data.decode('utf8')
    entries=[]; seq=''; name=None
    for line in raw.splitlines():
        line=line.strip()
        if not line or line.startswith(';'): continue
        if line.startswith('>'):
            if name is not None: entries.append((name,seq))
            name=line[1:][:200]; seq=''
        elif name is None:
            raise ValueError('sequence before FASTA header')
        else:
            seq += line.upper()
        if len(seq)>10_000_000 or len(entries)>100_000: raise ValueError('FASTA sequence budget exceeded')
    if name is not None: entries.append((name,seq))
    if not entries: raise ValueError('no FASTA records')
    legal = set('ACDEFGHIKLMNPQRSTVWYBXZJUO*-.')
    weird = sum(ch not in legal for _,seq in entries for ch in seq)
    empty = sum(not seq for _,seq in entries)
    total = sum(len(seq) for _,seq in entries)
    r.metrics = {'sequences':len(entries), 'residues':total, 'empty_sequences':empty, 'unexpected_characters':weird}
    r.details = {'identifiers_sample':[name for name,_ in entries[:12]]}
    r.add('FASTA_FORMAT','FAIL' if weird or empty else 'PASS','Protein-like FASTA syntax',
          f'{len(entries)} records, {total} symbols, {empty} empty, {weird} unusual symbols. Nucleotide FASTA may be misclassified.')
    r.add('FASTA_FUNCTION','OPEN','Sequence identity and function not established',
          'No evidence about protein folding, structure, activity or sequence provenance was provided')


def inspect_sbml(r: Report):
    from defusedxml import ElementTree as DET
    if b'<!DOCTYPE' in r.data.upper() or b'<!ENTITY' in r.data.upper():
        raise ValueError('DTD and entity declarations forbidden')
    if len(r.data) > 16*1024*1024: raise ValueError('SBML XML file exceeds budget')
    root = DET.fromstring(r.data)
    def tag(e): return e.tag.rsplit('}',1)[-1]
    if tag(root) != 'sbml': raise ValueError('not an SBML root')
    model = next((e for e in root if tag(e)=='model'),None)
    if model is None: raise ValueError('missing SBML model')
    elems = list(model.iter())
    if len(elems)>200_000: raise ValueError('too many XML elements')
    species = [e for e in elems if tag(e)=='species']
    reactions = [e for e in elems if tag(e)=='reaction']
    params = [e for e in elems if tag(e)=='parameter']
    ids = [e.get('id') for e in species]
    known = set(ids)
    duplicates = len(ids)-len(known)
    missing_species=set(); negative_stoich=0; missing_kinetics=0; negatives=0
    for s in species:
        for k in ('initialAmount','initialConcentration'):
            if k in s.attrib:
                try:
                    if float(s.get(k))<0: negatives+=1
                except (TypeError,ValueError): negatives+=1
    for reaction in reactions:
        if not any(tag(ch)=='kineticLaw' for ch in reaction): missing_kinetics+=1
        for e in reaction.iter():
            if tag(e) not in ('speciesReference','modifierSpeciesReference'): continue
            if e.get('species') not in known: missing_species.add(e.get('species') or '(empty)')
            if 'stoichiometry' in e.attrib:
                try:
                    if float(e.get('stoichiometry')) < 0: negative_stoich+=1
                except (TypeError,ValueError): negative_stoich+=1
    r.metrics={'level':root.get('level'), 'version':root.get('version'), 'species':len(species),
               'reactions':len(reactions), 'parameters':len(params),
               'reactions_without_kinetic_law':missing_kinetics, 'broken_species_references':len(missing_species)}
    r.details={'unknown_species_sample':sorted(missing_species)[:20], 'model_id':model.get('id')}
    if duplicates or missing_species or negative_stoich or negatives:
        r.add('SBML_REFERENCES','FAIL','SBML semantic consistency issues',
              f'{duplicates} duplicate species IDs; {len(missing_species)} unknown species references; '
              f'{negative_stoich} negative/non-numeric stoichiometries; {negatives} negative/non-numeric initial conditions')
    else:
        r.add('SBML_REFERENCES','PASS','Selected SBML species references are consistent',
              f'{len(species)} species and {len(reactions)} reactions inspected')
    if missing_kinetics:
        r.add('SBML_KINETICS','OPEN','Reaction kinetic laws absent',
              f'{missing_kinetics} of {len(reactions)} reactions lack kineticLaw (may be valid SBML but not directly simulatable)')
    else:
        r.add('SBML_KINETICS','PASS','All reactions have kineticLaw elements',
              'Only presence checked; MathML mathematics and units were not validated')
    if not duplicates and not missing_species and not negative_stoich and not negatives:
        cons, why = sbml_conservation(model,species,reactions,tag)
        if cons is not None:
            r.details['reaction_only_invariants']=cons
            r.metrics['linear_conserved_quantities_reaction_only']=cons['linear_invariant_count']
            r.add('SBML_STOICHIOMETRY','PASS','Exact reaction-only stoichiometric invariants',
                  f"Rank {cons['stoichiometric_rank']} and {cons['linear_invariant_count']} linear invariants computed with rational row reduction. This does NOT establish mass conservation or full SBML dynamics.", 'bounded rational linear algebra')
        else:
            r.add('SBML_STOICHIOMETRY','OPEN','Stoichiometric invariants not established',why)
    else:
        r.add('SBML_STOICHIOMETRY','OPEN','Stoichiometric analysis blocked by invalid species references',
              'Resolve SBML references before computing reaction-only invariants')
    if not duplicates and not missing_species and not negative_stoich:
        balance,why = sbml_element_balance(species,reactions,tag)
        if balance is not None:
            r.details['elemental_balance']=balance
            n=balance['imbalanced_reactions_at_least'];u=balance['unresolved_reactions']
            r.add('SBML_ELEMENT_BALANCE', 'FAIL' if n else ('OPEN' if u else 'PASS'),
                  'Elemental balance from explicit species formulas',
                  f"{balance['balanced_reactions']} balanced, {n} demonstrably imbalanced, {u} unresolved reactions. Charges, formula correctness, and chemical mechanism unverified.", 'formula-tagged stoichiometric check')
        else:
            r.add('SBML_ELEMENT_BALANCE','OPEN','Elemental-balance evidence unavailable',why)
    else:
        r.add('SBML_ELEMENT_BALANCE','OPEN','Elemental balance blocked by invalid species references',
              'Fix species references before formula-based balance analysis')
    if not duplicates and not missing_species and not negative_stoich:
        cb, why=sbml_charge_balance(species,reactions,tag)
        if cb is not None:
            r.details['charge_balance']=cb
            n=cb['imbalanced_reactions_at_least'];u=cb['unresolved_reactions']
            r.add('SBML_CHARGE_BALANCE','FAIL' if n else ('OPEN' if u else 'PASS'),
                  'Explicit-charge stoichiometric balance',
                  f'{cb["balanced_reactions"]} charge-balanced; {n} charge-imbalanced; {u} unresolved reactions. Declared annotations are assumptions; external electron reservoirs not modeled.',
                  'exact rational charge bookkeeping')
        else:
            r.add('SBML_CHARGE_BALANCE','OPEN','Explicit charge balance not established',why)
    else:
        r.add('SBML_CHARGE_BALANCE','OPEN','Charge balance blocked by invalid species references',
              'Resolve species references before checking charge balance')
    r.add('SBML_FULL_VALIDATION','OPEN' ,'Complete SBML schema/units validation not performed',
          'libSBML validation, simulation stability, parameter identifiability and experimental validity are outside this prototype')
