import Std

/-! Finite research model. A reviewer supplies a list of possible interpretations, a
claim predicate on those interpretations, and observations grouped by common source.
A withdrawal erases entire groups. Interpretation coverage and observation custody
must be justified by the application. -/
namespace PCSResearch.Withdrawal

def cost (groups : List G) (mask : G → Bool) : Nat := groups.countP mask

def survives (groups : List G) (agrees : W → G → Bool) (drop : G → Bool) (w : W) : Prop :=
  ∀ g ∈ groups, agrees w g = true ∨ drop g = true

def conflicts (agrees : W → G → Bool) (w : W) : G → Bool := fun g => !(agrees w g)

theorem cost_mono (groups : List G) (a b : G → Bool)
    (incl : ∀ g ∈ groups, a g = true → b g = true) : cost groups a ≤ cost groups b := by
  induction groups with
  | nil => simp [cost]
  | cons g gs ih =>
    have head := incl g (by simp)
    have tail := ih (fun x hx => incl x (by simp [hx]))
    cases ha : a g <;> cases hb : b g <;> simp_all [cost] <;> omega

/-- Minimum withdrawal needed to retain one specified interpretation. -/
theorem minimum_for_world (gs : List G) (a : W → G → Bool) (w : W) (k : Nat) :
    (∃ d : G → Bool, cost gs d ≤ k ∧ survives gs a d w) ↔ cost gs (conflicts a w) ≤ k := by
  constructor
  · rintro ⟨d, budget, ok⟩
    apply Nat.le_trans _ budget
    apply cost_mono
    intro g hg h
    rcases ok g hg with ha | hd
    · simp [conflicts, ha] at h
    · exact hd
  · intro h
    refine ⟨conflicts a w, h, ?_⟩
    intro g _
    cases ha : a w g <;> simp [conflicts, ha]

/-- Abstain on an inconsistent starting exercise. A sufficient conclusion must have
at least one live interpretation and cover every surviving interpretation. -/
def grounded (ws : List W) (gs : List G) (a : W → G → Bool) : Prop :=
  ∃ w ∈ ws, survives gs a (fun _ => false) w

def robust (ws : List W) (gs : List G) (a : W → G → Bool) (good : W → Bool) (k : Nat) : Prop :=
  grounded ws gs a ∧ ∀ d : G → Bool, cost gs d ≤ k →
    ∀ w ∈ ws, survives gs a d w → good w = true

def check (ws : List W) (gs : List G) (a : W → G → Bool) (good : W → Bool) (k : Nat) : Bool :=
  ws.any (fun w => gs.all (a w)) &&
    ws.all (fun w => good w || decide (k < cost gs (conflicts a w)))

theorem check_exact (ws : List W) (gs : List G) (a : W → G → Bool) (good : W → Bool) (k : Nat) :
    check ws gs a good k = true ↔ robust ws gs a good k := by
  simp only [check, Bool.and_eq_true, List.any_eq_true, List.all_eq_true, Bool.or_eq_true,
    decide_eq_true_eq]
  constructor
  · rintro ⟨⟨v, hv, agree⟩, safe⟩
    refine ⟨⟨v, hv, fun g hg => Or.inl (agree g hg)⟩, ?_⟩
    intro d budget w hw ok
    rcases safe w hw with h | h
    · exact h
    · have bound := (minimum_for_world gs a w k).mp ⟨d, budget, ok⟩
      omega
  · rintro ⟨⟨v, hv, agree⟩, safe⟩
    refine ⟨⟨v, hv, fun g hg => ?_⟩, ?_⟩
    · simpa using agree g hg
    · intro w hw
      by_cases h : k < cost gs (conflicts a w)
      · exact Or.inr h
      · obtain ⟨d, budget, ok⟩ := (minimum_for_world gs a w k).mpr (Nat.le_of_not_gt h)
        exact Or.inl (safe d budget w hw ok)

/-- Witness for circular corroboration. Conflicting records copied from one source
can inflate the withdrawal count if the issuer repeats the source identifier. -/
example : check [false,true] [0,0] (fun w (_ : Nat) => w) id 1 = true := by decide
example : check [false,true] [0] (fun w (_ : Nat) => w) id 1 = false := by decide

#print axioms cost_mono
#print axioms minimum_for_world
#print axioms check_exact
end PCSResearch.Withdrawal
