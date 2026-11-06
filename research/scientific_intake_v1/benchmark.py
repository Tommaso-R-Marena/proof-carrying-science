"""Frozen-label scientific intake evaluation; final split is never training data."""
from __future__ import annotations
import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import platform
import resource
import sys
import time

from .intake import canonical,digest
from .projects import materialize_projects
from .pipeline import run,replay,stable_result
from .cache import checker_context

PROTOCOL={
    'format':'pcs-scientific-intake-evaluation-v1','training':[],
    'split_policy':'development: 1CRN/Norris/Nat; final:1UBQ/Pontius/List. Frozen IDs and source-selection amendment retained in fixtures. No project is model training data.',
    'conditions':['deterministic_cold','deterministic_warm','learned_schema_fallback'],
    'budget_work_units':1000.,'model_selection':'None. Both earlier trained model families are retained unchanged. No compatible scientific schema is claimed.',
    'labels':'Annotations authored by deterministic source-derived fixture constructors before evaluation, stored outside input. Not independent human expert labels.',
    'matching':'Exact statement and source path; verification obligation matched separately from meaning review.',
    'metrics':['parsing_status','annotated_claim_recall','annotated_check_agreement','exact_source_quote_grounding','unsupported_promotion','checker_calls','wall_seconds','CPU_seconds','peak_RSS','replay'],
    'scope':'Narrow explicit claim grammar, bounded mathematical fragment, exact file observations. Not general paper comprehension or biological validation.',
    'final_rule':'Run only after component source digest is frozen. Retain failures; repair validation defects with recorded reruns, never relabel cases.'}


def _write(path,value):Path(path).write_bytes(canonical(value)+b'\n')


def _evaluate(record, directory):
    graph=json.loads((directory/'graph.json').read_text());results=json.loads((directory/'checks.json').read_text())
    obligations={o['id']:o for o in graph['obligations']};by_claim={obligations[r['obligation_id']]['claim_id']:r for r in results}
    rows=[]
    for annotation in record['annotations']:
        candidates=[c for c in graph['claims'] if c['statement']==annotation['statement'] and
                    next(a['path'] for a in graph['artifacts'] if a['id']==c['source']['artifact_id'])==annotation['source_path']]
        found=len(candidates)==1
        if found:
            claim=candidates[0];result=by_claim.get(claim['id'])
            status=result['status'] if result else 'UNSUPPORTED' if annotation['checker']=='unsupported' else 'UNCHECKED'
            grounded=claim['source']['quote']==annotation['origin']['quote'] and claim['source']['sha256']==annotation['origin']['sha256']
        else:status='NOT_FOUND';grounded=False
        rows.append({'annotation_id':annotation['id'],'statement':annotation['statement'],'found':found,
                     'grounded':grounded,'expected':annotation['expected_status'],'actual':status,
                     'agreement':found and status==annotation['expected_status'],'scientific_acceptance':False})
    quote_grounded=0;total=0
    arts={a['id']:a for a in graph['artifacts']}
    for c in graph['claims']:
        total+=1;a=arts[c['source']['artifact_id']]
        quote_grounded+=any(s['text']==c['source']['quote'] and s['locator']==c['source']['locator'] for s in a['segments'])
    return {'annotations':rows,'annotation_count':len(rows),'found':sum(r['found'] for r in rows),
            'annotation_agreement':sum(r['agreement'] for r in rows),'annotated_grounded':sum(r['grounded'] for r in rows),
            'source_grounding':{'matching_extracted_spans':quote_grounded,'claims':total,
                'interpretation':'Exact match to retained extraction spans; not independent confirmation of PDF/OCR accuracy or scientific interpretation.'},
            'unsupported_promotions':sum(r['actual']=='VERIFIED_SUPPORTED' and r['expected'] in {'UNSUPPORTED','REFUTED','UNKNOWN'} for r in rows),
            'assessed_meaning_correctness':False}


def _numeric_oracle(record):
    if record['domain']!='regression':return None
    # Numerically independent SVD least-squares oracle, not reused rational
    # Gaussian elimination, on original-derived CSV. No source code executes.
    import csv
    import numpy as np
    from fractions import Fraction
    root=Path(record['path']);cert=json.loads((root/'ols_experiment.json').read_text())
    data=list(csv.DictReader((root/'data.csv').open()))
    x=np.array([float(r['x']) for r in data]);y=np.array([float(r['y']) for r in data]);degree=cert['degree']
    # Scale x for SVD conditioning and transform coefficients back.
    scale=max(abs(x));design=np.stack([(x/scale)**i for i in range(degree+1)],axis=1)
    fitted,_,rank,_=np.linalg.lstsq(design,y,rcond=None)
    coeff=fitted/np.array([scale**i for i in range(degree+1)])
    exact=np.array([float(Fraction(v)) for v in cert['coefficients_rational']])
    prediction=design@fitted;exact_prediction=np.stack([x**i for i in range(degree+1)],axis=1)@exact
    return {'method':'independent NumPy SVD least squares with scaled design','numpy':np.__version__,
            'rows':len(data),'degree':degree,'rank':int(rank),'coefficients_float':coeff.tolist(),
            'certificate_coefficients_float':exact.tolist(),'max_prediction_difference':float(abs(prediction-exact_prediction).max()),
            'sse_float':float(((y-prediction)**2).sum()),'certificate_sse_float':float(Fraction(cert['sse_rational'])),
            'allclose_prediction_atol_1e-7_rtol_1e-10':bool(np.allclose(prediction,exact_prediction,atol=1e-7,rtol=1e-10)),
            'formal_authority':False}


def incremental_experiment(output):
    root=Path(output);root.mkdir(parents=True);source=root/'input';source.mkdir()
    (source/'data.csv').write_text('x\n1\n2\n3\n')
    (source/'config.json').write_text('{"task":"calibration"}')
    (source/'claims.md').write_text('PCS-CLAIM: rows(data.csv)=3\nPCS-CLAIM: sum(data.csv,x)=6\n')
    rows=[]
    for step in ('initial','unchanged','unrelated_edit','dependency_edit'):
        if step=='unrelated_edit':(source/'readme.txt').write_text('An unrelated source note with no checkable assertion.')
        if step=='dependency_edit':(source/'data.csv').write_text('x\n1\n2\n4\n')
        result=run(source,root/step,check=True,cache_dir=root/'host-cache')
        rows.append({'step':step,'summary':result})
    independent=replay(root/'dependency_edit')
    return {'scope':'First-party controlled dependency mutation; finite empirical result, not Python refinement proof.',
            'rows':rows,'changed_source_replay':independent,
            'unchanged_saved_calls':rows[0]['summary']['checker_calls']-rows[1]['summary']['checker_calls'],
            'unrelated_edit_reused':rows[2]['summary']['checker_calls']==0,
            'dependency_edit_rechecked':rows[3]['summary']['checker_calls']>0 and rows[3]['summary']['cache_hits']>0}


def benchmark(output,*,split='development'):
    output=Path(output).absolute()
    if output.exists():raise ValueError('refuse benchmark overwrite')
    output.mkdir(parents=True,mode=0o700)
    context=checker_context();freeze={'protocol':PROTOCOL,'protocol_sha256':digest(PROTOCOL),'context':context,
                                    'context_sha256':digest(context),'frozen_unix_ns':time.time_ns()}
    # Written before any final materialization, model inference or case opening.
    _write(output/'freeze.json',freeze)
    records=materialize_projects(output/'projects',split=split);cases=[]
    for record in records:
        case_root=output/'runs'/record['id'];case_root.mkdir(parents=True)
        conditions=[];cache=output/'cache'/record['id']
        for condition in PROTOCOL['conditions']:
            start=time.monotonic();cpu=time.process_time();child_cpu=resource.getrusage(resource.RUSAGE_CHILDREN)
            target=case_root/condition
            summary=run(record['path'],target,check=True,
                        cache_dir=cache if condition!='learned_schema_fallback' else None,
                        mode='learned' if condition=='learned_schema_fallback' else 'deterministic',budget=PROTOCOL['budget_work_units'])
            after=resource.getrusage(resource.RUSAGE_CHILDREN)
            conditions.append({'condition':condition,'summary':summary,'evaluation':_evaluate(record,target),
                'wall_seconds':time.monotonic()-start,'parent_CPU_seconds':time.process_time()-cpu,
                'child_CPU_seconds':after.ru_utime+after.ru_stime-child_cpu.ru_utime-child_cpu.ru_stime,
                'peak_parent_RSS_KiB':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                'peak_child_RSS_KiB':after.ru_maxrss,
                'memory_scope':'process high-water marks; cumulative across earlier cases, not isolated per case'})
        replay_result=replay(case_root/'deterministic_cold')
        def verdicts(condition):
            return sorted((r['obligation_id'],r['status'],r['evidence']) for r in json.loads((case_root/condition/'checks.json').read_text()))
        same=verdicts('deterministic_cold')==verdicts('deterministic_warm')==verdicts('learned_schema_fallback')
        cases.append({'id':record['id'],'split':record['split'],'domain':record['domain'],'license':record['license'],
                      'annotation_sha256':record['annotation_sha256'],'conditions':conditions,
                      'same_verdicts':same,'independent_replay':replay_result,'numeric_oracle':_numeric_oracle(record)})
        _write(output/'partial.json',cases)
    if checker_context()!=context:raise ValueError('component source changed during frozen evaluation')
    report={'format':'pcs-scientific-intake-benchmark-v1','split':split,'freeze_sha256':digest(freeze),'protocol':PROTOCOL,
            'python':sys.version,'platform':platform.platform(),'cases':cases,
            'incremental':incremental_experiment(output/'incremental'),'training_performed':False,
            'scientific_claims_certified':0,'authority':'NONE',
            'scope':'Finite internal source-derived evaluation; not external scientific validation or neural superiority.'}
    _write(output/'results.json',report)
    return report


def validate_report(report):
    return (report['incremental']['unrelated_edit_reused'] and report['incremental']['dependency_edit_rechecked'] and bool(report['cases']) and all(c['same_verdicts'] and c['independent_replay']['status']=='REPLAYED'
        and all(v['evaluation']['annotation_agreement']==v['evaluation']['annotation_count']
                and v['evaluation']['unsupported_promotions']==0 for v in c['conditions'])
        and (c['numeric_oracle'] is None or c['numeric_oracle']['allclose_prediction_atol_1e-7_rtol_1e-10'])
        for c in report['cases']))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True);p.add_argument('--split',choices=['development','final','all'],default='development');a=p.parse_args()
    report=benchmark(a.output,split=a.split)
    print(json.dumps({'split':report['split'],'cases':[{'id':c['id'],'same_verdicts':c['same_verdicts'],'annotation_agreement':c['conditions'][0]['evaluation']['annotation_agreement'],'annotations':c['conditions'][0]['evaluation']['annotation_count'],'replay':c['independent_replay']} for c in report['cases']]},indent=2))
    if not validate_report(report):raise SystemExit('Evaluation discrepancies retained in results.json')
if __name__=='__main__':main()
