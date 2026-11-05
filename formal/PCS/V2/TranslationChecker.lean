import PCS.V2.TranslationContract

/-!
# The deterministic semantic translation checker and its soundness

`diagnose A req` is the executable, deterministic validator.  It returns a list of
structured `Diagnostic`s (failure code, failing component, detail); the request is
accepted exactly when the list is empty (`translationAccepts`).  Unknown never means pass:
every condition is a positive check, and every missing receipt, unresolved symbol or
unresolved ambiguity produces a diagnostic.

Main results (all kernel-checked, no hypotheses beyond acceptance):

* `diagnose_eq_nil_iff`, `translationAccepts_iff` — the checker **decides the certified
  contract exactly**: `translationAccepts A req = true ↔ TranslationContract A req`.
* `translation_acceptance_sound` — the flagship conjunction (no ambiguity, grounded
  symbols, quantifier/polarity/negation/assumption/binding preservation, no free
  variables, supported fragment, structural round trip) **plus**
* `accepted_translation_preserves_meaning` — **for every model and every valuation**, the
  denotation of the selected interpretation is logically equivalent to the denotation of
  the accepted candidate (the strongest semantic relationship: equivalence in all
  structures).  This is proved from the independent semantics, via the
  denotation-preserving normalization (`alphaEquiv_denote_iff`) — not from the checker's
  Boolean conditions alone.
* Individual preservation theorems `accepted_translation_*` and rejection theorems
  `*_rejected` (unknown symbol, unresolved ambiguity, dropped/added assumption, quantifier,
  polarity, negation, connective and binding changes, shadowed/duplicate grounding,
  incorrect symbol identity, unknown definition, unsupported construct, free variable,
  missing/forged/mis-bound confirmation, missing/forged elaboration and proof receipts,
  disallowed axioms, Lean-source and explanation mismatches, and **any semantically
  inequivalent candidate**).
* `decision_ignores_model_metadata` — the decision does not depend on the proposer's
  identity, self-reported confidence, or self-asserted confirmation.
-/

set_option autoImplicit false

namespace PCS.V2.Semantic

/-! ## Failure codes and diagnostics -/

/-- Deterministic failure codes. -/
inductive FailureCode where
  | ambiguousScope
  | unresolvedAmbiguity
  | confirmationMissing
  | confirmationNotVerified
  | registryMalformed
  | unresolvedSymbol
  | unknownDefinition
  | incorrectSymbolIdentity
  | duplicateOrShadowedGrounding
  | illTyped
  | unsupportedConstruct
  | unexpectedFreeVariable
  | binderShadowing
  | quantifierMismatch
  | polarityMismatch
  | negationMismatch
  | connectiveMismatch
  | assumptionDropped
  | assumptionAdded
  | bindingMismatch
  | semanticMismatch
  | roundtripMismatch
  | leanRenderingMismatch
  | elaborationNotVerified
  | proofNotVerified
  | malformedInput
  deriving Repr, DecidableEq, Inhabited

/-- Stable wire names of the failure codes. -/
def FailureCode.name : FailureCode → String
  | .ambiguousScope => "AMBIGUOUS_SCOPE"
  | .unresolvedAmbiguity => "UNRESOLVED_AMBIGUITY"
  | .confirmationMissing => "CONFIRMATION_MISSING"
  | .confirmationNotVerified => "CONFIRMATION_NOT_VERIFIED"
  | .registryMalformed => "REGISTRY_MALFORMED"
  | .unresolvedSymbol => "UNRESOLVED_SYMBOL"
  | .unknownDefinition => "UNKNOWN_DEFINITION"
  | .incorrectSymbolIdentity => "INCORRECT_SYMBOL_IDENTITY"
  | .duplicateOrShadowedGrounding => "DUPLICATE_OR_SHADOWED_GROUNDING"
  | .illTyped => "ILL_TYPED"
  | .unsupportedConstruct => "UNSUPPORTED_CONSTRUCT"
  | .unexpectedFreeVariable => "UNEXPECTED_FREE_VARIABLE"
  | .binderShadowing => "BINDER_SHADOWING"
  | .quantifierMismatch => "QUANTIFIER_MISMATCH"
  | .polarityMismatch => "POLARITY_MISMATCH"
  | .negationMismatch => "NEGATION_MISMATCH"
  | .connectiveMismatch => "CONNECTIVE_MISMATCH"
  | .assumptionDropped => "ASSUMPTION_DROPPED"
  | .assumptionAdded => "ASSUMPTION_ADDED"
  | .bindingMismatch => "BINDING_MISMATCH"
  | .semanticMismatch => "SEMANTIC_MISMATCH"
  | .roundtripMismatch => "ROUNDTRIP_MISMATCH"
  | .leanRenderingMismatch => "LEAN_RENDERING_MISMATCH"
  | .elaborationNotVerified => "ELABORATION_NOT_VERIFIED"
  | .proofNotVerified => "PROOF_NOT_VERIFIED"
  | .malformedInput => "MALFORMED_INPUT"

/-- A structured diagnostic. -/
structure Diagnostic where
  code : FailureCode
  component : String
  detail : String
  deriving Repr, DecidableEq, Inhabited

/-- Verdicts.  `needsClarification` is a *rejection* that only asks for human input. -/
inductive Verdict where
  | accepted
  | needsClarification
  | rejected
  deriving Repr, DecidableEq, Inhabited

def Verdict.name : Verdict → String
  | .accepted => "ACCEPTED"
  | .needsClarification => "NEEDS_CLARIFICATION"
  | .rejected => "REJECTED"

/-- Codes that only require human clarification/confirmation. -/
def FailureCode.isClarification : FailureCode → Bool
  | .ambiguousScope | .unresolvedAmbiguity | .confirmationMissing => true
  | _ => false

/-- A decision: verdict plus all diagnostics. -/
structure Decision where
  verdict : Verdict
  diagnostics : List Diagnostic
  deriving Repr, DecidableEq, Inhabited

/-! ## Individual checks -/

/-- `[]` if the condition holds, otherwise the diagnostic. -/
def failIf (b : Bool) (d : Diagnostic) : List Diagnostic := if b then [] else [d]

theorem failIf_nil (b : Bool) (d : Diagnostic) : failIf b d = [] ↔ b = true := by
  unfold failIf; cases b <;> simp

theorem filter_map_nil {α β : Type} (l : List α) (p : α → Bool) (f : α → β) :
    (l.filter p).map f = [] ↔ ∀ x ∈ l, p x = false := by
  simp [List.filter_eq_nil_iff]

def ambCode : AmbiguityKind → FailureCode
  | .scope => .ambiguousScope
  | _ => .unresolvedAmbiguity

def checkAmbiguity (I : Interpretation) : List Diagnostic :=
  (I.ambiguities.filter (fun a => a.resolution.isNone)).map
    (fun a => ⟨ambCode a.kind, "interpretation.ambiguities", a.id ++ ": " ++ a.question⟩)

def checkConfirmation (A : Authority) (req : Request) : List Diagnostic :=
  match req.confirmation with
  | none => [⟨.confirmationMissing, "confirmation",
      "no authorized confirmation receipt (model-asserted confirmation is ignored)"⟩]
  | some r =>
    failIf (r.binds req.interpretation)
      ⟨.confirmationNotVerified, "confirmation", "receipt is not bound to this exact interpretation"⟩ ++
    failIf (A.verifyConfirmation r)
      ⟨.confirmationNotVerified, "confirmation", "receipt signature/authority did not verify"⟩

def checkRegistry (R : Registry) : List Diagnostic :=
  failIf R.wellFormedB ⟨.registryMalformed, "registry",
    "duplicate symbol/sort ids or unregistered sort in a signature"⟩

def checkInterpretationSymbols (R : Registry) (I : Interpretation) : List Diagnostic :=
  (I.selected.symbols.filter (fun f => (R.resolve f).isNone)).map
    (fun f => ⟨.unresolvedSymbol, "interpretation", f⟩)

/-- Classify a failing candidate symbol. -/
def classifySymbol (R : Registry) (cand : Candidate) (f : String) : Diagnostic :=
  match R.entries f, cand.groundings.filter (fun g => g.symbol == f) with
  | [], _ => ⟨.unresolvedSymbol, "candidate.symbols", f ++ " is not an approved symbol"⟩
  | _ :: _ :: _, _ => ⟨.duplicateOrShadowedGrounding, "registry", f ++ " resolves ambiguously"⟩
  | _, [] => ⟨.unresolvedSymbol, "candidate.groundings", f ++ " has no declared grounding"⟩
  | _, _ :: _ :: _ => ⟨.duplicateOrShadowedGrounding, "candidate.groundings",
      f ++ " has several (shadowing) groundings"⟩
  | _, _ => ⟨.incorrectSymbolIdentity, "candidate.groundings",
      f ++ " is grounded to a different definition than the approved one"⟩

def checkCandidateSymbols (R : Registry) (cand : Candidate) : List Diagnostic :=
  (cand.claim.symbols.filter (fun f => !groundOK R cand f)).map (classifySymbol R cand)

def checkGroundingRefs (R : Registry) (cand : Candidate) : List Diagnostic :=
  (cand.groundings.filter (fun g => !refOK R g)).map (fun g =>
    match R.resolve g.symbol with
    | none => ⟨.unknownDefinition, "candidate.groundings", g.symbol ++ " ↦ " ++ g.leanName⟩
    | some e => ⟨.incorrectSymbolIdentity, "candidate.groundings",
        g.symbol ++ " ↦ " ++ g.leanName ++ " (approved: " ++ e.leanName ++ ")"⟩)

def checkTyping (R : Registry) (I : Interpretation) (cand : Candidate) : List Diagnostic :=
  failIf (I.selected.wellTypedB R) ⟨.illTyped, "interpretation", "ill-typed under the registry"⟩ ++
  failIf (cand.claim.wellTypedB R) ⟨.illTyped, "candidate", "ill-typed under the registry"⟩

def checkSupported (I : Interpretation) (cand : Candidate) : List Diagnostic :=
  I.selected.unsupportedTags.map (fun t => ⟨.unsupportedConstruct, "interpretation", t⟩) ++
  cand.claim.unsupportedTags.map (fun t => ⟨.unsupportedConstruct, "candidate", t⟩)

def checkFreeVars (I : Interpretation) (cand : Candidate) : List Diagnostic :=
  I.selected.freeVars.map (fun x => ⟨.unexpectedFreeVariable, "interpretation", x⟩) ++
  cand.claim.freeVars.map (fun x => ⟨.unexpectedFreeVariable, "candidate", x⟩)

def checkHygiene (R : Registry) (cand : Candidate) : List Diagnostic :=
  failIf (cand.claim.hygienicB R) ⟨.binderShadowing, "candidate",
    "a binder re-binds an in-scope variable or shadows a registered symbol"⟩

def checkQuantifiers (I : Interpretation) (cand : Candidate) : List Diagnostic :=
  failIf (decide (I.selected.normalize.paramSorts = cand.claim.normalize.paramSorts) &&
      decide (NFormula.quantSkel [] I.selected.normalize.conclusion =
        NFormula.quantSkel [] cand.claim.normalize.conclusion))
    ⟨.quantifierMismatch, "conclusion",
      "expected " ++ reprStr (I.selected.normalize.paramSorts,
        NFormula.quantSkel [] I.selected.normalize.conclusion) ++
      " got " ++ reprStr (cand.claim.normalize.paramSorts,
        NFormula.quantSkel [] cand.claim.normalize.conclusion)⟩

def checkPolarity (I : Interpretation) (cand : Candidate) : List Diagnostic :=
  failIf (decide (PreservesPolarity I cand) : Bool) ⟨.polarityMismatch, "conclusion",
    "polarity of some atomic occurrence differs (e.g. reversed implication or dropped negation)"⟩

def checkNegation (I : Interpretation) (cand : Candidate) : List Diagnostic :=
  failIf (decide (PreservesNegation I cand) : Bool) ⟨.negationMismatch, "conclusion",
    "expected negations at " ++ reprStr (NFormula.negSkel [] I.selected.normalize.conclusion) ++
    " got " ++ reprStr (NFormula.negSkel [] cand.claim.normalize.conclusion)⟩

def checkConnectives (I : Interpretation) (cand : Candidate) : List Diagnostic :=
  failIf (decide (PreservesConnectives I cand) : Bool) ⟨.connectiveMismatch, "conclusion",
    "connective structure differs (e.g. ∧ replaced by ∨)"⟩

def checkAssumptions (I : Interpretation) (cand : Candidate) : List Diagnostic :=
  (I.selected.normalize.assumptions.filter
      (fun a => !cand.claim.normalize.assumptions.contains a)).map
    (fun a => ⟨.assumptionDropped, "assumptions", reprStr a⟩) ++
  (cand.claim.normalize.assumptions.filter
      (fun a => !I.selected.normalize.assumptions.contains a)).map
    (fun a => ⟨.assumptionAdded, "assumptions", reprStr a⟩)

def checkBindings (I : Interpretation) (cand : Candidate) : List Diagnostic :=
  failIf (decide (PreservesBindings I cand) : Bool) ⟨.bindingMismatch, "bindings",
    "expected occurrences " ++ reprStr (NFormula.varSkel I.selected.normalize.conclusion) ++
    " got " ++ reprStr (NFormula.varSkel cand.claim.normalize.conclusion)⟩

def checkNormalForm (I : Interpretation) (cand : Candidate) : List Diagnostic :=
  failIf (I.selected.normalize.equivB cand.claim.normalize) ⟨.semanticMismatch, "claim",
    "normal forms differ: the candidate is not α-equivalent (up to assumption order) to the interpretation"⟩

def roundTripB (R : Registry) (I : Interpretation) (cand : Candidate) : Bool :=
  I.selected.normalize.equivB (toExplanation R cand.claim).toClaim.normalize &&
    match cand.explanation with
    | none => true
    | some e => decide (e = toExplanation R cand.claim)

def checkRoundTrip (R : Registry) (I : Interpretation) (cand : Candidate) : List Diagnostic :=
  failIf (roundTripB R I cand) ⟨.roundtripMismatch, "explanation",
    "structured round trip through Explanation IR does not reproduce the interpretation"⟩

def checkLeanRendering (R : Registry) (cand : Candidate) : List Diagnostic :=
  failIf (decide (cand.leanSource = renderClaimLean R cand.claim)) ⟨.leanRenderingMismatch,
    "candidate.leanSource", "expected " ++ renderClaimLean R cand.claim⟩

def checkElaboration (A : Authority) (req : Request) : List Diagnostic :=
  if A.requireElaboration then
    match req.elaboration with
    | none => [⟨.elaborationNotVerified, "elaboration", "required receipt missing"⟩]
    | some r => failIf (decide (r.leanSource = req.candidate.leanSource) &&
        decide (r.declName = req.candidate.declName) && A.verifyElaboration r)
        ⟨.elaborationNotVerified, "elaboration", "receipt unbound or not verified"⟩
  else []

def checkProof (A : Authority) (req : Request) : List Diagnostic :=
  if A.requireProof then
    match req.proof with
    | none => [⟨.proofNotVerified, "proof", "required receipt missing"⟩]
    | some r => failIf (decide (r.leanSource = req.candidate.leanSource) &&
        decide (r.declName = req.candidate.declName) &&
        r.axioms.all (fun ax => A.allowedAxioms.contains ax) && A.verifyProof r)
        ⟨.proofNotVerified, "proof", "receipt unbound, uses a disallowed axiom, or not verified"⟩
  else []

/-! ## The checker -/

/-- **The deterministic semantic translation checker** (all diagnostics). -/
def diagnose (A : Authority) (req : Request) : List Diagnostic :=
  let R := A.registry
  let I := req.interpretation
  let c := req.candidate
  checkAmbiguity I ++ checkConfirmation A req ++ checkRegistry R ++
  checkInterpretationSymbols R I ++ checkCandidateSymbols R c ++ checkGroundingRefs R c ++
  checkTyping R I c ++ checkSupported I c ++ checkFreeVars I c ++ checkHygiene R c ++
  checkQuantifiers I c ++ checkPolarity I c ++ checkNegation I c ++ checkConnectives I c ++
  checkAssumptions I c ++ checkBindings I c ++ checkNormalForm I c ++
  checkRoundTrip R I c ++ checkLeanRendering R c ++ checkElaboration A req ++ checkProof A req

/-- Boolean projection. -/
def translationAccepts (A : Authority) (req : Request) : Bool := (diagnose A req).isEmpty

/-- Full decision with verdict. -/
def checkTranslation (A : Authority) (req : Request) : Decision :=
  let ds := diagnose A req
  { verdict := if ds.isEmpty then .accepted
      else if ds.all (fun d => d.code.isClarification) then .needsClarification
      else .rejected,
    diagnostics := ds }

/-! ## Component lemmas -/

theorem checkAmbiguity_nil (I : Interpretation) :
    checkAmbiguity I = [] ↔ NoUnresolvedAmbiguity I := by
  unfold checkAmbiguity NoUnresolvedAmbiguity
  rw [filter_map_nil]
  apply forall_congr'; intro a; apply imp_congr Iff.rfl
  cases a.resolution <;> simp

theorem checkConfirmation_nil (A : Authority) (req : Request) :
    checkConfirmation A req = [] ↔ ConfirmationVerified A req := by
  unfold checkConfirmation ConfirmationVerified
  cases h : req.confirmation with
  | none => simp
  | some r => simp [List.append_eq_nil_iff, failIf_nil]

theorem checkRegistry_nil (R : Registry) : checkRegistry R = [] ↔ R.wellFormedB = true :=
  failIf_nil _ _

theorem checkInterpretationSymbols_nil (R : Registry) (I : Interpretation) :
    checkInterpretationSymbols R I = [] ↔ InterpretationGrounded R I := by
  unfold checkInterpretationSymbols InterpretationGrounded
  rw [filter_map_nil]
  apply forall_congr'; intro f; apply imp_congr Iff.rfl
  cases R.resolve f <;> simp

theorem checkCandidateSymbols_nil (R : Registry) (cand : Candidate) :
    checkCandidateSymbols R cand = [] ↔ ∀ f ∈ cand.claim.symbols, groundOK R cand f = true := by
  unfold checkCandidateSymbols
  rw [filter_map_nil]
  simp

theorem checkGroundingRefs_nil (R : Registry) (cand : Candidate) :
    checkGroundingRefs R cand = [] ↔ ∀ g ∈ cand.groundings, refOK R g = true := by
  unfold checkGroundingRefs
  rw [filter_map_nil]
  simp

theorem checkTyping_nil (R : Registry) (I : Interpretation) (cand : Candidate) :
    checkTyping R I cand = [] ↔ WellTypedPair R I cand := by
  simp [checkTyping, WellTypedPair, List.append_eq_nil_iff, failIf_nil]

theorem checkSupported_nil (I : Interpretation) (cand : Candidate) :
    checkSupported I cand = [] ↔ SupportedFragment I cand := by
  simp [checkSupported, SupportedFragment, List.append_eq_nil_iff]

theorem checkFreeVars_nil (I : Interpretation) (cand : Candidate) :
    checkFreeVars I cand = [] ↔ NoUnexpectedFreeVariables I cand := by
  simp [checkFreeVars, NoUnexpectedFreeVariables, List.append_eq_nil_iff]

theorem checkQuantifiers_nil (I : Interpretation) (cand : Candidate) :
    checkQuantifiers I cand = [] ↔ PreservesQuantifiers I cand := by
  simp [checkQuantifiers, PreservesQuantifiers, failIf_nil]

theorem checkAssumptions_nil (I : Interpretation) (cand : Candidate) :
    checkAssumptions I cand = [] ↔ PreservesAssumptions I cand := by
  unfold checkAssumptions PreservesAssumptions NoAssumptionDropped NoAssumptionAdded
  rw [List.append_eq_nil_iff, filter_map_nil, filter_map_nil]
  simp

theorem checkRoundTrip_nil (R : Registry) (I : Interpretation) (cand : Candidate) :
    checkRoundTrip R I cand = [] ↔ RoundTripEquivalent R I cand := by
  unfold checkRoundTrip roundTripB RoundTripEquivalent
  rw [failIf_nil, Bool.and_eq_true, NClaim.equivB_iff]
  apply and_congr Iff.rfl
  cases cand.explanation <;> simp

theorem checkElaboration_nil (A : Authority) (req : Request) :
    checkElaboration A req = [] ↔ ElaborationVerified A req := by
  unfold checkElaboration ElaborationVerified
  cases hA : A.requireElaboration
  · simp
  · cases h : req.elaboration with
    | none => simp
    | some r => simp [failIf_nil, and_assoc]

theorem checkProof_nil (A : Authority) (req : Request) :
    checkProof A req = [] ↔ ProofVerified A req := by
  unfold checkProof ProofVerified
  cases hA : A.requireProof
  · simp
  · cases h : req.proof with
    | none => simp
    | some r => simp [failIf_nil, and_assoc, List.all_eq_true]

/-! ## Exact characterisation (certified specification ↔ executable checker) -/

theorem diagnose_eq_nil_iff (A : Authority) (req : Request) :
    diagnose A req = [] ↔ TranslationContract A req := by
  unfold diagnose
  simp only [List.append_eq_nil_iff, checkAmbiguity_nil, checkConfirmation_nil, checkRegistry_nil,
    checkInterpretationSymbols_nil, checkCandidateSymbols_nil, checkGroundingRefs_nil,
    checkTyping_nil, checkSupported_nil, checkFreeVars_nil, checkQuantifiers_nil,
    checkAssumptions_nil, checkRoundTrip_nil, checkElaboration_nil, checkProof_nil,
    checkHygiene, checkPolarity, checkNegation, checkConnectives, checkBindings,
    checkNormalForm, checkLeanRendering, failIf_nil, decide_eq_true_eq, NClaim.equivB_iff, and_assoc]
  constructor
  · rintro ⟨h1, h2, h3, h4, h5, h6, h7, h8, h9, h10, h11, h12, h13, h14, h15, h16, h17, h18,
      h19, h20, h21⟩
    exact ⟨h1, h2, h4, ⟨h3, h5, h6⟩, h7, h8, h9, h10, h11, h12, h13, h14, h15, h16, h17, h18,
      h19, h20, h21⟩
  · rintro ⟨h1, h2, h4, ⟨h3, h5, h6⟩, h7, h8, h9, h10, h11, h12, h13, h14, h15, h16, h17, h18,
      h19, h20, h21⟩
    exact ⟨h1, h2, h3, h4, h5, h6, h7, h8, h9, h10, h11, h12, h13, h14, h15, h16, h17, h18,
      h19, h20, h21⟩

/-- **Executable/certified refinement**: the Boolean checker decides the certified
    contract exactly. -/
theorem translationAccepts_iff (A : Authority) (req : Request) :
    translationAccepts A req = true ↔ TranslationContract A req := by
  unfold translationAccepts
  rw [List.isEmpty_iff]
  exact diagnose_eq_nil_iff A req

theorem translationAccepts_eq_false_iff (A : Authority) (req : Request) :
    translationAccepts A req = false ↔ ¬ TranslationContract A req := by
  rw [← translationAccepts_iff]; cases translationAccepts A req <;> simp

theorem verdict_accepted_iff (A : Authority) (req : Request) :
    (checkTranslation A req).verdict = .accepted ↔ translationAccepts A req = true := by
  unfold checkTranslation translationAccepts
  simp only
  split
  · simp_all
  · rename_i h
    simp only [h]
    split <;> simp

/-- Acceptance ⇔ no diagnostic. -/
theorem accepted_iff_no_diagnostics (A : Authority) (req : Request) :
    translationAccepts A req = true ↔ (checkTranslation A req).diagnostics = [] := by
  unfold translationAccepts checkTranslation; simp [List.isEmpty_iff]

/-! ## Flagship soundness -/

/-- **Flagship soundness theorem** (structural contract). -/
theorem translation_acceptance_sound {A : Authority} {req : Request}
    (h : translationAccepts A req = true) :
    NoUnresolvedAmbiguity req.interpretation ∧
    GroundedSymbols A.registry req.candidate ∧
    PreservesQuantifiers req.interpretation req.candidate ∧
    PreservesPolarity req.interpretation req.candidate ∧
    PreservesNegation req.interpretation req.candidate ∧
    PreservesAssumptions req.interpretation req.candidate ∧
    PreservesBindings req.interpretation req.candidate ∧
    NoUnexpectedFreeVariables req.interpretation req.candidate ∧
    SupportedFragment req.interpretation req.candidate ∧
    RoundTripEquivalent A.registry req.interpretation req.candidate := by
  have c := (translationAccepts_iff A req).mp h
  exact ⟨c.noUnresolvedAmbiguity, c.groundedSymbols, c.preservesQuantifiers,
    c.preservesPolarity, c.preservesNegation, c.preservesAssumptions, c.preservesBindings,
    c.noUnexpectedFreeVariables, c.supportedFragment, c.roundTrip⟩

/-- **Main semantic preservation theorem.**  If PCS accepts a translation, then for every
    model `M` (every interpretation of the approved symbols, in particular the intended
    one) and every valuation `ρ`, the meaning of the selected interpretation is logically
    equivalent to the meaning of the accepted candidate. -/
theorem accepted_translation_preserves_meaning {A : Authority} {req : Request}
    (h : translationAccepts A req = true) (M : Model) (ρ : String → M.Dom) :
    req.interpretation.selected.denote M ρ ↔ req.candidate.claim.denote M ρ :=
  alphaEquiv_denote_iff ((translationAccepts_iff A req).mp h).normalFormEquivalent M ρ

/-- Typed corollary: the equivalence holds in particular for every registry-conforming
    model and every well-typed valuation. -/
theorem accepted_translation_preserves_meaning_typed {A : Authority} {req : Request}
    (h : translationAccepts A req = true) (M : Model) (_hM : M.Conforms A.registry)
    (Γ : Ctx) (ρ : String → M.Dom) (_hρ : WellTypedVal M Γ ρ) :
    req.interpretation.selected.denote M ρ ↔ req.candidate.claim.denote M ρ :=
  accepted_translation_preserves_meaning h M ρ

/-- The accepted Explanation IR means exactly what the selected interpretation means. -/
theorem accepted_explanation_means_interpretation {A : Authority} {req : Request}
    (h : translationAccepts A req = true) (M : Model) (ρ : String → M.Dom) :
    (toExplanation A.registry req.candidate.claim).denote M ρ ↔
      req.interpretation.selected.denote M ρ :=
  (explanationIR_preserves_semantics _ M ρ _).trans (accepted_translation_preserves_meaning h M ρ).symm

/-! ## Individual preservation theorems -/

section Individual
variable {A : Authority} {req : Request} (h : translationAccepts A req = true)
include h

theorem accepted_translation_has_no_unresolved_ambiguity :
    NoUnresolvedAmbiguity req.interpretation :=
  ((translationAccepts_iff A req).mp h).noUnresolvedAmbiguity

theorem accepted_translation_preserves_quantifiers :
    PreservesQuantifiers req.interpretation req.candidate :=
  ((translationAccepts_iff A req).mp h).preservesQuantifiers

theorem accepted_translation_preserves_polarity :
    PreservesPolarity req.interpretation req.candidate :=
  ((translationAccepts_iff A req).mp h).preservesPolarity

theorem accepted_translation_preserves_negation :
    PreservesNegation req.interpretation req.candidate :=
  ((translationAccepts_iff A req).mp h).preservesNegation

theorem accepted_translation_preserves_assumptions :
    PreservesAssumptions req.interpretation req.candidate :=
  ((translationAccepts_iff A req).mp h).preservesAssumptions

theorem accepted_translation_preserves_bindings :
    PreservesBindings req.interpretation req.candidate :=
  ((translationAccepts_iff A req).mp h).preservesBindings

theorem accepted_translation_has_no_unexpected_free_variables :
    NoUnexpectedFreeVariables req.interpretation req.candidate :=
  ((translationAccepts_iff A req).mp h).noUnexpectedFreeVariables

theorem accepted_translation_roundtrips :
    RoundTripEquivalent A.registry req.interpretation req.candidate :=
  ((translationAccepts_iff A req).mp h).roundTrip

theorem accepted_translation_is_confirmed : ConfirmationVerified A req :=
  ((translationAccepts_iff A req).mp h).confirmation

/-- Every symbol used by an accepted candidate is a registered, approved symbol, resolved
    uniquely, and the candidate's grounding is exactly the approved Lean definition. -/
theorem accepted_translation_uses_only_grounded_symbols :
    ∀ f ∈ req.candidate.claim.symbols, ∃ e, A.registry.resolve f = some e ∧
      e ∈ A.registry.symbols ∧
      req.candidate.groundings.filter (fun g => g.symbol == f) = [⟨f, e.leanName, e.provenance⟩] := by
  intro f hf
  have hg := ((translationAccepts_iff A req).mp h).groundedSymbols.2.1 f hf
  unfold groundOK at hg
  split at hg
  · rename_i e g hres hfil
    refine ⟨e, hres, ?_, ?_⟩
    · unfold Registry.resolve at hres
      split at hres
      · rename_i e' hent
        cases hres
        have : e ∈ A.registry.entries f := by rw [hent]; exact List.mem_singleton_self e
        exact (List.mem_filter.mp this).1
      · cases hres
    · rw [hfil]
      have hsym : g.symbol = f := by
        have : g ∈ req.candidate.groundings.filter (fun g => g.symbol == f) := by
          rw [hfil]; exact List.mem_singleton_self g
        simpa using (List.mem_filter.mp this).2
      simp only [Bool.and_eq_true, beq_iff_eq] at hg
      cases g; simp_all
  · cases hg

end Individual

/-! ## Rejection theorems -/

/-- Generic rejection: violating any field of the contract rejects. -/
theorem rejected_of_not_contract {A : Authority} {req : Request} (h : ¬ TranslationContract A req) :
    translationAccepts A req = false := (translationAccepts_eq_false_iff A req).mpr h

/-- **Semantic rejection**: a candidate whose meaning differs from the interpretation's in
    *some* model and valuation is rejected. -/
theorem semantically_inequivalent_rejected {A : Authority} {req : Request} {M : Model}
    {ρ : String → M.Dom}
    (hne : ¬ (req.interpretation.selected.denote M ρ ↔ req.candidate.claim.denote M ρ)) :
    translationAccepts A req = false := by
  cases h : translationAccepts A req
  · rfl
  · exact absurd (accepted_translation_preserves_meaning h M ρ) hne

theorem unresolved_ambiguity_rejected {A : Authority} {req : Request} {a : Ambiguity}
    (ha : a ∈ req.interpretation.ambiguities) (hr : a.resolution = none) :
    translationAccepts A req = false :=
  rejected_of_not_contract fun c => by
    have := c.noUnresolvedAmbiguity a ha; rw [hr] at this; cases this

theorem unknown_symbol_rejected {A : Authority} {req : Request} {f : String}
    (hf : f ∈ req.candidate.claim.symbols) (hu : A.registry.resolve f = none) :
    translationAccepts A req = false :=
  rejected_of_not_contract fun c => by
    have := c.groundedSymbols.2.1 f hf
    unfold groundOK at this; rw [hu] at this; cases this

theorem unknown_interpretation_symbol_rejected {A : Authority} {req : Request} {f : String}
    (hf : f ∈ req.interpretation.selected.symbols) (hu : A.registry.resolve f = none) :
    translationAccepts A req = false :=
  rejected_of_not_contract fun c => by
    have := c.interpretationGrounded f hf; rw [hu] at this; cases this

/-- A declared grounding naming no approved definition (hallucinated definition). -/
theorem unknown_definition_rejected {A : Authority} {req : Request} {g : SymbolRef}
    (hg : g ∈ req.candidate.groundings) (hu : A.registry.resolve g.symbol = none) :
    translationAccepts A req = false :=
  rejected_of_not_contract fun c => by
    have := c.groundedSymbols.2.2 g hg
    unfold refOK at this; rw [hu] at this; cases this

/-- A declared grounding pointing a symbol at a different (e.g. similarly named) Lean
    definition or provenance than the approved one. -/
theorem incorrect_symbol_identity_rejected {A : Authority} {req : Request} {g : SymbolRef}
    {e : SymbolEntry} (hg : g ∈ req.candidate.groundings) (he : A.registry.resolve g.symbol = some e)
    (hne : g.leanName ≠ e.leanName ∨ g.provenance ≠ e.provenance) :
    translationAccepts A req = false :=
  rejected_of_not_contract fun c => by
    have := c.groundedSymbols.2.2 g hg
    unfold refOK at this; rw [he] at this
    simp only [Bool.and_eq_true, beq_iff_eq] at this
    rcases hne with h | h
    · exact h this.1
    · exact h this.2

/-- Shadowed / duplicate grounding (1): the registry resolves some id ambiguously. -/
theorem duplicate_registry_entry_rejected {A : Authority} {req : Request}
    (hdup : ¬ (A.registry.symbols.map (·.id)).Nodup) : translationAccepts A req = false :=
  rejected_of_not_contract fun c => by
    have := c.groundedSymbols.1
    unfold Registry.wellFormedB at this
    simp only [Bool.and_eq_true, decide_eq_true_eq] at this
    exact hdup this.1.1

/-- Shadowed / duplicate grounding (2): the candidate declares two groundings for a used
    symbol (one shadowing the other). -/
theorem shadowed_grounding_rejected {A : Authority} {req : Request} {f : String}
    (hf : f ∈ req.candidate.claim.symbols)
    (h2 : 2 ≤ (req.candidate.groundings.filter (fun g => g.symbol == f)).length) :
    translationAccepts A req = false :=
  rejected_of_not_contract fun c => by
    have := c.groundedSymbols.2.1 f hf
    unfold groundOK at this
    split at this
    · rename_i hfil; rw [hfil] at h2; simp at h2
    · cases this

/-- Shadowed / duplicate grounding (3): a binder of the candidate is named like a
    registered symbol (it would capture that constant in the rendered Lean source). -/
theorem binder_shadowing_symbol_rejected {A : Authority} {req : Request} {b : Binder}
    (hb : b ∈ req.candidate.claim.params) (hs : b.name ∈ A.registry.symbols.map (·.id)) :
    translationAccepts A req = false :=
  rejected_of_not_contract fun c => by
    have := c.hygienic
    unfold SemanticClaim.hygienicB at this
    simp only [Bool.and_eq_true, List.all_eq_true] at this
    have h1 := this.1.2 b.name (List.mem_map.mpr ⟨b, hb, rfl⟩)
    have h2 : (A.registry.symbols.map (·.id) ++ A.registry.symbols.map (·.leanName)).contains
        b.name = true := List.contains_iff_mem.mpr (List.mem_append_left _ hs)
    rw [h2] at h1; cases h1

/-- Combined statement required by the contract. -/
theorem shadowed_or_duplicate_grounding_rejected {A : Authority} {req : Request} :
    (¬ (A.registry.symbols.map (·.id)).Nodup ∨
      (∃ f ∈ req.candidate.claim.symbols,
        2 ≤ (req.candidate.groundings.filter (fun g => g.symbol == f)).length) ∨
      (∃ b ∈ req.candidate.claim.params, b.name ∈ A.registry.symbols.map (·.id))) →
    translationAccepts A req = false := by
  rintro (h | ⟨f, hf, h⟩ | ⟨b, hb, h⟩)
  · exact duplicate_registry_entry_rejected h
  · exact shadowed_grounding_rejected hf h
  · exact binder_shadowing_symbol_rejected hb h

theorem dropped_assumption_rejected {A : Authority} {req : Request} {a : NFormula}
    (ha : a ∈ req.interpretation.selected.normalize.assumptions)
    (hn : a ∉ req.candidate.claim.normalize.assumptions) : translationAccepts A req = false :=
  rejected_of_not_contract fun c => hn (c.preservesAssumptions.1 a ha)

theorem added_assumption_rejected {A : Authority} {req : Request} {a : NFormula}
    (ha : a ∈ req.candidate.claim.normalize.assumptions)
    (hn : a ∉ req.interpretation.selected.normalize.assumptions) : translationAccepts A req = false :=
  rejected_of_not_contract fun c => hn (c.preservesAssumptions.2 a ha)

theorem quantifier_change_rejected {A : Authority} {req : Request}
    (h : ¬ PreservesQuantifiers req.interpretation req.candidate) :
    translationAccepts A req = false :=
  rejected_of_not_contract fun c => h c.preservesQuantifiers

theorem polarity_change_rejected {A : Authority} {req : Request}
    (h : ¬ PreservesPolarity req.interpretation req.candidate) :
    translationAccepts A req = false :=
  rejected_of_not_contract fun c => h c.preservesPolarity

theorem negation_change_rejected {A : Authority} {req : Request}
    (h : ¬ PreservesNegation req.interpretation req.candidate) :
    translationAccepts A req = false :=
  rejected_of_not_contract fun c => h c.preservesNegation

theorem connective_change_rejected {A : Authority} {req : Request}
    (h : ¬ PreservesConnectives req.interpretation req.candidate) :
    translationAccepts A req = false :=
  rejected_of_not_contract fun c => h c.preservesConnectives

theorem binding_change_rejected {A : Authority} {req : Request}
    (h : ¬ PreservesBindings req.interpretation req.candidate) :
    translationAccepts A req = false :=
  rejected_of_not_contract fun c => h c.preservesBindings

theorem free_variable_rejected {A : Authority} {req : Request} {x : String}
    (hx : x ∈ req.candidate.claim.freeVars) : translationAccepts A req = false :=
  rejected_of_not_contract fun c => by
    have := c.noUnexpectedFreeVariables.2; rw [this] at hx; cases hx

theorem unsupported_construct_rejected {A : Authority} {req : Request} {t : String}
    (ht : t ∈ req.candidate.claim.unsupportedTags) : translationAccepts A req = false :=
  rejected_of_not_contract fun c => by
    have := c.supportedFragment.2; rw [this] at ht; cases ht

theorem ill_typed_rejected {A : Authority} {req : Request}
    (ht : req.candidate.claim.wellTypedB A.registry = false) : translationAccepts A req = false :=
  rejected_of_not_contract fun c => by have := c.wellTyped.2; rw [ht] at this; cases this

theorem missing_confirmation_rejected {A : Authority} {req : Request}
    (h : req.confirmation = none) : translationAccepts A req = false :=
  rejected_of_not_contract fun c => by
    obtain ⟨r, hr, _⟩ := c.confirmation; rw [h] at hr; cases hr

/-- A confirmation receipt that the authorized verifier does not accept (forged). -/
theorem forged_confirmation_rejected {A : Authority} {req : Request} {r : ConfirmationReceipt}
    (h : req.confirmation = some r) (hf : A.verifyConfirmation r = false) :
    translationAccepts A req = false :=
  rejected_of_not_contract fun c => by
    obtain ⟨r', hr, _, hv⟩ := c.confirmation; rw [h] at hr; cases hr; rw [hf] at hv; cases hv

/-- A (possibly genuine) confirmation of a *different* interpretation is rejected. -/
theorem misbound_confirmation_rejected {A : Authority} {req : Request} {r : ConfirmationReceipt}
    (h : req.confirmation = some r) (hb : r.binds req.interpretation = false) :
    translationAccepts A req = false :=
  rejected_of_not_contract fun c => by
    obtain ⟨r', hr, hbd, _⟩ := c.confirmation; rw [h] at hr; cases hr; rw [hb] at hbd; cases hbd

theorem missing_elaboration_rejected {A : Authority} {req : Request}
    (hreq : A.requireElaboration = true) (h : req.elaboration = none) :
    translationAccepts A req = false :=
  rejected_of_not_contract fun c => by
    obtain ⟨r, hr, _⟩ := c.elaboration hreq; rw [h] at hr; cases hr

theorem forged_elaboration_rejected {A : Authority} {req : Request} {r : ElaborationReceipt}
    (hreq : A.requireElaboration = true) (h : req.elaboration = some r)
    (hf : A.verifyElaboration r = false) : translationAccepts A req = false :=
  rejected_of_not_contract fun c => by
    obtain ⟨r', hr, _, _, hv⟩ := c.elaboration hreq; rw [h] at hr; cases hr; rw [hf] at hv; cases hv

theorem missing_proof_rejected {A : Authority} {req : Request}
    (hreq : A.requireProof = true) (h : req.proof = none) : translationAccepts A req = false :=
  rejected_of_not_contract fun c => by
    obtain ⟨r, hr, _⟩ := c.proof hreq; rw [h] at hr; cases hr

theorem forged_proof_rejected {A : Authority} {req : Request} {r : ProofReceipt}
    (hreq : A.requireProof = true) (h : req.proof = some r) (hf : A.verifyProof r = false) :
    translationAccepts A req = false :=
  rejected_of_not_contract fun c => by
    obtain ⟨r', hr, _, _, _, hv⟩ := c.proof hreq; rw [h] at hr; cases hr; rw [hf] at hv; cases hv

/-- A proof receipt reporting a disallowed axiom (e.g. `sorryAx`) is rejected even if its
    signature verifies. -/
theorem disallowed_axiom_rejected {A : Authority} {req : Request} {r : ProofReceipt} {ax : String}
    (hreq : A.requireProof = true) (h : req.proof = some r) (hax : ax ∈ r.axioms)
    (hna : ax ∉ A.allowedAxioms) : translationAccepts A req = false :=
  rejected_of_not_contract fun c => by
    obtain ⟨r', hr, _, _, hall, _⟩ := c.proof hreq; rw [h] at hr; cases hr; exact hna (hall ax hax)

theorem lean_source_mismatch_rejected {A : Authority} {req : Request}
    (h : req.candidate.leanSource ≠ renderClaimLean A.registry req.candidate.claim) :
    translationAccepts A req = false :=
  rejected_of_not_contract fun c => h c.leanRendering

theorem explanation_mismatch_rejected {A : Authority} {req : Request} {e : ExplanationIR}
    (h : req.candidate.explanation = some e) (hne : e ≠ toExplanation A.registry req.candidate.claim) :
    translationAccepts A req = false :=
  rejected_of_not_contract fun c => by
    rcases c.roundTrip.2 with h' | h'
    · rw [h] at h'; cases h'
    · rw [h] at h'; cases h'; exact hne rfl

/-! ## Metadata independence (no authority from proposer identity or confidence) -/

/-- **The decision ignores model metadata**: the proposer identities, the self-reported
    confidence and the model's self-asserted confirmation flag have no influence on any
    diagnostic, hence on the verdict. -/
theorem decision_ignores_model_metadata (A : Authority) (req : Request) (conf : Nat)
    (p₁ p₂ : String) (asserted : Bool) :
    checkTranslation A { req with
      interpretation := { req.interpretation with proposer := p₁, modelAssertsConfirmed := asserted },
      confirmation := req.confirmation.map id,
      candidate := { req.candidate with proposer := p₂, modelConfidence := conf } } =
    checkTranslation A req := by
  cases req with
  | mk I conf' c el pr =>
    cases I; cases c; cases conf' <;> rfl

/-- A self-asserted confirmation without an authorized receipt never yields acceptance. -/
theorem model_asserted_confirmation_insufficient (A : Authority) (req : Request)
    (h : req.confirmation = none) (_hassert : req.interpretation.modelAssertsConfirmed = true) :
    translationAccepts A req = false := missing_confirmation_rejected h

/-- An unresolved ambiguity yields a non-accepting verdict (`NEEDS_CLARIFICATION` when it
    is the only problem, `REJECTED` otherwise). -/
theorem unresolved_ambiguity_not_accepted {A : Authority} {req : Request} {a : Ambiguity}
    (ha : a ∈ req.interpretation.ambiguities) (hr : a.resolution = none) :
    (checkTranslation A req).verdict ≠ .accepted := by
  rw [Ne, verdict_accepted_iff, unresolved_ambiguity_rejected ha hr]; simp

end PCS.V2.Semantic
