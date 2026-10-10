"""Bounded, exclusive-output interface to the intervention planning oracle."""
import json
from pathlib import Path

from pcs.jsonio import strict_json_loads
from .intervention import plan, verify


def load(path):
    with Path(path).open('rb') as stream:
        raw = stream.read(1048577)
    if len(raw) > 1048576:
        raise ValueError('Intervention input exceeds 1 MiB')
    try:
        return strict_json_loads(raw.decode('utf-8'))
    except (RecursionError, UnicodeError) as error:
        raise ValueError('Malformed intervention input') from error


def execute(args):
    try:
        if args.operation == 'verify':
            decision = verify(load(args.input))
            print(json.dumps({'receipt_verified': True, 'decision': decision, 'pcs_authority': False}))
            return 0
        result = plan(load(args.input), {'nodes': args.nodes, 'operations': args.operations})
        text = json.dumps(result, separators=(',', ':'), allow_nan=False) + '\n'
        if len(text.encode('utf-8')) > 1048576:
            raise ValueError('Intervention export exceeds replay input budget')
        if args.output:
            with Path(args.output).open('x', encoding='utf-8') as stream:
                stream.write(text)
        else:
            print(text, end='')
        return {'optimal_plan': 0, 'no_feasible_plan': 1, 'inconsistent_assumptions': 2, 'resource_limit': 3}[result['decision']]
    except (ValueError, OSError, RecursionError) as error:
        print('Intervention planning rejected: ' + str(error))
        return 4


def register(sub):
    group = sub.add_parser('intervention', help='Experimental exact weighted Boolean intervention planning')
    operations = group.add_subparsers(dest='operation', required=True)
    parser = operations.add_parser('plan'); parser.add_argument('input'); parser.add_argument('--output')
    parser.add_argument('--nodes', type=int, default=4096); parser.add_argument('--operations', type=int, default=100000)
    parser.set_defaults(func=execute)
    parser = operations.add_parser('verify'); parser.add_argument('input'); parser.set_defaults(func=execute)
