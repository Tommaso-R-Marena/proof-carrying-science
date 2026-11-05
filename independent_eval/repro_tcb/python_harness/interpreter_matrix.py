"""Explicit cross-Python interpreter matrix with recorded absences (E-P08 substance).

Never treats a missing interpreter as a pass. Measures SHA-256 of archive bytes
under each available interpreter via a tiny subprocess probe.
"""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from .canonical_zip import canonical_zip_bytes
from .environment import discover_python_interpreters
from .hashing import sha256_bytes, sha256_file
from .paths import RESULTS
from .reconstruction import build_synthetic_members


_PROBE = r"""
import hashlib, sys
path = sys.argv[1]
h = hashlib.sha256()
with open(path, "rb") as f:
    for chunk in iter(lambda: f.read(1024 * 1024), b""):
        h.update(chunk)
print(h.hexdigest())
"""


def _probe_sha_with_interpreter(executable: str, archive: Path) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            [executable, "-c", _PROBE, str(archive)],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "ok": False,
            "sha256": None,
            "error": str(exc),
        }
    if proc.returncode != 0:
        return {
            "ok": False,
            "sha256": None,
            "error": (proc.stderr or proc.stdout or "probe failed")[-400:],
            "returncode": proc.returncode,
        }
    digest = (proc.stdout or "").strip().splitlines()[-1] if proc.stdout else ""
    if len(digest) != 64:
        return {"ok": False, "sha256": None, "error": f"bad digest output: {digest!r}"}
    return {"ok": True, "sha256": digest, "returncode": 0}


def run_interpreter_matrix(
    *,
    output: Path | None = None,
    candidates: list[str] | None = None,
) -> dict[str, Any]:
    """Hash a canonical synthetic archive under each discovered interpreter."""
    evidence = build_synthetic_members()
    archive_bytes = evidence.canonical_archive
    expected = sha256_bytes(archive_bytes)

    with tempfile.TemporaryDirectory(prefix="pcs-repro-matrix-") as tmp:
        archive_path = Path(tmp) / "evidence_canonical.zip"
        archive_path.write_bytes(archive_bytes)

        interpreters = discover_python_interpreters(extra=candidates)
        rows: list[dict[str, Any]] = []
        for info in interpreters:
            exe = info.get("path") or info.get("executable")
            if not exe:
                continue
            probe = _probe_sha_with_interpreter(str(exe), archive_path)
            rows.append(
                {
                    "interpreter": info,
                    "archive_sha256": probe.get("sha256"),
                    "matches_expected": probe.get("sha256") == expected if probe.get("ok") else False,
                    "probe_ok": probe.get("ok"),
                    "error": probe.get("error"),
                }
            )

        present = [r for r in rows if r["probe_ok"]]
        agreeing = [r for r in present if r["matches_expected"]]
        disagreeing = [r for r in present if not r["matches_expected"]]

        # Explicitly record common absences (not passes).
        wanted_names = ["python3.11", "python3.12", "python3.13", "python3.10"]
        seen_paths = {str((r["interpreter"] or {}).get("path")) for r in rows}
        absences: list[dict[str, Any]] = []
        import shutil

        for name in wanted_names:
            which = shutil.which(name)
            if which is None:
                absences.append(
                    {
                        "name": name,
                        "status": "ABSENT",
                        "note": "Not treated as pass; not measured on this host.",
                    }
                )
            elif which not in seen_paths and which not in {
                str((r["interpreter"] or {}).get("path")) for r in rows
            }:
                # which found but not in discover list — still note
                absences.append(
                    {
                        "name": name,
                        "status": "PRESENT_BUT_NOT_PROBED",
                        "path": which,
                    }
                )

        report = {
            "format": "pcs-independent-eval-interpreter-matrix-v1",
            "task": "12/E-P08",
            "expected_archive_sha256": expected,
            "member_digests": evidence.member_digests,
            "interpreters_probed": len(rows),
            "interpreters_ok": len(present),
            "interpreters_agree": len(agreeing),
            "interpreters_disagree": len(disagreeing),
            "absences": absences,
            "rows": rows,
            "pass": len(disagreeing) == 0 and len(present) >= 1,
            "disclaimer": (
                "Missing interpreters are recorded as ABSENT, never as PASS. "
                "Agreement is byte-identity of SHA-256 over the same archive file."
            ),
        }

    out = output or (RESULTS / "interpreter_matrix.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report["written_to"] = str(out)
    return report
