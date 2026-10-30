import argparse,json
from pathlib import Path
from .experiment import evaluate,replay

def main():
    p=argparse.ArgumentParser('Proof-carrying canonical release research');s=p.add_subparsers(dest='cmd',required=True)
    q=s.add_parser('evaluate');q.add_argument('weights',type=Path);q.add_argument('out',type=Path)
    q=s.add_parser('replay');q.add_argument('capture',type=Path);q.add_argument('out',type=Path)
    a=p.parse_args();r=evaluate(a.weights,a.out) if a.cmd=='evaluate' else replay(a.capture,a.out)
    print(json.dumps(r));return 0 if r.get('complete',r.get('replayed',False)) else 20
if __name__=='__main__':raise SystemExit(main())
