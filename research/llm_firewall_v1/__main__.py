"""Research-only compiled Lean tool mediation and real-model experiments."""
import argparse
import json
from pathlib import Path

from .monitor import Monitor


def main():
    p=argparse.ArgumentParser(__doc__);sub=p.add_subparsers(dest='command',required=True)
    q=sub.add_parser('audit');q.add_argument('out',type=Path)
    q=sub.add_parser('evaluate',help='Live synthetic inference on the existing free Cloudflare account')
    q.add_argument('out',type=Path);q.add_argument('--live',action='store_true',required=True)
    q=sub.add_parser('replay',help='Offline fresh execution/proofs; no model/API calls')
    q.add_argument('evidence',type=Path);q.add_argument('out',type=Path)
    args=p.parse_args()
    try:
        if args.out.exists():raise ValueError('Fresh output directory required')
        if args.command=='audit':
            m=Monitor(args.out)
            try:r=m.audit_objects()
            finally:m.close()
        elif args.command=='evaluate':
            from .campaign import run
            r=run(args.out)
        else:
            from .replay import verify
            r=verify(args.evidence,args.out)
        print(json.dumps({k:v for k,v in r.items() if k not in {'executions','axiom_closures'}}))
        return 0 if r.get('complete',r.get('replayed',r.get('kernel_checked',False))) else 20
    except (OSError,ValueError,KeyError,TypeError,RecursionError) as e:
        print(json.dumps(dict(status='REFUSED',error=str(e),kernel_checked=False,production_authority=False)));return 20


if __name__=='__main__':raise SystemExit(main())
