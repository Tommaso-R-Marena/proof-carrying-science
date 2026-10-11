import PCSOmega.Formula

/-!
# Fresh exhaustive equivalence checking and remembered-witness screening

Reference model of `pcs/experimental/omega/logic.py::check` and of the witness screen in
`adaptive.py::search`.

* `check src cand` scans `allAsg n` (False-before-True) and returns the first
  disagreement.  `check_none_iff` : no disagreement ⇔ semantic equivalence;
  `check_some_sound` : a returned witness has length `n` and genuinely distinguishes the
  immutable source from the candidate; `check_some_least` : it is the lexicographically least
  disagreement.
* `checkReceipt` mirrors the Python receipt content (truth pairs, count `2^n`, verdict,
  counterexample, authority flags `false`).
* `screen` evaluates a candidate on remembered witnesses only.  Rejection implies
  non-equivalence; rejection persists when witnesses are appended; every equivalent
  candidate survives every witness list.  Survival alone does **not** imply equivalence
  (`screen_survivor_not_equiv` in `PCSOmega.Controls`).
-/

namespace PCSOmega

variable {n : Nat}

/-- Disagreement of source and candidate at a total assignment. -/
def disagree (src cand : BForm n) (a : List Bool) : Bool :=
  src.eval (envOf a) != cand.eval (envOf a)

/-- Fresh exhaustive check: first disagreement in False-before-True order. -/
def check (src cand : BForm n) : Option (List Bool) :=
  (allAsg n).find? (disagree src cand)

theorem disagree_iff (src cand : BForm n) (a : List Bool) :
    disagree src cand a = true ↔ ¬ (src.Holds (envOf a) ↔ cand.Holds (envOf a)) := by
  rw [← BForm.eval_iff_holds, ← BForm.eval_iff_holds]
  unfold disagree
  cases src.eval (envOf a) <;> cases cand.eval (envOf a) <;> simp

/-- Equivalence on all valuations reduces to agreement on all total assignments. -/
theorem semEquiv_iff_lists (src cand : BForm n) :
    SemEquiv src cand ↔ ∀ a : List Bool, a.length = n → disagree src cand a = false := by
  constructor
  · intro h a _
    have := h (envOf a)
    cases hd : disagree src cand a
    · rfl
    · exact absurd this ((disagree_iff src cand a).1 hd)
  · intro h ρ
    have hl := h (listOf ρ n) (listOf_length ρ n)
    have hc : ∀ f : BForm n, f.eval (envOf (listOf ρ n)) = f.eval ρ :=
      fun f => BForm.eval_congr (fun i hi => envOf_listOf hi) f
    have : ¬ ¬ (src.Holds (envOf (listOf ρ n)) ↔ cand.Holds (envOf (listOf ρ n))) := by
      intro hn; rw [(disagree_iff src cand _).2 hn] at hl; contradiction
    have hiff := Classical.not_not.1 this
    rw [← BForm.eval_iff_holds, ← BForm.eval_iff_holds, hc, hc] at hiff
    rw [← BForm.eval_iff_holds, ← BForm.eval_iff_holds]; exact hiff

/-- **Exhaustive checking is exactly equivalence.** -/
theorem check_none_iff (src cand : BForm n) : check src cand = none ↔ SemEquiv src cand := by
  rw [semEquiv_iff_lists, check, List.find?_eq_none]
  constructor
  · intro h a ha
    have := h a (mem_allAsg.2 ha)
    simpa using this
  · intro h a ha
    simp [h a (mem_allAsg.1 ha)]

/-- **A returned witness genuinely distinguishes the immutable source.** -/
theorem check_some_sound {src cand : BForm n} {w : List Bool} (h : check src cand = some w) :
    w.length = n ∧ disagree src cand w = true ∧
      (src.Holds (envOf w) ↔ ¬ cand.Holds (envOf w)) ∧ ¬ SemEquiv src cand := by
  have hmem := List.mem_of_find?_eq_some h
  have hp := List.find?_some h
  refine ⟨mem_allAsg.1 hmem, hp, ?_, fun he => (disagree_iff src cand w).1 hp (he _)⟩
  have := (disagree_iff src cand w).1 hp
  constructor
  · intro hs hc; exact this ⟨fun _ => hc, fun _ => hs⟩
  · intro hc
    exact Classical.byContradiction fun hs => this ⟨fun h' => absurd h' hs, fun h' => absurd h' hc⟩

/-- **The returned witness is the first (lexicographically least) disagreement.** -/
theorem check_some_least {src cand : BForm n} {w : List Bool} (h : check src cand = some w) :
    IsLexLeast (fun a => a.length = n ∧ disagree src cand a = true) w := by
  refine ⟨⟨(check_some_sound h).1, (check_some_sound h).2.1⟩, ?_⟩
  intro b ⟨hb, hd⟩
  exact find?_pairwise_least (pairwise_lexLt_allAsg n) h b (mem_allAsg.2 hb) hd

/-- Receipt content of a fresh exhaustive check (hash fields are outside the model). -/
structure CheckReceipt where
  assignmentsChecked : Nat
  truthPairs : List (Bool × Bool)
  equivalent : Bool
  counterexample : Option (List Bool × Bool × Bool)
  pcsAuthority : Bool
  leanKernelChecked : Bool
  deriving DecidableEq, Repr

/-- The receipt regenerated from the task. -/
def checkReceipt (src cand : BForm n) : CheckReceipt :=
  { assignmentsChecked := (allAsg n).length
    truthPairs := (allAsg n).map (fun a => (src.eval (envOf a), cand.eval (envOf a)))
    equivalent := (check src cand).isNone
    counterexample := (check src cand).map (fun a => (a, src.eval (envOf a), cand.eval (envOf a)))
    pcsAuthority := false
    leanKernelChecked := false }

theorem checkReceipt_equivalent_iff (src cand : BForm n) :
    (checkReceipt src cand).equivalent = true ↔ SemEquiv src cand := by
  simp [checkReceipt, ← check_none_iff, Option.isNone_iff_eq_none]

theorem checkReceipt_count (src cand : BForm n) :
    (checkReceipt src cand).assignmentsChecked = 2 ^ n := length_allAsg n

theorem checkReceipt_flags (src cand : BForm n) :
    (checkReceipt src cand).pcsAuthority = false ∧
      (checkReceipt src cand).leanKernelChecked = false := ⟨rfl, rfl⟩

/-- Receipt verification: exact regeneration. -/
def verifyCheckReceipt (src cand : BForm n) (r : CheckReceipt) : Bool :=
  r == checkReceipt src cand

theorem verifyCheckReceipt_iff (src cand : BForm n) (r : CheckReceipt) :
    verifyCheckReceipt src cand r = true ↔ r = checkReceipt src cand := by
  simp [verifyCheckReceipt]

/-! ## Remembered-witness screening -/

/-- Partial evaluation on remembered witnesses; returns the first rejecting witness. -/
def screen (src cand : BForm n) (W : List (List Bool)) : Option (List Bool) :=
  W.find? (disagree src cand)

/-- **Screen rejection implies non-equivalence.** -/
theorem screen_some_not_equiv {src cand : BForm n} {W : List (List Bool)} {w : List Bool}
    (h : screen src cand W = some w) : w ∈ W ∧ ¬ SemEquiv src cand := by
  refine ⟨List.mem_of_find?_eq_some h, fun he => ?_⟩
  exact (disagree_iff src cand w).1 (List.find?_some h) (he _)

/-- **Adding witnesses cannot restore a rejected candidate** (the same witness still rejects). -/
theorem screen_append_of_some {src cand : BForm n} {W : List (List Bool)} {w : List Bool}
    (h : screen src cand W = some w) (W' : List (List Bool)) :
    screen src cand (W ++ W') = some w := by
  unfold screen at *; rw [List.find?_append, h]; rfl

/-- Rejection is also preserved under prepending witnesses. -/
theorem screen_isSome_append_left {src cand : BForm n} {W : List (List Bool)}
    (h : (screen src cand W).isSome) (W' : List (List Bool)) :
    (screen src cand (W' ++ W)).isSome := by
  unfold screen at *
  rw [List.find?_append]
  cases h' : W'.find? (disagree src cand) <;> simp_all

/-- **Every genuinely equivalent candidate survives every remembered witness.** -/
theorem screen_none_of_equiv {src cand : BForm n} (he : SemEquiv src cand)
    (W : List (List Bool)) : screen src cand W = none := by
  unfold screen
  rw [List.find?_eq_none]
  intro a _ hd
  exact (disagree_iff src cand a).1 hd (he _)

end PCSOmega
