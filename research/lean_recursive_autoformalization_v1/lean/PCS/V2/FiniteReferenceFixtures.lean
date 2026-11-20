import PCS.V2.NamedReference

/-! Kernel-reduced discriminating cases and the dependency closure of the
specific correspondence, witness, binding, and trace results. -/
namespace PCS.V2.FiniteReference.Fixtures
open PCS.V2.FiniteReference

private def p : Formula 2 := .var 0
private def q : Formula 2 := .var 1
private def top : Formula n := .truth true
private def whole (f : Formula n) : Contract n := ⟨top, f⟩

-- A one-directional weakening holds on some valuations and fails on others.
example : counterexample (whole (.conj p q)) (whole p) = some (true, false, ()) := rfl
example : counterexample (whole (.implies p q)) (whole (.implies q p)) =
    some (false, true, ()) := rfl

-- Both implications are valid, yet their contracts require different inputs.
example : falsifier (⟨p, p⟩ : Contract 2) = none := rfl
example : falsifier (⟨q, q⟩ : Contract 2) = none := rfl
example : counterexample (⟨p, p⟩ : Contract 2) ⟨q, q⟩ = some (false, true, ()) := rfl
example : counterexample (⟨p, q⟩ : Contract 2) ⟨.truth false, q⟩ =
    some (true, false, ()) := rfl

private def equalBits : Formula 2 := .conj (.implies p q) (.implies q p)
example : counterexample (whole (.every (.someVal equalBits)))
    (whole (.someVal (.every equalBits))) = some () := rfl
example : counterexample (whole (.implies p q)) (whole (.neg (.conj p (.neg q)))) =
    none := rfl
example : falsifier (whole p) = some (false, false, ()) := rfl

-- Inner binders shadow outer variables.
example : (resolve ["y"] (.every "x" (.someVal "x" (.var "x")))).map
    (fun (f : Formula 1) => eval f (false, ())) = some true := rfl
example : (resolve ["y"] (.every "x" (.someVal "z" (.var "x")))).map
    (fun (f : Formula 1) => eval f (false, ())) = some false := rfl
example : (resolve ["x"] (.var "missing")).isNone = true := rfl

#print axioms eval_iff_denote
#print axioms counterexample_none_iff
#print axioms counterexample_some_sound
#print axioms falsifier_none_iff
#print axioms falsifier_some_sound
#print axioms resolve_defined_iff
#print axioms resolve_sound
#print axioms named_counterexample_none_iff
#print axioms trace_preserves_correspondence
end PCS.V2.FiniteReference.Fixtures
