from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from pcs.canonical_json import canonicalize_jcs_bytes
from pcs.jsonio import strict_json_load
from pcs.scientific_contracts_v1 import (evaluate, simulate, trajectory_csv,
    validate_contract, ScientificContractError, ScientificResourceLimit)
from pcs.scientific_obligations_v1 import (make_plan, resolve_plan, topological_order,
    new_review_revision, unsupported_claim_diagnostics, ScientificObligationError)

EXAMPLE = Path(__file__).resolve().parents[1] / "examples/scientific_mass_action/model.json"


def _model():
    return strict_json_load(EXAMPLE)


def _report(model):
    return evaluate(canonicalize_jcs_bytes(model), trajectory_csv(model))


def test_exact_branched_reaction_replay_has_eight_genuine_predicates():
    model = _model()
    checked = _report(model)
    assert checked["outcome"] == "PASS"
    assert len(checked["checks"]) == 8
    assert checked["resources"]["reaction_step_evaluations"] == 24
    assert checked["clinical_or_biological_acceptance"] is False
    assert checked["pcs_authority"] is False
    assert simulate(model)[-1][1]["isomer"] > 0


def test_mass_preserving_corruption_still_fails_reference_computation():
    model = _model()
    rows = trajectory_csv(model).decode().splitlines()
    cells = rows[-1].split(",")
    from fractions import Fraction
    cells[2] = str(Fraction(cells[2]) + Fraction(1, 1000))
    cells[3] = str(Fraction(cells[3]) - Fraction(1, 1000))
    rows[-1] = ",".join(cells)
    checked = evaluate(canonicalize_jcs_bytes(model), ("\n".join(rows) + "\n").encode())
    outcomes = {item["id"]: item for item in checked["checks"]}
    assert outcomes["element_conservation"]["outcome"] == "PASS"
    assert outcomes["reference_match"]["outcome"] == "FAIL"
    assert outcomes["reference_match"]["witness"]["row"] == 12
    assert checked["outcome"] == "FAIL"


def test_leaked_mass_counterexample_and_failed_prerequisite_block_aggregate():
    model = _model()
    rows = trajectory_csv(model).decode().splitlines()
    cells = rows[-1].split(",")
    cells[1] = "100"
    rows[-1] = ",".join(cells)
    raw = canonicalize_jcs_bytes(model)
    checked = evaluate(raw, ("\n".join(rows) + "\n").encode())
    import hashlib
    plan = make_plan(model, contract_artifact_sha256=hashlib.sha256(raw).hexdigest())
    resolved = resolve_plan(plan, checked)
    statuses = {x["id"]: x["status"] for x in resolved["nodes"]}
    assert statuses["element_conservation"] == "FAILED"
    assert statuses["workflow"] == "BLOCKED"
    assert statuses["biological_adequacy"] == "BLOCKED"
    assert resolved["scientific_acceptance"] is False


def test_wrong_time_grid_blocks_dependent_reference_even_when_cells_match():
    model = _model()
    raw = canonicalize_jcs_bytes(model)
    observations = trajectory_csv(model).decode().replace("1/4,", "1/3,", 1).encode()
    checked = evaluate(raw, observations)
    plan = make_plan(model, contract_artifact_sha256=checked["contract_sha256"])
    statuses = {x["id"]: x["status"] for x in resolve_plan(plan, checked)["nodes"]}
    assert statuses["time_grid"] == "FAILED"
    assert statuses["reference_match"] == "BLOCKED"


@pytest.mark.parametrize("mutation", [
    lambda x: x.update(steps=True),
    lambda x: x.update(steps=129),
    lambda x: x.update(initial={"glucose": -1, "lactate": "0", "isomer": "0"}),
    lambda x: x.update(assumptions=[]),
    lambda x: x.update(time_step="NaN"),
    lambda x: x.update(absolute_tolerance="-1"),
    lambda x: x["species"][0].update(formula="Ca(OH)2"),
    lambda x: x["species"][0].update(formula="H0"),
    lambda x: x["reactions"][0]["reactants"][0].update(coefficient=True),
    lambda x: x["reactions"][0].update(rate_unit="s^9999999"),
    lambda x: x["reactions"][0].update(rate_constant="-1"),
    lambda x: x.update(concentration_unit="mM"),
    lambda x: x.update(unknown_semantics=True),
])
def test_unsupported_contracts_remain_open_with_actionable_diagnostics(mutation):
    model = _model()
    mutation(model)
    checked = evaluate(canonicalize_jcs_bytes(model), b"time_s,glucose,lactate,isomer\n")
    assert checked["outcome"] == "OPEN"
    assert checked["checks"] == []
    assert checked["diagnostics"][0]["suggestions_are_verified"] is False


def test_parameter_domain_valid_but_negative_numerical_euler_is_falsified():
    model = _model()
    model["reactions"][0]["rate_constant"] = "100"
    checked = _report(model)
    assert checked["outcome"] == "FAIL"
    nonnegative = next(x for x in checked["checks"] if x["id"] == "nonnegative")
    assert nonnegative["outcome"] == "FAIL"
    assert nonnegative["witness"]["row"] == 1


def test_dimension_mismatch_is_genuine_failed_obligation():
    model = _model()
    model["reactions"][0]["rate_unit"] = "mol/L"
    checked = _report(model)
    assert checked["outcome"] == "FAIL"
    assert next(x for x in checked["checks"] if x["id"] == "dimensions_cleavage")["outcome"] == "FAIL"


def test_stoichiometric_error_is_genuine_failed_obligation():
    model = _model()
    model["reactions"][0]["products"][0]["coefficient"] = 1
    checked = _report(model)
    assert checked["outcome"] == "FAIL"
    balance = next(x for x in checked["checks"] if x["id"] == "balance_cleavage")
    assert balance["witness"]["delta_product_minus_reactant"] == {"C": -3, "H": -6, "O": -3}


def test_rational_explosion_is_exhaustion_not_a_value_or_pass():
    model = _model()
    model["reactions"][0]["reactants"][0]["coefficient"] = 8
    model["reactions"][0]["products"][0]["coefficient"] = 8
    model["reactions"][0]["rate_constant"] = "10"
    model["reactions"][0]["rate_unit"] = "mol^-7*m^21*s^-1"
    model["steps"] = 20
    with pytest.raises(ScientificResourceLimit):
        simulate(model)
    rows = b"time_s,glucose,lactate,isomer\n" + b"0,1,0,0\n" * 21
    checked = evaluate(canonicalize_jcs_bytes(model), rows)
    assert checked["outcome"] == "RESOURCE_LIMIT"
    assert checked["checks"] == []


def test_premise_revision_invalidates_transitive_evidence_and_retains_original():
    model = _model()
    checked = _report(model)
    plan = make_plan(model, contract_artifact_sha256=checked["contract_sha256"])
    original = resolve_plan(plan, checked)
    amended = deepcopy(plan)
    amended["nodes"][0]["statement"] = "The compartment is not closed."
    changed = resolve_plan(amended, checked, previous=original)
    statuses = {x["id"]: x for x in changed["nodes"]}
    assert statuses[plan["nodes"][0]["id"]]["assumption_change"] is True
    assert statuses["workflow"]["status"] == "INVALIDATED"
    assert next(x for x in original["nodes"] if x["id"] == "workflow")["status"] == "SATISFIED_WITHIN_SCOPE"


def test_cycles_and_missing_prerequisites_are_rejected():
    model = _model()
    checked = _report(model)
    plan = make_plan(model, contract_artifact_sha256=checked["contract_sha256"])
    plan["nodes"][0]["dependencies"] = ["workflow"]
    with pytest.raises(ScientificObligationError, match="cycle"):
        topological_order(plan)
    plan["nodes"][0]["dependencies"] = ["nonexistent"]
    with pytest.raises(ScientificObligationError, match="unknown"):
        topological_order(plan)


def test_review_revision_chain_is_immutable_unauthenticated_and_not_training_authority():
    first = new_review_revision(previous=None, evidence_sha256="a" * 64, reviewer_id="authored-test-fixture",
        decisions=[{"obligation_id": "workflow", "type": "assumptions", "message": "Check closed volume."}])
    second = new_review_revision(previous=first, evidence_sha256="a" * 64, reviewer_id="authored-test-fixture",
        decisions=[{"obligation_id": "biological_adequacy", "type": "reject", "message": "No biological validation."}], independent=True)
    assert first["revision"] == 1 and second["revision"] == 2
    assert second["previous_revision_sha256"] is not None
    assert second["independent_human_review_verified"] is False
    assert second["training_authorization"] is False
    with pytest.raises(ScientificObligationError, match="same original"):
        new_review_revision(previous=first, evidence_sha256="b" * 64, reviewer_id="fixture", decisions=second["decisions"])


def test_clinical_unbounded_ambiguous_english_remains_open_with_typed_suggestions():
    diagnostics = unsupported_claim_diagnostics("This model is always safe for every possible patient.")
    codes = {x["code"] for x in diagnostics["diagnostics"]}
    assert {"scientific_adequacy_not_supported", "unbounded_domain_not_supported", "possible_ambiguity", "missing_evidence"} <= codes
    assert diagnostics["status"] == "OPEN"
    assert diagnostics["interpretation_verified"] is False
