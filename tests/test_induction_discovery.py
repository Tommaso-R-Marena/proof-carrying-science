"""Actual induction, grounding, admission and heldout guards."""
import copy
import os
import shutil
import pytest
from pcs.experimental.prover.ir import theorem, expression, digest, canonical_declaration
from pcs.experimental.prover.language import formalize, parse_lean, explain
from pcs.experimental.prover.environment import act, render_action, search
from pcs.experimental.prover.induction_environment import InductionEnvironment
from pcs.experimental.prover.induction_corpus import tasks
from pcs.experimental.prover.discovery import lift_state, propose, discover
from pcs.experimental.prover.public_job import check_actions

@pytest.fixture
def env(tmp_path):
    if not shutil.which("lean"):
        if os.environ.get("PCS_REQUIRE_PROVER")=="1": pytest.fail("required Lean missing")
        pytest.skip("Lean unavailable")
    e=InductionEnvironment(cache=tmp_path/"lean",timeout=30)
    try: yield e
    finally: e.close()

def length_goal(): return tasks()[0]["goal"]
def length_actions():
    return [act("intro","h0"),act("intro","h1"),act("induct_list","h0 h2 h3 h4"),act("normalize","list"),act("rewrite","h4"),act("normalize","list")]

def test_real_induction_retains_both_goals_and_kernel_replays(env):
    goal=length_goal(); actions=length_actions()
    induced=env.observe(goal,actions[:3]); assert induced["status"]=="open"
    state=induced["states"][-1]; assert len(state["goals"])==2
    assert any(l["name"]=="h4" and "length" in l["type"] for l in state["goals"][0]["locals"])
    assert env.observe(goal,actions[:-1])["status"]=="open"
    with pytest.raises(RuntimeError): env.verify(goal,actions[:-1])
    assert env.observe(goal,actions)["status"]=="closed"
    receipt=env.verify(goal,actions); assert receipt["goal_sha256"]==digest(goal)
    assert set(receipt["kernel"]["axioms"])<={"propext","Classical.choice","Quot.sound"}
    assert check_actions(tasks()[0]["original_statement"],actions,0)["status"]=="verified"

def test_multi_step_search_and_genuine_state_lifting(env):
    task=tasks()[0]; result=search(env,task["goal"],budget=96,beam=4)
    assert result["status"]=="verified" and any(a["kind"]=="induct_list" for a in result["receipt"]["actions"])
    state=env.observe(task["goal"],length_actions()[:4])["states"][-1]
    lifted=lift_state(state); assert lifted["body"]["op"]=="implies"
    solved=search(env,lifted,budget=96,beam=4); assert solved["status"]=="verified"
    proposals=propose([{**task,"result":result}],maximum=8)
    assert proposals and all(p["source_state_sha256"] and p["source_task"]==task["id"] for p in proposals)
    with pytest.raises(ValueError,match="training"):
        propose([{**task,"split":"final","result":result}])
    with pytest.raises(ValueError,match="firewall"):
        discover(env,[{**task,"result":result}],heldout=[task],source_revision="test")

def test_false_induction_and_forged_actions_never_certify(env):
    false=formalize("For all natural numbers n, the successor of n equals n.")["candidates"][0]["ir"]
    assert search(env,false,budget=32,beam=4)["status"]=="unknown"
    for action in [{"kind":"induct_nat","argument":"h0 h1 h1"},{"kind":"induct_list","argument":"h0 h1 h2 h3; sorry"},{"kind":"normalize","argument":"list, native_decide"}]:
        with pytest.raises(ValueError): render_action(action)
    tampered=copy.deepcopy(length_goal()); tampered["body"]["right"]={"op":"number","value":0,"type":"Nat"}
    with pytest.raises(RuntimeError): env.verify(tampered,length_actions())

def test_list_scope_types_and_explanation_roundtrip():
    for task in tasks():
        assert parse_lean(theorem(task["goal"]))==canonical_declaration(task["goal"])
        assert explain(task["goal"])["source_correspondence"]["ir_sha256"]==digest(task["goal"])
    with pytest.raises(ValueError): expression({"op":"length","arg":{"op":"number","value":1,"type":"Nat"}}, {})
    with pytest.raises(ValueError): expression({"op":"add","left":{"op":"nil"},"right":{"op":"nil"}}, {})
    assert formalize("For all lists of natural numbers xs, the length of xs equals the reversal of xs.")["status"]=="unsupported"

def test_grounded_training_changes_binding_encoder_and_saves_safe_checkpoint(env,tmp_path):
    torch=pytest.importorskip("torch")
    from pcs.experimental.prover.grounded_model import GroundedNetwork,binding_graph,train_validity
    from pcs.experimental.prover.model import imitate,actor_critic
    task=tasks()[0]; result=search(env,task["goal"],budget=96,beam=4); episode={**task,"result":result}
    state=result["states"][3]; nodes,edges=binding_graph(state)
    assert len(edges)>2*(len(nodes)-1)
    torch.manual_seed(17); m=GroundedNetwork()
    report=imitate(m,[episode],epochs=2,seed=17,candidate_provider=env.candidates)
    assert "message.weight" in report["changed_parameters"] and report["examples"]>=6
    validity=train_validity(m,[episode],epochs=1)
    assert validity["invalid_examples"]>0 and validity["validity_head_changed"]
    rl=actor_critic(m,env,[task],episodes=2,seed=19); assert rl["weights_changed"]
    checkpoint=tmp_path/"model.json"; sha=m.save(checkpoint,{"experimental":True})
    restored=GroundedNetwork.load(checkpoint,sha)
    assert restored.rank(state,env.candidates(state))==m.rank(state,env.candidates(state))
    checkpoint.write_text(checkpoint.read_text()+" ")
    with pytest.raises(ValueError,match="integrity"): GroundedNetwork.load(checkpoint,sha)
