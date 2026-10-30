"""Post-study recovery of an interrupted producer; never rerun/select model responses.

Existing capture bytes are retained as producer evidence, NOT adopted as an
execution verdict. A complete independent receiving pass is still required.
No prior SQLite ledger or executable is resumed/adopted. Partial outputs remain.
"""
import json
from pathlib import Path
import shutil
import sys
import time

from research.public_study_validation_v1 import study as s, protocol as p
from research.public_study_validation_v1.runtime import MODELS, PINS, resource, request_body, extract
from research.progress_supervisor_v1.broker import Broker
from research.progress_supervisor_v1.evidence import sources as parent_sources, publish, EXTERNAL_ORIGIN
from research.progress_supervisor_v1.intake import preflight
from pcs.jsonio import strict_json_loads


def finish(original, output):
    original,output=Path(original),Path(output)
    registration=s.data(original/'registration.json')
    if registration['sources']!=s.sources() or registration['plan']!=p.plan(MODELS) or registration['pins']!=PINS:
        raise ValueError('exact original registered source/plan/runtime required')
    expected=[(m,a,c) for m in MODELS for a in p.ARMS for c in p.cases()]
    frozen={};rows=[];captures={}
    def bound(name):
        raw=s.read(original/name);frozen[name]=raw;return raw
    bound('registration.json')
    # Freeze and validate EVERY original generated request/response before effects.
    for i,(model,arm,case) in enumerate(expected):
        row=strict_json_loads(bound(f'measurement-{i:03}.json').decode())
        if (row['model'],row['arm'],row['case_id'],row['attack'],row['goal_id'])!=(model,arm,case['id'],case['attack'],case['goal_id']):
            raise ValueError('original complete ordered generation census required')
        name=f'proposal-{i:03}.json'
        raw=bound(name)
        if row['proposal_path']!=name or row['proposal_sha256']!=p.sha(raw) or row['proposal_metrics']!=p.classify(raw):
            raise ValueError('original proposal differs')
        mid=MODELS.index(model);call=i%36;provenance=row['provenance']
        req=bound(f'model-{mid}/call-{call:03}/request.json')
        resp=bound(f'model-{mid}/call-{call:03}/response.json')
        if (json.loads(req)!=request_body(model,p.messages(case,arm,model)) or extract(resp,model)!=raw
                or provenance['request_sha256']!=p.sha(req) or provenance['response_sha256']!=p.sha(resp)
                or provenance['model']!=model or provenance['call']!=call
                or provenance['weight_sha256']!=resource(model)['sha256']
                or provenance['runtime_commit']!=PINS['runtime_commit'] or provenance['remote_model_api'] is not False):
            raise ValueError('original raw generation binding differs')
        capture=f'guarded-{i:03}/capture.json'
        if (original/capture).is_file():
            capraw=bound(capture);cap=preflight(strict_json_loads(capraw.decode()))
            if cap.samples[2].proposal!=raw or json.loads(cap.final_json)['public']!=[p.PUBLIC] or json.loads(cap.final_json)['state']!=4:
                raise ValueError('existing capture disagrees with original generation')
            # Preserve existing completion and proof sources, never execute supplied code.
            bound(f'guarded-{i:03}/result.json')
            for proof in sorted((original/f'guarded-{i:03}'/'proofs').glob('*.lean')):
                bound(str(proof.relative_to(original)))
            captures[i]=cap
        rows.append(row)
    for mid in range(len(MODELS)):
        for name in ('binding.json','props.json','server.log'):
            bound(f'model-{mid}/{name}')
    if registration['sources']!=s.sources():raise ValueError('source changed during input validation')
    output.mkdir(parents=True,exist_ok=False)
    for name,raw in frozen.items():
        dest=output/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
    s.write(output/'recovery.json',dict(format='pcs-interrupted-producer-recovery-v1',
        original_path=str(original),original_model_calls=len(rows),new_model_calls=0,
        reused_capture_indices=list(captures),new_capture_indices=[i for i in range(len(rows)) if i not in captures],
        prior_ledgers_adopted=False,prior_executables_adopted=False,prior_proofs_executed=False,
        complete_receiving_replay_still_required=True,
        input_sha256={name:p.sha(raw) for name,raw in frozen.items()}))
    started=time.monotonic()
    for i,row in enumerate(rows):
        if i in captures:
            cap=captures[i];final=json.loads(cap.final_json);action=json.loads(cap.samples[2].receipt_json)['action']
        else:
            folder=output/f'guarded-{i:03}';folder.mkdir();samples=[];before=parent_sources()
            with Broker(folder/'effects.sqlite',output/'native-authority') as broker:
                for rid,raw in [('load',b'{"action":0}'),('review',b'{"action":1}'),('model',frozen[row['proposal_path']]),('finish',b'{"action":3}')]:
                    record=broker.step(raw,rid);samples.append(dict(request_id=rid,proposal_hex=raw.hex(),record=record))
                result=publish(folder,broker,samples,before,pre_sanitized=False,replayed=False,data_origin=EXTERNAL_ORIGIN)
                final=result['final'];action=samples[2]['record']['action']
                if final['public']!=[p.PUBLIC] or final['state']!=4:raise ValueError('guarded completion failed')
        row.update(capture_path=f'guarded-{i:03}/capture.json',guarded_action=action,guarded_final=final,
                   guarded_private_publication=p.PRIVATE in ''.join(final['public']))
        print('COMPLETE',i+1,'/',len(rows),'preserved' if i in captures else 'fresh',flush=True)
    if registration['sources']!=s.sources():raise ValueError('source changed during recovery')
    if any(s.read(original/name)!=raw for name,raw in frozen.items()):raise ValueError('original evidence changed')
    if any(s.read(output/name)!=raw for name,raw in frozen.items()):raise ValueError('copied evidence changed')
    s.write(output/'measurements.json',rows)
    result=s.analyze(registration['plan'],rows)
    result['recovery_seconds']=round(time.monotonic()-started,3)
    result['interrupted_producer_recovered']=True
    s.write(output/'summary.json',result)
    return result


if __name__=='__main__':print(json.dumps(finish(*sys.argv[1:]),indent=2))
