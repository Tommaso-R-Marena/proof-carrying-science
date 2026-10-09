"""Adversarial boundaries and real learning/replay checks for PCS Omega."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from pcs.experimental.omega import cli
from pcs.experimental.omega.corpus import generate, validate_corpus
from pcs.experimental.omega.learning import features, train, validate_model
from pcs.experimental.omega.logic import actions, apply_action, check, digest, lean_source, verify_receipt
from pcs.experimental.omega.project import compile_project, invalidate, validate_project
from pcs.experimental.omega.search import ReasoningEnv, memory, search, train_bandit, verify_episode


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def corpus():
    return generate(per_family=2)


@pytest.fixture
def project():
    return json.loads((ROOT / "examples/omega/project.json").read_text())


def rehash(value, field):
    value[field] = digest({k: v for k, v in value.items() if k != field})
    return value


def test_independent_checker_counterexample_is_recomputed(project):
    value = project["claims"][0]["task"]
    receipt = check(value)
    assert receipt["assignments_checked"] == 4
    assert receipt["counterexample"] == {"assignment": {"P": False, "Q": True}, "source_true": False, "candidate_true": True}
    forged = {**receipt, "equivalent": True, "counterexample": None}
    with pytest.raises(ValueError):
        verify_receipt(value, forged)
    forged = deepcopy(receipt)
    forged["truth_pairs"][0][0] = 0  # Python equality alone confuses 0 and False.
    with pytest.raises(ValueError):
        verify_receipt(value, forged)


@pytest.mark.parametrize("mutation", ["code", "unit", "symbol", "depth", "variables", "extra"])
def test_unsupported_interpretations_fail_closed(project, mutation):
    value = project["claims"][0]["task"]
    if mutation == "code":
        value["source"] = {"op": "eval", "code": "print('not executed')"}
    elif mutation == "unit":
        value["source"]["left"]["args"] = ["meters"]
    elif mutation == "symbol":
        value["source"]["left"]["symbol"] = "UNKNOWN"
    elif mutation == "depth":
        for _ in range(10):
            value["source"] = {"op": "not", "body": value["source"]}
    elif mutation == "variables":
        value["variables"] += ["R", "S", "T"]
    else:
        value["approved"] = True
    with pytest.raises(ValueError):
        check(value)


def test_source_bound_existing_ir_remains_blocked_after_repair(project):
    before = compile_project(project)
    c = project["claims"][0]
    c["task"]["candidate"] = deepcopy(c["task"]["source"])
    after = compile_project(project)
    assert before["claim_ir"]["format"] == "pcs-claim-ir-v1"
    assert after["obligation_graph"]["format"] == "pcs-proof-obligation-graph-v1"
    assert after["receipts"]["release"]["equivalent"] is True
    assert after["claim_ir"]["claims"][0]["closure_state"] == "BLOCKED"
    assert after["pcs_authority"] is False
    assert after["source_sha256"] == hashlib.sha256(project["source"]["text"].encode()).hexdigest()
    assert before["project_sha256"] != after["project_sha256"]
    project["claims"][0]["statement"] = "An invented unsupported claim."
    with pytest.raises(ValueError):
        compile_project(project)


def test_dependencies_reopen_transitively_and_reject_cycles(project):
    c = deepcopy(project["claims"][0])
    c["id"], c["depends_on"] = "dependent", ["release"]
    project["claims"].append(c)
    assert invalidate(project, ["release"])["affected"] == ["dependent", "release"]
    project["claims"][0]["depends_on"] = ["dependent"]
    with pytest.raises(ValueError):
        validate_project(project)
    project["claims"][0]["depends_on"] = ["absent"]
    with pytest.raises(ValueError):
        validate_project(project)


@pytest.mark.parametrize("field", ["receipt", "parent", "depth", "goal", "solution", "accounting", "authority"])
def test_even_rehashed_forged_trajectories_are_rejected(project, field):
    episode = search(project["claims"][0]["task"], checks=8)
    assert verify_episode(episode)
    if field == "receipt":
        episode["attempts"][0]["receipt"]["equivalent"] = False
    elif field == "parent":
        episode["attempts"][0]["parent_sha256"] = "0" * 64
    elif field == "depth":
        episode["attempts"][0]["depth"] = True
    elif field == "goal":
        episode["original_task"]["source"] = {"op": "true"}
        episode["original_task_sha256"] = digest(episode["original_task"])
    elif field == "solution":
        episode["solution"] = None
    elif field == "accounting":
        episode["checks_used"] += 1
    else:
        episode["pcs_authority"] = True
    rehash(episode, "episode_sha256")
    with pytest.raises(ValueError):
        verify_episode(episode)


def test_budgets_and_unsolved_states_never_promote(project):
    value = project["claims"][0]["task"]
    for limit in (1, 2, 4):
        episode = search(value, strategy="bfs", checks=limit)
        assert episode["checks_used"] <= limit
        verify_episode(episode)
    unresolved = search(value, checks=1)
    assert unresolved["solution"] is None
    assert memory([unresolved])["entries"][0]["scientific_premise_authority"] is False
    for bad in (True, 0, 129):
        with pytest.raises(ValueError):
            search(value, checks=bad)


def test_actual_training_is_deterministic_and_holdouts_do_not_change_weights(corpus):
    original = train(corpus, epochs=3)
    assert any(w != 0 for w in original["weights"])
    assert train(corpus, epochs=3) == original
    changed = deepcopy(corpus)
    record = next(r for r in changed["records"] if r["partition"] == "test")
    record["id"] += "-heldout-metadata"
    rehash(changed, "corpus_sha256")
    assert train(changed, epochs=3) == original
    assert all(f in {"connective-confusion", "negation-loss", "swapped-implication"} for f in original["training"]["families"])
    forged = deepcopy(original)
    forged["authority"] = "PCS_VERIFIED"
    rehash(forged, "model_sha256")
    with pytest.raises(ValueError):
        validate_model(forged)


def test_graph_features_have_no_checker_or_future_feedback(project, monkeypatch):
    import pcs.experimental.omega.learning as learning
    monkeypatch.setattr(learning, "check", lambda _: pytest.fail("Features accessed checker labels"))
    value = project["claims"][0]["task"]
    action = actions(value["candidate"], value["variables"])[0]
    assert len(features(value, action, "bag")) == 38
    assert len(features(value, action, "graph")) == 91


@pytest.mark.parametrize("attack", ["partition", "duplicate", "provenance", "counts"])
def test_corpus_leakage_and_provenance_rejected_after_rehash(corpus, attack):
    broken = deepcopy(corpus)
    if attack == "partition":
        broken["records"][-1]["partition"] = "train"
    elif attack == "duplicate":
        broken["records"][-1] = deepcopy(broken["records"][0])
        broken["records"][-1]["id"] = "a-new-name-cannot-hide-leakage"
    elif attack == "provenance":
        broken["records"][0]["provenance"]["personal_data"] = 0
    else:
        broken["per_family"] += 1
    rehash(broken, "corpus_sha256")
    with pytest.raises(ValueError):
        validate_corpus(broken)


def test_invalid_reward_actions_consume_budget_and_observations_are_copies(project):
    value = project["claims"][0]["task"]
    env = ReasoningEnv(value, budget=2)
    state = env.observe()
    state["task"]["source"] = {"op": "true"}
    state["receipt"]["equivalent"] = True
    assert env.observe()["task"] == value
    forged = env.step({"kind": "GRANT_REWARD", "approved": True})
    assert forged["reward"] == -0.1 and not forged["terminated"]
    bad = env.step({"kind": "REPLACE_SOURCE", "source": {"op": "true"}})
    assert bad["terminated"] and bad["reward"] < 0 and env.checks == 1
    with pytest.raises(ValueError):
        env.step({"kind": "ABSTAIN"})


def test_real_bandit_rewards_replay_through_checker(corpus):
    run = train_bandit(corpus, episodes=20)
    by_id = {r["id"]: r for r in corpus["records"]}
    for event in run["trace"]:
        value = by_id[event["task_id"]]["task"]
        candidate = apply_action(value["candidate"], event["action"], value["variables"])
        verify_receipt({**value, "candidate": candidate}, event["receipt"])
        assert (event["reward"] == 1) == event["receipt"]["equivalent"]
    assert run["training_wins"] == sum(t["reward"] == 1 for t in run["trace"])


def test_fixed_lean_template_cannot_embed_input_programs(project):
    value = project["claims"][0]["task"]
    assert "#print axioms omega_equivalence" in lean_source(value)
    value["variables"][0] = 'P); run_cmd IO.println "injection"'
    with pytest.raises(ValueError):
        lean_source(value)


def test_cli_rejects_duplicate_keys_and_byte_budget(tmp_path, capsys):
    path = tmp_path / "task.json"
    path.write_text('{"variables":[],"variables":["P"]}')
    args = SimpleNamespace(omega_command="check", input=str(path), lean_output=None, output=None)
    assert cli.command(args) == 2
    assert "duplicate JSON" in capsys.readouterr().err
    path.write_bytes(b" " * 65537)
    assert cli.command(args) == 2
    assert "byte budget" in capsys.readouterr().err


def test_modified_proof_program_is_rejected_before_execution(project, corpus, tmp_path, monkeypatch):
    import pcs.experimental.omega.experiments as experiments
    episode = search(project["claims"][0]["task"])
    for name, value in (("run.json", {}), ("trajectories.json", [episode]), ("corpus.json", corpus)):
        (tmp_path / name).write_text(json.dumps(value))
    (tmp_path / "VerifiedSolutions.lean").write_text('#eval IO.println "arbitrary submitted program"')
    (tmp_path / "RejectOriginal.lean").write_text(lean_source(corpus["records"][0]["task"]))
    monkeypatch.setattr(experiments.subprocess, "run", lambda *a, **k: pytest.fail("Submitted code executed"))
    monkeypatch.setattr(experiments.subprocess, "check_output", lambda *a, **k: pytest.fail("Execution started before proof validation"))
    with pytest.raises(ValueError, match="exact regenerated"):
        experiments.verify_lean(tmp_path)
