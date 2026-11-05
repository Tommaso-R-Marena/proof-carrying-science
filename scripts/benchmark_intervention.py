"""Analytical intervention controls with independent small-world enumeration."""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
import time

from pcs.experimental.conditional import evaluate, from_text
from pcs.experimental.intervention import TASK, audit_proposal, plan, verify


def make(target, assumptions='', baseline=None, costs=None, locked=None):
    problem = from_text(target, 'FALSE', assumptions); names = problem['variables']
    return {'format': TASK, 'problem': problem, 'baseline': baseline or dict.fromkeys(names, False),
            'costs': costs or dict.fromkeys(names, 1), 'locked': locked or []}


def cases():
    out = []
    for n in (4, 8, 12, 16, 20, 24):
        names = [f'V{i:02}' for i in range(n)]
        target = ' AND '.join(f'({names[i]} OR {names[i+1]})' for i in range(0, n, 2))
        out.append((f'tied-pairs-{n}', make(target), None, n // 2, 2 ** (n // 2)))
        out.append((f'weighted-pairs-{n}', make(target, costs={v: 3 if i % 2 == 0 else 1 for i, v in enumerate(names)}), None, n // 2, 1))
        out.append((f'locked-pairs-{n}', make(target, locked=names[1::2]), None, n // 2, 1))
    out.extend([
        ('already-satisfied', make('A OR B', baseline={'A': True, 'B': False}), None, 0, 1),
        ('goal-impossible', make('A AND NOT A'), None, None, None),
        ('lock-impossible', make('A OR B', locked=['A', 'B']), None, None, None),
        ('conflicting-context', make('A', 'A\nNOT A'), None, None, None),
        ('premise-enforcement', make('B', 'A -> B', costs={'A': 3, 'B': 1}), None, 1, 1),
        ('constant-true', make('TRUE'), None, 0, 1),
        ('constant-false', make('FALSE'), None, None, None),
        ('node-limit', make('A AND B'), {'nodes': 1, 'operations': 100000}, None, None),
        ('operation-limit', make('A AND B'), {'nodes': 4096, 'operations': 1}, None, None),
    ])
    return out


def exhaustive(task, receipt):
    names = task['problem']['variables']; worlds = []; context = False
    for values in itertools.product((False, True), repeat=len(names)):
        world = dict(zip(names, values))
        if not all(evaluate(f, world) for f in task['problem']['assumptions']): continue
        context = True
        if not evaluate(task['problem']['source'], world) or any(world[n] != task['baseline'][n] for n in task['locked']): continue
        cost = sum(task['costs'][n] for n in names if world[n] != task['baseline'][n]); worlds.append((cost, world))
    if receipt['decision'] == 'resource_limit': return  # No semantic assertion to validate.
    if not context: assert receipt['decision'] == 'inconsistent_assumptions'; return
    if not worlds: assert receipt['decision'] == 'no_feasible_plan'; return
    best = min(c for c, _ in worlds); winners = [w for c, w in worlds if c == best]
    assert receipt['minimum_cost'] == best and receipt['optimal_count'] == len(winners) and receipt['assignment'] == winners[0]
    assert receipt['mandatory_flips'] == [n for n in names if all(w[n] != task['baseline'][n] for w in winners)]
    assert receipt['possible_flips'] == [n for n in names if any(w[n] != task['baseline'][n] for w in winners)]


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--output', type=Path, required=True); args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False); records = []
    for name, task, limits, cost, count in cases():
        start = time.perf_counter_ns(); receipt = plan(task, limits); elapsed = time.perf_counter_ns() - start
        start = time.perf_counter_ns(); verify(receipt); replay = time.perf_counter_ns() - start
        assert receipt['minimum_cost'] == cost and receipt['optimal_count'] == count
        enumerated = len(task['problem']['variables']) <= 12 and receipt['decision'] != 'resource_limit'
        if enumerated: exhaustive(task, receipt)
        proposal = audit_proposal(task, dict.fromkeys(task['problem']['variables'], True), limits)
        records.append({'id': name, 'elapsed_ns': elapsed, 'replay_ns': replay, 'independent_exhaustive': enumerated,
                        'all_true_proposal': {k: v for k, v in proposal.items() if k != 'planner_receipt'}, 'receipt': receipt})
    root = Path(__file__).resolve().parents[1]
    hashes = {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in ('pcs/experimental/conditional.py', 'pcs/experimental/intervention.py')}
    report = {'format': 'pcs-intervention-evaluation-v1', 'cases': records, 'source_sha256': hashes,
              'pcs_authority': False, 'bdd_refinement_proved': False, 'general_optimality_proved': False}
    (args.output / 'evaluation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'cases': len(records), 'independent_exhaustive': sum(r['independent_exhaustive'] for r in records), 'source_sha256': hashes}))


if __name__ == '__main__': main()
