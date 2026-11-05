import PCSCountermodel.Enumeration
import PCSCountermodel.Named

/-!
# Reference fixtures (kernel-checked with ordinary `decide` / `rfl`)

Mission `implication-flip`:
* left  `∀ x : Agent, P x → Q x`
* right `∀ x : Agent, Q x → P x`
* world `{n:1, P:[true], Q:[false], R:[[false]]}`

Neither formula is modified.
-/

namespace PCSCountermodel.Fixtures

open PCSCountermodel

/-- `{n:1, P:[true], Q:[false], R:[[false]]}` -/
def implicationFlipWorld : World 1 where
  P _ := true
  Q _ := false
  R _ _ := false

/-- Named AST of the left formula, field-for-field from the fixture JSON
(`forall x . imp (pred P x) (pred Q x)`). -/
def implicationFlipLeftN : NFormula :=
  .all "x" (.imp (.pred "P" "x") (.pred "Q" "x"))

/-- Named AST of the right formula (`forall x . imp (pred Q x) (pred P x)`). -/
def implicationFlipRightN : NFormula :=
  .all "x" (.imp (.pred "Q" "x") (.pred "P" "x"))

/-- Typed de Bruijn form of the left formula. -/
def implicationFlipLeft : Formula 0 := .all (.imp (.pred .P 0) (.pred .Q 0))

/-- Typed de Bruijn form of the right formula. -/
def implicationFlipRight : Formula 0 := .all (.imp (.pred .Q 0) (.pred .P 0))

/-- The lowering of the named ASTs yields exactly the typed formulas above. -/
theorem implicationFlip_lowering :
    lower [] implicationFlipLeftN = some implicationFlipLeft ∧
    lower [] implicationFlipRightN = some implicationFlipRight := ⟨rfl, rfl⟩

/-- The original implication is false in the reference world. -/
theorem implicationFlip_left_false :
    ¬ Holds implicationFlipWorld emptyEnv implicationFlipLeft := by decide

/-- Its reversal is true in the reference world. -/
theorem implicationFlip_right_true :
    Holds implicationFlipWorld emptyEnv implicationFlipRight := by decide

/-- **Positive reference counterexample.** The checker accepts the world, and therefore
(by `checker_iff`) the two statements genuinely disagree in it. -/
theorem implicationFlip_checker_accepts :
    checker implicationFlipWorld implicationFlipLeft implicationFlipRight = true := by decide

theorem implicationFlip_counterexample :
    ¬ (Holds implicationFlipWorld emptyEnv implicationFlipLeft ↔
       Holds implicationFlipWorld emptyEnv implicationFlipRight) :=
  (checker_iff _ _ _).mp implicationFlip_checker_accepts

/-- The same verdict through the named-syntax lowering, for every valuation. -/
theorem implicationFlip_named_counterexample (ρ : String → Fin 1) :
    ¬ (NHolds implicationFlipWorld ρ implicationFlipLeftN ↔
       NHolds implicationFlipWorld ρ implicationFlipRightN) :=
  (namedChecker_sound implicationFlipWorld (c := true) (by decide) ρ).mp rfl

/-- Bounded search on the fixture returns a size-1 world (hence minimal). -/
theorem implicationFlip_search_size :
    (search implicationFlipLeft implicationFlipRight).map Sigma.fst = some 1 := by decide

/-! ### Binding / shadowing / capture examples -/

/-- Shadowing: in `∀x. ∀x. P x` the occurrence resolves to the innermost binder. -/
theorem shadowing_innermost :
    lower [] (.all "x" (.all "x" (.pred "P" "x"))) = some (.all (.all (.pred .P 0))) := rfl

/-- `∀x. ∃y. R x y` lowers to `∀ ∃ R 1 0`. -/
theorem capture_free_lowering :
    lower [] (.all "x" (.ex "y" (.rel "x" "y"))) = some (.all (.ex (.rel 1 0))) := rfl

/-- Capturing variant `∀x. ∃x. R x x` lowers to `∀ ∃ R 0 0` (the inner binder captures). -/
theorem captured_lowering :
    lower [] (.all "x" (.ex "x" (.rel "x" "x"))) = some (.all (.ex (.rel 0 0))) := rfl

/-- The capture is semantically visible: bounded search finds a 2-element disagreement and no
1-element one. -/
theorem capture_search_size :
    (search (.all (.ex (.rel 1 0))) (.all (.ex (.rel 0 0)))).map Sigma.fst = some 2 := by
  decide

/-- Unbound variables are rejected. -/
theorem unbound_rejected : lower [] (.pred "P" "x") = none := rfl

/-- A variable bound only in a sibling scope is rejected: `(∀x. P x) ∧ Q x`. -/
theorem out_of_scope_rejected :
    lower [] (.and (.all "x" (.pred "P" "x")) (.pred "Q" "x")) = none := rfl

end PCSCountermodel.Fixtures
