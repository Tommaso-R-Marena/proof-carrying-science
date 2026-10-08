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
    ("claimed_proof_receipt", lambda h,c: (c.update(proof_receipt={"verified":True}),c["formula"].update(op="exists")), "QUANTIFIER_MISMATCH"),
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

