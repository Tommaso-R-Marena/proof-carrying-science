"""Fresh Lean assurance for exact finite transport matrices, for all discrete times.

Existing signed v3 workflow claims retain their authority. Mathematical matrix
truth, bounded trajectory replay, implementation correspondence, and scientific
adequacy are separate results. No submitted proof or project code is executed.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
from fractions import Fraction

from .canonical_json import canonicalize_jcs_bytes
from .jsonio import strict_json_loads
from . import scientific_workflow_v3 as workflow
from .scientific_contracts_v1 import rational, rational_text, _bounded

FORMAT = 'pcs-transport-kernel-replay-v1'
MODEL_FORMAT = 'pcs-transport-matrix-certificate-v1'
MATHLIB_REVISION = '8f9d9cff6bd728b17a24e163c9402775d9e6a365'
ROOT = Path(__file__).resolve().parents[1]
FORMAL = ROOT / 'formal/real/PCSReal/Transport.lean'
GENERAL_THEOREMS = [f'PCSReal.Transport.{name}' for name in (
    'of_detailed_balance', 'step_lower', 'step_upper', 'step_nonnegative', 'amount_step',
    'row_quadratic_bound', 'quadratic_step', 'amount_all_times',
    'nonnegative_all_times', 'bounds_all_times', 'quadratic_all_times', 'all_times_contract',
    'check_sound', 'rational_certificate_real')]
REPLAY_THEOREMS = [f'PCSTransportReplay.{name}' for name in (
    'matrix_checked', 'initial_bounds', 'declared_all_times', 'all_real_initial_states')]
APPROVED_AXIOMS = {'propext', 'Classical.choice', 'Quot.sound'}


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def prepare(contract_raw: bytes) -> dict:
    """Reconstruct coefficients by incidence sums, separately from v3 updates."""
    contract = workflow.load_contract(contract_raw)
    cells = contract['cells']
    volumes = [rational(c['volume'], 'volume') for c in cells]
    initial = [rational(c['initial_concentration'], 'initial') for c in cells]
    dt = rational(contract['time_step'], 'time_step')
    conductance = [[Fraction() for _ in cells] for _ in cells]
    indices = {c['id']: i for i, c in enumerate(cells)}
    for e in contract['edges']:
        i, j = indices[e['left']], indices[e['right']]
        conductance[i][j] = conductance[j][i] = rational(e['conductance'], 'conductance')
    matrix = [[_bounded((Fraction(1) - _bounded(dt * sum(conductance[i], Fraction()) / volumes[i]))
        if i == j else _bounded(dt * conductance[i][j] / volumes[i]))
        for j in range(len(cells))] for i in range(len(cells))]
    # These are diagnostics, not a substitute for the receiving kernel.
    if (any(v <= 0 for v in volumes) or any(p < 0 for row in matrix for p in row)
            or any(sum(row) != 1 for row in matrix)
            or any(sum(volumes[i] * matrix[i][j] for i in range(len(cells))) != volumes[j]
                   for j in range(len(cells)))):
        raise ValueError('declared matrix violates the supported transport contract')
    return {'format': MODEL_FORMAT, 'contract_sha256': sha(contract_raw),
        'volumes': [rational_text(v) for v in volumes],
        'matrix': [[rational_text(p) for p in row] for row in matrix],
        'initial': [rational_text(x) for x in initial]}



def _validate_model(model: dict) -> None:
    if (not isinstance(model, dict) or set(model) != {'format', 'contract_sha256', 'volumes', 'matrix', 'initial'}
            or model['format'] != MODEL_FORMAT or not isinstance(model['contract_sha256'], str)
            or re.fullmatch('[0-9a-f]{64}', model['contract_sha256']) is None):
        raise ValueError('exact bounded matrix certificate required')
    volumes, matrix, initial = model['volumes'], model['matrix'], model['initial']
    if (not isinstance(volumes, list) or not 2 <= len(volumes) <= workflow.MAX_CELLS
            or not isinstance(initial, list) or len(initial) != len(volumes)
            or not isinstance(matrix, list) or len(matrix) != len(volumes)
            or any(not isinstance(row, list) or len(row) != len(volumes) for row in matrix)):
        raise ValueError('bounded complete matrix dimensions required')
    for value in [*volumes, *initial, *(x for row in matrix for x in row)]:
        if not isinstance(value, str) or rational_text(rational(value, 'matrix scalar')) != value:
            raise ValueError('canonical exact rational matrix scalars required')

def _literal(text: str) -> str:
    # Only bounded exact integers enter generated Lean syntax. Never insert IDs,
    # premise statements, submitted code, or producer proof text.
    q = rational(text, 'literal')
    return f'(({q.numerator} : ℚ) / ({q.denominator} : ℚ))'


def _render(model: dict, *, rejection: bool = False) -> bytes:
    _validate_model(model)
    n = len(model['volumes'])
    vector = lambda xs: '[' + ', '.join(_literal(x) for x in xs) + ']'
    rows = '[' + ', '.join(vector(row) for row in model['matrix']) + ']'
    lower, upper = min(map(Fraction, model['initial'])), max(map(Fraction, model['initial']))
    text = f'''import PCSReal.Transport
set_option autoImplicit false
set_option maxRecDepth 8192
set_option maxHeartbeats 2000000
namespace PCSTransportReplay
open PCSReal.Transport
-- Exact source contract: {model['contract_sha256']}
def volume (i : Fin {n}) : ℚ := ({vector(model['volumes'])} : List ℚ).getD i.val 0
def matrix (i j : Fin {n}) : ℚ := (({rows} : List (List ℚ)).getD i.val []).getD j.val 0
def initial (i : Fin {n}) : ℚ := ({vector(model['initial'])} : List ℚ).getD i.val 0
def lower : ℚ := {_literal(rational_text(lower))}
def upper : ℚ := {_literal(rational_text(upper))}
theorem matrix_checked : check volume matrix = true := by decide +kernel
theorem initial_bounds : ∀ i, lower ≤ initial i ∧ initial i ≤ upper := by decide +kernel
theorem declared_all_times (n : Nat) :
    amount volume (evolve matrix initial n) = amount volume initial ∧
    (∀ i, lower ≤ evolve matrix initial n i ∧ evolve matrix initial n i ≤ upper) ∧
    quadratic volume (evolve matrix initial (n + 1)) ≤ quadratic volume (evolve matrix initial n) ∧
    quadratic volume (evolve matrix initial n) ≤ quadratic volume initial :=
  all_times_contract (check_sound matrix_checked) initial lower upper initial_bounds n
theorem all_real_initial_states (x : Fin {n} → ℝ) (lo hi : ℝ)
    (hx : ∀ i, lo ≤ x i ∧ x i ≤ hi) (n : Nat) :
    amount (fun i => (volume i : ℝ)) (evolve (fun i j => (matrix i j : ℝ)) x n) =
      amount (fun i => (volume i : ℝ)) x ∧
    (∀ i, lo ≤ evolve (fun i j => (matrix i j : ℝ)) x n i ∧
      evolve (fun i j => (matrix i j : ℝ)) x n i ≤ hi) ∧
    quadratic (fun i => (volume i : ℝ)) (evolve (fun i j => (matrix i j : ℝ)) x (n + 1)) ≤
      quadratic (fun i => (volume i : ℝ)) (evolve (fun i j => (matrix i j : ℝ)) x n) ∧
    quadratic (fun i => (volume i : ℝ)) (evolve (fun i j => (matrix i j : ℝ)) x n) ≤
      quadratic (fun i => (volume i : ℝ)) x :=
  all_times_contract (rational_certificate_real matrix_checked) x lo hi hx n
end PCSTransportReplay
'''
    if rejection:
        text = text[:text.index('theorem matrix_checked')] + (
            'theorem matrix_rejected : check volume matrix = false := by decide +kernel\n'
            'end PCSTransportReplay\n#print axioms PCSTransportReplay.matrix_rejected\n')
        return text.encode()
    return (text + '\n'.join('#print axioms ' + name for name in REPLAY_THEOREMS) + '\n').encode()


def _inventory(output: str, names: list[str]) -> dict:
    found = {}
    for line in output.splitlines():
        match = re.fullmatch(r"'([^']+)' (?:depends on axioms: \[([^\]]*)\]|does not depend on any axioms)", line)
        if not match:
            continue
        name = match[1]
        if name in found:
            raise ValueError('duplicate theorem audit')
        axioms = sorted(x.strip() for x in (match[2] or '').split(',') if x.strip())
        if not set(axioms) <= APPROVED_AXIOMS:
            raise ValueError('unapproved theorem axiom')
        found[name] = axioms
    if set(found) != set(names) or len(found) != len(names):
        raise ValueError('complete exact theorem inventory required')
    return found


def _source_files() -> dict[str, bytes]:
    return {'PCSReal/Transport.lean': FORMAL.read_bytes(),
        'receiver.py.txt': Path(__file__).read_bytes(), **workflow._implementation()}


def _environment(timeout: float) -> tuple[str, dict, str]:
    deadline = time.monotonic() + timeout
    def remaining():
        value = deadline - time.monotonic()
        if value <= 0:
            raise subprocess.TimeoutExpired('transport environment', timeout)
        return value
    revision = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT/'.lake/packages/mathlib',
        capture_output=True, text=True, check=True, timeout=remaining()).stdout.strip()
    if revision != MATHLIB_REVISION:
        raise ValueError('pinned Mathlib revision required')
    dirty = subprocess.run(['git', 'status', '--porcelain', '--untracked-files=no'],
        cwd=ROOT/'.lake/packages/mathlib', capture_output=True, text=True, check=True, timeout=remaining()).stdout
    if dirty.strip():
        raise ValueError('Mathlib tracked sources differ from the pinned revision')
    def lake_value(name):
        return subprocess.run(['lake', 'env', 'printenv', name], cwd=ROOT,
            capture_output=True, text=True, check=True, timeout=remaining()).stdout.strip()
    paths = lake_value('PATH')
    lean = shutil.which('lean', path=paths)
    if lean is None:
        raise ValueError('pinned Lean unavailable')
    version = subprocess.run([lean, '--version'], capture_output=True, text=True,
        check=True, timeout=remaining()).stdout.strip()
    if 'version 4.28.0' not in version or '7e01a1b' not in version:
        raise ValueError('exact qualified Lean release required')
    env = dict(os.environ)
    env['LEAN_PATH'] = lake_value('LEAN_PATH')
    return lean, env, version


def kernel_replay(model: dict, *, timeout: float = 120) -> dict:
    """Compile a private snapshot, then check regenerated literal-model proofs.

    Called only with receiving data from prepare(); this low-level function does
    not authenticate an arbitrary model's binding to an external contract.
    """
    if type(timeout) not in {int, float} or not 0 < timeout <= 180:
        raise ValueError('kernel timeout must be within (0,180] seconds')
    started = time.monotonic()
    deadline = started + timeout
    def remaining():
        value = deadline - time.monotonic()
        if value <= 0:
            raise subprocess.TimeoutExpired('transport replay', timeout)
        return value
    sources = _source_files()
    before = {name: sha(raw) for name, raw in sources.items()}
    proof = _render(model)
    base = {'kernel_checked': False, 'status': 'UNAVAILABLE_OR_EXHAUSTED',
        'formal_source_sha256': before['PCSReal/Transport.lean'], 'source_sha256': before,
        'proof_sha256': sha(proof), 'model_sha256': sha(canonicalize_jcs_bytes(model)),
        'mathlib_revision': MATHLIB_REVISION, 'kernel_theorems': {}, 'executions': []}
    executions = base['executions']
    try:
        lean, env, version = _environment(min(remaining(), 30))
        with tempfile.TemporaryDirectory(prefix='pcs-transport-kernel-') as folder:
            private = Path(folder)
            (private/'PCSReal').mkdir()
            module = private/'PCSReal/Transport.lean'
            # Audit the exact newly compiled source, rather than cached PCS objects.
            module.write_bytes(sources['PCSReal/Transport.lean'] + ('\n' + '\n'.join(
                '#print axioms ' + n for n in GENERAL_THEOREMS) + '\n').encode())
            driver = private/'Replay.lean'
            driver.write_bytes(proof)
            env['LEAN_PATH'] = str(private) + os.pathsep + env['LEAN_PATH']
            for path, output, names in [(module, module.with_suffix('.olean'), GENERAL_THEOREMS),
                                        (driver, None, REPLAY_THEOREMS)]:
                command = [lean, '-j1', '-M2048', '--root='+str(private)]
                if output is not None:
                    command += ['-o', str(output)]
                command.append(str(path))
                result = subprocess.run(command, cwd=private, env=env, capture_output=True,
                    text=True, timeout=remaining())
                executions.append({'command': command, 'returncode': result.returncode,
                    'stdout': result.stdout, 'stderr': result.stderr})
                if result.returncode:
                    if output is not None:
                        return {**base, 'status': 'FORMAL_SOURCE_REJECTED'}
                    rejected = _render(model, rejection=True)
                    negative = private/'MatrixRejected.lean'
                    negative.write_bytes(rejected)
                    neg = subprocess.run(command[:-1]+[str(negative)], cwd=private, env=env,
                        capture_output=True, text=True, timeout=remaining())
                    executions.append({'command': command[:-1]+[str(negative)], 'returncode': neg.returncode,
                        'stdout': neg.stdout, 'stderr': neg.stderr})
                    if neg.returncode == 0:
                        inventory = _inventory(neg.stdout, ['PCSTransportReplay.matrix_rejected'])
                        if before != {name: sha(raw) for name, raw in _source_files().items()}:
                            raise ValueError('receiving source changed during negative replay')
                        return {**base, 'status': 'CERTIFICATE_FALSIFIED', 'negative_kernel_checked': True,
                            'negative_kernel_theorems': inventory, 'negative_proof_sha256': sha(rejected),
                            'elapsed_seconds': round(time.monotonic()-started, 6)}
                    return {**base, 'status': 'CERTIFICATE_REJECTED', 'negative_kernel_checked': False}
                base['kernel_theorems'].update(_inventory(result.stdout, names))
        if before != {name: sha(raw) for name, raw in _source_files().items()}:
            raise ValueError('receiving source changed during kernel replay')
        return {**base, 'kernel_checked': True, 'status': 'KERNEL_CHECKED',
            'lean_version': version, 'elapsed_seconds': round(time.monotonic()-started, 6)}
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        return {**base, 'error': f'{type(exc).__name__}: {exc}',
                'elapsed_seconds': round(time.monotonic()-started, 6)}


def replay(contract_raw: bytes, trajectory_raw: bytes | None = None, *,
           proposal_raw: bytes | None = None, timeout: float = 120) -> dict:
    base = {'format': FORMAT, 'accepted': False, 'all_time_model_supported': False,
        'bounded_trajectory_supported': False, 'implementation_correspondence': 'OPEN',
        'continuum_accuracy': 'OPEN', 'empirical_validity': 'OPEN', 'scientific_acceptance': False,
        'pcs_authority': False, 'producer_proof_executed': False, 'errors': []}
    try:
        model = prepare(contract_raw)
        if proposal_raw is not None:
            if not isinstance(proposal_raw, bytes) or len(proposal_raw) > workflow.MAX_BYTES:
                raise ValueError('proposal byte limit exceeded')
            proposed = strict_json_loads(proposal_raw.decode('utf-8'))
            if canonicalize_jcs_bytes(proposed) != canonicalize_jcs_bytes(model):
                raise ValueError('proposed model differs from exact receiving reconstruction')
        domain = workflow.evaluate(contract_raw, trajectory_raw) if trajectory_raw is not None else None
        kernel = kernel_replay(model, timeout=timeout)
        supported = kernel['kernel_checked'] is True
        bounded = domain is not None and domain['outcome'] == 'PASS'
        return {**base, 'accepted': supported and (bounded if domain is not None else True),
            'all_time_model_supported': supported, 'bounded_trajectory_supported': bounded,
            'acceptance_scope': 'MODEL_AND_BOUNDED_TRAJECTORY' if domain is not None else 'MODEL_ONLY',
            'contract_sha256': sha(contract_raw), 'model': model, 'kernel': kernel,
            'bounded_replay': domain, 'time_horizon': 'all natural discrete times in the declared matrix model',
            'obligations': [
                {'id': 'discrete_matrix_invariants_all_times', 'status': 'KERNEL_SUPPORTED' if supported else 'OPEN',
                 'authority': 'FRESH_LEAN_KERNEL_DECLARED_MATRIX_ONLY'},
                {'id': 'submitted_finite_trajectory', 'status': 'COMPUTATIONALLY_SUPPORTED' if bounded else 'OPEN',
                 'authority': 'INDEPENDENT_EXACT_RATIONAL_REPLAY'},
                *[{'id': name, 'status': 'OPEN', 'authority': 'NONE'} for name in
                  ('implementation_correspondence', 'continuum_accuracy', 'empirical_validity')]]}
    except (ValueError, KeyError, TypeError, UnicodeError, RecursionError, OSError) as exc:
        return {**base, 'errors': [f'{type(exc).__name__}: {exc}']}


def replay_bundle(bundle, public_key_path, *, expected_fingerprint,
                  lean_authority_path=None, timeout: float = 120) -> dict:
    """Compose existing signed v3 replay with a new, scoped matrix theorem."""
    existing = workflow.verify_bundle(bundle, public_key_path,
        expected_fingerprint=expected_fingerprint, lean_authority_path=lean_authority_path)
    if not existing['bounded_contract_satisfied']:
        return {'format': FORMAT, 'accepted': False, 'pcs_package_valid': existing['pcs_package_valid'],
            'all_time_model_supported': False, 'existing_workflow': existing,
            'scientific_acceptance': False, 'errors': ['existing signed workflow replay rejected']}
    loaded = workflow.load_package_zip_v06(bundle)
    certificate = workflow._json(loaded['certificate_bytes'])
    sources = {a['source_path']: loaded['package_files'][a['path']] for a in certificate['artifacts']}
    contract_raw = sources['contract.json']
    contract = workflow.load_contract(contract_raw)
    result = replay(contract_raw, sources[contract['data_path']], timeout=timeout)
    return {**result, 'acceptance_scope': 'SIGNED_PACKAGE_MODEL_AND_BOUNDED_TRAJECTORY',
        'pcs_package_valid': True, 'existing_workflow': existing,
        'bundle_sha256': sha(Path(bundle).read_bytes()),
        'base_numerical_claim': 'OPEN', 'base_continuum_claim': 'OPEN', 'base_empirical_claim': 'OPEN'}


def export_evidence(output: Path, result: dict, contract_raw: bytes | None = None,
                    trajectory_raw: bytes | None = None) -> None:
    sources = _source_files() if result.get('model') else {}
    if sources and result.get('kernel', {}).get('source_sha256') != {name: sha(raw) for name, raw in sources.items()}:
        raise ValueError('receiving sources changed before evidence export')
    output.mkdir(parents=True, exist_ok=False)
    (output/'report.json').write_bytes(canonicalize_jcs_bytes(result))
    if contract_raw is not None:
        (output/'contract.json').write_bytes(contract_raw)
    if trajectory_raw is not None:
        (output/'trajectory.csv').write_bytes(trajectory_raw)
    if model := result.get('model'):
        (output/'matrix-certificate.json').write_bytes(canonicalize_jcs_bytes(model))
        (output/'Replay.lean').write_bytes(_render(model))
        for name, raw in sources.items():
            destination = output/'receiving-source'/name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(raw)
    inventory = {str(p.relative_to(output)): sha(p.read_bytes())
                 for p in sorted(output.rglob('*')) if p.is_file()}
    (output/'SHA256.json').write_bytes(canonicalize_jcs_bytes(inventory))


def command(args) -> int:
    def read(path):
        with Path(path).open('rb') as file:
            raw = file.read(workflow.MAX_BYTES + 1)
        if len(raw) > workflow.MAX_BYTES:
            raise ValueError('input byte limit exceeded')
        return raw
    try:
        if args.bundle:
            if args.trajectory or args.proposal:
                raise ValueError('trajectory/proposal options require raw contract replay')
            if not args.public_key or not args.fingerprint:
                raise ValueError('signed replay requires a public key and pinned fingerprint')
            result = replay_bundle(args.bundle, args.public_key, expected_fingerprint=args.fingerprint,
                lean_authority_path=args.lean_authority, timeout=args.timeout)
            contract_raw = trajectory_raw = None
        else:
            if args.public_key or args.fingerprint or args.lean_authority:
                raise ValueError('key/authority options require signed bundle replay')
            contract_raw = read(args.contract)
            trajectory_raw = read(args.trajectory) if args.trajectory else None
            result = replay(contract_raw, trajectory_raw,
                proposal_raw=read(args.proposal) if args.proposal else None, timeout=args.timeout)
        export_evidence(Path(args.output), result, contract_raw, trajectory_raw)
        print(json.dumps({'accepted': result['accepted'], 'all_time_model_supported': result['all_time_model_supported'],
            'scientific_acceptance': False, 'output': str(Path(args.output).resolve())}))
        return 0 if result['accepted'] else 1
    except (ValueError, OSError) as exc:
        print(json.dumps({'accepted': False, 'error': str(exc), 'scientific_acceptance': False}))
        return 1


def register(subparsers) -> None:
    parser = subparsers.add_parser('transport-kernel-v1',
        help='freshly kernel-check universal discrete transport invariants; scientific claims stay OPEN')
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument('--contract', help='typed existing v3 transport contract JSON')
    inputs.add_argument('--bundle', help='existing signed PCS v3 workflow ZIP')
    parser.add_argument('--trajectory', help='optional finite trajectory CSV')
    parser.add_argument('--proposal', help='optional untrusted matrix-certificate JSON')
    parser.add_argument('--public-key')
    parser.add_argument('--fingerprint')
    parser.add_argument('--lean-authority')
    parser.add_argument('--timeout', type=float, default=120, help='total kernel replay wall budget, at most 180 seconds')
    parser.add_argument('--output', required=True, help='new evidence directory')
    parser.set_defaults(func=command)
