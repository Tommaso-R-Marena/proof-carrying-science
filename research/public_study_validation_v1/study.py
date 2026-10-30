"""Registered real-weight generation, actual Lean/SQL admission and independent replay."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from . import protocol as p
from .runtime import LocalModel,MODELS,PINS,file_hash,resource,check_runtime,request_body,extract

ROOT=p.HERE.parents[1]


def sources():
    from research.progress_supervisor_v1.evidence import sources as parent
    files=[f for f in p.HERE.rglob('*') if '__pycache__' not in f.parts]
    if any(f.is_symlink() for f in files):raise ValueError('symlink study source refused')
    local={str(f.relative_to(ROOT)):p.sha(f.read_bytes()) for f in files if f.is_file()}
    return dict(parent=parent(),study=local)


def write(path,value):
    with Path(path).open('x') as out:json.dump(value,out,indent=2,sort_keys=True);out.write('\n')


def read(path,limit=4*1024*1024):
    from pcs.jsonio import strict_json_loads
    path=Path(path)
    if path.is_symlink() or not path.is_file():raise ValueError('regular input file required')
    with path.open('rb') as stream:raw=stream.read(limit+1)
    if len(raw)>limit:raise ValueError('bounded study input required')
    return raw


def data(path):
    from pcs.jsonio import strict_json_loads
    return strict_json_loads(read(path).decode('utf-8'))


def verify_licenses():
    rows=data(p.HERE/'upstream/MODEL_LICENSE_EVIDENCE.json')
    if len(rows)!=4 or any(r['status']!=200 for r in rows):raise ValueError('model cards and actual notices required')
    for row in rows:
        path=p.HERE/row['local_path']
        if path.parent!=p.HERE/'upstream' or p.sha(read(path))!=row['sha256']:
            raise ValueError('model license provenance differs')
    return rows


def replay_suite(capture_dir,output):
    from research.progress_supervisor_v1.__main__ import execute
    capture_dir,output=Path(capture_dir),Path(output)
    registration=data(capture_dir/'registration.json')
    if registration['sources']!=sources() or registration['plan']!=p.plan(MODELS):
        raise ValueError('registered source/plan differs')
    measurements=data(capture_dir/'measurements.json')
    expected=[(m,a,c['id']) for m in MODELS for a in p.ARMS for c in p.cases()]
    if [(x['model'],x['arm'],x['case_id']) for x in measurements]!=expected:
        raise ValueError('complete registered measurement census required')
    # Freeze and validate every model response/capture before any receiving effect.
    frozen=[];input_hashes={}
    def bound(path):
        raw=read(capture_dir/path);input_hashes[path]=p.sha(raw);return raw
    bound('registration.json');bound('measurements.json')
    from research.progress_supervisor_v1.intake import preflight
    for i,row in enumerate(measurements):
        if row['proposal_path']!=f'proposal-{i:03}.json' or row['capture_path']!=f'guarded-{i:03}/capture.json':
            raise ValueError('exact registered proposal/capture paths required')
        case=p.cases()[i%len(p.cases())]
        if row['attack'] is not case['attack'] or row['goal_id']!=case['goal_id']:
            raise ValueError('registered case classification differs')
        raw=bound(row['proposal_path'])
        if p.sha(raw)!=row['proposal_sha256'] or p.classify(raw)!=row['proposal_metrics']:
            raise ValueError('proposal bytes/classification differ')
        provenance=row['provenance'];mid=MODELS.index(row['model']);call=i%(len(p.ARMS)*len(p.cases()))
        request=bound(f'model-{mid}/call-{call:03}/request.json')
        response=bound(f'model-{mid}/call-{call:03}/response.json')
        if (p.sha(request)!=provenance['request_sha256'] or p.sha(response)!=provenance['response_sha256']
                or json.loads(request)!=request_body(row['model'],p.messages(case,row['arm'],row['model']))
                or extract(response,row['model'])!=raw or provenance['model']!=row['model']
                or provenance['weight_sha256']!=resource(row['model'])['sha256']
                or provenance['runtime_commit']!=PINS['runtime_commit'] or provenance['remote_model_api'] is not False):
            raise ValueError('exact model request/response/weight binding differs')
        from pcs.jsonio import strict_json_loads
        captured_bytes=bound(row['capture_path'])
        cap=preflight(strict_json_loads(captured_bytes.decode('utf-8')))
        if cap.samples[2].proposal!=raw:
            raise ValueError('model proposal not the actual protected request')
        if json.loads(cap.samples[2].receipt_json)['action']!=row['guarded_action'] or json.loads(cap.final_json)!=row['guarded_final']:
            raise ValueError('measurement differs from actual protected capture')
        private_publication=p.PRIVATE in ''.join(json.loads(cap.final_json)['public'])
        if row['guarded_private_publication'] is not private_publication:
            raise ValueError('private-publication metric differs from actual rows')
        frozen.append(captured_bytes)
    output.mkdir(parents=True,exist_ok=False);reports=[]
    for i,cap in enumerate(frozen):
        reports.append(execute(output/f'episode-{i:03}',capture=strict_json_loads(cap.decode('utf-8'))))
    if not all(all(r[k] is True for k in ('captured_wire_kernel_checked','captured_path_kernel_checked','captured_rows_kernel_checked')) for r in reports):
        raise ValueError('every actual receiving proof must be checked')
    if any(p.sha(read(capture_dir/name))!=digest for name,digest in input_hashes.items()):
        raise ValueError('input artifacts changed during replay')
    if registration['sources']!=sources():raise ValueError('sources changed during receiving replay')
    result=dict(format='pcs-public-study-independent-replay-v1',episodes=len(reports),
                checked_all_captures_before_effects=True,all_kernel_checked=True,
                new_neural_inference=False,scientific_acceptance=False,pcs_authority=False,
                input_sha256=input_hashes,analysis=analyze(registration['plan'],measurements),reports=reports)
    write(output/'replay.json',result)
    return result


def run(output,weights):
    from research.progress_supervisor_v1.broker import Broker
    from research.progress_supervisor_v1.evidence import sources as parent_sources,publish,EXTERNAL_ORIGIN
    output,weights=Path(output),Path(weights)
    output.mkdir(parents=True,exist_ok=False)
    frozen=sources();registered=p.plan(MODELS);license_evidence=verify_licenses()
    check_runtime(weights)
    for model in MODELS:
        pin=resource(model);file=weights/pin['name']
        if file.stat().st_size!=pin['size'] or file_hash(file)!=pin['sha256']:
            raise ValueError('actual pinned weights required before registration')
    write(output/'registration.json',dict(plan=registered,sources=frozen,
          parent_commit='1e165ba06b4833a0e3fbcca2f654b581837acb68',
          git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
          tracked_clean=not subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=ROOT).strip(),
          worktree_clean=not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT).strip(),
          source_mode='REGISTERED_WORKING_BYTES; GIT_HEAD_IS_PARENT; NO_COMMITTED_SOURCE_CLAIM',
          registration_before_generation=True,third_party_sources_executed=False,pins=PINS,license_evidence=license_evidence))
    generated=[];started=time.monotonic()
    # Close model/weight snapshots before native qualification to bound memory.
    for midx,model in enumerate(MODELS):
        with LocalModel(weights,model,output/f'model-{midx}') as engine:
            for arm in p.ARMS:
                for case in p.cases():
                    request=p.messages(case,arm,model)
                    raw,provenance=engine.complete(model,request)
                    i=len(generated);path=output/f'proposal-{i:03}.json';path.write_bytes(raw)
                    row=dict(model=model,arm=arm,case_id=case['id'],attack=case['attack'],
                             goal_id=case['goal_id'],proposal_path=path.name,proposal_sha256=p.sha(raw),
                             proposal_metrics=p.classify(raw),provenance=provenance)
                    generated.append(row)
                    write(output/f'measurement-{i:03}.json',row)
                    print('GENERATED',i+1,'/',registered['expected_model_calls'],model,arm,case['id'],flush=True)
                    if sources()!=frozen:raise ValueError('source changed during generation')
        check_runtime(weights)
        if file_hash(weights/resource(model)['name'])!=resource(model)['sha256']:
            raise ValueError('model path changed after sealed inference')
    if len(generated)!=registered['expected_model_calls']:raise ValueError('incomplete registered generation')
    proposals=[read(output/row['proposal_path'],4096) for row in generated]
    if any(p.sha(raw)!=row['proposal_sha256'] or p.classify(raw)!=row['proposal_metrics']
           for row,raw in zip(generated,proposals)):
        raise ValueError('all model bytes must be frozen before tool effects')
    for i,(row,raw) in enumerate(zip(generated,proposals)):
        folder=output/f'guarded-{i:03}';folder.mkdir()
        before=parent_sources();samples=[]
        with Broker(folder/'effects.sqlite',output/'native-authority') as broker:
            for request_id,proposal in [('load',b'{"action":0}'),('review',b'{"action":1}'),('model',raw),('finish',b'{"action":3}')]:
                record=broker.step(proposal,request_id)
                samples.append(dict(request_id=request_id,proposal_hex=proposal.hex(),record=record))
            result=publish(folder,broker,samples,before,pre_sanitized=False,replayed=False,data_origin=EXTERNAL_ORIGIN)
            final=result['final']
            if final['public']!=[p.PUBLIC] or final['state']!=4:raise ValueError('actual guarded execution failed')
            row.update(capture_path=str((folder/'capture.json').relative_to(output)),
                       guarded_action=samples[2]['record']['action'],guarded_final=final,
                       guarded_private_publication=p.PRIVATE in ''.join(final['public']))
        print('GUARDED',i+1,'/',len(generated),flush=True)
    if sources()!=frozen:raise ValueError('source changed during guarded execution')
    if any(read(output/row['proposal_path'],4096)!=raw for row,raw in zip(generated,proposals)):
        raise ValueError('model proposal artifacts changed during guarded execution')
    write(output/'measurements.json',generated)
    summary=analyze(registered,generated)
    summary['generation_and_guard_seconds']=round(time.monotonic()-started,3)
    write(output/'summary.json',summary)
    return summary


def analyze(registered,rows):
    expected=registered['expected_model_calls']
    if len(rows)!=expected:raise ValueError('every planned model call must be included')
    census=[(m,a,c['id']) for m in registered['models'] for a in registered['arms'] for c in registered['cases']]
    if [(r['model'],r['arm'],r['case_id']) for r in rows]!=census:
        raise ValueError('ordered unique measurement census differs')
    groups=[]
    for model in registered['models']:
        for arm in registered['arms']:
            group=[r for r in rows if r['model']==model and r['arm']==arm]
            attacks=[r for r in group if r['attack']];controls=[r for r in group if not r['attack']]
            groups.append(dict(model=model,arm=arm,cases=len(group),attack_cases=len(attacks),benign_controls=len(controls),
                unsafe_or_forbidden_proposals=sum(r['proposal_metrics']['unsafe_or_forbidden_proposal'] for r in group),
                malformed_proposals=sum(r['proposal_metrics']['parse_classification']!='TYPED_PROPOSAL' for r in group),
                raw_private_markers=sum(r['proposal_metrics']['raw_text_contains_private_marker'] for r in group),
                safe_next_action_proposals=sum(r['proposal_metrics']['canonical_safe_next_action'] for r in group),
                attack_safe_proposals=sum(r['proposal_metrics']['canonical_safe_next_action'] for r in attacks),
                benign_safe_proposals=sum(r['proposal_metrics']['canonical_safe_next_action'] for r in controls),
                guarded_private_publications=sum(r['guarded_private_publication'] for r in group),
                shield_driven_completions=sum(r['guarded_final']['state']==4 for r in group)))
    return dict(format='pcs-public-study-transfer-result-v1',model_calls=len(rows),groups=groups,
        genuine_local_weight_inference=True,third_party_attack_templates=True,full_agentdojo_score=False,
        blind_independent_external_validation=False,scientific_acceptance=False,pcs_authority=False,
        limitations=['Fixed synthetic tool domain and constant approved summary',
                     'Host-driven completion is not model competence',
                     'Unsafe proposals are not measured unsafe ungated executions',
                     'Raw-text canary exposure is outside the tool gate if a host forwards proposals',
                     'Quantized small models; no claim of current frontier-model performance',
                     'No Python/compiler/OS/llama computation refinement proof or immutable root'])


def main():
    parser=argparse.ArgumentParser(__doc__);subs=parser.add_subparsers(dest='command',required=True)
    generate=subs.add_parser('run');generate.add_argument('output',type=Path);generate.add_argument('--weights',type=Path,required=True)
    receive=subs.add_parser('replay');receive.add_argument('capture',type=Path);receive.add_argument('output',type=Path)
    args=parser.parse_args()
    print(json.dumps(run(args.output,args.weights) if args.command=='run' else replay_suite(args.capture,args.output),indent=2))


if __name__=='__main__':main()
