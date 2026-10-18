"""Load and verify dataset provenance manifests."""

from __future__ import annotations

import json
from pathlib import Path

from ..core.hashing import sha256_file
from ..core.errors import ErrorCode, PcsNextError

FIX = Path(__file__).resolve().parents[2] / "fixtures" / "journal_demos"


def verify_manifest(root: Path | None = None) -> dict:
    root = root or FIX
    man = json.loads((root / "MANIFEST.json").read_text(encoding="utf-8"))
    findings = []
    for ds in man["datasets"]:
        path = root / ds["path"]
        if not path.is_file():
            findings.append({"path": ds["path"], "error": "missing"})
            continue
        digest = sha256_file(path)
        if digest != ds["sha256"]:
            findings.append({"path": ds["path"], "error": "hash_mismatch", "expected": ds["sha256"], "actual": digest})
        size = path.stat().st_size
        if size != ds["bytes"]:
            findings.append({"path": ds["path"], "error": "size_mismatch", "expected": ds["bytes"], "actual": size})
    if findings:
        raise PcsNextError(ErrorCode.HASH_MISMATCH, "dataset manifest verification failed", details={"findings": findings})
    return {"ok": True, "n": len(man["datasets"]), "root": str(root)}
