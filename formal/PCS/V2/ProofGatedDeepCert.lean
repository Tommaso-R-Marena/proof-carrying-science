import PCS.V2.ProofGatedDeep
import PCS.V2.ProofGatedRobust

/-!
# Proof-carrying worst-case error certificates for deep one-input integer ReLU networks

For one-hidden-layer networks, `ProofGatedRobust` finds the cells of the error function
itself, from the hidden-unit breakpoints. For a `DeepNet` (`ProofGatedDeep`: any depth,
any widths, exact `Int` arithmetic) the breakpoints of later layers depend on earlier
ones and their number can grow exponentially with depth. This module therefore uses a
**proof-carrying certificate**: a strictly increasing list of integers
`L = p₀ < p₁ < … < pₙ = U`. A certificate is checked cell by cell by exact symbolic
affine propagation:

* on a cell `[p, q]` the input is `x = p + e` with `0 ≤ e ≤ q - p`; every hidden value
  is kept as a pair `(value at p, slope)` (`affv`);
* a neuron's pre-activation is then `P + e·S`. If it is `≥ 0` at both ends of the cell,
  it is `≥ 0` on the whole cell, and ReLU is the identity there. If it is `≤ 0` at both
  ends, ReLU is `0` there. A cell of width `1` has only two integer points, so it is
  always accepted, with the exact slope `relu(P+S) - relu P`. Otherwise the cell is
  rejected (`neuronStep`);
* if every neuron of both networks passes, both networks are affine on the cell
  (`cellCoeffs_spec`), and so is their difference.

Results:
* `certMaxErr_isMax`: if the certificate passes `chainOK`, the maximum of
  `|f x - t x|` over the certificate points is the **exact** maximum over all of
  `[L,U] ∩ ℤ`;
* `certErrBound_iff`: a sound and complete bound check given any valid certificate;
* `cert_exists`: every bounded interval has a valid certificate (the full enumeration),
  so the approach never fails outright;
* `cert_must_contain`: every valid certificate contains every interior point at which
  the network has nonzero second difference. So no certificate can be smaller than the
  number of such points;
* `sawtooth_all_kinks`: a checked width-2 network with `6` hidden layers and weights of
  absolute value at most `16` has nonzero second difference at **every** one of the `63`
  interior integers of `[-32,32]`. So every valid certificate is the full enumeration.
  This is an instance of exponential growth with depth, not a general theorem;
* `deepRobustCert_sound` / `deepRobustCert_complete`: a certificate-carrying robustness
  check for deep self-modifications, and the gate `acceptDeepCert` that combines it with
  the corpus gate.
-/

namespace PCS.V2.ProofGatedDeepCert

open PCS.V2.ProofGatedSelfImprovement (relu)
open PCS.V2.ProofGatedGeneric
open PCS.V2.ProofGatedDeep
open PCS.V2.ProofGatedNoForget (SecondDiffZero)
open PCS.V2.ProofGatedRobust (maxOver le_maxOver maxOver_attained maxOver_le_iff)

/-! ## Affine families of vectors -/

/-- The vector `c + e·s` (componentwise; truncated to the shorter list). -/
def affv : List Int → List Int → Int → List Int
  | c :: cs, s :: ss, e => (c + e * s) :: affv cs ss e
  | _, _, _ => []

theorem dot_affv (w c s : List Int) (e : Int) (h : c.length = s.length) :
    dot w (affv c s e) = dot w c + e * dot w s := by
  induction w generalizing c s with
  | nil => cases c <;> cases s <;> simp [dot]
  | cons x xs ih =>
    cases c with
    | nil => cases s <;> simp_all [affv, dot]
    | cons c cs =>
      cases s with
      | nil => simp at h
      | cons s ss =>
        simp only [List.length_cons, Nat.add_right_cancel_iff] at h
        simp only [affv, dot, ih cs ss h]
        rw [Int.mul_add, Int.mul_add, Int.mul_left_comm x e s]
        omega

theorem affv_zero (c s : List Int) (h : c.length = s.length) : affv c s 0 = c := by
  induction c generalizing s with
  | nil => simp [affv]
  | cons c cs ih =>
    cases s with
    | nil => simp at h
    | cons s ss =>
      simp only [List.length_cons, Nat.add_right_cancel_iff] at h
      simp [affv, ih ss h]

/-- On a segment `[0,d]`, an affine function lies between its endpoint values. -/
theorem between_of_affine (S d e : Int) (he0 : 0 ≤ e) (hed : e ≤ d) :
    (0 ≤ e * S ∧ e * S ≤ d * S) ∨ (d * S ≤ e * S ∧ e * S ≤ 0) := by
  rcases Int.le_total 0 S with hs | hs
  · left
    exact ⟨Int.mul_nonneg he0 hs, Int.mul_le_mul_of_nonneg_right hed hs⟩
  · right
    exact ⟨Int.mul_le_mul_of_nonpos_right hed hs, Int.mul_nonpos_of_nonneg_of_nonpos he0 hs⟩

/-! ## The cell checker -/

/-- One neuron on a cell of width `d`, with inputs `c + e·s`: returns the value at the left
end and the slope of its (affine) output, or `none` if ReLU may bend inside the cell. -/
def neuronStep (d : Int) (c s : List Int) (n : DNeuron) : Option (Int × Int) :=
  let P := dot n.weights c + n.bias
  let S := dot n.weights s
  let Q := P + d * S
  if 0 ≤ P ∧ 0 ≤ Q then some (P, S)
  else if P ≤ 0 ∧ Q ≤ 0 then some (0, 0)
  else if d = 1 then some (relu P, relu Q - relu P)
  else none

theorem neuronStep_spec (d : Int) (c s : List Int) (n : DNeuron) (a b : Int)
    (hlen : c.length = s.length) (h : neuronStep d c s n = some (a, b)) :
    ∀ e, 0 ≤ e → e ≤ d → relu (dot n.weights (affv c s e) + n.bias) = a + e * b := by
  intro e he0 hed
  rw [dot_affv _ _ _ _ hlen]
  unfold neuronStep at h
  simp only at h
  generalize dot n.weights c = Pc at h ⊢
  generalize dot n.weights s = S at h ⊢
  have hb := between_of_affine S d e he0 hed
  split at h
  · rename_i h1
    simp only [Option.some.injEq, Prod.mk.injEq] at h
    obtain ⟨rfl, rfl⟩ := h
    unfold relu
    rw [Int.max_eq_right (by omega)]
    omega
  · split at h
    · rename_i _ h2
      simp only [Option.some.injEq, Prod.mk.injEq] at h
      obtain ⟨rfl, rfl⟩ := h
      unfold relu
      rw [Int.max_eq_left (by omega)]
      simp
    · split at h
      · rename_i _ _ hd
        simp only [Option.some.injEq, Prod.mk.injEq] at h
        obtain ⟨rfl, rfl⟩ := h
        subst hd
        rcases (show e = 0 ∨ e = 1 by omega) with rfl | rfl
        · simp
        · simp only [Int.one_mul]
          rw [show Pc + S + n.bias = Pc + n.bias + S by omega]
          omega
      · simp at h

/-- Width-1 cells always pass. -/
theorem neuronStep_one (c s : List Int) (n : DNeuron) : (neuronStep 1 c s n).isSome := by
  unfold neuronStep
  simp only
  split
  · rfl
  · split
    · rfl
    · simp

/-- One layer on a cell. -/
def layerStep (d : Int) (c s : List Int) : List DNeuron → Option (List Int × List Int)
  | [] => some ([], [])
  | n :: ns =>
    match neuronStep d c s n, layerStep d c s ns with
    | some (a, b), some (as, bs) => some (a :: as, b :: bs)
    | _, _ => none

theorem layerStep_spec (d : Int) (c s : List Int) (hlen : c.length = s.length) :
    ∀ (L : List DNeuron) (c' s' : List Int), layerStep d c s L = some (c', s') →
      c'.length = s'.length ∧
        ∀ e, 0 ≤ e → e ≤ d → layerEval L (affv c s e) = affv c' s' e := by
  intro L
  induction L with
  | nil =>
    intro c' s' h
    simp only [layerStep, Option.some.injEq, Prod.mk.injEq] at h
    obtain ⟨rfl, rfl⟩ := h
    exact ⟨rfl, fun e _ _ => by simp [layerEval, affv]⟩
  | cons n ns ih =>
    intro c' s' h
    unfold layerStep at h
    split at h
    · rename_i a b as bs hn hns
      simp only [Option.some.injEq, Prod.mk.injEq] at h
      obtain ⟨rfl, rfl⟩ := h
      obtain ⟨hl, hev⟩ := ih as bs hns
      refine ⟨by simp [hl], fun e he0 hed => ?_⟩
      have h1 := neuronStep_spec d c s n a b hlen hn e he0 hed
      have h2 := hev e he0 hed
      simp only [layerEval, List.map_cons, affv] at h2 ⊢
      rw [h1, h2]
    · simp at h

theorem layerStep_one (c s : List Int) (L : List DNeuron) : (layerStep 1 c s L).isSome := by
  induction L with
  | nil => rfl
  | cons n ns ih =>
    unfold layerStep
    have hn := neuronStep_one c s n
    revert hn ih
    cases neuronStep 1 c s n <;> cases layerStep 1 c s ns <;> simp

/-- All hidden layers on a cell. -/
def hiddenStep (d : Int) : List (List DNeuron) → List Int → List Int →
    Option (List Int × List Int)
  | [], c, s => some (c, s)
  | L :: Ls, c, s =>
    match layerStep d c s L with
    | some (c', s') => hiddenStep d Ls c' s'
    | none => none

theorem hiddenStep_spec (d : Int) :
    ∀ (Ls : List (List DNeuron)) (c s cf sf : List Int), c.length = s.length →
      hiddenStep d Ls c s = some (cf, sf) →
      cf.length = sf.length ∧
        ∀ e, 0 ≤ e → e ≤ d → hiddenEval Ls (affv c s e) = affv cf sf e := by
  intro Ls
  induction Ls with
  | nil =>
    intro c s cf sf hlen h
    simp only [hiddenStep, Option.some.injEq, Prod.mk.injEq] at h
    obtain ⟨rfl, rfl⟩ := h
    exact ⟨hlen, fun e _ _ => by simp [hiddenEval]⟩
  | cons L Ls ih =>
    intro c s cf sf hlen h
    unfold hiddenStep at h
    split at h
    · rename_i c' s' hL
      obtain ⟨hl', hev⟩ := layerStep_spec d c s hlen L c' s' hL
      obtain ⟨hlf, hevf⟩ := ih c' s' cf sf hl' h
      refine ⟨hlf, fun e he0 hed => ?_⟩
      simp only [hiddenEval]
      rw [hev e he0 hed, hevf e he0 hed]
    · simp at h

theorem hiddenStep_one : ∀ (Ls : List (List DNeuron)) (c s : List Int),
    (hiddenStep 1 Ls c s).isSome := by
  intro Ls
  induction Ls with
  | nil => intro c s; rfl
  | cons L Ls ih =>
    intro c s
    unfold hiddenStep
    have := layerStep_one c s L
    revert this
    cases layerStep 1 c s L with
    | none => simp
    | some p => intro _; exact ih p.1 p.2

/-- Affine coefficients `(value at l, slope)` of a network on the cell `[l, l+d]`, if the
cell check passes. -/
def cellCoeffs (m : DeepNet) (l d : Int) : Option (Int × Int) :=
  match hiddenStep d m.layers [l] [1] with
  | some (cf, sf) => some (dot m.readout.weights cf + m.readout.bias, dot m.readout.weights sf)
  | none => none

/-- **The cell theorem.** A passed cell check means the network is affine on the cell. -/
theorem cellCoeffs_spec (m : DeepNet) (l d A B : Int) (h : cellCoeffs m l d = some (A, B)) :
    ∀ e, 0 ≤ e → e ≤ d → predict m (l + e) = A + e * B := by
  unfold cellCoeffs at h
  split at h
  · rename_i cf sf hh
    simp only [Option.some.injEq, Prod.mk.injEq] at h
    obtain ⟨rfl, rfl⟩ := h
    obtain ⟨hlen, hev⟩ := hiddenStep_spec d m.layers [l] [1] cf sf rfl hh
    intro e he0 hed
    have hx : [l + e] = affv [l] [1] e := by simp [affv]
    unfold predict
    rw [hx, hev e he0 hed, dot_affv _ _ _ _ hlen]
    omega
  · simp at h

/-- The executable cell check for the cell `[p, q]`. -/
def cellOK (m : DeepNet) (p q : Int) : Bool := (cellCoeffs m p (q - p)).isSome

theorem cellOK_affine (m : DeepNet) (p q : Int) (h : cellOK m p q = true) :
    ∃ A B, ∀ e, 0 ≤ e → e ≤ q - p → predict m (p + e) = A + e * B := by
  unfold cellOK at h
  cases hc : cellCoeffs m p (q - p) with
  | none => simp [hc] at h
  | some ab => exact ⟨ab.1, ab.2, cellCoeffs_spec m p (q - p) ab.1 ab.2 hc⟩

theorem cellOK_succ (m : DeepNet) (p : Int) : cellOK m p (p + 1) = true := by
  unfold cellOK cellCoeffs
  rw [show p + 1 - p = 1 by omega]
  have := hiddenStep_one m.layers [p] [1]
  revert this
  cases hiddenStep 1 m.layers [p] [1] <;> simp

/-! ## Affine pieces and absolute values -/

theorem affine_abs_le (g : Int → Int) (p q A B : Int)
    (hg : ∀ e, 0 ≤ e → e ≤ q - p → g (p + e) = A + e * B) (x : Int) (hp : p ≤ x)
    (hq : x ≤ q) : (g x).natAbs ≤ max (g p).natAbs (g q).natAbs := by
  have hx := hg (x - p) (by omega) (by omega)
  have h0 := hg 0 (Int.le_refl 0) (by omega)
  have hqq := hg (q - p) (by omega) (Int.le_refl _)
  rw [show p + (x - p) = x by omega] at hx
  rw [show p + (q - p) = q by omega] at hqq
  rw [Int.add_zero, Int.zero_mul, Int.add_zero] at h0
  have hb := between_of_affine B (q - p) (x - p) (by omega) (by omega)
  omega

theorem affine_secondDiff (g : Int → Int) (p q A B : Int)
    (hg : ∀ e, 0 ≤ e → e ≤ q - p → g (p + e) = A + e * B) (z : Int) (hp : p < z)
    (hq : z < q) : SecondDiffZero g z := by
  unfold SecondDiffZero
  have h1 := hg (z - 1 - p) (by omega) (by omega)
  have h2 := hg (z + 1 - p) (by omega) (by omega)
  have h3 := hg (z - p) (by omega) (by omega)
  rw [show p + (z - 1 - p) = z - 1 by omega] at h1
  rw [show p + (z + 1 - p) = z + 1 by omega] at h2
  rw [show p + (z - p) = z by omega] at h3
  rw [h1, h2, h3, show z - 1 - p = (z - p) - 1 by omega, show z + 1 - p = (z - p) + 1 by omega,
    Int.sub_mul, Int.add_mul, Int.one_mul]
  omega

/-! ## Certificates -/

/-- Absolute error of a deep network `f` against a deep target `t`. -/
def derr (f t : DeepNet) (x : Int) : Nat := (predict f x - predict t x).natAbs

/-- A certificate `p :: rest` is valid when it is strictly increasing and both networks
pass the cell check on every consecutive cell. -/
def chainOK (f t : DeepNet) : Int → List Int → Bool
  | _, [] => true
  | p, q :: rest => decide (p < q) && cellOK f p q && cellOK t p q && chainOK f t q rest

/-- The right end of a certificate. -/
def lastPt : Int → List Int → Int
  | p, [] => p
  | _, q :: rest => lastPt q rest

theorem chainOK_cons {f t : DeepNet} {p q : Int} {rest : List Int}
    (h : chainOK f t p (q :: rest) = true) :
    p < q ∧ cellOK f p q = true ∧ cellOK t p q = true ∧ chainOK f t q rest = true := by
  simp only [chainOK, Bool.and_eq_true, decide_eq_true_eq] at h
  exact ⟨h.1.1.1, h.1.1.2, h.1.2, h.2⟩

theorem chain_in_range (f t : DeepNet) :
    ∀ (rest : List Int) (p : Int), chainOK f t p rest = true →
      ∀ y ∈ p :: rest, p ≤ y ∧ y ≤ lastPt p rest := by
  intro rest
  induction rest with
  | nil => intro p _ y hy; simp at hy; subst hy; simp [lastPt]
  | cons q rest ih =>
    intro p h y hy
    obtain ⟨hpq, _, _, hr⟩ := chainOK_cons h
    have := ih q hr
    simp only [List.mem_cons] at hy
    rcases hy with rfl | hy
    · have := this q (by simp); simp only [lastPt]; omega
    · have := this y (List.mem_cons.mpr hy); simp only [lastPt]; omega

/-- On a passed cell the error is dominated by an endpoint. -/
theorem cell_dominates (f t : DeepNet) (p q : Int) (hf : cellOK f p q = true)
    (ht : cellOK t p q = true) (x : Int) (h1 : p ≤ x) (h2 : x ≤ q) :
    derr f t x ≤ max (derr f t p) (derr f t q) := by
  obtain ⟨Af, Bf, hAf⟩ := cellOK_affine f p q hf
  obtain ⟨At, Bt, hAt⟩ := cellOK_affine t p q ht
  apply affine_abs_le (fun x => predict f x - predict t x) p q (Af - At) (Bf - Bt) _ x h1 h2
  intro e he0 hed
  simp only
  rw [hAf e he0 hed, hAt e he0 hed, Int.mul_sub]
  omega

/-- Every point of the certified interval is dominated by a certificate point. -/
theorem chain_dominates (f t : DeepNet) :
    ∀ (rest : List Int) (p : Int), chainOK f t p rest = true →
      ∀ x, p ≤ x → x ≤ lastPt p rest → ∃ y ∈ p :: rest, derr f t x ≤ derr f t y := by
  intro rest
  induction rest with
  | nil =>
    intro p _ x h1 h2
    simp only [lastPt] at h2
    exact ⟨p, by simp, by rw [show x = p by omega]; exact Nat.le_refl _⟩
  | cons q rest ih =>
    intro p h x h1 h2
    obtain ⟨hpq, hf, ht, hr⟩ := chainOK_cons h
    by_cases hxq : x ≤ q
    · have := cell_dominates f t p q hf ht x h1 hxq
      rcases Nat.le_total (derr f t p) (derr f t q) with hle | hle
      · exact ⟨q, by simp, by omega⟩
      · exact ⟨p, by simp, by omega⟩
    · obtain ⟨y, hy, hle⟩ := ih q hr x (by omega) (by simpa [lastPt] using h2)
      exact ⟨y, List.mem_cons_of_mem _ hy, hle⟩

/-- The certified maximum error: the maximum over the certificate points. -/
def certMaxErr (f t : DeepNet) (L : Int) (rest : List Int) : Nat :=
  maxOver (derr f t) (L :: rest)

/-- **Exactness of certified maxima.** -/
theorem certMaxErr_isMax (f t : DeepNet) (L : Int) (rest : List Int)
    (h : chainOK f t L rest = true) :
    (∀ x, L ≤ x → x ≤ lastPt L rest → derr f t x ≤ certMaxErr f t L rest) ∧
      ∃ x, L ≤ x ∧ x ≤ lastPt L rest ∧ derr f t x = certMaxErr f t L rest := by
  refine ⟨fun x h1 h2 => ?_, ?_⟩
  · obtain ⟨y, hy, hle⟩ := chain_dominates f t rest L h x h1 h2
    exact Nat.le_trans hle (le_maxOver _ _ y hy)
  · obtain ⟨x, hx, hex⟩ := maxOver_attained (derr f t) L rest
    have := chain_in_range f t rest L h x hx
    exact ⟨x, this.1, this.2, hex⟩

/-- Semantic error bound for deep networks on `[L,U]`. -/
def DErrBound (f t : DeepNet) (L U : Int) (B : Nat) : Prop :=
  ∀ x, L ≤ x → x ≤ U → derr f t x ≤ B

/-- **Sound and complete bound check relative to any valid certificate.** -/
theorem certErrBound_iff (f t : DeepNet) (L : Int) (rest : List Int)
    (h : chainOK f t L rest = true) (B : Nat) :
    certMaxErr f t L rest ≤ B ↔ DErrBound f t L (lastPt L rest) B := by
  obtain ⟨hub, x, h1, h2, hx⟩ := certMaxErr_isMax f t L rest h
  constructor
  · intro hB y hy1 hy2
    exact Nat.le_trans (hub y hy1 hy2) hB
  · intro hB
    rw [← hx]
    exact hB x h1 h2

/-- The trivial certificate `L+1, …, L+n`. -/
def enumCert (L : Int) : Nat → List Int
  | 0 => []
  | n + 1 => (L + 1) :: enumCert (L + 1) n

theorem enumCert_ok (f t : DeepNet) :
    ∀ (n : Nat) (L : Int), chainOK f t L (enumCert L n) = true ∧
      lastPt L (enumCert L n) = L + n := by
  intro n
  induction n with
  | zero => intro L; simp [enumCert, chainOK, lastPt]
  | succ n ih =>
    intro L
    obtain ⟨h1, h2⟩ := ih (L + 1)
    simp only [enumCert, chainOK, lastPt, cellOK_succ, h1, h2, Bool.and_true,
      decide_eq_true_eq]
    omega

/-- **Certificates always exist** for bounded intervals. -/
theorem cert_exists (f t : DeepNet) (L U : Int) (h : L ≤ U) :
    ∃ rest, chainOK f t L rest = true ∧ lastPt L rest = U := by
  obtain ⟨h1, h2⟩ := enumCert_ok f t (U - L).toNat L
  exact ⟨_, h1, by rw [h2]; omega⟩

/-- **Lower bound on certificate size.** A valid certificate contains every interior point
at which the candidate network has nonzero second difference. -/
theorem cert_must_contain (f t : DeepNet) :
    ∀ (rest : List Int) (p : Int), chainOK f t p rest = true →
      ∀ z, p < z → z < lastPt p rest → ¬ SecondDiffZero (predict f) z → z ∈ rest := by
  intro rest
  induction rest with
  | nil => intro p _ z h1 h2; simp only [lastPt] at h2; omega
  | cons q rest ih =>
    intro p h z h1 h2 hz
    obtain ⟨hpq, hf, _, hr⟩ := chainOK_cons h
    rcases Int.lt_trichotomy z q with hzq | hzq | hzq
    · obtain ⟨A, B, hAB⟩ := cellOK_affine f p q hf
      exact absurd (affine_secondDiff (predict f) p q A B hAB z h1 hzq) hz
    · simp [hzq]
    · exact List.mem_cons_of_mem _ (ih q hr z hzq (by simpa [lastPt] using h2) hz)

/-! ## A certificate-carrying robustness gate for deep self-modification -/

/-- Robustness check for a deep self-modification `a ↦ m` against a target `t`, carrying
certificates `ca` (for `a`) and `cm` (for `m`) over the same interval. -/
def deepRobustCert (a m t : DeepNet) (L : Int) (ca cm : List Int) : Bool :=
  chainOK a t L ca && chainOK m t L cm && decide (lastPt L ca = lastPt L cm) &&
    decide (certMaxErr m t L cm ≤ certMaxErr a t L ca)

theorem deepRobustCert_sound (a m t : DeepNet) (L : Int) (ca cm : List Int)
    (h : deepRobustCert a m t L ca cm = true) :
    ∀ B, DErrBound a t L (lastPt L ca) B → DErrBound m t L (lastPt L ca) B := by
  simp only [deepRobustCert, Bool.and_eq_true, decide_eq_true_eq] at h
  obtain ⟨⟨⟨ha, hm⟩, he⟩, hle⟩ := h
  intro B hB
  rw [he]
  rw [← certErrBound_iff a t L ca ha] at hB
  exact (certErrBound_iff m t L cm hm B).mp (Nat.le_trans hle hB)

/-- Completeness relative to valid certificates: whenever the robustness property holds,
any pair of valid certificates for the same interval is accepted. -/
theorem deepRobustCert_complete (a m t : DeepNet) (L : Int) (ca cm : List Int)
    (ha : chainOK a t L ca = true) (hm : chainOK m t L cm = true)
    (he : lastPt L ca = lastPt L cm)
    (hR : ∀ B, DErrBound a t L (lastPt L ca) B → DErrBound m t L (lastPt L ca) B) :
    deepRobustCert a m t L ca cm = true := by
  simp only [deepRobustCert, ha, hm, he, Bool.true_and, decide_true, decide_eq_true_eq]
  have h1 := hR (certMaxErr a t L ca) ((certErrBound_iff a t L ca ha _).mp (Nat.le_refl _))
  rw [he] at h1
  exact (certErrBound_iff m t L cm hm _).mpr h1

/-- Corpus gate for deep networks combined with the certified robustness check. -/
def acceptDeepCert (A : DeepArch) (t : DeepNet) (corpus : List Int) (L : Int)
    (a m : DeepNet) (ca cm : List Int) : Bool :=
  accept (deepSpec A (predict t) corpus) a m && deepRobustCert a m t L ca cm

theorem acceptDeepCert_sound (A : DeepArch) (t : DeepNet) (corpus : List Int) (L : Int)
    (a m : DeepNet) (ca cm : List Int) (h : acceptDeepCert A t corpus L a m ca cm = true) :
    admissible (deepSpec A (predict t) corpus) a m ∧
      ∀ B, DErrBound a t L (lastPt L ca) B → DErrBound m t L (lastPt L ca) B := by
  simp only [acceptDeepCert, Bool.and_eq_true] at h
  exact ⟨(accept_iff_admissible _ a m).mp h.1, deepRobustCert_sound a m t L ca cm h.2⟩

/-! ## Checked instances -/

/-- A two-hidden-layer network: `|x| - 2` followed by ReLU (`dFull` of `ProofGatedDeep`).
A 5-point certificate covers `[-10^6, 10^6]`. -/
theorem dFull_cert :
    chainOK dFull dZero (-1000000) [-2, 0, 2, 1000000] = true ∧
      certMaxErr dFull dZero (-1000000) [-2, 0, 2, 1000000] = 999998 := by
  decide

/-- A cell that crosses a breakpoint of the second layer is rejected. -/
theorem dFull_bad_cert : chainOK dFull dZero (-1000000) [0, 1000000] = false := by decide

/-- Folding layer: `y ↦ (relu (y - c), relu (c - y))` applied to `y = u + v`. -/
def foldLayer (c : Int) : List DNeuron := [⟨[1, 1], -c⟩, ⟨[-1, -1], c⟩]

/-- Iterated absolute-value folds `| … ||x| - c₁| - … - cₖ|`, width 2. -/
def sawtooth (cs : List Int) : DeepNet :=
  ⟨[⟨[1], 0⟩, ⟨[-1], 0⟩] :: cs.map foldLayer, ⟨[1, 1], 0⟩⟩

/-- Six hidden layers of width two, weights and biases in `[-16, 16]`. -/
def saw6 : DeepNet := sawtooth [16, 8, 4, 2, 1]

/-- **Exponential certificate size (checked instance).** `saw6` has nonzero second
difference at all `63` interior integers of `[-32,32]`. -/
theorem sawtooth_all_kinks :
    ∀ i : Fin 63, ¬ SecondDiffZero (predict saw6) ((i : Int) - 31) := by
  unfold SecondDiffZero
  decide

/-- Hence every valid certificate for `saw6` on `[-32,32]` contains all `63` interior
integers. -/
theorem saw6_cert_contains_all (t : DeepNet) (rest : List Int)
    (h : chainOK saw6 t (-32) rest = true) (hU : lastPt (-32) rest = 32) :
    ∀ i : Fin 63, ((i : Int) - 31) ∈ rest := by
  intro i
  have hi := i.isLt
  exact cert_must_contain saw6 t rest (-32) h _ (by omega) (by rw [hU]; omega)
    (sawtooth_all_kinks i)

end PCS.V2.ProofGatedDeepCert
