import argparse,json
from .experiment import evaluate,replay
p=argparse.ArgumentParser();s=p.add_subparsers(dest='command',required=True)
e=s.add_parser('evaluate');e.add_argument('weights');e.add_argument('out')
r=s.add_parser('replay');r.add_argument('capture');r.add_argument('out')
a=p.parse_args()
print(json.dumps(evaluate(a.weights,a.out) if a.command=='evaluate' else replay(a.capture,a.out),indent=2))
