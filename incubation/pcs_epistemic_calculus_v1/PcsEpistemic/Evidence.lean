import Std

/-!
# Graded evidence classes for proof-carrying science

Four evidence classes remain distinct. Computational or provenance support must
never silently discharge a formal or empirical obligation. This module is the
lattice substrate for composition, invalidation, and scientific dialectic.
-/
set_option autoImplicit false

namespace PcsEpistemic

inductive EvidenceClass where
  | formal
  | computational
  | empirical
  | provenance
  deriving DecidableEq, Repr, Inhabited

/-- Partial order on evidence strength for discharging claim obligations.
    Formal is strongest for mathematical claims; computational and empirical
    are incomparable; provenance never discharges scientific content. -/
def EvidenceClass.le : EvidenceClass → EvidenceClass → Bool
  | .provenance, .provenance => true
  | .computational, .computational => true
  | .computational, .formal => false
  | .empirical, .empirical => true
  | .empirical, .formal => false
  | .formal, .formal => true
  | .formal, .computational => true
  | .formal, .empirical => false
  | .computational, .empirical => false
  | .empirical, .computational => false
  | .provenance, _ => false
  | _, .provenance => true

theorem EvidenceClass.le_refl (c : EvidenceClass) : c.le c = true := by
  cases c <;> rfl

/-- Non-promotion: computational evidence cannot authorize a formal claim. -/
theorem no_computational_to_formal :
    EvidenceClass.computational.le .formal = false := rfl

/-- Non-promotion: provenance never authorizes formal content. -/
theorem no_provenance_to_formal :
    EvidenceClass.provenance.le .formal = false := rfl

/-- Non-promotion: provenance never authorizes empirical content. -/
theorem no_provenance_to_empirical :
    EvidenceClass.provenance.le .empirical = false := rfl

/-- Formal evidence may discharge a computational obligation. -/
theorem formal_covers_computational :
    EvidenceClass.formal.le .computational = true := rfl

/-- Meet for combining required obligation classes (greatest lower bound
    approximation used by dialectic agreement cores). -/
def EvidenceClass.meet : EvidenceClass → EvidenceClass → EvidenceClass
  | .formal, .formal => .formal
  | .formal, .computational => .computational
  | .computational, .formal => .computational
  | .computational, .computational => .computational
  | .empirical, .empirical => .empirical
  | .provenance, c => c
  | c, .provenance => c
  | .formal, .empirical => .provenance
  | .empirical, .formal => .provenance
  | .computational, .empirical => .provenance
  | .empirical, .computational => .provenance

/-- Join used when composing heterogeneous evidence sets for reporting. -/
def EvidenceClass.join : EvidenceClass → EvidenceClass → EvidenceClass
  | .formal, _ => .formal
  | _, .formal => .formal
  | .empirical, .computational => .formal
  | .computational, .empirical => .formal
  | .empirical, .empirical => .empirical
  | .computational, .computational => .computational
  | .provenance, c => c
  | c, .provenance => c

end PcsEpistemic
