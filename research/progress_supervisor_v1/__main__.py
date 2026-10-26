"""Research CLI; unknown inputs or failed Lean execution never grant authority."""
from __future__ import annotations
import argparse,json,sqlite3,subprocess,sys
from pathlib import Path
from pcs.jsonio import strict_json_loads
from .certificate import encode,sha,propose,evaluate
from .authority import Authority
from .broker import Broker
from .evidence import sources, read, write, publish

def execute(out,*,pre_sanitized=False,capture=None):
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=False)
    before=sources()
    if capture is not None:
        expected={'format','data_origin','sources','model_hex','certificate_hex','pre_sanitized','samples','final'}
        if type(capture) is not dict or set(capture)!=expected or capture['format']!='pcs-progress-supervisor-capture-v1' or capture['data_origin']!='synthetic fixed-tool experiment; no participant data':raise ValueError('unsupported capture schema')
        if capture['sources']!=before:raise ValueError('capture belongs to different implementation sources')
        pre_sanitized=capture['pre_sanitized']
        if type(capture['samples']) is not list or not 1<=len(capture['samples'])<=32:raise ValueError('bounded capture required')
        for s in capture['samples']:
            if type(s) is not dict or set(s)!={'request_id','proposal_hex','record'} or type(s['proposal_hex']) is not str or len(s['proposal_hex'])>8192:raise ValueError('invalid captured sample')
        inputs=[(s['request_id'],bytes.fromhex(s['proposal_hex'])) for s in capture['samples']]
    else:
        inputs=[('round-'+str(i),raw) for i,raw in enumerate([b'{"action":5,"verifier":"ALLOW"}',b'not JSON',b'{"action":3}',b'{"action":65535}'])]
    with Broker(out/'effects.sqlite',out/'authority',pre_sanitized=pre_sanitized) as b:
        if capture and (capture['model_hex']!=b.model_raw.hex() or capture['certificate_hex']!=b.cert_raw.hex()):raise ValueError('model/certificate byte identity mismatch')
        samples=[]
        for i,(rid,raw) in enumerate(inputs):
            r=b.step(raw,rid);samples.append(dict(request_id=rid,proposal_hex=raw.hex(),record=r))
            if capture and r!=capture['samples'][i]['record']:raise ValueError('fresh native/effect receipt disagrees with capture')
        final=b.snapshot()
        if capture and final!=capture['final']:raise ValueError('fresh final effects disagree with capture')
        publish(out,b,samples,before,pre_sanitized=pre_sanitized,replayed=capture is not None)
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
