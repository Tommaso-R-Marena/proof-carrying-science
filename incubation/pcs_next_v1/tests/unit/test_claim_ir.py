from pcs_next_v1.translation.claim_ir import Var, exists, forall, eq, const, var_ref, expr_to_dict, alpha_eq, claim_document
from pcs_next_v1.translation.formalize import formalize_text

def test_exists_not_forall():
    v = Var("x", "Real")
    e = exists(v, eq(var_ref(v), const(0, "Real")))
    d = expr_to_dict(e)
    assert d["kind"] == "exists"
    f = formalize_text("c", "there exists x such that x > 0")
    assert f["expr"]["kind"] == "exists"

def test_alpha_eq():
    a = expr_to_dict(forall(Var("x", "Real"), eq(var_ref(Var("x", "Real")), const(1, "Real"))))
    b = expr_to_dict(forall(Var("y", "Real"), eq(var_ref(Var("y", "Real")), const(1, "Real"))))
    assert alpha_eq(a, b)

def test_approx_not_eq_pattern():
    r = formalize_text("a", "x approx y within 0.1")
    assert r["expr"]["kind"] == "approx"
