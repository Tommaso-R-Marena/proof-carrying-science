import Std

/-!
Research-only certificate checker for scalar-input finite integer ReLU sums.
No imports from, or changes to, the PCS production authority or Aristotle modules.
The optimized certificate producer is untrusted. All arithmetic is exact Int.
-/
namespace PCS.Research.IntegerAffine

structure Cell where
  low : Option Int
  high : Option Int
  deriving Repr, DecidableEq

structure Affine where
  slope : Int
  bias : Int
  deriving Repr, DecidableEq

def Affine.eval (f : Affine) (x : Int) : Int := f.slope * x + f.bias

def Within (c : Cell) (x : Int) : Prop :=
  (match c.low with | none => True | some l => l ≤ x) ∧
  (match c.high with | none => True | some h => x ≤ h)
instance (c : Cell) (x : Int) : Decidable (Within c x) := by
  unfold Within; cases c.low <;> cases c.high <;> infer_instance

def nonneg (c : Cell) (f : Affine) : Bool :=
  decide (f.slope = 0 ∧ 0 ≤ f.bias) ||
  (match c.low with
   | none => false
   | some l => decide (0 ≤ f.slope ∧ 0 ≤ f.eval l)) ||
  (match c.high with
   | none => false
   | some h => decide (f.slope ≤ 0 ∧ 0 ≤ f.eval h))

theorem nonneg_sound (c : Cell) (f : Affine) (h : nonneg c f = true)
    (x : Int) (hx : Within c x) : 0 ≤ f.eval x := by
  simp only [nonneg, Bool.or_eq_true, decide_eq_true_eq] at h
  rcases h with (h | h) | h
  · simp [Affine.eval, h.1, h.2]
  · cases hl : c.low with
    | none => simp [hl] at h
    | some l =>
      simp only [hl, decide_eq_true_eq] at h
      have hx' : l ≤ x := by simpa [Within, hl] using hx.1
      have hm := Int.mul_le_mul_of_nonneg_left hx' h.1
      simp only [Affine.eval] at *
      omega
  · cases hh : c.high with
    | none => simp [hh] at h
    | some r =>
      simp only [hh, decide_eq_true_eq] at h
      have hx' : x ≤ r := by simpa [Within, hh] using hx.2
      have hm := Int.mul_le_mul_of_nonpos_left h.1 hx'
      simp only [Affine.eval] at *
      omega

structure Term where
  coefficient : Int
  weight : Int
  bias : Int
  deriving Repr, DecidableEq

structure Net where
  terms : List Term
  bias : Int
  deriving Repr, DecidableEq

def relu (z : Int) : Int := if 0 ≤ z then z else 0

def termValue (t : Term) (x : Int) : Int :=
  t.coefficient * relu (t.weight * x + t.bias)

def termsValue : List Term → Int → Int
  | [], _ => 0
  | t :: ts, x => termValue t x + termsValue ts x

def predict (n : Net) (x : Int) : Int := n.bias + termsValue n.terms x

def plus (a b : Affine) : Affine := ⟨a.slope + b.slope, a.bias + b.bias⟩
def minus (a b : Affine) : Affine := ⟨a.slope - b.slope, a.bias - b.bias⟩
def neg (a : Affine) : Affine := ⟨-a.slope, -a.bias⟩

theorem plus_eval (a b : Affine) (x : Int) :
    (plus a b).eval x = a.eval x + b.eval x := by
  simp [plus, Affine.eval, Int.add_mul, Int.add_assoc, Int.add_comm, Int.add_left_comm]

theorem minus_eval (a b : Affine) (x : Int) :
    (minus a b).eval x = a.eval x - b.eval x := by
  simp only [minus, Affine.eval, Int.sub_mul]
  omega

theorem neg_eval (a : Affine) (x : Int) : (neg a).eval x = -a.eval x := by
  simp [neg, Affine.eval, Int.neg_mul, Int.neg_add]

def termForm (c : Cell) (t : Term) : Option Affine :=
  if nonneg c ⟨t.weight, t.bias - 1⟩ then
    some ⟨t.coefficient * t.weight, t.coefficient * t.bias⟩
  else if nonneg c ⟨-t.weight, -t.bias⟩ then some ⟨0, 0⟩
  else none

theorem termForm_sound (c : Cell) (t : Term) (f : Affine)
    (h : termForm c t = some f) (x : Int) (hx : Within c x) :
    termValue t x = f.eval x := by
  unfold termForm at h
  split at h
  next hp =>
    have hz := nonneg_sound c ⟨t.weight, t.bias - 1⟩ hp x hx
    simp only [Option.some.injEq] at h
    subst f
    simp only [Affine.eval] at hz
    have hz' : 0 ≤ t.weight * x + t.bias := by omega
    simp [termValue, relu, hz', Affine.eval, Int.mul_add, Int.mul_assoc]
  next hp =>
    split at h
    next hn =>
      have hz := nonneg_sound c ⟨-t.weight, -t.bias⟩ hn x hx
      simp only [Affine.eval, Int.neg_mul] at hz
      have hz' : t.weight * x + t.bias ≤ 0 := by omega
      simp only [Option.some.injEq] at h
      subst f
      unfold termValue relu Affine.eval
      split
      · next hz0 =>
          have hz0' : t.weight * x + t.bias = 0 := by omega
          simp [hz0']
      · simp
    next => cases h

def termsForm (c : Cell) : List Term → Option Affine
  | [] => some ⟨0, 0⟩
  | t :: ts => do
    let a ← termForm c t
    let b ← termsForm c ts
    pure (plus a b)

theorem termsForm_sound (c : Cell) (ts : List Term) (f : Affine)
    (h : termsForm c ts = some f) (x : Int) (hx : Within c x) :
    termsValue ts x = f.eval x := by
  induction ts generalizing f with
  | nil =>
    have hf : f = ⟨0, 0⟩ := by simpa [termsForm] using h.symm
    subst f
    simp [termsValue, Affine.eval]
  | cons t ts ih =>
    cases ha : termForm c t with
    | none => simp [termsForm, ha] at h
    | some a =>
      cases hb : termsForm c ts with
      | none => simp [termsForm, ha, hb] at h
      | some b =>
        have hf : plus a b = f := by simpa [termsForm, ha, hb] using h
        subst f
        rw [termsValue, termForm_sound c t a ha x hx,
          ih b hb, plus_eval]

def form (c : Cell) (n : Net) : Option Affine := do
  let f ← termsForm c n.terms
  pure (plus ⟨0, n.bias⟩ f)

theorem form_sound (c : Cell) (n : Net) (f : Affine)
    (h : form c n = some f) (x : Int) (hx : Within c x) :
    predict n x = f.eval x := by
  cases ht : termsForm c n.terms with
  | none => simp [form, ht] at h
  | some a =>
    have hf : plus ⟨0, n.bias⟩ a = f := by simpa [form, ht] using h
    subst f
    rw [plus_eval]
    simp only [predict, Affine.eval, Int.zero_mul, Int.zero_add]
    rw [termsForm_sound c n.terms a ht x hx]
    rfl

def ordered (c : Cell) : Bool :=
  match c.low, c.high with
  | some l, some h => decide (l ≤ h)
  | _, _ => true

def coverFrom (lower : Option Int) : List Cell → Bool
  | [] => false
  | c :: cs => decide (c.low = lower) && ordered c &&
    match c.high with
    | none => cs.isEmpty
    | some h => coverFrom (some (h + 1)) cs

def Lower (lower : Option Int) (x : Int) : Prop :=
  match lower with | none => True | some l => l ≤ x

theorem coverFrom_sound (cs : List Cell) (lower : Option Int)
    (h : coverFrom lower cs = true) (x : Int)
    (hx : Lower lower x) :
    ∃ c ∈ cs, Within c x := by
  induction cs generalizing lower with
  | nil => simp [coverFrom] at h
  | cons c cs ih =>
    have hparts : (c.low = lower ∧ ordered c = true) ∧
        (match c.high with
         | none => cs.isEmpty
         | some r => coverFrom (some (r+1)) cs) = true := by
      simpa only [coverFrom, Bool.and_eq_true, decide_eq_true_eq] using h
    have hlo : match c.low with | none => True | some l => l ≤ x := by
      rw [hparts.1.1]; exact hx
    cases hh : c.high with
    | none => exact ⟨c, by simp, hlo, by simp [hh]⟩
    | some r =>
      by_cases hr : x ≤ r
      · exact ⟨c, by simp, hlo, by simpa [hh] using hr⟩
      · have ht : coverFrom (some (r+1)) cs = true := by
          simpa [hh] using hparts.2
        obtain ⟨d, hd, hdx⟩ := ih (some (r+1)) ht (by simp only [Lower]; omega)
        exact ⟨d, by simp [hd], hdx⟩

def zeroOn (c : Cell) (f : Affine) : Bool :=
  decide (f.slope = 0 ∧ f.bias = 0) ||
  match c.low, c.high with
  | some l, some h => decide (l = h ∧ f.eval l = 0)
  | _, _ => false

theorem zeroOn_sound (c : Cell) (f : Affine) (h : zeroOn c f = true)
    (x : Int) (hx : Within c x) : f.eval x = 0 := by
  simp only [zeroOn, Bool.or_eq_true, decide_eq_true_eq] at h
  rcases h with h | h
  · simp [Affine.eval, h.1, h.2]
  · cases hl : c.low <;> cases hh : c.high <;> simp only [hl, hh] at h
    all_goals try contradiction
    next l r =>
      have hs : l = r ∧ f.eval l = 0 := of_decide_eq_true h
      have hx' : l ≤ x ∧ x ≤ r := by simpa [Within, hl, hh] using hx
      have he : x = l := by omega
      simpa [he] using hs.2

def preservesAffine (c : Cell) (old new : Affine) : Bool :=
  if old.slope = 0 then
    if old.bias = 0 then zeroOn c new else true
  else
    let root := (-old.bias) / old.slope
    if old.eval root = 0 ∧ Within c root then decide (new.eval root = 0) else true

theorem preservesAffine_sound (c : Cell) (old new : Affine)
    (h : preservesAffine c old new = true) (x : Int)
    (hx : Within c x) (he : old.eval x = 0) : new.eval x = 0 := by
  unfold preservesAffine at h
  split at h
  next ha =>
    have hb : old.bias = 0 := by simpa [Affine.eval, ha] using he
    simp only [hb, ↓reduceIte] at h
    exact zeroOn_sound c new h x hx
  next ha =>
    have hm : old.slope * x = -old.bias := by unfold Affine.eval at he; omega
    have hr : (-old.bias) / old.slope = x := by
      rw [← hm, Int.mul_ediv_cancel_left x ha]
    simp only [hr, he, hx, and_self, ↓reduceIte, decide_eq_true_eq] at h
    exact h

structure Row where
  cell : Cell
  left : Affine
  right : Affine
  target : Affine
  deriving Repr, DecidableEq

def equalRow (a b : Net) (r : Row) : Bool :=
  decide (form r.cell a = some r.left) &&
  decide (form r.cell b = some r.right) &&
  zeroOn r.cell (minus r.left r.right)

def preservesRow (a b t : Net) (r : Row) : Bool :=
  decide (form r.cell a = some r.left) &&
  decide (form r.cell b = some r.right) &&
  decide (form r.cell t = some r.target) &&
  preservesAffine r.cell (minus r.left r.target) (minus r.right r.target)

def acceptEqual (a b : Net) (rows : List Row) : Bool :=
  coverFrom none (rows.map Row.cell) && rows.all (equalRow a b)

def acceptPreserves (a b t : Net) (rows : List Row) : Bool :=
  coverFrom none (rows.map Row.cell) && rows.all (preservesRow a b t)

theorem acceptEqual_sound (a b : Net) (rows : List Row)
    (h : acceptEqual a b rows = true) : ∀ x : Int, predict a x = predict b x := by
  have hp : coverFrom none (rows.map Row.cell) = true ∧ rows.all (equalRow a b) = true := by
    simpa only [acceptEqual, Bool.and_eq_true] using h
  intro x
  obtain ⟨c, hc, hx⟩ := coverFrom_sound (rows.map Row.cell) none hp.1 x trivial
  obtain ⟨r, hr, hrc⟩ := List.mem_map.mp hc
  subst c
  have hv := List.all_eq_true.mp hp.2 r hr
  have hv' : (form r.cell a = some r.left ∧ form r.cell b = some r.right) ∧
      zeroOn r.cell (minus r.left r.right) = true := by
    simpa only [equalRow, Bool.and_eq_true, decide_eq_true_eq] using hv
  rw [form_sound r.cell a r.left hv'.1.1 x hx,
    form_sound r.cell b r.right hv'.1.2 x hx]
  have hz := zeroOn_sound r.cell (minus r.left r.right) hv'.2 x hx
  rw [minus_eval] at hz
  omega

theorem acceptPreserves_sound (a b t : Net) (rows : List Row)
    (h : acceptPreserves a b t rows = true) :
    ∀ x : Int, predict a x = predict t x → predict b x = predict t x := by
  have hp : coverFrom none (rows.map Row.cell) = true ∧ rows.all (preservesRow a b t) = true := by
    simpa only [acceptPreserves, Bool.and_eq_true] using h
  intro x he
  obtain ⟨c, hc, hx⟩ := coverFrom_sound (rows.map Row.cell) none hp.1 x trivial
  obtain ⟨r, hr, hrc⟩ := List.mem_map.mp hc
  subst c
  have hv := List.all_eq_true.mp hp.2 r hr
  have hv' : ((form r.cell a = some r.left ∧ form r.cell b = some r.right) ∧
      form r.cell t = some r.target) ∧
      preservesAffine r.cell (minus r.left r.target) (minus r.right r.target) = true := by
    simpa only [preservesRow, Bool.and_eq_true, decide_eq_true_eq] using hv
  have ha := form_sound r.cell a r.left hv'.1.1.1 x hx
  have hb := form_sound r.cell b r.right hv'.1.1.2 x hx
  have ht := form_sound r.cell t r.target hv'.1.2 x hx
  have hold : (minus r.left r.target).eval x = 0 := by rw [minus_eval]; omega
  have hn := preservesAffine_sound r.cell (minus r.left r.target)
    (minus r.right r.target) hv'.2 x hx hold
  rw [minus_eval] at hn
  omega

def clipLow (c : Cell) (l : Int) : Int :=
  match c.low with | none => l | some a => max l a

def clipHigh (c : Cell) (h : Int) : Int :=
  match c.high with | none => h | some b => min h b

def clip (c : Cell) (l h : Int) : Cell := ⟨some (clipLow c l), some (clipHigh c h)⟩

theorem clip_contains (c : Cell) (l h x : Int) (hx : Within c x)
    (hl : l ≤ x) (hh : x ≤ h) : Within (clip c l h) x := by
  cases hc : c.low <;> cases hd : c.high <;>
    simp_all [Within, clip, clipLow, clipHigh, Int.max_def, Int.min_def] <;> omega

def boundRow (a b : Net) (l h e : Int) (r : Row) : Bool :=
  decide (form r.cell a = some r.left) &&
  decide (form r.cell b = some r.right) &&
  (if clipHigh r.cell h < clipLow r.cell l then true else
    nonneg (clip r.cell l h) (minus ⟨0, e⟩ (minus r.left r.right)) &&
    nonneg (clip r.cell l h) (plus ⟨0, e⟩ (minus r.left r.right)))

def acceptBound (a b : Net) (rows : List Row) (l h e : Int) : Bool :=
  decide (l ≤ h ∧ 0 ≤ e) && coverFrom none (rows.map Row.cell) &&
  rows.all (boundRow a b l h e)

theorem acceptBound_sound (a b : Net) (rows : List Row) (l h e : Int)
    (ha : acceptBound a b rows l h e = true) :
    ∀ x : Int, l ≤ x → x ≤ h →
      -e ≤ predict a x - predict b x ∧ predict a x - predict b x ≤ e := by
  have hp : ((l ≤ h ∧ 0 ≤ e) ∧ coverFrom none (rows.map Row.cell) = true) ∧
      rows.all (boundRow a b l h e) = true := by
    simpa only [acceptBound, Bool.and_eq_true, decide_eq_true_eq] using ha
  intro x hl hh
  obtain ⟨c, hc, hx⟩ := coverFrom_sound (rows.map Row.cell) none hp.1.2 x trivial
  obtain ⟨r, hr, hrc⟩ := List.mem_map.mp hc
  subst c
  have hv := List.all_eq_true.mp hp.2 r hr
  have hclip := clip_contains r.cell l h x hx hl hh
  have hends : clipLow r.cell l ≤ x ∧ x ≤ clipHigh r.cell h := by
    simpa only [Within, clip] using hclip
  have hn : ¬ clipHigh r.cell h < clipLow r.cell l := by omega
  have hv' : (form r.cell a = some r.left ∧ form r.cell b = some r.right) ∧
      (nonneg (clip r.cell l h) (minus ⟨0, e⟩ (minus r.left r.right)) = true ∧
       nonneg (clip r.cell l h) (plus ⟨0, e⟩ (minus r.left r.right)) = true) := by
    simpa only [boundRow, hn, ↓reduceIte, Bool.and_eq_true, decide_eq_true_eq] using hv
  have hup := nonneg_sound _ _ hv'.2.1 x hclip
  have hdown := nonneg_sound _ _ hv'.2.2 x hclip
  rw [minus_eval, minus_eval] at hup
  rw [plus_eval, minus_eval] at hdown
  simp only [Affine.eval, Int.zero_mul, Int.zero_add] at hup hdown
  have hpa := form_sound r.cell a r.left hv'.1.1 x hx
  have hpb := form_sound r.cell b r.right hv'.1.2 x hx
  simp only [Affine.eval] at hpa hpb
  omega

def acceptMaximum (a b : Net) (rows : List Row) (l h : Int) (m : Nat) (peak : Int) : Bool :=
  acceptBound a b rows l h m &&
  decide (l ≤ peak ∧ peak ≤ h ∧ (predict a peak - predict b peak).natAbs = m)

theorem natAbs_bound (z : Int) (m : Nat) (hl : -(m : Int) ≤ z) (hh : z ≤ m) :
    z.natAbs ≤ m := by
  by_cases hz : 0 ≤ z
  · have he := Int.natAbs_of_nonneg hz
    omega
  · have he := Int.ofNat_natAbs_of_nonpos (by omega : z ≤ 0)
    omega

theorem acceptMaximum_sound (a b : Net) (rows : List Row) (l h : Int) (m : Nat) (peak : Int)
    (ha : acceptMaximum a b rows l h m peak = true) :
    (∀ x : Int, l ≤ x → x ≤ h → (predict a x - predict b x).natAbs ≤ m) ∧
    l ≤ peak ∧ peak ≤ h ∧ (predict a peak - predict b peak).natAbs = m := by
  have hp : acceptBound a b rows l h m = true ∧
      (l ≤ peak ∧ peak ≤ h ∧ (predict a peak - predict b peak).natAbs = m) := by
    simpa only [acceptMaximum, Bool.and_eq_true, decide_eq_true_eq] using ha
  refine ⟨?_, hp.2⟩
  intro x hl hh
  have hb := acceptBound_sound a b rows l h m hp.1 x hl hh
  exact natAbs_bound _ m hb.1 hb.2

def acceptNonvacuous (a b t : Net) (rows : List Row) (witness : Int) : Bool :=
  acceptPreserves a b t rows && decide (predict a witness = predict t witness)

theorem acceptNonvacuous_sound (a b t : Net) (rows : List Row) (witness : Int)
    (h : acceptNonvacuous a b t rows witness = true) :
    (∀ x : Int, predict a x = predict t x → predict b x = predict t x) ∧
    predict a witness = predict t witness := by
  have hp : acceptPreserves a b t rows = true ∧ predict a witness = predict t witness := by
    simpa only [acceptNonvacuous, Bool.and_eq_true, decide_eq_true_eq] using h
  exact ⟨acceptPreserves_sound a b t rows hp.1, hp.2⟩

def refutesEqual (a b : Net) (x : Int) : Bool := decide (predict a x ≠ predict b x)
def refutesPreserves (a b t : Net) (x : Int) : Bool :=
  decide (predict a x = predict t x ∧ predict b x ≠ predict t x)

theorem refutesEqual_sound (a b : Net) (x : Int) (h : refutesEqual a b x = true) :
    ¬ (∀ y : Int, predict a y = predict b y) := by
  have hx : predict a x ≠ predict b x := of_decide_eq_true h
  intro he
  exact hx (he x)

theorem refutesPreserves_sound (a b t : Net) (x : Int)
    (h : refutesPreserves a b t x = true) :
    ¬ (∀ y : Int, predict a y = predict t y → predict b y = predict t y) := by
  have hx : predict a x = predict t x ∧ predict b x ≠ predict t x := of_decide_eq_true h
  intro he
  exact hx.2 (he x hx.1)

def shift (n : Net) (d : Int) : Net := ⟨n.terms, n.bias + d⟩

theorem shift_predict (n : Net) (d x : Int) : predict (shift n d) x = predict n x + d := by
  simp only [shift, predict]
  omega

def acceptNoCorrect (a t : Net) (rows : List Row) : Bool :=
  acceptPreserves a (shift t 1) t rows

theorem acceptNoCorrect_sound (a t : Net) (rows : List Row)
    (h : acceptNoCorrect a t rows = true) : ∀ x : Int, predict a x ≠ predict t x := by
  intro x he
  have hn := acceptPreserves_sound a (shift t 1) t rows h x he
  rw [shift_predict] at hn
  omega

end PCS.Research.IntegerAffine
