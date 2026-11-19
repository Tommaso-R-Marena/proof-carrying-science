import json

import pytest

import lean_compile_oracle as oracle
import sota_competitive as benchmark


def test_probe_accepts_one_declaration_only():
    with pytest.raises(ValueError):
        oracle.normalize_candidate("theorem t : True := by sorry\ntheorem u : False := by sorry")


def test_probe_rejects_free_variables():
    with pytest.raises(ValueError):
        oracle.normalize_candidate("theorem t : n = n")


def test_zero_demo_generation_entry_point(monkeypatch, tmp_path):
    monkeypatch.setattr(benchmark.protocol, "select", lambda path, n: [{"id": "row7", "english": "Seven."}])
    weights = tmp_path / "mock.gguf"
    weights.touch()
    monkeypatch.setattr(benchmark, "DEFAULT_GGUF", weights)
    seen = []

    def proposal(english, *, theorem_name, temperature):
        seen.append((english, theorem_name))
        assert (tmp_path / "run/protocol.json").is_file()
        return {"text": "example : True"}

    monkeypatch.setattr(benchmark, "kimina_autoformalize", proposal)
    monkeypatch.setattr(benchmark, "_load_minif2f", lambda n: [])
    monkeypatch.setattr(benchmark, "compile_lean", lambda text: {"compiled": True, "status": "WELL_TYPED_UNVALIDATED"})
    report = benchmark.run(output=tmp_path / "run", minif2f_n=0)
    assert seen == [("Seven.", "row7")]
    assert json.loads((tmp_path / "run/protocol.json").read_text())["demo_count"] == 0
    assert report["forml4_basic"]["proofs_checked"] == 0
    assert report["forml4_basic"]["semantically_evaluated"] == 0


def test_changed_basic_file_rejected_before_generation(tmp_path):
    file = tmp_path / "basic_test.json"
    file.write_text('[{"nl_problem": "a replacement"}]')
    with pytest.raises(ValueError, match="pinned release"):
        benchmark.protocol.select(file, 1)


def test_recorded_closure_and_cardinality_mismatches():
    from research.lean_recursive_autoformalization_v1.historical_statement_audit import ROOT, replay, review
    data = json.loads((ROOT / "sota_competitive_summary.json").read_text())
    rows = data["forml4_basic"]["rows"]
    for i, symbol in [(0, "closure"), (2, "Infinite")]:
        row = rows[i]
        code = row["attempts"][0]["code"]
        assert row["compiled"] and symbol in code
        assert review(row["english"], code)["status"] == "SEMANTICALLY_REJECTED"
        assert review(row["english"] + " changed", code)["status"] == "UNKNOWN"
        assert review(row["english"], "example : True")["status"] == "UNKNOWN"
    report = replay()
    assert (report["first_candidate_compile_count"], report["any_attempt_compile_count"]) == (28, 51)
    assert report["unassessed_successes"] == 49
