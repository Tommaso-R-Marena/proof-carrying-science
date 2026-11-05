import argparse
import json
from pathlib import Path
from .runtime import download
from .experiment import run,replay


def main():
    p=argparse.ArgumentParser('Pinned actual local weights, CPU inference and Lean tool enforcement')
    sub=p.add_subparsers(dest='command',required=True)
    q=sub.add_parser('download');q.add_argument('weights',type=Path)
    q=sub.add_parser('evaluate');q.add_argument('weights',type=Path);q.add_argument('out',type=Path)
    q=sub.add_parser('replay');q.add_argument('capture',type=Path);q.add_argument('out',type=Path)
    a=p.parse_args()
    try:
        r=download(a.weights) if a.command=='download' else run(a.out,a.weights) if a.command=='evaluate' else replay(a.capture,a.out)
        print(json.dumps(r));return 0 if r.get('verified',r.get('complete',r.get('replayed',False))) else 20
    except (ValueError,OSError,KeyError,TypeError) as e:
        print(json.dumps(dict(status='REFUSED',error=str(e),production_authority=False)));return 20


if __name__=='__main__':raise SystemExit(main())
