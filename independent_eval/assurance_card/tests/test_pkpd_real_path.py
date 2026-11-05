"""Optional real-path demo: certify → verify → Assurance Card for pkpd example.

Skipped when pcs is unavailable or the example tree is missing.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from python_harness.card import build_and_write
from python_harness.pcs_cli import resolve_verify_argv

REPO_ROOT = Path(__file__).resolve().parents[3]
PKPD_MANIFEST = REPO_ROOT / "examples" / "pkpd_one_compartment" / "manifest.json"


def _pcs_available() -> bool:
    if shutil.which("pcs"):
        return True
    try:
        import pcs.cli  # noqa: F401

        return True
    except ImportError:
        return False


@pytest.mark.skipif(not PKPD_MANIFEST.is_file(), reason="pkpd example missing")
@pytest.mark.skipif(not _pcs_available(), reason="pcs CLI unavailable")
def test_pkpd_certify_verify_assurance_card(tmp_path: Path):
    evidence = tmp_path / "pkpd_evidence"
    evidence.mkdir()
    certify_argv = [
        sys.executable,
        "-m",
        "pcs.cli",
        "certify",
        str(PKPD_MANIFEST),
        "-o",
        str(evidence),
    ]
    # Ensure repo root is importable for pcs.
    env = dict(**{k: v for k, v in __import__("os").environ.items()})
    # Prefer running with repo on PYTHONPATH.
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = (
        str(REPO_ROOT) if not existing else f"{REPO_ROOT}{__import__('os').pathsep}{existing}"
    )
    cert_proc = subprocess.run(
        certify_argv,
        capture_output=True,
        text=True,
        timeout=120,
        cwd=str(REPO_ROOT),
        env=env,
    )
    assert cert_proc.returncode == 0, cert_proc.stderr
    cert = evidence / "certificate.json"
    assert cert.is_file()

    # Authority verify must resolve.
    argv = resolve_verify_argv(cert)
    assert argv is not None

    def runner(cmd, **kwargs):
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(REPO_ROOT),
            env=env,
        )

    out = tmp_path / "pkpd-card"
    card, written = build_and_write(evidence, out, fmt="both", runner=runner)
    assert written["json"].is_file()
    assert written["html"].is_file()
    assert card["card_issues_accept"] is False
    assert card["inspection_is_not_authority"] is True
    assert card["authority"]["attempted"] is True
    assert card["authority"]["ok"] is True
    assert card["authority"]["returncode"] == 0
    # Claims should include computational PKPD claims.
    claim_ids = {c["id"] for c in card["inspection"]["claims"]}
    assert "C_PK_CONTRACT" in claim_ids or "C_PK_REPLAY" in claim_ids
    assert card["lane_consistency"]["overall"] == "agreement"
    payload = json.loads(written["json"].read_text(encoding="utf-8"))
    assert payload["authority"]["ok"] is True
    html = written["html"].read_text(encoding="utf-8")
    assert "skip-link" in html
    assert "never certifies" in html.lower() or "LIMITATIONS" in html
