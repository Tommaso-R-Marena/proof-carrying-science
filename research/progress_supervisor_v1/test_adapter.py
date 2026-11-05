"""Actual SQL refinement and actual Lean authority tests, kept distinct.

Raw _apply differential tests deliberately have NO verifier: they qualify only
SQL row semantics. Authorization/fault tests below construct the real Broker.
No affirmative authority is mocked or substituted.
"""
import itertools
import os
import sqlite3
from pathlib import Path

import pytest

from .adapter import ADAPTER, BRIDGE, qualify
from .broker import Broker
from .effects import PRIVATE, PUBLIC, Rows, check_effects, project, read_rows, valid


def database(rows):
    db = sqlite3.connect(':memory:', isolation_level=None)
    db.executescript('CREATE TABLE payload(value TEXT,loaded INTEGER,sanitized INTEGER); CREATE TABLE public(value TEXT);')
    db.execute('BEGIN IMMEDIATE')
    db.execute('INSERT INTO payload VALUES(?,?,?)', (rows.value, int(rows.loaded), int(rows.sanitized)))
    db.executemany('INSERT INTO public VALUES(?)', [(v,) for v in rows.public])
    return db


def raw_operation(state, action, rows):
    """Exercise the actual SQL implementation in isolation, not authorization."""
    db = database(rows)
    try:
        isolated = object.__new__(Broker);isolated._db = db
        try:target = isolated._apply(state, action)
        except ValueError:return None
        value, loaded, sanitized = db.execute('SELECT value,loaded,sanitized FROM payload').fetchone()
        assert type(value) is str and value in (PRIVATE, PUBLIC)
        assert type(loaded) is int and loaded in (0, 1)
        assert type(sanitized) is int and sanitized in (0, 1)
        public = tuple(v[0] for v in db.execute('SELECT value FROM public'))
        return target, Rows(value, bool(loaded), bool(sanitized), public)
    finally:
        db.execute('ROLLBACK');db.close()


def configurations():
    for state, action, is_public, loaded, sanitized, published in itertools.product(
            range(7), range(8), (False, True), (False, True), (False, True), range(3)):
        yield state, action, Rows(PUBLIC if is_public else PRIVATE, loaded, sanitized, (PUBLIC,) * published)


def test_exhaustive_reference_projection_matches_actual_supported_sql():
    cases, valid_steps = 0, 0
    for state, action, rows in configurations():
        cases += 1
        if valid(state, rows) and state < 4 and action == state:
            projected = project(state, action, rows)
            assert raw_operation(state, action, rows) == projected
            assert valid(*projected)
            valid_steps += 1
        else:
            with pytest.raises(ValueError):project(state, action, rows)
    assert cases == 1344 and valid_steps == 6


def test_fresh_kernel_model_and_native_table_match_actual_sql(tmp_path, record_testsuite_property):
    out = (Path(os.environ['PCS_PROGRESS_QUALIFICATION_DIR']) / 'adapter-spec'
           if 'PCS_PROGRESS_QUALIFICATION_DIR' in os.environ else tmp_path / 'qualification')
    report = qualify(out)
    assert report['fresh_objects_checked'] and report['pcs_authority'] is False
    assert set(report['axiom_closures']) == set(ADAPTER + BRIDGE)
    table = {}
    for line in (out / 'table.csv').read_text().splitlines():
        values = list(map(int, line.split(',')))
        assert len(values) == 13 and tuple(values[:6]) not in table
        table[tuple(values[:6])] = values[6:]
    compared, supported = 0, 0
    for state, action, rows in configurations():
        key = state, action, int(rows.value == PUBLIC), int(rows.loaded), int(rows.sanitized), len(rows.public)
        is_valid, selected, target, public, loaded, sanitized, count = table.pop(key)
        assert all(flag in (0, 1) for flag in (is_valid, selected, public, loaded, sanitized))
        assert bool(is_valid) == valid(state, rows)
        observed = raw_operation(state, action, rows)
        if selected:
            assert observed == (target, Rows(PUBLIC if public else PRIVATE, bool(loaded), bool(sanitized), (PUBLIC,) * count))
            if is_valid:
                assert observed == project(state, action, rows)
                supported += 1
        else:
            assert observed is None
        compared += 1
    assert compared == report['cases'] == 1344 and supported == 6 and not table
    record_testsuite_property('actual_sql_lean_table_cases', compared)
    record_testsuite_property('adapter_theorem_closures', len(ADAPTER + BRIDGE))
    record_testsuite_property('adapter_qualification_seconds', report['seconds'])


@pytest.mark.parametrize('attack', ['extra-public', 'missing-payload', 'duplicate-payload',
                                    'wrong-loaded', 'wrong-sanitized', 'wrong-value',
                                    'wrong-target', 'bool-target', 'float-target',
                                    'receipt-trigger', 'cas-trigger'])
def test_real_authorized_adapter_fault_never_commits(tmp_path, attack):
    with Broker(tmp_path / 'ledger.sqlite', tmp_path / 'native') as broker:
        before = broker.snapshot()
        apply = broker._apply
        if attack == 'receipt-trigger':
            broker._db.execute("CREATE TRIGGER fault AFTER INSERT ON events BEGIN INSERT INTO public VALUES('UNINTENDED'); END")
        elif attack == 'cas-trigger':
            broker._db.execute("CREATE TRIGGER fault AFTER UPDATE ON meta BEGIN INSERT INTO public VALUES('UNINTENDED'); END")
        def faulty(state, action):
            target = apply(state, action)
            if attack == 'extra-public':broker._db.execute("INSERT INTO public VALUES('UNINTENDED')")
            elif attack == 'missing-payload':broker._db.execute('DELETE FROM payload')
            elif attack == 'duplicate-payload':broker._db.execute('INSERT INTO payload SELECT * FROM payload')
            elif attack == 'wrong-loaded':broker._db.execute('UPDATE payload SET loaded=1')
            elif attack == 'wrong-sanitized':broker._db.execute('UPDATE payload SET sanitized=1')
            elif attack == 'wrong-value':broker._db.execute('UPDATE payload SET value=?', (PUBLIC,))
            elif attack == 'wrong-target':return 2
            elif attack == 'bool-target':return True
            elif attack == 'float-target':return 1.0
            return target
        broker._apply = faulty
        with pytest.raises(ValueError, match='fixed adapter'):broker.step(b'{"action":5}', 'retry')
        if attack in ('receipt-trigger', 'cas-trigger'):
            with pytest.raises(ValueError, match='schema mismatch'):broker.snapshot()
            assert broker._db.execute('SELECT state,generation,head FROM meta').fetchall() == [(before['state'],before['transitions'],before['head'])]
            assert broker._db.execute('SELECT value FROM public').fetchall() == []
            broker._db.execute('DROP TRIGGER fault')
        assert broker.snapshot() == before
        assert broker._db.execute('SELECT COUNT(*) FROM events').fetchone() == (0,)
        assert not broker._db.in_transaction
        broker._apply = apply
        assert broker.step(b'{"action":5}', 'retry')['generation'] == 1
        assert broker._authority.manifest['kernel_checked']


@pytest.mark.parametrize('state,sequence', [(0, (0, 1, 2, 3)), (1, (0, 1, 3))])
def test_real_authority_every_fixture_step_matches_reference(tmp_path, state, sequence):
    with Broker(tmp_path / 'ledger.sqlite', tmp_path / 'native', pre_sanitized=bool(state)) as broker:
        for i, action in enumerate(sequence):
            current = broker.snapshot()['state']
            expected_target, expected_rows = project(current, action, read_rows(broker._db))
            event = broker.step(b'{"action":5}', 'step-' + str(i))
            assert (event['target'], read_rows(broker._db)) == (expected_target, expected_rows)
        assert broker.snapshot()['public'] == [PUBLIC]


@pytest.mark.parametrize('attack', ['missing', 'extra', 'null', 'float', 'blob', 'flag', 'public'])
def test_strict_row_decoding_refuses_out_of_domain_storage(attack):
    db = database(Rows(PRIVATE, False, False, ()))
    try:
        if attack == 'missing':db.execute('DELETE FROM payload')
        elif attack == 'extra':db.execute('INSERT INTO payload SELECT * FROM payload')
        elif attack == 'null':db.execute('UPDATE payload SET value=NULL')
        elif attack == 'float':db.execute('UPDATE payload SET loaded=0.5')
        elif attack == 'blob':db.execute('UPDATE payload SET value=?', (b'bytes',))
        elif attack == 'flag':db.execute('UPDATE payload SET loaded=2')
        else:db.execute("INSERT INTO public VALUES('UNINTENDED')")
        with pytest.raises(ValueError, match='fixed adapter'):read_rows(db)
    finally:db.close()


def test_precommit_check_requires_transaction_and_exact_target_type():
    rows = Rows(PRIVATE, False, False, ())
    db = database(rows)
    try:
        for target in (True, 1.0, 2):
            with pytest.raises(ValueError):check_effects(db, target, (1, rows))
        check_effects(db, 1, (1, rows))
        db.execute('ROLLBACK')
        with pytest.raises(ValueError, match='open transaction'):check_effects(db, 1, (1, rows))
    finally:db.close()


@pytest.mark.parametrize('pre,fault_step', [(False, i) for i in range(4)] + [(True, i) for i in range(3)])
def test_private_write_at_every_real_workflow_boundary_rolls_back(tmp_path, pre, fault_step):
    with Broker(tmp_path / 'ledger.sqlite', tmp_path / 'native', pre_sanitized=pre) as broker:
        for i in range(fault_step):broker.step(b'{"action":5}', 'step-' + str(i))
        before = broker.snapshot()
        rows = read_rows(broker._db)
        original = broker._apply
        def write_private(state, action):
            target = original(state, action)
            broker._db.execute('INSERT INTO public VALUES(?)', (PRIVATE,))
            return target
        broker._apply = write_private
        with pytest.raises(ValueError, match='fixed adapter'):
            broker.step(b'{"action":5}', 'step-' + str(fault_step))
        assert broker.snapshot() == before and read_rows(broker._db) == rows
        assert broker._db.execute('SELECT COUNT(*) FROM events').fetchone() == (fault_step,)
        broker._apply = original
        count = 3 if pre else 4
        for i in range(fault_step, count):broker.step(b'{"action":5}', 'step-' + str(i))
        assert broker.snapshot()['public'] == [PUBLIC]


@pytest.mark.parametrize('attack', ['event-json', 'meta-head', 'meta-duplicate'])
def test_transaction_history_corruption_never_commits(tmp_path, attack):
    with Broker(tmp_path / 'ledger.sqlite', tmp_path / 'native') as broker:
        before = broker.snapshot()
        actual = broker._db
        class CorruptPendingData:
            armed = True
            def __getattr__(self, name):return getattr(actual, name)
            def execute(self, sql, *args):
                result = actual.execute(sql, *args)
                if self.armed and ((attack == 'event-json' and sql.startswith('INSERT INTO events')) or
                                   (attack != 'event-json' and sql.startswith('UPDATE meta SET state='))):
                    self.armed = False
                    if attack == 'event-json':actual.execute("UPDATE events SET event_json='{}'")
                    elif attack == 'meta-head':actual.execute("UPDATE meta SET head='bad'")
                    else:actual.execute('INSERT INTO meta SELECT * FROM meta')
                return result
        broker._db = CorruptPendingData()
        with pytest.raises(ValueError, match='receipt|state'):
            broker.step(b'{"action":5}', 'retry')
        assert broker.snapshot() == before
        assert broker._db.execute('SELECT COUNT(*) FROM meta').fetchone() == (1,)
        assert broker._db.execute('SELECT COUNT(*) FROM events').fetchone() == (0,)
        assert not broker._db.in_transaction
        assert broker.step(b'{"action":5}', 'retry')['generation'] == 1
