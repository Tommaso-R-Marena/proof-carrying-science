import pytest

from pcs.experimental.prover.hybrid_cli import run


def test_unsupported_input_does_not_load_a_model_or_start_lean(tmp_path):
    result = run("Solve all open mathematical problems", models=tmp_path / "absent")
    assert result["status"] == "unsupported_formalization"
    assert result["training_feedback"] is None
    assert not result["production_authority"]


def test_ambiguity_requires_explicit_interpretation_before_execution(tmp_path):
    statement = "For all propositions P, Q and R, P and Q or R."
    result = run(statement, models=tmp_path / "absent")
    assert result["status"] == "ambiguous_interpretation"
    assert len(result["formalization"]["candidates"]) == 2
    assert result["training_feedback"] is None
    with pytest.raises(ValueError, match="interpretation"):
        run(statement, models=tmp_path / "absent", interpretation=9)


@pytest.mark.parametrize("budget", [True, 0, 5, 97, "48"])
def test_untrusted_resource_parameter_rejected_before_execution(budget):
    with pytest.raises(ValueError, match="budget"):
        run("For all natural numbers n, (n + 0) equals n.", budget=budget)
