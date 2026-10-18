import PCS.V2.ProofGatedNoForget

/-!
# Proof-carrying no-forgetting: sorted-breakpoint sweep certificates

V6's certificate checker re-runs the exact all-integer no-forgetting decision procedure
`noForgetting` of `ProofGatedNoForget`. That procedure evaluates the three networks at a
candidate list of at least `9·N + 3` integers (`N` = number of hidden units with nonzero
input weight, `v6_candidates_length_ge`), each evaluation costing `Θ(N)` unit evaluations:
`Θ(N²)` work.

This module replaces it with a **proof-carrying witness** that a small checker validates
with *no network evaluation at all*.

## Mathematics

For a hidden unit `u = (w, b, out)` with `w ≠ 0` and an integer `x`, the unit is *active*
(`0 < w*x + b`) exactly on one side of an **integer split point** `splitPt u`
(`act_iff_pos`, `act_iff_neg`):

* `w > 0`: active iff `splitPt u < x`, with `splitPt u = ⌊-b/w⌋`;
* `w < 0`: active iff `x ≤ splitPt u`, with `splitPt u = ⌊(b-1)/(-w)⌋`.

When active, `out * relu (w*x + b) = (out*w)*x + out*b` is affine. Hence the error functions
`F = predict a - predict t` and `G = predict m - predict t` are *exactly* affine on every
integer interval between consecutive split points, with coefficients that change at a split
point only by the contribution of the units splitting there (`corr_le`, `corr_gt`).

## The witness and the checker

The witness (`NFCert`) is the list of all *tagged* nonconstant units of `a`, `m` and `t`
(`TU`: a unit plus its coefficients in `F` and `G`) **sorted by split point**. The checker
`checkNF a m t c`:

1. checks that the list is a permutation of the actual units (`List.isPerm`);
2. checks sortedness with one adjacent-pair pass (`sortedB`);
3. computes the coefficients at `-∞` in one pass (`initCo`);
4. sweeps left to right, updating the four affine coefficients in `O(1)` per unit, and on
   each piece decides `∀ x ∈ piece, F x = 0 → G x = 0` in `O(1)` by exact integer
   arithmetic (`localOK`, exact by `localOK_iff`).

Pieces between equal split points are empty, so the witness needs no deduplication.

## Results

* `checkNF_sound`: an accepted witness proves no-forgetting **on every integer**, whatever
  the witness contains (forged, incomplete, reordered or contradictory witnesses are
  either rejected or harmless);
* `checkNF_complete`: for every no-forgetting triple, the generated witness `genNF`
  (insertion sort; any sorting procedure would do) is accepted;
* `checkNF_iff_noForgetting`: some witness is accepted iff V6's `noForgetting` holds;
* rejection theorems for incomplete / non-permutation (`checkNF_not_perm`) and unsorted
  (`checkNF_unsorted`) witnesses, with concrete fixtures;
* cost theorems: the sweep performs exactly `N` piece updates and `N + 1` constant-time
  piece decisions (`sweep_steps`), versus at least `9N + 3` full network-pair evaluations
  for the V6 procedure (`v6_candidates_length_ge`).
-/

namespace PCS.V2.ProofGatedSweepCert

open PCS.V2.ProofGatedSelfImprovement (relu)
open PCS.V2.ProofGatedWide
open PCS.V2.ProofGatedNoForget

/-! ## Activation and split points -/

theorem unitOut_eq_ite (u : HiddenUnit) (x : Int) :
    unitOut u x = if 0 < u.w * x + u.b then u.out * u.w * x + u.out * u.b else 0 := by
  unfold unitOut relu
  split
  · rw [Int.max_eq_right (by omega), Int.mul_add, Int.mul_assoc]
  · rw [Int.max_eq_left (by omega), Int.mul_zero]

/-- The integer split point of a unit with nonzero input weight. -/
def splitPt (u : HiddenUnit) : Int :=
  if 0 < u.w then (-u.b) / u.w else (u.b - 1) / (-u.w)

theorem act_iff_pos (u : HiddenUnit) (hw : 0 < u.w) (x : Int) :
    0 < u.w * x + u.b ↔ splitPt u < x := by
  unfold splitPt
  rw [if_pos hw]
  have hdiv := Int.emod_add_mul_ediv (-u.b) u.w
  have hr0 := Int.emod_nonneg (-u.b) (show u.w ≠ 0 by omega)
  have hr1 := Int.emod_lt_of_pos (-u.b) hw
  generalize (-u.b) % u.w = r at hdiv hr0 hr1
  generalize (-u.b) / u.w = q at hdiv ⊢
  constructor
  · intro h
    apply Classical.byContradiction
    intro hx
    have := Int.mul_le_mul_of_nonneg_left (show x ≤ q by omega) (Int.le_of_lt hw)
    omega
  · intro h
    have := Int.mul_le_mul_of_nonneg_left (show q + 1 ≤ x by omega) (Int.le_of_lt hw)
    rw [Int.mul_add, Int.mul_one] at this
    omega

theorem act_iff_neg (u : HiddenUnit) (hw : u.w < 0) (x : Int) :
    0 < u.w * x + u.b ↔ x ≤ splitPt u := by
  unfold splitPt
  rw [if_neg (by omega)]
  have hv : 0 < -u.w := by omega
  have hdiv := Int.emod_add_mul_ediv (u.b - 1) (-u.w)
  have hr0 := Int.emod_nonneg (u.b - 1) (show -u.w ≠ 0 by omega)
  have hr1 := Int.emod_lt_of_pos (u.b - 1) hv
  generalize (u.b - 1) % (-u.w) = r at hdiv hr0 hr1
  generalize (u.b - 1) / (-u.w) = q at hdiv ⊢
  have hwx : u.w * x = -((-u.w) * x) := by rw [Int.neg_mul, Int.neg_neg]
  rw [hwx]
  constructor
  · intro h
    apply Classical.byContradiction
    intro hx
    have := Int.mul_le_mul_of_nonneg_left (show q + 1 ≤ x by omega) (Int.le_of_lt hv)
    rw [Int.mul_add, Int.mul_one] at this
    omega
  · intro h
    have := Int.mul_le_mul_of_nonneg_left h (Int.le_of_lt hv)
    omega

/-! ## Affine coefficient vectors -/

/-- Coefficients of the two affine forms `F x = sF*x + tF`, `G x = sG*x + tG`. -/
structure Co where
  sF : Int
  tF : Int
  sG : Int
  tG : Int
  deriving Repr, DecidableEq

instance : Add Co := ⟨fun c d => ⟨c.sF + d.sF, c.tF + d.tF, c.sG + d.sG, c.tG + d.tG⟩⟩
instance : Neg Co := ⟨fun c => ⟨-c.sF, -c.tF, -c.sG, -c.tG⟩⟩

def Co.zero : Co := ⟨0, 0, 0, 0⟩

def Co.evF (c : Co) (x : Int) : Int := c.sF * x + c.tF
def Co.evG (c : Co) (x : Int) : Int := c.sG * x + c.tG

theorem evF_add (c d : Co) (x : Int) : (c + d).evF x = c.evF x + d.evF x := by
  show (c.sF + d.sF) * x + (c.tF + d.tF) = _
  unfold Co.evF; rw [Int.add_mul]; omega

theorem evG_add (c d : Co) (x : Int) : (c + d).evG x = c.evG x + d.evG x := by
  show (c.sG + d.sG) * x + (c.tG + d.tG) = _
  unfold Co.evG; rw [Int.add_mul]; omega

theorem evF_neg (c : Co) (x : Int) : (-c).evF x = -(c.evF x) := by
  show (-c.sF) * x + (-c.tF) = _
  unfold Co.evF; rw [Int.neg_mul]; omega

theorem evG_neg (c : Co) (x : Int) : (-c).evG x = -(c.evG x) := by
  show (-c.sG) * x + (-c.tG) = _
  unfold Co.evG; rw [Int.neg_mul]; omega

theorem evF_zero (x : Int) : Co.zero.evF x = 0 := by simp [Co.evF, Co.zero]
theorem evG_zero (x : Int) : Co.zero.evG x = 0 := by simp [Co.evG, Co.zero]

/-! ## Tagged units -/

/-- A hidden unit together with its coefficient in `F` and in `G`. -/
structure TU where
  u : HiddenUnit
  cF : Int
  cG : Int
  deriving Repr, DecidableEq

/-- The affine coefficients contributed by an active tagged unit. -/
def onCo (v : TU) : Co :=
  ⟨v.cF * (v.u.out * v.u.w), v.cF * (v.u.out * v.u.b),
    v.cG * (v.u.out * v.u.w), v.cG * (v.u.out * v.u.b)⟩

def contribF (v : TU) (x : Int) : Int := v.cF * unitOut v.u x
def contribG (v : TU) (x : Int) : Int := v.cG * unitOut v.u x

theorem contribF_eq (v : TU) (x : Int) :
    contribF v x = if 0 < v.u.w * x + v.u.b then (onCo v).evF x else 0 := by
  unfold contribF Co.evF onCo
  rw [unitOut_eq_ite]
  split
  · simp only [Int.mul_add, Int.mul_assoc]
  · rw [Int.mul_zero]

theorem contribG_eq (v : TU) (x : Int) :
    contribG v x = if 0 < v.u.w * x + v.u.b then (onCo v).evG x else 0 := by
  unfold contribG Co.evG onCo
  rw [unitOut_eq_ite]
  split
  · simp only [Int.mul_add, Int.mul_assoc]
  · rw [Int.mul_zero]

/-- Activity at `x → -∞` (for `w = 0`: the constant activity). -/
def leftAct (u : HiddenUnit) : Bool := decide (u.w < 0) || (decide (u.w = 0) && decide (0 < u.b))

def leftCo (v : TU) : Co := if leftAct v.u then onCo v else Co.zero

/-- The coefficient change when the sweep passes the unit's split point. -/
def deltaCo (v : TU) : Co := if 0 < v.u.w then onCo v else -(onCo v)

/-- Correction of the actual contribution relative to the `-∞` coefficients. -/
def corrF (v : TU) (x : Int) : Int := contribF v x - (leftCo v).evF x
def corrG (v : TU) (x : Int) : Int := contribG v x - (leftCo v).evG x

theorem corr_const (v : TU) (hw : v.u.w = 0) (x : Int) : corrF v x = 0 ∧ corrG v x = 0 := by
  unfold corrF corrG
  rw [contribF_eq, contribG_eq]
  unfold leftCo leftAct
  rw [hw]
  by_cases hb : 0 < v.u.b
  · simp [hb]
  · simp [hb, evF_zero, evG_zero]

theorem corr_le (v : TU) (hw : v.u.w ≠ 0) (x : Int) (hx : x ≤ splitPt v.u) :
    corrF v x = 0 ∧ corrG v x = 0 := by
  unfold corrF corrG
  rw [contribF_eq, contribG_eq]
  unfold leftCo leftAct
  rcases Int.lt_or_gt_of_ne hw with hneg | hpos
  · have ha := (act_iff_neg v.u hneg x).mpr hx
    simp [ha, hneg]
  · have ha : ¬ 0 < v.u.w * x + v.u.b := fun h => by
      have := (act_iff_pos v.u hpos x).mp h; omega
    have h1 : ¬ v.u.w < 0 := by omega
    have h2 : ¬ v.u.w = 0 := by omega
    simp [ha, h1, h2, evF_zero, evG_zero]

theorem corr_gt (v : TU) (hw : v.u.w ≠ 0) (x : Int) (hx : splitPt v.u < x) :
    corrF v x = (deltaCo v).evF x ∧ corrG v x = (deltaCo v).evG x := by
  unfold corrF corrG deltaCo
  rw [contribF_eq, contribG_eq]
  unfold leftCo leftAct
  rcases Int.lt_or_gt_of_ne hw with hneg | hpos
  · have ha : ¬ 0 < v.u.w * x + v.u.b := fun h => by
      have := (act_iff_neg v.u hneg x).mp h; omega
    have h1 : ¬ 0 < v.u.w := by omega
    simp [ha, hneg, h1, evF_neg, evG_neg]
  · have ha := (act_iff_pos v.u hpos x).mpr hx
    have h1 : ¬ v.u.w < 0 := by omega
    have h2 : ¬ v.u.w = 0 := by omega
    simp [ha, h1, h2, hpos, evF_zero, evG_zero]

/-! ## Sums -/

def sumBy {α : Type} (f : α → Int) : List α → Int
  | [] => 0
  | a :: as => f a + sumBy f as

theorem sumBy_append {α : Type} (f : α → Int) (l₁ l₂ : List α) :
    sumBy f (l₁ ++ l₂) = sumBy f l₁ + sumBy f l₂ := by
  induction l₁ with
  | nil => simp [sumBy]
  | cons a as ih => simp only [List.cons_append, sumBy, ih]; omega

theorem sumBy_perm {α : Type} (f : α → Int) {l₁ l₂ : List α} (h : l₁.Perm l₂) :
    sumBy f l₁ = sumBy f l₂ := by
  induction h with
  | nil => rfl
  | cons a _ ih => simp only [sumBy, ih]
  | swap a b l => simp only [sumBy]; omega
  | trans _ _ ih₁ ih₂ => rw [ih₁, ih₂]

theorem sumBy_congr {α : Type} (f g : α → Int) (l : List α) (h : ∀ a ∈ l, f a = g a) :
    sumBy f l = sumBy g l := by
  induction l with
  | nil => rfl
  | cons a as ih =>
    simp only [sumBy]
    rw [h a (by simp), ih (fun b hb => h b (by simp [hb]))]

theorem sumBy_zero {α : Type} (f : α → Int) (l : List α) (h : ∀ a ∈ l, f a = 0) :
    sumBy f l = 0 := by
  rw [sumBy_congr f (fun _ => 0) l h]
  induction l with
  | nil => rfl
  | cons a as ih => simp only [sumBy]; rw [ih (fun b hb => h b (by simp [hb]))]; rfl

theorem sumBy_filter {α : Type} (f : α → Int) (p : α → Bool) (l : List α)
    (h : ∀ a ∈ l, p a = false → f a = 0) : sumBy f (l.filter p) = sumBy f l := by
  induction l with
  | nil => rfl
  | cons a as ih =>
    have ih' := ih (fun b hb => h b (by simp [hb]))
    by_cases hp : p a = true
    · simp [hp, sumBy, ih']
    · have := h a (by simp) (by simpa using hp)
      simp [hp, sumBy, ih', this]

/-- Sum of coefficient vectors. -/
def sumCo {α : Type} (f : α → Co) : List α → Co
  | [] => Co.zero
  | a :: as => f a + sumCo f as

theorem evF_sumCo {α : Type} (f : α → Co) (l : List α) (x : Int) :
    (sumCo f l).evF x = sumBy (fun a => (f a).evF x) l := by
  induction l with
  | nil => simp [sumCo, sumBy, evF_zero]
  | cons a as ih => simp only [sumCo, sumBy, evF_add, ih]

theorem evG_sumCo {α : Type} (f : α → Co) (l : List α) (x : Int) :
    (sumCo f l).evG x = sumBy (fun a => (f a).evG x) l := by
  induction l with
  | nil => simp [sumCo, sumBy, evG_zero]
  | cons a as ih => simp only [sumCo, sumBy, evG_add, ih]

/-! ## The error functions as sums of tagged units -/

def tagged (a m t : WideNet) : List TU :=
  a.hidden.map (fun u => ⟨u, 1, 0⟩) ++ m.hidden.map (fun u => ⟨u, 0, 1⟩) ++
    t.hidden.map (fun u => ⟨u, -1, -1⟩)

theorem sumBy_map_hidden (l : List HiddenUnit) (cF cG : Int) (x : Int) :
    sumBy (fun v => contribF v x) (l.map fun u => (⟨u, cF, cG⟩ : TU)) = cF * hiddenSum l x ∧
    sumBy (fun v => contribG v x) (l.map fun u => (⟨u, cF, cG⟩ : TU)) = cG * hiddenSum l x := by
  induction l with
  | nil => simp [sumBy, hiddenSum]
  | cons u us ih =>
    obtain ⟨h1, h2⟩ := ih
    simp only [contribF, contribG] at h1 h2 ⊢
    simp only [List.map_cons, sumBy, hiddenSum, h1, h2, Int.mul_add, and_self]

theorem gapF_eq (a m t : WideNet) (x : Int) :
    gap a t x = sumBy (fun v => contribF v x) (tagged a m t) + (a.outBias - t.outBias) := by
  unfold gap tagged predict
  rw [sumBy_append, sumBy_append, (sumBy_map_hidden _ _ _ x).1, (sumBy_map_hidden _ _ _ x).1,
    (sumBy_map_hidden _ _ _ x).1]
  rw [Int.one_mul, Int.zero_mul, Int.neg_one_mul]
  omega

theorem gapG_eq (a m t : WideNet) (x : Int) :
    gap m t x = sumBy (fun v => contribG v x) (tagged a m t) + (m.outBias - t.outBias) := by
  unfold gap tagged predict
  rw [sumBy_append, sumBy_append, (sumBy_map_hidden _ _ _ x).2, (sumBy_map_hidden _ _ _ x).2,
    (sumBy_map_hidden _ _ _ x).2]
  rw [Int.one_mul, Int.zero_mul, Int.neg_one_mul]
  omega

/-- The coefficients at `-∞` (including all constant units and output biases). -/
def initCo (a m t : WideNet) : Co :=
  ⟨0, a.outBias - t.outBias, 0, m.outBias - t.outBias⟩ + sumCo leftCo (tagged a m t)

/-- Nonconstant units: those with nonzero input weight. -/
def nonconst (v : TU) : Bool := v.u.w != 0

/-- The units that the sweep must pass. -/
def sweepUnits (a m t : WideNet) : List TU := (tagged a m t).filter nonconst

theorem nonconst_iff (v : TU) : nonconst v = true ↔ v.u.w ≠ 0 := by simp [nonconst]

theorem gapF_decomp (a m t : WideNet) (x : Int) :
    gap a t x = (initCo a m t).evF x + sumBy (fun v => corrF v x) (sweepUnits a m t) := by
  rw [gapF_eq a m t x, sweepUnits, sumBy_filter]
  · unfold initCo
    rw [evF_add, evF_sumCo]
    have : ∀ l : List TU, sumBy (fun v => contribF v x) l =
        sumBy (fun v => (leftCo v).evF x) l + sumBy (fun v => corrF v x) l := by
      intro l
      induction l with
      | nil => rfl
      | cons v vs ih => simp only [sumBy, ih, corrF]; omega
    rw [this]
    simp only [Co.evF]
    omega
  · intro v _ hv
    exact (corr_const v (by simpa [nonconst] using hv) x).1

theorem gapG_decomp (a m t : WideNet) (x : Int) :
    gap m t x = (initCo a m t).evG x + sumBy (fun v => corrG v x) (sweepUnits a m t) := by
  rw [gapG_eq a m t x, sweepUnits, sumBy_filter]
  · unfold initCo
    rw [evG_add, evG_sumCo]
    have : ∀ l : List TU, sumBy (fun v => contribG v x) l =
        sumBy (fun v => (leftCo v).evG x) l + sumBy (fun v => corrG v x) l := by
      intro l
      induction l with
      | nil => rfl
      | cons v vs ih => simp only [sumBy, ih, corrG]; omega
    rw [this]
    simp only [Co.evG]
    omega
  · intro v _ hv
    exact (corr_const v (by simpa [nonconst] using hv) x).2

/-! ## Exact decision on one affine piece -/

/-- `x ≥ lo` (no constraint for `lo = none`). -/
def LoOK (lo : Option Int) (x : Int) : Prop := ∀ l, lo = some l → l ≤ x

/-- `x ≤ hi` (no constraint for `hi = none`). -/
def HiOK (hi : Option Int) (x : Int) : Prop := ∀ h, hi = some h → x ≤ h

def loB (lo : Option Int) (x : Int) : Bool :=
  match lo with
  | none => true
  | some l => decide (l ≤ x)

def hiB (hi : Option Int) (x : Int) : Bool :=
  match hi with
  | none => true
  | some h => decide (x ≤ h)

theorem loB_iff (lo : Option Int) (x : Int) : loB lo x = true ↔ LoOK lo x := by
  cases lo <;> simp [loB, LoOK]

theorem hiB_iff (hi : Option Int) (x : Int) : hiB hi x = true ↔ HiOK hi x := by
  cases hi <;> simp [hiB, HiOK]

/-- **Constant-time piece decision**: on the integer piece `[lo, hi]`, does `F = 0` imply
`G = 0`, for the affine forms `F x = sF*x + tF`, `G x = sG*x + tG`? -/
def localOK (lo hi : Option Int) (c : Co) : Bool :=
  if c.sF ≠ 0 then
    if c.tF % c.sF = 0 then
      !(loB lo (-(c.tF / c.sF)) && hiB hi (-(c.tF / c.sF))) || c.evG (-(c.tF / c.sF)) == 0
    else true
  else if c.tF ≠ 0 then true
  else
    match lo, hi with
    | some l, some h =>
      if h < l then true else if h = l then c.evG l == 0 else (c.sG == 0 && c.tG == 0)
    | _, _ => c.sG == 0 && c.tG == 0

theorem root_iff (s t x : Int) (hs : s ≠ 0) :
    s * x + t = 0 ↔ t % s = 0 ∧ x = -(t / s) := by
  constructor
  · intro h
    have ht : t = s * (-x) := by rw [Int.mul_neg]; omega
    refine ⟨by rw [ht]; exact Int.mul_emod_right s (-x), ?_⟩
    rw [ht, Int.mul_ediv_cancel_left _ hs, Int.neg_neg]
  · rintro ⟨h1, rfl⟩
    have := Int.emod_add_mul_ediv t s
    rw [Int.mul_neg]
    generalize t % s = r at h1 this
    generalize s * (t / s) = q at this ⊢
    omega

theorem affine_zero_two (s t p : Int) (h1 : s * p + t = 0) (h2 : s * (p + 1) + t = 0) :
    s = 0 ∧ t = 0 := by
  rw [Int.mul_add, Int.mul_one] at h2
  have hs : s = 0 := by omega
  subst hs
  simp at h1
  exact ⟨rfl, h1⟩

theorem localOK_iff (lo hi : Option Int) (c : Co) :
    localOK lo hi c = true ↔ ∀ x, LoOK lo x → HiOK hi x → c.evF x = 0 → c.evG x = 0 := by
  unfold localOK
  by_cases hs : c.sF ≠ 0
  · rw [if_pos hs]
    by_cases hd : c.tF % c.sF = 0
    · rw [if_pos hd]
      constructor
      · intro h x hl hh hF
        have hx := ((root_iff c.sF c.tF x hs).mp hF).2
        subst hx
        rw [← loB_iff] at hl; rw [← hiB_iff] at hh
        simp only [hl, hh, Bool.and_self, Bool.not_true, Bool.false_or, beq_iff_eq] at h
        exact h
      · intro h
        by_cases hin : (loB lo (-(c.tF / c.sF)) && hiB hi (-(c.tF / c.sF))) = true
        · simp only [Bool.and_eq_true] at hin
          have := h _ ((loB_iff _ _).mp hin.1) ((hiB_iff _ _).mp hin.2)
            ((root_iff c.sF c.tF _ hs).mpr ⟨hd, rfl⟩)
          simp [this]
        · simp only [Bool.not_eq_true] at hin
          simp [hin]
    · rw [if_neg hd]
      simp only [true_iff]
      intro x _ _ hF
      exact absurd ((root_iff c.sF c.tF x hs).mp hF).1 hd
  · rw [if_neg hs]
    have hs0 : c.sF = 0 := by omega
    by_cases ht : c.tF ≠ 0
    · rw [if_pos ht]
      simp only [true_iff]
      intro x _ _ hF
      simp only [Co.evF, hs0, Int.zero_mul, Int.zero_add] at hF
      exact absurd hF ht
    · rw [if_neg ht]
      have ht0 : c.tF = 0 := by omega
      have hF0 : ∀ x, c.evF x = 0 := fun x => by simp [Co.evF, hs0, ht0]
      have hzero : (c.sG == 0 && c.tG == 0) = true ↔ ∀ x, c.evG x = 0 := by
        simp only [Bool.and_eq_true, beq_iff_eq]
        constructor
        · rintro ⟨h1, h2⟩ x; simp [Co.evG, h1, h2]
        · intro h; exact affine_zero_two c.sG c.tG 0 (h 0) (h 1)
      -- the two-point extraction used for unbounded or long pieces
      have two : ∀ p, LoOK lo p → HiOK hi (p + 1) → LoOK lo (p + 1) → HiOK hi p →
          (∀ x, LoOK lo x → HiOK hi x → c.evF x = 0 → c.evG x = 0) → ∀ x, c.evG x = 0 := by
        intro p hl hh hl1 hh0 h
        have h1 := h p hl hh0 (hF0 p)
        have h2 := h (p + 1) hl1 hh (hF0 _)
        obtain ⟨e1, e2⟩ := affine_zero_two c.sG c.tG p h1 h2
        intro x; simp [Co.evG, e1, e2]
      cases lo with
      | none =>
        cases hi with
        | none =>
          simp only
          rw [hzero]
          constructor
          · intro h x _ _ _; exact h x
          · intro h
            exact two 0 (by simp [LoOK]) (by simp [HiOK]) (by simp [LoOK]) (by simp [HiOK]) h
        | some hv =>
          simp only
          rw [hzero]
          constructor
          · intro h x _ _ _; exact h x
          · intro h
            exact two (hv - 1) (by simp [LoOK]) (by simp [HiOK]) (by simp [LoOK])
              (by simp [HiOK]; omega) h
      | some l =>
        cases hi with
        | none =>
          simp only
          rw [hzero]
          constructor
          · intro h x _ _ _; exact h x
          · intro h
            exact two l (by simp [LoOK]) (by simp [HiOK]) (by simp [LoOK]; omega)
              (by simp [HiOK]) h
        | some hv =>
          simp only
          by_cases hlt : hv < l
          · rw [if_pos hlt]
            simp only [true_iff]
            intro x hl hh _
            have := hl l rfl; have := hh hv rfl; omega
          · rw [if_neg hlt]
            by_cases heq : hv = l
            · rw [if_pos heq]
              simp only [beq_iff_eq]
              constructor
              · intro h x hl hh _
                have := hl l rfl; have := hh hv rfl
                have hx : x = l := by omega
                rw [hx]; exact h
              · intro h
                exact h l (by simp [LoOK]) (by simp [HiOK]; omega) (hF0 l)
            · rw [if_neg heq, hzero]
              constructor
              · intro h x _ _ _; exact h x
              · intro h
                exact two l (by simp [LoOK]) (by simp [HiOK]; omega) (by simp [LoOK]; omega)
                  (by simp [HiOK]; omega) h

/-! ## The generic sweep -/

/-- Left-to-right sweep over units sorted by split point, deciding a **local piece check**
`P`. Piece `i` is `[lo, splitPt vᵢ]`; passing `vᵢ` updates the coefficients by
`deltaCo vᵢ`. -/
def sweepWith (P : Option Int → Option Int → Co → Bool) : Option Int → Co → List TU → Bool
  | lo, c, [] => P lo none c
  | lo, c, v :: vs => P lo (some (splitPt v.u)) c && sweepWith P (some (splitPt v.u + 1)) (c + deltaCo v) vs

def SortedSplit (l : List TU) : Prop := l.Pairwise (fun a b => splitPt a.u ≤ splitPt b.u)

/-- `P` decides the pointwise relation `R x (F x) (G x)` exactly on every piece. -/
def PieceSpec (P : Option Int → Option Int → Co → Bool) (R : Int → Int → Int → Prop) : Prop :=
  ∀ lo hi c, P lo hi c = true ↔ ∀ x, LoOK lo x → HiOK hi x → R x (c.evF x) (c.evG x)

theorem sumCorr_zero_below (vs : List TU) (x : Int)
    (h : ∀ v ∈ vs, v.u.w ≠ 0 ∧ x ≤ splitPt v.u) :
    sumBy (fun v => corrF v x) vs = 0 ∧ sumBy (fun v => corrG v x) vs = 0 :=
  ⟨sumBy_zero _ vs (fun v hv => (corr_le v (h v hv).1 x (h v hv).2).1),
   sumBy_zero _ vs (fun v hv => (corr_le v (h v hv).1 x (h v hv).2).2)⟩

theorem below_all {v : TU} {vs : List TU} {x : Int} (hw : ∀ w ∈ v :: vs, w.u.w ≠ 0)
    (hs : ∀ w ∈ vs, splitPt v.u ≤ splitPt w.u) (hx : x ≤ splitPt v.u) :
    ∀ w ∈ v :: vs, w.u.w ≠ 0 ∧ x ≤ splitPt w.u := by
  intro w hw'
  refine ⟨hw w hw', ?_⟩
  simp only [List.mem_cons] at hw'
  rcases hw' with rfl | hw'
  · exact hx
  · have := hs w hw'; omega

/-- **Soundness of the generic sweep.** -/
theorem sweepWith_sound {P : Option Int → Option Int → Co → Bool} {R : Int → Int → Int → Prop}
    (hP : PieceSpec P R) : ∀ (vs : List TU) (lo : Option Int) (c : Co),
    sweepWith P lo c vs = true → (∀ v ∈ vs, v.u.w ≠ 0) → SortedSplit vs →
    ∀ x, LoOK lo x →
      R x (c.evF x + sumBy (fun v => corrF v x) vs) (c.evG x + sumBy (fun v => corrG v x) vs) := by
  intro vs
  induction vs with
  | nil =>
    intro lo c h _ _ x hl
    simp only [sumBy, Int.add_zero]
    exact (hP lo none c).mp h x hl (by simp [HiOK])
  | cons v vs ih =>
    intro lo c h hw hs x hl
    simp only [sweepWith, Bool.and_eq_true] at h
    simp only [SortedSplit, List.pairwise_cons] at hs
    by_cases hx : x ≤ splitPt v.u
    · have hz := sumCorr_zero_below (v :: vs) x (below_all hw hs.1 hx)
      rw [hz.1, hz.2, Int.add_zero, Int.add_zero]
      exact (hP lo _ c).mp h.1 x hl (by simp [HiOK]; exact hx)
    · have hc := corr_gt v (hw v (by simp)) x (by omega)
      have := ih (some (splitPt v.u + 1)) (c + deltaCo v) h.2
        (fun w hw' => hw w (by simp [hw'])) hs.2 x (by simp [LoOK]; omega)
      rw [evF_add, evG_add] at this
      simp only [sumBy]
      rw [hc.1, hc.2, ← Int.add_assoc, ← Int.add_assoc]
      exact this

/-- **Completeness of the generic sweep.** -/
theorem sweepWith_complete {P : Option Int → Option Int → Co → Bool} {R : Int → Int → Int → Prop}
    (hP : PieceSpec P R) : ∀ (vs : List TU) (lo : Option Int) (c : Co),
    (∀ v ∈ vs, v.u.w ≠ 0) → SortedSplit vs → (∀ v ∈ vs, LoOK lo (splitPt v.u + 1)) →
    (∀ x, LoOK lo x →
      R x (c.evF x + sumBy (fun v => corrF v x) vs) (c.evG x + sumBy (fun v => corrG v x) vs)) →
    sweepWith P lo c vs = true := by
  intro vs
  induction vs with
  | nil =>
    intro lo c _ _ _ h
    simp only [sweepWith]
    rw [hP]
    intro x hl _
    simpa [sumBy] using h x hl
  | cons v vs ih =>
    intro lo c hw hs hlo h
    simp only [SortedSplit, List.pairwise_cons] at hs
    simp only [sweepWith, Bool.and_eq_true]
    refine ⟨?_, ?_⟩
    · rw [hP]
      intro x hl hh
      have hx : x ≤ splitPt v.u := hh _ rfl
      have hz := sumCorr_zero_below (v :: vs) x (below_all hw hs.1 hx)
      have := h x hl
      rw [hz.1, hz.2, Int.add_zero, Int.add_zero] at this
      exact this
    · apply ih _ _ (fun w hw' => hw w (by simp [hw'])) hs.2
      · intro w hw'
        have := hs.1 w hw'
        simp only [LoOK, Option.some.injEq]
        intro l hl; omega
      · intro x hl
        have hx : splitPt v.u < x := by have := hl _ rfl; omega
        have hc := corr_gt v (hw v (by simp)) x hx
        have hlx : LoOK lo x := by
          intro l hl'
          have := hlo v (by simp) l hl'
          omega
        have := h x hlx
        simp only [sumBy] at this
        rw [hc.1, hc.2, ← Int.add_assoc, ← Int.add_assoc, ← evF_add, ← evG_add] at this
        exact this

/-! ## Instance 1: no-forgetting -/

def NFRel (_ f g : Int) : Prop := f = 0 → g = 0

theorem localOK_spec : PieceSpec localOK NFRel := fun lo hi c => localOK_iff lo hi c

/-- The no-forgetting sweep. -/
def sweep : Option Int → Co → List TU → Bool := sweepWith localOK

theorem sweep_sound (vs : List TU) (lo : Option Int) (c : Co)
    (h : sweep lo c vs = true) (hw : ∀ v ∈ vs, v.u.w ≠ 0) (hs : SortedSplit vs) (x : Int)
    (hl : LoOK lo x) (hF : c.evF x + sumBy (fun v => corrF v x) vs = 0) :
    c.evG x + sumBy (fun v => corrG v x) vs = 0 :=
  sweepWith_sound localOK_spec vs lo c h hw hs x hl hF

theorem sweep_complete (vs : List TU) (lo : Option Int) (c : Co)
    (hw : ∀ v ∈ vs, v.u.w ≠ 0) (hs : SortedSplit vs) (hlo : ∀ v ∈ vs, LoOK lo (splitPt v.u + 1))
    (h : ∀ x, LoOK lo x → c.evF x + sumBy (fun v => corrF v x) vs = 0 →
      c.evG x + sumBy (fun v => corrG v x) vs = 0) :
    sweep lo c vs = true :=
  sweepWith_complete localOK_spec vs lo c hw hs hlo h

/-! ## Instance 2: no-forgetting and an interval error bound in one pass -/

/-- On the piece `[lo,hi]`, clipped to `[L,U]`: `|G| ≤ B` (checked at the two clipped
endpoints, since `|G|` is convex on an affine piece). -/
def localErr (L U : Int) (B : Nat) (lo hi : Option Int) (c : Co) : Bool :=
  let l := match lo with | none => L | some l => max l L
  let h := match hi with | none => U | some h => min h U
  decide (h < l) || (decide ((c.evG l).natAbs ≤ B) && decide ((c.evG h).natAbs ≤ B))

def ErrRel (L U : Int) (B : Nat) (x _ g : Int) : Prop := L ≤ x → x ≤ U → g.natAbs ≤ B

theorem affine_between (s t l h x : Int) (hl : l ≤ x) (hh : x ≤ h) :
    (s * l + t ≤ s * x + t ∧ s * x + t ≤ s * h + t) ∨
      (s * h + t ≤ s * x + t ∧ s * x + t ≤ s * l + t) := by
  by_cases hs : 0 ≤ s
  · left
    exact ⟨by have := Int.mul_le_mul_of_nonneg_left hl hs; omega,
      by have := Int.mul_le_mul_of_nonneg_left hh hs; omega⟩
  · right
    have hs' : 0 ≤ -s := by omega
    have h1 := Int.mul_le_mul_of_nonneg_left hl hs'
    have h2 := Int.mul_le_mul_of_nonneg_left hh hs'
    rw [Int.neg_mul, Int.neg_mul] at h1 h2
    exact ⟨by omega, by omega⟩

theorem localErr_spec (L U : Int) (B : Nat) : PieceSpec (localErr L U B) (ErrRel L U B) := by
  intro lo hi c
  unfold localErr ErrRel
  generalize hl : (match lo with | none => L | some l => max l L) = l
  generalize hh : (match hi with | none => U | some h => min h U) = h
  have hlx : ∀ x, LoOK lo x → L ≤ x → l ≤ x := by
    intro x h1 h2; subst hl; cases lo with
    | none => exact h2
    | some l' => have := h1 l' rfl; simp only; omega
  have hhx : ∀ x, HiOK hi x → x ≤ U → x ≤ h := by
    intro x h1 h2; subst hh; cases hi with
    | none => exact h2
    | some h' => have := h1 h' rfl; simp only; omega
  have hl1 : L ≤ l ∧ LoOK lo l := by
    subst hl; cases lo with
    | none => exact ⟨Int.le_refl _, by simp [LoOK]⟩
    | some l' => simp only [LoOK, Option.some.injEq]; exact ⟨by omega, by intro _ e; subst e; omega⟩
  have hh1 : h ≤ U ∧ HiOK hi h := by
    subst hh; cases hi with
    | none => exact ⟨Int.le_refl _, by simp [HiOK]⟩
    | some h' => simp only [HiOK, Option.some.injEq]; exact ⟨by omega, by intro _ e; subst e; omega⟩
  simp only [Bool.or_eq_true, Bool.and_eq_true, decide_eq_true_eq]
  constructor
  · rintro (hlt | ⟨e1, e2⟩) x h1 h2 h3 h4
    · have := hlx x h1 h3; have := hhx x h2 h4; omega
    · have hb := affine_between c.sG c.tG l h x (hlx x h1 h3) (hhx x h2 h4)
      simp only [Co.evG] at e1 e2 ⊢
      omega
  · intro H
    by_cases hlt : h < l
    · exact Or.inl hlt
    · right
      have hlh : l ≤ h := by omega
      have hloh : HiOK hi l := by
        intro h' e; have := hh1.2 h' e; omega
      have hhil : LoOK lo h := by
        intro l' e; have := hl1.2 l' e; omega
      exact ⟨H l hl1.2 hloh hl1.1 (by omega), H h hhil hh1.2 (by omega) hh1.1⟩

def BothRel (L U : Int) (B : Nat) (x f g : Int) : Prop := NFRel x f g ∧ ErrRel L U B x f g

def localBoth (L U : Int) (B : Nat) (lo hi : Option Int) (c : Co) : Bool :=
  localOK lo hi c && localErr L U B lo hi c

theorem localBoth_spec (L U : Int) (B : Nat) : PieceSpec (localBoth L U B) (BothRel L U B) := by
  intro lo hi c
  unfold localBoth BothRel
  rw [Bool.and_eq_true, localOK_spec, localErr_spec]
  exact ⟨fun ⟨h1, h2⟩ x a b => ⟨h1 x a b, h2 x a b⟩,
    fun h => ⟨fun x a b => (h x a b).1, fun x a b => (h x a b).2⟩⟩

/-! ## Sortedness check -/

def splitLe (v w : TU) : Bool := decide (splitPt v.u ≤ splitPt w.u)

/-- One adjacent-pair pass. -/
def sortedB : List TU → Bool
  | v :: w :: rest => splitLe v w && sortedB (w :: rest)
  | _ => true

theorem sortedB_pairwise : ∀ (l : List TU), sortedB l = true → SortedSplit l
  | [], _ => List.Pairwise.nil
  | [_], _ => List.pairwise_singleton _ _
  | v :: w :: rest, h => by
    simp only [sortedB, Bool.and_eq_true, splitLe, decide_eq_true_eq] at h
    have ih := sortedB_pairwise (w :: rest) h.2
    simp only [SortedSplit, List.pairwise_cons] at ih ⊢
    refine ⟨?_, ih.1, ih.2⟩
    intro a ha
    simp only [List.mem_cons] at ha
    rcases ha with rfl | ha
    · exact h.1
    · have := ih.1 a ha; omega

theorem sortedB_of_pairwise : ∀ (l : List TU), SortedSplit l → sortedB l = true
  | [], _ => rfl
  | [_], _ => rfl
  | v :: w :: rest, h => by
    simp only [SortedSplit, List.pairwise_cons] at h
    simp only [sortedB, Bool.and_eq_true, splitLe, decide_eq_true_eq]
    refine ⟨h.1 w (by simp), sortedB_of_pairwise (w :: rest) ?_⟩
    simp only [SortedSplit, List.pairwise_cons]
    exact ⟨fun a ha => h.2.1 a ha, h.2.2⟩

/-! ## The witness, the checker and the generator -/

/-- The no-forgetting witness: all nonconstant tagged units, sorted by split point. -/
structure NFCert where
  order : List TU
  deriving Repr, DecidableEq

/-- **The small no-forgetting checker.** It evaluates no network. -/
def checkNF (a m t : WideNet) (c : NFCert) : Bool :=
  c.order.isPerm (sweepUnits a m t) && sortedB c.order && sweep none (initCo a m t) c.order

/-- Insertion by split point (used by the untrusted generator; any sort would do, because
the checker re-validates the result). -/
def insertSplit (v : TU) : List TU → List TU
  | [] => [v]
  | w :: ws => if splitLe v w then v :: w :: ws else w :: insertSplit v ws

def sortSplit : List TU → List TU
  | [] => []
  | v :: vs => insertSplit v (sortSplit vs)

theorem insertSplit_perm (v : TU) : ∀ l : List TU, (insertSplit v l).Perm (v :: l)
  | [] => List.Perm.refl _
  | w :: ws => by
    unfold insertSplit
    split
    · exact List.Perm.refl _
    · exact ((insertSplit_perm v ws).cons w).trans (List.Perm.swap v w ws)

theorem sortSplit_perm : ∀ l : List TU, (sortSplit l).Perm l
  | [] => List.Perm.refl _
  | v :: vs => (insertSplit_perm v _).trans ((sortSplit_perm vs).cons v)

theorem insertSplit_sorted (v : TU) : ∀ l : List TU, SortedSplit l → SortedSplit (insertSplit v l)
  | [], _ => List.pairwise_singleton _ _
  | w :: ws, h => by
    unfold insertSplit
    simp only [SortedSplit, List.pairwise_cons] at h
    split
    · next hle =>
      simp only [splitLe, decide_eq_true_eq] at hle
      simp only [SortedSplit, List.pairwise_cons, List.mem_cons]
      refine ⟨?_, h.1, h.2⟩
      rintro a (rfl | ha)
      · exact hle
      · have := h.1 a ha; omega
    · next hle =>
      simp only [splitLe, decide_eq_true_eq] at hle
      simp only [SortedSplit, List.pairwise_cons]
      refine ⟨?_, insertSplit_sorted v ws h.2⟩
      intro a ha
      have ha' := (insertSplit_perm v ws).mem_iff.mp ha
      simp only [List.mem_cons] at ha'
      rcases ha' with rfl | ha'
      · omega
      · exact h.1 a ha'

theorem sortSplit_sorted : ∀ l : List TU, SortedSplit (sortSplit l)
  | [] => List.Pairwise.nil
  | v :: vs => insertSplit_sorted v _ (sortSplit_sorted vs)

/-- The (untrusted) witness generator: sort the nonconstant units by split point. -/
def genNF (a m t : WideNet) : NFCert := ⟨sortSplit (sweepUnits a m t)⟩

theorem mem_sweepUnits {a m t : WideNet} {v : TU} (h : v ∈ sweepUnits a m t) : v.u.w ≠ 0 := by
  unfold sweepUnits at h
  exact (nonconst_iff v).mp (List.mem_filter.mp h).2

/-- **Soundness of the witness checker** (for every witness, however forged). -/
theorem checkNF_sound {a m t : WideNet} {c : NFCert} (h : checkNF a m t c = true) :
    ∀ x, predict a x = predict t x → predict m x = predict t x := by
  simp only [checkNF, Bool.and_eq_true] at h
  obtain ⟨⟨hp, hs⟩, hsw⟩ := h
  have hperm := List.isPerm_iff.mp hp
  have hw : ∀ v ∈ c.order, v.u.w ≠ 0 := fun v hv => mem_sweepUnits (hperm.mem_iff.mp hv)
  intro x hx
  have hF : gap a t x = 0 := by unfold gap; omega
  rw [gapF_decomp a m t x, ← sumBy_perm _ hperm] at hF
  have := sweep_sound c.order none (initCo a m t) hsw hw (sortedB_pairwise _ hs) x
    (by simp [LoOK]) hF
  rw [sumBy_perm _ hperm, ← gapG_decomp a m t x] at this
  unfold gap at this; omega

theorem genNF_perm (a m t : WideNet) : (genNF a m t).order.Perm (sweepUnits a m t) :=
  sortSplit_perm _

theorem genNF_sorted (a m t : WideNet) : SortedSplit (genNF a m t).order :=
  sortSplit_sorted _

/-- **Completeness for the one-dimensional integer ReLU class.** -/
theorem checkNF_complete (a m t : WideNet)
    (h : ∀ x, predict a x = predict t x → predict m x = predict t x) :
    checkNF a m t (genNF a m t) = true := by
  have hperm := genNF_perm a m t
  have hw : ∀ v ∈ (genNF a m t).order, v.u.w ≠ 0 :=
    fun v hv => mem_sweepUnits (hperm.mem_iff.mp hv)
  simp only [checkNF, Bool.and_eq_true]
  refine ⟨⟨List.isPerm_iff.mpr hperm, sortedB_of_pairwise _ (genNF_sorted a m t)⟩, ?_⟩
  apply sweep_complete _ none _ hw (genNF_sorted a m t) (fun _ _ => by simp [LoOK])
  intro x _ hF
  rw [sumBy_perm _ hperm, ← gapF_decomp a m t x] at hF
  rw [sumBy_perm _ hperm, ← gapG_decomp a m t x]
  unfold gap at hF ⊢
  have := h x (by omega)
  omega

/-- **Exact agreement with V6**: some witness is accepted iff V6's decision procedure
accepts. -/
theorem checkNF_iff_noForgetting (a m t : WideNet) :
    (∃ c, checkNF a m t c = true) ↔ noForgetting a m t = true := by
  rw [noForgetting_iff]
  exact ⟨fun ⟨_, hc⟩ => checkNF_sound hc, fun h => ⟨_, checkNF_complete a m t h⟩⟩

/-! ## Rejection of malformed witnesses -/

/-- A witness that is not a permutation of the actual units (missing, duplicated, forged or
foreign units) is rejected. -/
theorem checkNF_not_perm (a m t : WideNet) (c : NFCert)
    (h : ¬ c.order.Perm (sweepUnits a m t)) : checkNF a m t c = false := by
  have : c.order.isPerm (sweepUnits a m t) = false := by
    cases hp : c.order.isPerm (sweepUnits a m t) with
    | false => rfl
    | true => exact absurd (List.isPerm_iff.mp hp) h
  simp [checkNF, this]

/-- An unsorted witness is rejected. -/
theorem checkNF_unsorted (a m t : WideNet) (c : NFCert) (h : ¬ SortedSplit c.order) :
    checkNF a m t c = false := by
  have : sortedB c.order = false := by
    cases hp : sortedB c.order with
    | false => rfl
    | true => exact absurd (sortedB_pairwise _ hp) h
  simp [checkNF, this]

/-- A witness whose length differs from the number of nonconstant units is rejected. -/
theorem checkNF_wrong_length (a m t : WideNet) (c : NFCert)
    (h : c.order.length ≠ (sweepUnits a m t).length) : checkNF a m t c = false :=
  checkNF_not_perm a m t c (fun hp => h hp.length_eq)

/-- If the candidate forgets anywhere, **every** witness is rejected. -/
theorem checkNF_forgetting_rejected (a m t : WideNet) (x : Int)
    (hx : predict a x = predict t x) (hm : predict m x ≠ predict t x) (c : NFCert) :
    checkNF a m t c = false := by
  cases h : checkNF a m t c with
  | false => rfl
  | true => exact absurd (checkNF_sound h x hx) hm

/-! ## Cost -/

/-- The sweep makes one constant-time piece decision per witness entry plus one, and one
coefficient update per witness entry. -/
def sweepSteps : List TU → Nat
  | [] => 1
  | _ :: vs => 1 + sweepSteps vs

theorem sweep_steps (l : List TU) : sweepSteps l = l.length + 1 := by
  induction l with
  | nil => rfl
  | cons _ vs ih => simp only [sweepSteps, ih, List.length_cons]; omega

theorem genNF_length (a m t : WideNet) :
    (genNF a m t).order.length = (sweepUnits a m t).length := (genNF_perm a m t).length_eq

theorem kinks_length (l : List HiddenUnit) :
    (kinks l).length = 3 * (l.filter (fun u => u.w != 0)).length := by
  induction l with
  | nil => rfl
  | cons u us ih =>
    simp only [kinks, List.flatMap_cons, List.length_append] at ih ⊢
    rw [ih]
    by_cases hw : u.w = 0
    · simp [unitKinks, hw]
    · simp [unitKinks, hw]; omega

theorem sweepUnits_length (a m t : WideNet) :
    (sweepUnits a m t).length =
      ((a.hidden ++ m.hidden ++ t.hidden).filter (fun u => u.w != 0)).length := by
  unfold sweepUnits tagged nonconst
  simp only [List.filter_append, List.length_append, List.filter_map, List.length_map]
  rfl

/-- **The V6 procedure examines at least `9N + 3` inputs**, where `N` is the number of
nonconstant units; each examined input needs a full evaluation of the incumbent and the
target network. -/
theorem v6_candidates_length_ge (a m t : WideNet) :
    9 * (sweepUnits a m t).length + 3 ≤ (candidates a m t).length := by
  have hk : (anchors a m t).length = 3 * (sweepUnits a m t).length + 1 := by
    simp only [anchors, List.length_cons, kinks_length, sweepUnits_length]
  have : ∀ K : List Int, 3 * K.length ≤ (K.flatMap fun k =>
      [k - 1, k, k + 1] ++ rootFrom (gap a t) (k - 1) ++ rootFrom (gap a t) k).length := by
    intro K
    induction K with
    | nil => simp
    | cons k ks ih => simp only [List.flatMap_cons, List.length_append, List.length_cons]; omega
  have := this (anchors a m t)
  unfold candidates
  omega

/-! ## Generic witness checking and the combined checker -/

theorem sweepWith_gap_sound {P : Option Int → Option Int → Co → Bool} {R : Int → Int → Int → Prop}
    (hP : PieceSpec P R) {a m t : WideNet} {order : List TU}
    (hperm : order.Perm (sweepUnits a m t)) (hs : SortedSplit order)
    (hsw : sweepWith P none (initCo a m t) order = true) :
    ∀ x, R x (gap a t x) (gap m t x) := by
  have hw : ∀ v ∈ order, v.u.w ≠ 0 := fun v hv => mem_sweepUnits (hperm.mem_iff.mp hv)
  intro x
  have := sweepWith_sound hP order none (initCo a m t) hsw hw hs x (by simp [LoOK])
  rw [sumBy_perm _ hperm, sumBy_perm _ hperm, ← gapF_decomp, ← gapG_decomp] at this
  exact this

theorem sweepWith_gap_complete {P : Option Int → Option Int → Co → Bool}
    {R : Int → Int → Int → Prop} (hP : PieceSpec P R) (a m t : WideNet)
    (h : ∀ x, R x (gap a t x) (gap m t x)) :
    sweepWith P none (initCo a m t) (genNF a m t).order = true := by
  have hperm := genNF_perm a m t
  have hw : ∀ v ∈ (genNF a m t).order, v.u.w ≠ 0 :=
    fun v hv => mem_sweepUnits (hperm.mem_iff.mp hv)
  apply sweepWith_complete hP _ none _ hw (genNF_sorted a m t) (fun _ _ => by simp [LoOK])
  intro x _
  rw [sumBy_perm _ hperm, sumBy_perm _ hperm, ← gapF_decomp, ← gapG_decomp]
  exact h x

/-- **Combined witness checker**: one sweep decides no-forgetting on all integers *and*
the error bound `|predict m x - predict t x| ≤ B` on `[L, U]`, evaluating no network. -/
def checkBoth (a m t : WideNet) (L U : Int) (B : Nat) (c : NFCert) : Bool :=
  c.order.isPerm (sweepUnits a m t) && sortedB c.order &&
    sweepWith (localBoth L U B) none (initCo a m t) c.order

theorem checkBoth_sound {a m t : WideNet} {L U : Int} {B : Nat} {c : NFCert}
    (h : checkBoth a m t L U B c = true) :
    (∀ x, predict a x = predict t x → predict m x = predict t x) ∧
    (∀ x, L ≤ x → x ≤ U → (predict m x - predict t x).natAbs ≤ B) := by
  simp only [checkBoth, Bool.and_eq_true] at h
  obtain ⟨⟨hp, hs⟩, hsw⟩ := h
  have H := sweepWith_gap_sound (localBoth_spec L U B) (List.isPerm_iff.mp hp)
    (sortedB_pairwise _ hs) hsw
  refine ⟨fun x hx => ?_, fun x h1 h2 => ?_⟩
  · have := (H x).1 (by unfold gap; omega)
    unfold gap at this; omega
  · exact (H x).2 h1 h2

theorem checkBoth_complete (a m t : WideNet) (L U : Int) (B : Nat)
    (h1 : ∀ x, predict a x = predict t x → predict m x = predict t x)
    (h2 : ∀ x, L ≤ x → x ≤ U → (predict m x - predict t x).natAbs ≤ B) :
    checkBoth a m t L U B (genNF a m t) = true := by
  simp only [checkBoth, Bool.and_eq_true]
  refine ⟨⟨List.isPerm_iff.mpr (genNF_perm a m t), sortedB_of_pairwise _ (genNF_sorted a m t)⟩,
    sweepWith_gap_complete (localBoth_spec L U B) a m t ?_⟩
  intro x
  refine ⟨fun hF => ?_, fun hl hu => h2 x hl hu⟩
  unfold gap at hF ⊢
  have := h1 x (by omega)
  omega

theorem checkBoth_iff (a m t : WideNet) (L U : Int) (B : Nat) :
    (∃ c, checkBoth a m t L U B c = true) ↔
      (∀ x, predict a x = predict t x → predict m x = predict t x) ∧
      (∀ x, L ≤ x → x ≤ U → (predict m x - predict t x).natAbs ≤ B) :=
  ⟨fun ⟨_, h⟩ => checkBoth_sound h, fun ⟨h1, h2⟩ => ⟨_, checkBoth_complete a m t L U B h1 h2⟩⟩

theorem checkBoth_not_perm (a m t : WideNet) (L U : Int) (B : Nat) (c : NFCert)
    (h : ¬ c.order.Perm (sweepUnits a m t)) : checkBoth a m t L U B c = false := by
  have : c.order.isPerm (sweepUnits a m t) = false := by
    cases hp : c.order.isPerm (sweepUnits a m t) with
    | false => rfl
    | true => exact absurd (List.isPerm_iff.mp hp) h
  simp [checkBoth, this]

theorem checkBoth_unsorted (a m t : WideNet) (L U : Int) (B : Nat) (c : NFCert)
    (h : ¬ SortedSplit c.order) : checkBoth a m t L U B c = false := by
  have : sortedB c.order = false := by
    cases hp : sortedB c.order with
    | false => rfl
    | true => exact absurd (sortedB_pairwise _ hp) h
  simp [checkBoth, this]

/-! ## Executable fixtures (kernel-checked) -/

/-- The witness for the exact step `gen2 ↦ gen3` (target `gen3`): eight tagged units with
split points `-1,-1,-1,0,0,0,2,2`. -/
theorem nf_gen2_gen3_splits :
    (genNF gen2 gen3 gen3).order.map (fun v => splitPt v.u) = [-1, -1, -1, 0, 0, 0, 2, 2] := by
  decide +kernel

theorem nf_gen2_gen3_accepted : checkNF gen2 gen3 gen3 (genNF gen2 gen3 gen3) = true := by
  decide +kernel

/-- The corpus-perfect `blindForget` (which forgets `x = -12`): the generated witness is
rejected, and so is every other witness. -/
theorem nf_blindForget_rejected : checkNF gen2 blindForget gen3 (genNF gen2 blindForget gen3) = false := by
  decide +kernel

theorem nf_blindForget_all_rejected (c : NFCert) : checkNF gen2 blindForget gen3 c = false :=
  checkNF_forgetting_rejected gen2 blindForget gen3 (-12) (by decide) (by decide) c

/-- Incomplete witness (first entry dropped). -/
theorem nf_incomplete_rejected :
    checkNF gen2 gen3 gen3 ⟨(genNF gen2 gen3 gen3).order.drop 1⟩ = false := by decide +kernel

/-- Reordered witness (reversed). -/
theorem nf_reordered_rejected :
    checkNF gen2 gen3 gen3 ⟨(genNF gen2 gen3 gen3).order.reverse⟩ = false := by decide +kernel

/-- Contradictory witness (an entry duplicated in place of another). -/
theorem nf_duplicated_rejected :
    checkNF gen2 gen3 gen3
      ⟨(genNF gen2 gen3 gen3).order.take 1 ++ (genNF gen2 gen3 gen3).order.take 1 ++
        (genNF gen2 gen3 gen3).order.drop 2⟩ = false := by decide +kernel

/-- Forged witness (a unit's bias changed, which moves its claimed split point). -/
theorem nf_forged_rejected :
    checkNF gen2 gen3 gen3
      ⟨(genNF gen2 gen3 gen3).order.map (fun v => if v.cF = 1 && v.cG = 0 then
        { v with u := { v.u with b := v.u.b + 7 } } else v)⟩ = false := by decide +kernel

/-- Foreign witness (a unit that occurs in none of the three networks appended). -/
theorem nf_foreign_rejected :
    checkNF gen2 gen3 gen3 ⟨(genNF gen2 gen3 gen3).order ++ [⟨⟨1, 0, 0⟩, 0, 0⟩]⟩ = false := by
  decide +kernel

/-- The combined checker certifies the exact step on `[-10^9, 10^9]` with error level `0`. -/
theorem both_gen2_gen3_accepted :
    checkBoth gen2 gen3 gen3 (-1000000000) 1000000000 0 (genNF gen2 gen3 gen3) = true := by
  decide +kernel

/-- … and rejects a candidate whose error exceeds the claimed level on the interval. -/
theorem both_level_rejected :
    checkBoth gen2 gen2 gen3 (-1000000000) 1000000000 0 (genNF gen2 gen2 gen3) = false := by
  decide +kernel

end PCS.V2.ProofGatedSweepCert
