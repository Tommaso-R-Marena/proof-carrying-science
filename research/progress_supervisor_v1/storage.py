"""Exact fixed-ledger storage contract and bounded receipt decoding.

These are host/SQLite checks, not kernel proofs or an immutable storage root.
Schema SQL is compared as data and never adopted as executable authority.
"""
from __future__ import annotations
import re
import sqlite3

from pcs.jsonio import strict_json_loads
from .certificate import encode


class StorageIntegrityError(ValueError):
    """The fixed storage observation contract no longer holds."""


TABLES = {
    'meta': 'CREATE TABLE meta(state INTEGER,generation INTEGER,head TEXT)',
    'events': 'CREATE TABLE events(id TEXT PRIMARY KEY,generation INTEGER UNIQUE,body_sha TEXT,event_json TEXT)',
    'payload': 'CREATE TABLE payload(value TEXT,loaded INTEGER,sanitized INTEGER)',
    'public': 'CREATE TABLE public(value TEXT)',
}
SCHEMA = '; '.join(TABLES.values()) + ';'
EXPECTED_SCHEMA = tuple(sorted(
    [('table', name, name, sql) for name, sql in TABLES.items()] +
    [('index', 'sqlite_autoindex_events_1', 'events', None),
     ('index', 'sqlite_autoindex_events_2', 'events', None)]))
LIMITS = {
    sqlite3.SQLITE_LIMIT_LENGTH: 65536,
    sqlite3.SQLITE_LIMIT_SQL_LENGTH: 8192,
    sqlite3.SQLITE_LIMIT_ATTACHED: 0,
    sqlite3.SQLITE_LIMIT_TRIGGER_DEPTH: 0,
    sqlite3.SQLITE_LIMIT_VARIABLE_NUMBER: 64,
}
MAX_PAGES = 128
EVENT_FIELDS = frozenset((
    'request_id', 'generation', 'source', 'target', 'action', 'proposal',
    'proposal_classification', 'body_sha256', 'request_hex', 'reply_hex',
    'source_id', 'previous_sha256', 'pcs_authority', 'event_sha256',
    'row_request_hex', 'row_reply_hex',
))


def configure(db):
    """Only for a newly created connection/database, before its first transaction."""
    if db.in_transaction:
        raise StorageIntegrityError('fixed adapter storage initialization requires no transaction')
    db.enable_load_extension(False)
    for category, value in LIMITS.items():db.setlimit(category, value)
    db.execute('PRAGMA journal_mode=WAL')
    db.execute('PRAGMA synchronous=FULL')
    db.execute('PRAGMA trusted_schema=OFF')
    db.execute('PRAGMA read_uncommitted=OFF')
    db.execute('PRAGMA max_page_count=128')


def check(db):
    """Validate connection configuration and the exact schema in the owned snapshot."""
    if not db.in_transaction:
        raise StorageIntegrityError('fixed adapter storage requires an owned transaction')
    if any(db.getlimit(category) != value for category, value in LIMITS.items()):
        raise StorageIntegrityError('fixed adapter state connection limits changed')
    for pragma, expected in [('journal_mode', 'wal'), ('synchronous', 2),
                             ('trusted_schema', 0), ('read_uncommitted', 0),
                             ('max_page_count', MAX_PAGES)]:
        if db.execute('PRAGMA ' + pragma).fetchone() != (expected,):
            raise StorageIntegrityError('fixed adapter state connection policy changed: ' + pragma)
    if db.execute('PRAGMA page_count').fetchone()[0] > MAX_PAGES:
        raise StorageIntegrityError('fixed adapter state database exceeds page budget')
    databases = db.execute('PRAGMA database_list').fetchall()
    if any(name not in ('main', 'temp') for _, name, _ in databases):
        raise StorageIntegrityError('fixed adapter state has an attached database')
    # Inspect TEMP before any unqualified model-table query can be shadowed.
    if db.execute('SELECT name FROM temp.sqlite_schema LIMIT 1').fetchone() is not None:
        raise StorageIntegrityError('fixed adapter state TEMP schema is not empty')
    actual = db.execute('SELECT type,name,tbl_name,sql FROM main.sqlite_schema ORDER BY type,name LIMIT 7').fetchall()
    if tuple(actual) != EXPECTED_SCHEMA:
        raise StorageIntegrityError('fixed adapter state schema mismatch')


def _hex(value, size):
    return type(value) is str and len(value) == size * 2 and re.fullmatch('[0-9a-f]+', value) is not None


def decode_event(rid, generation, body_sha, encoded):
    """Reject malformed rows before hashing, native calls or SQL effects."""
    if (type(rid) is not str or re.fullmatch('[a-z0-9_-]{1,64}', rid) is None
            or type(generation) is not int or not 1 <= generation <= 4
            or not _hex(body_sha, 32) or type(encoded) is not str or len(encoded) > 4096):
        raise StorageIntegrityError('fixed adapter receipt storage fields invalid')
    try:event = strict_json_loads(encoded)
    except (ValueError, RecursionError) as exc:
        raise StorageIntegrityError('fixed adapter receipt JSON invalid') from exc
    if type(event) is not dict or set(event) != EVENT_FIELDS:
        raise StorageIntegrityError('fixed adapter receipt schema invalid')
    for key in ('source', 'target', 'action', 'generation'):
        if type(event[key]) is not int or not 0 <= event[key] < 65536:
            raise StorageIntegrityError('fixed adapter receipt integer invalid')
    if event['proposal'] is not None and (type(event['proposal']) is not int or not 0 <= event['proposal'] < 65536):
        raise StorageIntegrityError('fixed adapter receipt proposal invalid')
    if (event['request_id'] != rid or event['generation'] != generation
            or event['body_sha256'] != body_sha or event['pcs_authority'] is not False
            or event['proposal_classification'] not in ('TYPED_PROPOSAL', 'MALFORMED_FALLBACK')):
        raise StorageIntegrityError('fixed adapter receipt identity/type mismatch')
    for key in ('body_sha256', 'source_id', 'previous_sha256', 'event_sha256'):
        if not _hex(event[key], 32):raise StorageIntegrityError('fixed adapter receipt digest invalid')
    for key, size in [('request_hex', 6), ('reply_hex', 6), ('row_request_hex', 16), ('row_reply_hex', 2)]:
        if not _hex(event[key], size):raise StorageIntegrityError('fixed adapter receipt packet invalid')
    if encoded != encode(event).decode('ascii'):
        raise StorageIntegrityError('fixed adapter receipt storage is not canonical')
    return event


def events(db):
    rows = db.execute('SELECT id,generation,body_sha,event_json FROM events ORDER BY generation LIMIT 5').fetchall()
    if len(rows) > 4:
        raise StorageIntegrityError('fixed adapter receipt count exceeds model bound')
    return [(rid, generation, body_sha, decode_event(rid, generation, body_sha, encoded))
            for rid, generation, body_sha, encoded in rows]
