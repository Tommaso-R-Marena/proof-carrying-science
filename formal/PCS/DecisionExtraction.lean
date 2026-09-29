import PCS.Refinement

namespace PCS.DecisionExtraction

open PCS.Decision
open PCS.Refinement

/-! Proof-internal helpers for the extraction lemmas. -/

/-- If no selected required evidence is FAIL or UNVERIFIED, all of it is PASS. -/
private theorem passes_of_no_bad {c : Claim} {es : List Evidence}
    (hf : hasOutcome Outcome.fail (requiredEvidenceFor c es) = false)
    (hu : hasOutcome Outcome.unverified (requiredEvidenceFor c es) = false) :
    RequiredEvidencePasses c es := by
  intro e he
  simp only [hasOutcome, List.any_eq_false, beq_iff_eq] at hf hu
  have h1 := hf e he
  have h2 := hu e he
  cases ho : e.outcome <;> simp_all

/-- A successful `hasKind` check yields a witness of that kind. -/
private theorem hasKind_witness {k : EvidenceKind} {es : List Evidence}
    (h : hasKind k es = true) : ∃ e, e ∈ es ∧ e.kind = k := by
  simpa [hasKind] using h

/-- A successful `allKind` check on a nonempty list yields a witness of that kind. -/
private theorem allKind_witness {k : EvidenceKind} {es : List Evidence}
    (h : allKind k es = true) (hne : es.isEmpty = false) : ∃ e, e ∈ es ∧ e.kind = k := by
  cases es with
  | nil => simp at hne
  | cons x xs => exact ⟨x, List.mem_cons_self, by simp [allKind] at h; exact h.1⟩

/-- Any status other than OPEN/FAILED passes the four guard checks of `decideClaim`. -/
private theorem prefix_of_accepted {c : Claim} {es : List Evidence}
    (hopen : decideClaim c es ≠ DecisionStatus.open_)
    (hfail : decideClaim c es ≠ DecisionStatus.failed) :
    missingRequiredEvidence c es = false ∧
    hasOutcome Outcome.fail (requiredEvidenceFor c es) = false ∧
    hasOutcome Outcome.unverified (requiredEvidenceFor c es) = false ∧
    (requiredEvidenceFor c es).isEmpty = false := by
  unfold decideClaim at hopen hfail
  simp only at hopen hfail
  cases hm : missingRequiredEvidence c es <;> simp only [hm] at hopen hfail
  · cases hf : hasOutcome Outcome.fail (requiredEvidenceFor c es) <;> simp only [hf] at hopen hfail
    · cases hu : hasOutcome Outcome.unverified (requiredEvidenceFor c es) <;> simp [hu] at hopen hfail
      cases he : (requiredEvidenceFor c es).isEmpty <;> simp_all
    · simp at hfail
  · simp at hopen

/-- Any accepted status is produced by the claim-kind branch of `decideClaim`. -/
private theorem accepted_branch {c : Claim} {es : List Evidence} {s : DecisionStatus}
    (h : decideClaim c es = s)
    (hopen : s ≠ DecisionStatus.open_) (hfail : s ≠ DecisionStatus.failed) :
    RequiredEvidencePasses c es ∧
    (requiredEvidenceFor c es).isEmpty = false ∧
    (match c.kind with
    | ClaimKind.formal =>
        if allKind EvidenceKind.formalProof (requiredEvidenceFor c es)
        then DecisionStatus.formal
        else DecisionStatus.open_
    | ClaimKind.empirical =>
        if hasKind EvidenceKind.empiricalValidation (requiredEvidenceFor c es) ||
           hasKind EvidenceKind.statisticalValidation (requiredEvidenceFor c es)
        then DecisionStatus.empirical
        else DecisionStatus.open_
    | ClaimKind.mixed =>
        if hasKind EvidenceKind.formalProof (requiredEvidenceFor c es) &&
           (hasKind EvidenceKind.empiricalValidation (requiredEvidenceFor c es) ||
            hasKind EvidenceKind.statisticalValidation (requiredEvidenceFor c es))
        then DecisionStatus.mixed
        else DecisionStatus.open_
    | ClaimKind.computational =>
        if hasKind EvidenceKind.computationalTest (requiredEvidenceFor c es) ||
           hasKind EvidenceKind.formalProof (requiredEvidenceFor c es)
        then DecisionStatus.computational
        else DecisionStatus.open_) = s := by
  subst h
  obtain ⟨hm, hf, hu, hne⟩ := prefix_of_accepted hopen hfail
  refine ⟨passes_of_no_bad hf hu, hne, ?_⟩
  simp only [decideClaim, hm, hf, hu, hne, Bool.false_eq_true, ↓reduceIte]
  rfl

theorem decideClaim_computational_extract
    {c : Claim} {es : List Evidence}
    (h : decideClaim c es = DecisionStatus.computational) :
    c.kind = ClaimKind.computational ∧
    RequiredEvidencePasses c es ∧
    (∃ e, e ∈ requiredEvidenceFor c es ∧
      (e.kind = EvidenceKind.computationalTest ∨
       e.kind = EvidenceKind.formalProof)) := by
  obtain ⟨passes, _, hb⟩ := accepted_branch h (by decide) (by decide)
  cases hk : c.kind <;> simp only [hk] at hb <;> split at hb <;> try cases hb
  rename_i hkinds
  refine ⟨rfl, passes, ?_⟩
  rcases Bool.or_eq_true_iff.mp hkinds with hkind | hkind
  · obtain ⟨e, he, ek⟩ := hasKind_witness hkind
    exact ⟨e, he, Or.inl ek⟩
  · obtain ⟨e, he, ek⟩ := hasKind_witness hkind
    exact ⟨e, he, Or.inr ek⟩

theorem decideClaim_formal_extract
    {c : Claim} {es : List Evidence}
    (h : decideClaim c es = DecisionStatus.formal) :
    c.kind = ClaimKind.formal ∧
    RequiredEvidencePasses c es ∧
    (∃ e, e ∈ requiredEvidenceFor c es ∧
      e.kind = EvidenceKind.formalProof) := by
  obtain ⟨passes, hne, hb⟩ := accepted_branch h (by decide) (by decide)
  cases hk : c.kind <;> simp only [hk] at hb <;> split at hb <;> try cases hb
  rename_i hall
  exact ⟨rfl, passes, allKind_witness hall hne⟩

theorem decideClaim_empirical_extract
    {c : Claim} {es : List Evidence}
    (h : decideClaim c es = DecisionStatus.empirical) :
    c.kind = ClaimKind.empirical ∧
    RequiredEvidencePasses c es ∧
    (∃ e, e ∈ requiredEvidenceFor c es ∧
      (e.kind = EvidenceKind.empiricalValidation ∨
       e.kind = EvidenceKind.statisticalValidation)) := by
  obtain ⟨passes, _, hb⟩ := accepted_branch h (by decide) (by decide)
  cases hk : c.kind <;> simp only [hk] at hb <;> split at hb <;> try cases hb
  rename_i hkinds
  refine ⟨rfl, passes, ?_⟩
  rcases Bool.or_eq_true_iff.mp hkinds with hkind | hkind
  · obtain ⟨e, he, ek⟩ := hasKind_witness hkind
    exact ⟨e, he, Or.inl ek⟩
  · obtain ⟨e, he, ek⟩ := hasKind_witness hkind
    exact ⟨e, he, Or.inr ek⟩

theorem decideClaim_mixed_extract
    {c : Claim} {es : List Evidence}
    (h : decideClaim c es = DecisionStatus.mixed) :
    c.kind = ClaimKind.mixed ∧
    RequiredEvidencePasses c es ∧
    (∃ correctness,
      correctness ∈ requiredEvidenceFor c es ∧
      correctness.kind = EvidenceKind.formalProof) ∧
    (∃ empiricalEvidence,
      empiricalEvidence ∈ requiredEvidenceFor c es ∧
      (empiricalEvidence.kind = EvidenceKind.empiricalValidation ∨
       empiricalEvidence.kind = EvidenceKind.statisticalValidation)) := by
  obtain ⟨passes, _, hb⟩ := accepted_branch h (by decide) (by decide)
  cases hk : c.kind <;> simp only [hk] at hb <;> split at hb <;> try cases hb
  rename_i hkinds
  obtain ⟨hformal, hemp⟩ := Bool.and_eq_true_iff.mp hkinds
  refine ⟨rfl, passes, hasKind_witness hformal, ?_⟩
  rcases Bool.or_eq_true_iff.mp hemp with hkind | hkind
  · obtain ⟨e, he, ek⟩ := hasKind_witness hkind
    exact ⟨e, he, Or.inl ek⟩
  · obtain ⟨e, he, ek⟩ := hasKind_witness hkind
    exact ⟨e, he, Or.inr ek⟩

theorem decideClaim_computational_sound
    {Γ : List Assumption} {c : Claim} {es : List Evidence}
    (context : ContextCovers Γ c)
    (binding : RequiredEvidenceBound c es)
    (h : decideClaim c es = DecisionStatus.computational) :
    Assures Γ AssuranceLevel.computational c es := by
  rcases decideClaim_computational_extract h with
    ⟨claimKind, passes, witness⟩
  exact computational_claim_sound
    context claimKind passes binding witness

theorem decideClaim_formal_sound
    {Γ : List Assumption} {c : Claim} {es : List Evidence}
    (context : ContextCovers Γ c)
    (binding : RequiredEvidenceBound c es)
    (h : decideClaim c es = DecisionStatus.formal) :
    Assures Γ AssuranceLevel.formal c es := by
  rcases decideClaim_formal_extract h with
    ⟨claimKind, passes, witness⟩
  exact formal_claim_sound
    context claimKind passes binding witness

theorem decideClaim_empirical_sound
    {Γ : List Assumption} {c : Claim} {es : List Evidence}
    (context : ContextCovers Γ c)
    (binding : RequiredEvidenceBound c es)
    (h : decideClaim c es = DecisionStatus.empirical) :
    Assures Γ AssuranceLevel.empirical c es := by
  rcases decideClaim_empirical_extract h with
    ⟨claimKind, passes, witness⟩
  exact empirical_claim_sound
    context claimKind passes binding witness

theorem decideClaim_mixed_sound
    {Γ : List Assumption} {c : Claim} {es : List Evidence}
    (context : ContextCovers Γ c)
    (binding : RequiredEvidenceBound c es)
    (h : decideClaim c es = DecisionStatus.mixed) :
    Assures Γ AssuranceLevel.mixed c es := by
  rcases decideClaim_mixed_extract h with
    ⟨claimKind, passes, correctnessWitness, empiricalWitness⟩
  exact mixed_claim_sound
    context claimKind passes binding
    correctnessWitness empiricalWitness

end PCS.DecisionExtraction
