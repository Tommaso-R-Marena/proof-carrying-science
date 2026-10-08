from __future__ import annotations

from copy import deepcopy

import pytest

from pcs.semantic_translation_v1 import (
    CANDIDATE_FORMAT, DECISION_FORMAT, INTERPRETATION_FORMAT,
    REGISTRY_FORMAT, SemanticError, attach_to_claim_ir,
    check_translation, explanation_ir, interpretation_digest, listify, sha256,
    validate_registry, compile_claim,
)

D = "0123456789abcdef" * 4
E = "abcdef0123456789" * 4


def var(name):
    return {"var": name}


def atom(symbol, *args):
    return {"op": "atom", "symbol": symbol, "args": [var(x) for x in args]}


def bind(op, name, sort, body):
    return {"op": op, "var": name, "sort": sort, "body": body}


def op(name, left, right):
    return {"op": name, "left": left, "right": right}


def fixture():
    registry = {
        "format": REGISTRY_FORMAT,
        "sorts": ["Trace", "Time"],
        "symbols": [
            {"id": "safety.revoked", "kind": "predicate", "args": ["Trace", "Time"],
             "definition_id": "PCS.Safety.revoked", "definition_sha256": D,
             "provenance": "approved formal safety predicate"},
            {"id": "safety.unsafe", "kind": "predicate", "args": ["Trace", "Time"],
             "definition_id": "PCS.Safety.unsafe", "definition_sha256": E,
             "provenance": "approved unsafe-action predicate"},
            {"id": "safety.allowed", "kind": "predicate", "args": ["Trace", "Time"],
             "definition_id": "PCS.Safety.allowed", "definition_sha256": D,
             "provenance": "approved permission predicate"},
        ],
    }
    formula = bind("forall", "t", "Trace", bind("forall", "i", "Time",
              op("implies", atom("safety.revoked", "t", "i"),
                 {"op": "not", "body": atom("safety.unsafe", "t", "i")})))
    assumptions = [bind("forall", "t", "Trace", bind("forall", "i", "Time", atom("safety.allowed", "t", "i")))]
    human = {"format": INTERPRETATION_FORMAT, "claim_id": "C_SAFE", "statement": "All actions are safe when permission is revoked.",
             "formula": formula, "assumptions": assumptions, "free_variables": [],
             "scope": {"context_id": "world.v1", "description": "Trace/time world v1"},
             "ambiguities": [], "provenance": {"origin": "human-selected interpretation"}}
    candidate = {"format": CANDIDATE_FORMAT, "claim_id": "C_SAFE", "formula": deepcopy(formula),
                 "assumptions": deepcopy(assumptions), "free_variables": [], "scope": deepcopy(human["scope"]),
                 "grounding": [{"symbol": s["id"], "definition_sha256": s["definition_sha256"]}
                               for s in registry["symbols"]], "model_confidence": 0.99}
    return registry, human, candidate


def decision(modify=None, *, confirm=True, registry_transform=None):
    reg, human, cand = fixture()
    if modify:
        modify(human, cand)
    if registry_transform:
        registry_transform(reg)
    return check_translation(reg, human, cand, approved_registry_sha256=sha256(reg),
                             confirmed_interpretation_sha256=interpretation_digest(human) if confirm else None)


def codes(out):
    return {x["code"] for x in out["diagnostics"]}


def test_valid_structure_but_never_authority():
    r = decision()
    assert r["format"] == DECISION_FORMAT
    assert r["structural_precheck_pass"] and not r["authoritative"]
    assert r["decision"] == "STRUCTURALLY_CONFORMANT_NONAUTHORITATIVE"
    assert "PYTHON_CHECKER_LEAN_REFINEMENT_NOT_VERIFIED" in r["unverified_authority_bridges"]
    assert "PCS_EXECUTABLE_AUTHORITY_NOT_INVOKED" in r["unverified_authority_bridges"]


def test_confirmation_fail_closed_and_not_in_candidate():
    r = decision(confirm=False)
    assert r["decision"] == "NEEDS_CONFIRMATION" and "CONFIRMATION_NOT_VERIFIED" in codes(r)


def test_changing_original_words_invalidates_confirmation():
    reg, human, cand = fixture()
    old = interpretation_digest(human)
    human["statement"] = "Something completely different."
    r = check_translation(reg, human, cand, approved_registry_sha256=sha256(reg),
                          confirmed_interpretation_sha256=old)
    assert "CONFIRMATION_NOT_VERIFIED" in codes(r)


def test_alpha_renamed_bound_variables_equivalent():
    def mutate(h, c):
        c["formula"] = bind("forall", "z", "Trace", bind("forall", "j", "Time",
                       op("implies", atom("safety.revoked", "z", "j"),
                          {"op": "not", "body": atom("safety.unsafe", "z", "j")})))
    assert decision(mutate)["structural_precheck_pass"]


def test_assumption_order_not_semantically_significant():
    def mutate(h, c):
        h["assumptions"].append({"op": "true"})
        c["assumptions"].insert(0, {"op": "true"})
    assert decision(mutate)["structural_precheck_pass"]


@pytest.mark.parametrize("label,modify,expected", [
    ("forall_to_exists", lambda h,c: c["formula"].update(op="exists"), "QUANTIFIER_MISMATCH"),
    ("exists_to_forall", lambda h,c: (h["formula"].update(op="exists")), "QUANTIFIER_MISMATCH"),
    ("remove_negation", lambda h,c: c["formula"]["body"]["body"].update(right=c["formula"]["body"]["body"]["right"]["body"]), "NEGATION_MISMATCH"),
    ("insert_negation", lambda h,c: c.update(formula={"op":"not","body":c["formula"]}), "NEGATION_MISMATCH"),
    ("reverse_implication", lambda h,c: c["formula"]["body"]["body"].update(left=h["formula"]["body"]["body"]["right"], right=h["formula"]["body"]["body"]["left"]), "NEGATION_MISMATCH"),
    ("drop_assumption", lambda h,c: c.update(assumptions=[]), "ASSUMPTION_DROPPED"),
    ("add_assumption", lambda h,c: c["assumptions"].append({"op":"true"}), "ASSUMPTION_ADDED"),
    ("unbound_variable", lambda h,c: c["formula"]["body"]["body"]["left"]["args"][0].update(var="missing"), "UNEXPECTED_FREE_VARIABLE"),
    ("wrong_binding", lambda h,c: c["formula"]["body"]["body"]["left"]["args"][1].update(var="t"), "BINDING_MISMATCH"),
    ("unknown_predicate", lambda h,c: c["formula"]["body"]["body"]["left"].update(symbol="fake.check"), "UNRESOLVED_SYMBOL"),
    ("swap_definition", lambda h,c: c["grounding"][0].update(definition_sha256=E), "UNKNOWN_DEFINITION"),
    ("duplicate_grounding", lambda h,c: c["grounding"].append(deepcopy(c["grounding"][0])), "SHADOWED_OR_DUPLICATE_GROUNDING"),
    ("scope_ambiguity", lambda h,c: h["ambiguities"].append({"question":"when?"}), "AMBIGUOUS_SCOPE"),
    ("scope_changed", lambda h,c: c["scope"].update(context_id="world.v2"), "AMBIGUOUS_SCOPE"),
    ("unsupported", lambda h,c: c.update(formula={"op":"until","left":{"op":"true"},"right":{"op":"true"}}), "UNSUPPORTED_CONSTRUCT"),
    ("extra_field", lambda h,c: c["formula"].update(unknown="ignored"), "MALFORMED_CANDIDATE"),
    ("confidence_attack", lambda h,c: (c.update(model_confidence=1.0), c["formula"].update(op="exists")), "QUANTIFIER_MISMATCH"),
    ("claimed_proof_receipt", lambda h,c: (c.update(proof_receipt={"verified":True}),c["formula"].update(op="exists")), "UNVERIFIED_EXTERNAL_RECEIPT"),
    ("candidate_free_variable", lambda h,c: c.update(free_variables=[{"name":"z","sort":"Trace"}]), "BINDING_MISMATCH"),
    ("claim_binding", lambda h,c: c.update(claim_id="ANOTHER"), "CLAIM_BINDING_MISMATCH"),
    ("changed_atom", lambda h,c: c["formula"]["body"]["body"]["left"].update(symbol="safety.unsafe"), "SYMBOL_MISMATCH"),
    ("miss_grounding", lambda h,c: c["grounding"].pop(), "GROUNDING_MISMATCH"),
    ("duplicate_assumption", lambda h,c: c["assumptions"].append(deepcopy(c["assumptions"][0])), "ASSUMPTION_DUPLICATED"),
])
def test_adversarial_fails_closed(label, modify, expected):
    out = decision(modify)
    assert out["decision"] == "REJECTED", label
    assert expected in codes(out), (label,codes(out))
    assert not out["authoritative"]


def test_symbol_registry_pinned_independently():
    reg, human, cand = fixture()
    reg["symbols"][0]["definition_id"] = "PCS.Malicious.fake"
    result = check_translation(reg, human, cand, approved_registry_sha256=sha256(fixture()[0]),
                               confirmed_interpretation_sha256=interpretation_digest(human))
    assert "REGISTRY_COMMITMENT_MISMATCH" in codes(result)


def test_duplicate_registry_symbol_rejected():
    def mutate(reg):
        reg["symbols"].append(deepcopy(reg["symbols"][0]))
    assert "SHADOWED_OR_DUPLICATE_GROUNDING" in codes(decision(registry_transform=mutate))


def test_shadowed_variable_rejected():
    def mutate(h,c):
        c["formula"]["body"].update(var="t",sort="Trace")
    assert "BINDING_MISMATCH" in codes(decision(mutate))


def test_connective_and_or_change_rejected():
    def mutate(h,c):
        h["formula"]["body"]["body"]["op"] = "and"
        c["formula"]["body"]["body"]["op"] = "or"
    assert "POLARITY_MISMATCH" in codes(decision(mutate))


def test_quantifier_order_changes_binding_and_rejects():
    def mutate(h,c):
        c["formula"] = bind("forall", "i", "Time", bind("forall", "t", "Trace",
                        op("implies", atom("safety.revoked", "t", "i"),
                           {"op": "not", "body": atom("safety.unsafe", "t", "i")})))
    assert "BINDING_MISMATCH" in codes(decision(mutate))


def test_known_equality_and_inequality():
    reg,h,c=fixture()
    e={"op":"eq","left":var("x"),"right":var("x")}
    h["formula"]=bind("forall","x","Trace",e)
    c["formula"]=deepcopy(h["formula"])
    h["assumptions"]=[];c["assumptions"]=[]
    h["provenance"]={"source":"user"}
    c["grounding"]=[]
    good=check_translation(reg,h,c,approved_registry_sha256=sha256(reg),confirmed_interpretation_sha256=interpretation_digest(h))
    assert good["structural_precheck_pass"]
    c["formula"]["body"]["op"]="neq"
    bad=check_translation(reg,h,c,approved_registry_sha256=sha256(reg),confirmed_interpretation_sha256=interpretation_digest(h))
    assert "POLARITY_MISMATCH" in codes(bad)


def test_explanation_structure_preserves_normalized_semantics():
    reg,h,c=fixture()
    approved=validate_registry(reg,sha256(reg))
    compiled=compile_claim(h,approved,human=True,path="human")
    exp=explanation_ir(compiled,approved,human_digest=interpretation_digest(h))
    assert exp["conclusion"]==listify(compiled["formula"])
    assert exp["assumptions"]==[listify(x) for x in compiled["assumptions"]]
    assert "Human intent is not formally verified" in exp["limitations"]
    assert len(exp["grounding"])==3


def test_claim_ir_binding_and_non_authoritative_overlay():
    reg,h,c=fixture()
    cir={"format":"pcs-claim-ir-v1","claims":[{"claim_id":"C_SAFE","statement":h["statement"]}],
         "summary":{"claims":1}}
    cir["claim_ir_sha256"] = sha256(cir)
    good=check_translation(reg,h,c,approved_registry_sha256=sha256(reg),
                           confirmed_interpretation_sha256=interpretation_digest(h),claim_ir=cir)
    overlay=attach_to_claim_ir(cir,good)
    assert overlay["claim_id"]=="C_SAFE"
    assert not overlay["pcs_authority_granted"] and overlay["blocking_obligations"]
    cir["claims"][0]["statement"]="Other sentence"
    bad=check_translation(reg,h,c,approved_registry_sha256=sha256(reg),
                          confirmed_interpretation_sha256=interpretation_digest(h),claim_ir=cir)
    assert "CLAIM_BINDING_MISMATCH" in codes(bad)


def test_claim_ir_overlay_rejects_wrong_receipt_binding():
    reg,h,c=fixture()
    d=check_translation(reg,h,c,approved_registry_sha256=sha256(reg),
                        confirmed_interpretation_sha256=interpretation_digest(h))
    with pytest.raises(SemanticError):
        attach_to_claim_ir({"format":"pcs-claim-ir-v1","claim_ir_sha256":D},d)


def test_wire_schema_accepts_positive_and_rejects_unknown(tmp_path):
    import json
    from pathlib import Path
    from jsonschema import Draft202012Validator
    schema = json.loads((Path(__file__).resolve().parents[1] / "pcs/schemas/semantic_translation_v1.schema.json").read_text())
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    reg, h, c = fixture()
    for x in (reg, h, c):
        assert validator.is_valid(x)
    c["formula"]["body"]["body"]["left"]["unrecognized"] = "bad"
    assert not validator.is_valid(c)


def test_strict_json_loader_rejects_duplicate_and_nan(tmp_path):
    from scripts.run_semantic_translation_v1 import read_json
    p = tmp_path / "test.json"
    p.write_text('{"a": 1, "a": 2}')
    with pytest.raises(ValueError, match="duplicate"):
        read_json(p)
    p.write_text('{"a": NaN}')
    with pytest.raises(ValueError, match="nonstandard"):
        read_json(p)


def test_cli_end_to_end_positive_and_negative(tmp_path):
    from scripts.run_semantic_translation_v1 import main
    import json
    reg,h,c=fixture()
    args=[]
    for name,val in (("registry",reg),( "interpretation",h),("candidate",c)):
        file=tmp_path/(name+".json")
        file.write_text(json.dumps(val))
        args += ["--"+name, str(file)]
    args += ["--approved-registry-sha256",sha256(reg),
             "--confirmed-interpretation-sha256",interpretation_digest(h)]
    out=tmp_path/"decision.json"
    assert main(args+["--output",str(out)])==0
    assert json.loads(out.read_text())["decision"]=="STRUCTURALLY_CONFORMANT_NONAUTHORITATIVE"
    c["formula"]["op"]="exists"
    (tmp_path/"candidate.json").write_text(json.dumps(c))
    assert main(args+["--output",str(out)])==1
    assert "QUANTIFIER_MISMATCH" in {x["code"] for x in json.loads(out.read_text())["diagnostics"]}


@pytest.mark.parametrize("receipt", ["proof_receipt", "elaboration_receipt"])
def test_untrusted_credential_claim_alone_rejected(receipt):
    reg, human, candidate = fixture()
    candidate[receipt] = {"verified": True, "issuer": "pretend-Lean-kernel"}
    out = check_translation(reg, human, candidate, approved_registry_sha256=sha256(reg),
                            confirmed_interpretation_sha256=interpretation_digest(human))
    assert out["decision"] == "REJECTED"
    assert "UNVERIFIED_EXTERNAL_RECEIPT" in codes(out)
    assert out["authoritative"] is False


@pytest.mark.parametrize("confidence", [True, -0.1, 1.1, float("nan"), float("inf"), "1.0"])
def test_invalid_model_confidence_rejected(confidence):
    reg, human, candidate = fixture()
    candidate["model_confidence"] = confidence
    out = check_translation(reg, human, candidate, approved_registry_sha256=sha256(reg),
                            confirmed_interpretation_sha256=interpretation_digest(human))
    assert out["decision"] == "REJECTED"
    assert "MALFORMED_CANDIDATE" in codes(out)


def test_same_canonical_definition_with_two_symbols_rejected():
    reg, human, candidate = fixture()
    reg["symbols"][1]["definition_id"] = reg["symbols"][0]["definition_id"]
    out = check_translation(reg, human, candidate, approved_registry_sha256=sha256(reg),
                            confirmed_interpretation_sha256=interpretation_digest(human))
    assert "SHADOWED_OR_DUPLICATE_GROUNDING" in codes(out)


@pytest.mark.parametrize("change", [
    lambda e: e["conclusion"].__setitem__(0, "exists"),
    lambda e: e["grounding"].pop(),
    lambda e: e["assumptions"].clear(),
    lambda e: e["scope"].__setitem__(0, "other-context"),
    lambda e: e.__setitem__("limitations", []),
])
def test_structural_explanation_roundtrip_fails_closed(change):
    from pcs.semantic_translation_v1 import explanation_roundtrip_check
    reg, human, candidate = fixture()
    pinned = validate_registry(reg, sha256(reg))
    compiled = compile_claim(human, pinned, human=True, path="interpretation")
    exp = explanation_ir(compiled, pinned, human_digest=interpretation_digest(human))
    assert explanation_roundtrip_check(exp, compiled, pinned, human_digest=interpretation_digest(human))["equivalent"]
    change(exp)
    bad = explanation_roundtrip_check(exp, compiled, pinned, human_digest=interpretation_digest(human))
    assert not bad["equivalent"] and bad["authoritative"] is False
    assert bad["diagnostics"][0]["code"] == "ROUNDTRIP_MISMATCH"


def test_overlay_recomputes_existing_claim_ir_commitment_on_export():
    reg, human, candidate = fixture()
    ir = {"format": "pcs-claim-ir-v1", "claims": [{"claim_id": "C_SAFE", "statement": human["statement"]}],
          "summary": {"claims": 1}}
    ir["claim_ir_sha256"] = sha256(ir)
    out = check_translation(reg, human, candidate, approved_registry_sha256=sha256(reg),
                            confirmed_interpretation_sha256=interpretation_digest(human), claim_ir=ir)
    assert attach_to_claim_ir(ir, out)["pcs_authority_granted"] is False
    ir["summary"]["claims"] = 7
    with pytest.raises(SemanticError, match="changed since its commitment"):
        attach_to_claim_ir(ir, out)


def test_boolean_is_not_equal_to_bound_variable_index_in_explanation_roundtrip():
    from pcs.semantic_translation_v1 import explanation_roundtrip_check
    reg, human, candidate = fixture()
    pinned = validate_registry(reg, sha256(reg))
    compiled = compile_claim(human, pinned, human=True, path="interpretation")
    exp = explanation_ir(compiled, pinned, human_digest=interpretation_digest(human))
    # In Python, True == 1; structured semantic checks must not use that equality.
    exp["conclusion"][2][2][1][3][0][1] = True
    got = explanation_roundtrip_check(exp, compiled, pinned, human_digest=interpretation_digest(human))
    assert not got["equivalent"]
    assert got["diagnostics"][0]["code"] == "ROUNDTRIP_MISMATCH"
