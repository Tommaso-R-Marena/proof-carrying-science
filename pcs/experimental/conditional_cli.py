"""Bounded file interface to the experimental conditional checker."""
import json
from pathlib import Path
from pcs.jsonio import strict_json_loads
from .conditional import check, verify


def load(path):
    with Path(path).open('rb') as stream: raw = stream.read(262145)
    if len(raw) > 262144: raise ValueError('Conditional input exceeds 256 KiB')
    try: return strict_json_loads(raw.decode('utf-8'))
    except (RecursionError, UnicodeError) as error: raise ValueError('Malformed conditional input') from error


def execute(args):
    try:
        if args.operation == 'verify':
            decision = verify(load(args.input)); print(json.dumps({'receipt_verified':True,'decision':decision,'pcs_authority':False})); return 0
        receipt = check(load(args.input), {'nodes':args.nodes,'operations':args.operations})
        # Compact exports preserve replayability under the bounded file reader.
        text = json.dumps(receipt, separators=(',', ':'), allow_nan=False)+'\n'
        if args.output:
            with Path(args.output).open('x', encoding='utf-8') as stream: stream.write(text)
        else: print(text, end='')
        return {'equivalent_under_assumptions':0,'counterexample':1,'inconsistent_assumptions':2,'resource_limit':3}[receipt['decision']]
    except (ValueError, OSError, RecursionError) as error:
        print('Conditional reasoning rejected: '+str(error)); return 4


def register(sub):
    group = sub.add_parser('conditional', help='Experimental assumption-aware Boolean reasoning')
    operations = group.add_subparsers(dest='operation', required=True)
    check_parser = operations.add_parser('check'); check_parser.add_argument('input')
    check_parser.add_argument('--output'); check_parser.add_argument('--nodes', type=int, default=4096)
    check_parser.add_argument('--operations', type=int, default=100000); check_parser.set_defaults(func=execute)
    verify_parser = operations.add_parser('verify'); verify_parser.add_argument('input'); verify_parser.set_defaults(func=execute)
