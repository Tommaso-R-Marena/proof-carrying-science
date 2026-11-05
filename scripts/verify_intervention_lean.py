"""Kernel-check selected minimum-cost and optimal-count claims, with false control."""
import itertools
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pcs.experimental.intervention import validate_task, verify
from scripts.verify_conditional_lean import lean_formula


def expressions(task):
    names = task['problem']['variables']
    feasible = lean_formula(task['problem']['source'])
    for f in task['problem']['assumptions']:
        feasible = f'({feasible} && {lean_formula(f)})'
    for n in task['locked']:
        term = n if task['baseline'][n] else f'(!{n})'
        feasible = f'({feasible} && {term})'
    terms = [f'(if {"(!" + n + ")" if task["baseline"][n] else n} then {task["costs"][n]} else 0)' for n in names]
    return feasible, '(' + (' + '.join(terms) or '0') + ' : Nat)'


def main(output):
    data = json.loads((output / 'evaluation.json').read_text()); sources = ['import Std']; names = []
    selected = []
    for row in data['cases']:
        r = row['receipt']; verify(r); t = validate_task(r['original_task'])
        if r['decision'] != 'optimal_plan' or len(t['problem']['variables']) > 4: continue
        selected.append(row)
        index = len(selected) - 1; vars = t['problem']['variables']; feasible, cost = expressions(t)
        quantifier = '∀ ' + ' '.join(vars) + ' : Bool, ' if vars else ''
        name = f'intervention_minimum_{index}'; names.append(name)
        sources += [f'theorem {name} : {quantifier}{feasible} = true → {r["minimum_cost"]} ≤ {cost} := by decide', '#print axioms ' + name]
        # The finite sum is an independently evaluated Lean count, not the DP count.
        summands = []
        for bits in itertools.product((False, True), repeat=len(vars)):
            env = dict(zip(vars, bits))
            f, c = feasible, cost
            for n in sorted(vars, key=len, reverse=True):
                f = re.sub(r'\b' + re.escape(n) + r'\b', str(env[n]).lower(), f)
                c = re.sub(r'\b' + re.escape(n) + r'\b', str(env[n]).lower(), c)
            summands.append(f'(if {f} && ({c} == {r["minimum_cost"]}) then 1 else 0)')
        name = f'intervention_count_{index}'; names.append(name)
        sources += [f'theorem {name} : ({" + ".join(summands)} : Nat) = {r["optimal_count"]} := by decide', '#print axioms ' + name]
    version = subprocess.check_output(['lake', 'env', 'lean', '--version'], cwd=ROOT / 'formal', text=True)
    assert re.search(r'Lean \(version 4\.28\.0(?:,|\))', version)
    source = output / 'Claims.lean'; source.write_text('\n'.join(sources) + '\n')
    positive = subprocess.run(['lake', 'env', 'lean', str(source.resolve())], cwd=ROOT / 'formal', text=True, capture_output=True)
    (output / 'lean-positive.log').write_text(positive.stdout + positive.stderr)
    assert positive.returncode == 0, positive.stdout + positive.stderr
    inventory = re.findall(r"'(intervention_(?:minimum|count)_\d+)' (?:does not depend on any axioms|depends on axioms: \[([^\]]*)\])", positive.stdout)
    assert len(inventory) == len(names) and {n for n, _ in inventory} == set(names)
    axioms = sorted({a.strip() for _, aa in inventory for a in aa.split(',') if a.strip()})
    assert set(axioms) <= {'propext'}
    false = output / 'FalseClaim.lean'
    false.write_text('import Std\ntheorem false_minimum : ∀ A B : Bool, (A || B) = true → 2 ≤ ((if A then 3 else 0) + (if B then 1 else 0) : Nat) := by decide\n')
    negative = subprocess.run(['lake', 'env', 'lean', str(false.resolve())], cwd=ROOT / 'formal', text=True, capture_output=True)
    (output / 'lean-negative.log').write_text(negative.stdout + negative.stderr)
    assert negative.returncode != 0 and 'error' in negative.stdout and 'decide' in negative.stdout
    result = {'format': 'pcs-intervention-lean-controls-v1', 'version': version.strip(), 'positive_theorems': len(names),
              'standard_axioms': axioms, 'negative_minimum_rejected': True, 'general_optimality_proved': False,
              'implementation_refinement_proved': False, 'pcs_authority': False}
    (output / 'lean-result.json').write_text(json.dumps(result, indent=2) + '\n'); print(json.dumps(result))


if __name__ == '__main__': main(Path(sys.argv[1]).resolve())
