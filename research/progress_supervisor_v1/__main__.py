"""Research CLI; unknown inputs or failed Lean execution never grant authority."""
from __future__ import annotations
import argparse,json,sqlite3,subprocess,sys
from pathlib import Path
from pcs.jsonio import strict_json_loads
from .certificate import encode,sha,propose,evaluate
from .authority import Authority
from .broker import Broker
from .evidence import ORIGINS, SYNTHETIC_ORIGIN, sources, read, write, publish
from .intake import preflight

def execute(out,*,pre_sanitized=False,capture=None):
    # Reject the entire input before creating files, compiling or applying tools.
    plan=preflight(capture) if capture is not None else None
    out=Path(out).resolve()
    before=sources()
    data_origin=SYNTHETIC_ORIGIN
    if plan is not None:
        if dict(plan.sources)!=before:raise ValueError('implementation changed after preflight')
        pre_sanitized=plan.pre_sanitized
        data_origin=plan.data_origin
        inputs=[(s.request_id,s.proposal) for s in plan.samples]
    else:
        inputs=[('round-'+str(i),raw) for i,raw in enumerate([b'{"action":5,"verifier":"ALLOW"}',b'not JSON',b'{"action":3}',b'{"action":65535}'])]
    out.mkdir(parents=True,exist_ok=False)
    with Broker(out/'effects.sqlite',out/'authority',pre_sanitized=pre_sanitized) as b:
        if plan is not None and (plan.model_raw!=b.model_raw or plan.certificate_raw!=b.cert_raw or plan.binding!=b._authority.source_binding):raise ValueError('preflight/native source identity mismatch')
        samples=[]
        for i,(rid,raw) in enumerate(inputs):
            r=b.step(raw,rid);samples.append(dict(request_id=rid,proposal_hex=raw.hex(),record=r))
            if plan is not None and encode(r)!=plan.samples[i].receipt_json:raise ValueError('fresh native/effect receipt disagrees with capture')
        final=b.snapshot()
        if plan is not None and encode(final)!=plan.final_json:raise ValueError('fresh final effects disagree with capture')
        publish(out,b,samples,before,pre_sanitized=pre_sanitized,replayed=capture is not None,data_origin=data_origin)
    if sources()!=before:raise ValueError('implementation changed during capture/replay')
    return dict(output=str(out),transitions=final['transitions'],final_state=final['state'],captured_wire_kernel_checked=True,captured_path_kernel_checked=True,replayed=capture is not None,pcs_authority=False)

def main():
    p=argparse.ArgumentParser(__doc__);s=p.add_subparsers(dest='command',required=True)
    demo=s.add_parser('demo');demo.add_argument('output');demo.add_argument('--pre-sanitized',action='store_true')
    replay=s.add_parser('replay');replay.add_argument('capture');replay.add_argument('output')
    syn=s.add_parser('synthesize');syn.add_argument('model');syn.add_argument('goals');syn.add_argument('output')
    ck=s.add_parser('check');ck.add_argument('model');ck.add_argument('certificate');ck.add_argument('output')
    server=s.add_parser('serve',help='one process-owned action-only JSONL session')
    server.add_argument('output');server.add_argument('--pre-sanitized',action='store_true')
    server.add_argument('--max-requests',type=int,default=32)
    server.add_argument('--frame-timeout',type=float,default=30)
    args=p.parse_args()
    try:
        if args.command=='serve':
            from .worker import serve
            return serve(args.output,pre_sanitized=args.pre_sanitized,max_requests=args.max_requests,frame_timeout=args.frame_timeout)
        if args.command=='demo':r=execute(args.output,pre_sanitized=args.pre_sanitized)
        elif args.command=='replay':r=execute(args.output,capture=strict_json_loads(read(args.capture,1024*1024).decode('utf-8',errors='strict')))
        elif args.command=='synthesize':
            raw=read(args.model);goals=strict_json_loads(read(args.goals).decode('utf-8',errors='strict'));c=propose(raw,goals);write(args.output,c);r=evaluate(raw,encode(c))
        else:
            raw,cert=read(args.model),read(args.certificate)
            with Authority(raw,cert,args.output) as authority:r=dict(analysis=evaluate(raw,cert),kernel_checked=True,build=authority.manifest,pcs_authority=False)
        print(json.dumps(r));return 0
    except (OSError,ValueError,RuntimeError,sqlite3.Error,subprocess.SubprocessError) as e:
        print(json.dumps(dict(status='REFUSED_OR_UNAVAILABLE',error=str(e)[-2000:],kernel_checked=False,pcs_authority=False)),file=sys.stderr);return 20
if __name__=='__main__':raise SystemExit(main())
