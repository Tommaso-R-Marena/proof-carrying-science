"""Finite reference semantics and precommit checks for the fixed SQL adapter.

The Lean model proves properties of the corresponding finite row abstraction.
This Python/SQLite implementation is differentially tested, not source-extracted.
"""
from __future__ import annotations
from dataclasses import dataclass
import sqlite3

PRIVATE = 'PCS_SYNTHETIC_PRIVATE_CANARY'
PUBLIC = 'APPROVED_PUBLIC_SUMMARY'


@dataclass(frozen=True)
class Rows:
    value: str
    loaded: bool
    sanitized: bool
    public: tuple[str, ...]


def read_rows(db: sqlite3.Connection) -> Rows:
    # LIMIT bounds accidental row multiplication while still detecting it.
    payload = db.execute('SELECT value,loaded,sanitized FROM payload LIMIT 2').fetchall()
    public = db.execute('SELECT value FROM public LIMIT 2').fetchall()
    if len(payload) != 1 or len(public) > 1:
        raise ValueError('fixed adapter row cardinality mismatch')
    value, loaded, sanitized = payload[0]
    if (type(value) is not str or value not in (PRIVATE, PUBLIC)
            or type(loaded) is not int or loaded not in (0, 1)
            or type(sanitized) is not int or sanitized not in (0, 1)
            or any(type(row[0]) is not str or row[0] != PUBLIC for row in public)):
        raise ValueError('fixed adapter row type/value mismatch')
    return Rows(value, bool(loaded), bool(sanitized), tuple(row[0] for row in public))


def valid(state: int, rows: Rows) -> bool:
    if type(state) is not int or type(rows) is not Rows:
        return False
    if (type(rows.value) is not str or rows.value not in (PRIVATE, PUBLIC)
            or type(rows.loaded) is not bool or type(rows.sanitized) is not bool
            or type(rows.public) is not tuple or any(type(v) is not str or v != PUBLIC for v in rows.public)):
        return False
    if state in (0, 1):
        return not rows.loaded and not rows.public and rows.sanitized == (rows.value == PUBLIC)
    if state == 2:
        return rows == Rows(PRIVATE, True, False, ())
    if state == 3:
        return rows == Rows(PUBLIC, True, True, ())
    if state == 4:
        return rows == Rows(PUBLIC, True, True, (PUBLIC,))
    return False


def project(state: int, action: int, rows: Rows) -> tuple[int, Rows]:
    """Expected complete materialized effects, computed before actual SQL runs."""
    if type(action) is not int or not valid(state, rows):
        raise ValueError('fixed adapter precondition mismatch')
    if (state, action) == (0, 0):
        return 1, rows
    if (state, action) == (1, 1):
        return (3 if rows.value == PUBLIC else 2), Rows(rows.value, True, rows.sanitized, ())
    if (state, action) == (2, 2):
        return 3, Rows(PUBLIC, True, True, ())
    if (state, action) == (3, 3):
        return 4, Rows(PUBLIC, True, True, (PUBLIC,))
    raise ValueError('no modeled fixed adapter step')


def check_effects(db: sqlite3.Connection, target: int, expected: tuple[int, Rows]) -> None:
    if not db.in_transaction:
        raise ValueError('fixed adapter checks require an open transaction')
    if type(target) is not int or target != expected[0] or read_rows(db) != expected[1]:
        raise ValueError('fixed adapter postcondition mismatch before commit')
