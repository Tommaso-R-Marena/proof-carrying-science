"""Offline tests for unrestricted LLM benchmark (no network)."""
from __future__ import annotations

from pathlib import Path

from unrestricted_llm_benchmark import _load_samples, _parse_llm_json, run


def test_samples_present():
    items = _load_samples()
    assert len(items) >= 20
    benches = {i.get("benchmark") for i in items}
    assert "miniF2F" in benches
    assert "FormL4" in benches


def test_parse_llm_json():
    raw = '```json\n{"decision":"ABSTAIN","text":"","reason":"reals"}\n```'
    p = _parse_llm_json(raw)
    assert p["decision"] == "ABSTAIN"


def test_zero_shot_only(tmp_path: Path):
    summary = run(output=tmp_path / "u", limit=10, skip_llm=True)
    assert summary["overall"]["n"] == 10
    assert summary["pcs_scientific_authority"] is False
    benches = set(summary["by_benchmark"])
    assert "miniF2F" in benches or "FormL4" in benches
    # Pure external items should almost never zero-shot accept.
    for name in ("miniF2F", "FormL4"):
        if name in summary["by_benchmark"]:
            assert summary["by_benchmark"][name]["zero_shot_rate"] <= 0.2
