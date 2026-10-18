import PCS.V2.ProofGatedRobust

/-!
# The unified strong acceptance gate

A self-modification `a ↦ m` of a one-input integer ReLU network (`WideNet`, any width,
any parameter size), with a target network `t`, a finite benchmark `corpus`, an
architecture bound `A` and a bounded interval `[L,U]`, is accepted iff:

* **A. Certified progress.** The corpus gate of `ProofGatedGeneric` accepts: both models
  are valid for `A`, every corpus input correct for `a` stays correct, at least one
  corpus input becomes newly correct, and the natural-valued corpus loss strictly
  decreases.
* **B. Universal no-forgetting.** Every integer (not only corpus inputs) on which `a`
  agrees with `t` is still handled correctly by `m` (`ProofGatedNoForget`).
* **C. Bounded-region robustness.** The maximum absolute error over `[L,U] ∩ ℤ` does not
  increase (`ProofGatedRobust`), computed exactly from breakpoints.

Results:
* `acceptStrong_iff`: the executable gate is **sound and complete** for A ∧ B ∧ C;
* `StrongTrace` chains: `strongTrace_noForget`, `strongTrace_robust`,
  `strongTrace_maxAbsErr`, `strongTrace_loss`, `strongTrace_valid`;
* `runStrong`: an arbitrary, adaptive, possibly adversarial proposal schedule
  `proposer : Nat → WideNet → WideNet` filtered by the gate. Whatever the proposer does,
  the run is a `StrongTrace` (`runStrong_trace`), so all invariants hold, and the number
  of accepted modifications is at most the initial corpus loss (`countStrong_le_loss`);
* checked examples: a 3-generation improvement chain that passes the gate on
  `[-10^9, 10^9]`, the original growth chain that passes on `[-4,4]` but is rejected on
  `[-50,50]` (with an extracted witness), and adversarial rejections showing that each
  of A, B and C rejects some candidate that the other two accept.
-/

namespace PCS.V2.ProofGatedStrongGate

open PCS.V2.ProofGatedSelfImprovement (relu)
open PCS.V2.ProofGatedGeneric
open PCS.V2.ProofGatedWide
open PCS.V2.ProofGatedNoForget
open PCS.V2.ProofGatedRobust
open PCS.V2.ProofGatedLimits (oodCandidate)

/-- Parameters of the strong gate. -/
structure StrongSpec where
  arch : Arch
  target : WideNet
  corpus : List Int
  lo : Int
  hi : Int

/-- The corpus gate specification induced by a strong specification. -/
def StrongSpec.corpusSpec (S : StrongSpec) : GateSpec WideNet :=
  wideSpec S.arch (predict S.target) S.corpus

/-- **The executable strong gate.** -/
def acceptStrong (S : StrongSpec) (a m : WideNet) : Bool :=
  accept S.corpusSpec a m && noForgetting a m S.target && robustB a m S.target S.lo S.hi

/-- The mathematical requirement A ∧ B ∧ C. -/
def StrongAdmissible (S : StrongSpec) (a m : WideNet) : Prop :=
  admissible S.corpusSpec a m ∧
  (∀ x : Int, predict a x = predict S.target x → predict m x = predict S.target x) ∧
  (∀ B : Nat, ErrBound a S.target S.lo S.hi B → ErrBound m S.target S.lo S.hi B)

/-- **Soundness and completeness of the strong gate.** -/
theorem acceptStrong_iff (S : StrongSpec) (a m : WideNet) :
    acceptStrong S a m = true ↔ StrongAdmissible S a m := by
  simp only [acceptStrong, Bool.and_eq_true, StrongAdmissible]
  rw [accept_iff_admissible, noForgetting_iff, robustB_iff]
  exact ⟨fun ⟨⟨h1, h2⟩, h3⟩ => ⟨h1, h2, h3⟩, fun ⟨h1, h2, h3⟩ => ⟨⟨h1, h2⟩, h3⟩⟩

theorem acceptStrong_sound {S : StrongSpec} {a m : WideNet} (h : acceptStrong S a m = true) :
    StrongAdmissible S a m := (acceptStrong_iff S a m).mp h

theorem acceptStrong_complete {S : StrongSpec} {a m : WideNet} (h : StrongAdmissible S a m) :
    acceptStrong S a m = true := (acceptStrong_iff S a m).mpr h

/-- The strong gate refines the all-integer gate of `ProofGatedNoForget`. -/
theorem acceptStrong_acceptNF {S : StrongSpec} {a m : WideNet}
    (h : acceptStrong S a m = true) : acceptNF S.arch S.target S.corpus a m = true := by
  simp only [acceptStrong, Bool.and_eq_true] at h
  simp only [acceptNF, Bool.and_eq_true]
  exact h.1

theorem acceptStrong_maxAbsErr {S : StrongSpec} {a m : WideNet}
    (h : acceptStrong S a m = true) :
    maxAbsErr m S.target S.lo S.hi ≤ maxAbsErr a S.target S.lo S.hi := by
  simp only [acceptStrong, Bool.and_eq_true, robustB, decide_eq_true_eq] at h
  exact h.2

/-- A model is never strongly accepted against itself (no stuttering). -/
theorem acceptStrong_irrefl (S : StrongSpec) (a : WideNet) : acceptStrong S a a = false := by
  simp [acceptStrong, accept_irrefl]

/-- **Semantics-preserving transformations commute with the gate.** Replacing the
candidate by any network with the same validity status that computes the same function
on all integers does not change the strong decision. -/
theorem acceptStrong_congr_candidate (S : StrongSpec) (a : WideNet) {m m' : WideNet}
    (h : ∀ x, predict m x = predict m' x)
    (hv : valid S.arch m = valid S.arch m') :
    acceptStrong S a m = acceptStrong S a m' := by
  have h1 : accept S.corpusSpec a m = accept S.corpusSpec a m' :=
    accept_congr_candidate S.corpusSpec a (fun x _ => h x) hv
  have h2 : noForgetting a m S.target = noForgetting a m' S.target := by
    apply Bool.eq_iff_iff.mpr
    rw [noForgetting_iff, noForgetting_iff]
    simp only [h]
  have h3 : robustB a m S.target S.lo S.hi = robustB a m' S.target S.lo S.hi := by
    simp only [robustB,
      maxAbsErr_congr (f := m) (f' := m') (t := S.target) (t' := S.target)
        (fun x _ _ => h x) (fun _ _ _ => rfl)]
  simp only [acceptStrong, h1, h2, h3]

/-- Likewise for the incumbent. -/
theorem acceptStrong_congr_incumbent (S : StrongSpec) (m : WideNet) {a a' : WideNet}
    (h : ∀ x, predict a x = predict a' x)
    (hv : valid S.arch a = valid S.arch a') :
    acceptStrong S a m = acceptStrong S a' m := by
  have h1 : accept S.corpusSpec a m = accept S.corpusSpec a' m :=
    accept_congr_incumbent S.corpusSpec m (fun x _ => h x) hv
  have h2 : noForgetting a m S.target = noForgetting a' m S.target := by
    apply Bool.eq_iff_iff.mpr
    rw [noForgetting_iff, noForgetting_iff]
    simp only [h]
  have h3 : robustB a m S.target S.lo S.hi = robustB a' m S.target S.lo S.hi := by
    simp only [robustB,
      maxAbsErr_congr (f := a) (f' := a') (t := S.target) (t' := S.target)
        (fun x _ _ => h x) (fun _ _ _ => rfl)]
  simp only [acceptStrong, h1, h2, h3]

/-- Permuting the candidate's hidden units never changes the strong decision. -/
theorem acceptStrong_perm_invariant (S : StrongSpec) (a : WideNet) {m m' : WideNet}
    (h : m.hidden.Perm m'.hidden) (hb : m.outBias = m'.outBias) :
    acceptStrong S a m = acceptStrong S a m' :=
  acceptStrong_congr_candidate S a (fun x => predict_perm h hb x) (valid_perm S.arch h hb)

/-! ## Arbitrary accepted chains -/

/-- Chains of strongly accepted self-modifications of length `n` from `a` to `b`. -/
inductive StrongTrace (S : StrongSpec) : Nat → WideNet → WideNet → Prop
  | zero (a : WideNet) : StrongTrace S 0 a a
  | extend {n : Nat} {a b c : WideNet} : StrongTrace S n a b →
      acceptStrong S b c = true → StrongTrace S (n + 1) a c

variable {S : StrongSpec}

/-- **B along chains.** Every integer handled correctly at the start stays correct. -/
theorem strongTrace_noForget {n : Nat} {a b : WideNet} (h : StrongTrace S n a b) :
    ∀ x : Int, predict a x = predict S.target x → predict b x = predict S.target x := by
  induction h with
  | zero => exact fun _ hx => hx
  | extend _ hstep ih => exact fun x hx => (acceptStrong_sound hstep).2.1 x (ih x hx)

/-- **C along chains.** Every error bound valid for the start model on `[lo,hi]` remains
valid for every later model. -/
theorem strongTrace_robust {n : Nat} {a b : WideNet} (h : StrongTrace S n a b) :
    ∀ B : Nat, ErrBound a S.target S.lo S.hi B → ErrBound b S.target S.lo S.hi B := by
  induction h with
  | zero => exact fun _ hB => hB
  | extend _ hstep ih => exact fun B hB => (acceptStrong_sound hstep).2.2 B (ih B hB)

theorem strongTrace_maxAbsErr {n : Nat} {a b : WideNet} (h : StrongTrace S n a b) :
    maxAbsErr b S.target S.lo S.hi ≤ maxAbsErr a S.target S.lo S.hi := by
  induction h with
  | zero => exact Nat.le_refl _
  | extend _ hstep ih => exact Nat.le_trans (acceptStrong_maxAbsErr hstep) ih

/-- **A along chains.** Each accepted step strictly lowers the corpus loss, so the chain
is no longer than the starting loss. -/
theorem strongTrace_loss {n : Nat} {a b : WideNet} (h : StrongTrace S n a b) :
    loss S.corpusSpec b + n ≤ loss S.corpusSpec a := by
  induction h with
  | zero => simp
  | extend _ hstep ih =>
    have := (acceptStrong_sound hstep).1.2.2.2.2
    omega

theorem strongTrace_length_le_loss {n : Nat} {a b : WideNet} (h : StrongTrace S n a b) :
    n ≤ loss S.corpusSpec a := by
  have := strongTrace_loss h; omega

theorem strongTrace_valid {n : Nat} {a b : WideNet} (h : StrongTrace S n a b)
    (ha : S.corpusSpec.valid a = true) : S.corpusSpec.valid b = true := by
  induction h with
  | zero => exact ha
  | extend _ hstep _ => exact (acceptStrong_sound hstep).1.2.1

/-- Correctness on the corpus is preserved along chains. -/
theorem strongTrace_corpus {n : Nat} {a b : WideNet} (h : StrongTrace S n a b) :
    ∀ x ∈ S.corpus, correct S.corpusSpec a x → correct S.corpusSpec b x :=
  fun x _ hx => strongTrace_noForget h x hx

/-- No chain is longer than the initial loss. -/
theorem no_long_strongTrace (a b : WideNet) (n : Nat) (hn : loss S.corpusSpec a < n) :
    ¬ StrongTrace S n a b := fun h => by
  have := strongTrace_length_le_loss h; omega

/-! ## Adversarial proposal schedules -/

/-- One gated step: adopt the proposal iff the strong gate accepts it. -/
def strongStep (S : StrongSpec) (m p : WideNet) : WideNet :=
  if acceptStrong S m p then p else m

/-- Run `k` rounds from step index `i`; at step `i` the proposal `proposer i m` may depend
arbitrarily on the index and the current model (adaptive / adversarial generators). -/
def runStrong (S : StrongSpec) (proposer : Nat → WideNet → WideNet) :
    Nat → Nat → WideNet → WideNet
  | _, 0, m => m
  | i, k + 1, m => runStrong S proposer (i + 1) k (strongStep S m (proposer i m))

/-- Number of accepted proposals in a run. -/
def countStrong (S : StrongSpec) (proposer : Nat → WideNet → WideNet) :
    Nat → Nat → WideNet → Nat
  | _, 0, _ => 0
  | i, k + 1, m =>
      (if acceptStrong S m (proposer i m) then 1 else 0) +
        countStrong S proposer (i + 1) k (strongStep S m (proposer i m))

theorem strongTrace_append {n k : Nat} {a b c : WideNet} (h1 : StrongTrace S n a b)
    (h2 : StrongTrace S k b c) : StrongTrace S (n + k) a c := by
  induction h2 with
  | zero => exact h1
  | extend _ hstep ih => exact .extend (ih h1) hstep

/-- **Every run is an accepted chain**, whatever the proposer. -/
theorem runStrong_trace (proposer : Nat → WideNet → WideNet) (k i : Nat) (m : WideNet) :
    StrongTrace S (countStrong S proposer i k m) m (runStrong S proposer i k m) := by
  induction k generalizing i m with
  | zero => exact .zero m
  | succ k ih =>
    simp only [countStrong, runStrong]
    by_cases hacc : acceptStrong S m (proposer i m) = true
    · have h1 : StrongTrace S 1 m (proposer i m) := .extend (.zero m) hacc
      have e : strongStep S m (proposer i m) = proposer i m := by simp [strongStep, hacc]
      rw [e, if_pos hacc]
      exact strongTrace_append h1 (ih (i + 1) (proposer i m))
    · have := ih (i + 1) (strongStep S m (proposer i m))
      simp only [strongStep, hacc] at this ⊢
      simpa using this

/-- **Finite improvement bound.** Any run, under any proposal schedule and any number of
rounds, accepts at most `loss m` modifications. -/
theorem countStrong_le_loss (proposer : Nat → WideNet → WideNet) (k i : Nat) (m : WideNet) :
    countStrong S proposer i k m ≤ loss S.corpusSpec m :=
  strongTrace_length_le_loss (runStrong_trace proposer k i m)

/-- **All three guarantees survive arbitrary adversarial self-modification runs.** -/
theorem runStrong_guarantees (proposer : Nat → WideNet → WideNet) (k i : Nat) (m : WideNet) :
    let r := runStrong S proposer i k m
    (∀ x : Int, predict m x = predict S.target x → predict r x = predict S.target x) ∧
    (∀ B : Nat, ErrBound m S.target S.lo S.hi B → ErrBound r S.target S.lo S.hi B) ∧
    loss S.corpusSpec r + countStrong S proposer i k m ≤ loss S.corpusSpec m ∧
    (S.corpusSpec.valid m = true → S.corpusSpec.valid r = true) := by
  have h := runStrong_trace (S := S) proposer k i m
  exact ⟨strongTrace_noForget h, strongTrace_robust h, strongTrace_loss h,
    strongTrace_valid h⟩

/-! ## Checked examples on the three-unit target `target3` of `ProofGatedWide` -/

/-- Strong gate on the benchmark hull `[-4,4]`. -/
def specNarrow : StrongSpec := ⟨arch3, gen3, corpus9, -4, 4⟩
/-- Strong gate on `[-50,50]`. -/
def specMid : StrongSpec := ⟨arch3, gen3, corpus9, -50, 50⟩
/-- Strong gate on `[-10^9, 10^9]`. -/
def specWide : StrongSpec := ⟨arch3, gen3, corpus9, -1000000000, 1000000000⟩

theorem specNarrow_corpusSpec : specNarrow.corpusSpec = spec3 := spec3_eq.symm

/-- Worst-case errors of the original growth chain against `gen3` (which computes
`target3` exactly) on the three intervals. -/
theorem growth_chain_errors :
    (maxAbsErr gen0 gen3 (-4) 4, maxAbsErr gen1 gen3 (-4) 4, maxAbsErr gen2 gen3 (-4) 4,
      maxAbsErr gen3 gen3 (-4) 4) = (5, 5, 4, 0) ∧
    (maxAbsErr gen0 gen3 (-50) 50, maxAbsErr gen1 gen3 (-50) 50) = (51, 96) ∧
    (maxAbsErr gen0 gen3 (-1000000000) 1000000000,
      maxAbsErr gen1 gen3 (-1000000000) 1000000000) = (1000000001, 1999999996) := by
  decide

/-- The original 3-generation growth chain passes the strong gate on `[-4,4]`. -/
theorem growth_chain_narrow : StrongTrace specNarrow 3 gen0 gen3 :=
  .extend (.extend (.extend (.zero gen0)
    (show acceptStrong specNarrow gen0 gen1 = true by decide))
    (show acceptStrong specNarrow gen1 gen2 = true by decide))
    (show acceptStrong specNarrow gen2 gen3 = true by decide)

/-- On `[-50,50]` its first step is rejected: adding `relu (2x+1)` alone raises the worst
error from `51` to `96`. The extracted witness is `x = 50`. -/
theorem growth_step1_rejected_mid :
    acceptNF arch3 gen3 corpus9 gen0 gen1 = true ∧
      acceptStrong specMid gen0 gen1 = false ∧
      findRobustViolation gen0 gen1 gen3 (-50) 50 = some 50 := by
  decide

/-- Intermediate models of a chain that is robust on `[-10^9, 10^9]`. -/
def r1 : WideNet := ⟨[⟨-2, 0, 1⟩], 0⟩
def r2 : WideNet := ⟨[uB], 0⟩

/-- **A nontrivial 3-generation chain under the strong gate on `[-10^9, 10^9]`.** The
second step *replaces* the hidden unit (a structural modification), and the third step
grows the width from 1 to 3. The worst-case errors on `[-10^9,10^9]` are
`1000000001 ≥ 999999999 ≥ 5 ≥ 0`, and the corpus losses are `34 > 26 > 19 > 0`. -/
theorem robust_chain_wide : StrongTrace specWide 3 gen0 gen3 :=
  .extend (.extend (.extend (.zero gen0)
    (show acceptStrong specWide gen0 r1 = true by decide))
    (show acceptStrong specWide r1 r2 = true by decide))
    (show acceptStrong specWide r2 gen3 = true by decide)

theorem robust_chain_wide_values :
    (maxAbsErr gen0 gen3 (-1000000000) 1000000000, maxAbsErr r1 gen3 (-1000000000) 1000000000,
      maxAbsErr r2 gen3 (-1000000000) 1000000000,
      maxAbsErr gen3 gen3 (-1000000000) 1000000000) = (1000000001, 999999999, 5, 0) ∧
    (loss specWide.corpusSpec gen0, loss specWide.corpusSpec r1, loss specWide.corpusSpec r2,
      loss specWide.corpusSpec gen3) = (34, 26, 19, 0) := by
  decide

/-- Consequence of the chain theorems: the final model of the chain is correct at every
integer where the empty network was, and its error on `[-10^9,10^9]` is bounded by any
bound valid for `gen0`. -/
theorem robust_chain_wide_guarantee :
    ∀ B, ErrBound gen0 gen3 (-1000000000) 1000000000 B →
      ErrBound gen3 gen3 (-1000000000) 1000000000 B :=
  strongTrace_robust robust_chain_wide

/-! ### Adversarial rejections: each of A, B, C is needed -/

/-- **Only B rejects.** `blindForget` is corpus-perfect and has error `0` on `[-4,4]`,
but forgets the integer `-12`. -/
theorem blindForget_only_B :
    accept specNarrow.corpusSpec gen2 blindForget = true ∧
      robustB gen2 blindForget gen3 (-4) 4 = true ∧
      noForgetting gen2 blindForget gen3 = false ∧
      acceptStrong specNarrow gen2 blindForget = false := by
  decide

/-- **Only C rejects.** `oodCandidate` of `ProofGatedLimits` is corpus-perfect and forgets
nothing, but its worst error on `[-50,50]` is `1440` against `96` for the incumbent; the
extracted witness is `x = 50`. -/
theorem ood_only_C :
    accept specMid.corpusSpec gen2 oodCandidate = true ∧
      noForgetting gen2 oodCandidate gen3 = true ∧
      robustB gen2 oodCandidate gen3 (-50) 50 = false ∧
      findRobustViolation gen2 oodCandidate gen3 (-50) 50 = some 50 ∧
      (maxAbsErr gen2 gen3 (-50) 50, maxAbsErr oodCandidate gen3 (-50) 50) = (96, 1440) ∧
      acceptStrong specMid gen2 oodCandidate = false := by
  decide

/-- A permuted copy of the incumbent (semantically identical). -/
def gen2swap : WideNet := ⟨[uB, uA], 0⟩

/-- **Only A rejects.** A semantics-preserving rewrite trivially satisfies B and C but
makes no progress, so it is not accepted. -/
theorem noProgress_only_A :
    noForgetting gen2 gen2swap gen3 = true ∧ robustB gen2 gen2swap gen3 (-50) 50 = true ∧
      accept specMid.corpusSpec gen2 gen2swap = false ∧
      acceptStrong specMid gen2 gen2swap = false := by
  decide

/-- The final exact model is terminal for every strong gate on this target. -/
theorem gen3_strong_terminal (lo hi : Int) (c : WideNet) :
    acceptStrong ⟨arch3, gen3, corpus9, lo, hi⟩ gen3 c = false := by
  have := gen3_terminal c
  simp only [acceptStrong, Bool.and_eq_false_iff]
  left; left
  rw [show (⟨arch3, gen3, corpus9, lo, hi⟩ : StrongSpec).corpusSpec = spec3 from
    spec3_eq.symm]
  exact this

end PCS.V2.ProofGatedStrongGate
