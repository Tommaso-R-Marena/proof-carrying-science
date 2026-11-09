"""Adversarial grading and prospective-boundary tests, without final data."""
from copy import deepcopy
import hashlib
from pathlib import Path

import pytest

from research.scientific_review_v4.evaluation import compare_candidate, equation_match, grade, grade_workflow, value_equal
from research.scientific_review_v4 import benchmark


def example():
    raw = b"parameter k = 0.10\n"
    src = {"path": "model.txt", "sha256": hashlib.sha256(raw).hexdigest(),
           "byte_start": 0, "byte_end": len(raw), "quote": raw.decode()}
    expected = {"kind": "quantity", "entity": "k", "scope": "model", "relation": "declared_value", "value": "1e-1",
                "quantity_role": "parameter", "unit": None, "conditions": {}}
    ref = {"id": "R1", "expected_status": "supported", "typed_expectation": expected,
           "source": deepcopy(src), "assumptions": ["reviewer caveat"], "verification_expectation": {"status": "unknown", "level": "empirical"}}
    claim = {**deepcopy(expected), "id": "C1", "source": deepcopy(src), "authority": False, "meaning_status": "OPEN"}
    return claim, ref, {"model.txt": raw}


def test_strict_exact_numbers_and_case_sensitive_scope():
    claim, ref, artifacts = example()
    assert value_equal("0.10", "1e-1")
    assert not value_equal("0.10001", "0.10")
    assert not value_equal(True, "1")
    assert not value_equal("NaN", "0")
    assert not value_equal("0.10001", "0.10", tolerance="0.1")
    assert compare_candidate(claim, ref, artifacts)["typed_context_match"]
    for field in ("kind", "entity", "scope", "relation"):
        changed = dict(claim, **{field: claim[field].upper()})
        assert not compare_candidate(changed, ref, artifacts)["core_match"]


def test_quote_overlap_scoped_pass_and_correct_entity_do_not_credit_value():
    claim, ref, artifacts = example()
    claim["value"] = "99"
    result = grade([ref], {"claims": [claim]}, artifacts, [{"authority": False, "status": "PASS", "scientific_meaning": "OPEN"}])
    assert result["core_found"] == 0
    assert result["annotated_probe_precision"] == 0
    assert result["outcomes"][0]["comparisons"][0]["grounded"]


def test_context_slots_are_distinct_and_caveat_prose_not_required():
    claim, ref, artifacts = example()
    assert compare_candidate(claim, ref, artifacts)["typed_context_match"]
    assert compare_candidate(claim, ref, artifacts)["assumption_literals_present"] == 0
    for field, value in [("quantity_role", "initial_amount"), ("unit", "dimensionless"), ("conditions", {"state": "initial"})]:
        changed_ref = deepcopy(ref)
        changed_ref["typed_expectation"][field] = value
        compared = compare_candidate(claim, changed_ref, artifacts)
        assert compared["core_match"] and not compared["typed_context_match"]
    local = dict(claim, quantity_role="local_parameter")
    assert not compare_candidate(local, ref, artifacts)["typed_context_match"]


def test_suffix_canonicalization_recorded_ambiguous_or_forged_denied():
    claim, ref, artifacts = example()
    ref["source"]["path"] = "repo/fixtures/project/model.txt"
    compared = compare_candidate(claim, ref, artifacts)
    assert compared["core_match"]
    assert compared["source_paths"]["reference"]["rule"] == "unambiguous_literal_suffix"
    forged = deepcopy(claim)
    forged["source"]["sha256"] = "0" * 64
    assert not compare_candidate(forged, ref, artifacts)["core_match"]
    forged["source"] = dict(claim["source"], byte_start=True)
    assert not compare_candidate(forged, ref, artifacts)["core_match"]


def test_roles_only_annotated_pairs_and_counter_core_remains_visible():
    claim, ref, artifacts = example()
    other = dict(claim, id="std", quantity_role="parameter_std", value="0.001")
    graded = grade([ref], {"claims": [claim, other]}, artifacts)
    assert graded["annotated_probe_pairs"] == 1 and graded["annotated_probe_precision"] == 1
    ref["expected_status"] = "contradicted"
    ref["typed_expectation"]["unit"] = "kg"
    graded = grade([ref], {"claims": [claim]}, artifacts)
    assert graded["counterprobe_core_proposals"] == 1
    assert graded["counterprobe_full_context_proposals"] == 0
    assert graded["correct_counterprobe_abstentions"] == 0


def test_safe_equations_domains_stay_open_and_unsupported_calls_abstain():
    same = equation_match("(x*x)/x", "x")
    assert same["matches"] and same["domain_preservation"] == "OPEN"
    assert same["nonzero_obligations"]
    assert equation_match("2*x", "x+x")["matches"]
    assert not equation_match("__import__('os').system('true')", "0")["matches"]
    assert not equation_match("f(x)=0", "f(x)=0")["matches"]
    claim, ref, artifacts = example()
    ref["typed_expectation"].pop("value")
    ref["typed_expectation"].update(canonical_rhs="x+x", kind="equation")
    claim.update(kind="equation", rhs="2*x")
    assert compare_candidate(claim, ref, artifacts)["core_match"]


def test_authority_promotion_and_binding_failure_separate():
    claim, ref, artifacts = example()
    claim["source"]["sha256"] = "0" * 64
    graded = grade([ref], {"claims": [claim]}, artifacts, [{"authority": True, "scientific_meaning": "CERTIFIED"}])
    assert graded["unsupported_authority_count"] == 1
    assert graded["source_binding_failures"] == 1
    assert graded["scientific_meaning_certified"] == 0


def task(expected="supported"):
    return {"id": "Q1", "question": "Is the result reproduced?", "required_annotation_ids": ["R1"],
            "required_check_scopes": ["original_execution"], "expected_answer": expected}


def test_workflow_unmatched_or_unknown_for_expected_supported_gets_zero():
    claim, ref, artifacts = example()
    grading = grade([ref], {"claims": [claim]}, artifacts)
    generic = {"claims": [claim], "unresolved": [{"status": "UNKNOWN", "reason": "All scientific meaning open"}]}
    assert grade_workflow([task()], [ref], grading, generic)["correct"] == 0
    answer = {"task_id": "Q1", "annotation_ids": ["R1"], "answer": "unknown", "reason": "Execution unavailable",
              "check_scopes": {"original_execution": {"status": "unknown", "reason": "No executor for original MATLAB"}}}
    assert grade_workflow([task()], [ref], grading, generic, answers=[answer])["correct"] == 0
    result = grade_workflow([task("unknown")], [ref], grading, generic, answers=[answer])
    assert result["correct_informative_abstentions"] == 1
    answer["annotation_ids"] = []
    assert grade_workflow([task("unknown")], [ref], grading, generic, answers=[answer])["correct"] == 0


def test_workflow_pass_does_not_broaden_check_scope():
    claim, ref, artifacts = example()
    grading = grade([ref], {"claims": [claim]}, artifacts)
    check = {"id": "receipt", "status": "REPRODUCED_COMPUTATION", "authority": False, "scientific_meaning": "OPEN"}
    answer = {"task_id": "Q1", "annotation_ids": ["R1"], "answer": "supported",
              "check_scopes": {"original_execution": {"status": "supported", "check_ids": ["receipt"]}}}
    assert grade_workflow([task()], [ref], grading, {}, [check], answers=[answer])["correct"] == 0
    check.update(check_scopes=["original_execution"], annotation_ids=["R1"])
    assert grade_workflow([task()], [ref], grading, {}, [check], answers=[answer])["correct"] == 1


def test_final_gates_precede_labels_materialization_and_create_no_output(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Final labels or sources were touched before software guard")
    monkeypatch.setattr(benchmark, "load_reference", forbidden)
    monkeypatch.setattr(benchmark, "materialize", forbidden)
    monkeypatch.setattr(benchmark, "software_freeze", lambda: {"fixed": True})
    out = tmp_path / "final"
    with pytest.raises(ValueError, match="explicit"):
        benchmark.run_benchmark(out, split="final")
    with pytest.raises(ValueError, match="precommitted"):
        benchmark.run_benchmark(out, split="final", allow_final=True)
    with pytest.raises(ValueError, match="software changed"):
        benchmark.run_benchmark(out, split="final", allow_final=True, expected_software_sha256="0"*64)
    assert not out.exists()


def test_freeze_written_before_processing_and_failures_retained(tmp_path, monkeypatch):
    freeze = {"fixed": True}
    monkeypatch.setattr(benchmark, "software_freeze", lambda: freeze)
    def label_failure(*args, **kwargs):
        assert (tmp_path / "run/software-freeze.json").is_file()
        raise ValueError("label integrity failure")
    monkeypatch.setattr(benchmark, "load_reference", label_failure)
    with pytest.raises(ValueError, match="label integrity"):
        benchmark.run_benchmark(tmp_path / "run")
    assert '"FAILED_UNKNOWN"' in (tmp_path / "run/results.json").read_text()


def test_ambiguous_suffix_cannot_be_canonicalized():
    claim, ref, artifacts = example()
    ref["source"]["path"] = "repo/project/sub/model.txt"
    artifacts["sub/model.txt"] = artifacts["model.txt"]
    compared = compare_candidate(claim, ref, artifacts)
    assert not compared["core_match"]
    assert compared["source_paths"]["reference"]["rule"] == "unresolved_or_ambiguous"


def test_transformed_pdf_evidence_requires_exact_adapter_receipt():
    claim, ref, _ = example()
    raw, text = b"%PDF-opaque-original", "parameter k = 0.10\n"
    sha = hashlib.sha256(raw).hexdigest()
    transformation = {"kind": "adapter_extracted_text", "adapter": "pdf", "version": "1", "segment_index": 0,
                      "segment_sha256": hashlib.sha256(text.encode()).hexdigest(), "locator": {"page": 1},
                      "extracted_byte_start": 0, "extracted_byte_end": len(text.encode())}
    src = {"path": "paper.pdf", "sha256": sha, "quote": text, "transformation": transformation}
    inventory = {"artifacts": [{"path": "paper.pdf", "sha256": sha, "adapter": "pdf", "version": "1",
                                "segments": [{"text": text, "locator": {"page": 1}}]}]}
    claim["source"], ref["source"] = deepcopy(src), deepcopy(src)
    assert compare_candidate(claim, ref, {"paper.pdf": raw}, inventory)["core_match"]
    assert not compare_candidate(claim, ref, {"paper.pdf": raw})["core_match"]
    claim["source"]["transformation"]["version"] = "2"
    assert not compare_candidate(claim, ref, {"paper.pdf": raw}, inventory)["core_match"]


def test_actual_runtime_failure_keeps_unknown_outcomes_and_replay_failure(tmp_path):
    from types import SimpleNamespace
    claim, ref, artifacts = example()
    counter = deepcopy(ref)
    counter.update(id="R2", expected_status="contradicted")
    def failed(*args, **kwargs):
        raise ValueError("historical source size bound")
    engine = SimpleNamespace(run=failed, replay=failed)
    result = benchmark._pipeline_case(engine, tmp_path / "source", tmp_path / "package", [ref, counter], [], artifacts, v4=False)
    assert result["status"] == "FAILED_UNKNOWN"
    assert not result["valid_for_prospective_scoring"]
    assert result["independent_replay"]["status"] == "FAILED_UNKNOWN"
    assert len(result["grading"]["outcomes"]) == 2
    assert result["grading"]["correct_counterprobe_abstentions"] == 0
    assert result["checks"] == [] and result["numerical"] == []


def test_successful_grading_then_replay_failure_cannot_improve_aggregate(tmp_path):
    import json
    from types import SimpleNamespace
    claim, ref, artifacts = example()
    counter = deepcopy(ref)
    counter.update(id="R2", expected_status="contradicted")
    counter["typed_expectation"]["entity"] = "other"
    checks = [{"id": "ode", "checker": "conditional_ode_reconstruction", "status": "UNKNOWN", "authority": False},
              {"id": "domain", "checker": "parameter_domain", "status": "REPRODUCED_COMPUTATION", "authority": False},
              {"id": "source", "checker": "source_declaration", "status": "SOURCE_DECLARATION_CHECKED", "authority": False}]
    def completed(source, packet, **kwargs):
        packet.mkdir()
        (packet / "semantics.json").write_text(json.dumps({"claims": [claim]}))
        (packet / "checks.json").write_text(json.dumps(checks))
        return {"authority": False}
    def failed_replay(*args, **kwargs):
        raise ValueError("independent recomputation differs")
    engine = SimpleNamespace(run=completed, replay=failed_replay,
                             snapshot_artifacts=lambda path: ({"artifacts": []}, artifacts))
    invalid = benchmark._pipeline_case(engine, tmp_path / "source", tmp_path / "package", [ref, counter], [], artifacts, v4=False)
    assert invalid["grading"]["core_found"] == 1
    assert invalid["grading"]["typed_correct_probe_pairs"] == 1
    assert invalid["grading"]["correct_counterprobe_abstentions"] == 1
    assert invalid["provisional_grading"] == invalid["grading"]
    assert [c["id"] for c in invalid["numerical"]] == ["ode", "domain"]
    assert len(invalid["checks"]) == 3
    assert not invalid["valid_for_prospective_scoring"]
    # Include explicit provisional workflow successes to ensure they receive
    # the same replay gate as strict source interpretation achievements.
    invalid["workflow_utility"] = {"tasks": 8, "correct": 8, "correct_informative_abstentions": 4}
    valid = deepcopy(invalid)
    valid["valid_for_prospective_scoring"] = True
    cases = [{"baseline_v3_new_protocol": invalid, "review_v4_new_protocol": invalid},
             {"baseline_v3_new_protocol": valid, "review_v4_new_protocol": valid}]
    for totals in benchmark._aggregate(cases).values():
        assert totals["supported_total"] == 2 and totals["counterprobes"] == 2
        assert totals["annotated_probe_pairs"] == 2
        assert totals["core_found"] == 1 and totals["typed_context_found"] == 1
        assert totals["typed_correct_probe_pairs"] == 1
        assert totals["core_recall"] == 0.5 and totals["annotated_probe_precision"] == 0.5
        assert totals["correct_counterprobe_abstentions"] == 1
        assert totals["workflow_tasks"] == 16 and totals["workflow_correct"] == 8
        assert totals["workflow_correct_informative_abstentions"] == 4
        assert totals["failed_or_unreplayed_projects"] == 1
        assert totals["positive_credit_requires_independent_replay"]
    all_invalid = benchmark._aggregate([cases[0]])["review_v4_new_protocol"]
    assert all_invalid["core_recall"] == 0 and all_invalid["annotated_probe_precision"] == 0
    assert all_invalid["correct_counterprobe_abstentions"] == 0
    assert all_invalid["workflow_correct"] == 0 and all_invalid["workflow_tasks"] == 8
