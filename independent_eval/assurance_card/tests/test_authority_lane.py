from __future__ import annotations

import json
import subprocess
from pathlib import Path

from python_harness.card import build_assurance_card, compare_lanes
from python_harness.inspect_lane import inspect_evidence
from python_harness.pcs_cli import run_pcs_verify


def _fake_completed(
    *,
    returncode: int,
    stdout: str = "",
    stderr: str = "",
    argv: list[str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args=argv or ["pcs", "verify", "certificate.json"],
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
    )


def test_authority_agree_when_cli_ok(fixture_bundle: Path):
    cert = fixture_bundle / "certificate.json"

    def runner(argv, **kwargs):
        payload = {"valid": True, "errors": [], "certificate": str(cert)}
        return _fake_completed(returncode=0, stdout=json.dumps(payload), argv=list(argv))

    auth = run_pcs_verify(cert, runner=runner).to_dict()
    assert auth["cli_is_authority"] is True
    assert auth["attempted"] is True
    assert auth["ok"] is True
    assert auth["returncode"] == 0
    assert auth["duration_seconds"] is not None
    assert auth["argv"] and auth["argv"][-1].endswith("certificate.json")

    inspection = inspect_evidence(fixture_bundle)
    consistency = compare_lanes(authority=auth, inspection=inspection)
    assert consistency["overall"] == "agreement"


def test_authority_disagree_when_cli_fails_and_classes_supported(fixture_bundle: Path):
    cert = fixture_bundle / "certificate.json"

    def runner(argv, **kwargs):
        payload = {
            "valid": False,
            "errors": ["integrity hash mismatch"],
            "certificate": str(cert),
        }
        return _fake_completed(returncode=1, stdout=json.dumps(payload), argv=list(argv))

    card = build_assurance_card(fixture_bundle, runner=runner)
    assert card["authority"]["ok"] is False
    assert card["lane_consistency"]["overall"] == "disagreement"
    # Inspection classes must not be mutated by authority failure.
    replay = next(c for c in card["inspection"]["claims"] if c["id"] == "C_REPLAY")
    assert replay["inspection_class"] == "computationally_supported"
    assert card["card_issues_accept"] is False
    assert card["inspection_is_not_authority"] is True


def test_authority_inconclusive_when_cli_unavailable(monkeypatch, fixture_bundle: Path):
    monkeypatch.setattr(
        "python_harness.pcs_cli.resolve_verify_argv",
        lambda certificate: None,
    )
    auth = run_pcs_verify(fixture_bundle / "certificate.json").to_dict()
    assert auth["skipped"] is True
    assert auth["ok"] is None
    inspection = inspect_evidence(fixture_bundle)
    consistency = compare_lanes(authority=auth, inspection=inspection)
    assert consistency["overall"] == "inconclusive"


def test_authority_agree_when_cli_fails_and_rejected_class(tmp_path: Path, fixture_bundle: Path):
    # Build a tiny rejected-claim bundle by rewriting certificate status.
    import shutil

    bundle = tmp_path / "rejected"
    shutil.copytree(fixture_bundle, bundle)
    cert_path = bundle / "certificate.json"
    cert = json.loads(cert_path.read_text(encoding="utf-8"))
    for claim in cert["claims"]:
        claim["assessment"] = {"status": "REJECTED", "note": "forced reject fixture"}
        claim["kind"] = "computational"
    cert_path.write_text(json.dumps(cert), encoding="utf-8")
    # Drop receipt so it cannot override statuses.
    (bundle / "verification-receipt.json").unlink()

    def runner(argv, **kwargs):
        payload = {"valid": False, "errors": ["check failed"]}
        return _fake_completed(returncode=1, stdout=json.dumps(payload), argv=list(argv))

    card = build_assurance_card(bundle, runner=runner)
    assert card["authority"]["ok"] is False
    assert any(c["inspection_class"] == "rejected_or_failed" for c in card["inspection"]["claims"])
    assert card["lane_consistency"]["overall"] == "agreement"
