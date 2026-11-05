"""Exact-byte local release evidence. Records are evidence, never release authority.

Only ``verify(..., replay=True)`` executes independent local checks. Provider CI,
external review and deployment require separate provider/human-controlled gates.
The runner accepts recipe names, never caller-supplied command strings.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
try:
    import resource
except ImportError:  # Windows retains wall time; child CPU/RSS are unavailable.
    resource = None
import signal
import subprocess
import sys
import time
from types import MappingProxyType
from typing import Any

FORMAT = 'pcs-release-qualification-v1'
RECIPES = MappingProxyType({
    'python-baseline': ('python', '-m', 'pytest', '-q'),
    'source-integrity': ('python', 'scripts/check_repository_integrity.py'),
    'memory-evidence': ('python', 'scripts/check_memory_evidence.py'),
    'induction-evidence': ('python', 'scripts/check_induction_evidence.py'),
    'lean-full': ('bash', 'scripts/verify_lean.sh'),
})
REQUIRED = tuple(RECIPES)
MANIFESTS = ('pyproject.toml', 'requirements-build.lock', 'requirements-dev.lock',
             'requirements-prover.lock', 'lean-toolchain', 'formal/lean-toolchain',
             'formal/lakefile.lean', 'formal/lake-manifest.json')
MAX_RECORD_BYTES = 4 * 1024 * 1024

def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''): h.update(chunk)
    return h.hexdigest()

def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()

def _git(root: Path, *args: str) -> str:
    return subprocess.check_output(('git', *args), cwd=root, text=True).strip()

def snapshot(root: Path) -> dict:
    root = root.resolve()
    raw = subprocess.check_output(('git', 'ls-files', '-z', '--cached', '--others', '--exclude-standard'), cwd=root)
    names = sorted(set(raw.decode().split('\0')) - {''})
    files = {}
    for name in names:
        path = root / name
        if path.is_symlink():
            # Hash the link itself; no reading arbitrary files outside the checkout.
            files[name] = {'kind': 'symlink', 'target_sha256': hashlib.sha256(os.readlink(path).encode()).hexdigest()}
        elif path.is_file():
            files[name] = {'kind': 'file', 'sha256': sha(path), 'executable': bool(path.stat().st_mode & 0o111)}
        else:
            files[name] = {'kind': 'missing'}
    return {'commit': _git(root, 'rev-parse', 'HEAD'), 'tree': _git(root, 'rev-parse', 'HEAD^{tree}'),
            'dirty_status': _git(root, 'status', '--porcelain'), 'files': files,
            'snapshot_sha256': hashlib.sha256(canonical(files)).hexdigest(),
            'dependency_manifests': {name: sha(root / name) for name in MANIFESTS if (root / name).is_file()}}

def environment() -> dict:
    packages = {}
    for name in ('pytest', 'cryptography', 'jsonschema', 'torch', 'numpy'):
        try: packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError: packages[name] = None
    return {'python': sys.version, 'platform': platform.platform(), 'packages': packages,
            'measurement_limits': 'CPU is child process usage; RSS is cumulative child high-water mark on Linux, not per-gate allocation.'}

def _outside(root: Path, output: Path) -> Path:
    output = output.resolve()
    if output == root.resolve() or root.resolve() in output.parents:
        raise ValueError('Evidence output must be outside the checkout so source snapshots remain stable')
    output.mkdir(parents=True, exist_ok=True)
    return output

def execute_recipe(root: Path, output: Path, name: str, timeout_seconds: int = 3600) -> dict:
    if name not in RECIPES: raise ValueError('Unknown recipe; arbitrary commands are forbidden')
    if type(timeout_seconds) is not int or not 1 <= timeout_seconds <= 18000:
        raise ValueError('Timeout must be between 1 and 18000 seconds')
    output = _outside(root, output)
    argv = [sys.executable if token == 'python' else token for token in RECIPES[name]]
    log = output / (name + '.log')
    before = resource.getrusage(resource.RUSAGE_CHILDREN) if resource else None
    started_utc = datetime.now(timezone.utc).isoformat()
    start = time.monotonic()
    timed_out = False
    with log.open('wb') as stream:
        proc = subprocess.Popen(argv, cwd=root, stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
        try: proc.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(proc.pid, signal.SIGKILL) if os.name == 'posix' else proc.kill()
            proc.wait()
    after = resource.getrusage(resource.RUSAGE_CHILDREN) if resource else None
    return {'recipe': name, 'argv': argv, 'exit_code': proc.returncode, 'started_utc': started_utc,
            'finished_utc': datetime.now(timezone.utc).isoformat(),
            'outcome': 'resource_exhausted' if timed_out else ('passed' if proc.returncode == 0 else 'failed'),
            'wall_seconds': time.monotonic() - start,
            'child_cpu_seconds': after.ru_utime + after.ru_stime - before.ru_utime - before.ru_stime if after and before else None,
            'child_cumulative_peak_rss_kib': after.ru_maxrss if after else None,
            'timeout_seconds': timeout_seconds, 'log': log.name, 'log_sha256': sha(log)}

def generate(root: Path, output: Path, recipes: tuple[str, ...] = REQUIRED, timeout_seconds: int = 3600, related_roots: tuple[Path, ...] = ()) -> dict:
    if len(set(recipes)) != len(recipes) or any(name not in RECIPES for name in recipes):
        raise ValueError('Unknown or duplicate recipe')
    root = root.resolve(); output = _outside(root, output)
    before = snapshot(root)
    related_paths = {path.resolve().name: path.resolve() for path in related_roots}
    if len(related_paths) != len(related_roots) or len(related_paths) > 4: raise ValueError('Related repository names must be unique, at most four')
    related = {name: snapshot(path) for name, path in related_paths.items()}
    gates = [execute_recipe(root, output, name, timeout_seconds) for name in recipes]
    after = snapshot(root)
    related_after = {name: snapshot(path) for name, path in related_paths.items()}
    missing = sorted(set(REQUIRED) - set(recipes))
    blockers = ([f'missing local gate: {name}' for name in missing] +
                [f"local gate {gate['recipe']}: {gate['outcome']}" for gate in gates if gate['outcome'] != 'passed'])
    if before != after or related != related_after: blockers.append('source changed during qualification')
    if before['dirty_status']: blockers.append('checkout differs from immutable commit; snapshot is development evidence')
    record = {'format': FORMAT, 'source': before, 'source_after': after,
              'cross_repository_snapshots': related, 'cross_repository_snapshots_after': related_after,
              'cross_repository_compatibility': {'status': 'not_independently_checked'},
              'environment': environment(), 'required_local_gates': list(REQUIRED), 'local_gates': gates,
              'blockers': blockers, 'local_gate_results_passed': not missing and all(g['outcome'] == 'passed' for g in gates) and before == after and related == related_after,
              'provider_ci': {'status': 'not_independently_checked'},
              'deployment': {'status': 'not_observed'},
              'migration_readiness': {'status': 'not_evaluated'},
              'deployment_eligible': False,
              'authority': 'Unsigned local execution record; never authorizes production or scientific acceptance.'}
    (output / 'qualification.json').write_bytes(canonical(record) + b'\n')
    return record

def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result: raise ValueError('Duplicate JSON key')
        result[key] = value
    return result

def read_record(path: Path) -> dict:
    if path.stat().st_size > MAX_RECORD_BYTES: raise ValueError('Qualification record exceeds bound')
    return json.loads(path.read_text(), object_pairs_hook=_unique,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Non-finite JSON')))

def verify(root: Path, path: Path, *, replay: bool = False, output: Path | None = None, related_roots: tuple[Path, ...] = ()) -> dict:
    record = read_record(path)
    from jsonschema import Draft202012Validator
    schema = json.loads((Path(__file__).parent / 'schemas' / 'release-qualification-v1.schema.json').read_text())
    structural = list(Draft202012Validator(schema).iter_errors(record))
    if structural:
        return {'format': 'pcs-release-qualification-verification-v1', 'artifact_integrity_valid': False,
                'local_checks_independently_replayed': False, 'deployment_eligible': False,
                'errors': ['schema: ' + error.message for error in structural[:16]],
                'limits': 'Malformed local evidence cannot supply release authority.'}
    errors = []
    if record.get('format') != FORMAT: errors.append('wrong schema version')
    if record.get('required_local_gates') != list(REQUIRED): errors.append('required gate policy changed')
    if record.get('source') != snapshot(root): errors.append('exact source snapshot mismatch')
    if record.get('source_after') != record.get('source'): errors.append('source drift during original execution')
    related = record.get('cross_repository_snapshots', {})
    if related != record.get('cross_repository_snapshots_after', {}): errors.append('cross-repository source drift')
    related_paths = {item.resolve().name: item.resolve() for item in related_roots}
    if set(related_paths) != set(related): errors.append('explicit related repository roots required for verification')
    for name, stored in related.items():
        if name not in related_paths: continue
        try:
            if snapshot(related_paths[name]) != stored: errors.append('cross-repository exact snapshot mismatch')
        except (OSError, subprocess.CalledProcessError): errors.append('cross-repository snapshot unavailable')
    gates = record.get('local_gates')
    if not isinstance(gates, list): gates = []; errors.append('invalid gate list')
    names = [g.get('recipe') for g in gates if isinstance(g, dict)]
    if len(names) != len(gates) or len(set(names)) != len(names): errors.append('invalid or duplicate gate')
    for gate in gates:
        if not isinstance(gate, dict): continue
        name = gate.get('recipe')
        if name not in RECIPES: errors.append('unapproved recipe'); continue
        expected = [sys.executable if t == 'python' else t for t in RECIPES[name]]
        if gate.get('argv') != expected: errors.append(f'{name}: command mismatch')
        log_name = gate.get('log')
        if log_name != name + '.log': errors.append(f'{name}: invalid log path'); continue
        log = path.parent / log_name
        if not log.is_file() or log.is_symlink() or sha(log) != gate.get('log_sha256'):
            errors.append(f'{name}: log checksum mismatch')
        if type(gate.get('exit_code')) is not int or gate.get('exit_code') != 0 or gate.get('outcome') != 'passed':
            errors.append(f'{name}: gate did not pass')
    for name in sorted(set(REQUIRED) - set(names)): errors.append(f'missing required gate: {name}')
    # A caller can rewrite a JSON result and its hashes. Only actual fresh replay
    # can establish a local check; metadata booleans never supply authority.
    replay_record = None
    if replay and not errors:
        if output is None: raise ValueError('Independent replay requires separate output directory')
        if output.resolve() == path.parent.resolve(): raise ValueError('Replay must not overwrite original evidence')
        replay_record = generate(root, output, REQUIRED, related_roots=tuple(related_paths.values()))
        if not replay_record['local_gate_results_passed']: errors.append('independent local replay failed')
        if replay_record['source'] != record['source']: errors.append('source changed before replay')
    return {'format': 'pcs-release-qualification-verification-v1', 'artifact_integrity_valid': not errors,
            'local_checks_independently_replayed': bool(replay_record) and not errors,
            'deployment_eligible': False, 'errors': errors,
            'limits': 'Record integrity is not proof of execution. Production requires independently validated provider CI, migration readiness and authorized deployment.'}

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path.cwd())
    sub = parser.add_subparsers(dest='operation', required=True)
    run = sub.add_parser('run'); run.add_argument('--output', type=Path, required=True)
    run.add_argument('--recipe', action='append', choices=REQUIRED)
    run.add_argument('--timeout', type=int, default=3600)
    run.add_argument('--related-root', type=Path, action='append', default=[])
    check = sub.add_parser('verify'); check.add_argument('record', type=Path)
    check.add_argument('--replay-output', type=Path)
    check.add_argument('--related-root', type=Path, action='append', default=[])
    args = parser.parse_args(argv)
    if args.operation == 'run':
        result = generate(args.root, args.output, tuple(args.recipe or REQUIRED), args.timeout, tuple(args.related_root))
        print(json.dumps({k: result[k] for k in ('format', 'blockers', 'local_gate_results_passed', 'deployment_eligible')}, indent=2))
        return 0 if not result['blockers'] else 1
    result = verify(args.root, args.record, replay=args.replay_output is not None, output=args.replay_output, related_roots=tuple(args.related_root))
    print(json.dumps(result, indent=2))
    return 0 if result['artifact_integrity_valid'] else 1

if __name__ == '__main__': raise SystemExit(main())
