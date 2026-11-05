"""SHA-256 hashing helpers (offline, streaming)."""
from __future__ import annotations

import hashlib
from pathlib import Path


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: str | Path) -> str:
    """Compute SHA-256 of a file without loading it entirely into memory."""
    p = Path(path)
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_paths(paths: list[str | Path]) -> dict[str, str]:
    """Map each existing file path to its sha256 hex digest."""
    out: dict[str, str] = {}
    for raw in paths:
        p = Path(raw)
        if p.is_file():
            out[str(p.resolve())] = sha256_file(p)
    return out
