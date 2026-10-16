"""Audit the complete static transport theorem inventory after the real build."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from audit_lean_source import active_code, audit
from pcs.transport_kernel_v1 import GENERAL_THEOREMS, MATHLIB_REVISION, _inventory

CONTROLS = [f'PCSReal.TransportControls.{n}' for n in (
    'uniform_checked', 'uniform_all_times', 'negative_weight_rejected',
    'nonconservative_rejected', 'wrong_row_sum_rejected', 'zero_volume_rejected',
    'oscillation_preserves_quadratic')]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('new audit output required')
    sources = [ROOT/'formal/real/PCSReal'/n for n in ('Transport.lean', 'TransportControls.lean', 'TransportAudit.lean')]
    if findings := audit(sources):
        raise ValueError('\n'.join(findings))
    declared = []
    for source, namespace in zip(sources[:2], ['PCSReal.Transport', 'PCSReal.TransportControls']):
        declared.extend(namespace+'.'+m[1] for m in re.finditer(
            r'(?m)^(?:@\[[^\]]+\]\s*)*(?:theorem|lemma) (\S+)', active_code(source.read_text())))
    names = GENERAL_THEOREMS + CONTROLS
    if len(names) != 21 or len(declared) != len(set(declared)) or set(declared) != set(names):
        raise ValueError('complete distinct static transport inventory required')
    expected_driver = 'import PCSReal.TransportControls\n\n' + ''.join('#print axioms '+n+'\n' for n in names)
    if sources[-1].read_text() != expected_driver:
        raise ValueError('exact transport audit driver required')
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'],
        cwd=ROOT/'.lake/packages/mathlib', text=True).strip()
    if revision != MATHLIB_REVISION:
        raise ValueError('Mathlib revision changed')
    before = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    proc = subprocess.run(['lake', 'env', 'lean', 'formal/real/PCSReal/TransportAudit.lean'],
        cwd=ROOT, capture_output=True, text=True, timeout=180)
    if proc.returncode:
        raise RuntimeError(proc.stdout+proc.stderr)
    inventory = _inventory(proc.stdout, names)
    if before != {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}:
        raise ValueError('transport source changed during audit')
    report = {'format': 'pcs-transport-static-audit-v1', 'kernel_theorems': inventory,
        'mathlib_revision': revision, 'source_sha256': before, 'returncode': proc.returncode,
        'stdout': proc.stdout, 'scientific_acceptance': False, 'implementation_correspondence': 'OPEN'}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as f:
        json.dump(report, f, indent=2);f.write('\n')
    print(json.dumps({'kernel_theorems': len(inventory), 'scientific_acceptance': False}))


if __name__ == '__main__':
    main()
