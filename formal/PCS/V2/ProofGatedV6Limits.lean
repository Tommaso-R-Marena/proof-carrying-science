import PCS.V2.ProofGatedStrongGate
import PCS.V2.ProofGatedNetArtifacts

/-!
# V6 limits: what the strong gate does *not* guarantee

Each result is a kernel-checked theorem about the strong gate of `ProofGatedStrongGate`.

1. **Unbounded degradation outside the certified interval** (`outside_unbounded`): a
   modification passes all three requirements (progress, universal no-forgetting, no
   increase of the worst-case error on `[0, 10^9]`), yet its error at `x = -N` is `N` for
   **every** `N`, while the incumbent's error is `1` everywhere.
2. **Local moves fail where a coordinated move succeeds** (`all_single_coordinate_moves_rejected`,
   `coordinated_move_accepted`): from the incumbent, *every* candidate obtained by changing
   exactly one integer parameter of its canonical parameter vector — to any integer
   value — is rejected, while changing two parameters together is accepted.
3. **Preserving capabilities does not preserve improvability** (`dead_end`): a strongly
   accepted modification leads to a model with nonzero loss from which **no** candidate
   in the architecture is accepted, although its predecessor had an accepted successor;
   enlarging the architecture removes the dead end (`dead_end_escaped_by_width`).
4. **Interval mismatch** (`interval_mismatch`): a step accepted on `[-4,4]` almost doubles
   the worst-case error on `[-10^9, 10^9]`.

(Exponential certificate size: `ProofGatedDeepCertGen.sawNet_cert_length`. Arithmetic
configuration mismatch: `ProofGatedInterpreter.int64_mismatch`.)

These are statements about a fixed finite corpus, a fixed target network and a fixed
interval. They are mathematical non-regression facts; they say nothing about scientific
truth, real-world safety or recursive intelligence.
-/

namespace PCS.V2.ProofGatedV6Limits

open PCS.V2.ProofGatedSelfImprovement (relu)
open PCS.V2.ProofGatedGeneric
open PCS.V2.ProofGatedWide
open PCS.V2.ProofGatedRobust
open PCS.V2.ProofGatedStrongGate
open PCS.V2.ProofGatedNetArtifacts (toInts ofInts ofInts_toInts)

/-! ## 1. Unbounded degradation outside the interval -/

def zeroNet : WideNet := ⟨[], 0⟩
def constOne : WideNet := ⟨[], 1⟩
/-- `x ↦ 1 - relu (1 - x)`: equals `0` at `0`, `1` for `x ≥ 1`, and `x` for `x ≤ 0`. -/
def bentNet : WideNet := ⟨[⟨-1, 1, -1⟩], 1⟩

def specOutside : StrongSpec := ⟨⟨1, 1⟩, zeroNet, [0], 0, 1000000000⟩

theorem outside_accepted : acceptStrong specOutside constOne bentNet = true := by decide

/-- **Unbounded outside error.** The accepted candidate's error at `-N` is `N` for every
`N`, whereas the incumbent's error is `1` at every integer. -/
theorem outside_unbounded :
    acceptStrong specOutside constOne bentNet = true ∧
    (∀ x : Int, errAt constOne zeroNet x = 1) ∧
    (∀ N : Nat, errAt bentNet zeroNet (-(N : Int)) = N) := by
  refine ⟨outside_accepted, fun x => by simp [errAt, predict, constOne, zeroNet, hiddenSum], fun N => ?_⟩
  simp only [errAt, predict, bentNet, zeroNet, hiddenSum, unitOut, relu]
  rw [Int.max_eq_right (by omega)]
  omega

/-! ## 2. Local moves fail, a coordinated move succeeds -/

/-- The incumbent: one dead unit `(0, 0, 0)` and output bias `0` (computes `0`). -/
def deadUnit : WideNet := ⟨[⟨0, 0, 0⟩], 0⟩
/-- The target `relu x`. -/
def reluNet : WideNet := ⟨[⟨1, 0, 1⟩], 0⟩

def specLocal : StrongSpec := ⟨⟨1, 1⟩, reluNet, [1], -10, 10⟩

/-- Changing `w` and `out` *together* (two coordinates) is accepted. -/
theorem coordinated_move_accepted : acceptStrong specLocal deadUnit reluNet = true := by decide

theorem toInts_deadUnit : toInts deadUnit = [0, 0, 0, 0] := rfl

/-- A candidate whose function equals the incumbent's on the corpus is never accepted. -/
theorem rejected_of_same_on_corpus (S : StrongSpec) (a m : WideNet)
    (h : ∀ x ∈ S.corpus, predict m x = predict a x) : acceptStrong S a m = false := by
  cases hc : acceptStrong S a m with
  | false => rfl
  | true =>
    have hlt := (acceptStrong_sound hc).1.2.2.2.2
    have := loss_congr S.corpusSpec (m := m) (m' := a) h
    omega

/-- **Every single-coordinate move is rejected.** For every index `i` and every integer
value `v`, the network whose canonical parameter vector is that of `deadUnit` with the
`i`-th entry replaced by `v` is rejected by the strong gate. -/
theorem all_single_coordinate_moves_rejected (m : WideNet) (i : Nat) (v : Int)
    (h : toInts m = (toInts deadUnit).set i v) : acceptStrong specLocal deadUnit m = false := by
  have hm : ofInts ((toInts deadUnit).set i v) = some m := by rw [← h, ofInts_toInts]
  rw [toInts_deadUnit] at hm
  match i, hm with
  | 0, hm =>
    -- output bias changed: forgetting at `x = 0` unless `v = 0`
    have : m = ⟨[⟨0, 0, 0⟩], v⟩ := by simp [ofInts, PCS.V2.ProofGatedNetArtifacts.unitsOfInts] at hm; exact hm.symm
    subst this
    cases hc : acceptStrong specLocal deadUnit ⟨[⟨0, 0, 0⟩], v⟩ with
    | false => rfl
    | true =>
      have hB := (acceptStrong_sound hc).2.1 0 (by decide)
      have hv : v = 0 := by
        simp only [predict, hiddenSum, unitOut, specLocal, reluNet, relu] at hB; omega
      subst hv
      exact absurd ((acceptStrong_irrefl specLocal deadUnit).symm.trans hc) Bool.false_ne_true
  | 1, hm =>
    have : m = ⟨[⟨v, 0, 0⟩], 0⟩ := by simp [ofInts, PCS.V2.ProofGatedNetArtifacts.unitsOfInts] at hm; exact hm.symm
    subst this
    exact rejected_of_same_on_corpus _ _ _ fun x _ => by simp [predict, hiddenSum, unitOut, deadUnit]
  | 2, hm =>
    have : m = ⟨[⟨0, v, 0⟩], 0⟩ := by simp [ofInts, PCS.V2.ProofGatedNetArtifacts.unitsOfInts] at hm; exact hm.symm
    subst this
    exact rejected_of_same_on_corpus _ _ _ fun x _ => by simp [predict, hiddenSum, unitOut, deadUnit]
  | 3, hm =>
    have : m = ⟨[⟨0, 0, v⟩], 0⟩ := by simp [ofInts, PCS.V2.ProofGatedNetArtifacts.unitsOfInts] at hm; exact hm.symm
    subst this
    exact rejected_of_same_on_corpus _ _ _ fun x _ => by
      simp [predict, hiddenSum, unitOut, deadUnit, relu]
  | n + 4, hm =>
    rw [List.set_eq_of_length_le (by simp)] at hm
    have : m = deadUnit := by simp [ofInts, PCS.V2.ProofGatedNetArtifacts.unitsOfInts] at hm; exact hm.symm
    subst this
    exact acceptStrong_irrefl _ _

/-! ## 3. Dead ends -/

/-- Target `|x| = relu x + relu (-x)`, which needs two hidden units. -/
def absNet : WideNet := ⟨[⟨1, 0, 1⟩, ⟨-1, 0, 1⟩], 0⟩

/-- Width at most one, parameters in `[-1, 1]`. -/
def arch11 : Arch := ⟨1, 1⟩

def specDead : StrongSpec := ⟨arch11, absNet, [-1, 1], -1, 1⟩

def params1 : List Int := [-1, 0, 1]

/-- Every network valid for `arch11` (84 of them). -/
def allNets11 : List WideNet :=
  params1.map (fun ob => ⟨[], ob⟩) ++
    params1.flatMap fun w => params1.flatMap fun b => params1.flatMap fun o =>
      params1.map fun ob => ⟨[⟨w, b, o⟩], ob⟩

theorem mem_params1 (z : Int) (h : inRange 1 z = true) : z ∈ params1 := by
  simp only [inRange, decide_eq_true_eq] at h
  simp only [params1, List.mem_cons, List.not_mem_nil, or_false]
  omega

theorem mem_allNets11 (c : WideNet) (h : valid arch11 c = true) : c ∈ allNets11 := by
  obtain ⟨hs, ob⟩ := c
  simp only [valid, arch11, width, Bool.and_eq_true, decide_eq_true_eq] at h
  obtain ⟨⟨hw, hob⟩, hus⟩ := h
  have hob' := mem_params1 ob hob
  match hs, hw, hus with
  | [], _, _ =>
    simp only [allNets11, List.mem_append, List.mem_map]
    exact Or.inl ⟨ob, hob', rfl⟩
  | [⟨w, b, o⟩], _, hus =>
    simp only [unitsOK, unitOK, Bool.and_eq_true, Bool.and_true] at hus
    simp only [allNets11, List.mem_append, List.mem_flatMap, List.mem_map]
    exact Or.inr ⟨w, mem_params1 w hus.1.1, b, mem_params1 b hus.1.2, o,
      mem_params1 o hus.2, ob, hob', rfl⟩
  | _ :: _ :: _, hw, _ => simp at hw

/-- The accepted first step `0 ↦ relu`. -/
theorem dead_end_entry : acceptStrong specDead zeroNet reluNet = true := by decide

theorem dead_end_loss : loss specDead.corpusSpec reluNet = 1 ∧
    loss specDead.corpusSpec zeroNet = 2 := by decide

theorem dead_end_finite : ∀ c ∈ allNets11, acceptStrong specDead reluNet c = false := by
  decide

/-- **Dead end.** `relu` was reached by an accepted step from `0`, still has loss `1`,
but no network whatsoever is an accepted successor. -/
theorem dead_end :
    acceptStrong specDead zeroNet reluNet = true ∧ 0 < loss specDead.corpusSpec reluNet ∧
    ∀ c : WideNet, acceptStrong specDead reluNet c = false := by
  refine ⟨dead_end_entry, by decide, fun c => ?_⟩
  by_cases hv : valid arch11 c = true
  · exact dead_end_finite c (mem_allNets11 c hv)
  · cases hc : acceptStrong specDead reluNet c with
    | false => rfl
    | true => exact absurd (acceptStrong_sound hc).1.2.1 hv

/-- Allowing width two, the target itself is an accepted successor of `relu`. -/
theorem dead_end_escaped_by_width :
    acceptStrong { specDead with arch := ⟨2, 1⟩ } reluNet absNet = true := by decide

/-! ## 4. Interval mismatch -/

/-- **Interval mismatch.** The first step of the growth chain is accepted on `[-4,4]`, but
on `[-10^9, 10^9]` it raises the worst-case error from `1000000001` to `1999999996`. -/
theorem interval_mismatch :
    acceptStrong specNarrow gen0 gen1 = true ∧
    maxAbsErr gen0 gen3 (-1000000000) 1000000000 = 1000000001 ∧
    maxAbsErr gen1 gen3 (-1000000000) 1000000000 = 1999999996 := by
  decide

end PCS.V2.ProofGatedV6Limits
