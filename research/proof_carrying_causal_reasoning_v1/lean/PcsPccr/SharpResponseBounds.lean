import PcsPccr.FiniteResponse

/-! Sharp bounds in a binary randomized trial. The unobserved response type is
(Y₀,Y₁). A fair, independently allocated treatment bit is paired with each
response type. Observing the full joint law of (X,Y) then determines both
intervention marginals, but may leave the probability of individual benefit
unidentified. This is the usual Fréchet bound, here derived constructively
from the executable SCM using exact counts. -/
namespace PcsPccr.SharpResponseBounds
open FiniteResponse

structure Table where
  never : Nat -- (0,0)
  helped : Nat -- (0,1)
  harmed : Nat -- (1,0)
  always : Nat -- (1,1)
  deriving DecidableEq, Repr

def Table.size (t : Table) := t.never + t.helped + t.harmed + t.always
def Table.control (t : Table) := t.harmed + t.always
def Table.treated (t : Table) := t.helped + t.always

/-- Noise consists of treatment assignment and both potential outcomes. -/
abbrev Noise := Bool × Bool × Bool

def bit (b : Bool) : Fin 2 := if b then 1 else 0

def trial : Equations Noise [2,2] :=
  .extend (.extend .empty (fun u _ => bit u.1))
    (fun u prior => bit (if prior.1 = 1 then u.2.2 else u.2.1))

def doX (x : Bool) : Intervention [2,2] := (none, some (bit x), ())

def rows (t : Table) : List (Noise × Nat) :=
  [(⟨false,false,false⟩, t.never), (⟨false,false,true⟩, t.helped),
   (⟨false,true,false⟩, t.harmed), (⟨false,true,true⟩, t.always),
   (⟨true,false,false⟩, t.never), (⟨true,false,true⟩, t.helped),
   (⟨true,true,false⟩, t.harmed), (⟨true,true,true⟩, t.always)]

theorem total_weight (t : Table) : count (fun _ => true) (rows t) = 2 * t.size := by
  simp [count, rows, Table.size]; omega

def population (t : Table) (h : 0 < t.size) : Population Noise where
  rows := rows t
  positive := by rw [total_weight]; omega

/-- Each of the four exact (unnormalized) observed cell probabilities;
the denominator is the identifiable total population size 2N. -/
def observed (t : Table) (x y : Bool) : Nat := count (fun u =>
  let v := evaluate trial (natural [2,2]) u
  (v.2.1 == bit x) && (v.1 == bit y)) (rows t)

theorem observed_table (t : Table) (x y : Bool) : observed t x y =
    (if x then (if y then t.treated else t.size - t.treated)
     else (if y then t.control else t.size - t.control)) := by
  cases x <;> cases y <;>
    simp [observed, count, rows, trial, evaluate, natural, bit, Table.size,
      Table.treated, Table.control] <;> omega

/-- Number of units benefiting in the full doubled population, evaluated
by surgical intervention twice on the same exogenous state. -/
def benefitCount (t : Table) : Nat := count (fun u =>
  ((evaluate trial (doX false) u).1 == 0) && ((evaluate trial (doX true) u).1 == 1)) (rows t)

theorem benefit_count (t : Table) : benefitCount t = 2 * t.helped := by
  simp [benefitCount, count, rows, trial, evaluate, doX, bit]; omega

/-- Among factual untreated nonresponders, what fraction would have responded
to treatment? Zero evidence is returned as none. -/
def effectAmongUntreatedNonresponders (t : Table) (h : 0 < t.size) : Option Rat :=
  conditional (population t h) trial (doX true)
    (fun v => (v.2.1 == 0) && (v.1 == 0)) (fun v => v.1 == 1)

theorem conditional_value (t : Table) (h : 0 < t.size) :
    effectAmongUntreatedNonresponders t h =
      (if t.never + t.helped = 0 then none else some (mkRat t.helped (t.never + t.helped))) := by
  simp [effectAmongUntreatedNonresponders, conditional, population, count, rows, trial,
    evaluate, natural, doX, bit]

/-- Each margin is a count per N subjects in one arm. -/
def lower (control treated : Nat) := treated - control
def upper (n control treated : Nat) := min treated (n - control)

def realizes (t : Table) (n control treated : Nat) : Prop :=
  t.size = n ∧ t.control = control ∧ t.treated = treated

theorem necessary (t : Table) (h : realizes t n c r) :
    lower c r ≤ t.helped ∧ t.helped ≤ upper n c r := by
  rcases h with ⟨hn, hc, hr⟩
  simp only [Table.size, Table.control, Table.treated] at hn hc hr
  simp only [lower, upper, Nat.le_min]
  omega

/-- Candidate joint law reconstructed from a proposed helped-cell count. -/
def complete (n c r k : Nat) : Table :=
  { never := n - c - k, helped := k, harmed := c - (r - k), always := r - k }

theorem attain (hc : c ≤ n) (hk : lower c r ≤ k) (hu : k ≤ upper n c r) :
    realizes (complete n c r k) n c r ∧ (complete n c r k).helped = k := by
  simp only [lower] at hk
  simp only [upper, Nat.le_min] at hu
  simp only [realizes, complete, Table.size, Table.control, Table.treated]
  have hrc : r - k ≤ c := by omega
  have htail := Nat.sub_add_cancel hrc
  rw [Nat.sub_add_cancel hu.2, Nat.add_assoc (n - c), htail, Nat.sub_add_cancel hc,
    Nat.add_sub_of_le hu.1]
  simp

/-- Every grid point in the reported interval is attained by an explicit SCM,
and every compatible SCM in this finite family gives a point in the interval. -/
theorem sharp (hc : c ≤ n) (_hr : r ≤ n) :
    (∃ t : Table, realizes t n c r ∧ benefitCount t = 2*k) ↔
      lower c r ≤ k ∧ k ≤ upper n c r := by
  constructor
  · rintro ⟨t, ht, hk⟩
    rw [benefit_count] at hk
    have h := necessary t ht
    omega
  · rintro ⟨hl, hu⟩
    obtain ⟨ht, he⟩ := attain hc hl hu
    exact ⟨complete n c r k, ht, by rw [benefit_count, he]⟩

theorem feasible (hc : c ≤ n) (hr : r ≤ n) : lower c r ≤ upper n c r := by
  simp [lower, upper, Nat.le_min]; omega

/-- Equality of actual observational tables (all four cells) computed by the
SCM evaluator under common margins. -/
theorem same_observations (hs : realizes s n c r) (ht : realizes t n c r) :
    observed s = observed t := by
  rcases hs with ⟨hsn, hsc, hsr⟩
  rcases ht with ⟨htn, htc, htr⟩
  funext x y
  simp only [observed_table, hsn, hsc, hsr, htn, htc, htr]

/-- A point-identification criterion for this entire finite family. A
non-singleton interval furnishes two independently enumerated observationally
equivalent laws with unequal shared-noise effects. -/
theorem identified_iff (hc : c ≤ n) (hr : r ≤ n) :
    (∀ s t : Table, realizes s n c r → realizes t n c r → observed s = observed t →
      benefitCount s = benefitCount t) ↔ lower c r = upper n c r := by
  constructor
  · intro unique
    have bounds := feasible hc hr
    obtain ⟨hs, ks⟩ := attain hc (Nat.le_refl _) bounds
    obtain ⟨ht, kt⟩ := attain hc bounds (Nat.le_refl _)
    have e := unique _ _ hs ht (same_observations hs ht)
    rw [benefit_count, benefit_count, ks, kt] at e
    omega
  · intro h s t hs ht _
    obtain ⟨ls, us⟩ := necessary s hs
    obtain ⟨lt, ut⟩ := necessary t ht
    rw [benefit_count, benefit_count]
    omega

/-- Interventional arm marginals, evaluated even for subjects whose original
assignment differs. -/
def interventional (t : Table) (x : Bool) : Nat := count (fun u =>
  (evaluate trial (doX x) u).1 == 1) (rows t)

theorem arm_totals (t : Table) (x : Bool) :
    interventional t x = 2 * (if x then t.treated else t.control) := by
  cases x <;> simp [interventional, count, rows, trial, evaluate, doX, bit,
    Table.control, Table.treated] <;> omega

/-- Both models agree on all trial cells and interventional marginals. The
counterfactual among untreated nonresponders nevertheless changes from zero to
one. Varying extra changes the common normalized observable law. -/
theorem opposite_conditionals (m extra : Nat) (hm : 0 < m) :
    let same : Table := ⟨m, 0, 0, m + extra⟩
    let flip : Table := ⟨0, m, m, extra⟩
    ∃ hs : 0 < same.size, ∃ hf : 0 < flip.size,
      observed same = observed flip ∧ interventional same = interventional flip ∧
      effectAmongUntreatedNonresponders same hs = some 0 ∧
      effectAmongUntreatedNonresponders flip hf = some 1 := by
  dsimp
  have hs : 0 < (Table.mk m 0 0 (m + extra)).size := by simp [Table.size]; omega
  have hf : 0 < (Table.mk 0 m m extra).size := by simp [Table.size]; omega
  refine ⟨hs, hf, ?_, ?_, ?_, ?_⟩
  · funext x y; simp [observed_table, Table.size, Table.control, Table.treated, Nat.add_assoc]
  · funext x; simp [arm_totals, Table.control, Table.treated]
  · rw [conditional_value]; simp [Nat.ne_zero_of_lt hm, ← Rat.divInt_ofNat]
  · rw [conditional_value]; simp [Nat.ne_zero_of_lt hm, ← Rat.divInt_ofNat,
      Rat.divInt_self']

/-- A receiver consumes counts from a separately supplied randomized trial
and a proposed closed interval of helped counts. Invalid/empty populations
are outside the domain of this checker. -/
def checkInterval (n c r lo hi : Nat) : Bool :=
  decide (0 < n ∧ c ≤ n ∧ r ≤ n ∧ lo = lower c r ∧ hi = upper n c r)

theorem accepted_interval_sound (h : checkInterval n c r lo hi = true) :
    0 < n ∧ ∀ k, (∃ t : Table, realizes t n c r ∧ benefitCount t = 2*k) ↔
      lo ≤ k ∧ k ≤ hi := by
  obtain ⟨hn, hc, hr, rfl, rfl⟩ := of_decide_eq_true h
  exact ⟨hn, fun _ => sharp hc hr⟩

/-- An accepted closed interval is uniquely determined by the achievable
effects. This converse excludes refusing a valid nonempty observed table
or accepting an arbitrary inner/outer approximation. -/
theorem accepted_iff_exact (hn : 0 < n) (hc : c ≤ n) (hr : r ≤ n) :
    checkInterval n c r lo hi = true ↔
      ∀ k, (∃ t : Table, realizes t n c r ∧ benefitCount t = 2*k) ↔ lo ≤ k ∧ k ≤ hi := by
  constructor
  · intro h; exact (accepted_interval_sound h).2
  · intro exactBounds
    have feasible' := feasible hc hr
    have incl (k : Nat) := (sharp (k := k) hc hr).symm.trans (exactBounds k)
    have left := (incl (lower c r)).mp ⟨Nat.le_refl _, feasible'⟩
    have right := (incl (upper n c r)).mp ⟨feasible', Nat.le_refl _⟩
    have order : lo ≤ hi := Nat.le_trans left.1 left.2
    have left' := (incl lo).mpr ⟨Nat.le_refl _, order⟩
    have right' := (incl hi).mpr ⟨order, Nat.le_refl _⟩
    exact decide_eq_true ⟨hn, hc, hr, Nat.le_antisymm left.1 left'.1,
      Nat.le_antisymm right'.2 right.2⟩

end PcsPccr.SharpResponseBounds
