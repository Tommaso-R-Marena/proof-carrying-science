"""Actual malformed inputs and independent arithmetic expectations."""
import ast
from decimal import Decimal
from fractions import Fraction
import hashlib

import pytest

from research.scientific_semantics_v3 import adversarial, numerical, semantics


CASE_IDS = [
    "document_authority_injection", "uploaded_python_nonexecution", "symbolic_count_not_newtons",
    "foreign_sbml_container", "foreign_mathml_namespace", "duplicate_global_identifier",
    "duplicate_local_identifier", "duplicate_assignment_target", "reaction_global_identifier_collision",
    "local_shadowing_positive_control", "undeclared_math_symbol", "unit_case_and_affine_abstention",
    "nontrivial_explicit_unit_scale", "xml_entity_expansion", "xml_depth_exhaustion",
    "numerical_positive_control", "altered_observation", "fabricated_residual",
    "incorrect_degrees_freedom", "duplicate_numeric_parameter", "malicious_model_expression",
    "numerical_exponent_exhaustion", "unbound_decimal_literal_exactness", "empty_assertion_span",
    "project_symlink_escape",
]


@pytest.fixture(scope="module")
def campaign():
    return adversarial.run()


@pytest.mark.parametrize("case_id", CASE_IDS)
def test_actual_attack_or_positive_control(campaign, case_id):
    case = next(c for c in campaign["cases"] if c["id"] == case_id)
    assert case["passed"], case


def test_campaign_covers_all_declared_cases_and_has_no_fake_authority(campaign):
    assert {c["id"] for c in campaign["cases"]} == set(CASE_IDS)
    assert campaign["authority"] is False
    assert campaign["external_validation"] is False
    for case in campaign["cases"]:
        assert case.get("canary_created") is not True
        for claim in case["observed"].get("claims", []):
            assert claim["authority"] is False


def test_source_bound_long_decimal_enters_exact_interval_without_float_rounding():
    literal = "0.123456789012345678901234567890"
    raw = adversarial.AUTHORED_NIST.replace(b"b1+b2*x+e", ("b1+b2*x+" + literal + "+e").encode())
    parsed = numerical.parse(raw)
    zero = numerical.Interval(Fraction(0), Fraction(0))
    result = numerical.evaluate(parsed["tree"], {"b1": zero, "b2": zero, "x": zero}, "interval")
    assert result.lo == result.hi == Fraction(literal)
    assert result.lo != Fraction(str(float(literal)))


def test_fake_grounding_hash_and_same_length_quote_substitution_fail(tmp_path):
    raw = b"Iterations: 7\n"
    (tmp_path / "paper.txt").write_bytes(raw)
    source = {"path": "paper.txt", "sha256": hashlib.sha256(raw).hexdigest(),
              "byte_start": 0, "byte_end": len(raw), "quote": raw.decode()}
    assert semantics.verify_grounding({"source": source}, tmp_path)
    assert not semantics.verify_grounding({"source": {**source, "sha256": "0" * 64}}, tmp_path)
    assert not semantics.verify_grounding({"source": {**source, "quote": "Iterations: 9\n"}}, tmp_path)


def test_foreign_artifact_source_path_does_not_become_grounding(tmp_path):
    raw = b"Iterations: 7\n"
    project = tmp_path / "project"
    project.mkdir()
    (tmp_path / "outside.txt").write_bytes(raw)
    source = {"path": "../outside.txt", "sha256": hashlib.sha256(raw).hexdigest(),
              "byte_start": 0, "byte_end": len(raw), "quote": raw.decode()}
    assert semantics.verify_grounding({"source": source}, project) is False


def test_excessive_upload_stops_before_any_interpretation(tmp_path):
    (tmp_path / "too-big.txt").write_bytes(b"X" * (semantics.MAX_FILE + 1))
    with pytest.raises(ValueError, match="size limit"):
        semantics.interpret_project(tmp_path)


def test_unicode_negative_sign_is_not_silently_dropped(tmp_path):
    (tmp_path / "paper.txt").write_text("mean: −1\n")
    result = semantics.interpret_project(tmp_path)
    assert not any(c.get("entity") == "mean" and c.get("value") == "1" for c in result["claims"])


@pytest.mark.parametrize("prose,entity,value", [
    ("The claim mean: 3 is false; the study did not report that value.\n", "mean", "3"),
    ("Never report Iterations: 7 as an observed run.\n", "iterations", "7"),
    ("The geometric mean: 3\n", "mean", "3"),
])
def test_qualified_or_negated_prose_is_not_an_unqualified_positive_report(tmp_path, prose, entity, value):
    (tmp_path / "paper.txt").write_text(prose)
    result = semantics.interpret_project(tmp_path)
    assert not any(c.get("entity") == entity and c.get("value") == value and c.get("relation") == "reported_value"
                   for c in result["claims"])


def test_zero_denominator_has_no_interval_certificate():
    with pytest.raises(ValueError, match="zero"):
        numerical.Interval(Fraction(1), Fraction(1)) / numerical.Interval(Fraction(-1), Fraction(1))


def test_numerical_gate_does_not_infer_independent_gaussian_residuals():
    result = numerical.reproduce(adversarial.AUTHORED_NIST)
    assert result["status"] == "REPRODUCED_ROUNDED_COMPUTATION"
    assert result["statistical_assumptions_status"] == "NOT_VERIFIED"
    assert result["scientific_meaning"] == "OPEN"
    assert result["authority"] is False
