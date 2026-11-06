"""Closed, source-bound research checks. No imported proof or code is executed."""
from __future__ import annotations
import ast
import csv
import hashlib
import io
import re
import tempfile
import time
from fractions import Fraction
from pathlib import Path

from pcs.jsonio import strict_json_loads
from .intake import MAX_FILE, _regular, adapter_observation
from .knowledge import build_graph

VERSION = 'scientific-checks-1.0'
SUPPORTED = frozenset({'csv_rows','csv_numeric','ols_optimality','sequence_length','coordinate_count',
                       'sequence_matches_structure','json_field','python_import','lean_closed'})


def bound_bytes(artifact):
    raw = _regular(artifact['snapshot_path'], MAX_FILE)
    if len(raw) != artifact['size'] or hashlib.sha256(raw).hexdigest() != artifact['sha256']:
        raise ValueError('source byte binding failed')
    return raw


def bindings_valid(obligation, artifacts):
    bindings=obligation['source_bindings']
    if len({b['artifact_id'] for b in bindings}) != len(bindings):raise ValueError('duplicate binding')
    if set(obligation['artifact_ids']) != {b['artifact_id'] for b in bindings}:raise ValueError('dependency mismatch')
    for b in bindings:
        a=artifacts[b['artifact_id']]
        if b != {k:a[k if k!='artifact_id' else 'id'] for k in ('artifact_id','sha256','size')}:raise ValueError('metadata binding failed')
        bound_bytes(a)


def _validate_proposal(obligation, artifacts):
    """Re-extract source and reproduce lowering rather than trusting a payload."""
    source_id=obligation['source']['artifact_id'];source=artifacts[source_id]
    source=dict(source);parsed=adapter_observation(source['path'],source['snapshot_path'])
    for segment in parsed.get('segments',[]):
        segment['locator']['source_sha256']=source['sha256']
    source.update(parsed)
    inputs=[source if a['id']==source_id else {**a,'segments':[]} for a in artifacts.values()]
    graph=build_graph(inputs)
    if obligation not in graph['obligations']:raise ValueError('obligation not reproduced from exact source')


def _number(value):
    if not isinstance(value,str) or len(value)>128 or not re.fullmatch(r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?',value):raise ValueError('not a bounded exact decimal')
    if 'e' in value.lower() and abs(int(value.lower().split('e')[1]))>1000:raise ValueError('exponent bound')
    return Fraction(value)


def _csv(raw, path):
    reader=csv.DictReader(io.StringIO(raw.decode('utf-8'),newline=''),delimiter='\t' if path.endswith('.tsv') else ',',strict=True)
    if not reader.fieldnames or len(set(reader.fieldnames))!=len(reader.fieldnames):raise ValueError('invalid CSV schema')
    rows=list(reader)
    if len(rows)>10000 or any(None in row or any(v is None for v in row.values()) for row in rows):raise ValueError('invalid CSV rows')
    return rows


def _fasta(raw):
    records={};name=None
    for line in raw.decode('utf-8').splitlines():
        line=line.strip()
        if not line:continue
        if line.startswith('>'):
            name=line[1:].split()[0]
            if name in records:raise ValueError('duplicate sequence ID')
            records[name]=''
        else:
            if name is None or not re.fullmatch('[A-Za-z*.-]+',line):raise ValueError('invalid FASTA')
            records[name]+=line.upper()
    if not records or any(not x for x in records.values()):raise ValueError('empty sequence')
    return records


AMINO=dict(zip(('ALA ARG ASN ASP CYS GLN GLU GLY HIS ILE LEU LYS MET PHE PRO SER THR TRP TYR VAL').split(),'ARNDCQEGHILKMFPSTWYV'))


def _atoms(raw,path):
    if path.lower().endswith('.pdb'):
        result=[]
        for line in raw.decode('utf-8').splitlines():
            if line[:6].strip() in {'ATOM','HETATM'}:
                if len(line)<54:raise ValueError('truncated coordinate')
                result.append({'record':line[:6].strip(),'chain':line[21].strip(),'residue_number':int(line[22:26]),'insertion_code':line[26].strip(),'residue_name':line[17:20].strip(),'model':1})
        return result
    from .bio_adapters import extract_mmcif
    return [s['data'] for s in extract_mmcif(raw.decode('utf-8')) if s['kind']=='structure_atom']


def _lean(payload):
    # Strict existing IR renderers construct a closed statement. Imported proof
    # text never reaches Lean. One-shot verification does not launch a worker.
    from pcs.experimental.prover.environment import LeanEnvironment
    from pcs.experimental.prover.induction_language import formalize,parse_lean
    if payload['language']=='controlled_english':
        lowered=formalize(payload['input_statement'])
        if lowered.get('status')!='supported' or len(lowered['candidates'])!=1:raise ValueError('ambiguous mathematical meaning')
        goal=lowered['candidates'][0]['ir']
    else:goal=parse_lean(payload['input_statement'])
    if goal!=payload['ir']:raise ValueError('typed IR does not match source')
    # Fixed safe tactic sequence, independently checked, no search predictions.
    binders=len(goal.get('binders',[]));body=goal['body']
    while body.get('op')=='forall':binders+=1;body=body['body']
    if binders>12:raise ValueError('binder limit')
    actions=[{'kind':'intro','argument':f'h{i}'} for i in range(binders)]
    with tempfile.TemporaryDirectory(prefix='pcs-science-lean-') as scratch:
        env=LeanEnvironment(cache=scratch,timeout=20)
        try:
            for final in ({'kind':'rfl','argument':None},{'kind':'normalize','argument':'list' if any(b['type']=='NatList' for b in goal['binders']) else 'nat'}):
                try:return env.verify(goal,actions+[final])
                except RuntimeError:pass
        finally:env.close()
    return None


def execute(obligation, artifacts_by_id, root=None, cache=None, budget=None):
    started=time.monotonic()
    result={'format':'pcs-scientific-check-v1','obligation_id':obligation.get('id'),
            'checker':obligation.get('checker'),'checker_version':VERSION,'status':'UNKNOWN',
            'category':'research_observation','source_bindings':obligation.get('source_bindings',[]),
            'assumptions':obligation.get('assumptions',[]),'authority':False,
            'scientific_meaning':'OPEN','evidence':{}}
    try:
        bindings_valid(obligation,artifacts_by_id)
        _validate_proposal(obligation,artifacts_by_id)
        checker=obligation['checker'];p=obligation['payload']
        if checker not in SUPPORTED:
            result.update(status='UNSUPPORTED',evidence={'reason':p.get('reason','Human review required')})
            return result
        if checker=='lean_closed':
            receipt=_lean(p)
            bindings_valid(obligation,artifacts_by_id)
            if receipt is None:result['evidence']={'reason':'Bounded independent proof attempts did not close the claim'}
            else:result.update(status='VERIFIED_SUPPORTED',category='kernel_proof_of_closed_typed_statement',evidence={'receipt':receipt})
            return result
        artifact=artifacts_by_id[p['artifact_id']];raw=bound_bytes(artifact)
        if checker in {'csv_rows','csv_numeric'}:
            rows=_csv(raw,artifact['path'])
            if checker=='csv_rows':actual=len(rows);expected=int(p['expected'])
            else:
                values=[_number(row[p['column']]) for row in rows]
                if not values and p['operation']=='mean':raise ValueError('empty mean')
                actual=sum(values,Fraction(0))
                if p['operation']=='mean':actual/=len(values)
                expected=_number(p['expected'])
        elif checker=='ols_optimality':
            fit=artifacts_by_id[p['fit_artifact_id']]
            certificate=strict_json_loads(bound_bytes(fit).decode('utf-8'))
            degree=certificate['degree']
            if type(degree) is not int or not 0<=degree<=4:raise ValueError('unsupported design degree')
            if certificate['design']!=['1']+['x' if i==1 else f'x^{i}' for i in range(1,degree+1)]:raise ValueError('design schema mismatch')
            def rational(value):
                if not isinstance(value,str) or len(value)>2048 or not re.fullmatch(r'[+-]?[0-9]+(?:/[1-9][0-9]*)?',value):raise ValueError('unsupported rational encoding')
                return Fraction(value)
            if type(certificate['coefficients_rational']) is not list or type(certificate['observations']) is not int:raise ValueError('invalid certificate schema')
            coefficients=[rational(v) for v in certificate['coefficients_rational']]
            if len(coefficients)!=degree+1:raise ValueError('coefficient dimension mismatch')
            pairs=[(_number(row['x']),_number(row['y'])) for row in _csv(raw,artifact['path'])]
            if not pairs or len(pairs)>1000:raise ValueError('bounded regression rows required')
            design=[[x**i for i in range(degree+1)] for x,y in pairs]
            residuals=[y-sum((b*x for b,x in zip(coefficients,row)),Fraction()) for row,(x,y) in zip(design,pairs)]
            normal=[sum((row[i]*r for row,r in zip(design,residuals)),Fraction()) for i in range(degree+1)]
            sse=sum((r*r for r in residuals),Fraction())
            actual=all(v==0 for v in normal) and sse==rational(certificate['sse_rational']) and certificate['observations']==len(pairs)
            expected=p['expected']=='true'
            result['evidence'].update(normal_residuals=[str(v) for v in normal],sse_rational=str(sse),
                                      scope='Exact finite rational normal equations and squared residuals. General least-squares optimality is a mathematical consequence; Python refinement is not kernel-proved.')
        elif checker=='sequence_length':actual=len(_fasta(raw)[p['sequence_id']]);expected=int(p['expected'])
        elif checker=='coordinate_count':actual=len(_atoms(raw,artifact['path']));expected=int(p['expected'])
        elif checker=='sequence_matches_structure':
            structure=artifacts_by_id[p['structure_artifact_id']]
            atoms=_atoms(bound_bytes(structure),structure['path'])
            residues={}
            for atom in atoms:
                if atom['record']=='ATOM' and atom['chain']==p['chain']:
                    key=(atom['residue_number'],atom.get('insertion_code',''))
                    residue=atom['residue_name']
                    if key in residues and residues[key]!=residue:raise ValueError('conflicting residue identities')
                    residues[key]=residue
            sequence=''.join(AMINO[name] for key,name in sorted(residues.items()))
            if not residues:raise ValueError('no supported chain residues')
            actual=sequence in _fasta(raw).values();expected=p['expected']=='true'
        elif checker=='json_field':
            value=strict_json_loads(raw.decode('utf-8'));pointer=p['pointer'];actual=True
            if pointer and not pointer.startswith('/'):raise ValueError('invalid JSON pointer')
            for part in pointer.split('/')[1:] if pointer else []:
                part=part.replace('~1','/').replace('~0','~')
                try:
                    if isinstance(value,list):
                        if not re.fullmatch('0|[1-9][0-9]*',part):raise KeyError(part)
                        value=value[int(part)]
                    else:value=value[part]
                except (IndexError,KeyError,TypeError):actual=False;break
            expected=p['expected']=='true'
        elif checker=='python_import':
            tree=ast.parse(raw.decode('utf-8'));modules=set()
            for node in ast.walk(tree):
                if isinstance(node,ast.Import):modules.update(a.name for a in node.names)
                elif isinstance(node,ast.ImportFrom):modules.add(node.module or '')
            actual=p['module'] in modules;expected=p['expected']=='true'
        else:raise ValueError('unreachable checker')
        # Recheck every dependency after checking; execution used these exact
        # in-memory bytes. Same-host memory/process compromise remains outside.
        bindings_valid(obligation,artifacts_by_id)
        result.update(status='VERIFIED_SUPPORTED' if actual==expected else 'REFUTED',
                      evidence={**result['evidence'],'actual':str(actual),'expected':str(expected),'comparison':'exact'})
    except (OSError,ValueError,KeyError,TypeError,RuntimeError,RecursionError,OverflowError,ImportError,SyntaxError,IndexError,csv.Error,ZeroDivisionError) as exc:
        result.update(status='UNKNOWN',evidence={'reason':str(exc)[:1000],'error_type':type(exc).__name__})
    finally:result['seconds']=time.monotonic()-started
    return result
