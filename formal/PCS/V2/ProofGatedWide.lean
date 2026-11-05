import PCS.V2.ProofGatedGeneric
import PCS.V2.ProofGatedMultilayer

/-!
# Parameterized-width exact integer ReLU networks under the generic proof gate

`WideNet` is a one-hidden-layer integer ReLU network of **arbitrary finite width**:

  predict m x = Σ_{u ∈ m.hidden} u.out * relu (u.w * x + u.b) + m.outBias

All arithmetic is on mathematical integers (no floating point, no rounding).
An `Arch` record (a *versioned architecture bound*) fixes a maximum width and a
parameter magnitude bound; `valid` checks both.

Main results (for every architecture bound, every target, every corpus):
* the generic gate theorems of `ProofGatedGeneric` apply verbatim (`wideSpec`);
* **semantics-preserving structure transforms, valid on all integer inputs**:
  hidden-unit permutation (`predict_perm`), insertion of a zero-output unit
  (`predict_insert_dead`), pruning zero-output units (`predict_prune_dead`),
  merging two units with identical pre-activation (`predict_merge`), and positive
  rescaling (`predict_rescale`);
* the gate cannot distinguish semantically equal models (`accept_congr_*`), so it is
  invariant under the above reparameterisations;
* exact embeddings: the existing two-hidden-unit `TinyNet` embeds with identical
  predictions on all inputs and *identical* gate decisions (`accept_ofTiny`); the
  single neuron (ReLU or linear) embeds with identical predictions (`predict_ofNeuron`);
* a checked three-generation chain on networks with up to three hidden units that
  **grows the architecture** 0 → 1 → 2 → 3 units (`wide_three_generations`), with
  blocked regression, out-of-range-parameter and over-width fixtures.
-/

namespace PCS.V2.ProofGatedWide

open PCS.V2.ProofGatedSelfImprovement (relu)
open PCS.V2.ProofGatedGeneric

structure HiddenUnit where
  w : Int
  b : Int
  out : Int
  deriving Repr, DecidableEq

structure WideNet where
  hidden : List HiddenUnit
  outBias : Int
  deriving Repr, DecidableEq

def unitOut (u : HiddenUnit) (x : Int) : Int := u.out * relu (u.w * x + u.b)

def hiddenSum : List HiddenUnit → Int → Int
  | [], _ => 0
  | u :: us, x => unitOut u x + hiddenSum us x

def predict (m : WideNet) (x : Int) : Int := hiddenSum m.hidden x + m.outBias

def width (m : WideNet) : Nat := m.hidden.length

/-- Versioned architecture bound. -/
structure Arch where
  maxWidth : Nat
  bound : Nat
  deriving Repr, DecidableEq

def inRange (B : Nat) (z : Int) : Bool := decide (-(B : Int) ≤ z ∧ z ≤ (B : Int))

def unitOK (B : Nat) (u : HiddenUnit) : Bool :=
  inRange B u.w && inRange B u.b && inRange B u.out

def unitsOK (B : Nat) : List HiddenUnit → Bool
  | [] => true
  | u :: us => unitOK B u && unitsOK B us

def valid (A : Arch) (m : WideNet) : Bool :=
  decide (width m ≤ A.maxWidth) && inRange A.bound m.outBias && unitsOK A.bound m.hidden

def wideSpec (A : Arch) (target : Int → Int) (corpus : List Int) : GateSpec WideNet :=
  ⟨predict, target, corpus, valid A⟩

/-! ## Algebra of the evaluator -/

theorem hiddenSum_append (l₁ l₂ : List HiddenUnit) (x : Int) :
    hiddenSum (l₁ ++ l₂) x = hiddenSum l₁ x + hiddenSum l₂ x := by
  induction l₁ with
  | nil => simp [hiddenSum]
  | cons u us ih => simp [hiddenSum, ih, Int.add_assoc]

theorem hiddenSum_perm {l₁ l₂ : List HiddenUnit} (h : l₁.Perm l₂) (x : Int) :
    hiddenSum l₁ x = hiddenSum l₂ x := by
  induction h with
  | nil => rfl
  | cons u _ ih => simp [hiddenSum, ih]
  | swap u v l => simp only [hiddenSum]; omega
  | trans _ _ ih₁ ih₂ => exact ih₁.trans ih₂

/-- **Hidden-unit permutation** preserves the function on every integer input. -/
theorem predict_perm {m m' : WideNet} (h : m.hidden.Perm m'.hidden)
    (hb : m.outBias = m'.outBias) (x : Int) : predict m x = predict m' x := by
  simp [predict, hiddenSum_perm h x, hb]

/-- Inserting a unit with zero output weight anywhere preserves the function. -/
theorem predict_insert_dead (pre post : List HiddenUnit) (ob w b : Int) (x : Int) :
    predict ⟨pre ++ ⟨w, b, 0⟩ :: post, ob⟩ x = predict ⟨pre ++ post, ob⟩ x := by
  simp [predict, hiddenSum_append, hiddenSum, unitOut]

def isLive (u : HiddenUnit) : Bool := u.out != 0

theorem hiddenSum_filter_live (l : List HiddenUnit) (x : Int) :
    hiddenSum (l.filter isLive) x = hiddenSum l x := by
  induction l with
  | nil => rfl
  | cons u us ih =>
      by_cases hu : u.out = 0
      · have : isLive u = false := by simp [isLive, hu]
        simp [this, ih, hiddenSum, unitOut, hu]
      · have : isLive u = true := by simp [isLive, hu]
        simp [this, hiddenSum, ih]

/-- Pruning every zero-output unit preserves the function. -/
theorem predict_prune_dead (m : WideNet) (x : Int) :
    predict ⟨m.hidden.filter isLive, m.outBias⟩ x = predict m x := by
  simp [predict, hiddenSum_filter_live]

/-- Two units with identical pre-activation can be merged into one. -/
theorem predict_merge (pre post : List HiddenUnit) (ob w b o₁ o₂ : Int) (x : Int) :
    predict ⟨pre ++ ⟨w, b, o₁⟩ :: ⟨w, b, o₂⟩ :: post, ob⟩ x =
      predict ⟨pre ++ ⟨w, b, o₁ + o₂⟩ :: post, ob⟩ x := by
  simp only [predict, hiddenSum_append, hiddenSum, unitOut, Int.add_mul]
  omega

theorem relu_mul_nonneg (k z : Int) (hk : 0 ≤ k) : relu (k * z) = k * relu z := by
  unfold relu
  by_cases hz : 0 ≤ z
  · have h1 : 0 ≤ k * z := Int.mul_nonneg hk hz
    rw [Int.max_eq_right h1, Int.max_eq_right hz]
  · have hz' : z ≤ 0 := by omega
    have h1 : k * z ≤ 0 := Int.mul_nonpos_of_nonneg_of_nonpos hk hz'
    rw [Int.max_eq_left h1, Int.max_eq_left hz', Int.mul_zero]

/-- Positive rescaling symmetry: `(k w, k b, o)` computes the same as `(w, b, k o)`. -/
theorem unitOut_rescale (w b o k : Int) (hk : 0 ≤ k) (x : Int) :
    unitOut ⟨k * w, k * b, o⟩ x = unitOut ⟨w, b, k * o⟩ x := by
  simp only [unitOut]
  have : k * w * x + k * b = k * (w * x + b) := by
    rw [Int.mul_add, Int.mul_assoc]
  rw [this, relu_mul_nonneg k _ hk, ← Int.mul_assoc, Int.mul_comm o k]

theorem predict_rescale (pre post : List HiddenUnit) (ob w b o k : Int) (hk : 0 ≤ k)
    (x : Int) :
    predict ⟨pre ++ ⟨k * w, k * b, o⟩ :: post, ob⟩ x =
      predict ⟨pre ++ ⟨w, b, k * o⟩ :: post, ob⟩ x := by
  simp only [predict, hiddenSum_append, hiddenSum, unitOut_rescale w b o k hk x]

/-! ## Validity is invariant under permutation and pruning -/

theorem unitsOK_append (B : Nat) (l₁ l₂ : List HiddenUnit) :
    unitsOK B (l₁ ++ l₂) = (unitsOK B l₁ && unitsOK B l₂) := by
  induction l₁ with
  | nil => simp [unitsOK]
  | cons u us ih => simp [unitsOK, ih, Bool.and_assoc]

theorem unitsOK_perm (B : Nat) {l₁ l₂ : List HiddenUnit} (h : l₁.Perm l₂) :
    unitsOK B l₁ = unitsOK B l₂ := by
  induction h with
  | nil => rfl
  | cons u _ ih => simp [unitsOK, ih]
  | swap u v l =>
      simp only [unitsOK]
      cases unitOK B u <;> cases unitOK B v <;> rfl
  | trans _ _ ih₁ ih₂ => exact ih₁.trans ih₂

theorem valid_perm (A : Arch) {m m' : WideNet} (h : m.hidden.Perm m'.hidden)
    (hb : m.outBias = m'.outBias) : valid A m = valid A m' := by
  simp [valid, width, h.length_eq, unitsOK_perm A.bound h, hb]

/-! ## The gate cannot distinguish semantically equal models -/

section congr
variable {M : Type} (S : GateSpec M)

theorem loss_congr {m m' : M} (h : ∀ x ∈ S.corpus, S.predict m x = S.predict m' x) :
    loss S m = loss S m' := by
  unfold loss
  congr 1
  apply List.map_congr_left
  intro x hx
  rw [h x hx]

theorem correct_congr {m m' : M} (h : ∀ x ∈ S.corpus, S.predict m x = S.predict m' x)
    (x : Int) (hx : x ∈ S.corpus) : correct S m x ↔ correct S m' x := by
  simp [correct, h x hx]

/-- Replacing the **candidate** by any model with the same validity and the same
predictions on the corpus does not change the gate decision. -/
theorem accept_congr_candidate (a : M) {m m' : M}
    (h : ∀ x ∈ S.corpus, S.predict m x = S.predict m' x)
    (hv : S.valid m = S.valid m') : accept S a m = accept S a m' := by
  apply Bool.eq_iff_iff.mpr
  rw [accept_iff_admissible, accept_iff_admissible]
  unfold admissible
  rw [hv, loss_congr S h]
  constructor
  · rintro ⟨h1, h2, h3, ⟨x, hx, h4, h5⟩, h6⟩
    exact ⟨h1, h2, fun y hy hc => (correct_congr S h y hy).mp (h3 y hy hc),
      ⟨x, hx, h4, (correct_congr S h x hx).mp h5⟩, h6⟩
  · rintro ⟨h1, h2, h3, ⟨x, hx, h4, h5⟩, h6⟩
    exact ⟨h1, h2, fun y hy hc => (correct_congr S h y hy).mpr (h3 y hy hc),
      ⟨x, hx, h4, (correct_congr S h x hx).mpr h5⟩, h6⟩

/-- Replacing the **incumbent** likewise does not change the decision. -/
theorem accept_congr_incumbent (b : M) {m m' : M}
    (h : ∀ x ∈ S.corpus, S.predict m x = S.predict m' x)
    (hv : S.valid m = S.valid m') : accept S m b = accept S m' b := by
  apply Bool.eq_iff_iff.mpr
  rw [accept_iff_admissible, accept_iff_admissible]
  unfold admissible
  rw [hv, loss_congr S h]
  constructor
  · rintro ⟨h1, h2, h3, ⟨x, hx, h4, h5⟩, h6⟩
    exact ⟨h1, h2, fun y hy hc => h3 y hy ((correct_congr S h y hy).mpr hc),
      ⟨x, hx, fun hc => h4 ((correct_congr S h x hx).mpr hc), h5⟩, h6⟩
  · rintro ⟨h1, h2, h3, ⟨x, hx, h4, h5⟩, h6⟩
    exact ⟨h1, h2, fun y hy hc => h3 y hy ((correct_congr S h y hy).mp hc),
      ⟨x, hx, fun hc => h4 ((correct_congr S h x hx).mp hc), h5⟩, h6⟩

end congr

/-- Permuting the hidden units of a candidate never changes the gate decision. -/
theorem accept_perm_invariant (A : Arch) (target : Int → Int) (corpus : List Int)
    (a : WideNet) {m m' : WideNet} (h : m.hidden.Perm m'.hidden)
    (hb : m.outBias = m'.outBias) :
    accept (wideSpec A target corpus) a m = accept (wideSpec A target corpus) a m' :=
  accept_congr_candidate _ a (fun x _ => predict_perm h hb x) (valid_perm A h hb)

/-! ## Exact embeddings of the earlier models -/

section embed
open PCS.V2.ProofGatedMultilayer (TinyNet)

def ofTiny (t : TinyNet) : WideNet :=
  ⟨[⟨t.h1w, t.h1b, t.out1⟩, ⟨t.h2w, t.h2b, t.out2⟩], t.outBias⟩

theorem predict_ofTiny (t : TinyNet) (x : Int) :
    predict (ofTiny t) x = PCS.V2.ProofGatedMultilayer.predict t x := by
  simp only [predict, ofTiny, hiddenSum, unitOut, PCS.V2.ProofGatedMultilayer.predict]
  omega

/-- The architecture of the earlier two-hidden-unit model. -/
def tinyArch : Arch := ⟨2, 32⟩

theorem valid_ofTiny (t : TinyNet) :
    valid tinyArch (ofTiny t) = PCS.V2.ProofGatedMultilayer.bounded t := by
  apply Bool.eq_iff_iff.mpr
  simp only [valid, tinyArch, width, ofTiny, unitsOK, unitOK, inRange,
    PCS.V2.ProofGatedMultilayer.bounded, PCS.V2.ProofGatedMultilayer.params,
    PCS.V2.ProofGatedMultilayer.boundedParam, List.all_cons, List.all_nil,
    List.length_cons, List.length_nil, Bool.and_eq_true, decide_eq_true_eq, Bool.and_true]
  constructor <;> intro h <;> omega

/-- The earlier gate, stated generically. -/
def tinySpec : GateSpec TinyNet :=
  ⟨PCS.V2.ProofGatedMultilayer.predict, PCS.V2.ProofGatedMultilayer.target,
    PCS.V2.ProofGatedMultilayer.corpus, PCS.V2.ProofGatedMultilayer.bounded⟩

theorem tiny_preservesB (xs : List Int) (a b : TinyNet) :
    PCS.V2.ProofGatedMultilayer.preservesB xs a b = preservesB tinySpec xs a b := by
  induction xs with
  | nil => rfl
  | cons y ys ih => simp [PCS.V2.ProofGatedMultilayer.preservesB, preservesB, ih]; rfl

theorem tiny_gainsB (xs : List Int) (a b : TinyNet) :
    PCS.V2.ProofGatedMultilayer.gainsB xs a b = gainsB tinySpec xs a b := by
  induction xs with
  | nil => rfl
  | cons y ys ih => simp [PCS.V2.ProofGatedMultilayer.gainsB, gainsB, ih]; rfl

/-- Regression bridge: the earlier executable gate **is** the generic gate. -/
theorem tiny_accept_eq (a b : TinyNet) :
    PCS.V2.ProofGatedMultilayer.accept a b = accept tinySpec a b := by
  simp only [PCS.V2.ProofGatedMultilayer.accept, accept, tiny_preservesB, tiny_gainsB]
  rfl

/-- The wide gate on embedded tiny networks makes **exactly** the earlier decisions. -/
theorem accept_ofTiny (a b : TinyNet) :
    accept (wideSpec tinyArch PCS.V2.ProofGatedMultilayer.target
        PCS.V2.ProofGatedMultilayer.corpus) (ofTiny a) (ofTiny b) =
      PCS.V2.ProofGatedMultilayer.accept a b := by
  rw [tiny_accept_eq]
  apply Bool.eq_iff_iff.mpr
  rw [accept_iff_admissible, accept_iff_admissible]
  simp only [admissible, correct, loss, wideSpec, tinySpec, predict_ofTiny, valid_ofTiny]

open PCS.V2.ProofGatedSelfImprovement (Neuron) in
/-- The original single-neuron gate, stated generically (no validity constraint). -/
def neuronSpec : GateSpec Neuron :=
  ⟨PCS.V2.ProofGatedSelfImprovement.predict, PCS.V2.ProofGatedSelfImprovement.target,
    PCS.V2.ProofGatedSelfImprovement.corpus, fun _ => true⟩

open PCS.V2.ProofGatedSelfImprovement (Neuron) in
theorem neuron_preservesB (xs : List Int) (a b : Neuron) :
    PCS.V2.ProofGatedSelfImprovement.preservesB xs a b = preservesB neuronSpec xs a b := by
  induction xs with
  | nil => rfl
  | cons y ys ih =>
      simp [PCS.V2.ProofGatedSelfImprovement.preservesB, preservesB, ih]; rfl

open PCS.V2.ProofGatedSelfImprovement (Neuron) in
theorem neuron_expandsB (xs : List Int) (a b : Neuron) :
    PCS.V2.ProofGatedSelfImprovement.expandsB xs a b = gainsB neuronSpec xs a b := by
  induction xs with
  | nil => rfl
  | cons y ys ih =>
      simp [PCS.V2.ProofGatedSelfImprovement.expandsB, gainsB, ih]; rfl

open PCS.V2.ProofGatedSelfImprovement (Neuron) in
/-- Regression bridge: the original single-neuron gate **is** the generic gate. -/
theorem neuron_accept_eq (a b : Neuron) :
    PCS.V2.ProofGatedSelfImprovement.accept a b = accept neuronSpec a b := by
  simp only [PCS.V2.ProofGatedSelfImprovement.accept, accept, neuron_preservesB,
    neuron_expandsB]
  rfl

open PCS.V2.ProofGatedSelfImprovement (Neuron) in
/-- Every single neuron (ReLU *or* linear) is exactly a width-≤2 network, using
`z = relu z - relu (-z)`. -/
def ofNeuron (n : Neuron) : WideNet :=
  if n.useReLU then ⟨[⟨n.weight, n.bias, 1⟩], 0⟩
  else ⟨[⟨n.weight, n.bias, 1⟩, ⟨-n.weight, -n.bias, -1⟩], 0⟩

open PCS.V2.ProofGatedSelfImprovement (Neuron) in
theorem predict_ofNeuron (n : Neuron) (x : Int) :
    predict (ofNeuron n) x = PCS.V2.ProofGatedSelfImprovement.predict n x := by
  unfold ofNeuron PCS.V2.ProofGatedSelfImprovement.predict
  cases n.useReLU
  · simp only [predict, hiddenSum, unitOut, relu, Bool.false_eq_true, if_false]
    have : -n.weight * x + -n.bias = -(n.weight * x + n.bias) := by
      rw [Int.neg_mul]; omega
    rw [this]
    omega
  · simp [predict, hiddenSum, unitOut]

end embed

/-! ## Checked multi-generation witness that grows the architecture -/

def arch3 : Arch := ⟨8, 32⟩
def corpus9 : List Int := [-4, -3, -2, -1, 0, 1, 2, 3, 4]
def target3 (x : Int) : Int := relu (2 * x + 1) + relu (-x + 1) - 2 * relu (x - 2)
def spec3 : GateSpec WideNet := wideSpec arch3 target3 corpus9

def uA : HiddenUnit := ⟨2, 1, 1⟩
def uB : HiddenUnit := ⟨-1, 1, 1⟩
def uC : HiddenUnit := ⟨1, -2, -2⟩

def gen0 : WideNet := ⟨[], 0⟩
def gen1 : WideNet := ⟨[uA], 0⟩
def gen2 : WideNet := ⟨[uA, uB], 0⟩
def gen3 : WideNet := ⟨[uA, uB, uC], 0⟩

theorem wide_step1 : accept spec3 gen0 gen1 = true := by decide
theorem wide_step2 : accept spec3 gen1 gen2 = true := by decide
theorem wide_step3 : accept spec3 gen2 gen3 = true := by decide
theorem wide_losses : loss spec3 gen0 = 34 ∧ loss spec3 gen1 = 21 ∧
    loss spec3 gen2 = 6 ∧ loss spec3 gen3 = 0 := by decide


theorem wide_three_generations : CertifiedTrace spec3 3 gen0 gen3 :=
  .extend (.extend (.extend (.zero gen0) wide_step1) wide_step2) wide_step3

/-- `gen3` computes the target on **every** integer, not just the corpus. -/
theorem gen3_exact (x : Int) : predict gen3 x = target3 x := by
  simp only [predict, gen3, hiddenSum, unitOut, uA, uB, uC, target3, relu]
  omega

theorem gen3_terminal (c : WideNet) : accept spec3 gen3 c = false :=
  perfect_cannot_advance (S := spec3) gen3 (fun x _ => gen3_exact x) c

/-- Blocked regression: loss `1 < 6 = loss gen2`, but it breaks the previously
correct case `x = -4`, so the gate rejects it although it is "better on average". -/
def regressive : WideNet := ⟨[uA, uB, uC, ⟨-1, -3, 1⟩], 0⟩
theorem regressive_lower_loss : loss spec3 regressive = 1 ∧ loss spec3 gen2 = 6 := by decide

theorem regressive_blocked : accept spec3 gen2 regressive = false := by decide

/-- Blocked invalid parameter: semantically identical to the perfect `gen3` on all
inputs (dead unit), but a parameter is out of range. -/
def outOfRange : WideNet := ⟨[uA, uB, uC, ⟨100, 0, 0⟩], 0⟩
theorem outOfRange_semantics (x : Int) : predict outOfRange x = predict gen3 x := by
  simp [predict, outOfRange, gen3, hiddenSum, unitOut]
theorem outOfRange_blocked : accept spec3 gen2 outOfRange = false := by decide

/-- Blocked over-width candidate: perfect on all inputs but nine hidden units. -/
def overWidth : WideNet := ⟨[uA, uB, uC] ++ List.replicate 6 ⟨0, 0, 0⟩, 0⟩
theorem overWidth_blocked : accept spec3 gen2 overWidth = false := by decide

/-- The permuted perfect model is accepted exactly like the original. -/
theorem permuted_gen3_accepted : accept spec3 gen2 ⟨[uC, uA, uB], 0⟩ = true := by
  have hp : gen3.hidden.Perm [uC, uA, uB] := by
    simp only [gen3]
    exact List.perm_middle (a := uC) (l₁ := [uA, uB]) (l₂ := [])
  have := accept_perm_invariant arch3 target3 corpus9 gen2 (m := gen3)
    (m' := ⟨[uC, uA, uB], 0⟩) hp rfl
  exact this ▸ wide_step3

end PCS.V2.ProofGatedWide
