"""Prospective source/annotation/model frozen scientific review experiment."""
from pathlib import Path
import hashlib
import json
import resource
import time
from .pipeline import run,replay,portable_inventory,context
from .corpus import materialize
from .reference import load_reference
from .evaluation import FROZEN_PROTOCOL,protocol_sha256,grade_reference,evaluate_retrieval
from .adversarial import campaign
from research.scientific_intake_v1.intake import digest,canonical


def benchmark(output,*,split='development',adversarial=True):
    output=Path(output)
    if output.exists():raise ValueError('refuse benchmark overwrite')
    output.mkdir(parents=True,mode=0o700);here=Path(__file__).parent
    ctx=context()
    freeze={'format':'pcs-scientific-understanding-freeze-v2','context':ctx,'context_sha256':digest(ctx),'protocol':FROZEN_PROTOCOL,'protocol_sha256':protocol_sha256(),
            'source_preregistration_sha256':hashlib.sha256((here/'preregistration.json').read_bytes()).hexdigest(),
            'reference_annotation_freeze_sha256':hashlib.sha256((here/'reference/annotation_freeze.json').read_bytes()).hexdigest(),
            'retrieval_checkpoint_sha256':hashlib.sha256((here/'learning/artifacts/scientific_encoder.json').read_bytes()).hexdigest(),
            'frozen_unix_ns':time.time_ns(),'training_on_projects':False,'split':split}
    (output/'freeze.json').write_bytes(canonical(freeze)+b'\n')
    # Final labels/sources first enter the integrated system after this freeze.
    records=materialize(output/'projects',split=split)
    references=load_reference(split,allow_final=split=='final');annotations=references['annotations'] if isinstance(references,dict) else references
    cases=[]
    for record in records:
        name=record['id'];folder=output/name;start=time.monotonic();cpu=time.process_time();before=resource.getrusage(resource.RUSAGE_CHILDREN)
        summary=run(record['path'],folder,check=True,cache_dir=output/'host-cache'/name)
        latency=time.monotonic()-start;child=resource.getrusage(resource.RUSAGE_CHILDREN)
        inv=portable_inventory(folder/'intake');interpretations=json.loads((folder/'interpretations.json').read_text());checks=json.loads((folder/'checks.json').read_text())
        reference=[a for a in annotations if a['project_id']==name]
        grading=grade_reference(reference,interpretations,inv,checks=checks);retrieval=evaluate_retrieval(reference,interpretations,inv)
        replayed=replay(folder)
        cases.append({'id':name,'split':split,'summary':summary,'reference':grading,'retrieval':retrieval,'replay':replayed,
                      'wall_seconds':latency,'parent_CPU_seconds':time.process_time()-cpu,
                      'child_CPU_seconds':child.ru_utime+child.ru_stime-before.ru_utime-before.ru_stime,
                      'parent_peak_RSS_KiB':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'child_peak_RSS_KiB':child.ru_maxrss,
                      'resource_scope':'Process high water marks are cumulative; not an isolated per-case memory estimate.'})
        (output/'partial.json').write_bytes(canonical(cases)+b'\n')
    attacks=campaign(output/'adversarial') if adversarial and split=='development' else None
    if ctx!=context():raise ValueError('component sources changed during evaluation; retain run as invalidated')
    result={'format':'pcs-scientific-understanding-benchmark-v2','freeze_sha256':digest(freeze),'split':split,'cases':cases,'adversarial':attacks,
            'training_on_projects':False,'scientific_claims_certified':0,'external_expert_validation':False,'authority':False}
    (output/'results.json').write_bytes(canonical(result)+b'\n')
    if attacks is not None and not attacks['all_detected']:raise AssertionError('Adversarial regression failed; results retained')
    return result
