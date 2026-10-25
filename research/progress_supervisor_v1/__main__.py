"""Research CLI; unknown inputs or failed Lean execution never grant authority."""
from __future__ import annotations
import argparse,json,subprocess,sys
from pathlib import Path
from pcs.jsonio import strict_json_loads
from .certificate import encode,sha,propose,evaluate
from .authority import Authority
from .broker import Broker
from .trace import certify_path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
IMPLEMENTATION=['Progress.lean','Wire.lean','Main.lean','authority.py','broker.py','certificate.py','example.py','trace.py','__main__.py']

def sources():
    return {**{n:sha((HERE/n).read_bytes()) for n in IMPLEMENTATION},'formal/PCSActionShield.lean':sha((ROOT/'formal/PCSActionShield.lean').read_bytes())}
def read(path,limit=2*1024*1024):
    with Path(path).open('rb') as f:raw=f.read(limit+1)
    if len(raw)>limit:raise ValueError('input exceeds byte limit')
    return raw

def write(path,value):
    with Path(path).open('xb') as f:f.write(encode(value)+b'\n')

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
        if final['state']!=4 or final['transitions']>4:raise ValueError('workflow failed its certified bound')
        records=[s['record'] for s in samples if 'action' in s['record']]
        pairs=[(bytes.fromhex(r['request_hex']),bytes.fromhex(r['reply_hex'])) for r in records]
        wire=b._authority.certify(pairs,'workflow-wire');path=certify_path(b._authority,records)
        # A process-owned qualified supervisor may be shared; publish independent
        # source/proof evidence, never claim the host or a directory is immutable.
        artifact=dict(format='pcs-progress-supervisor-capture-v1',data_origin='synthetic fixed-tool experiment; no participant data',sources=before,
            model_hex=b.model_raw.hex(),certificate_hex=b.cert_raw.hex(),pre_sanitized=pre_sanitized,samples=samples,final=final)
        write(out/'capture.json',artifact)
        write(out/'result.json',dict(format='pcs-progress-supervisor-result-v1',analysis=evaluate(b.model_raw,b.cert_raw),native_build=b._authority.manifest,
            captured_wire_proof=wire,captured_path_proof=path,final=final,replayed=capture is not None,pcs_authority=False,
            implementation_correspondence='TESTED_NOT_PROVED',deployment_safety='OPEN',empirical_model_safety='NOT_ESTABLISHED'))
    if sources()!=before:raise ValueError('implementation changed during capture/replay')
    return dict(output=str(out),transitions=final['transitions'],final_state=final['state'],captured_wire_kernel_checked=True,captured_path_kernel_checked=True,replayed=capture is not None,pcs_authority=False)

def main():
    p=argparse.ArgumentParser(__doc__);s=p.add_subparsers(dest='command',required=True)
    demo=s.add_parser('demo');demo.add_argument('output');demo.add_argument('--pre-sanitized',action='store_true')
    replay=s.add_parser('replay');replay.add_argument('capture');replay.add_argument('output')
    syn=s.add_parser('synthesize');syn.add_argument('model');syn.add_argument('goals');syn.add_argument('output')
    ck=s.add_parser('check');ck.add_argument('model');ck.add_argument('certificate');ck.add_argument('output')
    args=p.parse_args()
    try:
        if args.command=='demo':r=execute(args.output,pre_sanitized=args.pre_sanitized)
        elif args.command=='replay':r=execute(args.output,capture=strict_json_loads(read(args.capture,1024*1024).decode('utf-8',errors='strict')))
        elif args.command=='synthesize':
            raw=read(args.model);goals=strict_json_loads(read(args.goals).decode('utf-8',errors='strict'));c=propose(raw,goals);write(args.output,c);r=evaluate(raw,encode(c))
        else:
            raw,cert=read(args.model),read(args.certificate)
            with Authority(raw,cert,args.output) as authority:r=dict(analysis=evaluate(raw,cert),kernel_checked=True,build=authority.manifest,pcs_authority=False)
        print(json.dumps(r));return 0
    except (OSError,ValueError,RuntimeError,subprocess.SubprocessError) as e:
        print(json.dumps(dict(status='REFUSED_OR_UNAVAILABLE',error=str(e)[-2000:],kernel_checked=False,pcs_authority=False)),file=sys.stderr);return 20
if __name__=='__main__':raise SystemExit(main())
