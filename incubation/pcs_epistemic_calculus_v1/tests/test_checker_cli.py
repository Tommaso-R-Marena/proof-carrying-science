import json
from pathlib import Path

from pcs_epistemic.checker import verify_certificate
from pcs_epistemic.cli import main


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "pk_dialectic"


def test_verify_dialectic_certificate():
    raw = (EXAMPLE / "dialectic_certificate.json").read_bytes()
    receipt = verify_certificate(raw)
    assert receipt["accepted"] is True
    assert receipt["production_authority"] is False


def test_verify_rejects_illicit_promotion():
    cert = {
        "format": "pcs-epistemic-certificate-v1",
        "kind": "assures",
        "level": "formal",
        "claim": {
            "id": "c",
            "required_class": "formal",
            "required_evidence": ["e"],
        },
        "evidence": [{"id": "e", "class": "computational", "accepted": True}],
    }
    receipt = verify_certificate(json.dumps(cert).encode())
    assert receipt["accepted"] is False


def test_cli_dialectic(tmp_path):
    ens = {
        "models": json.loads((EXAMPLE / "ensemble.json").read_text())["models"],
        "candidates": json.loads((EXAMPLE / "ensemble.json").read_text())["candidates"],
    }
    path = tmp_path / "ens.json"
    path.write_text(json.dumps(ens), encoding="utf-8")
    assert main(["dialectic", str(path)]) == 0
