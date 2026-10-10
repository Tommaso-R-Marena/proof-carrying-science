import PCSOmega
/-!
NEGATIVE CONTROL (outside every library and the production import graph).
Intended result: compilation FAILS because `decide` evaluates the exhaustive checker and finds the
disagreement `A = false, B = true`; implication reversal is not an equivalence.
-/
open PCSOmega
def A : BForm 2 := .atom ⟨0, by decide⟩
def B : BForm 2 := .atom ⟨1, by decide⟩
theorem false_implication_reversal : SemEquiv (.imp A B) (.imp B A) :=
  (check_none_iff _ _).1 (by decide)
