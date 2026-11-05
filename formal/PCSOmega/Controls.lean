import PCSOmega.Repair
import PCSOmega.Named

/-!
# Executed Omega controls

Ordinary kernel-checked `decide` on small finite instances, combined with the general theorems.

* implication reversal is rejected with the least distinguishing assignment;
* De Morgan is accepted by the fresh exhaustive check (hence semantically equivalent);
* a remembered counterexample rejects a candidate (hence non-equivalence);
* `screen_survivor_not_equiv`: a candidate can survive a partial witness filter and still be
  non-equivalent, so acceptance requires a fresh exhaustive check;
* `n = 0` constants;
* a search episode for an arbitrary (here: constant) ranking, its replay, and soundness;
* named lowering rejects undeclared symbols and preserves meaning.
-/

namespace PCSOmega.Controls

open PCSOmega

def A : BForm 2 := .atom ⟨0, by decide⟩
def B : BForm 2 := .atom ⟨1, by decide⟩

/-- Implication reversal: least distinguishing assignment `A = false, B = true`. -/
example : check (.imp A B) (.imp B A) = some [false, true] := by decide
theorem implication_reversal_not_equiv : ¬ SemEquiv (.imp A B) (.imp B A) :=
  (check_some_sound (w := [false, true]) (by decide)).2.2.2

/-- De Morgan. -/
theorem de_morgan_equiv : SemEquiv (.not (.and A B)) (.or (.not A) (.not B)) :=
  (check_none_iff _ _).1 (by decide)

/-- A remembered counterexample rejects the reversed implication. -/
example : screen (.imp A B) (.imp B A) [[false, true]] = some [false, true] := by decide
theorem remembered_rejection : ¬ SemEquiv (.imp A B) (.imp B A) :=
  (screen_some_not_equiv (w := [false, true]) (W := [[false, true]]) (by decide)).2

/-- **Survival of a partial witness filter does not imply equivalence.** -/
theorem screen_survivor_not_equiv :
    screen (.imp A B) (.or A B) [[true, true]] = none ∧ ¬ SemEquiv (.imp A B) (.or A B) :=
  ⟨by decide, (check_some_sound (w := [false, false]) (by decide)).2.2.2⟩

/-- `n = 0`. -/
example : check (.tt : BForm 0) .ff = some [] := by decide
example : check (.tt : BForm 0) (.not .ff) = none := by decide
example : (checkReceipt (.tt : BForm 0) .ff).assignmentsChecked = 1 := by decide

/-- A bounded repair episode for the constant ranking: the reversed implication is repaired by
swapping, the episode replays, and the solution is equivalent (by the general theorem). -/
def rk : Ranker 2 := fun _ _ => true
def bud : Budget := ⟨8, 1, 64⟩
example : (search (.imp A B) (.imp B A) rk bud).status = .booleanVerified := by decide
example : (search (.imp A B) (.imp B A) rk bud).solution = some (.imp A B) := by decide
example : replay (search (.imp A B) (.imp B A) rk bud) = true := by decide
theorem episode_solution_sound : ∀ s, (search (.imp A B) (.imp B A) rk bud).solution = some s →
    SemEquiv (.imp A B) s := fun _ h => search_solution_sound _ _ _ _ h

/-- A tampered episode (claimed solution changed) fails replay. -/
example : replay { search (.imp A B) (.imp B A) rk bud with solution := some (.imp B A) } = false := by
  decide

/-- Named lowering: undeclared symbol rejected, declared formula lowered with its meaning. -/
example : (lower (n := 2) ["A", "B"] (.and (.atom "A") (.atom "C"))).isNone = true := by decide
example : lower (n := 2) ["A", "B"] (.imp (.atom "A") (.atom "B")) = some (.imp A B) := by decide
example : namesOK 24 ["A", "B", "C_1"] = true := by decide
example : namesOK 24 ["B", "A"] = false := by decide
example : namesOK 24 ["A", "A"] = false := by decide
example : namesOK 24 ["AND"] = false := by decide
example : namesOK 24 ["a"] = false := by decide

end PCSOmega.Controls
