"""Task 8 — formal/computational correctness vs scientific inadequacy."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python_harness.paths import INADEQUACY  # noqa: E402
from python_harness.pcs_cli import certify, load_json, verify_certificate  # noqa: E402


def test_inadequacy_index_lists_three_examples():
    index = load_json(INADEQUACY / "INDEX.json")
    assert len(index["examples"]) >= 3


def test_correct_but_inadequate_pkpd_still_verifies(tmp_path):
    ex = INADEQUACY / "examples" / "01_correct_but_inadequate_pkpd"
    out = tmp_path / "evidence"
    c = certify(ex / "manifest.json", out)
    assert c.ok, c.combined()
    cert = load_json(out / "certificate.json")
    for claim in cert["claims"]:
        assert claim["assessment"]["status"] == "COMPUTATIONALLY_SUPPORTED"
    v = verify_certificate(out / "certificate.json")
    assert v.ok, v.combined()
    # Scientific adequacy is not a certificate field — document via README.
    readme = (ex / "README.md").read_text(encoding="utf-8").lower()
    assert "adequacy" in readme
    assert "empirical" in readme or "clinical" in readme


def test_balanced_but_biologically_inadequate_verifies(tmp_path):
    ex = INADEQUACY / "examples" / "02_balanced_but_biologically_inadequate"
    out = tmp_path / "evidence"
    c = certify(ex / "manifest.json", out)
    assert c.ok, c.combined()
    cert = load_json(out / "certificate.json")
    assert cert["claims"][0]["assessment"]["status"] == "COMPUTATIONALLY_SUPPORTED"
    v = verify_certificate(out / "certificate.json")
    assert v.ok, v.combined()


def test_units_ok_quantity_inadequate_verifies(tmp_path):
    ex = INADEQUACY / "examples" / "03_units_ok_quantity_inadequate"
    out = tmp_path / "evidence"
    c = certify(ex / "manifest.json", out)
    assert c.ok, c.combined()
    v = verify_certificate(out / "certificate.json")
    assert v.ok, v.combined()
