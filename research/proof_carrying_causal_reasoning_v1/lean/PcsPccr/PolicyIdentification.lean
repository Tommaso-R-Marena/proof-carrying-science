import PcsPccr.FiniteResponse

/-! Finite-population identification of the success probability under a deterministic
policy with arbitrary finite pretreatment strata and categorical actions. Each unit
has a natural assignment and a full potential-response vector. They may be arbitrarily
dependent. Equal unit weights fix the population grid; multiplicities are repetitions. -/
namespace PcsPccr.PolicyIdentification
open FiniteResponse

structure Datum (s a : Nat) where
  stratum : Fin s
  assigned : Fin a
  outcome : Bool
  deriving DecidableEq, BEq, Repr

structure UnitModel (s a : Nat) where
  stratum : Fin s
  assigned : Fin a
  response : Fin a → Bool

abbrev Policy (s a : Nat) := Fin s → Fin a

def observe (u : UnitModel s a) : Datum s a :=
  ⟨u.stratum, u.assigned, u.response u.assigned⟩

def eventBit (b : Bool) : Fin 2 := if b then 1 else 0

/-- Ordered endogenous variables in causal order Z, X, Y. The shared latent unit
may influence all three. Y reads the surgically assigned X. -/
def scm : Equations (UnitModel s a) [2, a, s] :=
  .extend (.extend (.extend .empty (fun u _ => u.stratum)) (fun u _ => u.assigned))
    (fun u prior => eventBit (u.response prior.1))

theorem factual_evaluation (u : UnitModel s a) :
    evaluate scm (natural [2,a,s]) u =
      (eventBit (observe u).outcome, (observe u).assigned, (observe u).stratum, ()) := rfl

theorem policy_evaluation (p : Policy s a) (u : UnitModel s a) :
    evaluate scm (none, some (p u.stratum), none, ()) u =
      (eventBit (u.response (p u.stratum)), p u.stratum, u.stratum, ()) := rfl

def value (p : Policy s a) (m : List (UnitModel s a)) :=
  m.countP (fun u => u.response (p u.stratum))

/-- Observations reveal only the multiset of factual triples. -/
def Compatible (d : List (Datum s a)) (m : List (UnitModel s a)) : Prop :=
  (m.map observe).Perm d

def aligned (p : Policy s a) (d : Datum s a) := d.assigned == p d.stratum
def lower (p : Policy s a) (d : List (Datum s a)) :=
  d.countP (fun r => aligned p r && r.outcome)
def free (p : Policy s a) (d : List (Datum s a)) :=
  d.countP (fun r => !(aligned p r))
def upper (p : Policy s a) (d : List (Datum s a)) := lower p d + free p d

theorem necessary (p : Policy s a) (h : Compatible d m) :
    lower p d ≤ value p m ∧ value p m ≤ upper p d := by
  unfold lower upper free
  unfold lower
  rw [← h.countP_eq (fun r => aligned p r && r.outcome),
      ← h.countP_eq (fun r => !(aligned p r))]
  clear h
  induction m with
  | nil => simp [value]
  | cons u us ih =>
    simp only [List.map_cons, List.countP_cons, value] at *
    cases he : u.assigned == p u.stratum with
    | false => simp [aligned, observe, he] at * <;> split <;> omega
    | true =>
      have eq := eq_of_beq he
      simp [aligned, observe, eq] at *
      split <;> omega

/-- Fill unobserved responses with a single bit. The observed action retains
the observed outcome even when its policy does not match. -/
def fill (r : Datum s a) (b : Bool) : UnitModel s a :=
  ⟨r.stratum, r.assigned, fun x => if x = r.assigned then r.outcome else b⟩

@[simp] theorem observe_fill (r : Datum s a) (b : Bool) : observe (fill r b) = r := by
  cases r; simp [observe, fill]

/-- Select up to k off-policy units as successful; this constructs a full SCM
population, not only a numerical endpoint. -/
def complete (p : Policy s a) : List (Datum s a) → Nat → List (UnitModel s a)
  | [], _ => []
  | r :: rs, k =>
    if aligned p r then fill r false :: complete p rs k
    else fill r (decide (0 < k)) :: complete p rs (k - 1)

theorem observations_complete (p : Policy s a) (d : List (Datum s a)) (k : Nat) :
    (complete p d k).map observe = d := by
  induction d generalizing k with
  | nil => rfl
  | cons r rs ih => simp only [complete]; split <;> simp [ih]

theorem value_complete (p : Policy s a) (d : List (Datum s a)) (k : Nat) :
    value p (complete p d k) = lower p d + min k (free p d) := by
  induction d generalizing k with
  | nil => simp [value, complete, lower, free]
  | cons r rs ih =>
    simp only [complete]
    split <;> rename_i h
    · have eq : p r.stratum = r.assigned := (eq_of_beq h).symm
      simp only [value, List.countP_cons, fill, eq]
      rw [← value, ih]
      simp [lower, free, List.countP_cons, h, Nat.add_right_comm]
    · have ne : p r.stratum ≠ r.assigned := fun e => h (beq_iff_eq.mpr e.symm)
      simp only [value, List.countP_cons, fill, if_neg ne]
      rw [← value, ih]
      simp [lower, free, h]
      split <;> omega

/-- Exact identified set in units per population. The reverse implication
constructs every grid point, with equality of the entire observational table. -/
theorem sharp (p : Policy s a) (d : List (Datum s a)) (k : Nat) :
    (∃ m, Compatible d m ∧ value p m = k) ↔ lower p d ≤ k ∧ k ≤ upper p d := by
  constructor
  · rintro ⟨m, h, rfl⟩
    exact necessary p h
  · rintro ⟨hl, hu⟩
    refine ⟨complete p d (k - lower p d), ?_, ?_⟩
    · unfold Compatible; rw [observations_complete]
    · rw [value_complete, Nat.min_eq_left (by unfold upper at hu; omega)]; omega

/-- Point identification under unrestricted latent dependence occurs exactly
when all factual units already followed the requested policy. -/
theorem identified_iff (p : Policy s a) (d : List (Datum s a)) :
    (∀ m n, Compatible d m → Compatible d n → value p m = value p n) ↔ free p d = 0 := by
  constructor
  · intro h
    have le : lower p d ≤ upper p d := by simp [upper]
    obtain ⟨m, hm, hv⟩ := (sharp p d _).mpr ⟨Nat.le_refl _, le⟩
    obtain ⟨n, hn, hw⟩ := (sharp p d _).mpr ⟨le, Nat.le_refl _⟩
    have same := h m n hm hn
    simp only [hv, hw, upper] at same
    omega
  · intro hz m n hm hn
    have h₁ := necessary p hm
    have h₂ := necessary p hn
    simp only [upper, hz, Nat.add_zero] at h₁ h₂
    omega

def checkBounds (p : Policy s a) (d : List (Datum s a)) (lo hi : Nat) :=
  decide (d ≠ [] ∧ lo = lower p d ∧ hi = upper p d)

theorem bounds_sound (h : checkBounds p d lo hi = true) :
    d ≠ [] ∧ ∀ k, (∃ m, Compatible d m ∧ value p m = k) ↔ lo ≤ k ∧ k ≤ hi := by
  obtain ⟨hd, rfl, rfl⟩ := of_decide_eq_true h
  exact ⟨hd, sharp p d⟩

/-- The certificate submits two full models; each observational multiset is
compared to independent data. Separate claims bind the reported target counts. -/
def checkPair (p : Policy s a) (d : List (Datum s a)) (m n : List (UnitModel s a))
    (k j : Nat) :=
  decide (d ≠ [] ∧ (m.map observe).Perm d ∧ (n.map observe).Perm d ∧
    value p m = k ∧ value p n = j ∧ k ≠ j)

theorem pair_sound (h : checkPair p d m n k j = true) :
    Compatible d m ∧ Compatible d n ∧ value p m = k ∧ value p n = j ∧
    ¬ ∃ target : Nat, ∀ model, Compatible d model → value p model = target := by
  obtain ⟨_, hm, hn, hv, hw, ne⟩ := of_decide_eq_true h
  refine ⟨hm, hn, hv, hw, ?_⟩
  rintro ⟨c, unique⟩
  exact ne (hv.symm.trans ((unique m hm).trans ((unique n hn).symm.trans hw)))

end PcsPccr.PolicyIdentification
