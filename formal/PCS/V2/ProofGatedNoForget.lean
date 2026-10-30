import PCS.V2.ProofGatedLimits

/-!
# An exact all-integer no-forgetting checker for one-input integer ReLU networks

The proof gate of `ProofGatedGeneric` only compares models on a finite corpus, and
`ProofGatedLimits` shows that this permits regressions outside the corpus. This module
adds a decision procedure that checks **every integer**.

Inputs: an incumbent `a`, a candidate `m` and a target `t`. All three are
arbitrary-width one-hidden-layer integer ReLU networks (`WideNet`) with one input.
The candidate **forgets** at `x` when the incumbent is correct at `x`
(`predict a x = predict t x`) and the candidate is not (`predict m x ≠ predict t x`).

The checker `findForgetting a m t` does not enumerate all integers. It uses the fact
that each network is piecewise affine on `Int`:
* a hidden unit `out * relu (w*x + b)` can only bend at the at most two integers next to
  the real point `-b/w`. These are found among `q-1, q, q+1` with `q = (-b)/w`
  (`unitKinks`);
* away from these points every network has zero second difference
  (`predict_secondDiff`), so it is affine on each gap between consecutive points
  (`affine_of_secondDiff`);
* on each affine piece, the incumbent's error is either identically zero, in which case a
  forgetting point (if any) lies at one of two neighbouring integers, or it has at most one
  zero, which is computed by exact integer division (`rootFrom`).

This gives a finite list of candidate inputs (`candidates`), linear in the total number
of hidden units. The checker returns the first candidate input that is forgotten.

Main results, for **all** networks `a m t` of any width and any parameter sizes:
* `findForgetting_sound`: if the checker returns `some x`, then `x` is a real
  counterexample: `a` is correct at `x` and `m` is not;
* `noForgetting_sound`: if the checker returns `none`, then `m` is correct at every
  integer where `a` is correct;
* `noForgetting_iff`: the checker is exact (it is a decision procedure);
* `acceptNF_sound`: the corpus gate combined with the checker accepts only steps that are
  corpus improvements and lose no correct integer anywhere;
* `nfTrace_preserves`: along any chain of accepted steps, every integer that is handled
  correctly at some generation is handled correctly at all later generations.

Concrete checks with `decide`: the checker finds an out-of-corpus forgetting point
(`x = -12`) of a corpus-perfect candidate that the corpus gate accepts
(`blindForget_caught`). It accepts the exact step `gen2 ↦ gen3`. It also accepts the
corpus-perfect `oodCandidate` of `ProofGatedLimits`, which is wrong at `x = 20`
(`ood_not_forgetting`). So "no forgetting" is a *non-regression* guarantee. It does not
imply generalisation.
-/

namespace PCS.V2.ProofGatedNoForget

open PCS.V2.ProofGatedSelfImprovement (relu)
open PCS.V2.ProofGatedGeneric
open PCS.V2.ProofGatedWide
open PCS.V2.ProofGatedLimits (oodCandidate)

/-! ## Second differences and affinity -/

/-- `h` has zero second difference at `y`. -/
def SecondDiffZero (h : Int → Int) (y : Int) : Prop := h (y - 1) + h (y + 1) = 2 * h y

theorem affine_up (h : Int → Int) (a hi : Int)
    (hsd : ∀ z, a < z → z < hi → SecondDiffZero h z) :
    ∀ n : Nat, a + n ≤ hi → h (a + n) = h a + n * (h (a + 1) - h a) := by
  intro n
  induction n using Nat.strongRecOn with
  | _ n ih =>
    intro hn
    match n, ih with
    | 0, _ => simp
    | 1, _ => simp; omega
    | k + 2, ih =>
      have h1 := ih (k + 1) (by omega) (by omega)
      have h0 := ih k (by omega) (by omega)
      have hs := hsd (a + (k + 1 : Nat)) (by omega) (by omega)
      unfold SecondDiffZero at hs
      have e1 : a + ((k + 1 : Nat) : Int) - 1 = a + (k : Nat) := by omega
      have e2 : a + ((k + 1 : Nat) : Int) + 1 = a + ((k + 2 : Nat) : Int) := by omega
      rw [e1, e2] at hs
      have c1 : ((k + 1 : Nat) : Int) * (h (a + 1) - h a) =
          (k : Int) * (h (a + 1) - h a) + (h (a + 1) - h a) := by
        rw [show ((k + 1 : Nat) : Int) = (k : Int) + 1 by omega, Int.add_mul, Int.one_mul]
      have c2 : ((k + 2 : Nat) : Int) * (h (a + 1) - h a) =
          (k : Int) * (h (a + 1) - h a) + 2 * (h (a + 1) - h a) := by
        rw [show ((k + 2 : Nat) : Int) = (k : Int) + 2 by omega, Int.add_mul]
      rw [c1] at h1
      rw [c2]
      omega

theorem affine_down (h : Int → Int) (a lo : Int)
    (hsd : ∀ z, lo < z → z < a + 1 → SecondDiffZero h z) :
    ∀ n : Nat, lo ≤ a - n → h (a - n) = h a - n * (h (a + 1) - h a) := by
  intro n
  induction n using Nat.strongRecOn with
  | _ n ih =>
    intro hn
    match n, ih with
    | 0, _ => simp
    | 1, _ =>
      have hs := hsd a (by omega) (by omega)
      unfold SecondDiffZero at hs
      simp; omega
    | k + 2, ih =>
      have h1 := ih (k + 1) (by omega) (by omega)
      have h0 := ih k (by omega) (by omega)
      have hs := hsd (a - (k + 1 : Nat)) (by omega) (by omega)
      unfold SecondDiffZero at hs
      have e1 : a - ((k + 1 : Nat) : Int) + 1 = a - (k : Nat) := by omega
      have e2 : a - ((k + 1 : Nat) : Int) - 1 = a - ((k + 2 : Nat) : Int) := by omega
      rw [e1, e2] at hs
      have c1 : ((k + 1 : Nat) : Int) * (h (a + 1) - h a) =
          (k : Int) * (h (a + 1) - h a) + (h (a + 1) - h a) := by
        rw [show ((k + 1 : Nat) : Int) = (k : Int) + 1 by omega, Int.add_mul, Int.one_mul]
      have c2 : ((k + 2 : Nat) : Int) * (h (a + 1) - h a) =
          (k : Int) * (h (a + 1) - h a) + 2 * (h (a + 1) - h a) := by
        rw [show ((k + 2 : Nat) : Int) = (k : Int) + 2 by omega, Int.add_mul]
      rw [c1] at h1
      rw [c2]
      omega

/-- **Discrete affinity.** A function with zero second difference at every point strictly
inside `[lo, hi]` is affine on `[lo, hi]`, with the slope read off at any anchor pair
`a, a+1` inside the interval. -/
theorem affine_of_secondDiff (h : Int → Int) (lo hi a y : Int)
    (hsd : ∀ z, lo < z → z < hi → SecondDiffZero h z)
    (ha1 : lo ≤ a) (ha2 : a + 1 ≤ hi) (hy1 : lo ≤ y) (hy2 : y ≤ hi) :
    h y = h a + (y - a) * (h (a + 1) - h a) := by
  by_cases hya : a ≤ y
  · have := affine_up h a hi (fun z h1 h2 => hsd z (by omega) h2) (y - a).toNat
      (by omega)
    rw [show a + ((y - a).toNat : Int) = y by omega,
      show (((y - a).toNat : Nat) : Int) = y - a by omega] at this
    exact this
  · have := affine_down h a lo (fun z h1 h2 => hsd z h1 (by omega)) (a - y).toNat
      (by omega)
    rw [show a - ((a - y).toNat : Int) = y by omega,
      show (((a - y).toNat : Nat) : Int) = a - y by omega] at this
    rw [this, show y - a = -(a - y) by omega, Int.neg_mul]
    omega

theorem secondDiff_sub {f g : Int → Int} {y : Int} (hf : SecondDiffZero f y)
    (hg : SecondDiffZero g y) : SecondDiffZero (fun x => f x - g x) y := by
  unfold SecondDiffZero at *
  simp only
  omega

/-! ## Kinks of a hidden unit -/

/-- A finite superset of the integers at which the unit `out * relu (w*x + b)` can bend. -/
def unitKinks (u : HiddenUnit) : List Int :=
  if u.w = 0 then [] else [(-u.b) / u.w - 1, (-u.b) / u.w, (-u.b) / u.w + 1]

/-- All potential bend points of a list of hidden units. -/
def kinks (l : List HiddenUnit) : List Int := l.flatMap unitKinks

theorem relu_linear_nonneg (z w : Int) (h1 : 0 ≤ z - w) (h2 : 0 ≤ z) (h3 : 0 ≤ z + w) :
    relu (z - w) + relu (z + w) = 2 * relu z := by
  unfold relu
  rw [Int.max_eq_right h1, Int.max_eq_right h2, Int.max_eq_right h3]
  omega

theorem relu_linear_nonpos (z w : Int) (h1 : z - w ≤ 0) (h2 : z ≤ 0) (h3 : z + w ≤ 0) :
    relu (z - w) + relu (z + w) = 2 * relu z := by
  unfold relu
  rw [Int.max_eq_left h1, Int.max_eq_left h2, Int.max_eq_left h3]
  rfl

/-- Away from its kinks, the pre-activation does not change sign on `y-1, y, y+1`. -/
theorem relu_secondDiff_of_not_kink (w b y : Int) (hw : w ≠ 0)
    (hy : y ≠ (-b) / w - 1 ∧ y ≠ (-b) / w ∧ y ≠ (-b) / w + 1) :
    relu (w * (y - 1) + b) + relu (w * (y + 1) + b) = 2 * relu (w * y + b) := by
  have hdiv := Int.emod_add_mul_ediv (-b) w
  have hr0 := Int.emod_nonneg (-b) hw
  have hr1 := Int.emod_lt (-b) hw
  generalize (-b) % w = r at hdiv hr0 hr1
  generalize hq : (-b) / w = q at hdiv hy
  have e1 : w * (y - 1) + b = (w * y + b) - w := by rw [Int.mul_sub, Int.mul_one]; omega
  have e2 : w * (y + 1) + b = (w * y + b) + w := by rw [Int.mul_add, Int.mul_one]; omega
  rw [e1, e2]
  -- `w*y + b = w*(y - q) - r`
  have hz : w * y + b = w * (y - q) - r := by rw [Int.mul_sub]; omega
  rcases Int.lt_or_gt_of_ne hw with hneg | hpos
  · have hn : (w.natAbs : Int) = -w := by omega
    rw [hn] at hr1
    by_cases hk : 2 ≤ y - q
    · have := Int.mul_nonpos_of_nonpos_of_nonneg (show w ≤ 0 by omega)
        (show 0 ≤ y - q - 2 by omega)
      rw [Int.mul_sub] at this
      apply relu_linear_nonpos <;> omega
    · have hk' : y - q ≤ -2 := by omega
      have := Int.mul_nonneg_of_nonpos_of_nonpos (show w ≤ 0 by omega)
        (show y - q + 2 ≤ 0 by omega)
      rw [Int.mul_add] at this
      apply relu_linear_nonneg <;> omega
  · have hn : (w.natAbs : Int) = w := by omega
    rw [hn] at hr1
    by_cases hk : 2 ≤ y - q
    · have := Int.mul_nonneg (show 0 ≤ w by omega) (show 0 ≤ y - q - 2 by omega)
      rw [Int.mul_sub] at this
      apply relu_linear_nonneg <;> omega
    · have hk' : y - q ≤ -2 := by omega
      have := Int.mul_nonpos_of_nonneg_of_nonpos (show 0 ≤ w by omega)
        (show y - q + 2 ≤ 0 by omega)
      rw [Int.mul_add] at this
      apply relu_linear_nonpos <;> omega

theorem unitOut_secondDiff (u : HiddenUnit) (y : Int) (hy : y ∉ unitKinks u) :
    SecondDiffZero (unitOut u) y := by
  unfold SecondDiffZero unitOut
  by_cases hw : u.w = 0
  · simp [hw]; omega
  · simp only [unitKinks, hw, if_false, List.mem_cons, List.not_mem_nil, or_false,
      not_or] at hy
    have := relu_secondDiff_of_not_kink u.w u.b y hw ⟨hy.1, hy.2.1, hy.2.2⟩
    rw [← Int.mul_add, this, Int.mul_left_comm]

theorem hiddenSum_secondDiff (l : List HiddenUnit) (y : Int) (hy : y ∉ kinks l) :
    SecondDiffZero (hiddenSum l) y := by
  induction l with
  | nil => simp [SecondDiffZero, hiddenSum]
  | cons u us ih =>
    simp only [kinks, List.flatMap_cons, List.mem_append, not_or] at hy
    have h1 := unitOut_secondDiff u y hy.1
    have h2 := ih hy.2
    unfold SecondDiffZero at *
    simp only [hiddenSum]
    omega

/-- Every `WideNet` has zero second difference away from the kinks of its hidden units. -/
theorem predict_secondDiff (m : WideNet) (y : Int) (hy : y ∉ kinks m.hidden) :
    SecondDiffZero (predict m) y := by
  have := hiddenSum_secondDiff m.hidden y hy
  unfold SecondDiffZero at *
  simp only [predict]
  omega

/-! ## The checker -/

/-- Signed error of `a` against the target network `t`. -/
def gap (a t : WideNet) (x : Int) : Int := predict a x - predict t x

/-- `m` forgets at `x`: `a` was correct at `x`, `m` is not. -/
def forgets (a m t : WideNet) (x : Int) : Bool := gap a t x == 0 && gap m t x != 0

theorem forgets_iff (a m t : WideNet) (x : Int) :
    forgets a m t x = true ↔ predict a x = predict t x ∧ predict m x ≠ predict t x := by
  simp only [forgets, gap, Bool.and_eq_true, beq_iff_eq, bne_iff_ne, ne_eq]
  omega

/-- The (at most one) integer zero of the affine extension of `F` through `a, a+1`. -/
def rootFrom (F : Int → Int) (a : Int) : List Int :=
  if F (a + 1) - F a ≠ 0 ∧ F a % (F (a + 1) - F a) = 0 then
    [a - F a / (F (a + 1) - F a)]
  else []

/-- All potential bend points of the three networks, plus the anchor `0`. -/
def anchors (a m t : WideNet) : List Int := 0 :: kinks (a.hidden ++ m.hidden ++ t.hidden)

/-- The finite set of inputs examined by the checker. -/
def candidates (a m t : WideNet) : List Int :=
  (anchors a m t).flatMap fun k =>
    [k - 1, k, k + 1] ++ rootFrom (gap a t) (k - 1) ++ rootFrom (gap a t) k

/-- The all-integer no-forgetting checker: returns a forgotten input, if one exists. -/
def findForgetting (a m t : WideNet) : Option Int := (candidates a m t).find? (forgets a m t)

/-- `true` iff `m` keeps every integer on which `a` agrees with `t`. -/
def noForgetting (a m t : WideNet) : Bool := (findForgetting a m t).isNone

/-! ## Correctness -/

/-- Local step on one affine piece. -/
theorem forget_on_piece (F G : Int → Int) (a x : Int)
    (hF : F x = F a + (x - a) * (F (a + 1) - F a))
    (hG : G x = G a + (x - a) * (G (a + 1) - G a))
    (hFx : F x = 0) (hGx : G x ≠ 0) :
    (F a = 0 ∧ G a ≠ 0) ∨ (F (a + 1) = 0 ∧ G (a + 1) ≠ 0) ∨ x ∈ rootFrom F a := by
  generalize hp : F (a + 1) - F a = p at hF
  by_cases hp0 : p = 0
  · subst hp0
    rw [Int.mul_zero, Int.add_zero] at hF
    by_cases hGa : G a = 0
    · right; left
      refine ⟨by omega, ?_⟩
      intro hGa1
      rw [hGa, hGa1, Int.sub_zero, Int.mul_zero] at hG
      omega
    · left; exact ⟨by omega, hGa⟩
  · right; right
    have hFa : F a = p * (a - x) := by
      rw [Int.mul_sub, Int.mul_comm p a, Int.mul_comm p x]
      rw [Int.sub_mul] at hF
      omega
    unfold rootFrom
    rw [hp, if_pos ⟨hp0, by rw [hFa]; exact Int.mul_emod_right p (a - x)⟩, hFa,
      Int.mul_ediv_cancel_left _ hp0]
    simp only [List.mem_singleton]
    omega

theorem exists_min_above (K : List Int) (x : Int) (h : ∃ k ∈ K, x < k) :
    ∃ r ∈ K, x < r ∧ ∀ k ∈ K, x < k → r ≤ k := by
  induction K with
  | nil => simp at h
  | cons c cs ih =>
    by_cases hc : ∃ k ∈ cs, x < k
    · obtain ⟨r, hr, hxr, hmin⟩ := ih hc
      by_cases hcx : x < c ∧ c < r
      · refine ⟨c, by simp, hcx.1, ?_⟩
        intro k hk hxk
        simp only [List.mem_cons] at hk
        rcases hk with rfl | hk
        · omega
        · have := hmin k hk hxk; omega
      · refine ⟨r, by simp [hr], hxr, ?_⟩
        intro k hk hxk
        simp only [List.mem_cons] at hk
        rcases hk with rfl | hk
        · omega
        · exact hmin k hk hxk
    · obtain ⟨k, hk, hxk⟩ := h
      simp only [List.mem_cons] at hk
      rcases hk with rfl | hk
      · refine ⟨k, by simp, hxk, ?_⟩
        intro j hj hxj
        simp only [List.mem_cons] at hj
        rcases hj with rfl | hj
        · omega
        · exact absurd ⟨j, hj, hxj⟩ hc
      · exact absurd ⟨k, hk, hxk⟩ hc

theorem exists_max_below (K : List Int) (x : Int) (h : ∃ k ∈ K, k < x) :
    ∃ l ∈ K, l < x ∧ ∀ k ∈ K, k < x → k ≤ l := by
  have := exists_min_above (K.map (fun k => -k)) (-x) (by
    obtain ⟨k, hk, hkx⟩ := h
    exact ⟨-k, List.mem_map.mpr ⟨k, hk, rfl⟩, by omega⟩)
  obtain ⟨r, hr, hxr, hmin⟩ := this
  obtain ⟨l, hl, rfl⟩ := List.mem_map.mp hr
  refine ⟨l, hl, by omega, ?_⟩
  intro k hk hkx
  have := hmin (-k) (List.mem_map.mpr ⟨k, hk, rfl⟩) (by omega)
  omega

theorem gap_secondDiff (a t : WideNet) (y : Int) (ha : y ∉ kinks a.hidden)
    (ht : y ∉ kinks t.hidden) : SecondDiffZero (gap a t) y :=
  secondDiff_sub (predict_secondDiff a y ha) (predict_secondDiff t y ht)

theorem not_mem_kinks_of_not_mem_anchors (a m t : WideNet) (y : Int)
    (hy : y ∉ anchors a m t) :
    y ∉ kinks a.hidden ∧ y ∉ kinks m.hidden ∧ y ∉ kinks t.hidden := by
  simp only [anchors, kinks, List.mem_cons, List.flatMap_append, List.mem_append,
    not_or] at hy
  exact ⟨hy.2.1.1, hy.2.1.2, hy.2.2⟩

theorem mem_candidates (a m t : WideNet) (k y : Int) (hk : k ∈ anchors a m t)
    (hy : y ∈ [k - 1, k, k + 1] ++ rootFrom (gap a t) (k - 1) ++ rootFrom (gap a t) k) :
    y ∈ candidates a m t :=
  List.mem_flatMap.mpr ⟨k, hk, hy⟩

/-- **Candidate completeness.** If `m` forgets anywhere, it forgets at a candidate. -/
theorem exists_candidate_of_forgets (a m t : WideNet) (x : Int)
    (hx : forgets a m t x = true) :
    ∃ c ∈ candidates a m t, forgets a m t c = true := by
  have hx' := hx
  simp only [forgets, Bool.and_eq_true, beq_iff_eq, bne_iff_ne] at hx'
  obtain ⟨hFx, hGx⟩ := hx'
  by_cases hxK : x ∈ anchors a m t
  · exact ⟨x, mem_candidates a m t x x hxK (by simp), hx⟩
  -- every point strictly between `lo` and `hi` avoiding the anchors is a linear point
  have key : ∀ lo hi, (∀ z, lo < z → z < hi → z ∉ anchors a m t) →
      ∀ c, lo ≤ c → c + 1 ≤ hi → lo ≤ x → x ≤ hi →
      (gap a t c = 0 ∧ gap m t c ≠ 0) ∨ (gap a t (c + 1) = 0 ∧ gap m t (c + 1) ≠ 0) ∨
        x ∈ rootFrom (gap a t) c := by
    intro lo hi hfree c h1 h2 h3 h4
    have hsdF : ∀ z, lo < z → z < hi → SecondDiffZero (gap a t) z := by
      intro z hz1 hz2
      have := not_mem_kinks_of_not_mem_anchors a m t z (hfree z hz1 hz2)
      exact gap_secondDiff a t z this.1 this.2.2
    have hsdG : ∀ z, lo < z → z < hi → SecondDiffZero (gap m t) z := by
      intro z hz1 hz2
      have := not_mem_kinks_of_not_mem_anchors a m t z (hfree z hz1 hz2)
      exact gap_secondDiff m t z this.2.1 this.2.2
    exact forget_on_piece (gap a t) (gap m t) c x
      (affine_of_secondDiff _ lo hi c x hsdF h1 h2 h3 h4)
      (affine_of_secondDiff _ lo hi c x hsdG h1 h2 h3 h4) hFx hGx
  have toForgets : ∀ c, gap a t c = 0 ∧ gap m t c ≠ 0 → forgets a m t c = true := by
    intro c hc
    simp [forgets, hc.1, hc.2]
  by_cases habove : ∃ k ∈ anchors a m t, x < k
  · obtain ⟨r, hr, hxr, hmin⟩ := exists_min_above _ x habove
    have hfree : ∀ z, x - 1 < z → z < r → z ∉ anchors a m t := by
      intro z hz1 hz2 hzK
      by_cases hzx : z = x
      · exact hxK (hzx ▸ hzK)
      · have := hmin z hzK (by omega); omega
    rcases key (x - 1) r hfree (r - 1) (by omega) (by omega) (by omega) (by omega) with
      h | h | h
    · exact ⟨r - 1, mem_candidates a m t r _ hr (by simp), toForgets _ h⟩
    · exact ⟨r, mem_candidates a m t r _ hr (by simp),
        toForgets _ (by rw [show r - 1 + 1 = r by omega] at h; exact h)⟩
    · exact ⟨x, mem_candidates a m t r _ hr (by simp [h]), hx⟩
  · have hbelow : ∃ k ∈ anchors a m t, k < x := by
      refine ⟨0, by simp [anchors], ?_⟩
      have h0 : (0 : Int) ∈ anchors a m t := by simp [anchors]
      have hne : x ≠ 0 := fun h => hxK (h ▸ h0)
      have : ¬ x < 0 := fun h => habove ⟨0, h0, h⟩
      omega
    obtain ⟨l, hl, hlx, hmax⟩ := exists_max_below _ x hbelow
    have hfree : ∀ z, l < z → z < x + 1 → z ∉ anchors a m t := by
      intro z hz1 hz2 hzK
      by_cases hzx : z = x
      · exact hxK (hzx ▸ hzK)
      · have := hmax z hzK (by omega); omega
    rcases key l (x + 1) hfree l (by omega) (by omega) (by omega) (by omega) with
      h | h | h
    · exact ⟨l, mem_candidates a m t l _ hl (by simp), toForgets _ h⟩
    · exact ⟨l + 1, mem_candidates a m t l _ hl (by simp), toForgets _ h⟩
    · exact ⟨x, mem_candidates a m t l _ hl (by simp [h]), hx⟩

/-- **Sound counterexample extraction.** A returned input is a genuine forgetting point. -/
theorem findForgetting_sound (a m t : WideNet) (x : Int)
    (h : findForgetting a m t = some x) :
    predict a x = predict t x ∧ predict m x ≠ predict t x :=
  (forgets_iff a m t x).mp (List.find?_some h)

/-- **Sound acceptance.** If the checker reports no forgetting, the candidate is correct at
every integer at which the incumbent is correct. -/
theorem noForgetting_sound (a m t : WideNet) (h : noForgetting a m t = true) :
    ∀ x : Int, predict a x = predict t x → predict m x = predict t x := by
  intro x hax
  apply Classical.byContradiction
  intro hmx
  have hf : forgets a m t x = true := (forgets_iff a m t x).mpr ⟨hax, hmx⟩
  obtain ⟨c, hc, hfc⟩ := exists_candidate_of_forgets a m t x hf
  have hnone : findForgetting a m t = none := by
    simpa [noForgetting, Option.isNone_iff_eq_none] using h
  exact (List.find?_eq_none.mp hnone) c hc hfc

/-- The checker is an exact decision procedure for all-integer no-forgetting. -/
theorem noForgetting_iff (a m t : WideNet) :
    noForgetting a m t = true ↔
      ∀ x : Int, predict a x = predict t x → predict m x = predict t x := by
  refine ⟨noForgetting_sound a m t, fun h => ?_⟩
  cases hf : findForgetting a m t with
  | none => simp [noForgetting, hf]
  | some x =>
    have := findForgetting_sound a m t x hf
    exact absurd (h x this.1) this.2

/-- **Constructive counterexample extraction.** If some integer is forgotten, the checker
returns one. -/
theorem findForgetting_complete (a m t : WideNet)
    (h : ∃ x, predict a x = predict t x ∧ predict m x ≠ predict t x) :
    ∃ x, findForgetting a m t = some x := by
  cases hf : findForgetting a m t with
  | some x => exact ⟨x, rfl⟩
  | none =>
    obtain ⟨x, hx1, hx2⟩ := h
    exact absurd (noForgetting_sound a m t (by simp [noForgetting, hf]) x hx1) hx2

/-! ## The strengthened gate and chains -/

/-- Corpus gate with the target given as a network `t`, followed by the all-integer
no-forgetting check. -/
def acceptNF (A : Arch) (t : WideNet) (corpus : List Int) (a m : WideNet) : Bool :=
  accept (wideSpec A (predict t) corpus) a m && noForgetting a m t

theorem acceptNF_sound (A : Arch) (t : WideNet) (corpus : List Int) (a m : WideNet)
    (h : acceptNF A t corpus a m = true) :
    admissible (wideSpec A (predict t) corpus) a m ∧
      ∀ x : Int, predict a x = predict t x → predict m x = predict t x := by
  simp only [acceptNF, Bool.and_eq_true] at h
  exact ⟨(accept_iff_admissible _ a m).mp h.1, noForgetting_sound a m t h.2⟩

/-- Chains of `acceptNF`-accepted steps of length `n` from `a` to `b`. -/
inductive NFTrace (A : Arch) (t : WideNet) (corpus : List Int) :
    Nat → WideNet → WideNet → Prop
  | zero (a : WideNet) : NFTrace A t corpus 0 a a
  | extend {n : Nat} {a b c : WideNet} : NFTrace A t corpus n a b →
      acceptNF A t corpus b c = true → NFTrace A t corpus (n + 1) a c

/-- **No forgetting along chains.** Every integer on which the start model agrees with the
target is still handled correctly after any number of accepted steps. -/
theorem nfTrace_preserves {A : Arch} {t : WideNet} {corpus : List Int} {n : Nat}
    {a b : WideNet} (h : NFTrace A t corpus n a b) :
    ∀ x : Int, predict a x = predict t x → predict b x = predict t x := by
  induction h with
  | zero => exact fun _ hx => hx
  | extend _ hstep ih =>
    exact fun x hx => (acceptNF_sound _ _ _ _ _ hstep).2 x (ih x hx)

/-- Along chains the corpus loss strictly decreases, so a chain is at most as long as the
starting loss. -/
theorem nfTrace_loss {A : Arch} {t : WideNet} {corpus : List Int} {n : Nat}
    {a b : WideNet} (h : NFTrace A t corpus n a b) :
    loss (wideSpec A (predict t) corpus) b + n ≤ loss (wideSpec A (predict t) corpus) a := by
  induction h with
  | zero => simp
  | extend _ hstep ih =>
    have := ((acceptNF_sound _ _ _ _ _ hstep).1).2.2.2.2
    omega

/-! ## Checked fixtures on the three-unit target of `ProofGatedWide` -/

/-- `gen3` is a network representation of `target3`. -/
theorem target3_net (x : Int) : target3 x = predict gen3 x := (gen3_exact x).symm

theorem spec3_eq : spec3 = wideSpec arch3 (predict gen3) corpus9 := by
  unfold spec3
  congr 1
  funext x
  exact target3_net x

/-- A corpus-perfect candidate with a blind unit active only for `x ≤ -10`. -/
def blindForget : WideNet := ⟨[uA, uB, uC, ⟨-1, -10, 5⟩], 0⟩

/-- The corpus gate accepts it ... -/
theorem blindForget_corpus_accepted : accept spec3 gen2 blindForget = true := by decide

/-- ... but the checker extracts the forgotten input `-12` (`gen2` is correct there; the
candidate is wrong at every `x ≤ -11`). -/
theorem blindForget_caught : findForgetting gen2 blindForget gen3 = some (-12) := by decide

theorem blindForget_forgets_at_minus_12 :
    predict gen2 (-12) = target3 (-12) ∧ predict blindForget (-12) ≠ target3 (-12) := by
  decide

theorem blindForget_rejected : acceptNF arch3 gen3 corpus9 gen2 blindForget = false := by
  decide

/-- The exact step is accepted by the strengthened gate. -/
theorem gen3_acceptNF : acceptNF arch3 gen3 corpus9 gen2 gen3 = true := by decide

theorem growth_chain : NFTrace arch3 gen3 corpus9 3 gen0 gen3 :=
  .extend (.extend (.extend (.zero gen0)
    (show acceptNF arch3 gen3 corpus9 gen0 gen1 = true by decide))
    (show acceptNF arch3 gen3 corpus9 gen1 gen2 = true by decide))
    (show acceptNF arch3 gen3 corpus9 gen2 gen3 = true by decide)

/-- **Limitation.** `oodCandidate` (wrong at `x = 20`) also forgets nothing relative to
`gen2`, so the strengthened gate accepts it: no-forgetting is non-regression, not
generalisation. -/
theorem ood_not_forgetting :
    acceptNF arch3 gen3 corpus9 gen2 oodCandidate = true ∧
      predict oodCandidate 20 ≠ predict gen3 20 := by decide

end PCS.V2.ProofGatedNoForget
