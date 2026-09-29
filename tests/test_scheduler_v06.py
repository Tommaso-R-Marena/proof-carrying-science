from __future__ import annotations

import base64
import json
import shutil
import subprocess
import sys
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from pcs.certificate_v06 import finalize_certificate_hashes_v06
from pcs.decision import assess_claim
from pcs.replay_v06 import verify_certificate_replay_v06
from pcs.scheduler_v06 import (
    SCHEDULER_STRATEGIES_V06,
    TELEMETRY_FORMAT_V06,
    append_telemetry_history_v06,
    load_telemetry_history_v06,
    plan_evidence_v06,
    scheduler_report_v06,
    write_telemetry_v06,
)


ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "tests" / "v06_golden"
META = json.loads((GOLDEN / "metadata.json").read_text(encoding="utf-8"))


def _multi_check_certificate() -> dict:
    specs = [
        {
            "type": "unit_compatible",
            "left_unit": "mg/L",
            "right_unit": "g/m^3",
        },
        {
            "type": "reaction_balance",
            "reactants": [
                {"formula": "N2", "coefficient": 1},
                {"formula": "H2", "coefficient": 3},
            ],
            "products": [{"formula": "NH3", "coefficient": 2}],
        },
        {
            "type": "unit_compatible",
            "left_unit": "h",
            "right_unit": "min",
        },
    ]

    evidence = []
    claims = []
    for i, spec in enumerate(specs, start=1):
        evidence_id = f"E{i}"
        claim_id = f"C{i}"
        item = {
            "id": evidence_id,
            "kind": "computational_test",
            "claim_ids": [claim_id],
            "outcome": "PASS",
            "checker": "pcs-python-kernel/0.6.0-dev",
            "predicate": spec,
            "artifact_ids": [],
            "check_spec": spec,
        }
        evidence.append(item)
        claims.append(
            {
                "id": claim_id,
                "statement": f"Check {i} passes.",
                "kind": "computational",
                "predicate": spec,
                "required_evidence": [evidence_id],
                "assumptions": [],
                "assessment": {},
            }
        )

    evidence_map = {x["id"]: x for x in evidence}
    for claim in claims:
        claim["assessment"] = assess_claim(claim, evidence_map)

    source = {
        "spec_version": "pcs-0.6",
        "checker_version": "pcs-python-kernel/0.6.0-dev",
        "canonical_json_profile": "pcs-jcs-rfc8785-v1",
        "semantic_hash_format": "pcs-certificate-semantic-sha256-v2",
        "integrity_hash_format": "pcs-certificate-integrity-sha256-v2",
        "generated_at": "2026-09-29T00:00:00+00:00",
        "subject": "adaptive scheduler semantics test",
        "mission_scope": "test scheduling without changing scientific semantics",
        "assumptions": [],
        "claims": claims,
        "artifacts": [],
        "evidence": evidence,
        "workflow": {"nodes": []},
        "workflow_summary": {"node_count": 0, "topological_order": []},
        "semantic_hash": "",
        "integrity_hash": "",
    }
    return finalize_certificate_hashes_v06(source)


def _history() -> list[dict]:
    runs = []
    for i in range(10):
        runs.append(
            {
                "format": TELEMETRY_FORMAT_V06,
                "recorded_at": f"2026-09-29T00:{i:02d}:00+00:00",
                "certificate_semantic_hash": f"{i:064x}",
                "checker_version": "pcs-python-kernel/0.6.0-dev",
                "scheduler": {
                    "strategy": "manifest",
                    "execution_order": [f"old-unit-{i}", f"old-reaction-{i}"],
                },
                "checks": [
                    {
                        "evidence_id": f"old-unit-{i}",
                        "check_type": "unit_compatible",
                        "artifact_count": 0,
                        "input_bytes": 0,
                        "outcome": "PASS",
                        "duration_ms": 10.0 + i * 0.1,
                        "cpu_ms": 9.0 + i * 0.1,
                    },
                    {
                        "evidence_id": f"old-reaction-{i}",
                        "check_type": "reaction_balance",
                        "artifact_count": 0,
                        "input_bytes": 0,
                        "outcome": "FAIL",
                        "duration_ms": 1.0 + i * 0.01,
                        "cpu_ms": 0.8 + i * 0.01,
                    },
                ],
                "summary": {},
            }
        )
    return runs

def _write_public_key(path: Path) -> None:
    key = Ed25519PublicKey.from_public_bytes(
        base64.b64decode(META["public_key_raw_base64"], validate=True)
    )
    path.write_bytes(
        key.public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )


def _copy_package(tmp_path: Path) -> Path:
    package = tmp_path / "package"
    package.mkdir()
    for rel in [
        "certificate.json",
        "certificate_signature.json",
        "package_manifest.json",
        "package_signature.json",
        "artifacts/fixture.bin",
        "normalized/index.json",
        META["normalized_wire_path"],
    ]:
        src = GOLDEN / rel
        dst = package / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
    return package


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "pcs.cli", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_all_scheduler_strategies_preserve_scientific_replay_semantics():
    cert = _multi_check_certificate()
    history = _history()
    baseline = verify_certificate_replay_v06(cert, {})
    assert baseline["valid"], baseline["errors"]

    for strategy in SCHEDULER_STRATEGIES_V06:
        sink = {}
        result = verify_certificate_replay_v06(
            cert,
            {},
            scheduler_strategy=strategy,
            scheduler_history=history,
            telemetry_sink=sink,
        )
        assert result["valid"], (strategy, result["errors"])
        assert result["claim_statuses"] == baseline["claim_statuses"]
        assert result["evidence"] == baseline["evidence"]
        assert sink["format"] == TELEMETRY_FORMAT_V06
        assert len(sink["checks"]) == len(cert["evidence"])
        assert sorted(x["evidence_id"] for x in sink["checks"]) == ["E1", "E2", "E3"]
        assert result["scheduler"]["all_mandatory_checks_execute"] is True
        assert result["scheduler"]["scientific_verdict_uses_scheduler"] is False


def test_bandit_learns_to_prioritize_failure_prone_cheap_reaction_check():
    cert = _multi_check_certificate()
    plan = plan_evidence_v06(
        cert["evidence"],
        {},
        strategy="bandit",
        history=_history(),
        bandit_alpha=1.0,
    )

    assert plan["bandit_readiness"]["ready"] is True
    assert plan["requested_strategy"] == "bandit"
    assert plan["strategy"] == "bandit"
    assert plan["execution_order"][0] == "E2"
    assert plan["candidates"][1]["check_type"] == "reaction_balance"
    assert plan["candidates"][1]["scores"]["bandit_score"] > 0


def test_shadow_bandit_recommends_without_changing_manifest_order():
    cert = _multi_check_certificate()
    result = verify_certificate_replay_v06(
        cert,
        {},
        scheduler_strategy="manifest",
        scheduler_history=_history(),
        shadow_bandit=True,
    )

    assert result["valid"], result["errors"]
    assert result["scheduler"]["execution_order"] == ["E1", "E2", "E3"]
    assert result["scheduler"]["shadow_bandit_order"][0] == "E2"


def test_telemetry_history_round_trip_and_chronological_report(tmp_path):
    history_path = tmp_path / "history.jsonl"
    for row in _history():
        append_telemetry_history_v06(row, history_path)

    loaded = load_telemetry_history_v06(history_path)
    assert loaded == _history()

    report = scheduler_report_v06(loaded)
    assert report["format"] == "pcs-scheduler-report-v1"
    summary = report["chronological_counterfactuals"]["summary"]
    assert set(summary) == set(SCHEDULER_STRATEGIES_V06)
    assert summary["manifest"]["evaluated_runs"] == 10
    assert summary["bandit"]["evaluated_runs"] == 10


def test_write_telemetry_refuses_accidental_overwrite(tmp_path):
    telemetry = _history()[0]
    output = tmp_path / "run.json"
    write_telemetry_v06(telemetry, output)

    try:
        write_telemetry_v06(telemetry, output)
    except Exception as exc:
        assert "refusing to overwrite" in str(exc)
    else:
        raise AssertionError("telemetry overwrite was not refused")


def test_cli_can_emit_and_append_scheduler_telemetry_then_report_it(tmp_path):
    package = _copy_package(tmp_path)
    public_key = tmp_path / "public.pem"
    telemetry = tmp_path / "telemetry.json"
    history = tmp_path / "history.jsonl"
    report = tmp_path / "scheduler-report.json"
    _write_public_key(public_key)

    proc = _run(
        "verify-v06",
        str(package),
        "--public-key",
        str(public_key),
        "--scheduler",
        "failure-per-second",
        "--shadow-bandit",
        "--scheduler-telemetry-out",
        str(telemetry),
        "--scheduler-telemetry-append",
        str(history),
    )

    assert proc.returncode == 0, proc.stdout + proc.stderr
    output = json.loads(proc.stdout)
    saved = json.loads(telemetry.read_text(encoding="utf-8"))
    assert output["valid"] is True
    assert output["replay_scheduler"]["strategy"] == "failure-per-second"
    assert output["scheduler_telemetry_written"] == str(telemetry.resolve())
    assert output["scheduler_history_appended"] == str(history.resolve())
    assert saved["format"] == TELEMETRY_FORMAT_V06
    assert saved["scheduler"]["all_mandatory_checks_execute"] is True
    assert len(history.read_text(encoding="utf-8").splitlines()) == 1

    report_proc = _run(
        "scheduler-report-v06",
        str(history),
        "-o",
        str(report),
    )
    assert report_proc.returncode == 0, report_proc.stdout + report_proc.stderr
    report_obj = json.loads(report.read_text(encoding="utf-8"))
    assert report_obj["format"] == "pcs-scheduler-report-v1"
    assert report_obj["history_runs"] == 1



def test_cold_start_bandit_falls_back_without_changing_semantics():
    cert = _multi_check_certificate()
    result = verify_certificate_replay_v06(
        cert,
        {},
        scheduler_strategy="bandit",
        scheduler_history=[],
    )

    assert result["valid"], result["errors"]
    assert result["scheduler"]["requested_strategy"] == "bandit"
    assert result["scheduler"]["strategy"] == "failure-per-second"
    assert result["scheduler"]["bandit_readiness"]["ready"] is False
    assert "cold-start guard" in result["scheduler"]["fallback_reason"]
    assert result["scheduler"]["all_mandatory_checks_execute"] is True
    assert result["scheduler"]["scientific_verdict_uses_scheduler"] is False
