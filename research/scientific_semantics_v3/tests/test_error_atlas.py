"""Independent checks of the frozen-diagnostic boundary, not successor scores."""
import hashlib
import json

import pytest

from research.scientific_semantics_v3 import error_atlas as atlas_module


@pytest.fixture(scope="module")
def atlas():
    return atlas_module.build_atlas()


def entries(atlas):
    return {a["annotation_id"]: a for s in atlas["splits"] for c in s["cases"] for a in c["supported_claims"]}


def test_all_supported_claims_and_historical_metrics_reproduce(atlas):
    assert [(s["summary"]["matched"], s["summary"]["supported"], s["summary"]["missed"]) for s in atlas["splits"]] == [(6, 21, 15), (1, 20, 19)]
    assert len(entries(atlas)) == 41
    assert len(atlas["splits"][1]["summary"]["failed_claim_ids"]) == 19
    assert all(c["grade_reproduced_byte_equivalent_json"] for s in atlas["splits"] for c in s["cases"])


def test_all_references_have_real_source_spans(atlas):
    for item in entries(atlas).values():
        assert item["source_reference_spans"]
        source = item["reference"]["source"]
        raw = (atlas_module.ROOT / source["path"]).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == source["sha256"]
        assert source["quote"] in raw.decode("utf-8")


def test_equivalence_diagnostic_does_not_change_frozen_miss(atlas):
    item = entries(atlas)["final-goldbeter-003"]
    assert not item["frozen_outcome"]["semantic_match_ids"]
    result = item["independent_diagnostic_equivalence"]
    assert result["status"] == "EQUAL_ON_COMMON_DEFINED_DOMAIN"
    assert result["nonzero_denominator_obligations"]
    assert result["authority"] is False


def test_real_wrong_unit_counterexample_retained_outside_probes(atlas):
    case = next(c for s in atlas["splits"] for c in s["cases"] if c["id"] == "scipy_integrate")
    extra = case["unannotated_diagnostic_counterexamples"]
    assert len(extra) == 2
    assert all(x["candidate"]["typed"]["unit"] == "N" and x["candidate"]["typed"]["value"] == "2" for x in extra)
    assert all("2N" in x["candidate"]["source"]["quote"] for x in extra)
    assert case["frozen_metrics"]["overall_extraction_precision"] is None


def test_reported_counts_remain_distinct_from_proved_truth(atlas):
    item = entries(atlas)["dev-scipy-003"]
    assert item["primary_failure_class"] == "reported_relation_grading_mismatch"
    assert item["frozen_outcome"]["semantic_match_ids"] == []
    q = next(c for c in item["source_overlapping_candidates"] if c["category"] == "quantities" and c["typed"].get("name") == "iterations")
    assert q["typed"]["value"] == "339"
    assert q["typed"]["relation"] == "reported_value"
    assert q["typed"]["authority"] is False


def test_unlinked_formal_result_does_not_certify_scientific_meaning(atlas):
    item = entries(atlas)["tyson-cdc2-conservation"]
    assert not item["frozen_outcome"]["semantic_match_ids"]
    assert item["unlinked_existing_scoped_check"][0]["conservation"]["certificates"][0]["initial_total"] == "1"
    assert item["unlinked_existing_scoped_check"][0]["kernel_certificate_statuses"] == ["KERNEL_CHECKED_FINITE_INTEGER_CONSERVATION"]


def test_unmodified_counterclaim_and_abstention_evidence(atlas):
    counterclaims = [a for s in atlas["splits"] for c in s["cases"] for a in c["counterclaim_probes"]]
    assert len(counterclaims) == 12
    assert all(not a["frozen_outcome"]["semantic_match_ids"] for a in counterclaims)
    assert atlas["unsupported_promotion_total"] == 0
    assert atlas["adjudication_provenance"]["human_domain_expert_review"] is False


def test_changed_historical_inputs_fail_closed(monkeypatch):
    monkeypatch.setattr(atlas_module, "FROZEN_INPUT_SHA256", {"evaluation.py": "0" * 64})
    with pytest.raises(ValueError, match="historical input changed"):
        atlas_module.build_atlas()


def test_committed_diagnostic_exactly_regenerates(atlas):
    assert json.loads((atlas_module.HERE / "evidence/error-atlas.json").read_text()) == atlas
    assert (atlas_module.HERE / "ERROR_ATLAS.md").read_text() == atlas_module.markdown(atlas)
