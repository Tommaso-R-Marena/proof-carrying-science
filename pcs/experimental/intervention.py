"""Exact positive-cost interventions over a bounded conditional decision diagram.

This is a planning oracle for declared Boolean models, not causal identification.
The Bellman table counts optimal assignments and exposes mandatory/possible flips.
"""
from copy import deepcopy

from .conditional import check, digest, evaluate, exact, validate

TASK = 'pcs-intervention-task-v1'
RECEIPT = 'pcs-intervention-receipt-v1'


def validate_task(task):
    exact(task, {'format', 'problem', 'baseline', 'costs', 'locked'})
    if task['format'] != TASK:
        raise ValueError('Invalid intervention task format')
    problem = validate(task['problem'])
    if problem['candidate'] != {'op': 'false'}:
        raise ValueError('Intervention problem must compare its target with FALSE')
    names = problem['variables']
    exact(task['baseline'], names); exact(task['costs'], names)
    if any(type(task['baseline'][n]) is not bool for n in names):
        raise ValueError('Baseline values must be Boolean')
    if any(type(task['costs'][n]) is not int or not 1 <= task['costs'][n] <= 1000000 for n in names):
        raise ValueError('Change costs must be positive integers at most 1000000')
    locked = task['locked']
    if type(locked) is not list or any(type(n) is not str or n not in names for n in locked) or locked != sorted(set(locked)):
        raise ValueError('Locked names must be a distinct sorted subset of variables')
    return task


def bellman(nodes, names, baseline, costs, locked):
    """One pass over append-ordered nodes; skipped variables retain baseline.

    Strictly positive costs make that skipped-variable completion uniquely optimal.
    Cells are null (infeasible) or [cost, count, mandatory-mask, possible-mask].
    """
    cells = [None, [0, 1, 0, 0]]
    choices = [None, None]
    for var, low, high in nodes:
        name, bit = names[var], 1 << var
        branches = []
        for value, child in ((False, low), (True, high)):
            if name in locked and value != baseline[name]:
                continue
            cell = cells[child]
            if cell is None:
                continue
            flip = value != baseline[name]
            branches.append((value, [cell[0] + (costs[name] if flip else 0),
                                     cell[1], cell[2] | (bit if flip else 0),
                                     cell[3] | (bit if flip else 0)]))
        if not branches:
            cells.append(None); choices.append(None); continue
        best = min(cell[0] for _, cell in branches)
        winners = [(value, cell) for value, cell in branches if cell[0] == best]
        cell = list(winners[0][1])
        for _, other in winners[1:]:
            cell[1] += other[1]; cell[2] &= other[2]; cell[3] |= other[3]
        cells.append(cell); choices.append(winners[0][0])  # False wins equal costs.
    return cells, choices


def plan(task, limits=None):
    task = validate_task(deepcopy(task))
    symbolic = check(task['problem'], limits)
    result = {'format': RECEIPT, 'checker': 'pcs-intervention-bellman/1',
              'original_task': task, 'task_sha256': digest(task),
              'symbolic_receipt': symbolic, 'decision': None, 'minimum_cost': None,
              'optimal_count': None, 'assignment': None, 'flips': None,
              'mandatory_flips': None, 'possible_flips': None, 'bellman_cells': None,
              'dp_nodes': 0, 'scope': 'Minimum positive-cost changes within declared Boolean meanings only',
              'pcs_authority': False, 'lean_kernel_checked': False}
    if symbolic['decision'] in {'resource_limit', 'inconsistent_assumptions'}:
        result['decision'] = symbolic['decision']
    else:
        names = task['problem']['variables']
        diagram = symbolic['diagram']
        cells, choices = bellman(diagram['nodes'], names, task['baseline'], task['costs'], task['locked'])
        root = diagram['difference']
        result.update(bellman_cells=cells, dp_nodes=len(diagram['nodes']))
        cell = cells[root]
        if cell is None:
            result['decision'] = 'no_feasible_plan'
        else:
            assignment = dict(task['baseline'])
            while root >= 2:
                var, low, high = diagram['nodes'][root - 2]
                value = choices[root]
                assignment[names[var]] = value
                root = high if value else low
            assert root == 1
            result.update(decision='optimal_plan', minimum_cost=cell[0], optimal_count=cell[1],
                          assignment=assignment, flips=[n for n in names if assignment[n] != task['baseline'][n]],
                          mandatory_flips=[n for i, n in enumerate(names) if cell[2] & (1 << i)],
                          possible_flips=[n for i, n in enumerate(names) if cell[3] & (1 << i)])
    result['receipt_sha256'] = digest(result)
    return result


def verify(receipt):
    receipt = deepcopy(receipt)
    if type(receipt) is not dict or 'original_task' not in receipt or type(receipt.get('symbolic_receipt')) is not dict:
        raise ValueError('Invalid intervention receipt')
    if digest(receipt) != digest(plan(receipt['original_task'], receipt['symbolic_receipt'].get('limits'))):
        raise ValueError('Forged, stale or mismatched intervention receipt')
    return receipt['decision']


def audit_proposal(task, assignment, limits=None):
    """Evaluate a model/player proposal and attach an exact optimality gap if known."""
    task, assignment = validate_task(deepcopy(task)), deepcopy(assignment)
    names = task['problem']['variables']; exact(assignment, names)
    if any(type(assignment[n]) is not bool for n in names):
        raise ValueError('Proposal values must be Boolean')
    result = plan(task, limits)
    premises = [evaluate(f, assignment) for f in task['problem']['assumptions']]
    target = evaluate(task['problem']['source'], assignment)
    lock_violations = [n for n in task['locked'] if assignment[n] != task['baseline'][n]]
    cost = sum(task['costs'][n] for n in names if assignment[n] != task['baseline'][n])
    feasible = all(premises) and target and not lock_violations
    return {'assignment': assignment, 'assumptions_true': premises, 'target_true': target,
            'lock_violations': lock_violations, 'feasible': feasible, 'cost': cost,
            'optimality_gap': cost - result['minimum_cost'] if feasible and result['decision'] == 'optimal_plan' else None,
            'planner_receipt': result, 'pcs_authority': False}
