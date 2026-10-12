"""Adversarial qualification tests. Fixture logs are synthetic, never CI evidence."""
import json
from pathlib import Path
import subprocess
import sys
import pytest
from pcs import release_qualification_v1 as q

@pytest.fixture
def checkout(tmp_path):
    root = tmp_path / 'repo'; root.mkdir()
    subprocess.run(['git', 'init', '-q', str(root)], check=True)
    subprocess.run(['git', '-C', str(root), 'config', 'user.email', 'fixture@example.invalid'], check=True)
    subprocess.run(['git', '-C', str(root), 'config', 'user.name', 'Synthetic fixture'], check=True)
    (root / 'source.txt').write_text('original\n')
    subprocess.run(['git', '-C', str(root), 'add', '.'], check=True)
    subprocess.run(['git', '-C', str(root), 'commit', '-qm', 'fixture'], check=True)
    return root

@pytest.fixture
def record(checkout, tmp_path):
    output = tmp_path / 'evidence'; output.mkdir()
    gates = []
    for name, argv in q.RECIPES.items():
        log = output / (name + '.log'); log.write_text('SYNTHETIC unit-test log\n')
        gates.append({'recipe': name, 'argv': [sys.executable if token == 'python' else token for token in argv],
                      'exit_code': 0, 'outcome': 'passed', 'log': log.name, 'log_sha256': q.sha(log),
                      'wall_seconds': 0.0, 'child_cpu_seconds': 0.0, 'child_cumulative_peak_rss_kib': 0, 'timeout_seconds': 30})
    snapshot = q.snapshot(checkout)
    value = {'format': q.FORMAT, 'source': snapshot, 'source_after': snapshot,
             'required_local_gates': list(q.REQUIRED), 'local_gates': gates,
             'local_gate_results_passed': True, 'deployment_eligible': False, 'environment': {}, 'blockers': [],
             'migration_readiness': {'status': 'not_evaluated'}, 'authority': 'Synthetic unit-test fixture',
             'provider_ci': {'status': 'success'}, 'deployment': {'status': 'success'}}
    path = output / 'qualification.json'; path.write_text(json.dumps(value))
    return path, value

def write(record):
    path, value = record; path.write_text(json.dumps(value)); return path

def test_success_claims_cannot_grant_authority(checkout, record):
    result = q.verify(checkout, record[0])
    assert result['artifact_integrity_valid']
    assert not result['deployment_eligible']
    assert not result['local_checks_independently_replayed']

@pytest.mark.parametrize('attack', ['goal', 'missing', 'log', 'command', 'duplicate', 'exit', 'status', 'policy', 'drift', 'symlink', 'grant', 'nonstring'])
def test_rejects_changed_source_gates_and_artifacts(checkout, record, attack):
    path, value = record; gate = value['local_gates'][0]
    if attack == 'goal': (checkout / 'source.txt').write_text('weakened\n')
    elif attack == 'missing': value['local_gates'].pop()
    elif attack == 'log': (path.parent / gate['log']).write_text('tampered')
    elif attack == 'command': gate['argv'] = ['sh', '-c', 'echo forged']
    elif attack == 'duplicate': value['local_gates'].append(gate.copy())
    elif attack == 'exit': gate['exit_code'] = True  # bool is not an integer exit code
    elif attack == 'status': gate['outcome'] = 'resource_exhausted'
    elif attack == 'policy': value['required_local_gates'] = []
    elif attack == 'drift': value['source_after'] = {}
    elif attack == 'grant': value['deployment_eligible'] = True
    elif attack == 'nonstring': gate['recipe'] = []
    elif attack == 'symlink':
        log = path.parent / gate['log']; raw = log.read_bytes(); log.unlink()
        target = path.parent / 'outside.log'; target.write_bytes(raw); log.symlink_to(target)
    assert not q.verify(checkout, write(record))['artifact_integrity_valid']

def test_duplicate_json_nonfinite_and_size_rejected(checkout, tmp_path):
    path = tmp_path / 'bad.json'
    for raw in ['{"format":1,"format":2}', '{"value":NaN}', ' ' * (q.MAX_RECORD_BYTES + 1)]:
        path.write_text(raw)
        with pytest.raises(ValueError): q.verify(checkout, path)

def test_runner_never_accepts_commands_or_checkout_output(checkout, tmp_path):
    with pytest.raises(ValueError): q.execute_recipe(checkout, tmp_path / 'outside', 'echo forged')
    with pytest.raises(ValueError): q.execute_recipe(checkout, checkout / 'evidence', 'source-integrity')
    with pytest.raises(ValueError): q.execute_recipe(checkout, tmp_path / 'outside', 'source-integrity', 18001)

def test_snapshot_detects_untracked_sources_and_deleted_sources(checkout):
    before = q.snapshot(checkout)
    (checkout / 'new.py').write_text('raise RuntimeError()\n')
    assert q.snapshot(checkout)['snapshot_sha256'] != before['snapshot_sha256']
    (checkout / 'new.py').unlink(); (checkout / 'source.txt').unlink()
    assert q.snapshot(checkout)['files']['source.txt']['kind'] == 'missing'

def test_replay_cannot_overwrite_original_evidence(checkout, record):
    with pytest.raises(ValueError): q.verify(checkout, record[0], replay=True, output=record[0].parent)

def test_required_policy_immutable():
    with pytest.raises(TypeError): q.RECIPES['unsafe'] = ('sh', '-c', 'anything')

def test_external_repo_paths_cannot_be_selected_by_untrusted_record(checkout, record):
    path,value=record
    value['cross_repository_snapshots']={'arbitrary-sensitive-path':{}}
    value['cross_repository_snapshots_after']=value['cross_repository_snapshots']
    result=q.verify(checkout,write(record))
    assert not result['artifact_integrity_valid']
    assert 'explicit related repository roots required for verification' in result['errors']
