import argparse
import json
from pathlib import Path
from .authority import Authority
from .experiment import run,replay


def main():
    p=argparse.ArgumentParser('Exact native effect plans and causal public-sink research')
    sub=p.add_subparsers(dest='command',required=True)
    q=sub.add_parser('audit');q.add_argument('out',type=Path)
    q=sub.add_parser('evaluate');q.add_argument('weights',type=Path);q.add_argument('out',type=Path)
    q=sub.add_parser('replay');q.add_argument('capture',type=Path);q.add_argument('out',type=Path)
    args=p.parse_args()
    try:
        if args.command=='audit':
            a=Authority(args.out)
            try:r=a.audit_objects()
            finally:a.close()
        else:r=run(args.out,args.weights) if args.command=='evaluate' else replay(args.capture,args.out)
        print(json.dumps({k:v for k,v in r.items() if k not in {'executions','axiom_closures'}}))
        return 0 if r.get('complete',r.get('replayed',r.get('fresh_object_checked',False))) else 20
    except (ValueError,OSError,KeyError,TypeError,RecursionError) as e:
        print(json.dumps(dict(status='REFUSED',error=str(e),production_authority=False)));return 20


if __name__=='__main__':raise SystemExit(main())
