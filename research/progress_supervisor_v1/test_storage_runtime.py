"""Real native-authorized storage fault controls; no positive verifier mocks."""
import sqlite3

import pytest

from . import storage
from .broker import Broker, PRIVATE, PUBLIC


@pytest.mark.parametrize('pre', [False, True])
def test_snapshot_cannot_return_a_write_after_verified_observation(tmp_path, pre):
    path = tmp_path / 'race.sqlite'
    with Broker(path, tmp_path / 'native', pre_sanitized=pre) as broker:
        before = broker.snapshot();actual = broker._db
        class Interleave:
            count = 0
            def __getattr__(self, name):return getattr(actual, name)
            def execute(self, sql, *args):
                if sql == 'SELECT value FROM public':
                    self.count += 1
                    if self.count == 2:
                        with sqlite3.connect(path, isolation_level=None) as writer:
                            writer.execute('INSERT INTO public VALUES(?)', ('UNVERIFIED_INTERLEAVING',))
                return actual.execute(sql, *args)
        broker._db = Interleave()
        assert broker.snapshot() == before
        assert not broker._db.in_transaction
        assert actual.execute('SELECT value FROM public').fetchall() == [('UNVERIFIED_INTERLEAVING',)]
        with pytest.raises(ValueError, match='effects disagree'):broker.snapshot()
        assert not broker._db.in_transaction


def test_completed_ledger_view_substitution_cannot_hide_private_rows(tmp_path):
    with Broker(tmp_path / 'view.sqlite', tmp_path / 'native') as broker:
        for i in range(4):broker.step(b'{"action":5}', 'step-' + str(i))
        before = broker.snapshot()
        broker._db.executescript("ALTER TABLE public RENAME TO poisoned_public; CREATE VIEW public AS SELECT value FROM poisoned_public WHERE value='APPROVED_PUBLIC_SUMMARY';")
        broker._db.execute('INSERT INTO poisoned_public VALUES(?)', (PRIVATE,))
        with pytest.raises(storage.StorageIntegrityError, match='schema mismatch'):broker.snapshot()
        with pytest.raises(storage.StorageIntegrityError, match='schema mismatch'):broker.step(b'{"action":5}', 'extra')
        assert not broker._db.in_transaction
        assert broker._db.execute('SELECT value FROM poisoned_public').fetchall() == [(PUBLIC,), (PRIVATE,)]
        assert broker._anchor == (before['state'], before['transitions'], before['head'])


def test_temp_shadow_refuses_before_any_tool_call(tmp_path):
    with Broker(tmp_path / 'temp.sqlite', tmp_path / 'native') as broker:
        broker._db.execute('CREATE TEMP TABLE payload(value TEXT,loaded INTEGER,sanitized INTEGER)')
        def forbidden(*args):pytest.fail('schema drift reached a SQL tool')
        broker._apply = forbidden
        with pytest.raises(storage.StorageIntegrityError, match='TEMP'):broker.step(b'{"action":0}', 'one')
        assert broker._db.execute('SELECT COUNT(*) FROM events').fetchone() == (0,)


@pytest.mark.parametrize('encoded', ['[]', '{', '[' * 1500 + '0' + ']' * 1500])
def test_malformed_stored_receipt_refuses_without_effect_or_unclosed_transaction(tmp_path, encoded):
    with Broker(tmp_path / 'receipt.sqlite', tmp_path / 'native') as broker:
        broker.step(b'{"action":5}', 'one')
        broker._db.execute('UPDATE events SET event_json=?', (encoded,))
        with pytest.raises(storage.StorageIntegrityError, match='receipt'):broker.step(b'{"action":5}', 'two')
        assert not broker._db.in_transaction
        assert broker._db.execute('SELECT COUNT(*) FROM events').fetchone() == (1,)
        assert broker._db.execute('SELECT value FROM public').fetchall() == []


def test_snapshot_rejects_closed_or_borrowed_transaction(tmp_path):
    broker = Broker(tmp_path / 'own.sqlite', tmp_path / 'native')
    broker._db.execute('BEGIN')
    with pytest.raises(storage.StorageIntegrityError, match='own transaction'):broker.snapshot()
    assert broker._db.in_transaction  # Caller retains responsibility for its own transaction.
    broker._db.execute('ROLLBACK');broker.close()
    with pytest.raises(ValueError, match='closed'):broker.snapshot()


def test_failed_initialization_rolls_back_and_closes_connection(tmp_path, monkeypatch):
    actual = storage.check;seen = []
    def fault(db):
        seen.append(db)
        actual(db)
        raise storage.StorageIntegrityError('injected initialization fault')
    monkeypatch.setattr(storage, 'check', fault)
    path = tmp_path / 'failed.sqlite'
    with pytest.raises(storage.StorageIntegrityError, match='initialization fault'):Broker(path, tmp_path / 'native')
    with pytest.raises(sqlite3.ProgrammingError):seen[0].execute('SELECT 1')
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT name FROM sqlite_schema WHERE type='table'").fetchall() == []
    with pytest.raises(FileExistsError):Broker(path, tmp_path / 'unused')
