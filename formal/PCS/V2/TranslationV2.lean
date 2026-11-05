import PCS.V2.TranslationAuthority
import PCS.V2.FiniteModel
import PCS.V2.CertSearch

/-!
# PCS Proof-Carrying Semantic Intelligence v2 — contract, checker, classification

v1 (`PCS.V2.TranslationChecker`) accepts only candidates whose canonical normal form equals
the interpretation's.  v2 keeps every v1 gate (ambiguity, authorized confirmation, grounding,
typing, fragment membership, closedness, binder hygiene, Lean rendering, elaboration and
proof receipts) and replaces the *semantic* gate by a **proof-carrying** one:

    NormalFormEquivalent I C   ∨   ∃ cert, checkCert cert I.normalize C.normalize = true

The certificate may be supplied by the (untrusted) proposer or found by the (untrusted)
bounded search `findCert`; either way only the small replay checker `checkCert` is trusted,
and it is proved sound against the independent semantics.

When the semantic gate fails, v2 runs a bounded **countermodel search** and, if it finds a
registry-conforming finite structure distinguishing the claims, reports a *verified
counterexample* that is re-checked by `checkCountermodel`.

## Outcome classification (`OutcomeV2`)

`CERTIFIED_TRANSLATION`, `VERIFIED_COUNTEREXAMPLE`, `NEEDS_HUMAN_CLARIFICATION`,
`UNRESOLVED_PROOF_OBLIGATION`, `UNSUPPORTED_FRAGMENT`, `SEARCH_EXHAUSTED`,
`INVALID_PROPOSAL`.  Only the first is an acceptance.

## Main theorems

* `accepted_translation_preserves_denotation_v2` — the v2 contract implies, for **every**
  model and valuation, `I.denote M ρ ↔ C.denote M ρ`.
* `decideV2_certified_iff` / `executable_semantic_checker_refines_specification` — the
  executable classifier outputs `CERTIFIED_TRANSLATION` exactly when the v2 contract holds
  for the certificate it reports, and it is complete for proposer-supplied certificates.
* `v1_acceptance_implies_v2_contract` — v2 is a conservative extension of v1.
* `decideV2_counterexample_sound` — a `VERIFIED_COUNTEREXAMPLE` outcome carries a checked
  witness; the claims are then not equivalent, v1 rejects, and no certificate exists.
* `countermodel_and_certificate_exclusive` — the two positive diagnoses can never both hold.
* `semantic_authority_does_not_trust_proposer_metadata` — identity, confidence and
  self-asserted confirmation do not influence the v2 decision.
* `pcs_proof_carrying_translation_sound_v2` — the end-to-end conditional flagship.
-/

set_option autoImplicit false

namespace PCS.V2.Semantic

/-! ## Requests and the v2 contract -/

/-- Effort bounds for the untrusted searches (they influence only *which* certificate or
    countermodel is found, never soundness). -/
structure SearchBounds where
  certDepth : Nat
  certCap : Nat
  modelBound : Nat
  modelBudget : Nat
  deriving Repr, DecidableEq, Inhabited

/-- Default bounds. -/
def SearchBounds.default : SearchBounds := ⟨3, 400, 3, 20000⟩

/-- A v2 request: a v1 request, an optional proposer-supplied certificate, search bounds. -/
structure RequestV2 where
  base : Request
  certificate : Option EquivCert
  bounds : SearchBounds
  deriving Repr, Inhabited

/-- A proposer-supplied explanation (if any) is exactly the derived Explanation IR. -/
def ExplanationFaithful (R : Registry) (cand : Candidate) : Prop :=
  cand.explanation = none ∨ cand.explanation = some (toExplanation R cand.claim)

/-- **The proof-carrying semantic link**: equal normal forms, or a checked certificate. -/
def SemanticallyLinked (I : Interpretation) (cand : Candidate) (cert : Option EquivCert) : Prop :=
  NormalFormEquivalent I cand ∨
    ∃ c, cert = some c ∧ checkCert c I.selected.normalize cand.claim.normalize = true

/-- The non-semantic gates of the contract (identical to v1's). -/
structure GatesV2 (A : Authority) (req : Request) : Prop where
  noUnresolvedAmbiguity : NoUnresolvedAmbiguity req.interpretation
  confirmation : ConfirmationVerified A req
  interpretationGrounded : InterpretationGrounded A.registry req.interpretation
  groundedSymbols : GroundedSymbols A.registry req.candidate
  wellTyped : WellTypedPair A.registry req.interpretation req.candidate
  supportedFragment : SupportedFragment req.interpretation req.candidate
  noUnexpectedFreeVariables : NoUnexpectedFreeVariables req.interpretation req.candidate
  hygienic : req.candidate.claim.hygienicB A.registry = true
  explanationFaithful : ExplanationFaithful A.registry req.candidate
  leanRendering : LeanRenderingFaithful A.registry req.candidate
  elaboration : ElaborationVerified A req
  proof : ProofVerified A req

/-- **The certified v2 translation contract** (relative to the certificate `cert` in use). -/
structure CertifiedContractV2 (A : Authority) (req : Request) (cert : Option EquivCert) : Prop where
  gates : GatesV2 A req
  semanticLink : SemanticallyLinked req.interpretation req.candidate cert

/-! ## Flagship semantic theorem -/

/-- **`accepted_translation_preserves_denotation_v2`.**  If the v2 contract holds (with any
    certificate whatsoever), then for every model `M` and every valuation `ρ` the meaning of
    the explicitly selected interpretation is logically equivalent to the meaning of the
    accepted candidate.  The proof goes through the independent semantics: either the
    denotation-preserving normalization (`alphaEquiv_denote_iff`) or the certificate checker's
    soundness (`translation_certificate_sound`). -/
theorem accepted_translation_preserves_denotation_v2 {A : Authority} {req : Request}
    {cert : Option EquivCert} (h : CertifiedContractV2 A req cert) (M : Model)
    (ρ : String → M.Dom) :
    req.interpretation.selected.denote M ρ ↔ req.candidate.claim.denote M ρ := by
  rcases h.semanticLink with hn | ⟨c, _, hc⟩
  · exact alphaEquiv_denote_iff hn M ρ
  · exact translation_certificate_sound hc M ρ

/-- The derived Explanation IR of an accepted candidate means the selected interpretation. -/
theorem accepted_explanation_means_interpretation_v2 {A : Authority} {req : Request}
    {cert : Option EquivCert} (h : CertifiedContractV2 A req cert) (M : Model)
    (ρ : String → M.Dom) :
    (toExplanation A.registry req.candidate.claim).denote M ρ ↔
      req.interpretation.selected.denote M ρ :=
  (explanationIR_preserves_semantics _ M ρ _).trans
    (accepted_translation_preserves_denotation_v2 h M ρ).symm

/-- **Conservative extension**: every v1 acceptance satisfies the v2 contract with no
    certificate. -/
theorem v1_acceptance_implies_v2_contract {A : Authority} {req : Request}
    (h : translationAccepts A req = true) : CertifiedContractV2 A req none := by
  have c := (translationAccepts_iff A req).mp h
  exact ⟨⟨c.noUnresolvedAmbiguity, c.confirmation, c.interpretationGrounded, c.groundedSymbols,
    c.wellTyped, c.supportedFragment, c.noUnexpectedFreeVariables, c.hygienic, c.roundTrip.2,
    c.leanRendering, c.elaboration, c.proof⟩, Or.inl c.normalFormEquivalent⟩

/-- A checked countermodel makes the v2 contract unsatisfiable for **every** certificate. -/
theorem countermodel_refutes_contract_v2 {A : Authority} {req : Request} {w : Countermodel}
    (hw : checkCountermodel A.registry req.interpretation.selected req.candidate.claim w = true)
    (cert : Option EquivCert) : ¬ CertifiedContractV2 A req cert := by
  intro h
  exact (countermodel_witness_sound hw).2.2.2
    (accepted_translation_preserves_denotation_v2 h w.model.toModel ρ0)

/-- A checked countermodel also makes v1 reject. -/
theorem countermodel_v1_rejected {A : Authority} {req : Request} {w : Countermodel}
    (hw : checkCountermodel A.registry req.interpretation.selected req.candidate.claim w = true) :
    translationAccepts A req = false :=
  semantically_inequivalent_rejected (countermodel_witness_sound hw).2.2.2

/-- **A countermodel and an accepted certificate are mutually exclusive.** -/
theorem countermodel_and_certificate_exclusive (R : Registry) (I C : SemanticClaim)
    (w : Countermodel) (cert : EquivCert) :
    ¬ (checkCountermodel R I C w = true ∧ checkCert cert I.normalize C.normalize = true) := by
  rintro ⟨hw, hc⟩
  rw [countermodel_excludes_certificate hw cert] at hc
  cases hc

/-! ## The executable v2 checker -/

/-- Diagnostic for the explanation gate. -/
def checkExplanationV2 (R : Registry) (cand : Candidate) : List Diagnostic :=
  failIf (match cand.explanation with
      | none => true
      | some e => decide (e = toExplanation R cand.claim))
    ⟨.roundtripMismatch, "candidate.explanation",
      "proposer-supplied explanation differs from the Explanation IR derived from the candidate"⟩

/-- All non-semantic gate diagnostics (the v1 checks minus the structural-semantic ones). -/
def gateDiagnostics (A : Authority) (req : Request) : List Diagnostic :=
  let R := A.registry
  let I := req.interpretation
  let c := req.candidate
  checkAmbiguity I ++ checkConfirmation A req ++ checkRegistry R ++
  checkInterpretationSymbols R I ++ checkCandidateSymbols R c ++ checkGroundingRefs R c ++
  checkTyping R I c ++ checkSupported I c ++ checkFreeVars I c ++ checkHygiene R c ++
  checkExplanationV2 R c ++ checkLeanRendering R c ++ checkElaboration A req ++ checkProof A req

/-- The v1 structural diagnostics, reported (as localisation hints) when the semantic link
    fails. -/
def structuralDiagnostics (I : Interpretation) (c : Candidate) : List Diagnostic :=
  checkQuantifiers I c ++ checkPolarity I c ++ checkNegation I c ++ checkConnectives I c ++
  checkAssumptions I c ++ checkBindings I c ++ checkNormalForm I c

theorem checkExplanationV2_nil (R : Registry) (cand : Candidate) :
    checkExplanationV2 R cand = [] ↔ ExplanationFaithful R cand := by
  unfold checkExplanationV2 ExplanationFaithful
  rw [failIf_nil]
  cases cand.explanation <;> simp

theorem gateDiagnostics_nil (A : Authority) (req : Request) :
    gateDiagnostics A req = [] ↔ GatesV2 A req := by
  unfold gateDiagnostics
  simp only [List.append_eq_nil_iff, checkAmbiguity_nil, checkConfirmation_nil, checkRegistry_nil,
    checkInterpretationSymbols_nil, checkCandidateSymbols_nil, checkGroundingRefs_nil,
    checkTyping_nil, checkSupported_nil, checkFreeVars_nil, checkExplanationV2_nil,
    checkElaboration_nil, checkProof_nil, checkHygiene, checkLeanRendering, failIf_nil,
    decide_eq_true_eq, and_assoc]
  constructor
  · rintro ⟨h1, h2, h3, h4, h5, h6, h7, h8, h9, h10, h11, h12, h13, h14⟩
    exact ⟨h1, h2, h4, ⟨h3, h5, h6⟩, h7, h8, h9, h10, h11, h12, h13, h14⟩
  · rintro ⟨h1, h2, h4, ⟨h3, h5, h6⟩, h7, h8, h9, h10, h11, h12, h13, h14⟩
    exact ⟨h1, h2, h3, h4, h5, h6, h7, h8, h9, h10, h11, h12, h13, h14⟩

/-- Result of the semantic analysis. -/
inductive SemanticStatus where
  /-- equal canonical normal forms (v1 semantic gate) -/
  | normalFormEqual
  /-- a checked equivalence certificate -/
  | certified (c : EquivCert)
  /-- a checked finite countermodel -/
  | counterexample (w : Countermodel)
  /-- neither: the bounded searches did not settle the question -/
  | unknown (search : SearchOutcome)
  deriving Repr, DecidableEq, Inhabited

/-- The countermodel phase (bounded search, every result re-checked). -/
def countermodelPhase (R : Registry) (I C : SemanticClaim) (b : SearchBounds) : SemanticStatus :=
  match searchCountermodel R I C b.modelBound b.modelBudget with
  | .found F =>
    if checkCountermodel R I C (mkWitness I C F) then .counterexample (mkWitness I C F)
    else .unknown (.found F)
  | o => .unknown o

/-- **Semantic analysis**: normal forms, then the supplied certificate, then the untrusted
    certificate search (re-checked), then the countermodel search. -/
def semanticAnalysis (R : Registry) (I C : SemanticClaim) (cert : Option EquivCert)
    (b : SearchBounds) : SemanticStatus :=
  if I.normalize.equivB C.normalize then .normalFormEqual
  else match cert with
    | some c => if checkCert c I.normalize C.normalize then .certified c
      else countermodelPhase R I C b
    | none =>
      match findCheckedCert b.certDepth b.certCap I.normalize C.normalize with
      | some c => .certified c
      | none => countermodelPhase R I C b

/-- v2 outcome classes. -/
inductive OutcomeV2 where
  | certifiedTranslation
  | verifiedCounterexample
  | needsHumanClarification
  | unresolvedProofObligation
  | unsupportedFragment
  | searchExhausted
  | invalidProposal
  deriving Repr, DecidableEq, Inhabited

def OutcomeV2.name : OutcomeV2 → String
  | .certifiedTranslation => "CERTIFIED_TRANSLATION"
  | .verifiedCounterexample => "VERIFIED_COUNTEREXAMPLE"
  | .needsHumanClarification => "NEEDS_HUMAN_CLARIFICATION"
  | .unresolvedProofObligation => "UNRESOLVED_PROOF_OBLIGATION"
  | .unsupportedFragment => "UNSUPPORTED_FRAGMENT"
  | .searchExhausted => "SEARCH_EXHAUSTED"
  | .invalidProposal => "INVALID_PROPOSAL"

/-- The v2 decision. -/
structure DecisionV2 where
  outcome : OutcomeV2
  diagnostics : List Diagnostic
  semantic : SemanticStatus
  /-- the certificate under which the contract was checked -/
  certificate : Option EquivCert
  deriving Repr, Inhabited

def isReceiptCode : FailureCode → Bool
  | .elaborationNotVerified | .proofNotVerified => true
  | _ => false

/-- The certificate the decision is relative to. -/
def SemanticStatus.cert (s : SemanticStatus) (supplied : Option EquivCert) : Option EquivCert :=
  match s with
  | .certified c => some c
  | _ => supplied

def SemanticStatus.linked : SemanticStatus → Bool
  | .normalFormEqual | .certified _ => true
  | _ => false

/-- **The executable v2 classifier.** -/
def decideV2 (A : Authority) (r : RequestV2) : DecisionV2 :=
  let req := r.base
  let I := req.interpretation
  let C := req.candidate
  let gates := gateDiagnostics A req
  let sem := semanticAnalysis A.registry I.selected C.claim r.certificate r.bounds
  let semDiags := match sem with
    | .normalFormEqual | .certified _ => []
    | .counterexample _ => ⟨.semanticMismatch, "countermodel",
        "a verified finite countermodel distinguishes the candidate from the interpretation"⟩ ::
        structuralDiagnostics I C
    | .unknown _ => ⟨.semanticMismatch, "certificate",
        "no checked equivalence certificate and no countermodel within the search bounds"⟩ ::
        structuralDiagnostics I C
  let ds := gates ++ semDiags
  let outcome :=
    if gates.any (fun d => d.code.isClarification) then .needsHumanClarification
    else if gates.any (fun d => d.code == .unsupportedConstruct) then .unsupportedFragment
    else if gates.any (fun d => !isReceiptCode d.code) then .invalidProposal
    else match sem with
      | .counterexample _ => .verifiedCounterexample
      | .unknown _ => .searchExhausted
      | _ => if gates.isEmpty then .certifiedTranslation else .unresolvedProofObligation
  { outcome := outcome, diagnostics := ds, semantic := sem,
    certificate := sem.cert r.certificate }

/-! ## Refinement theorems -/

theorem countermodelPhase_not_linked (R : Registry) (I C : SemanticClaim) (b : SearchBounds) :
    (countermodelPhase R I C b).linked = false := by
  unfold countermodelPhase
  split
  · split <;> rfl
  · rfl

theorem semanticAnalysis_linked {R : Registry} {I C : SemanticClaim} {cert : Option EquivCert}
    {b : SearchBounds} {iv : Interpretation} {cand : Candidate} (hI : iv.selected = I)
    (hC : cand.claim = C) (h : (semanticAnalysis R I C cert b).linked = true) :
    SemanticallyLinked iv cand ((semanticAnalysis R I C cert b).cert cert) := by
  subst hI hC
  unfold semanticAnalysis at h ⊢
  by_cases heq : iv.selected.normalize.equivB cand.claim.normalize = true
  · rw [if_pos heq]; exact Or.inl ((NClaim.equivB_iff _ _).mp heq)
  · rw [if_neg heq] at h ⊢
    cases cert with
    | some c =>
      simp only at h ⊢
      by_cases hc : checkCert c iv.selected.normalize cand.claim.normalize = true
      · rw [if_pos hc]; exact Or.inr ⟨c, rfl, hc⟩
      · rw [if_neg hc] at h
        rw [countermodelPhase_not_linked] at h; cases h
    | none =>
      simp only at h ⊢
      cases hf : findCheckedCert b.certDepth b.certCap iv.selected.normalize cand.claim.normalize with
      | some c => exact Or.inr ⟨c, rfl, findCheckedCert_checked hf⟩
      | none =>
        rw [hf] at h
        rw [countermodelPhase_not_linked] at h; cases h

theorem decideV2_certified_gates {A : Authority} {r : RequestV2}
    (h : (decideV2 A r).outcome = .certifiedTranslation) :
    gateDiagnostics A r.base = [] ∧
      (semanticAnalysis A.registry r.base.interpretation.selected r.base.candidate.claim
        r.certificate r.bounds).linked = true := by
  unfold decideV2 at h
  simp only at h
  split at h
  · cases h
  · split at h
    · cases h
    · split at h
      · cases h
      · split at h
        · cases h
        · cases h
        · rename_i sem hne1 hne2
          split at h
          · rename_i hg
            refine ⟨List.isEmpty_iff.mp hg, ?_⟩
            revert hne1 hne2
            cases semanticAnalysis A.registry r.base.interpretation.selected
              r.base.candidate.claim r.certificate r.bounds <;>
              simp [SemanticStatus.linked]
          · cases h

/-- **Soundness of the executable classifier**: `CERTIFIED_TRANSLATION` implies the v2
    contract for the certificate reported in the decision. -/
theorem decideV2_certified_sound {A : Authority} {r : RequestV2}
    (h : (decideV2 A r).outcome = .certifiedTranslation) :
    CertifiedContractV2 A r.base (decideV2 A r).certificate := by
  obtain ⟨hg, hl⟩ := decideV2_certified_gates h
  exact ⟨(gateDiagnostics_nil A r.base).mp hg, semanticAnalysis_linked rfl rfl hl⟩

/-- **Completeness for supplied certificates**: if the v2 contract holds for the
    proposer-supplied certificate (or with no certificate, by normal forms), the classifier
    outputs `CERTIFIED_TRANSLATION`. -/
theorem decideV2_certified_complete {A : Authority} {r : RequestV2}
    (h : CertifiedContractV2 A r.base r.certificate) :
    (decideV2 A r).outcome = .certifiedTranslation := by
  have hg := (gateDiagnostics_nil A r.base).mpr h.gates
  have hsem : (semanticAnalysis A.registry r.base.interpretation.selected r.base.candidate.claim
      r.certificate r.bounds).linked = true := by
    unfold semanticAnalysis
    rcases h.semanticLink with hn | ⟨c, hc, hck⟩
    · rw [if_pos ((NClaim.equivB_iff _ _).mpr hn)]; rfl
    · split
      · rfl
      · rw [hc]; simp only; rw [if_pos hck]; rfl
  unfold decideV2
  simp only [hg, List.any_nil, Bool.false_eq_true, if_false, List.isEmpty_nil, if_true]
  revert hsem
  cases semanticAnalysis A.registry r.base.interpretation.selected r.base.candidate.claim
    r.certificate r.bounds <;> simp [SemanticStatus.linked]

/-- **Executable/specification refinement (v2).** -/
theorem executable_semantic_checker_refines_specification (A : Authority) (r : RequestV2) :
    ((decideV2 A r).outcome = .certifiedTranslation →
      CertifiedContractV2 A r.base (decideV2 A r).certificate) ∧
    (CertifiedContractV2 A r.base r.certificate →
      (decideV2 A r).outcome = .certifiedTranslation) :=
  ⟨decideV2_certified_sound, decideV2_certified_complete⟩

/-- `decideV2_certified_iff`: with the reported certificate, the classifier decides the
    contract exactly. -/
theorem decideV2_certified_iff (A : Authority) (r : RequestV2) :
    (decideV2 A r).outcome = .certifiedTranslation ↔
      (GatesV2 A r.base ∧ (semanticAnalysis A.registry r.base.interpretation.selected
        r.base.candidate.claim r.certificate r.bounds).linked = true) := by
  constructor
  · intro h
    obtain ⟨hg, hl⟩ := decideV2_certified_gates h
    exact ⟨(gateDiagnostics_nil A r.base).mp hg, hl⟩
  · rintro ⟨hg, hl⟩
    have hg' := (gateDiagnostics_nil A r.base).mpr hg
    unfold decideV2
    simp only [hg', List.any_nil, Bool.false_eq_true, if_false, List.isEmpty_nil, if_true]
    revert hl
    cases semanticAnalysis A.registry r.base.interpretation.selected r.base.candidate.claim
      r.certificate r.bounds <;> simp [SemanticStatus.linked]

/-- **v2 semantic preservation for the executable**: a `CERTIFIED_TRANSLATION` outcome
    implies denotational equivalence in every model and valuation. -/
theorem decideV2_certified_preserves_denotation {A : Authority} {r : RequestV2}
    (h : (decideV2 A r).outcome = .certifiedTranslation) (M : Model) (ρ : String → M.Dom) :
    r.base.interpretation.selected.denote M ρ ↔ r.base.candidate.claim.denote M ρ :=
  accepted_translation_preserves_denotation_v2 (decideV2_certified_sound h) M ρ

theorem countermodelPhase_sound {R : Registry} {I C : SemanticClaim} {b : SearchBounds}
    {w : Countermodel} (h : countermodelPhase R I C b = .counterexample w) :
    checkCountermodel R I C w = true := by
  unfold countermodelPhase at h
  split at h
  · split at h
    · cases h; assumption
    · cases h
  · cases h

theorem semanticAnalysis_counterexample_sound {R : Registry} {I C : SemanticClaim}
    {cert : Option EquivCert} {b : SearchBounds} {w : Countermodel}
    (h : semanticAnalysis R I C cert b = .counterexample w) :
    checkCountermodel R I C w = true := by
  unfold semanticAnalysis at h
  split at h
  · cases h
  · split at h
    · split at h
      · cases h
      · exact countermodelPhase_sound h
    · split at h
      · cases h
      · exact countermodelPhase_sound h

/-- **A `VERIFIED_COUNTEREXAMPLE` outcome is sound**: it carries a checked, registry-conforming
    countermodel; hence the claims are not equivalent, v1 rejects, and no certificate can make
    the v2 contract hold. -/
theorem decideV2_counterexample_sound {A : Authority} {r : RequestV2}
    (h : (decideV2 A r).outcome = .verifiedCounterexample) :
    ∃ w, (decideV2 A r).semantic = .counterexample w ∧
      checkCountermodel A.registry r.base.interpretation.selected r.base.candidate.claim w = true ∧
      ¬ (∀ (M : Model) (ρ : String → M.Dom), M.Conforms A.registry →
          (r.base.interpretation.selected.denote M ρ ↔ r.base.candidate.claim.denote M ρ)) ∧
      translationAccepts A r.base = false ∧
      ∀ cert, ¬ CertifiedContractV2 A r.base cert := by
  have hsem : ∃ w, semanticAnalysis A.registry r.base.interpretation.selected
      r.base.candidate.claim r.certificate r.bounds = .counterexample w := by
    unfold decideV2 at h
    simp only at h
    split at h
    · cases h
    · split at h
      · cases h
      · split at h
        · cases h
        · split at h
          · rename_i w hw; exact ⟨w, hw⟩
          · cases h
          · split at h <;> cases h
  obtain ⟨w, hw⟩ := hsem
  have hc := semanticAnalysis_counterexample_sound hw
  exact ⟨w, by unfold decideV2; exact hw, hc, countermodel_demonstrates_semantic_difference hc,
    countermodel_v1_rejected hc, countermodel_refutes_contract_v2 hc⟩

/-- Every non-`CERTIFIED_TRANSLATION` outcome is a non-acceptance; in particular an
    unresolved ambiguity never yields acceptance. -/
theorem decideV2_ambiguity_not_certified {A : Authority} {r : RequestV2} {a : Ambiguity}
    (ha : a ∈ r.base.interpretation.ambiguities) (hr : a.resolution = none) :
    (decideV2 A r).outcome ≠ .certifiedTranslation := by
  intro h
  have := (decideV2_certified_sound h).gates.noUnresolvedAmbiguity a ha
  rw [hr] at this; cases this

/-- Missing authorized confirmation never yields acceptance (model self-assertion ignored). -/
theorem decideV2_unconfirmed_not_certified {A : Authority} {r : RequestV2}
    (hc : r.base.confirmation = none) : (decideV2 A r).outcome ≠ .certifiedTranslation := by
  intro h
  obtain ⟨_, h1, _⟩ := (decideV2_certified_sound h).gates.confirmation
  rw [hc] at h1; cases h1

/-- A candidate symbol that is not uniquely grounded never yields acceptance. -/
theorem decideV2_ungrounded_not_certified {A : Authority} {r : RequestV2} {f : String}
    (hf : f ∈ r.base.candidate.claim.symbols) (hg : groundOK A.registry r.base.candidate f = false) :
    (decideV2 A r).outcome ≠ .certifiedTranslation := by
  intro h
  have := (decideV2_certified_sound h).gates.groundedSymbols.2.1 f hf
  rw [hg] at this; cases this

/-- An unsupported construct never yields acceptance. -/
theorem decideV2_unsupported_not_certified {A : Authority} {r : RequestV2} {t : String}
    (ht : t ∈ r.base.candidate.claim.unsupportedTags) :
    (decideV2 A r).outcome ≠ .certifiedTranslation := by
  intro h
  have := (decideV2_certified_sound h).gates.supportedFragment.2
  rw [this] at ht; cases ht

/-- A required but missing proof receipt never yields acceptance. -/
theorem decideV2_missing_proof_not_certified {A : Authority} {r : RequestV2}
    (hreq : A.requireProof = true) (hp : r.base.proof = none) :
    (decideV2 A r).outcome ≠ .certifiedTranslation := by
  intro h
  obtain ⟨_, h1, _⟩ := (decideV2_certified_sound h).gates.proof hreq
  rw [hp] at h1; cases h1

/-- **Semantically inequivalent candidates are never certified** (whatever certificate the
    proposer supplies and whatever the untrusted search returns). -/
theorem decideV2_inequivalent_not_certified {A : Authority} {r : RequestV2} {M : Model}
    {ρ : String → M.Dom}
    (h : ¬ (r.base.interpretation.selected.denote M ρ ↔ r.base.candidate.claim.denote M ρ)) :
    (decideV2 A r).outcome ≠ .certifiedTranslation :=
  fun hc => h (decideV2_certified_preserves_denotation hc M ρ)

/-! ## Metadata independence -/

/-- **The v2 authority does not trust proposer metadata**: proposer identities, self-reported
    confidence and the self-asserted confirmation flag have no influence on the decision. -/
theorem semantic_authority_does_not_trust_proposer_metadata (A : Authority) (r : RequestV2)
    (conf : Nat) (p₁ p₂ : String) (asserted : Bool) :
    decideV2 A { r with base := { r.base with
      interpretation := { r.base.interpretation with proposer := p₁, modelAssertsConfirmed := asserted },
      candidate := { r.base.candidate with proposer := p₂, modelConfidence := conf } } } =
    decideV2 A r := by
  obtain ⟨⟨I, cf, c, el, pr⟩, cert, b⟩ := r
  cases I; cases c; rfl

/-! ## End-to-end conditional flagship -/

/-- **`pcs_proof_carrying_translation_sound_v2`.**  If the executable v2 classifier outputs
    `CERTIFIED_TRANSLATION` for a request, then, with the external receipt contracts stated
    as explicit hypotheses:

    1. every interpretation question is resolved;
    2. every candidate symbol is uniquely and correctly grounded in the approved registry,
       and the interpretation's symbols resolve;
    3. both claims are well typed, closed and in the supported fragment, and the candidate
       is binder-hygienic;
    4. the selected structured meaning and the accepted formal meaning are denotationally
       equivalent in **every** model and valuation (no hypothesis);
    5. the semantic link is a v1 normal-form equality or a certificate re-checked by
       `checkCert` (no hypothesis);
    6. under `ExternalContracts`, the exact interpretation was confirmed by an authorized
       process, and the exact rendered Lean source was elaborated / kernel-proved when
       required;
    7. the Explanation IR derived from the candidate means the selected interpretation;
    8. under the explicit `ElaborationBridge` for an intended model `M`, the selected
       interpretation holds in `M`.

    Proposer metadata cannot change the outcome (`semantic_authority_does_not_trust_proposer_metadata`).
    Transfer from `M` to the deployed world is *not* claimed here: it needs a separate
    correspondence hypothesis (for example `FaithfulLog` in `PCS.V2.ExternalWorld`). -/
theorem pcs_proof_carrying_translation_sound_v2 {A : Authority} {r : RequestV2}
    {W : ExternalWorld} (h : (decideV2 A r).outcome = .certifiedTranslation)
    (hX : ExternalContracts A W) :
    NoUnresolvedAmbiguity r.base.interpretation ∧
    GroundedSymbols A.registry r.base.candidate ∧
    InterpretationGrounded A.registry r.base.interpretation ∧
    WellTypedPair A.registry r.base.interpretation r.base.candidate ∧
    NoUnexpectedFreeVariables r.base.interpretation r.base.candidate ∧
    SupportedFragment r.base.interpretation r.base.candidate ∧
    r.base.candidate.claim.hygienicB A.registry = true ∧
    (∀ (M : Model) (ρ : String → M.Dom),
      r.base.interpretation.selected.denote M ρ ↔ r.base.candidate.claim.denote M ρ) ∧
    SemanticallyLinked r.base.interpretation r.base.candidate (decideV2 A r).certificate ∧
    W.Confirmed r.base.interpretation.sourceText r.base.interpretation.selected
      r.base.interpretation.ambiguities ∧
    (A.requireElaboration = true →
      W.Elaborates r.base.candidate.leanSource r.base.candidate.declName) ∧
    (A.requireProof = true →
      W.KernelProved r.base.candidate.leanSource r.base.candidate.declName) ∧
    (∀ (M : Model) (ρ : String → M.Dom),
      (toExplanation A.registry r.base.candidate.claim).denote M ρ ↔
        r.base.interpretation.selected.denote M ρ) ∧
    (A.requireProof = true → ∀ M, ElaborationBridge A.registry W M →
      ∀ ρ, r.base.interpretation.selected.denote M ρ) := by
  have c := decideV2_certified_sound h
  have g := c.gates
  have hproved : A.requireProof = true →
      W.KernelProved r.base.candidate.leanSource r.base.candidate.declName := by
    intro hp
    obtain ⟨rc, _, hs, hd, _, hv⟩ := g.proof hp
    have := hX.proof_sound rc hv
    rw [hs, hd] at this; exact this
  refine ⟨g.noUnresolvedAmbiguity, g.groundedSymbols, g.interpretationGrounded, g.wellTyped,
    g.noUnexpectedFreeVariables, g.supportedFragment, g.hygienic,
    fun M ρ => accepted_translation_preserves_denotation_v2 c M ρ, c.semanticLink, ?_, ?_,
    hproved, fun M ρ => accepted_explanation_means_interpretation_v2 c M ρ, ?_⟩
  · obtain ⟨rc, _, hb, hv⟩ := g.confirmation
    have := hX.confirmation_sound rc hv
    unfold ConfirmationReceipt.binds at hb
    simp only [Bool.and_eq_true, decide_eq_true_eq] at hb
    obtain ⟨⟨h1, h2⟩, h3⟩ := hb
    rw [h1, h2, h3] at this; exact this
  · intro he
    obtain ⟨rc, _, hs, hd, hv⟩ := g.elaboration he
    have := hX.elaboration_sound rc hv
    rw [hs, hd] at this; exact this
  · intro hp M hB ρ
    have hk := hproved hp
    rw [g.leanRendering] at hk
    have hc := hB r.base.candidate.claim r.base.candidate.declName g.wellTyped.2
      g.noUnexpectedFreeVariables.2 g.hygienic hk ρ
    exact (accepted_translation_preserves_denotation_v2 c M ρ).mpr hc

end PCS.V2.Semantic
