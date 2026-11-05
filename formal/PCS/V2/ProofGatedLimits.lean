import PCS.V2.ProofGatedWide

/-!
# Limits of proof-gated self-improvement: stabilization, corpus blindness, local traps

Kernel-checked *negative* and *limiting* results. They are the formal counterpart of
the statement that a certificate about a fixed finite benchmark objective does not, by
itself, certify anything else.

1. `gated_run_stabilizes` (generic): every infinite gated run — under **any** proposer
   sequence — is eventually constant, after at most `loss initial` changes. There is no
   everlasting self-improvement under a bounded natural-valued loss.
2. `accept_congr_candidate` (in `ProofGatedWide`, generic) says the gate only sees corpus
   values. Here `blind_extension_accepted` turns this into a universal construction for
   width-`n` networks: whenever `a ↦ b` is accepted, adding one extra unit that is
   inactive on the corpus is *also* accepted, while changing the prediction by
   `k * (x - c)` at every held-out `x > c`.
3. `multilayer_ood_regression`: concrete instance — an accepted, corpus-perfect update of
   a multi-unit network whose error on the *same target* at the held-out input `20`
   increases from `36` to `480`, while an alternative (`gen3`) that is exact on all of
   `Int` is accepted by the very same check.
4. `local_trap`: a model where **all 20** single-parameter `±1` edits are rejected, yet a
   three-parameter edit to a perfect model is accepted; any proposer restricted to such
   local edits is frozen there forever (`local_proposer_frozen`).

None of these results says anything about general reasoning, scientific correctness
or open-ended capability; they show precisely which inferences are *not* licensed.
-/

namespace PCS.V2.ProofGatedLimits

open PCS.V2.ProofGatedSelfImprovement (relu)
open PCS.V2.ProofGatedGeneric
open PCS.V2.ProofGatedWide

/-! ## 1. Every gated run stabilizes -/

section stabilize
variable {M : Type} {S : GateSpec M}

theorem runSched_succ (P : Nat → M → M) (k i : Nat) (m : M) :
    runSched S P i (k + 1) m =
      gatedStep S (runSched S P i k m) (P (i + k) (runSched S P i k m)) := by
  induction k generalizing i m with
  | zero => rfl
  | succ k ih =>
      show runSched S P (i + 1) (k + 1) (gatedStep S m (P i m)) = _
      rw [ih (i + 1)]
      have : i + 1 + k = i + (k + 1) := by omega
      rw [this]
      rfl

/-- A nonincreasing natural sequence is eventually constant. -/
theorem nat_antitone_stabilizes (f : Nat → Nat) (hf : ∀ k, f (k + 1) ≤ f k) :
    ∃ N, ∀ k, N ≤ k → f k = f N := by
  have key : ∀ v, ∀ g : Nat → Nat, (∀ k, g (k + 1) ≤ g k) → g 0 ≤ v →
      ∃ N, ∀ k, N ≤ k → g k = g N := by
    intro v
    induction v with
    | zero =>
        intro g hg h0
        refine ⟨0, fun k _ => ?_⟩
        have : ∀ k, g k ≤ g 0 := by
          intro k; induction k with
          | zero => exact Nat.le_refl _
          | succ k ih => exact Nat.le_trans (hg k) ih
        have := this k
        omega
    | succ v ih =>
        intro g hg h0
        have mono : ∀ j k, j ≤ k → g k ≤ g j := by
          intro j k hjk
          induction k with
          | zero => have : j = 0 := by omega
                    subst this; exact Nat.le_refl _
          | succ k ihk =>
              by_cases h : j = k + 1
              · subst h; exact Nat.le_refl _
              · exact Nat.le_trans (hg k) (ihk (by omega))
        by_cases hall : ∀ k, g k = g 0
        · exact ⟨0, fun k _ => hall k⟩
        · have ⟨j, hj⟩ : ∃ j, g j ≠ g 0 := Classical.byContradiction fun hne =>
            hall fun k => Classical.byContradiction fun hk => hne ⟨k, hk⟩
          have hlt : g j < g 0 := by have := mono 0 j (Nat.zero_le _); omega
          obtain ⟨N, hN⟩ := ih (fun k => g (j + k))
            (fun k => by simpa [Nat.add_assoc] using hg (j + k)) (by simp; omega)
          refine ⟨j + N, fun k hk => ?_⟩
          have := hN (k - j) (by omega)
          simp only at this
          rwa [show j + (k - j) = k by omega] at this
  exact key (f 0) f hf (Nat.le_refl _)

/-- **No everlasting self-improvement**: for every proposer sequence, the infinite gated
run is eventually constant. -/
theorem gated_run_stabilizes (P : Nat → M → M) (m : M) :
    ∃ N, ∀ k, N ≤ k → runSched S P 0 k m = runSched S P 0 N m := by
  obtain ⟨N, hN⟩ := nat_antitone_stabilizes (fun k => loss S (runSched S P 0 k m))
    (fun k => by
      simp only
      rw [runSched_succ]
      have := gatedStep_count (S := S) (runSched S P 0 k m) (P (0 + k) (runSched S P 0 k m))
      omega)
  refine ⟨N, fun k hk => ?_⟩
  induction k with
  | zero => have : N = 0 := by omega
            subst this; rfl
  | succ k ih =>
      by_cases hNk : N = k + 1
      · subst hNk; rfl
      · have ihk := ih (by omega)
        rw [runSched_succ]
        cases ha : accept S (runSched S P 0 k m) (P (0 + k) (runSched S P 0 k m)) with
        | false => rw [gatedStep_reject ha, ihk]
        | true =>
            exfalso
            have hd := accepted_strict_loss ha
            have e1 := hN (k + 1) hk
            have e2 := hN k (by omega)
            simp only at e1 e2
            rw [runSched_succ, gatedStep_accept ha] at e1
            omega

/-- If every proposal at `m` is rejected, a gated run never leaves `m`. -/
theorem frozen_of_all_rejected (P : Nat → M → M) (m : M)
    (h : ∀ i, accept S m (P i m) = false) (k i : Nat) : runSched S P i k m = m := by
  induction k generalizing i with
  | zero => rfl
  | succ k ih =>
      show runSched S P (i + 1) k (gatedStep S m (P i m)) = m
      rw [gatedStep_reject (h i)]
      exact ih (i + 1)

end stabilize

/-! ## 2. Corpus blindness: a universal construction for width-`n` networks -/

def addUnit (m : WideNet) (u : HiddenUnit) : WideNet := ⟨m.hidden ++ [u], m.outBias⟩

theorem predict_addUnit (m : WideNet) (u : HiddenUnit) (x : Int) :
    predict (addUnit m u) x = predict m x + unitOut u x := by
  simp only [predict, addUnit, hiddenSum_append, hiddenSum]
  omega

/-- The blind unit `⟨1, -c, k⟩` contributes `k * relu (x - c)`. -/
theorem unitOut_blind (c k x : Int) : unitOut ⟨1, -c, k⟩ x = k * relu (x - c) := by
  simp only [unitOut, Int.one_mul]
  rfl

theorem unitOut_blind_le (c k x : Int) (hx : x ≤ c) : unitOut ⟨1, -c, k⟩ x = 0 := by
  rw [unitOut_blind]
  have : relu (x - c) = 0 := by unfold relu; omega
  rw [this, Int.mul_zero]

theorem unitOut_blind_gt (c k x : Int) (hx : c < x) : unitOut ⟨1, -c, k⟩ x = k * (x - c) := by
  rw [unitOut_blind]
  have : relu (x - c) = x - c := by unfold relu; omega
  rw [this]

/-- **Corpus blindness, universally**: if `a ↦ b` is accepted, the corpus lies in
`(-∞, c]`, and `b` extended by the unit `⟨1, -c, k⟩` is still valid, then the extension
is accepted as well — yet at every held-out `x > c` its prediction differs from `b`'s
by exactly `k * (x - c)`. Thus no gate that inspects only corpus values can certify
held-out behaviour of the *same* target. -/
theorem blind_extension_accepted (A : Arch) (target : Int → Int) (corpus : List Int)
    (a b : WideNet) (c k : Int) (hcorp : ∀ x ∈ corpus, x ≤ c)
    (hacc : accept (wideSpec A target corpus) a b = true)
    (hvalid : valid A (addUnit b ⟨1, -c, k⟩) = true) :
    accept (wideSpec A target corpus) a (addUnit b ⟨1, -c, k⟩) = true ∧
    ∀ x, c < x → predict (addUnit b ⟨1, -c, k⟩) x = predict b x + k * (x - c) := by
  constructor
  · have hb : valid A b = true := accepted_valid hacc
    rw [accept_congr_candidate (wideSpec A target corpus) a (m := addUnit b ⟨1, -c, k⟩)
      (m' := b) (fun x hx => by
        show predict (addUnit b ⟨1, -c, k⟩) x = predict b x
        rw [predict_addUnit, unitOut_blind_le c k x (hcorp x hx), Int.add_zero])
      (show valid A (addUnit b ⟨1, -c, k⟩) = valid A b by rw [hvalid, hb])]
    exact hacc
  · intro x hx
    rw [predict_addUnit, unitOut_blind_gt c k x hx]

/-! ## 3. Concrete multilayer out-of-corpus regression on the same target -/

def oodCandidate : WideNet := addUnit gen3 ⟨1, -5, 32⟩

theorem multilayer_ood_regression :
    accept spec3 gen2 oodCandidate = true ∧
    loss spec3 oodCandidate = 0 ∧
    (predict gen2 20 - target3 20).natAbs = 36 ∧
    (predict oodCandidate 20 - target3 20).natAbs = 480 := by
  decide

/-- The gate accepts both the held-out-exact `gen3` and the held-out-wrong
`oodCandidate` from `gen2`: certified corpus improvement cannot separate them. -/
theorem gate_cannot_separate :
    accept spec3 gen2 gen3 = true ∧ accept spec3 gen2 oodCandidate = true ∧
    (∀ x, predict gen3 x = target3 x) ∧ predict oodCandidate 20 ≠ target3 20 :=
  ⟨wide_step3, multilayer_ood_regression.1, gen3_exact, by decide⟩

/-- The universal construction instantiated: from the accepted step `gen2 ↦ gen3` and the
corpus bound `4`, every blind extension with `|k| ≤ 32` is accepted. -/
theorem blind_extensions_of_gen3 (k : Int) (hk1 : -32 ≤ k) (hk2 : k ≤ 32) :
    accept spec3 gen2 (addUnit gen3 ⟨1, -4, k⟩) = true ∧
    ∀ x, 4 < x → predict (addUnit gen3 ⟨1, -4, k⟩) x = target3 x + k * (x - 4) := by
  have hv : valid arch3 (addUnit gen3 ⟨1, -4, k⟩) = true := by
    simp [valid, arch3, width, addUnit, gen3, uA, uB, uC, unitsOK, unitOK, inRange]
    omega
  obtain ⟨h1, h2⟩ := blind_extension_accepted arch3 target3 corpus9 gen2 gen3 4 k
    (by decide) wide_step3 hv
  exact ⟨h1, fun x hx => by rw [h2 x hx, gen3_exact]⟩

/-! ## 4. Local-search trap despite a beneficial larger edit -/

def bumpUnit (u : HiddenUnit) : List HiddenUnit :=
  [⟨u.w + 1, u.b, u.out⟩, ⟨u.w - 1, u.b, u.out⟩, ⟨u.w, u.b + 1, u.out⟩,
   ⟨u.w, u.b - 1, u.out⟩, ⟨u.w, u.b, u.out + 1⟩, ⟨u.w, u.b, u.out - 1⟩]

def bumpList : List HiddenUnit → List (List HiddenUnit)
  | [] => []
  | u :: us => (bumpUnit u).map (· :: us) ++ (bumpList us).map (u :: ·)

/-- All single-parameter `±1` edits (fixed width). -/
def neighbors (m : WideNet) : List WideNet :=
  (bumpList m.hidden).map (fun h => ⟨h, m.outBias⟩) ++
    [⟨m.hidden, m.outBias + 1⟩, ⟨m.hidden, m.outBias - 1⟩]

/-- `gen2` plus a dead unit `⟨3, -3, 0⟩`: functionally equal to `gen2` on all inputs. -/
def trapM : WideNet := ⟨[uA, uB, ⟨3, -3, 0⟩], 0⟩

theorem trapM_semantics (x : Int) : predict trapM x = predict gen2 x := by
  simp [predict, trapM, gen2, hiddenSum, unitOut]

theorem trap_all_neighbors_rejected :
    (neighbors trapM).length = 20 ∧ (neighbors trapM).all (fun c => !accept spec3 trapM c) = true := by
  decide

theorem local_trap :
    loss spec3 trapM = 6 ∧
    (∀ c ∈ neighbors trapM, accept spec3 trapM c = false) ∧
    accept spec3 trapM gen3 = true ∧ loss spec3 gen3 = 0 := by
  refine ⟨by decide, ?_, by decide, by decide⟩
  intro c hc
  have h := trap_all_neighbors_rejected.2
  rw [List.all_eq_true] at h
  simpa using h c hc

/-- Any proposer whose proposals at `trapM` are local edits is frozen there forever,
although a perfect model is one (three-parameter) accepted step away. -/
theorem local_proposer_frozen (P : Nat → WideNet → WideNet)
    (hloc : ∀ i, P i trapM ∈ neighbors trapM) (k : Nat) :
    runSched spec3 P 0 k trapM = trapM :=
  frozen_of_all_rejected P trapM (fun i => local_trap.2.1 _ (hloc i)) k 0

end PCS.V2.ProofGatedLimits
