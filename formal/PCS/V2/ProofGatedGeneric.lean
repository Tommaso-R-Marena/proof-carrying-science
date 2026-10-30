import Lean

/-!
# Generic proof-gated self-modification over an arbitrary exact model family

This module abstracts the acceptance gate that `ProofGatedSelfImprovement` (single
neuron) and `ProofGatedMultilayer` (two hidden neurons) each re-implement, and proves
its properties **once**, for every model type `M` with an exact integer evaluator.

A `GateSpec M` fixes
* an exact, total evaluator `predict : M → Int → Int`,
* a reference `target : Int → Int`,
* a finite benchmark `corpus : List Int`,
* a decidable parameter / architecture validity predicate `valid : M → Bool`.

Results (all for arbitrary `M`, arbitrary specs, arbitrary proposal sequences):
* `accept_iff_admissible`: the executable decision is *exactly* the mathematical
  admissibility relation (soundness **and** completeness).
* `CertifiedTrace` / `trace_length_bound`: any accepted chain of length `n`
  satisfies `n + loss last ≤ loss first`.
* `runSched` with an arbitrary, possibly adaptive or adversarial proposer
  `Nat → M → M`: correctness preservation, validity preservation, loss
  non-increase, `countSched + loss final ≤ loss initial`.
* `perfect_valid_always_accepted`: a valid candidate that is perfect on the corpus
  is always accepted from any valid imperfect incumbent (no false rejection of the
  optimum), and `perfect_cannot_advance`: nothing is accepted after perfection.

What is **not** claimed: anything about inputs outside `corpus`, about the quality of
the proposer, or about an "acceleration" of future improvement. The loss is a
bounded natural number, so every gated run makes at most `loss initial` changes.
-/

namespace PCS.V2.ProofGatedGeneric

structure GateSpec (M : Type) where
  predict : M → Int → Int
  target : Int → Int
  corpus : List Int
  valid : M → Bool

variable {M : Type} (S : GateSpec M)

def correct (m : M) (x : Int) : Prop := S.predict m x = S.target x

instance instCorrectDecidable (m : M) (x : Int) : Decidable (correct S m x) :=
  inferInstanceAs (Decidable (S.predict m x = S.target x))

/-- Exact natural-valued benchmark error. -/
def loss (m : M) : Nat :=
  (S.corpus.map fun x => (S.predict m x - S.target x).natAbs).sum

def preservesB : List Int → M → M → Bool
  | [], _, _ => true
  | x :: xs, a, b => decide (correct S a x → correct S b x) && preservesB xs a b

def gainsB : List Int → M → M → Bool
  | [], _, _ => false
  | x :: xs, a, b => decide (¬ correct S a x ∧ correct S b x) || gainsB xs a b

/-- The mathematical admissibility relation of a self-modification `a ↦ b`. -/
def admissible (a b : M) : Prop :=
  S.valid a = true ∧ S.valid b = true ∧
  (∀ x ∈ S.corpus, correct S a x → correct S b x) ∧
  (∃ x ∈ S.corpus, ¬ correct S a x ∧ correct S b x) ∧
  loss S b < loss S a

/-- The executable gate. -/
def accept (a b : M) : Bool :=
  (((S.valid a && S.valid b) && preservesB S S.corpus a b) && gainsB S S.corpus a b) &&
    decide (loss S b < loss S a)

theorem preservesB_iff (xs : List Int) (a b : M) :
    preservesB S xs a b = true ↔ ∀ x ∈ xs, correct S a x → correct S b x := by
  induction xs with
  | nil => simp [preservesB]
  | cons y ys ih =>
      simp only [preservesB, Bool.and_eq_true, decide_eq_true_eq, ih, List.mem_cons]
      constructor
      · rintro ⟨h1, h2⟩ x (rfl | hx)
        · exact h1
        · exact h2 x hx
      · intro h
        exact ⟨h y (Or.inl rfl), fun x hx => h x (Or.inr hx)⟩

theorem gainsB_iff (xs : List Int) (a b : M) :
    gainsB S xs a b = true ↔ ∃ x ∈ xs, ¬ correct S a x ∧ correct S b x := by
  induction xs with
  | nil => simp [gainsB]
  | cons y ys ih =>
      simp only [gainsB, Bool.or_eq_true, decide_eq_true_eq, ih, List.mem_cons]
      constructor
      · rintro (h | ⟨x, hx, hc⟩)
        · exact ⟨y, Or.inl rfl, h⟩
        · exact ⟨x, Or.inr hx, hc⟩
      · rintro ⟨x, (rfl | hx), hc⟩
        · exact Or.inl hc
        · exact Or.inr ⟨x, hx, hc⟩

/-- Soundness and completeness of the executable gate. -/
theorem accept_iff_admissible (a b : M) : accept S a b = true ↔ admissible S a b := by
  simp only [accept, admissible, Bool.and_eq_true, decide_eq_true_eq, preservesB_iff,
    gainsB_iff]
  constructor
  · rintro ⟨⟨⟨⟨h1, h2⟩, h3⟩, h4⟩, h5⟩
    exact ⟨h1, h2, h3, h4, h5⟩
  · rintro ⟨h1, h2, h3, h4, h5⟩
    exact ⟨⟨⟨⟨h1, h2⟩, h3⟩, h4⟩, h5⟩

variable {S}

theorem accept_sound {a b : M} (h : accept S a b = true) : admissible S a b :=
  (accept_iff_admissible S a b).mp h

theorem accept_complete {a b : M} (h : admissible S a b) : accept S a b = true :=
  (accept_iff_admissible S a b).mpr h

theorem accepted_preserves {a b : M} (h : accept S a b = true)
    (x : Int) (hx : x ∈ S.corpus) (hc : correct S a x) : correct S b x :=
  (accept_sound h).2.2.1 x hx hc

theorem accepted_gains {a b : M} (h : accept S a b = true) :
    ∃ x ∈ S.corpus, ¬ correct S a x ∧ correct S b x :=
  (accept_sound h).2.2.2.1

theorem accepted_strict_loss {a b : M} (h : accept S a b = true) : loss S b < loss S a :=
  (accept_sound h).2.2.2.2

theorem accepted_valid {a b : M} (h : accept S a b = true) : S.valid b = true :=
  (accept_sound h).2.1

theorem accepted_incumbent_valid {a b : M} (h : accept S a b = true) : S.valid a = true :=
  (accept_sound h).1

/-- The acceptance relation is irreflexive. -/
theorem accept_irrefl (a : M) : accept S a a = false := by
  cases h : accept S a a with
  | false => rfl
  | true => exact absurd (accepted_strict_loss h) (Nat.lt_irrefl _)

/-- The acceptance relation is transitive: a two-step certified improvement is also a
one-step certified improvement. Hence acceptance is a strict partial order, and it is
well-founded because it strictly decreases the natural-valued loss. -/
theorem accept_trans {a b c : M} (hab : accept S a b = true) (hbc : accept S b c = true) :
    accept S a c = true := by
  obtain ⟨va, _, pab, ⟨x, hx, hxa, hxb⟩, lab⟩ := accept_sound hab
  obtain ⟨_, vc, pbc, _, lbc⟩ := accept_sound hbc
  exact accept_complete ⟨va, vc, fun y hy h => pbc y hy (pab y hy h),
    ⟨x, hx, hxa, pbc x hx hxb⟩, Nat.lt_trans lbc lab⟩

/-! ## Loss characterisation -/

theorem loss_eq_zero_iff (m : M) : loss S m = 0 ↔ ∀ x ∈ S.corpus, correct S m x := by
  unfold loss correct
  induction S.corpus with
  | nil => simp
  | cons y ys ih =>
      simp only [List.map_cons, List.sum_cons, List.mem_cons]
      constructor
      · intro h x hx
        have h1 : (S.predict m y - S.target y).natAbs = 0 := by omega
        have h2 : (ys.map fun x => (S.predict m x - S.target x).natAbs).sum = 0 := by omega
        rcases hx with rfl | hx
        · omega
        · exact ih.mp h2 x hx
      · intro h
        have h1 := h y (Or.inl rfl)
        have h2 := ih.mpr (fun x hx => h x (Or.inr hx))
        rw [h1, h2]
        simp

theorem perfect_cannot_advance (m : M) (h : ∀ x ∈ S.corpus, correct S m x) (c : M) :
    accept S m c = false := by
  cases hc : accept S m c with
  | false => rfl
  | true =>
      obtain ⟨x, hx, hwrong, _⟩ := accepted_gains hc
      exact False.elim (hwrong (h x hx))

/-- **Liveness of the optimum**: a valid candidate that is perfect on the corpus is
always accepted from a valid incumbent that is not yet perfect. -/
theorem perfect_valid_always_accepted (a b : M) (ha : S.valid a = true)
    (hb : S.valid b = true) (hperfect : ∀ x ∈ S.corpus, correct S b x)
    (himperfect : ∃ x ∈ S.corpus, ¬ correct S a x) : accept S a b = true := by
  apply accept_complete
  obtain ⟨x, hx, hwrong⟩ := himperfect
  refine ⟨ha, hb, fun y hy _ => hperfect y hy, ⟨x, hx, hwrong, hperfect x hx⟩, ?_⟩
  have h0 : loss S b = 0 := (loss_eq_zero_iff b).mpr hperfect
  have h1 : loss S a ≠ 0 := fun h => hwrong ((loss_eq_zero_iff a).mp h x hx)
  omega

/-! ## Accepted traces -/

inductive CertifiedTrace (S : GateSpec M) : Nat → M → M → Prop where
  | zero (m : M) : CertifiedTrace S 0 m m
  | extend {n : Nat} {a b c : M} :
      CertifiedTrace S n a b → accept S b c = true → CertifiedTrace S (n + 1) a c

theorem trace_preserves {n : Nat} {a b : M} (h : CertifiedTrace S n a b)
    (x : Int) (hx : x ∈ S.corpus) (ha : correct S a x) : correct S b x := by
  induction h with
  | zero m => exact ha
  | extend _ hc ih => exact accepted_preserves hc x hx (ih ha)

theorem trace_length_bound {n : Nat} {a b : M} (h : CertifiedTrace S n a b) :
    n + loss S b ≤ loss S a := by
  induction h with
  | zero m => simp
  | extend _ hc ih =>
      have := accepted_strict_loss hc
      omega

theorem trace_steps_bounded {n : Nat} {a b : M} (h : CertifiedTrace S n a b) :
    n ≤ loss S a := by
  have := trace_length_bound h
  omega

theorem trace_valid {n : Nat} {a b : M} (h : CertifiedTrace S n a b)
    (ha : S.valid a = true) : S.valid b = true := by
  induction h with
  | zero m => exact ha
  | extend _ hc _ => exact accepted_valid hc

/-- Every step of a positive-length certified trace gains a corpus point, and the
endpoint is correct on strictly more corpus points than the start. -/
theorem trace_strict_gain {n : Nat} {a b : M} (h : CertifiedTrace S (n + 1) a b) :
    ∃ x ∈ S.corpus, ¬ correct S a x ∧ correct S b x := by
  cases h with
  | extend hp hc =>
      rename_i mid
      obtain ⟨x, hx, hw, hcx⟩ := accepted_gains hc
      refine ⟨x, hx, fun hax => hw (trace_preserves hp x hx hax), hcx⟩

/-- No accepted trace from a model is longer than its loss: there is no infinite
certified self-improvement chain. -/
theorem no_long_trace (a b : M) (n : Nat) (hn : loss S a < n) :
    ¬ CertifiedTrace S n a b := fun h => by
  have := trace_steps_bounded h
  omega

/-! ## Arbitrary, adaptive, adversarial proposers -/

def gatedStep (S : GateSpec M) (m proposed : M) : M :=
  if accept S m proposed then proposed else m

theorem gatedStep_reject {m p : M} (h : accept S m p = false) : gatedStep S m p = m := by
  simp [gatedStep, h]

theorem gatedStep_accept {m p : M} (h : accept S m p = true) : gatedStep S m p = p := by
  simp [gatedStep, h]

/-- Fully general adaptive schedule: step `i` queries `proposer i` on the current
state, so the proposal may depend arbitrarily on the step index and the state (and
hence on any external schedule, adversary or changing strategy). -/
def runSched (S : GateSpec M) (proposer : Nat → M → M) : Nat → Nat → M → M
  | _, 0, m => m
  | i, k + 1, m => runSched S proposer (i + 1) k (gatedStep S m (proposer i m))

def countSched (S : GateSpec M) (proposer : Nat → M → M) : Nat → Nat → M → Nat
  | _, 0, _ => 0
  | i, k + 1, m =>
      (if accept S m (proposer i m) then 1 else 0) +
        countSched S proposer (i + 1) k (gatedStep S m (proposer i m))

theorem gatedStep_preserves (m p : M) (x : Int) (hx : x ∈ S.corpus)
    (hc : correct S m x) : correct S (gatedStep S m p) x := by
  cases h : accept S m p with
  | false => simpa [gatedStep, h] using hc
  | true => simpa [gatedStep, h] using accepted_preserves h x hx hc

theorem gatedStep_valid (m p : M) (hv : S.valid m = true) :
    S.valid (gatedStep S m p) = true := by
  cases h : accept S m p with
  | false => simpa [gatedStep, h] using hv
  | true => simpa [gatedStep, h] using accepted_valid h

theorem gatedStep_count (m p : M) :
    (if accept S m p then 1 else 0) + loss S (gatedStep S m p) ≤ loss S m := by
  cases h : accept S m p with
  | false => simp [gatedStep, h]
  | true =>
      have := accepted_strict_loss h
      simp [gatedStep, h]
      omega

theorem runSched_preserves (proposer : Nat → M → M) (k i : Nat) (m : M)
    (x : Int) (hx : x ∈ S.corpus) (hc : correct S m x) :
    correct S (runSched S proposer i k m) x := by
  induction k generalizing i m with
  | zero => simpa [runSched] using hc
  | succ k ih => exact ih (i + 1) _ (gatedStep_preserves m _ x hx hc)

theorem runSched_valid (proposer : Nat → M → M) (k i : Nat) (m : M)
    (hv : S.valid m = true) : S.valid (runSched S proposer i k m) = true := by
  induction k generalizing i m with
  | zero => simpa [runSched] using hv
  | succ k ih => exact ih (i + 1) _ (gatedStep_valid m _ hv)

/-- **Bounded improvement for arbitrary proposal sequences**: along any schedule of
any length, the number of accepted self-modifications plus the final loss is at
most the initial loss. -/
theorem runSched_count_bound (proposer : Nat → M → M) (k i : Nat) (m : M) :
    countSched S proposer i k m + loss S (runSched S proposer i k m) ≤ loss S m := by
  induction k generalizing i m with
  | zero => simp [countSched, runSched]
  | succ k ih =>
      have h1 := ih (i + 1) (gatedStep S m (proposer i m))
      have h2 := gatedStep_count (S := S) m (proposer i m)
      simp only [countSched, runSched]
      omega

theorem runSched_loss_nonincrease (proposer : Nat → M → M) (k i : Nat) (m : M) :
    loss S (runSched S proposer i k m) ≤ loss S m := by
  have := runSched_count_bound (S := S) proposer k i m
  omega

theorem runSched_accepted_le_loss (proposer : Nat → M → M) (k i : Nat) (m : M) :
    countSched S proposer i k m ≤ loss S m := by
  have := runSched_count_bound (S := S) proposer k i m
  omega

/-- Once perfect, a gated run is frozen whatever is proposed. -/
theorem runSched_frozen_of_perfect (proposer : Nat → M → M) (k i : Nat) (m : M)
    (h : ∀ x ∈ S.corpus, correct S m x) : runSched S proposer i k m = m := by
  induction k generalizing i with
  | zero => rfl
  | succ k ih =>
      simp only [runSched]
      rw [gatedStep_reject (perfect_cannot_advance m h _)]
      exact ih (i + 1)

/-- Every gated run is a certified trace whose length is the accepted count. -/
theorem runSched_certified (proposer : Nat → M → M) (k i : Nat) (m : M) :
    CertifiedTrace S (countSched S proposer i k m) m (runSched S proposer i k m) := by
  induction k generalizing i m with
  | zero => exact CertifiedTrace.zero m
  | succ k ih =>
      simp only [countSched, runSched]
      cases h : accept S m (proposer i m) with
      | false =>
          simp only [gatedStep_reject h]
          simpa using ih (i + 1) m
      | true =>
          simp only [gatedStep_accept h, if_true]
          have rest := ih (i + 1) (proposer i m)
          -- prepend the accepted step
          have pre : ∀ {n : Nat} {b c : M}, CertifiedTrace S n b c → accept S m b = true →
              CertifiedTrace S (1 + n) m c := by
            intro n b c hbc hmb
            induction hbc with
            | zero b' =>
                exact CertifiedTrace.extend (CertifiedTrace.zero m) hmb
            | extend _ hc' ih' =>
                rw [← Nat.add_assoc]
                exact CertifiedTrace.extend (ih' hmb) hc'
          exact pre rest h

/-- Index of change detection: if two consecutive gated states differ, the step was
an accepted, strictly loss-decreasing one. -/
theorem gatedStep_changed {m p : M} (h : gatedStep S m p ≠ m) :
    accept S m p = true ∧ loss S (gatedStep S m p) < loss S m := by
  cases ha : accept S m p with
  | false => exact absurd (gatedStep_reject ha) h
  | true => exact ⟨rfl, by rw [gatedStep_accept ha]; exact accepted_strict_loss ha⟩

end PCS.V2.ProofGatedGeneric
