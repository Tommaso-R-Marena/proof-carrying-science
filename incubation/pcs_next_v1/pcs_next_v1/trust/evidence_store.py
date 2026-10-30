"""Transactional evidence store with generation CAS and tamper-evident chain.

Caveat: a hash chain under attacker-controlled storage is NOT an immutable
trusted history. Rollback resistance requires an independently trusted
checkpoint or external trust anchor (documented, not assumed).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from ..core.canonical import canonicalize, canonical_hash
from ..core.errors import ErrorCode, PcsNextError


class EvidenceStore:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._meta_path = self.root / "meta.json"
        if not self._meta_path.exists():
            self._write_meta({"generation": 0, "head_hash": None, "events": []})

    def _read_meta(self) -> dict[str, Any]:
        return json.loads(self._meta_path.read_text(encoding="utf-8"))

    def _write_meta(self, meta: dict[str, Any]) -> None:
        tmp = self._meta_path.with_suffix(".tmp")
        data = canonicalize(meta)
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
        try:
            os.write(fd, data)
            os.fsync(fd)
        finally:
            os.close(fd)
        os.replace(tmp, self._meta_path)

    @property
    def generation(self) -> int:
        return int(self._read_meta()["generation"])

    def commit(
        self,
        event_type: str,
        payload: dict[str, Any],
        *,
        expected_generation: int | None = None,
    ) -> dict[str, Any]:
        meta = self._read_meta()
        if expected_generation is not None and expected_generation != meta["generation"]:
            raise PcsNextError(
                ErrorCode.GENERATION_CONFLICT,
                "evidence commit CAS failed",
                details={"expected": expected_generation, "actual": meta["generation"]},
            )
        prev = meta["head_hash"]
        body = {
            "event_type": event_type,
            "payload": payload,
            "prev_hash": prev,
            "generation": meta["generation"],
        }
        event_hash = canonical_hash(body)
        event_path = self.root / f"evt-{meta['generation']:08d}-{event_hash[:16]}.json"
        tmp = event_path.with_suffix(".tmp")
        tmp.write_bytes(canonicalize(body))
        tmp.replace(event_path)
        meta["events"].append({"hash": event_hash, "path": event_path.name})
        meta["head_hash"] = event_hash
        meta["generation"] = meta["generation"] + 1
        self._write_meta(meta)
        return {"event_hash": event_hash, "generation": meta["generation"], "prev_hash": prev}

    def verify_chain(self) -> dict[str, Any]:
        meta = self._read_meta()
        prev = None
        for i, ev in enumerate(meta["events"]):
            path = self.root / ev["path"]
            if not path.is_file():
                raise PcsNextError(ErrorCode.HASH_MISMATCH, f"missing event file {ev['path']}")
            body = json.loads(path.read_text(encoding="utf-8"))
            if body.get("prev_hash") != prev:
                raise PcsNextError(ErrorCode.HASH_MISMATCH, f"broken chain at index {i}")
            h = canonical_hash(body)
            if h != ev["hash"]:
                raise PcsNextError(ErrorCode.HASH_MISMATCH, f"event hash mismatch at {i}")
            prev = h
        if meta["events"] and meta["head_hash"] != meta["events"][-1]["hash"]:
            raise PcsNextError(ErrorCode.HASH_MISMATCH, "head_hash mismatch")
        return {
            "ok": True,
            "events": len(meta["events"]),
            "generation": meta["generation"],
            "head_hash": meta["head_hash"],
            "trust_caveat": (
                "Chain integrity under local storage only; not an external trust anchor."
            ),
        }
