import ScientificReasoning.Soundness

/-!
# Contradiction containment (no ex falso)

Classical semantic entailment explodes on unsatisfiable contexts. Our
non-explosion claim is about **derivability** in a calculus without ExFalso.
-/

namespace ScientificReasoning

def Formula.atoms : Formula → List PropId
  | .atom i => [i]
  | .not φ => Formula.atoms φ
  | .and φ ψ => Formula.atoms φ ++ Formula.atoms ψ

def Context.atoms (Γ : Context) : List PropId :=
  Γ.premises.flatMap (fun p => Formula.atoms p.formula)

theorem derives_atoms_from_context
    (Γ : Context) (S : Support) (a : Authority) (φ : Formula)
    (h : Derives Γ S a φ) :
    ∀ i ∈ Formula.atoms φ, i ∈ Context.atoms Γ := by
  induction h with
  | hyp p hp =>
      intro i hi
      unfold Context.atoms
      exact List.mem_flatMap.2 ⟨p, hp, hi⟩
  | andI S T a b φ ψ hφ hψ ihφ ihψ =>
      intro i hi
      simp [Formula.atoms] at hi
      cases hi with
      | inl h1 => exact ihφ i h1
      | inr h2 => exact ihψ i h2
  | andE1 S a φ ψ hand ih =>
      intro i hi
      exact ih i (by simp [Formula.atoms, hi])
  | andE2 S a φ ψ hand ih =>
      intro i hi
      exact ih i (by simp [Formula.atoms, List.mem_append, hi])

def LocallyContradictory (Γ : Context) : Prop :=
  ∃ (S T : Support) (a b : Authority) (φ : Formula),
    Derives Γ S a φ ∧ Derives Γ T b (Formula.not φ)

def p0 : Premise :=
  { id := 0, formula := Formula.atom 0, authority := Authority.empiricalAsserted }

def p1 : Premise :=
  { id := 1, formula := Formula.not (Formula.atom 0), authority := Authority.empiricalAsserted }

def p2 : Premise :=
  { id := 2, formula := Formula.atom 2, authority := Authority.hypothesis }

def demoΓ : Context := { premises := [p0, p1, p2] }

theorem demo_derives_P :
    Derives demoΓ [0] Authority.empiricalAsserted (Formula.atom 0) :=
  Derives.hyp demoΓ p0 (by simp [demoΓ])

theorem demo_derives_notP :
    Derives demoΓ [1] Authority.empiricalAsserted (Formula.not (Formula.atom 0)) :=
  Derives.hyp demoΓ p1 (by simp [demoΓ])

theorem demo_locally_contradictory : LocallyContradictory demoΓ :=
  ⟨[0], [1], Authority.empiricalAsserted, Authority.empiricalAsserted, Formula.atom 0,
    demo_derives_P, demo_derives_notP⟩

theorem demo_atoms_no_99 : 99 ∉ Context.atoms demoΓ := by
  simp [Context.atoms, demoΓ, p0, p1, p2, Formula.atoms]

/-- Non-explosion (derivability): unrelated atom 99 is not derivable from demoΓ. -/
theorem no_ex_falso_unrelated_atom
    (S : Support) (a : Authority)
    (h : Derives demoΓ S a (Formula.atom 99)) : False := by
  have hat := derives_atoms_from_context demoΓ S a (Formula.atom 99) h 99 (by simp [Formula.atoms])
  exact demo_atoms_no_99 hat

/-- Classical Boolean models of `demoΓ` do not exist (P ∧ ¬P premises). -/
theorem demoΓ_classically_unsatisfiable :
    ¬ ∃ σ : Assignment, Context.satisfied demoΓ σ := by
  intro ⟨σ, hsat⟩
  have h0 : Formula.eval σ (Formula.atom 0) = true := by
    simpa [p0] using hsat p0 (by simp [demoΓ])
  have h1 : Formula.eval σ (Formula.not (Formula.atom 0)) = true := by
    simpa [p1] using hsat p1 (by simp [demoΓ])
  simp [Formula.eval] at h0 h1
  cases hσ : σ 0 <;> simp [hσ] at h0 h1

/-- **Break point:** classical `Entails` explodes on inconsistent Γ (vacuous truth). -/
theorem classical_entails_explodes_on_demoΓ (φ : Formula) : Entails demoΓ φ := by
  intro σ hsat
  exact (demoΓ_classically_unsatisfiable ⟨σ, hsat⟩).elim

/-- In particular classical Entails yields atom 99 — unlike derivability / Entails4. -/
theorem classical_entails_atom99_demoΓ : Entails demoΓ (Formula.atom 99) :=
  classical_entails_explodes_on_demoΓ _

end ScientificReasoning

#print axioms ScientificReasoning.derives_atoms_from_context
#print axioms ScientificReasoning.no_ex_falso_unrelated_atom
#print axioms ScientificReasoning.demo_locally_contradictory
#print axioms ScientificReasoning.demoΓ_classically_unsatisfiable
#print axioms ScientificReasoning.classical_entails_explodes_on_demoΓ
