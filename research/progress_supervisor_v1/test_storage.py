"""Actual SQLite storage contracts only; no simulated positive Lean verdicts."""
import json
import sqlite3

import pytest

from . import storage
from .certificate import encode
from .test_intake import claimed_fixture


@pytest.fixture
def db(tmp_path):
    connection = sqlite3.connect(tmp_path / 'ledger.sqlite', isolation_level=None)
    storage.configure(connection)
    connection.executescript('BEGIN IMMEDIATE; ' + storage.SCHEMA)
    connection.execute('COMMIT')
    yield connection
    connection.close()


def verify(db):
    db.execute('BEGIN')
    try:storage.check(db)
    finally:db.execute('ROLLBACK')


def test_exact_schema_and_owned_transaction(db):
    with pytest.raises(storage.StorageIntegrityError, match='owned transaction'):storage.check(db)
    verify(db)
    assert not db.in_transaction


@pytest.mark.parametrize('attack', ['view', 'trigger', 'extra-index', 'extra-table', 'missing', 'column', 'temp-table', 'temp-view'])
def test_schema_drift_and_shadows_are_refused_before_observation(db, attack):
    statements = {
        'view': 'ALTER TABLE public RENAME TO hidden; CREATE VIEW public AS SELECT value FROM hidden;',
        'trigger': 'CREATE TRIGGER unexpected AFTER INSERT ON public BEGIN DELETE FROM public; END;',
        'extra-index': 'CREATE INDEX unexpected ON payload(value);',
        'extra-table': 'CREATE TABLE unexpected(value TEXT);',
        'missing': 'DROP TABLE meta;',
        'column': 'ALTER TABLE payload ADD COLUMN unexpected TEXT;',
        'temp-table': 'CREATE TEMP TABLE payload(value TEXT,loaded INTEGER,sanitized INTEGER);',
        'temp-view': 'CREATE TEMP VIEW public AS SELECT value FROM main.public;',
    }
    db.executescript(statements[attack])
    with pytest.raises(storage.StorageIntegrityError, match='state'):verify(db)
    assert not db.in_transaction


@pytest.mark.parametrize('category', list(storage.LIMITS))
def test_connection_limit_changes_are_refused(db, category):
    db.setlimit(category, storage.LIMITS[category] + 1)
    with pytest.raises(storage.StorageIntegrityError, match='limits changed'):verify(db)


@pytest.mark.parametrize('pragma,value', [('synchronous', 0), ('trusted_schema', 1), ('read_uncommitted', 1), ('max_page_count', 129)])
def test_changed_connection_policy_is_not_adopted(db, pragma, value):
    db.execute('PRAGMA ' + pragma + '=' + str(value))
    with pytest.raises(storage.StorageIntegrityError, match='connection policy'):verify(db)


def test_attached_database_refuses_even_after_limit_is_restored(db):
    with pytest.raises(sqlite3.OperationalError):db.execute("ATTACH ':memory:' AS extra")
    db.setlimit(sqlite3.SQLITE_LIMIT_ATTACHED, 1)
    db.execute("ATTACH ':memory:' AS extra")
    db.setlimit(sqlite3.SQLITE_LIMIT_ATTACHED, 0)
    with pytest.raises(storage.StorageIntegrityError, match='attached database'):verify(db)


def stored_event():
    e = claimed_fixture()['samples'][0]['record']
    return e['request_id'], e['generation'], e['body_sha256'], encode(e).decode()


def test_canonical_stored_receipt_roundtrips():
    row = stored_event()
    assert storage.decode_event(*row) == claimed_fixture()['samples'][0]['record']


@pytest.mark.parametrize('attack', ['not-json', 'list', 'extra', 'missing', 'duplicate', 'nan', 'deep', 'oversized', 'whitespace', 'unicode'])
def test_bounded_strict_json_receipts(attack):
    row = list(stored_event());event = json.loads(row[3])
    if attack == 'not-json':row[3] = 'not JSON'
    elif attack == 'list':row[3] = '[]'
    elif attack == 'extra':event['unknown'] = True;row[3] = json.dumps(event)
    elif attack == 'missing':del event['target'];row[3] = json.dumps(event)
    elif attack == 'duplicate':row[3] = row[3][:-1] + ',"target":1}'
    elif attack == 'nan':event['proposal'] = float('nan');row[3] = json.dumps(event)
    elif attack == 'deep':row[3] = '[' * 1500 + '0' + ']' * 1500
    elif attack == 'oversized':row[3] = ' ' * 4097
    elif attack == 'whitespace':row[3] += ' '
    else:event['request_id'] = '\ud800';row[3] = json.dumps(event)
    with pytest.raises(storage.StorageIntegrityError):storage.decode_event(*row)


@pytest.mark.parametrize('field', ['source', 'target', 'action', 'generation', 'proposal'])
@pytest.mark.parametrize('kind', ['boolean', 'float'])
def test_numeric_receipt_aliases_refuse(field, kind):
    row = list(stored_event());event = json.loads(row[3])
    event[field] = bool(event[field]) if kind == 'boolean' else float(event[field])
    row[3] = json.dumps(event)
    with pytest.raises(storage.StorageIntegrityError):storage.decode_event(*row)


@pytest.mark.parametrize('field', ['request_hex', 'reply_hex', 'row_request_hex', 'row_reply_hex', 'source_id', 'event_sha256'])
def test_noncanonical_stored_packet_or_digest_refuses(field):
    row = list(stored_event());event = json.loads(row[3]);event[field] += ' '
    row[3] = json.dumps(event)
    with pytest.raises(storage.StorageIntegrityError):storage.decode_event(*row)


def test_receipt_count_and_native_sqlite_length_budget(db):
    row = stored_event()
    db.executemany('INSERT INTO events VALUES(?,?,?,?)', [(str(i), i, row[2], row[3]) for i in range(1, 6)])
    with pytest.raises(storage.StorageIntegrityError, match='count exceeds'):storage.events(db)
    with pytest.raises(sqlite3.DataError):db.execute('INSERT INTO public VALUES(?)', ('x' * 65537,))
    assert db.execute('SELECT COUNT(*) FROM public').fetchone() == (0,)
