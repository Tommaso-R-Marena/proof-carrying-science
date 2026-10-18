import PcsEpistemic.Evidence

/-!
Partial-order and non-promotion laws for the evidence lattice.
Exhaustive finite case analysis.
-/
set_option autoImplicit false

namespace PcsEpistemic

theorem le_antisymm
    (a b : EvidenceClass)
    (h1 : a.le b = true) (h2 : b.le a = true) : a = b := by
  cases a <;> cases b <;> simp [EvidenceClass.le] at h1 h2 <;> try rfl

theorem le_trans
    (a b c : EvidenceClass)
    (h1 : a.le b = true) (h2 : b.le c = true) : a.le c = true := by
  cases a <;> cases b <;> cases c <;> simp [EvidenceClass.le] at h1 h2 ⊢

theorem computational_incomparable_empirical :
    EvidenceClass.computational.le .empirical = false ∧
      EvidenceClass.empirical.le .computational = false :=
  ⟨rfl, rfl⟩

theorem formal_incomparable_empirical :
    EvidenceClass.formal.le .empirical = false ∧
      EvidenceClass.empirical.le .formal = false :=
  ⟨rfl, rfl⟩

/-- Provenance evidence discharges only provenance obligations. -/
theorem provenance_discharges_only_self
    (c : EvidenceClass) (hc : c ≠ .provenance) :
    EvidenceClass.provenance.le c = false := by
  cases c <;> first | exact (hc rfl).elim | rfl

/-- Every evidence class discharges a provenance obligation. -/
theorem anything_covers_provenance (c : EvidenceClass) :
    c.le .provenance = true := by
  cases c <;> rfl

theorem meet_comm (a b : EvidenceClass) : a.meet b = b.meet a := by
  cases a <;> cases b <;> rfl

theorem meet_idem (a : EvidenceClass) : a.meet a = a := by
  cases a <;> rfl

/-- Heterogeneous formal/empirical meet collapses; it is not a lattice GLB witness
    for scientific discharge and must not be treated as one. -/
theorem meet_formal_empirical_collapses :
    EvidenceClass.formal.meet .empirical = .provenance :=
  rfl

theorem join_computational_empirical :
    EvidenceClass.computational.join .empirical = .formal :=
  rfl

theorem join_empirical_computational :
    EvidenceClass.empirical.join .computational = .formal :=
  rfl

end PcsEpistemic
