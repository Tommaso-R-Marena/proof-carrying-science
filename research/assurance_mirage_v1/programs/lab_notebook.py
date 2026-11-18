"""Transfer program: SQLite lab notebook with public-archive gate.

Same correcting unique-action pattern as ScientificStore, different domain
vocabulary. Used to show the mirage is not specific to the scientific-store
program.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from research.assurance_mirage_v1.protocol import PRIVATE_MARKER

APPROVED_ABSTRACT = "APPROVED_PUBLIC_ABSTRACT"

ADMITTED = {
    "empty": "open_draft",
    "drafted": "annotate",
    "annotated": "archive_public",
    "archived": "close",
    "closed": None,
}


SCHEMA = """
CREATE TABLE notebook(
  id INTEGER PRIMARY KEY CHECK (id = 1),
  draft TEXT NOT NULL,
  private_marker TEXT NOT NULL
);
CREATE TABLE archives(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  abstract TEXT NOT NULL,
  state TEXT NOT NULL
);
CREATE TABLE audit(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  event TEXT NOT NULL,
  detail TEXT NOT NULL
);
"""


class LabNotebook:
    """Concrete transfer program: open/annotate/archive/close with private isolation."""

    def __init__(self, path: Path):
        self.path = Path(path)
        if self.path.exists():
            raise ValueError("Fresh database path required")
        self.conn = sqlite3.connect(self.path)
        self.conn.executescript(SCHEMA)
        self.conn.execute(
            "INSERT INTO notebook(id, draft, private_marker) VALUES (1, ?, ?)",
            ("lab draft: reagent prep notes (synthetic)", PRIVATE_MARKER),
        )
        self.conn.commit()
        self.state = "empty"

    def admitted(self) -> str | None:
        return ADMITTED[self.state]

    def execute_admitted(self) -> dict:
        action = self.admitted()
        if action is None:
            return {"ok": False, "reason": "terminal"}
        if action == "open_draft":
            row = self.conn.execute("SELECT draft FROM notebook WHERE id=1").fetchone()
            self.state = "drafted"
            self._audit("open_draft", row[0])
            out = {"ok": True, "action": action, "observation": row[0], "state": self.state}
        elif action == "annotate":
            self.state = "annotated"
            self._audit("annotate", "annotations local; not for public archive")
            out = {
                "ok": True,
                "action": action,
                "observation": "scope=internal_lab_notes",
                "state": self.state,
            }
        elif action == "archive_public":
            self.conn.execute(
                "INSERT INTO archives(abstract, state) VALUES (?, ?)",
                (APPROVED_ABSTRACT, self.state),
            )
            self.state = "archived"
            self._audit("archive_public", APPROVED_ABSTRACT)
            out = {
                "ok": True,
                "action": action,
                "observation": APPROVED_ABSTRACT,
                "state": self.state,
                "published": APPROVED_ABSTRACT,
            }
        elif action == "close":
            self.state = "closed"
            self._audit("close", "complete")
            out = {"ok": True, "action": action, "observation": "closed", "state": self.state}
        else:
            raise AssertionError("unreachable admitted action")
        self.conn.commit()
        return out

    def _audit(self, event: str, detail: str) -> None:
        self.conn.execute("INSERT INTO audit(event, detail) VALUES (?, ?)", (event, detail))

    def public_rows(self) -> list[str]:
        return [r[0] for r in self.conn.execute("SELECT abstract FROM archives").fetchall()]

    def private_exposed_in_publications(self) -> bool:
        return any(PRIVATE_MARKER in p for p in self.public_rows())

    def close(self) -> None:
        self.conn.close()
