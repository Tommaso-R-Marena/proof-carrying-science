from pcs.formal_coverage_v06 import (
    CERTIFIED_BUILTIN_CHECK_TYPES_V06,
    classify_formal_coverage_v06,
)


def test_formal_coverage_separates_checker_theorem_scope_from_execution_authority():
    certificate = {
        "evidence": [
            {"id": "E1", "check_spec": {"type": "reaction_balance"}},
            {"id": "E2", "check_spec": {"type": "external_formal_proof"}},
        ]
    }

    before_authority = classify_formal_coverage_v06(certificate)
    assert before_authority["checker_classification_scope"] == "CHECK_TYPE_ONLY"
    assert before_authority["execution_authority_scope"] == "EXACT_PACKAGE_VERIFICATION"
    assert before_authority["package_authority"] == "LEAN_AUTHORITY_NOT_ESTABLISHED"
    assert before_authority["certified_type_evidence"] == 1
    assert before_authority["outside_certified_type_evidence"] == 1
    assert before_authority["evidence"][0] == {
        "evidence_id": "E1",
        "check_type": "reaction_balance",
        "checker_semantics": "PROVED_IN_LEAN_FOR_THIS_CHECK_TYPE",
        "execution_authority": "CHECKER_TYPE_PROVED_PACKAGE_NOT_LEAN_ACCEPTED",
    }
    assert before_authority["evidence"][1] == {
        "evidence_id": "E2",
        "check_type": "external_formal_proof",
        "checker_semantics": "NOT_IN_CERTIFIED_BUILTIN_SET",
        "execution_authority": "OUTSIDE_CERTIFIED_BUILTIN_SET",
    }

    accepted = classify_formal_coverage_v06(
        certificate,
        package_authoritative=True,
        lean_authority={"accepted": True, "verdict": "ACCEPT"},
    )
    assert accepted["package_authority"] == "LEAN_AUTHORITATIVE_ACCEPT"
    assert (
        accepted["evidence"][0]["execution_authority"]
        == "AUTHORITATIVELY_REPLAYED_BY_LEAN"
    )
    assert (
        accepted["evidence"][1]["execution_authority"]
        == "OUTSIDE_CERTIFIED_BUILTIN_SET"
    )


def test_certified_builtin_type_set_is_exactly_the_formal_frontier_set():
    assert CERTIFIED_BUILTIN_CHECK_TYPES_V06 == {
        "reaction_balance",
        "unit_compatible",
        "csv_disjoint",
        "pkpd_contract",
        "pkpd_reference_match",
        "pkpd_peak_concentration_threshold",
    }
