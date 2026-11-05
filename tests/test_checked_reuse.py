"""Real compiler checks for lemma admission, transfer and adversarial provenance."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import shutil

import pytest

from pcs.experimental.prover.environment import LeanEnvironment, act, search
from pcs.experimental.prover.ir import declaration, binary, var, digest
from pcs.experimental.prover.language import formalize
from pcs.experimental.prover.library import LibraryEnvironment, FORMAT, validate_library, replay_library_receipt
from pcs.experimental.prover.data import replay_receipt, intake_feedback


def swap_goal():
    return declaration(["A", "B"], binary("implies", binary("and", var("A"), var("B")), binary("and", var("B"), var("A"))))


def library():
    return {"format": FORMAT, "entries": [{"goal": swap_goal(), "actions": [act("intro", "h0"), act("intro", "h1"), act("intro", "h2"),
            act("constructor"), act("exact", "h2.2"), act("exact", "h2.1")],
            "license": "Apache-2.0", "source_revision": "4034db308d171b46c41e7e9ba2723e7fe4db6647"}]}


@pytest.fixture
def checked(tmp_path):
    if not shutil.which("lean"):
        if os.environ.get("PCS_REQUIRE_PROVER") == "1": pytest.fail("required Lean unavailable")
        pytest.skip("Lean unavailable; required prover CI runs this test")
    env = LibraryEnvironment(library(), cache=tmp_path / "lean", timeout=30)
    try: yield env
    finally: env.close()


def transfer_goal():
    return formalize("For all natural numbers a, b and c, if ((a + b equals c) and (c * 1 equals c)) then ((c * 1 equals c) and (a + b equals c)).")["candidates"][0]["ir"]


def test_actual_math_lemma_transfer_and_independent_reload(checked, tmp_path):
    goal = transfer_goal()
    actions = [act("intro", "h0"), act("intro", "h1"), act("intro", "h2"), act("apply", "PCSReuseL0")]
    observed = checked.observe(goal, actions)
    assert observed["status"] == "closed"
    assert observed["states"][0]["available_lemmas"][0]["expression"] == checked.catalog[0]["kernel"]["expression"]
    receipt = checked.verify(goal, actions)
    assert receipt["goal_sha256"] == digest(goal)
    assert receipt["library_sha256"] == digest(library())
    assert set(receipt["kernel"]["axioms"]) <= {"propext", "Classical.choice", "Quot.sound"}
    fresh = replay_library_receipt(goal, receipt, cache=tmp_path / "independent")
    assert fresh["proof"] == receipt["proof"]
    assert fresh["pcs_scientific_authority"] is False


def test_false_lemma_and_partial_proof_fail_kernel_admission(tmp_path):
    if not shutil.which("lean"): pytest.skip("Lean unavailable")
    bad = library()
    bad["entries"][0]["goal"] = declaration(["P"], var("P"))
    with pytest.raises(RuntimeError): LibraryEnvironment(bad, cache=tmp_path / "false", timeout=30)
    partial = library()
    partial["entries"][0]["actions"] = partial["entries"][0]["actions"][:-1]
    with pytest.raises(RuntimeError): LibraryEnvironment(partial, cache=tmp_path / "partial", timeout=30)


@pytest.mark.parametrize("change", ["producer_flag", "raw_source", "cycle", "forward", "injection", "unknown_license", "bool_actions"])
def test_untrusted_entry_envelope_rejected(change):
    bad = library(); e = bad["entries"][0]
    if change == "producer_flag": e["verified"] = True
    if change == "raw_source": e["source"] = "axiom evil : False"
    if change == "cycle": e["actions"] = [act("apply", "PCSReuseL0")]
    if change == "forward": e["actions"] = [act("apply", "PCSReuseL1")]
    if change == "injection": e["actions"] = [{"kind": "apply", "argument": "PCSReuseL0; sorry"}]
    if change == "unknown_license": e["license"] = "private"
    if change == "bool_actions": e["actions"] = True
    with pytest.raises(ValueError): validate_library(bad)


def test_holdout_alpha_duplicates_and_namespace_rejected():
    goal = formalize("For all propositions X and Y, if (X and Y) then (Y and X).")["candidates"][0]["ir"]
    with pytest.raises(ValueError, match="alpha"):
        validate_library(library(), [{"goal": goal}])
    bad = library(); bad["entries"].append(copy.deepcopy(bad["entries"][0]))
    with pytest.raises(ValueError, match="duplicate"): validate_library(bad)
    bad = library(); bad["entries"][0]["goal"] = declaration(["PCSReuseL0"], binary("implies", var("PCSReuseL0"), var("PCSReuseL0")))
    with pytest.raises(ValueError, match="namespace"): validate_library(bad)


def test_tampering_with_goal_library_or_replay_environment_rejected(checked, tmp_path):
    goal = transfer_goal()
    actions = [act("intro", "h0"), act("intro", "h1"), act("intro", "h2"), act("apply", "PCSReuseL0")]
    receipt = checked.verify(goal, actions)
    bad = copy.deepcopy(receipt); bad["library"]["entries"] = []
    with pytest.raises(ValueError, match="identity"): replay_library_receipt(goal, bad, cache=tmp_path / "bad")
    with pytest.raises(ValueError, match="original"): replay_library_receipt(swap_goal(), receipt)
    bad = copy.deepcopy(receipt); bad["library_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="generation"): replay_receipt(checked, goal, bad)
    bad = copy.deepcopy(receipt); bad["library_declarations"] += "axiom forged : False\n"
    with pytest.raises(ValueError, match="mismatch"): replay_library_receipt(goal, bad, cache=tmp_path / "text")


def test_admitted_library_does_not_prove_false_goal(checked):
    goal = declaration(["P", "Q"], binary("implies", var("P"), var("Q")))
    result = search(checked, goal, budget=24, beam=4)
    assert result["status"] == "unknown" and result["receipt"] is None
    with pytest.raises(RuntimeError): checked.verify(goal, [act("apply", "PCSReuseL0")])


def test_compiled_artifact_tampering_invalidates_cached_observations(checked):
    goal = transfer_goal()
    actions = [act("intro", "h0"), act("intro", "h1"), act("intro", "h2"), act("apply", "PCSReuseL0")]
    assert checked.observe(goal, actions)["status"] == "closed"
    checked._module_olean.write_bytes(b"forged compiled certificate")
    with pytest.raises(RuntimeError, match="artifact"):
        checked.observe(goal, actions)
    with pytest.raises(RuntimeError, match="artifact"):
        checked.verify(goal, actions)


def test_research_plan_really_reuses_preceding_proof(checked):
    from pcs.experimental.prover.research import investigate
    from pcs.experimental.prover.library import reuse_priority
    plan = {"format": "pcs-research-plan-v1", "nodes": [
        {"id": "generic_swap", "goal": swap_goal(), "depends_on": []},
        {"id": "arithmetic_transfer", "goal": transfer_goal(), "depends_on": ["generic_swap"]}]}
    # Empty baseline prevents accidentally borrowing the fixture's existing lemma.
    base = LeanEnvironment(cache=checked.cache, timeout=30)
    try:
        result = investigate(base, plan, reuse=True, source_revision="4034db308d171b46c41e7e9ba2723e7fe4db6647", source_license="Apache-2.0")
        assert result["verified_results"] == 2
        transfer = result["results"]["arithmetic_transfer"]
        assert transfer["available_verified_nodes"] == ["generic_swap"]
        assert any(a["argument"] == "PCSReuseL0" for a in transfer["receipt"]["actions"])
        assert result["library_construction_invocations"] >= 2
        with pytest.raises(ValueError): investigate(base, plan, reuse=True)
    finally: base.close()


@pytest.mark.parametrize("statement", [
    "For all natural numbers n, there exists a natural number m such that m equals n.",
    "For all integers z, there exists an integer w such that w equals z.",
])
def test_actual_unbounded_existential_witness(checked, statement):
    goal = formalize(statement)["candidates"][0]["ir"]
    state = checked.observe(goal, [act("intro", "h0")])["states"][-1]
    assert act("witness", "h0") in checked.candidates(state)
    receipt = checked.verify(goal, [act("intro", "h0"), act("witness", "h0"), act("rfl")])
    assert receipt["kernel"]["axioms"] == []


def test_verified_reuse_feedback_stays_behind_holdout_firewall(checked):
    goal = transfer_goal()
    receipt = checked.verify(goal, [act("intro", "h0"), act("intro", "h1"), act("intro", "h2"), act("apply", "PCSReuseL0")])
    feedback = {"goal": goal, "receipt": receipt, "original_statement": "PCS authored arithmetic relation exchange",
                "hint_exposure": "checked reusable lemma"}
    data = intake_feedback(checked, feedback, [], license="Apache-2.0", source_revision="4034db308d171b46c41e7e9ba2723e7fe4db6647")
    assert data["result"]["status"] == "verified" and data["result"]["receipt"]["library_sha256"] == checked.library_sha256
    with pytest.raises(ValueError, match="firewall"):
        intake_feedback(checked, feedback, [{"goal": goal}], license="Apache-2.0", source_revision="4034db308d171b46c41e7e9ba2723e7fe4db6647")


def test_graph_premise_parameters_update_and_safe_checkpoint(checked, tmp_path):
    if os.environ.get("PCS_REQUIRE_PROVER") == "1": assert importlib.util.find_spec("torch")
    torch = pytest.importorskip("torch")
    from pcs.experimental.prover.reuse_model import ReuseNetwork
    from pcs.experimental.prover.model import imitate
    goal = transfer_goal()
    actions = [act("intro", "h0"), act("intro", "h1"), act("intro", "h2"), act("apply", "PCSReuseL0")]
    observed = checked.observe(goal, actions)
    episode = {"goal": goal, "split": "train", "result": {"status": "verified", "receipt": checked.verify(goal, actions), "states": observed["states"]}}
    torch.manual_seed(17)
    model = ReuseNetwork()
    report = imitate(model, [episode], epochs=2, candidate_provider=checked.candidates)
    assert {"message.weight", "goal_query.weight", "premise_key.weight"} <= set(report["changed_parameters"])
    checkpoint = tmp_path / "model.json"
    sha = model.save(checkpoint, {"library_sha256": checked.library_sha256})
    loaded = ReuseNetwork.load(checkpoint, sha)
    state = observed["states"][-2]; options = checked.candidates(state)
    assert loaded.rank(state, options) == model.rank(state, options)
    with pytest.raises(ValueError): ReuseNetwork.load(checkpoint, "0" * 64)


def test_bad_policy_cannot_starve_reserved_basic_action_budget(checked):
    from pcs.experimental.prover.portfolio import search_portfolio
    goal = formalize("For all natural numbers n, there exists a natural number m such that (m equals n and m + 0 equals n).")["candidates"][0]["ir"]
    original = copy.deepcopy(goal)
    def bad_rank(state, options):
        return [20 if str(a["argument"]).startswith("PCSReuseL") else 0 for a in options]
    result = search_portfolio(checked, goal, bad_rank, budget=64)
    assert result["status"] == "verified" and result["portfolio"]["selected_stage"] == "symbolic_fallback"
    assert result["expansions"] <= 64
    assert result["receipt"]["goal_sha256"] == digest(original) and goal == original
    assert all(not str(a["argument"]).startswith("PCSReuseL") for a in result["receipt"]["actions"])
    assert len(result["portfolio"]["stages"]) == 2


@pytest.mark.parametrize("domain", ["natural numbers", "integers"])
@pytest.mark.parametrize("body", [
    "if ((a is less than or equal to b) and (b is less than or equal to c)) then (a is less than or equal to c)",
    "if ((a is less than or equal to b) and (b is less than or equal to a)) then (a equals b)",
])
def test_real_order_proofs_use_unification_and_checked_premises(checked, domain, body):
    goal = formalize(f"For all {domain} a, b and c, {body}.")["candidates"][0]["ir"]
    from pcs.experimental.prover.portfolio import _BasicActionView
    result = search(_BasicActionView(checked), goal, budget=64, beam=4)
    assert result["status"] == "verified"
    assert len(result["receipt"]["actions"]) >= 6
    assert any(a["kind"] == "lemma" and ".le_" in a["argument"] for a in result["receipt"]["actions"])
    assert result["receipt"]["goal_sha256"] == digest(goal)
    assert set(result["receipt"]["kernel"]["axioms"]) <= {"propext", "Classical.choice", "Quot.sound"}


def test_quantified_function_equalities_rewrite_through_composition(checked):
    statement = "For all functions from natural numbers to natural numbers f and g, if (∀ (a : Nat), f(a) equals g(a)) then (∀ (b : Nat), f(f(b)) equals g(g(b)))."
    goal = formalize(statement)["candidates"][0]["ir"]
    from pcs.experimental.prover.portfolio import _BasicActionView
    result = search(_BasicActionView(checked), goal, budget=64, beam=4)
    assert result["status"] == "verified"
    assert sum(a["kind"] == "rewrite" for a in result["receipt"]["actions"]) == 2


def test_metavariable_retrieval_requires_consistent_substitution():
    from pcs.experimental.prover.environment import premise_matches
    hole = {"kind": "goal", "value": "m0", "children": []}
    atom = lambda name: {"kind": "local", "value": name, "children": []}
    pair = lambda a,b: {"kind": "application", "value": "", "children": [a,b]}
    assert premise_matches(pair(hole,hole),pair(atom("a"),atom("a")))
    assert not premise_matches(pair(hole,hole),pair(atom("a"),atom("b")))
