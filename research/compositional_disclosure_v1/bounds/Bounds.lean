import Ledger
set_option autoImplicit false
namespace PCSDisclosureBounds
open PCSDisclosure

-- Optimality is restricted to truthful deterministic query gates that answer
-- in ALL worlds or deny in ALL worlds at the same public possibility set.
theorem safe_iff_all_worlds (k : List Nat) (q : Nat) :
    safe k q = true ↔ ∀ w ∈ k, ambiguous (cell k q (answer q w)) = true :=
  List.all_eq_true

theorem unsafe_has_disclosing_world (k : List Nat) (q : Nat) (hu : safe k q = false) :
    ∃ w ∈ k, ambiguous (cell k q (answer q w)) = false := by
  apply Classical.byContradiction
  intro hn
  have ht : safe k q = true := by
    apply (safe_iff_all_worlds k q).mpr
    intro w hw
    cases he : ambiguous (cell k q (answer q w)) with
    | false => exact False.elim (hn ⟨w,hw,he⟩)
    | true => rfl
  simp [hu] at ht

theorem maximal_truthful_uniform_gate (k : List Nat) (q : Nat) (allow : Bool)
    (hs : ∀ w ∈ k, ambiguous (if allow then cell k q (answer q w) else k) = true)
    (ha : allow = true) : safe k q = true := by
  apply (safe_iff_all_worlds k q).mpr
  intro w hw
  simpa [ha] using hs w hw

-- Exact finite closure. No learned model or Python search is a proof premise.
def classes : List (List Nat) :=
  [initial,cell initial 2 0,cell initial 2 1,cell initial 4 0,
   cell initial 4 1,cell initial 8 0,cell initial 8 1]
def trueCount (k : List Nat) : Nat := (k.filter secret).length
def falseCount (k : List Nat) : Nat := (k.filter fun w => !secret w).length
-- Under a UNIFORM prior and deterministic public planning, exact consistency
-- makes this a posterior majority bound. These integer inequalities themselves
-- make no probabilistic assumptions.
def bounded (k : List Nat) : Bool := decide
  (3 ≤ k.length ∧ 3 * trueCount k ≤ 2 * k.length ∧ 3 * falseCount k ≤ 2 * k.length)

theorem finite_class_closure : classes.all (fun k =>
    k.all (fun w => (List.range 16).all (fun q => decide ((step k w q).1 ∈ classes)))) = true := by decide

theorem every_class_bounded : classes.all bounded = true := by decide

theorem initial_in_classes : initial ∈ classes := by decide

theorem closed_step (k : List Nat) (w q : Nat) (hk : k ∈ classes)
    (hw : w ∈ k) (hq : q < 16) : (step k w q).1 ∈ classes := by
  have h := List.all_eq_true.mp finite_class_closure k hk
  have h' := List.all_eq_true.mp h w hw
  have h'' := List.all_eq_true.mp h' q (List.mem_range.mpr hq)
  exact of_decide_eq_true h''

theorem closed_history (qs k : List Nat) (w : Nat) (hk : k ∈ classes)
    (hw : w ∈ k) (hq : ∀ q ∈ qs, q < 16) : (run k w qs).1 ∈ classes := by
  induction qs generalizing k with
  | nil => exact hk
  | cons q qs ih =>
    exact ih _ (closed_step k w q hk hw (hq q (by simp)))
      (actual_retained k w q hw) (fun a ha => hq a (by simp [ha]))

theorem no_transcript_majority_above_two_thirds (qs : List Nat) (w : Nat)
    (hw : w ∈ initial) (hq : ∀ q ∈ qs, q < 16) :
    let k := (run initial w qs).1
    3 ≤ k.length ∧ 3 * trueCount k ≤ 2 * k.length ∧
      3 * falseCount k ≤ 2 * k.length := by
  have hc := closed_history qs initial w initial_in_classes hw hq
  have hb := List.all_eq_true.mp every_class_bounded _ hc
  exact of_decide_eq_true hb

theorem two_thirds_is_attained :
    let k := (run initial 3 [2]).1
    k.length = 3 ∧ trueCount k = 1 ∧ falseCount k = 2 := by decide
theorem adaptive_closed (planner : List (Nat × Option Nat) → Nat) (n : Nat)
    (k : List Nat) (w : Nat) (h : List (Nat × Option Nat)) (hk : k ∈ classes)
    (hw : w ∈ k) (hp : ∀ hist, planner hist < 16) :
    (adaptive planner w n k h).1 ∈ classes := by
  induction n generalizing k h with
  | zero => exact hk
  | succ n ih =>
    exact ih _ _ (closed_step k w (planner h) hk hw (hp h))
      (actual_retained k w (planner h) hw)

theorem adaptive_majority_bound (planner : List (Nat × Option Nat) → Nat)
    (n : Nat) (w : Nat) (h : List (Nat × Option Nat))
    (hw : w ∈ initial) (hp : ∀ hist, planner hist < 16) :
    let k := (adaptive planner w n initial h).1
    3 ≤ k.length ∧ 3 * trueCount k ≤ 2 * k.length ∧
      3 * falseCount k ≤ 2 * k.length := by
  have hc := adaptive_closed planner n initial w h initial_in_classes hw hp
  exact of_decide_eq_true (List.all_eq_true.mp every_class_bounded _ hc)
end PCSDisclosureBounds
