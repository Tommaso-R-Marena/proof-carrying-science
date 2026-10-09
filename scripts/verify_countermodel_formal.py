"""Required kernel/axiom/negative-control and exhaustive compiled-runtime gate."""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pcs.countermodel_v1 import RULESET_SHA256, _missions, _verdict
from generate_countermodel_missions import main as check_generated


def run(*args):
    return subprocess.run(args, cwd=ROOT / 'formal', capture_output=True, text=True, timeout=120)


def main():
    check_generated()
    audit_count = 0
    for file, count in [('PCSCountermodel/Audit.lean', 20), ('PCSCountermodel/Missions.lean', 28)]:
        result = run('lake', 'env', 'lean', file)
        if result.returncode:
            raise RuntimeError(result.stdout + result.stderr)
        declarations = re.findall(r"'([^']+)' depends on axioms: \[([^]]*)\]", result.stdout)
        if len(declarations) != count or len({name for name, _ in declarations}) != count:
            raise RuntimeError(f'Missing or duplicate axiom inventory: {file}')
        for name, axioms in declarations:
            used = {a.strip() for a in axioms.split(',') if a.strip()}
            if not used <= {'propext', 'Quot.sound'}:
                raise RuntimeError(f'Forbidden kernel dependency: {name}: {used}')
        audit_count += count
    negative = run('lake', 'env', 'lean', 'PCSCountermodel/Negative/WrongEquivalence.lean')
    if (negative.returncode == 0 or 'Tactic `decide` proved that the proposition' not in negative.stdout
            or 'is false' not in negative.stdout):
        raise RuntimeError('False equivalence was not rejected for the expected semantic reason')

    # Compare full Boolean interpretations, including every P/Q/R assignment for unary missions.
    # Use the actual independent Python evaluator, not generated Lean formulas as the oracle.
    cases = 0
    proc = subprocess.Popen([str(ROOT / 'formal/.lake/build/bin/pcs-countermodel-replay'), '--exhaustive'],
                            stdout=subprocess.PIPE, text=True)
    try:
        for id, mission in _missions().items():
            for n in (1, 2, 3):
                for mask in range(2 ** (2*n+n*n)):
                    line = proc.stdout.readline()
                    fields = line.rstrip('\n').split('\t')
                    world = {'n': n, 'P': [bool(mask & (1 << (2*i))) for i in range(n)],
                             'Q': [bool(mask & (1 << (2*i+1))) for i in range(n)],
                             'R': [[bool(mask & (1 << (2*n+n*i+j))) for j in range(n)] for i in range(n)]}
                    left, right = _verdict(mission, world)
                    expected = [id, str(n), str(mask), str(int(left)), str(int(right))]
                    if fields != expected:
                        raise RuntimeError(f'Lean/Python disagreement or missing record: {expected} / {fields}')
                    cases += 1
        if proc.stdout.readline() or proc.wait(timeout=15) != 0 or cases != 231224:
            raise RuntimeError('Incomplete or extra compiled Lean results')
    finally:
        if proc.poll() is None:
            proc.kill(); proc.wait()
        proc.stdout.close()
    print(json.dumps({'format': 'pcs-countermodel-formal-gate-v1', 'ruleset_sha256': RULESET_SHA256,
                      'axiom_audits': audit_count, 'axiom_allowlist': ['propext', 'Quot.sound'],
                      'false_equivalence_rejected': True, 'missions': 7, 'worlds': cases,
                      'coverage': 'Every P/Q/R interpretation on nonempty domains 1–3',
                      'lean_python_disagreements': 0, 'runtime_refinement_proved': False,
                      'pcs_authoritative': False}, indent=2))


if __name__ == '__main__':
    main()
