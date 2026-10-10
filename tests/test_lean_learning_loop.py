"""Independent fidelity, real Lean execution and adversarial boundary checks."""
import copy
import json
import os
import shutil

import pytest

from pcs.experimental.prover.ir import declaration, binary, var, theorem, digest
from pcs.experimental.prover.language import formalize, parse_lean, explain
from pcs.experimental.prover.environment import LeanEnvironment, act, render_action, search
from pcs.experimental.prover.data import structural_fingerprint, replay_receipt, intake_feedback, claim_graph


def identity(name="P"):
    return declaration([name], binary("implies", var(name), var(name)))


@pytest.fixture
def lean(tmp_path):
    if not shutil.which("lean"):
        if os.environ.get("PCS_REQUIRE_PROVER") == "1": pytest.fail("required Lean unavailable")
        pytest.skip("Lean unavailable; required prover CI runs this test")
    env = LeanEnvironment(cache=tmp_path / "lean", timeout=30)
    try: yield env
    finally: env.close()


@pytest.mark.parametrize("english,domain,op", [
    ("For all propositions A, A implies A.", "Prop", "implies"),
    ("For all propositions X and Y, if X then Y.", "Prop", "implies"),
    ("For all natural numbers k, k + 0 equals k.", "Nat", "eq"),
    ("For all integers z, z equals z.", "Int", "eq"),
])
def test_independent_english_typing_and_roundtrip(english, domain, op):
    result = formalize(english)
    assert result["status"] == "supported"
    c = result["candidates"][0]
    assert c["ir"]["binders"][0]["type"] == domain
    assert c["ir"]["body"]["op"] == op
    assert parse_lean(c["lean"]) == c["ir"]
    explanation = explain(c["ir"])
    assert explanation["variables"] == c["ir"]["binders"]
    assert explanation["source_correspondence"]["lean"] == c["lean"]


def test_ambiguity_and_scope_are_explicit():
    a = formalize("For all propositions A, B and C, A and B or C.")
    assert a["status"] == "ambiguous" and len(a["candidates"]) == 2
    b = formalize("For all propositions A, B and C, if A and B or C then A.")
    assert b["status"] == "ambiguous"
    assert formalize("Every connected finite graph has a spanning tree.")["status"] == "unsupported"
    assert formalize("For all real numbers x, x equals x.")["status"] == "unsupported"
    assert formalize("For all natural numbers n, n equals P.")["status"] == "unsupported"
    assert formalize("For all propositions P and P, P.")["status"] == "unsupported"


@pytest.mark.parametrize("source", ["theorem x : False := by sorry", "axiom evil : False", "∀ (n : Nat), (n ∧ n)",
                                   "∀ (P : Prop), ∀ (P : Prop), P", "∀ (x : Real), x = x"])
def test_injection_untyped_and_shadowing_rejected(source):
    with pytest.raises(ValueError): parse_lean(source)


def test_quantifier_order_negation_implication_domain():
    a = parse_lean("∀ (n : Nat), ∃ (m : Nat), n = m")
    b = parse_lean("∃ (m : Nat), ∀ (n : Nat), n = m")
    assert structural_fingerprint(a) != structural_fingerprint(b)
    assert structural_fingerprint(identity("P")) == structural_fingerprint(identity("X"))
    p = formalize("For all propositions P and Q, if P then Q.")["candidates"][0]["ir"]
    q = formalize("For all propositions P and Q, if Q then P.")["candidates"][0]["ir"]
    assert digest(p) != digest(q)
    assert parse_lean("∀ (P : Prop), ¬ P")["body"]["op"] == "not"
    with pytest.raises(ValueError): parse_lean("∀ (n : Nat) (z : Int), n = z")


@pytest.mark.parametrize("action", [
    {"kind": "exact", "argument": "sorry"}, {"kind": "shell", "argument": "rm"},
    {"kind": "exact", "argument": "h; axiom bad : False"}, {"kind": "simp", "argument": "native_decide"},
    {"kind": "lemma", "argument": []}, {"kind": "intro", "argument": "h0\naxiom"},
    {"kind": "rfl", "argument": None, "reward": 1},
])
def test_untrusted_action_rejection(action):
    with pytest.raises(ValueError): render_action(action)


def test_actual_multistep_states_and_fresh_kernel(lean):
    goal = formalize("For all propositions A and B, if (A and B) then (B and A).")["candidates"][0]["ir"]
    result = search(lean, goal, budget=96, beam=4)
    assert result["status"] == "verified"
    assert len(result["receipt"]["actions"]) >= 6
    assert any(len(s["goals"]) == 2 for s in result["states"])
    assert result["states"][-1]["goals"] == []
    assert result["receipt"]["kernel"]["axioms"] == []
    fresh = replay_receipt(lean, goal, result["receipt"])
    assert fresh["goal_sha256"] == digest(goal)
    bad = copy.deepcopy(fresh); bad["goal_sha256"] = "0" * 64
    with pytest.raises(ValueError): replay_receipt(lean, goal, bad)
    bad = copy.deepcopy(fresh); bad["actions"] = []
    with pytest.raises(RuntimeError): replay_receipt(lean, goal, bad)


def test_environment_rewards_and_goal_tampering(lean):
    state, _ = lean.reset(identity())
    state, reward, done, _, _ = lean.step(act("intro", "h0"))
    assert not done and reward < 1
    state, reward, done, _, _ = lean.step(act("intro", "h1"))
    assert not done and reward < 1
    state, reward, done, _, info = lean.step(act("assumption"))
    assert done and reward == 1 and info["receipt"]["kernel"]["axioms"] == []
    with pytest.raises(ValueError): lean.step(act("assumption"))
    lean.reset(identity()); lean._goal["body"] = {"op": "false"}
    with pytest.raises(RuntimeError): lean.step(act("assumption"))


def test_false_goals_and_policy_cannot_authorize(lean):
    false = declaration([], {"op": "false"})
    r = search(lean, false, rank=lambda s, a: [1.] * len(a), budget=8, beam=4)
    assert r["status"] == "unknown" and r["receipt"] is None
    with pytest.raises(ValueError): search(lean, identity(), rank=lambda s, a: [float("nan")] * len(a))
    with pytest.raises(RuntimeError): lean.verify(false, [act("assumption")])


def test_feedback_holdout_firewall_and_existing_claim_graph(lean):
    goal = identity()
    r = search(lean, goal, budget=48, beam=4)
    feedback = {"goal": goal, "receipt": r["receipt"], "original_statement": "Authored identity", "hint_exposure": "symbolic"}
    with pytest.raises(ValueError):
        intake_feedback(lean, feedback, [{"goal": identity("X")}], license="Apache-2.0", source_revision="test")
    accepted = intake_feedback(lean, feedback, [], license="Apache-2.0", source_revision="test")
    assert accepted["split"] == "train"
    graph = claim_graph(feedback["original_statement"], goal, r["receipt"])
    assert graph["pcs_authority"] is False
    assert graph["obligation_graph"]["summary"]["blocking_obligations"] >= 2


def test_actual_graph_training_and_sequential_updates(lean, tmp_path):
    if os.environ.get("PCS_REQUIRE_PROVER") == "1":
        import importlib.util
        assert importlib.util.find_spec("torch"), "required PyTorch unavailable"
    torch = pytest.importorskip("torch")
    from pcs.experimental.prover.model import ReasoningNetwork, imitate, actor_critic
    goal = identity()
    record = {"goal": goal, "split": "train", "result": search(lean, goal, budget=48, beam=4)}
    torch.manual_seed(7)
    m = ReasoningNetwork()
    report = imitate(m, [record], epochs=2)
    assert "message.weight" in report["changed_parameters"]
    assert "update.weight" in report["changed_parameters"]
    rl = actor_critic(m, lean, [record], episodes=4)
    assert rl["weights_changed"]
    assert any(len(e["steps"]) >= 2 for e in rl["episodes"])
    p = tmp_path / "weights.json"; sha = m.save(p, {})
    loaded = ReasoningNetwork.load(p, sha)
    assert all(torch.equal(v, loaded.state_dict()[k]) for k, v in m.state_dict().items())
    p.write_text("{}");
    with pytest.raises(ValueError): ReasoningNetwork.load(p, sha)
    with pytest.raises(ValueError): actor_critic(m, lean, [{**record, "split": "final"}], episodes=1)


def test_bounded_research_dependencies(lean):
    from pcs.experimental.prover.research import investigate
    plan = {"format": "pcs-research-plan-v1", "nodes": [
        {"id": "A", "goal": identity(), "depends_on": []},
        {"id": "B", "goal": identity("Q"), "depends_on": ["A"]},
        {"id": "C", "goal": identity("R"), "depends_on": ["A", "B"]}]}
    result = investigate(lean, plan)
    assert result["execution_order"] == ["A", "B", "C"] and result["verified_results"] == 3
    plan["nodes"][0]["goal"] = declaration([], {"op": "false"})
    result = investigate(lean, plan, budget=8)
    assert result["results"]["C"]["status"] == "blocked_dependency"
    plan["nodes"][0]["depends_on"] = ["C"]
    with pytest.raises(ValueError): investigate(lean, plan)


def test_real_formalization_encoder_updates_and_integrity(tmp_path):
    pytest.importorskip("torch")
    from pcs.experimental.prover.formalization_model import train, FormalizationRanker
    path = tmp_path / "formalization.json"
    model, report = train(path, epochs=2)
    assert report["weights_changed"] and report["examples"] == 75
    loaded = FormalizationRanker.load(path, report["checkpoint_sha256"])
    assert loaded.rank("For every natural number k, k = k.", declaration(["k"], binary("eq", var("k"), var("k")), "Nat")) >= 0
    path.write_text("{}");
    with pytest.raises(ValueError): FormalizationRanker.load(path, report["checkpoint_sha256"])
