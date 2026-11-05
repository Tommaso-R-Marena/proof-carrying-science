"""Real Lean positive controls; synthetic subprocesses exercise rejection only."""
from dataclasses import replace
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import signal
import time

import pytest

from research.scientific_receiver_v1 import host

HERE = Path(__file__).resolve().parents[1]
PRIMARY = Path('/workspace/pcs-scientific-receiver-v1/research/scientific_receiver_v1')
LEAN = Path('/workspace/.onboarding/tools/lean-4.28.0-linux/bin/lean')


def pin(kind, path):
    return host.Pin(kind, str(path), hashlib.sha256(path.read_bytes()).hexdigest())


def real_config():
    # Local explicit integration profile, never a requester-selected verifier.
    # CI/operator uses its own absolute config and rebuilt executable/source pins.
    if os.environ.get('PCS_SCI_HOST_OPERATOR_CONFIG'):
        return host.OperatorConfig.load(Path(os.environ['PCS_SCI_HOST_OPERATOR_CONFIG']))
    if os.environ.get('PCS_SCIENTIFIC_LEAN'):
        executable = Path(os.environ['PCS_SCIENTIFIC_LEAN'])
        main = Path(os.environ['PCS_SCIENTIFIC_MAIN'])
        cwd = Path(os.environ['PCS_SCIENTIFIC_CWD'])
        lean_path = os.environ['LEAN_PATH']
    else:
        executable, main, cwd = LEAN, PRIMARY / 'formal/Main.lean', PRIMARY / 'formal'
        environment_file = Path('/tmp/pcs-receiver-lean-env.json')
        if not environment_file.exists():
            pytest.fail('Actual Lean integration environment required; no mocked success fallback')
        lean_path = json.loads(environment_file.read_bytes())['LEAN_PATH']
    if not executable.exists():
        pytest.fail('Actual Lean integration environment required; no mocked success fallback')
    sources = tuple(cwd.rglob('*.lean'))
    deps = tuple((cwd / '.lake/build/lib/lean').rglob('*.olean'))
    assert sources and deps
    return host.operator_config_for_lean(executable=executable, main=main, cwd=cwd,
                                        lean_path=lean_path, source_files=sources,
                                        dependency_files=deps,
                                        toolchain='Lean 4.28.0; explicit partial local dependency pin inventory')


@pytest.fixture(scope='module')
def actual_service():
    return host.ReceiverService(real_config())


@pytest.mark.parametrize('fixture,accepted', [
    ('zero-step', True), ('one-step', True), ('multi-step-nonsingleton', True),
    ('signed-algebraic', True), ('sixty-four-steps', True),
    ('wrong-total', False), ('wrong-environment', False), ('wrong-step', False),
    ('nonreduced-rational', False), ('physical-intermediate-negative', False),
])
def test_actual_lean_snapshot_and_signed_receipt(actual_service, fixture, accepted):
    raw = (HERE / 'fixtures' / (fixture + '.wire')).read_bytes()
    envelope = actual_service.verify_bytes(raw)
    receipt = envelope['receipt']
    assert receipt['errors'] == [], receipt
    assert all(receipt['checks'].values())
    assert receipt['accepted'] is accepted
    assert receipt['verifier_response']['accepted'] is accepted
    assert receipt['raw_hex'] == raw.hex()
    assert receipt['raw_sha256'] == hashlib.sha256(raw).hexdigest()
    assert receipt['scientific_acceptance'] is False
    assert host.replay_signed_receipt(envelope, actual_service.public_key_hex)
    changed = copy.deepcopy(envelope)
    changed['receipt']['accepted'] = not accepted
    assert not host.replay_signed_receipt(changed, actual_service.public_key_hex)
    assert not host.replay_signed_receipt(envelope, host.ReceiverService(actual_service.config).public_key_hex)


def negative_config(tmp_path, code, **overrides):
    script = tmp_path / 'negative_child.py'
    script.write_text(code)
    executable = Path(sys.executable).resolve()
    config = host.OperatorConfig((str(executable), str(script)),
                                 hashlib.sha256(executable.read_bytes()).hexdigest(),
                                 (pin('source', script), pin('dependency', HERE / 'reference.py')),
                                 str(tmp_path), (), 'negative diagnostic subprocess; no Lean success claim',
                                 timeout_seconds=2)
    return replace(config, **overrides)


@pytest.mark.parametrize('code', [
    'print("not-json")',
    'print("{}")',
    'print("{}\\n{}")',
    'print("x"*40000)',
    'import sys;sys.stderr.write("x"*10000)',
    'raise SystemExit(3)',
    'import time;time.sleep(5)',
    'import os;os.write(1,b"\\xff\\n")',
    'print("NaN")',
    'print("{\\\"accepted\\\":NaN}")',
])
def test_bad_subprocesses_fail_closed(tmp_path, code):
    config = negative_config(tmp_path, code, timeout_seconds=0.3)
    result = host.ReceiverService(config).verify_bytes(b'bad')['receipt']
    assert result['accepted'] is False
    assert result['errors']
    assert result['verifier_response'] is None


@pytest.mark.parametrize('mutation', ['raw_hex', 'policy_bool', 'result', 'scope', 'unknown', 'duplicate'])
def test_fake_positive_metadata_is_never_accepted(tmp_path, mutation):
    raw = (HERE / 'fixtures/one-step.wire').read_bytes()
    response = {'accepted': True, 'protocol': host.PROTOCOL, 'policy': 1,
                'raw_hex': raw.hex(), 'scientific_acceptance': False,
                'production_authority': False, 'result': {}, 'error': ''}
    if mutation == 'raw_hex': response['raw_hex'] = '00'
    if mutation == 'policy_bool': response['policy'] = True
    if mutation == 'scope': response['scientific_acceptance'] = True
    if mutation == 'unknown': response['verifier'] = '/requester/selected/executable'
    line = json.dumps(response)
    if mutation == 'duplicate': line = '{"accepted":true,' + line[1:]
    result = host.ReceiverService(negative_config(tmp_path, 'print(' + repr(line) + ')')).verify_bytes(raw)['receipt']
    assert result['accepted'] is False and result['errors']


def test_precheck_detects_source_substitution_before_process(tmp_path, monkeypatch):
    config = negative_config(tmp_path, 'raise SystemExit(9)')
    Path(config.pins[0].path).write_text('print("substituted")')
    monkeypatch.setattr(host.subprocess, 'Popen', lambda *a, **kw: pytest.fail('process must not launch'))
    receipt = host.ReceiverService(config).verify_bytes(b'bad')['receipt']
    assert receipt['accepted'] is False
    assert 'identity differs' in receipt['errors'][0]


def test_postcheck_detects_self_modifying_child(tmp_path):
    code = 'from pathlib import Path;Path(__file__).write_text("# modified");print("{}")'
    receipt = host.ReceiverService(negative_config(tmp_path, code)).verify_bytes(b'bad')['receipt']
    assert receipt['accepted'] is False
    assert 'identity differs' in receipt['errors'][0]


def test_bounded_deep_json_becomes_signed_rejection(tmp_path):
    config = negative_config(tmp_path, 'print("["*12000+"0"+"]"*12000)')
    service = host.ReceiverService(config)
    envelope = service.verify_bytes(b'bad')
    assert envelope['receipt']['accepted'] is False
    assert 'nesting exceeds' in envelope['receipt']['errors'][0]
    assert host.replay_signed_receipt(envelope, service.public_key_hex)


def test_exited_leader_does_not_leave_same_group_child_running(tmp_path):
    pid_file = tmp_path / 'descendant.pid'
    code = ('import subprocess,sys\nfrom pathlib import Path\n'
            'child=subprocess.Popen([sys.executable,"-c","import time;time.sleep(30)"],'
            'stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)\n'
            f'Path({str(pid_file)!r}).write_text(str(child.pid))\n' + 'print("{}")\n')
    config = negative_config(tmp_path, code, timeout_seconds=0.5)
    receipt = host.ReceiverService(config).verify_bytes(b'bad')['receipt']
    assert receipt['accepted'] is False
    descendant = int(pid_file.read_text())
    try:
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            try:
                state = Path(f'/proc/{descendant}/stat').read_text().split()[2]
            except FileNotFoundError:
                return
            if state == 'Z':
                return
            time.sleep(0.01)
        pytest.fail('negative diagnostic descendant remained running after leader exit')
    finally:
        try:
            os.kill(descendant, signal.SIGKILL)
        except ProcessLookupError:
            pass


def test_input_snapshot_does_not_reopen_mutable_path(actual_service, tmp_path, monkeypatch):
    original = (HERE / 'fixtures/one-step.wire').read_bytes()
    path = tmp_path / 'model.wire'
    path.write_bytes(original)
    execute = host._bounded_process
    def substitute(config, framed):
        path.write_bytes(b'malformed replacement')
        return execute(config, framed)
    monkeypatch.setattr(host, '_bounded_process', substitute)
    receipt = actual_service.verify_path(path)['receipt']
    assert receipt['accepted'] is True, receipt
    assert receipt['raw_sha256'] == hashlib.sha256(original).hexdigest()
    assert receipt['verifier_response']['raw_hex'] == original.hex()
    assert path.read_bytes() != original


def test_missing_symlink_fifo_and_oversize_inputs_reject_without_process(tmp_path, monkeypatch):
    service = host.ReceiverService(negative_config(tmp_path, 'raise SystemExit(9)'))
    monkeypatch.setattr(host.subprocess, 'Popen', lambda *a, **kw: pytest.fail('process must not launch'))
    large = tmp_path / 'large'; large.write_bytes(b'x' * 8193)
    link = tmp_path / 'link'; link.symlink_to(large)
    fifo = tmp_path / 'fifo'; os.mkfifo(fifo)
    for path in (large, link, fifo, tmp_path / 'missing'):
        receipt = service.verify_path(path)['receipt']
        assert receipt['accepted'] is False and receipt['errors']
    assert service.verify_bytes(b'x' * 8193)['receipt']['raw_sha256'] is None


def test_request_has_no_verifier_selection_surface(actual_service):
    malicious = b'{"verifier":"/tmp/fake","accepted":true}'
    receipt = actual_service.verify_bytes(malicious)['receipt']
    assert receipt['accepted'] is False and receipt['errors'] == []
    assert receipt['verifier_response']['accepted'] is False
    with pytest.raises(TypeError):
        actual_service.verify_bytes(malicious, verifier='/tmp/fake')


def test_actual_cli_with_operator_config_creates_signed_receipt(actual_service, tmp_path):
    config = actual_service.config
    document = {**vars(config), 'pins': [vars(pin) for pin in config.pins],
                'environment': dict(config.environment)}
    config_file = tmp_path / 'operator.json'
    config_file.write_text(json.dumps(document))
    output = tmp_path / 'receipt.json'
    run = subprocess.run([
        sys.executable, '-m', 'research.scientific_receiver_v1.host',
        '--operator-config', str(config_file), '--request', str(HERE / 'fixtures/one-step.wire'),
        '--receipt', str(output),
    ], capture_output=True, text=True, timeout=90)
    assert run.returncode == 0, run.stderr
    envelope = json.loads(output.read_bytes())
    assert envelope['receipt']['accepted'] is True
    assert envelope['receipt']['scientific_acceptance'] is False
    assert host.replay_signed_receipt(envelope, envelope['public_key_hex'])
