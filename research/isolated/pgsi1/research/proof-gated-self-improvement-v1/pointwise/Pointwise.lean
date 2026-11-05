import PGSI1Bridge

/-! Isolated research checker. Certificates contain only cells and affine forms.
The producer and its partition algorithm are not trusted by these proofs.
The domain is exact mathematical integers, not floats or native execution. -/
namespace PCS.Research.Pointwise
open IntegerAffine

def error (a t : Net) (x : Int) : Nat := (predict a x - predict t x).natAbs
def Dominates (a b t : Net) : Prop := ∀ x : Int, error b t x ≤ error a t x

def absForm (c : Cell) (f : Affine) : Option Affine :=
  if nonneg c f then some f
  else if nonneg c (neg f) then some (neg f) else none

theorem absForm_sound (c : Cell) (f g : Affine)
    (h : absForm c f = some g) (x : Int) (hx : Within c x) :
    g.eval x = (f.eval x).natAbs := by
  unfold absForm at h
  split at h
  next hp =>
    cases Option.some.inj h
    exact (Int.natAbs_of_nonneg (nonneg_sound c f hp x hx)).symm
  next hp =>
    split at h
    next hn =>
      cases Option.some.inj h
      have hn' := nonneg_sound c (neg f) hn x hx
      rw [neg_eval] at hn'
      rw [neg_eval]
      exact (Int.ofNat_natAbs_of_nonpos (by omega : f.eval x ≤ 0)).symm
    next hn => contradiction

def dominanceRow (a b t : Net) (r : Row) : Bool :=
  decide (form r.cell a = some r.left) &&
  decide (form r.cell b = some r.right) &&
  decide (form r.cell t = some r.target) &&
  match absForm r.cell (minus r.left r.target), absForm r.cell (minus r.right r.target) with
  | some oldAbs, some newAbs => nonneg r.cell (minus oldAbs newAbs)
  | _, _ => false

theorem dominanceRow_sound (a b t : Net) (r : Row)
    (h : dominanceRow a b t r = true) (x : Int) (hx : Within r.cell x) :
    error b t x ≤ error a t x := by
  have hp : ((form r.cell a = some r.left ∧ form r.cell b = some r.right) ∧
      form r.cell t = some r.target) ∧
      (match absForm r.cell (minus r.left r.target), absForm r.cell (minus r.right r.target) with
      | some oldAbs, some newAbs => nonneg r.cell (minus oldAbs newAbs)
      | _, _ => false) = true := by
    simpa only [dominanceRow, Bool.and_eq_true, decide_eq_true_eq] using h
  cases ho : absForm r.cell (minus r.left r.target) with
  | none => simp [ho] at hp
  | some oldAbs =>
    cases hn : absForm r.cell (minus r.right r.target) with
    | none => simp [hn] at hp
    | some newAbs =>
      have hg : nonneg r.cell (minus oldAbs newAbs) = true := by simpa [ho, hn] using hp.2
      have bound := nonneg_sound _ _ hg x hx
      rw [minus_eval, absForm_sound _ _ _ ho x hx, absForm_sound _ _ _ hn x hx,
        minus_eval, minus_eval] at bound
      have ha := form_sound _ _ _ hp.1.1.1 x hx
      have hb := form_sound _ _ _ hp.1.1.2 x hx
      have ht := form_sound _ _ _ hp.1.2 x hx
      unfold error
      rw [ha, hb, ht]
      omega

def accept (a b t : Net) (rows : List Row) : Bool :=
  coverFrom none (rows.map Row.cell) && rows.all (dominanceRow a b t)

theorem accept_sound (a b t : Net) (rows : List Row) (h : accept a b t rows = true) :
    Dominates a b t := by
  have hp : coverFrom none (rows.map Row.cell) = true ∧ rows.all (dominanceRow a b t) = true := by
    simpa only [accept, Bool.and_eq_true] using h
  intro x
  obtain ⟨c, hc, hx⟩ := coverFrom_sound (rows.map Row.cell) none hp.1 x trivial
  obtain ⟨r, hr, hrc⟩ := List.mem_map.mp hc
  subst c
  exact dominanceRow_sound a b t r (List.all_eq_true.mp hp.2 r hr) x hx

theorem preserves_correct (a b t : Net) (h : Dominates a b t) :
    ∀ x : Int, predict a x = predict t x → predict b x = predict t x := by
  intro x hx
  have hb := h x
  simp only [error, hx, Int.sub_self, Int.natAbs_zero, Nat.le_zero] at hb
  have hz := Int.natAbs_eq_zero.mp hb
  omega

theorem preserves_bound (a b t : Net) (h : Dominates a b t) (domain : Int → Prop) (m : Nat)
    (hb : ∀ x, domain x → error a t x ≤ m) : ∀ x, domain x → error b t x ≤ m := by
  intro x hx
  exact Nat.le_trans (h x) (hb x hx)

theorem sum_error_le (a b t : Net) (h : Dominates a b t) (xs : List Int) :
    (xs.map (error b t)).sum ≤ (xs.map (error a t)).sum := by
  induction xs with
  | nil => simp
  | cons x xs ih => simpa only [List.map_cons, List.sum_cons] using Nat.add_le_add (h x) ih

theorem transitive (a b c t : Net) (hab : Dominates a b t) (hbc : Dominates b c t) :
    Dominates a c t := by
  intro x
  exact Nat.le_trans (hbc x) (hab x)

def refutes (a b t : Net) (x : Int) : Bool := decide (error a t x < error b t x)

theorem refutes_sound (a b t : Net) (x : Int) (h : refutes a b t x = true) :
    ¬ Dominates a b t := by
  have hx : error a t x < error b t x := of_decide_eq_true h
  intro hd
  have hn := hd x
  omega

inductive Claim where
  | dominates (a b t : Net) (rows : List Row)
  | notDominates (a b t : Net) (witness : Int)

def check : Claim → Bool
  | .dominates a b t rows => accept a b t rows
  | .notDominates a b t x => refutes a b t x
def Meaning : Claim → Prop
  | .dominates a b t _ => Dominates a b t
  | .notDominates a b t _ => ¬ Dominates a b t

theorem check_sound (c : Claim) (h : check c = true) : Meaning c := by
  cases c with
  | dominates a b t rs => exact accept_sound a b t rs h
  | notDominates a b t x => exact refutes_sound a b t x h

theorem batch_sound (cs : List Claim) (h : cs.all check = true) : ∀ c ∈ cs, Meaning c := by
  intro c hc
  exact check_sound c (List.all_eq_true.mp h c hc)

-- Mathematical composition only; the deployed PGSI1 authority is unchanged.
def guard (a b : PCS.V2.ProofGatedSelfImprovement.Neuron) (rows : List Row) : Bool :=
  PCS.V2.ProofGatedSelfImprovement.accept a b &&
    accept (PGSI1Bridge.embed a) (PGSI1Bridge.embed b) PGSI1Bridge.targetNet rows

theorem guard_sound (a b : PCS.V2.ProofGatedSelfImprovement.Neuron) (rows : List Row)
    (h : guard a b rows = true) :
    PCS.V2.ProofGatedSelfImprovement.admissible a b ∧
    (∀ x : Int,
      (PCS.V2.ProofGatedSelfImprovement.predict b x - PCS.V2.ProofGatedSelfImprovement.target x).natAbs ≤
      (PCS.V2.ProofGatedSelfImprovement.predict a x - PCS.V2.ProofGatedSelfImprovement.target x).natAbs) := by
  have hp : PCS.V2.ProofGatedSelfImprovement.accept a b = true ∧
      accept (PGSI1Bridge.embed a) (PGSI1Bridge.embed b) PGSI1Bridge.targetNet rows = true := by
    simpa only [guard, Bool.and_eq_true] using h
  refine ⟨PCS.V2.ProofGatedSelfImprovement.accept_sound hp.1, ?_⟩
  have hd := accept_sound _ _ _ _ hp.2
  simpa only [Dominates, error, PGSI1Bridge.embed_predict, PGSI1Bridge.target_predict] using hd

end PCS.Research.Pointwise
