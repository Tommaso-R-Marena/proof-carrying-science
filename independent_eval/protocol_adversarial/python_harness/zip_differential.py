"""Compare PCS ZIP acceptance with stdlib zipfile and an independent member inventory."""

from __future__ import annotations

import hashlib
import io
import json
import zipfile
from pathlib import Path
from typing import Any

from .paths import RESULTS


def _inventory_stdlib(raw: bytes) -> dict[str, Any]:
    try:
        with zipfile.ZipFile(io.BytesIO(raw), "r") as zf:
            names = zf.namelist()
            infos = []
            for info in zf.infolist():
                infos.append(
                    {
                        "filename": info.filename,
                        "file_size": info.file_size,
                        "compress_size": info.compress_size,
                        "compress_type": info.compress_type,
                        "CRC": info.CRC,
                        "external_attr": info.external_attr,
                    }
                )
            return {"ok": True, "names": names, "infos": infos, "error": None}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "names": [], "infos": [], "error": f"{type(exc).__name__}: {exc}"}


def _pcs_load(raw: bytes, tmp: Path) -> dict[str, Any]:
    tmp.mkdir(parents=True, exist_ok=True)
    path = tmp / "sample.pcs.zip"
    path.write_bytes(raw)
    try:
        from pcs.verifier_zip_v06 import load_package_zip_v06

        loaded = load_package_zip_v06(path)
        return {
            "ok": True,
            "member_names": sorted(loaded.get("package_files", {}).keys()),
            "bundle_sha256": loaded.get("bundle_sha256"),
            "error": None,
        }
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "member_names": [], "bundle_sha256": None, "error": f"{type(exc).__name__}: {exc}"}


def _craft_cases() -> list[tuple[str, bytes]]:
    # Minimal STORED ZIP with one member via zipfile
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_STORED) as zf:
        zf.writestr("hello.txt", b"hello")
    normal = buf.getvalue()

    # Path traversal
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_STORED) as zf:
        zf.writestr("../escape.txt", b"x")
    traversal = buf.getvalue()

    # Absolute path
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_STORED) as zf:
        zf.writestr("/tmp/abs.txt", b"x")
    absolute = buf.getvalue()

    # Duplicate names
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_STORED) as zf:
        zf.writestr("dup.txt", b"one")
        zf.writestr("dup.txt", b"two")
    duplicate = buf.getvalue()

    # Compression deflated (PCS high-assurance wants STORED canonical)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("deflated.txt", b"compress-me" * 20)
    deflated = buf.getvalue()

    truncated = normal[:20]
    garbage = b"not-a-zip-file"
    empty = b""

    return [
        ("normal_stored", normal),
        ("path_traversal", traversal),
        ("absolute_path", absolute),
        ("duplicate_names", duplicate),
        ("deflated_member", deflated),
        ("truncated", truncated),
        ("garbage", garbage),
        ("empty", empty),
    ]


def run_zip_differential(work: Path) -> dict[str, Any]:
    work.mkdir(parents=True, exist_ok=True)
    cases = []
    for name, raw in _craft_cases():
        std = _inventory_stdlib(raw)
        pcs = _pcs_load(raw, work / name)
        cases.append(
            {
                "id": name,
                "sha256": hashlib.sha256(raw).hexdigest(),
                "size": len(raw),
                "stdlib": std,
                "pcs_load": pcs,
                "disagreement": bool(std["ok"] != pcs["ok"]),
            }
        )
    report = {
        "format": "pcs-independent-zip-differential-v1",
        "case_count": len(cases),
        "disagreement_count": sum(1 for c in cases if c["disagreement"]),
        "cases": cases,
        "limits": {
            "note": "Bounded synthetic inputs only; disposable workspaces; no external hosts.",
        },
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "zip_differential.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report
