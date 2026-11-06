import argparse
import json
from .pipeline import run,replay
from .corpus import materialize


def main():
    p=argparse.ArgumentParser(description='Review scientific equations, evidence and reproducible computations. Research only.')
    s=p.add_subparsers(dest='cmd',required=True)
    a=s.add_parser('inspect');a.add_argument('source');a.add_argument('--output',required=True);a.add_argument('--check',action='store_true');a.add_argument('--cache')
    a=s.add_parser('replay');a.add_argument('directory');a.add_argument('--expected-manifest-sha256');a.add_argument('--integrity-only',action='store_true')
    a=s.add_parser('demo');a.add_argument('--output',required=True);a.add_argument('--split',choices=['development','final'],default='development')
    a=s.add_parser('serve');a.add_argument('--output',required=True);a.add_argument('--port',type=int,default=0)
    a=s.add_parser('benchmark');a.add_argument('--output',required=True);a.add_argument('--split',choices=['development','final'],default='development')
    args=p.parse_args()
    if args.cmd=='inspect':r=run(args.source,args.output,check=args.check,cache_dir=args.cache)
    elif args.cmd=='replay':r=replay(args.directory,recheck=not args.integrity_only,expected_manifest_sha256=args.expected_manifest_sha256)
    elif args.cmd=='demo':r=materialize(args.output,split=args.split)
    elif args.cmd=='serve':
        from .web import serve
        serve(args.output,args.port);return
    else:
        from .benchmark import benchmark
        r=benchmark(args.output,split=args.split)
    print(json.dumps(r,sort_keys=True,indent=2,allow_nan=False))
if __name__=='__main__':main()
