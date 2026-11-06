"""Local CLI; imported files are never executed or admitted to training."""
import argparse
import json
from .pipeline import run,replay


def main():
    parser=argparse.ArgumentParser(description='Organize a scientific project and inspect source-bound checks.')
    sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('inspect');p.add_argument('source');p.add_argument('--output',required=True)
    p.add_argument('--check',action='store_true',help='Authorize only the documented closed checks; imported code is never run.')
    p.add_argument('--cache');p.add_argument('--mode',choices=['deterministic','learned'],default='deterministic');p.add_argument('--budget',type=float,default=100.)
    p=sub.add_parser('replay');p.add_argument('directory');p.add_argument('--integrity-only',action='store_true');p.add_argument('--expected-manifest-sha256')
    p=sub.add_parser('demo');p.add_argument('--output',required=True);p.add_argument('--split',choices=['development','final','all'],default='development')
    p=sub.add_parser('diagnostics');p.add_argument('--effects',action='store_true')
    args=parser.parse_args()
    if args.command=='inspect':result=run(args.source,args.output,check=args.check,cache_dir=args.cache,mode=args.mode,budget=args.budget)
    elif args.command=='replay':result=replay(args.directory,recheck=not args.integrity_only,expected_manifest_sha256=args.expected_manifest_sha256)
    elif args.command=='demo':
        from .projects import materialize_projects
        result=materialize_projects(args.output,split=args.split)
    else:
        from .routing import frozen_diagnostics,replay_diagnostics
        result=replay_diagnostics() if args.effects else frozen_diagnostics()
    print(json.dumps(result,sort_keys=True,indent=2))
if __name__=='__main__':main()
