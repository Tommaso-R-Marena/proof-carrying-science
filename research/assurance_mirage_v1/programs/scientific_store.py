"""Real local program under test: SQLite scientific evidence store with publish gate."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from research.assurance_mirage_v1.protocol import APPROVED_SUMMARY, PRIVATE_MARKER


SCHEMA = """
CREATE TABLE evidence(
  id INTEGER PRIMARY KEY CHECK (id = 1),
  payload TEXT NOT NULL,
  private_marker TEXT NOT NULL
);
CREATE TABLE publications(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  summary TEXT NOT NULL,
  state TEXT NOT NULL
);
CREATE TABLE audit(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  event TEXT NOT NULL,
  detail TEXT NOT NULL
);
"""


class ScientificStore:
    """Concrete program: load/review/publish/finish with private marker isolation."""

    def __init__(self, path: Path):
        self.path = Path(path)
        if self.path.exists():
            raise ValueError("Fresh database path required")
        self.conn = sqlite3.connect(self.path)
        self.conn.executescript(SCHEMA)
        self.conn.execute(
            "INSERT INTO evidence(id, payload, private_marker) VALUES (1, ?, ?)",
            ("iris-like synthetic teaching rows: n=100 mean=5.1", PRIVATE_MARKER),
        )
        self.conn.commit()
        self.state = "start"

    def admitted(self) -> str | None:
        return {
            "start": "load_evidence",
            "loaded": "review_claim",
            "reviewed": "publish_summary",
            "published": "finish",
            "done": None,
        }[self.state]

    def execute_admitted(self) -> dict:
        """Execute only the unique admitted action; proposals cannot override."""
        action = self.admitted()
        if action is None:
            return {"ok": False, "reason": "terminal"}
        if action == "load_evidence":
            row = self.conn.execute("SELECT payload FROM evidence WHERE id=1").fetchone()
            self.state = "loaded"
            self._audit("load_evidence", row[0])
            out = {"ok": True, "action": action, "observation": row[0], "state": self.state}
        elif action == "review_claim":
            self.state = "reviewed"
            self._audit("review_claim", "finite teaching export; not clinical evidence")
            out = {
                "ok": True,
                "action": action,
                "observation": "scope=teaching_export",
                "state": self.state,
            }
        elif action == "publish_summary":
            self.conn.execute(
                "INSERT INTO publications(summary, state) VALUES (?, ?)",
                (APPROVED_SUMMARY, self.state),
            )
            self.state = "published"
            self._audit("publish_summary", APPROVED_SUMMARY)
            out = {
                "ok": True,
                "action": action,
                "observation": APPROVED_SUMMARY,
                "state": self.state,
                "published": APPROVED_SUMMARY,
            }
        elif action == "finish":
            self.state = "done"
            self._audit("finish", "complete")
            out = {"ok": True, "action": action, "observation": "done", "state": self.state}
        else:
            raise AssertionError("unreachable admitted action")
        self.conn.commit()
        return out

    def _audit(self, event: str, detail: str) -> None:
        self.conn.execute("INSERT INTO audit(event, detail) VALUES (?, ?)", (event, detail))

    def public_rows(self) -> list[str]:
        return [r[0] for r in self.conn.execute("SELECT summary FROM publications").fetchall()]

    def private_exposed_in_publications(self) -> bool:
        pubs = self.public_rows()
        return any(PRIVATE_MARKER in p for p in pubs)

    def close(self) -> None:
        self.conn.close()
