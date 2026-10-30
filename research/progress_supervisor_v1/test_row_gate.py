"""Actual sealed native row decisions, raw codecs and negative kernel controls."""
import itertools
import json
import subprocess

import pytest

from .authority import ROW, ROW_WIRE
from .broker import Broker
from .certificate import encode
from .effects import PRIVATE, PUBLIC, Rows, project, row_packet
from .test_adapter import configurations


@pytest.fixture(scope='module')
def native(tmp_path_factory):
    root = tmp_path_factory.mktemp('row-authority')
    with Broker(root / 'ledger.sqlite', root / 'native') as broker:
        yield broker._authority


def oracle(raw):
    if len(raw) != 16 or raw[:5] != b'PCSR\x01' or any(raw[i] > 1 for i in (7, 8, 9, 12, 13, 14)):
        return bytes([2, 0])
    s, a, b, l, z, p, t, c, m, n, q = raw[5:]
    before = Rows(PUBLIC if b else PRIVATE, bool(l), bool(z), (PUBLIC,) * p)
    after = Rows(PUBLIC if c else PRIVATE, bool(m), bool(n), (PUBLIC,) * q)
    try:expected = project(s, a, before)
    except ValueError:return bytes([2, 0])
    return bytes([2, int(expected == (t, after))])


def assert_frames(native, frames):
    accepted = 0
    for offset in range(0, len(frames), 2048):
        chunk = frames[offset:offset + 2048]
        replies = native.query_rows_raw(b''.join(chunk))
        expected = b''.join(oracle(f) for f in chunk)
        assert replies == expected
        accepted += sum(replies[i] for i in range(1, len(replies), 2))
    return accepted


def test_exhaustive_native_before_after_correspondence(native, record_testsuite_property):
    afters = [Rows(PUBLIC if b else PRIVATE, l, z, (PUBLIC,) * p)
              for b, l, z, p in itertools.product((False, True), (False, True), (False, True), range(3))]
    frames = [row_packet(s, a, before, t, after)
              for s, a, before in configurations() for t in range(7) for after in afters]
    assert len(frames) == 225792
    assert assert_frames(native, frames) == 6
    assert set(ROW) <= set(native.axioms) and len(ROW_WIRE) == 11
    record_testsuite_property('native_row_transition_cases', len(frames))
    record_testsuite_property('exact_accepted_transition_shapes', 6)


def test_every_field_byte_and_malformed_framing_against_native(native):
    good = row_packet(0, 0, Rows(PRIVATE, False, False, ()), 1, Rows(PRIVATE, False, False, ()))
    frames = []
    for field in range(16):
        for value in range(256):
            raw = bytearray(good);raw[field] = value;frames.append(bytes(raw))
    assert len(frames) == 4096
    assert_frames(native, frames)
    for size in range(16):
        assert native.query_rows_raw(good[:size]) == (b'' if not size else bytes([2, 0]))
    assert native.query_rows_raw(good + b'\x00') == bytes([2, 1, 2, 0])
    assert native.query_rows_raw(b'\xff' * 16) == bytes([2, 0])
    assert native.query_raw(good) == bytes([1, 3, 0, 0, 0, 0]) * 3
    for raw in (True, b'x' * 32769):
        with pytest.raises(ValueError):native.query_rows_raw(raw)


def test_forged_row_acceptance_is_rejected_by_actual_kernel(native, tmp_path):
    before = Rows(PRIVATE, False, False, ())
    bad = row_packet(0, 0, before, 1, Rows(PRIVATE, True, False, ()))
    assert native.query_rows_raw(bad) == bytes([2, 0])
    with pytest.raises(ValueError, match='Actual Lean/build process rejected'):
        native.certify_rows([(bad, bytes([2, 1]))], 'forged-rows', proof_dir=tmp_path)
    good = row_packet(0, 0, before, 1, before)
    proof = native.certify_rows([(good, native.query_rows_raw(good))], 'actual-rows', proof_dir=tmp_path)
    assert proof['kernel_checked'] and set(proof['axioms']) == {'CaptureRows.actual'}


def test_real_native_gate_blocks_a_matching_but_wrong_python_projection(native, tmp_path, monkeypatch):
    from . import broker as implementation
    with Broker(tmp_path / 'ledger.sqlite', tmp_path / 'unused') as broker:
        before = broker.snapshot();apply = broker._apply
        def wrong_projection(state, action, rows):
            return 1, Rows(PRIVATE, True, False, ())
        def wrong_sql(state, action):
            target = apply(state, action)
            broker._db.execute('UPDATE payload SET loaded=1')
            return target
        monkeypatch.setattr(implementation, 'project', wrong_projection)
        broker._apply = wrong_sql
        with pytest.raises(ValueError, match='Lean row gate refused'):
            broker.step(b'{"action":5}', 'retry')
        assert broker.snapshot() == before
        assert broker._db.execute('SELECT COUNT(*) FROM events').fetchone() == (0,)
        assert not broker._db.in_transaction
        monkeypatch.undo();broker._apply = apply
        event = broker.step(b'{"action":5}', 'retry')
        assert event['row_reply_hex'] == '0201'
        assert bytes.fromhex(event['row_request_hex']) == row_packet(0, 0, Rows(PRIVATE, False, False, ()), 1, Rows(PRIVATE, False, False, ()))


def test_row_mode_artifact_substitution_is_fail_closed(native):
    frame = row_packet(0, 0, Rows(PRIVATE, False, False, ()), 1, Rows(PRIVATE, False, False, ()))
    path = native.out / 'RowWire.olean';saved = path.read_bytes()
    try:
        path.write_bytes(b'not a qualified object')
        with pytest.raises(ValueError, match='artifact identity'):native.query_rows_raw(frame)
    finally:path.write_bytes(saved)
    assert native.query_rows_raw(frame) == bytes([2, 1])


@pytest.mark.parametrize('field,value', [('state', True), ('action', -1), ('target', 256), ('state', 1.0)])
def test_python_row_encoder_rejects_numeric_aliases_and_out_of_range(field, value):
    fields = dict(state=0, action=0, before=Rows(PRIVATE, False, False, ()), target=1, after=Rows(PRIVATE, False, False, ()))
    fields[field] = value
    with pytest.raises(ValueError):row_packet(**fields)
