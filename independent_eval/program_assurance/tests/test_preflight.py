"""Tests for local preflight gates."""

from __future__ import annotations

import json
from pathlib import Path

from python_harness import paths as p
from python_harness.preflight import run_preflight


def test_preflight_passes_on_clean_tree(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(p, "RESULTS", tmp_path / "results")
    monkeypatch.setattr(p, "INDEPENDENT_EVAL", tmp_path / "independent_eval")
    monkeypatch.setattr(p, "ROOT", tmp_path / "program_assurance")
    (tmp_path / "program_assurance").mkdir()
    (tmp_path / "independent_eval" / "ok").mkdir(parents=True)
    (tmp_path / "independent_eval" / "ok" / "a.txt").write_text("x\n", encoding="utf-8")

    # Avoid real git branch diffs for unit isolation.
    from python_harness import preflight as pref

    def fake_run_preflight_parts(**kwargs):
        # Call real function but stub nonoverlap via monkeypatch below
        return run_preflight(**kwargs)

    from python_harness import nonoverlap_auditor as na

    class FakeReport:
        changed_files = {"feature/x": ("independent_eval/ok/a.txt",)}
        missing_branches = ()
        errors = {}
        pair_overlaps = ()
        has_overlaps = False

        def to_dict(self):
            return {"has_overlaps": False}

    monkeypatch.setattr("python_harness.preflight.audit_branch_nonoverlap", lambda *a, **k: FakeReport())
    monkeypatch.setattr("python_harness.preflight.write_nonoverlap_report", lambda *a, **k: None)

    from python_harness import residual_trust as rt

    monkeypatch.setattr(
        rt,
        "rollup_residual_trust",
        lambda repo=None: {
            "sources_present": 1,
            "sources_missing": 0,
            "assumption_id_count": 2,
            "tcb_closed": False,
        },
    )
    monkeypatch.setattr(rt, "write_residual_trust_report", lambda *a, **k: None)

    report = fake_run_preflight_parts()
    assert report["pass"] is True
    assert report["gates"]["path_collision"]["pass"] is True
    assert (tmp_path / "results" / "preflight.json").is_file()


def test_preflight_fails_on_collision(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(p, "RESULTS", tmp_path / "results")
    monkeypatch.setattr(p, "INDEPENDENT_EVAL", tmp_path / "independent_eval")
    monkeypatch.setattr(p, "ROOT", tmp_path / "program_assurance")
    (tmp_path / "program_assurance").mkdir()
    pkg = tmp_path / "independent_eval" / "pkg"
    pkg.mkdir(parents=True)
    (pkg / "CHECKLIST.json").write_text("{}\n", encoding="utf-8")
    (pkg / "checklist.json").write_text("{}\n", encoding="utf-8")

    from python_harness import nonoverlap_auditor as na

    class FakeReport:
        changed_files = {"b": ()}
        missing_branches = ()
        errors = {}
        pair_overlaps = ()
        has_overlaps = False

    monkeypatch.setattr("python_harness.preflight.audit_branch_nonoverlap", lambda *a, **k: FakeReport())
    monkeypatch.setattr("python_harness.preflight.write_nonoverlap_report", lambda *a, **k: None)
    from python_harness import residual_trust as rt

    monkeypatch.setattr(
        rt,
        "rollup_residual_trust",
        lambda repo=None: {
            "sources_present": 0,
            "sources_missing": 1,
            "assumption_id_count": 0,
            "tcb_closed": False,
        },
    )
    monkeypatch.setattr(rt, "write_residual_trust_report", lambda *a, **k: None)

    report = run_preflight(check_nonoverlap=True, check_residual_trust=True)
    assert report["pass"] is False
    assert report["gates"]["path_collision"]["pass"] is False
    payload = json.loads((tmp_path / "results" / "preflight.json").read_text())
    assert payload["hard_failures"]
