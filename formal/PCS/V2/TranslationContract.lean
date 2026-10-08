import PCS.V2.SemanticNormalize
import PCS.V2.ExplanationIR

/-!
# PCS Semantic Translation Contract v1 — objects, receipts and the certified contract

This file fixes the seven-way separation required by the contract:

1. **Untrusted natural-language proposal** — `Interpretation.sourceText` and
   `Interpretation.proposer` (never interpreted by any check), and the model's own claim
   `Interpretation.modelAssertsConfirmed` (never read by any check).
2. **Authorized structured interpretation** — `Interpretation.selected` together with the
   explicit ambiguity register `Interpretation.ambiguities`.
3. **Its independent meaning** — `SemanticClaim.denote` (`PCS.V2.SemanticIR`).
4. **Formal translation candidate** — `Candidate` (structured claim, symbol groundings,
   Lean source text, optional proposed explanation, proposer metadata).
5. **Executable semantic validator** — `PCS.V2.TranslationChecker.diagnose`.
6. **Kernel-verified proof obligations** — the theorems of `PCS.V2.TranslationChecker`
   and `PCS.V2.TranslationAuthority`.
7. **External assumptions** — `ConfirmationReceipt`, `ElaborationReceipt`, `ProofReceipt`
   and the verifier functions of an `Authority`; their meaning is an explicit hypothesis
   (`PCS.V2.TranslationAuthority.ExternalContracts`), never a theorem.

`TranslationContract A req` is the **certified specification**: the conjunction of all
semantic, grounding, hygiene, ambiguity, round-trip and receipt conditions.  The checker
is proved to decide it exactly (`PCS.V2.TranslationChecker.translationAccepts_iff`).
-/

set_option autoImplicit false

namespace PCS.V2.Semantic

/-! ## Interpretations, ambiguity, candidates -/

/-- Kinds of interpretation questions. -/
inductive AmbiguityKind where
  | scope | lexical | symbol | temporal | referent | other
  deriving Repr, DecidableEq, Inhabited

/-- An explicit interpretation question; `resolution = none` means unresolved. -/
structure Ambiguity where
  id : String
  kind : AmbiguityKind
  question : String
  resolution : Option String
  deriving Repr, DecidableEq, Inhabited

/-- A structured interpretation of a natural-language claim. -/
structure Interpretation where
  /-- the natural-language text (untrusted, never interpreted) -/
  sourceText : String
  /-- who proposed the interpretation (metadata, never trusted) -/
  proposer : String
  /-- a model's own assertion that the interpretation is confirmed (**ignored**) -/
  modelAssertsConfirmed : Bool
  /-- the selected structured interpretation -/
  selected : SemanticClaim
  /-- explicit ambiguity register -/
  ambiguities : List Ambiguity
  deriving Repr, DecidableEq, Inhabited

/-- A candidate's declaration of which approved definition a symbol denotes. -/
structure SymbolRef where
  symbol : String
  leanName : String
  provenance : String
  deriving Repr, DecidableEq, Inhabited

/-- A formal translation candidate (produced by an untrusted proposer). -/
structure Candidate where
  claim : SemanticClaim
  groundings : List SymbolRef
  /-- Lean proposition text; must be the deterministic rendering of `claim` -/
  leanSource : String
  /-- declaration name under which the proposition is to be elaborated/proved -/
  declName : String
  /-- an optional proposer-supplied explanation; must equal the derived one -/
  explanation : Option ExplanationIR
  /-- proposer identity (metadata, never trusted) -/
  proposer : String
  /-- self-reported model confidence in per-mille (metadata, **ignored**) -/
  modelConfidence : Nat
  deriving Repr, DecidableEq, Inhabited

/-! ## External receipts -/

/-- Evidence, issued by an authorized external process, that the exact interpretation
    (text, selected structure, ambiguity resolutions) was confirmed. -/
structure ConfirmationReceipt where
  sourceText : String
  selected : SemanticClaim
  ambiguities : List Ambiguity
  authority : String
  signature : String
  deriving Repr, DecidableEq, Inhabited

/-- Evidence, issued by an external elaboration service, that `leanSource` elaborates as
    the type of a declaration `declName` against the approved environment. -/
structure ElaborationReceipt where
  leanSource : String
  declName : String
  authority : String
  signature : String
  deriving Repr, DecidableEq, Inhabited

/-- Evidence, issued by an external proof-checking service, that the Lean kernel accepted a
    proof of `leanSource` as `declName`, depending on exactly `axioms`. -/
structure ProofReceipt where
  leanSource : String
  declName : String
  axioms : List String
  authority : String
  signature : String
  deriving Repr, DecidableEq, Inhabited

/-- A full translation request. -/
structure Request where
  interpretation : Interpretation
  confirmation : Option ConfirmationReceipt
  candidate : Candidate
  elaboration : Option ElaborationReceipt
  proof : Option ProofReceipt
  deriving Repr, Inhabited

/-- The trusted configuration: approved symbol environment, policy, receipt verifiers. -/
structure Authority where
  registry : Registry
  requireElaboration : Bool
  requireProof : Bool
  allowedAxioms : List String
  verifyConfirmation : ConfirmationReceipt → Bool
  verifyElaboration : ElaborationReceipt → Bool
  verifyProof : ProofReceipt → Bool

/-- A confirmation receipt is bound to exactly this interpretation. -/
def ConfirmationReceipt.binds (r : ConfirmationReceipt) (I : Interpretation) : Bool :=
  decide (r.sourceText = I.sourceText) && decide (r.selected = I.selected) &&
    decide (r.ambiguities = I.ambiguities)

/-! ## Structural skeletons of normal forms (used for individual diagnostics) -/

/-- Quantifiers with their positions (paths are child-index lists, root first). -/
def NFormula.quantSkel : List Nat → NFormula → List (List Nat × Quant × SortId)
  | _, .tt | _, .ff | _, .pred _ _ | _, .eq _ _ | _, .unsupported _ => []
  | p, .not φ => NFormula.quantSkel (p ++ [0]) φ
  | p, .and φ ψ | p, .or φ ψ | p, .imp φ ψ =>
    NFormula.quantSkel (p ++ [0]) φ ++ NFormula.quantSkel (p ++ [1]) ψ
  | p, .quant q s φ => (p, q, s) :: NFormula.quantSkel (p ++ [0]) φ

/-- Positions of negations. -/
def NFormula.negSkel : List Nat → NFormula → List (List Nat)
  | _, .tt | _, .ff | _, .pred _ _ | _, .eq _ _ | _, .unsupported _ => []
  | p, .not φ => p :: NFormula.negSkel (p ++ [0]) φ
  | p, .and φ ψ | p, .or φ ψ | p, .imp φ ψ =>
    NFormula.negSkel (p ++ [0]) φ ++ NFormula.negSkel (p ++ [1]) ψ
  | p, .quant _ _ φ => NFormula.negSkel (p ++ [0]) φ

/-- Atomic formulas with their logical polarity (`true` = positive); negation and the
    antecedent of an implication flip polarity. -/
def NFormula.atomPol : Bool → NFormula → List (NFormula × Bool)
  | _, .tt | _, .ff | _, .unsupported _ => []
  | b, .pred p args => [(.pred p args, b)]
  | b, .eq x y => [(.eq x y, b)]
  | b, .not φ => NFormula.atomPol (!b) φ
  | b, .and φ ψ | b, .or φ ψ => NFormula.atomPol b φ ++ NFormula.atomPol b ψ
  | b, .imp φ ψ => NFormula.atomPol (!b) φ ++ NFormula.atomPol b ψ
  | b, .quant _ _ φ => NFormula.atomPol b φ

/-- Connective shape (atoms erased). -/
def NFormula.shape : NFormula → NFormula
  | .pred _ _ | .eq _ _ => .pred "" []
  | .tt => .tt
  | .ff => .ff
  | .unsupported t => .unsupported t
  | .not φ => .not (NFormula.shape φ)
  | .and φ ψ => .and (NFormula.shape φ) (NFormula.shape ψ)
  | .or φ ψ => .or (NFormula.shape φ) (NFormula.shape ψ)
  | .imp φ ψ => .imp (NFormula.shape φ) (NFormula.shape ψ)
  | .quant q s φ => .quant q s (NFormula.shape φ)

mutual
/-- Variable occurrences of a nameless term (bound indices and free names, in order). -/
def NTerm.varOccs : NTerm → List NTerm
  | .bvar i => [.bvar i]
  | .fvar x => [.fvar x]
  | .app _ args => NTerm.varOccsList args
def NTerm.varOccsList : List NTerm → List NTerm
  | [] => []
  | t :: ts => NTerm.varOccs t ++ NTerm.varOccsList ts
end

/-- Binding skeleton: every variable occurrence with its de Bruijn index (or free name). -/
def NFormula.varSkel : NFormula → List NTerm
  | .tt | .ff | .unsupported _ => []
  | .pred _ args => NTerm.varOccsList args
  | .eq a b => NTerm.varOccs a ++ NTerm.varOccs b
  | .not φ | .quant _ _ φ => NFormula.varSkel φ
  | .and φ ψ | .or φ ψ | .imp φ ψ => NFormula.varSkel φ ++ NFormula.varSkel ψ

/-! ## The certified semantic predicates -/

section Predicates

variable (R : Registry)

/-- All interpretation questions are resolved. -/
def NoUnresolvedAmbiguity (I : Interpretation) : Prop :=
  ∀ a ∈ I.ambiguities, a.resolution.isSome = true

/-- Symbol `f` of a candidate is grounded: it resolves uniquely in the registry and the
    candidate declares exactly one grounding for it, equal to the canonical identity. -/
def groundOK (cand : Candidate) (f : String) : Bool :=
  match R.resolve f, cand.groundings.filter (fun g => g.symbol == f) with
  | some e, [g] => g.leanName == e.leanName && g.provenance == e.provenance
  | _, _ => false

/-- A declared grounding names an approved definition with its canonical identity. -/
def refOK (g : SymbolRef) : Bool :=
  match R.resolve g.symbol with
  | some e => g.leanName == e.leanName && g.provenance == e.provenance
  | none => false

/-- **Grounded symbols**: well-formed registry, every symbol used by the candidate is
    uniquely and correctly grounded, and every declared grounding is an approved
    definition (no hallucinated or substituted definitions). -/
def GroundedSymbols (cand : Candidate) : Prop :=
  R.wellFormedB = true ∧ (∀ f ∈ cand.claim.symbols, groundOK R cand f = true) ∧
    (∀ g ∈ cand.groundings, refOK R g = true)

/-- Every symbol of the selected interpretation resolves uniquely in the registry. -/
def InterpretationGrounded (I : Interpretation) : Prop :=
  ∀ f ∈ I.selected.symbols, (R.resolve f).isSome = true

/-- Both claims are well typed under the registry. -/
def WellTypedPair (I : Interpretation) (cand : Candidate) : Prop :=
  I.selected.wellTypedB R = true ∧ cand.claim.wellTypedB R = true

/-- Binder hygiene of a claim: parameters distinct and no binder re-binds an in-scope
    variable or coincides with a registered symbol id / Lean name. -/
def SemanticClaim.hygienicB (c : SemanticClaim) : Bool :=
  let reserved := R.symbols.map (·.id) ++ R.symbols.map (·.leanName)
  let ps := c.params.map (·.name)
  decide ps.Nodup && ps.all (fun x => !reserved.contains x) &&
    (c.assumptions ++ [c.conclusion]).all (Formula.hygienicB (ps ++ reserved))

end Predicates

/-- Neither claim has free variables. -/
def NoUnexpectedFreeVariables (I : Interpretation) (cand : Candidate) : Prop :=
  I.selected.freeVars = [] ∧ cand.claim.freeVars = []

/-- Neither claim contains an unsupported construct. -/
def SupportedFragment (I : Interpretation) (cand : Candidate) : Prop :=
  I.selected.unsupportedTags = [] ∧ cand.claim.unsupportedTags = []

/-- Quantifier structure (parameter sorts, and every inner quantifier's kind, sort and
    position) is preserved. -/
def PreservesQuantifiers (I : Interpretation) (cand : Candidate) : Prop :=
  I.selected.normalize.paramSorts = cand.claim.normalize.paramSorts ∧
    NFormula.quantSkel [] I.selected.normalize.conclusion =
      NFormula.quantSkel [] cand.claim.normalize.conclusion

/-- The polarity of every atomic occurrence in the conclusion is preserved. -/
def PreservesPolarity (I : Interpretation) (cand : Candidate) : Prop :=
  NFormula.atomPol true I.selected.normalize.conclusion =
    NFormula.atomPol true cand.claim.normalize.conclusion

/-- The positions of all negations in the conclusion are preserved. -/
def PreservesNegation (I : Interpretation) (cand : Candidate) : Prop :=
  NFormula.negSkel [] I.selected.normalize.conclusion =
    NFormula.negSkel [] cand.claim.normalize.conclusion

/-- The connective shape of the conclusion (∧ vs ∨ vs →, etc.) is preserved. -/
def PreservesConnectives (I : Interpretation) (cand : Candidate) : Prop :=
  NFormula.shape I.selected.normalize.conclusion = NFormula.shape cand.claim.normalize.conclusion

/-- No assumption of the interpretation is missing from the candidate. -/
def NoAssumptionDropped (I : Interpretation) (cand : Candidate) : Prop :=
  ∀ a ∈ I.selected.normalize.assumptions, a ∈ cand.claim.normalize.assumptions

/-- The candidate adds no assumption absent from the interpretation. -/
def NoAssumptionAdded (I : Interpretation) (cand : Candidate) : Prop :=
  ∀ a ∈ cand.claim.normalize.assumptions, a ∈ I.selected.normalize.assumptions

/-- Assumptions are preserved exactly (as a set, up to α-renaming). -/
def PreservesAssumptions (I : Interpretation) (cand : Candidate) : Prop :=
  NoAssumptionDropped I cand ∧ NoAssumptionAdded I cand

/-- Bindings are preserved: same number of parameters and every variable occurrence of the
    conclusion refers to the same binder (de Bruijn index) or free name. -/
def PreservesBindings (I : Interpretation) (cand : Candidate) : Prop :=
  I.selected.params.length = cand.claim.params.length ∧
    NFormula.varSkel I.selected.normalize.conclusion =
      NFormula.varSkel cand.claim.normalize.conclusion

instance (I : Interpretation) (cand : Candidate) : Decidable (PreservesPolarity I cand) :=
  inferInstanceAs (Decidable (_ = _))
instance (I : Interpretation) (cand : Candidate) : Decidable (PreservesNegation I cand) :=
  inferInstanceAs (Decidable (_ = _))
instance (I : Interpretation) (cand : Candidate) : Decidable (PreservesConnectives I cand) :=
  inferInstanceAs (Decidable (_ = _))
instance (I : Interpretation) (cand : Candidate) : Decidable (PreservesBindings I cand) :=
  inferInstanceAs (Decidable (_ ∧ _))

/-- **Normal-form equivalence** (justified by `alphaEquiv_denote_iff`). -/
def NormalFormEquivalent (I : Interpretation) (cand : Candidate) : Prop :=
  I.selected.normalize.Equiv cand.claim.normalize

/-- Structured round trip: the candidate's derived Explanation IR reads back to a claim
    normal-form-equivalent to the interpretation, and a proposer-supplied explanation (if
    any) is exactly the derived one. -/
def RoundTripEquivalent (R : Registry) (I : Interpretation) (cand : Candidate) : Prop :=
  I.selected.normalize.Equiv (toExplanation R cand.claim).toClaim.normalize ∧
    (cand.explanation = none ∨ cand.explanation = some (toExplanation R cand.claim))

/-- The Lean source is the deterministic rendering of the candidate claim. -/
def LeanRenderingFaithful (R : Registry) (cand : Candidate) : Prop :=
  cand.leanSource = renderClaimLean R cand.claim

/-- Confirmation: an authorized receipt bound to this exact interpretation verifies. -/
def ConfirmationVerified (A : Authority) (req : Request) : Prop :=
  ∃ r, req.confirmation = some r ∧ r.binds req.interpretation = true ∧
    A.verifyConfirmation r = true

/-- Elaboration (if required): a receipt bound to the exact Lean source and declaration
    name verifies. -/
def ElaborationVerified (A : Authority) (req : Request) : Prop :=
  A.requireElaboration = true → ∃ r, req.elaboration = some r ∧
    r.leanSource = req.candidate.leanSource ∧ r.declName = req.candidate.declName ∧
    A.verifyElaboration r = true

/-- Proof (if required): a receipt bound to the exact Lean source and declaration name,
    depending only on allowed axioms, verifies. -/
def ProofVerified (A : Authority) (req : Request) : Prop :=
  A.requireProof = true → ∃ r, req.proof = some r ∧
    r.leanSource = req.candidate.leanSource ∧ r.declName = req.candidate.declName ∧
    (∀ ax ∈ r.axioms, ax ∈ A.allowedAxioms) ∧ A.verifyProof r = true

/-- **The certified translation contract.** -/
structure TranslationContract (A : Authority) (req : Request) : Prop where
  noUnresolvedAmbiguity : NoUnresolvedAmbiguity req.interpretation
  confirmation : ConfirmationVerified A req
  interpretationGrounded : InterpretationGrounded A.registry req.interpretation
  groundedSymbols : GroundedSymbols A.registry req.candidate
  wellTyped : WellTypedPair A.registry req.interpretation req.candidate
  supportedFragment : SupportedFragment req.interpretation req.candidate
  noUnexpectedFreeVariables : NoUnexpectedFreeVariables req.interpretation req.candidate
  hygienic : req.candidate.claim.hygienicB A.registry = true
  preservesQuantifiers : PreservesQuantifiers req.interpretation req.candidate
  preservesPolarity : PreservesPolarity req.interpretation req.candidate
  preservesNegation : PreservesNegation req.interpretation req.candidate
  preservesConnectives : PreservesConnectives req.interpretation req.candidate
  preservesAssumptions : PreservesAssumptions req.interpretation req.candidate
  preservesBindings : PreservesBindings req.interpretation req.candidate
  normalFormEquivalent : NormalFormEquivalent req.interpretation req.candidate
  roundTrip : RoundTripEquivalent A.registry req.interpretation req.candidate
  leanRendering : LeanRenderingFaithful A.registry req.candidate
  elaboration : ElaborationVerified A req
  proof : ProofVerified A req

end PCS.V2.Semantic
