from copy import deepcopy
import itertools
import json
import random
import subprocess
import sys

import pytest

from pcs.experimental.conditional import digest, evaluate, from_text
from pcs.experimental.intervention import TASK, audit_proposal, plan, verify


def task(target='A OR B', assumptions='', baseline=None, costs=None, locked=None):
    problem = from_text(target, 'FALSE', assumptions)
    names = problem['variables']
    return {'format': TASK, 'problem': problem,
            'baseline': dict.fromkeys(names, False) if baseline is None else baseline,
            'costs': dict.fromkeys(names, 1) if costs is None else costs,
            'locked': [] if locked is None else locked}


def oracle(t):
    names = t['problem']['variables']; worlds = []
    context_exists = False
    for values in itertools.product((False, True), repeat=len(names)):
        world = dict(zip(names, values))
        if not all(evaluate(f, world) for f in t['problem']['assumptions']):
            continue
        context_exists = True
        if not evaluate(t['problem']['source'], world) or any(world[n] != t['baseline'][n] for n in t['locked']):
            continue
        cost = sum(t['costs'][n] for n in names if world[n] != t['baseline'][n])
        worlds.append((cost, world))
    if not context_exists: return {'decision': 'inconsistent_assumptions'}
    if not worlds: return {'decision': 'no_feasible_plan'}
    best = min(c for c, _ in worlds); winners = [w for c, w in worlds if c == best]
    return {'decision': 'optimal_plan', 'minimum_cost': best, 'optimal_count': len(winners),
            'assignment': winners[0], 'flips': [n for n in names if winners[0][n] != t['baseline'][n]],
            'mandatory_flips': [n for n in names if all(w[n] != t['baseline'][n] for w in winners)],
            'possible_flips': [n for n in names if any(w[n] != t['baseline'][n] for w in winners)]}


@pytest.mark.parametrize('seed', range(200))
def test_independent_exhaustive_optimizer(seed):
    rng = random.Random(seed); names = list('ABCDEF')
    def formula(depth):
        if depth == 0 or rng.random() < .25:
            return rng.choice(names + ['TRUE', 'FALSE'])
        if rng.random() < .2: return 'NOT (' + formula(depth - 1) + ')'
        return '(' + formula(depth - 1) + rng.choice([' AND ', ' OR ', ' -> ']) + formula(depth - 1) + ')'
    t = task(formula(3), '\n'.join(formula(2) for _ in range(rng.randrange(4))))
    actual_names = t['problem']['variables']
    t['baseline'] = {n: bool(rng.randrange(2)) for n in actual_names}
    t['costs'] = {n: rng.randrange(1, 10) for n in actual_names}
    t['locked'] = [n for n in actual_names if rng.random() < .2]
    expected = oracle(t); result = plan(t)
    assert {k: result[k] for k in expected} == expected
    assert verify(result) == expected['decision']
    assert result['dp_nodes'] <= 4096


def test_ties_locks_skipped_variables_and_positive_weights():
    r = plan(task())
    assert r['assignment'] == {'A': False, 'B': True}
    assert r['optimal_count'] == 2 and r['mandatory_flips'] == [] and r['possible_flips'] == ['A', 'B']
    assert plan(task(costs={'A': 3, 'B': 1}))['mandatory_flips'] == ['B']
    assert plan(task(locked=['B']))['mandatory_flips'] == ['A']
    assert plan(task(locked=['A', 'B']))['decision'] == 'no_feasible_plan'
    t = task('A OR (B AND NOT B)', baseline={'A': False, 'B': True})
    r = plan(t)
    assert r['assignment'] == {'A': True, 'B': True} and r['optimal_count'] == 1


@pytest.mark.parametrize('target,assumptions,decision', [('TRUE', '', 'optimal_plan'), ('FALSE', '', 'no_feasible_plan'), ('TRUE', 'FALSE', 'inconsistent_assumptions')])
def test_zero_variables(target, assumptions, decision):
    r = plan(task(target, assumptions)); assert r['decision'] == decision
    if decision == 'optimal_plan': assert (r['minimum_cost'], r['optimal_count'], r['assignment']) == (0, 1, {})


@pytest.mark.parametrize('limits', [{'nodes': 1, 'operations': 100000}, {'nodes': 4096, 'operations': 1}])
def test_limits_never_claim_a_plan(limits):
    r = plan(task('A AND B'), limits)
    assert r['decision'] == 'resource_limit'
    assert all(r[k] is None for k in ['minimum_cost', 'optimal_count', 'assignment', 'bellman_cells', 'mandatory_flips'])
    assert verify(r) == 'resource_limit'


def test_maximum_scope_count_and_forgeries():
    names = [f'V{i:02}' for i in range(24)]
    target = ' AND '.join(f'({names[i]} OR {names[i+1]})' for i in range(0, 24, 2))
    r = plan(task(target))
    assert r['minimum_cost'] == 12 and r['optimal_count'] == 4096
    assert r['mandatory_flips'] == [] and r['possible_flips'] == names
    assert r['assignment'] == {n: bool(i % 2) for i, n in enumerate(names)}
    for field, value in [('minimum_cost', 0), ('optimal_count', 1), ('mandatory_flips', names), ('pcs_authority', True)]:
        bad = deepcopy(r); bad[field] = value; bad.pop('receipt_sha256'); bad['receipt_sha256'] = digest(bad)
        with pytest.raises(ValueError): verify(bad)
    bad = deepcopy(r); bad['bellman_cells'][-1] = [0, 1, 0, 0]
    bad.pop('receipt_sha256'); bad['receipt_sha256'] = digest(bad)
    with pytest.raises(ValueError): verify(bad)


@pytest.mark.parametrize('field,value', [('costs', {'A': 0, 'B': 1}), ('costs', {'A': True, 'B': 1}), ('costs', {'A': 1000001, 'B': 1}), ('baseline', {'A': 0, 'B': False}), ('locked', ['B', 'A']), ('locked', ['C']), ('locked', ['A', 'A'])])
def test_strict_policy_validation(field, value):
    t = task(); t[field] = value
    with pytest.raises(ValueError): plan(t)


def test_cli_replay_exclusive_outputs_and_strict_input(tmp_path):
    source = tmp_path / 'task.json'; output = tmp_path / 'receipt.json'
    source.write_text(json.dumps(task()))
    def run(*args): return subprocess.run([sys.executable, '-m', 'pcs.cli', 'intervention', *map(str, args)], capture_output=True, text=True)
    assert run('plan', source, '--output', output).returncode == 0
    original = output.read_bytes()
    assert run('verify', output).returncode == 0
    assert run('plan', source, '--output', output).returncode == 4 and output.read_bytes() == original
    source.write_text('{"format":1,"format":2}')
    assert run('plan', source).returncode == 4
    source.write_bytes(b' ' * 1048577)
    assert run('plan', source).returncode == 4


def test_model_proposals_receive_real_feasibility_and_cost_gaps():
    t = task(costs={'A': 3, 'B': 1})
    r = audit_proposal(t, {'A': True, 'B': True})
    assert r['feasible'] and r['cost'] == 4 and r['optimality_gap'] == 3
    assert audit_proposal(t, {'A': False, 'B': False})['optimality_gap'] is None
    t['locked'] = ['B']
    r = audit_proposal(t, {'A': False, 'B': True})
    assert r['lock_violations'] == ['B'] and not r['feasible'] and r['optimality_gap'] is None
    r = audit_proposal(task('A AND B'), {'A': True, 'B': True}, {'nodes': 1, 'operations': 100000})
    assert r['feasible'] and r['optimality_gap'] is None
