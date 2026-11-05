"""Executable existing-English/typed-IR to real checked Mathlib proof search.

Mathlib formal statements are developer-local inputs; no public arbitrary Lean
endpoint is added. Unsupported English and ambiguity abstain before search.
"""
import argparse
import hashlib
import json
import time
from pathlib import Path
from .induction_language import formalize, parse_lean, explain
from .induction_ir import theorem, digest
from .mathlib_environment_v4 import MathlibEnvironmentV4

def run(statement, *, english=False, checkpoint=None, checkpoint_sha256=None, budget=48):
    interpreted=None
    if english:
        interpreted=formalize(statement)
        if interpreted.get('status')!='supported' or len(interpreted.get('candidates',[]))!=1:
            return {'status':interpreted.get('status','unsupported'),'formalization':interpreted,'pcs_authority':False}
        formal=theorem(interpreted['candidates'][0]['ir'])
    else:formal=statement
    try:
        reconstructed=parse_lean(formal)
        explanation={'status':'supported_restricted_fragment','text':explain(reconstructed),
                     'formal_statement':formal,'render_parse_round_trip':theorem(reconstructed)==formal,
                     'english_ir_round_trip':digest(reconstructed)==digest(interpreted['candidates'][0]['ir']) if interpreted else None,
                     'scope':'Deterministic rendering of supported typed syntax; intended English meaning and proof narrative are not kernel certified'}
    except ValueError:
        explanation={'status':'unsupported_fragment','formal_statement':formal,
                     'scope':'The exact formal statement and actual kernel expression remain available; no unrestricted English explanation is claimed'}
    started=time.monotonic()
    try:env=MathlibEnvironmentV4(timeout=12)
    except RuntimeError as error:
        return {'status':'unknown','source':statement,'formalization':interpreted,'explanation':explanation,
                'phase':'environment_initialization','error':str(error),'pcs_authority':False,
                'automatic_training_authorization':False,'automatic_promotion':False}
    initialization={'wall_seconds':time.monotonic()-started,'compiler_invocations':getattr(env,'calls',0),
                    'structured_worker_requests':getattr(env,'worker_requests',0),
                    'worker_initialization_requests':getattr(env,'worker_initialization_requests',0),
                    'cpu_seconds':getattr(env,'cpu_seconds',0.)}
    try:
        ranker=None
        if checkpoint:
            from .premise_policy_v4 import PremisePolicy
            ranker=PremisePolicy.load(checkpoint,checkpoint_sha256,env.catalog)
        try:result=env.solve(formal,ranker=ranker,budget=budget,depth=18,beam=4,wall=90)
        except RuntimeError as error:result={'status':'unknown','receipt':None,'error':str(error),'phase':'proof_search','pcs_authority':False}
        return {'format':'pcs-mathlib-execution-v4','source':statement,'formalization':interpreted,'status':result['status'],
                'result':result,'explanation':explanation,'environment_initialization':initialization,'scope':'Existing restricted English semantics or trusted developer formal statement; research-local execution',
                'automatic_training_authorization':False,'automatic_promotion':False,'pcs_authority':False}
    finally:env.close()

def main():
    p=argparse.ArgumentParser();p.add_argument('statement');p.add_argument('--english',action='store_true');p.add_argument('--checkpoint');p.add_argument('--checkpoint-sha256');p.add_argument('--output',required=True);args=p.parse_args()
    out=Path(args.output)
    if out.exists():raise ValueError('Evidence must not overwrite an earlier run')
    result=run(args.statement,english=args.english,checkpoint=args.checkpoint,checkpoint_sha256=args.checkpoint_sha256)
    out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'status':result['status'],'output':str(out),'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'pcs_authority':False}))

if __name__=='__main__':main()
