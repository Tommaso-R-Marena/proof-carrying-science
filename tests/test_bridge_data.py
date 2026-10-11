"""Independently recheck human-session mathematics; fixtures are test data."""
import copy
import json
from pathlib import Path
import pytest
from pcs.experimental.prover.bridge_data import intake
from pcs.experimental.prover.bridge_catalog import build
from pcs.experimental.prover.environment import LeanEnvironment
from pcs.experimental.prover.induction_language import formalize
from pcs.experimental.prover.data import structural_fingerprint
from pcs.experimental.prover.induction_ir import canonical_declaration

def test_outer_quantifier_grouping_cannot_bypass_holdout_firewall():
    goal=formalize("For all functions from natural numbers to natural numbers f and g, (∀ (n : Nat), f(n) equals g(n)).")["candidates"][0]["ir"]
    assert structural_fingerprint(goal)==structural_fingerprint(canonical_declaration(goal))

def test_independent_session_intake_and_consent_firewall(tmp_path):
    # Use the separately exported catalog when available; no website dependency
    # is mandatory for core CI. A small fixture uses real freshly checked states.
    if not __import__("shutil").which("lean"):pytest.skip("Lean unavailable")
    from pcs.experimental.prover.environment import act
    from pcs.experimental.prover.induction_ir import digest
    from pcs.experimental.prover.bridge_catalog import compact, VERSION
    goal=formalize("For all propositions P, if P then P.")["candidates"][0]["ir"]
    actions=[act("intro","h0"),act("intro","h1"),act("exact","h1")]
    env=LeanEnvironment(cache=tmp_path/"source",timeout=30)
    nodes={}
    try:
        for i in range(len(actions)+1):
            path=actions[:i];state=env.observe(goal,path)["states"][-1];key=digest(path)[:24]
            nodes[key]={"path":path,"state":compact(state),"state_sha256":digest(state),"edges":[]}
            if i<len(actions):nodes[key]["edges"]=[{"action":actions[i],"status":"closed" if i+1==len(actions) else "open","next":digest(actions[:i+1])[:24]}]
        receipt=env.verify(goal,actions)
    finally:env.close()
    catalog={"version":VERSION,"core_revision":"test-fixture-not-participant-data","missions":[{"id":"fixture","goal":goal,"statement":"For all propositions P, if P then P.","start":digest([])[:24],"nodes":nodes,"automatic_setup_actions":[]}]}
    catalog["content_sha256"]=digest(catalog)
    session={"format":"pcs-bridge-session-v1","version":VERSION,"catalog_sha256":catalog["content_sha256"],"mission_id":"fixture","events":[{"kind":"choose","node":digest(actions[:i])[:24],"edge":0,"sequence":i} for i in range(3)]}
    export={"format":"pcs-bridge-consented-export-v1","version":VERSION,"entries":[{"id":"test-only","session":session,"license":"CC0-1.0","adult_consented":True,"training_consented":True}]}
    result=intake(catalog,export,cache=tmp_path/"independent")
    assert len(result["verified_training_examples"])==1
    assert result["verified_training_examples"][0]["result"]["receipt"]["goal_sha256"]==digest(goal)
    assert result["automatic_training_authorization"] is False
    with pytest.raises(ValueError,match="contamination"):intake(catalog,export,heldout=[{"goal":goal}],cache=tmp_path/"holdout")
    forged=copy.deepcopy(export);forged["entries"][0]["training_consented"]=False
    with pytest.raises(ValueError,match="provenance"):intake(catalog,forged,cache=tmp_path/"consent")
