"""Hostile same-schema stores and append failures stay inside explicit budgets."""

from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from research.authorization_history_v1 import history as h
from research.authorization_history_v1.test_history import _fixture, _sign


class ResourceTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "history.sqlite"
        self.authority, self.witness, self.root = _fixture()
        self.store = h.History.create(self.path, self.root)

    def intent(self, event_id=b"one", candidate=b"model"):
        payload = h.proposed_payload(self.root, self.store.expected_anchor, event_id=event_id,
                                     candidate=candidate, certificate=b"certificate")
        return _sign(payload, self.authority, self.witness)

    def sql(self, statement, parameters=()):
        with sqlite3.connect(self.path) as connection:
            connection.execute(statement, parameters)

    def assert_metadata_rejection(self, message):
        before = self.path.read_bytes()
        # Budget checks must reject before any envelope is returned to Python.
        with patch.object(h.Envelope, "decode", side_effect=AssertionError("BLOB fetched too early")):
            with self.assertRaisesRegex(h.Rejected, message):
                self.store.snapshot()
        self.assertEqual(before, self.path.read_bytes())

    def test_event_count_is_checked_before_loading_even_invalid_same_schema_rows(self):
        raw = self.intent()
        with sqlite3.connect(self.path) as connection:
            connection.executemany("INSERT INTO events VALUES (?, ?)",
                                   ((i, raw) for i in range(1, h.MAX_EVENTS + 2)))
        self.assert_metadata_rejection("event count")

    def test_aggregate_length_checked_before_loading_same_schema_rows(self):
        raw = self.intent()
        self.sql("INSERT INTO events VALUES (1, ?)", (raw,))
        self.sql("INSERT INTO events VALUES (2, ?)", (raw,))
        with patch.object(h, "MAX_TOTAL_WIRE", 2 * len(raw) - 1):
            self.assert_metadata_rejection("wire bytes")

    def test_oversized_real_blob_uses_length_metadata_before_fetch(self):
        # zeroblob creates a real on-disk oversized BLOB without a Python copy.
        self.sql("INSERT INTO events VALUES (1, zeroblob(?))", (h.MAX_WIRE + 1,))
        self.assert_metadata_rejection("wire bytes")

    def test_oversized_root_and_head_metadata_rejected_before_returning_blobs(self):
        self.sql("UPDATE config SET root=zeroblob(?)", (h.MAX_WIRE + 1,))
        self.assert_metadata_rejection("root metadata")
        self.sql("UPDATE config SET root=?", (self.root.encode(),))
        self.sql("UPDATE head SET incumbent=zeroblob(?)", (h.MAX_BYTES + 1,))
        self.assert_metadata_rejection("head metadata")

    def test_sqlite_connection_has_actual_row_length_limit(self):
        connection = h._connect(self.path)
        self.addCleanup(connection.close)
        self.assertEqual(connection.getlimit(sqlite3.SQLITE_LIMIT_LENGTH), h.SQLITE_LENGTH_LIMIT)
        with self.assertRaises(sqlite3.DataError):
            connection.execute("SELECT zeroblob(?)", (h.SQLITE_LENGTH_LIMIT + 1,)).fetchone()

    def test_append_event_count_limit_preserves_database_and_anchor(self):
        final = self.store.append(self.intent())
        raw = self.intent(b"two")
        before = self.path.read_bytes()
        with patch.object(h, "MAX_EVENTS", 1):
            with self.assertRaisesRegex(h.Rejected, "event count"):
                self.store.append(raw)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(self.store.snapshot().anchor, final)

    def test_append_aggregate_limit_preserves_database_and_anchor(self):
        first = self.intent()
        final = self.store.append(first)
        second = self.intent(b"two")
        before = self.path.read_bytes()
        with patch.object(h, "MAX_TOTAL_WIRE", len(first) + len(second) - 1):
            with self.assertRaisesRegex(h.Rejected, "wire bytes"):
                self.store.append(second)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(self.store.snapshot().anchor, final)

    def test_append_database_growth_limit_rolls_back_insert_and_head(self):
        before = self.path.read_bytes()
        raw = self.intent(candidate=b"large" * 10000)
        with patch.object(h, "MAX_DATABASE_BYTES", len(before)):
            with self.assertRaisesRegex(h.Rejected, "Database pages"):
                self.store.append(raw)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(self.store.snapshot().anchor, h.initial(self.root))

    def test_sparse_oversized_file_and_symlink_rejected_before_sqlite_open(self):
        huge = self.path.with_name("huge.sqlite")
        with huge.open("wb") as stream:
            stream.truncate(h.MAX_DATABASE_BYTES + 1)
        link = self.path.with_name("link.sqlite")
        link.symlink_to(self.path)
        with patch.object(h.sqlite3, "connect", side_effect=AssertionError("SQLite opened too early")):
            for path in (huge, link):
                with self.assertRaisesRegex(h.Rejected, "bounded regular nonsymlink"):
                    h.History(path, self.root, h.initial(self.root))

    def test_wal_and_oversized_rollback_sidecars_rejected_before_sqlite_open(self):
        for suffix in ("-wal", "-journal"):
            sidecar = Path(str(self.path) + suffix)
            with sidecar.open("wb") as stream:
                if suffix == "-journal":
                    stream.truncate(2 * h.MAX_DATABASE_BYTES + (1 << 20) + 1)
            with patch.object(h.sqlite3, "connect", side_effect=AssertionError("SQLite opened too early")):
                with self.assertRaisesRegex(h.Rejected, "sidecar"):
                    self.store.snapshot()
            sidecar.unlink()


if __name__ == "__main__":
    unittest.main(verbosity=2)
