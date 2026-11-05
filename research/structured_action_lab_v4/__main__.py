"""Separately versioned raw/constrained live experiments and independent replay."""
import argparse,json,sqlite3,subprocess,sys,tempfile
from contextlib import contextmanager
from pathlib import Path
from research.live_agent_lab_v3.__main__ import require_tokenizer
from research.live_agent_lab_v3.protocol import standard_plan,check_plan
from research.progress_supervisor_v1.evidence import write
from .protocol import FORMAT,HERE,sources
from .intake import read_once,parse,prepare
from .report import write_report,write_index


@contextmanager
def decoder(path,profile):
    require_tokenizer()
    from .codec import ActionOracle
    from research.real_model_execution_v2.artifacts import fetch
    if path is not None:yield ActionOracle(path,mode=profile);return
    print('Preparing pinned decoder files (~11 MB; no neural weights).',file=sys.stderr,flush=True)
    with tempfile.TemporaryDirectory(prefix='pcs-action-decoder-') as tmp:
        root=Path(tmp)/'files';fetch(root);yield ActionOracle(root,mode=profile)


def main():
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='command',required=True)
    r=s.add_parser('run');r.add_argument('output',type=Path);r.add_argument('--bundle',type=Path,required=True);r.add_argument('--dependencies',type=Path,required=True);r.add_argument('--profile',choices=('raw','trie','paired'),required=True);r.add_argument('--plan',type=Path)
    for name in ('demo','replay','view'):
        a=s.add_parser(name)
        if name!='demo':a.add_argument('input',type=Path)
        else:a.add_argument('--profile',choices=('raw','trie'),default='trie')
        a.add_argument('output',type=Path);a.add_argument('--tokenizer',type=Path)
    f=s.add_parser('qualify-codec');f.add_argument('output',type=Path)
    d=s.add_parser('doctor');d.add_argument('--json',action='store_true')
    args=p.parse_args()
    if args.command=='doctor':
        from research.live_agent_lab_v3.doctor import inspect,human
        value=inspect();print(json.dumps(value) if args.json else human(value));return 0
    if args.output.exists():raise FileExistsError('Choose a fresh output path')
    if args.command=='qualify-codec':
        from .formal import qualify
        print(json.dumps(qualify(args.output.resolve())));return 0
    if args.command=='run':
        require_tokenizer()
        from .experiment import run
        plan=check_plan(parse(read_once(args.plan))) if args.plan else standard_plan()
        if any(c['id']=='authority' for c in plan['cases']):p.error('Case ID authority is reserved')
        profiles=('raw','trie') if args.profile=='paired' else (args.profile,)
        args.output.mkdir(parents=True,exist_ok=False)
        write(args.output/'registration.json',dict(format=FORMAT,profiles=list(profiles),plan=plan,sources=sources(),training_eligibility='DO_NOT_TRAIN_WITHOUT_REVIEW'))
        counts={}
        for profile in profiles:
            print(f'Running {profile}: qualifying native authority before inference; cold builds can take minutes.',file=sys.stderr,flush=True)
            target=args.output/profile
            frozen=run(args.bundle,args.dependencies,target,plan,mode=profile,progress=lambda t:print(t,file=sys.stderr,flush=True))
            counts[profile]=write_report(frozen,target/'report.html','live')
        if len(counts)==2:write_index(counts,args.output/'index.html')
        print('Open '+str(args.output/('index.html' if len(counts)==2 else profiles[0]+'/report.html'))+' in your browser.',file=sys.stderr,flush=True)
        print(json.dumps(dict(format=FORMAT,complete=True,profiles=counts,output=str(args.output),inference_performed=any(v['model_proposals'] for v in counts.values()),pcs_authority=False)));return 0
    source=HERE/'demo'/args.profile if args.command=='demo' else args.input
    # Decoder files are fetched/verified by the existing owned temporary helper.
    value=parse(read_once(source/'suite.json'));profile=value.get('profile')
    if profile not in ('raw','trie'):raise ValueError('Explicit decoder profile required')
    with decoder(args.tokenizer,profile) as oracle:
        if args.command=='view':frozen=prepare(source,oracle);target=args.output;mode='loaded'
        else:
            from .experiment import replay
            print('Rebuilding Lean authority and replaying recorded responses; no neural inference.',file=sys.stderr,flush=True)
            frozen=replay(source,oracle,args.output);target=args.output/'report.html';mode='replay'
        counts=write_report(frozen,target,mode)
    print(json.dumps(dict(format=FORMAT,complete=True,profile=profile,mode=mode,summary=counts,report=str(target),inference_performed=False,native_execution_checked=mode=='replay',pcs_authority=False)));return 0


if __name__=='__main__':
    try:raise SystemExit(main())
    except (OSError,ValueError,EOFError,RuntimeError,KeyError,ImportError,sqlite3.Error,subprocess.SubprocessError) as e:
        print(json.dumps(dict(format=FORMAT,status='REFUSED_OR_UNAVAILABLE',reason=type(e).__name__,next_step='Choose fresh output paths, run doctor and inspect retained model/native logs. No success verdict was issued.',complete=False,pcs_authority=False)),file=sys.stderr);raise SystemExit(20)
