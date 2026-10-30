"""Versioned receiving hardening; original generation source/evidence stays exact.

Freeze each header from the SAME bytes used for its digest and parse. Preflight
ALL captures and recheck all named input bytes before any receiving tool effects.
After admission, re-execution uses only frozen capture bytes, never mutable paths.
This is ordinary trusted host behavior, not an immutable storage/process root.
"""
from pathlib import Path
import argparse
import json
from dataclasses import dataclass

from pcs.jsonio import strict_json_loads
from research.public_study_validation_v1 import study as s, protocol as p
from research.public_study_validation_v1.runtime import MODELS, PINS, resource, request_body, extract
from research.progress_supervisor_v1.intake import preflight

HERE=Path(__file__).resolve()


@dataclass(frozen=True)
class FrozenStudy:
    registration: bytes
    measurements: bytes
    captures: tuple[bytes,...]
    input_sha256: tuple[tuple[str,str],...]


def freeze(capture_dir):
    root=Path(capture_dir);hashes={}
    def bound(name):
        raw=s.read(root/name);hashes[name]=p.sha(raw);return raw
    regraw=bound('registration.json');rowsraw=bound('measurements.json')
    registration=strict_json_loads(regraw.decode('utf-8'))
    rows=strict_json_loads(rowsraw.decode('utf-8'))
    if (registration['sources']!=s.sources() or registration['plan']!=p.plan(MODELS)
            or registration['pins']!=PINS or registration['license_evidence']!=s.verify_licenses()):
        raise ValueError('exact registered source/plan/pins/license evidence required')
    expected=[(m,a,c['id']) for m in MODELS for a in p.ARMS for c in p.cases()]
    if [(r['model'],r['arm'],r['case_id']) for r in rows]!=expected:
        raise ValueError('complete ordered unique measurement census required')
    frozen=[]
    for i,row in enumerate(rows):
        if row['proposal_path']!=f'proposal-{i:03}.json' or row['capture_path']!=f'guarded-{i:03}/capture.json':
            raise ValueError('exact indexed proposal/capture paths required')
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
                or strict_json_loads(request.decode())!=request_body(row['model'],p.messages(case,row['arm'],row['model']))
                or extract(response,row['model'])!=raw or provenance['model']!=row['model'] or provenance['call']!=call
                or provenance['weight_sha256']!=resource(row['model'])['sha256']
                or provenance['runtime_commit']!=PINS['runtime_commit'] or provenance['remote_model_api'] is not False):
            raise ValueError('exact recorded model request/response/identity binding differs')
        capraw=bound(row['capture_path']);cap=preflight(strict_json_loads(capraw.decode('utf-8')))
        if cap.samples[2].proposal!=raw:
            raise ValueError('model proposal differs from protected capture')
        if json.loads(cap.samples[2].receipt_json)['action']!=row['guarded_action'] or json.loads(cap.final_json)!=row['guarded_final']:
            raise ValueError('measurement differs from captured effects')
        private=p.PRIVATE in ''.join(json.loads(cap.final_json)['public'])
        if row['guarded_private_publication'] is not private:
            raise ValueError('private publication metric differs')
        frozen.append(capraw)
    # A rewrite during preflight fails before output/native build/tool commitment.
    if any(p.sha(s.read(root/name))!=digest for name,digest in hashes.items()):
        raise ValueError('input changed during complete preflight')
    if registration['sources']!=s.sources():raise ValueError('registered sources changed')
    return FrozenStudy(regraw,rowsraw,tuple(frozen),tuple(hashes.items()))


def replay(capture_dir,output):
    from research.progress_supervisor_v1.__main__ import execute
    source=HERE.read_bytes();snapshot=freeze(capture_dir)
    registration=strict_json_loads(snapshot.registration.decode())
    measurements=strict_json_loads(snapshot.measurements.decode())
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    s.write(output/'receiving-admission.json',dict(format='pcs-public-study-frozen-receiving-admission-v2',
        receiver_sha256=p.sha(source),inputs_sha256=dict(snapshot.input_sha256),
        all_captures_checked_before_effects=True,new_neural_inference=False,
        recorded_generation_is_not_reproved=True,pcs_authority=False))
    reports=[]
    for i,capraw in enumerate(snapshot.captures):
        reports.append(execute(output/f'episode-{i:03}',capture=strict_json_loads(capraw.decode('utf-8'))))
        print('RECEIVED',i+1,'/',len(snapshot.captures),flush=True)
    if not all(all(r[k] is True for k in ('captured_wire_kernel_checked','captured_path_kernel_checked','captured_rows_kernel_checked')) for r in reports):
        raise ValueError('every real receiving proof must be checked')
    if any(p.sha(s.read(Path(capture_dir)/name))!=digest for name,digest in snapshot.input_sha256):
        raise ValueError('input artifacts changed during replay')
    if registration['sources']!=s.sources() or HERE.read_bytes()!=source:
        raise ValueError('source changed during replay')
    result=dict(format='pcs-public-study-independent-replay-v2',episodes=len(reports),
        checked_all_captures_before_effects=True,all_kernel_checked=True,
        single_header_snapshot=True,capture_bytes_frozen_before_effects=True,
        receiver_sha256=p.sha(source),new_neural_inference=False,
        scientific_acceptance=False,pcs_authority=False,
        input_sha256=dict(snapshot.input_sha256),analysis=s.analyze(registration['plan'],measurements),reports=reports)
    s.write(output/'replay.json',result)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(__doc__);parser.add_argument('capture');parser.add_argument('output')
    args=parser.parse_args();print(json.dumps(replay(args.capture,args.output),indent=2))
