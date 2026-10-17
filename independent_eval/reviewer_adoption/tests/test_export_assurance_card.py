from __future__ import annotations

import json
import subprocess
from pathlib import Path

from independent_eval.reviewer_adoption.workbench.export_assurance_card import (
    EXIT_ABSENT,
    EXIT_OK,
    discover_assurance_card_root,
    main as bridge_main,
    run_assurance_card_export,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "workbench" / "fixtures" / "sample_bundle"


def test_discover_absent_when_root_missing(tmp_path: Path):
    result = discover_assurance_card_root(tmp_path / "no-assurance-card")
    assert result["status"] == "ABSENT"
    assert result["root"] is None


def test_export_absent_exit_code(tmp_path: Path):
    record = run_assurance_card_export(
        evidence=FIXTURE,
        out=tmp_path / "card",
        assurance_card_root=tmp_path / "missing-f",
    )
    assert record["export_status"] == "ABSENT"
    assert record["workbench_issues_accept"] is False
    assert record["bridge_is_not_authority"] is True
    assert record["discovery"]["status"] == "ABSENT"

    rc = bridge_main(
        [
            "--evidence",
            str(FIXTURE),
            "--out",
            str(tmp_path / "cli-card"),
            "--assurance-card-root",
            str(tmp_path / "missing-f"),
            "--bridge-record",
            str(tmp_path / "bridge.json"),
        ]
    )
    assert rc == EXIT_ABSENT
    payload = json.loads((tmp_path / "bridge.json").read_text(encoding="utf-8"))
    assert payload["export_status"] == "ABSENT"


def test_export_present_subprocesses_f(tmp_path: Path, monkeypatch):
    fake_f = tmp_path / "assurance_card"
    (fake_f / "python_harness").mkdir(parents=True)
    (fake_f / "python_harness" / "card.py").write_text("# fake\n", encoding="utf-8")
    (fake_f / "python_harness" / "__init__.py").write_text("", encoding="utf-8")

    def fake_run(argv, **kwargs):
        out_stem = Path(argv[argv.index("--out") + 1])
        out_stem.with_suffix(".json").write_text("{}\n", encoding="utf-8")
        return subprocess.CompletedProcess(
            args=argv, returncode=0, stdout="WROTE_JSON ok\n", stderr=""
        )

    record = run_assurance_card_export(
        evidence=FIXTURE,
        out=tmp_path / "exported",
        skip_verify=True,
        assurance_card_root=fake_f,
        runner=fake_run,
    )
    assert record["discovery"]["status"] == "PRESENT"
    assert record["export_status"] == "EXPORTED"
    assert record["ok"] is True
    assert record["returncode"] == 0
    assert "python_harness.card" in record["argv"]
    assert record["workbench_issues_accept"] is False
    # Evidence/out forwarded to F must be absolute (F cwd is assurance_card root).
    assert Path(record["evidence"]).is_absolute()
    assert Path(record["out"]).is_absolute()
    ev_idx = record["argv"].index("--evidence")
    assert Path(record["argv"][ev_idx + 1]).is_absolute()

    monkeypatch.setattr(
        "independent_eval.reviewer_adoption.workbench.export_assurance_card.subprocess.run",
        fake_run,
    )
    rc = bridge_main(
        [
            "--evidence",
            str(FIXTURE),
            "--out",
            str(tmp_path / "exported3"),
            "--skip-verify",
            "--assurance-card-root",
            str(fake_f),
        ]
    )
    assert rc == EXIT_OK
