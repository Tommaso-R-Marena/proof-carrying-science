import Std
namespace ScopePilot

abbrev Profile := Bool × Bool
inductive Formula where
  | tag | inspected | neg (p : Formula) | conj (p q : Formula)
  | disj (p q : Formula) | impl (p q : Formula) | iff (p q : Formula)
  | all (p : Formula) | someObj (p : Formula)

def truth {D : Type} (profile : D → Profile) (x : D) : Formula → Prop
  | .tag => (profile x).1 = true
  | .inspected => (profile x).2 = true
  | .neg p => ¬truth profile x p
  | .conj p q => truth profile x p ∧ truth profile x q
  | .disj p q => truth profile x p ∨ truth profile x q
  | .impl p q => truth profile x p → truth profile x q
  | .iff p q => truth profile x p ↔ truth profile x q
  | .all p => ∀ a, truth profile a p
  | .someObj p => ∃ a, truth profile a p

/-- Multiplicity is immaterial even on infinite domains. For one-variable formulas,
matching assignments and surjective coverage of profiles in both directions suffice. -/
theorem profileInvariant {D E : Type} (d : D → Profile) (e : E → Profile)
    (forward : ∀ x, ∃ y, d x = e y) (back : ∀ y, ∃ x, d x = e y)
    (p : Formula) : ∀ x y, d x = e y → (truth d x p ↔ truth e y p) := by
  induction p with
  | tag | inspected => intro x y h; simp [truth, h]
  | neg _ ih => intro x y h; exact not_congr (ih x y h)
  | conj _ _ ih jh => intro x y h; exact and_congr (ih x y h) (jh x y h)
  | disj _ _ ih jh => intro x y h; exact or_congr (ih x y h) (jh x y h)
  | impl _ _ ih jh => intro x y h; exact imp_congr (ih x y h) (jh x y h)
  | iff _ _ ih jh => intro x y h; exact iff_congr (ih x y h) (jh x y h)
  | all _ ih =>
    intro _ _ _; constructor
    · intro h b
      obtain ⟨a, hab⟩ := back b
      exact (ih a b hab).mp (h a)
    · intro h a
      obtain ⟨b, hab⟩ := forward a
      exact (ih a b hab).mpr (h b)
  | someObj _ ih =>
    intro _ _ _; constructor
    · rintro ⟨a, ha⟩
      obtain ⟨b, hab⟩ := forward a
      exact ⟨b, (ih a b hab).mp ha⟩
    · rintro ⟨b, hb⟩
      obtain ⟨a, hab⟩ := back b
      exact ⟨a, (ih a b hab).mpr hb⟩
#print axioms profileInvariant
end ScopePilot
