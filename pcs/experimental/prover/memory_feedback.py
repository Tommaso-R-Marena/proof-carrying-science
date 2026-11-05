"""Explicitly licensed, freshly replayed feedback and an isolated gradient update.

This creates an experimental candidate, never edits the active registry, and
does not reuse the frozen final evaluation set to select that candidate.
"""
import argparse,gzip,json
import torch
from pathlib import Path
from .memory_cli import load
from .memory_cost import MeasuredMemoryEnvironment
from .data import intake_feedback
from .induction_ir import digest
from .model import imitate
from .memory_resume import save as save_resume,load as load_resume

def update(models,feedback,output,*,license,source_revision):
    folder=Path(models);output=Path(output)
    if output.exists():raise ValueError('feedback output must be a fresh directory')
    registry,entry,library,model=load(folder)
    tasks=json.loads((folder/'tasks.json').read_text())
    heldout=[t for t in tasks if t['split'] in {'selection','final'}]
    env=MeasuredMemoryEnvironment(library,heldout=heldout,timeout=30)
    try:
        record=intake_feedback(env,feedback,heldout,license=license,source_revision=source_revision)
        optimizer=torch.optim.Adam(model.parameters(),lr=.008)
        first=imitate(model,[record],epochs=1,seed=73,candidate_provider=env.candidates,optimizer=optimizer)
        output.mkdir(parents=True)
        resume_sha=save_resume(model,optimizer,output/'resume-epoch1',{'feedback_sha256':digest(record),
            'source_checkpoint_sha256':entry['sha256'],'completed_epochs':1,'production_authority':False})
        model,optimizer,metadata=load_resume(output/'resume-epoch1',resume_sha)
        if metadata['feedback_sha256']!=digest(record):raise ValueError('resumed dataset mismatch')
        second=imitate(model,[record],epochs=1,candidate_provider=env.candidates,optimizer=optimizer,resume=True)
        report={**second,'epochs':2,'changed_parameters':sorted(set(first['changed_parameters']+second['changed_parameters'])),
                'epoch_reports':[first,second],'optimizer_and_RNG_resumed':True,'resume_sha256':resume_sha}
        sha=model.save(output/'candidate.json',{'source_checkpoint_sha256':entry['sha256'],
            'feedback_sha256':digest(record),'library_sha256':registry['library_sha256'],
            'primitive_catalog_sha256':registry['primitive_catalog_sha256'],'production_authority':False})
        (output/'checked-feedback.json.gz').write_bytes(gzip.compress(json.dumps(record,sort_keys=True).encode(),mtime=0))
        receipt={'format':'pcs-verified-memory-feedback-cycle-v1','training':report,'checkpoint_sha256':sha,
            'source_checkpoint_sha256':entry['sha256'],'fresh_Lean_execution_attempts':env.actual_calls,
            'heldout_exclusion_checked':True,'candidate_evaluation':'Not evaluated on a new untouched holdout.',
            'active_registry_changed':False,'pcs_authority':False,'automatic_promotion':False}
        (output/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
        return receipt
    finally:env.close()

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--models',default='research/verified-memory-v1');p.add_argument('--feedback',required=True);p.add_argument('--output',required=True);p.add_argument('--license',required=True);p.add_argument('--source-revision',required=True);a=p.parse_args()
    print(json.dumps(update(a.models,json.loads(Path(a.feedback).read_text()),a.output,license=a.license,source_revision=a.source_revision)))
if __name__=='__main__':main()
