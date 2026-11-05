import PCS.V2.TranslationV2Json
import PCS.V2.SHA256
import PCS.V2.CNL

/-!
# Repair obligations, explanation views and verifier-grounded training records (v2)

Everything here is *derived deterministically from the checked decision*; nothing is
judged by a model.

* `RepairObligation` — a typed repair request for an untrusted proposer: failing component,
  expected invariant, observed failure, whether a mechanical repair is possible, whether
  human clarification is required, and the countermodel (if any).  Obligations that require
  human intent are never marked mechanically repairable (`human_obligations_not_mechanical`).
* `explanationViews` — three deterministic views of an accepted claim (beginner, technical,
  proof/trust boundary).  They are literal renderings of the Explanation IR, not certified
  English; the trust view records exactly what is and is not established.
* `TrainingRecord` / `trainingRecord` — the stable `pcs-verifier-feedback-v1` record for future
  supervised / reinforcement learning, with content digests, checker version, verdict,
  obligations, countermodel, certificate and an explicit provenance and partition.
  `label_positive_sound` and `label_negative_sound` prove that the two *verified* labels are
  semantically justified; every other case is labelled `UNRESOLVED` or `CONTRACT_REJECTION`.
-/

set_option autoImplicit false

namespace PCS.V2.Semantic

open PCS.V2.Json

/-! ## Repair obligations -/

/-- A typed repair request. -/
structure RepairObligation where
  code : String
  component : String
  expectedInvariant : String
  observed : String
  mechanicallyRepairable : Bool
  requiresHumanClarification : Bool
  deriving Repr, DecidableEq, Inhabited

/-- The invariant each failure code protects. -/
def FailureCode.invariant : FailureCode → String
  | .ambiguousScope | .unresolvedAmbiguity => "every interpretation question is resolved"
  | .confirmationMissing | .confirmationNotVerified =>
    "an authorized receipt confirms exactly this interpretation"
  | .registryMalformed => "registry ids are unique and signatures use registered sorts"
  | .unresolvedSymbol | .unknownDefinition | .incorrectSymbolIdentity
  | .duplicateOrShadowedGrounding => "every symbol is uniquely grounded in an approved definition"
  | .illTyped => "both claims are well typed under the registry"
  | .unsupportedConstruct => "only constructs of the supported fragment occur"
  | .unexpectedFreeVariable => "both claims are closed"
  | .binderShadowing => "no binder re-binds a variable or shadows a registered symbol"
  | .quantifierMismatch => "quantifier kinds, sorts and positions agree"
  | .polarityMismatch => "every atomic occurrence keeps its polarity"
  | .negationMismatch => "negations occur at the same positions"
  | .connectiveMismatch => "connective structure agrees"
  | .assumptionDropped | .assumptionAdded => "assumption sets agree (up to α-renaming)"
  | .bindingMismatch => "every variable occurrence refers to the same binder"
  | .semanticMismatch => "the candidate is denotationally equivalent to the interpretation"
  | .roundtripMismatch => "the supplied explanation is the derived Explanation IR"
  | .leanRenderingMismatch => "the Lean source is the deterministic rendering of the claim"
  | .elaborationNotVerified => "an authorized elaboration receipt binds the exact Lean source"
  | .proofNotVerified => "an authorized proof receipt binds the exact Lean source"
  | .malformedInput => "input is canonical JSON of the expected schema"

/-- Can an untrusted proposer repair this without new human input? -/
def FailureCode.mechanical : FailureCode → Bool
  | .ambiguousScope | .unresolvedAmbiguity | .confirmationMissing | .confirmationNotVerified
  | .registryMalformed | .elaborationNotVerified | .proofNotVerified => false
  | _ => true

def toObligation (d : Diagnostic) : RepairObligation :=
  { code := d.code.name, component := d.component, expectedInvariant := d.code.invariant,
    observed := d.detail, mechanicallyRepairable := d.code.mechanical,
    requiresHumanClarification := d.code.isClarification }

/-- Repair obligations of a decision (none for a certified translation). -/
def repairObligations (d : DecisionV2) : List RepairObligation :=
  if d.outcome = .certifiedTranslation then [] else d.diagnostics.map toObligation

/-- PCS never asks a proposer to guess missing human intent. -/
theorem human_obligations_not_mechanical (d : Diagnostic) :
    (toObligation d).requiresHumanClarification = true →
      (toObligation d).mechanicallyRepairable = false := by
  obtain ⟨c, _, _⟩ := d
  cases c <;> simp [toObligation, FailureCode.isClarification, FailureCode.mechanical]

/-! ## Explanation views -/

/-- Deterministic explanation views (literal renderings, not certified prose). -/
structure ExplanationViews where
  beginner : String
  technical : String
  trust : List String
  deriving Repr, Inhabited

def semanticLinkText : SemanticStatus → String
  | .normalFormEqual => "identical canonical normal forms (α-renaming, ≠-desugaring, assumption order)"
  | .certified c => "a replayed equivalence certificate (" ++ toString (c.left.length + c.right.length) ++
      " certified rewrite steps)"
  | .counterexample _ => "none: a verified countermodel shows the meanings differ"
  | .unknown _ => "none established within the search bounds"

def explanationViews (R : Registry) (c : SemanticClaim) (sem : SemanticStatus) : ExplanationViews :=
  let e := toExplanation R c
  { beginner := "In plain terms (literal rendering, not certified prose): " ++ e.renderLiteral,
    technical := renderClaimLean R c,
    trust := ("Semantic link between the selected interpretation and this claim: " ++
        semanticLinkText sem) :: e.trustBoundary ++ e.notEstablished.map ("NOT established: " ++ ·) }

/-! ## Verifier-grounded training records -/

/-- Labels a record may carry. -/
inductive FeedbackLabel where
  /-- certified: equivalent to the selected interpretation in every model -/
  | verifiedPositive
  /-- a checked finite countermodel shows the meanings differ -/
  | verifiedSemanticNegative
  /-- a deterministic contract gate failed (grounding, typing, receipts, …) -/
  | contractRejection
  /-- nothing was established either way -/
  | unresolved
  deriving Repr, DecidableEq, Inhabited

def FeedbackLabel.name : FeedbackLabel → String
  | .verifiedPositive => "VERIFIED_POSITIVE"
  | .verifiedSemanticNegative => "VERIFIED_SEMANTIC_NEGATIVE"
  | .contractRejection => "CONTRACT_REJECTION"
  | .unresolved => "UNRESOLVED"

def labelOf (d : DecisionV2) : FeedbackLabel :=
  match d.outcome with
  | .certifiedTranslation => .verifiedPositive
  | .verifiedCounterexample => .verifiedSemanticNegative
  | .invalidProposal | .unsupportedFragment => .contractRejection
  | _ => .unresolved

theorem labelOf_positive {d : DecisionV2} (h : labelOf d = .verifiedPositive) :
    d.outcome = .certifiedTranslation := by
  unfold labelOf at h
  cases ho : d.outcome <;> rw [ho] at h <;> first | rfl | cases h

theorem labelOf_negative {d : DecisionV2} (h : labelOf d = .verifiedSemanticNegative) :
    d.outcome = .verifiedCounterexample := by
  unfold labelOf at h
  cases ho : d.outcome <;> rw [ho] at h <;> first | rfl | cases h

/-- A `VERIFIED_POSITIVE` label is semantically justified (every model, every valuation). -/
theorem label_positive_sound {A : Authority} {r : RequestV2}
    (h : labelOf (decideV2 A r) = .verifiedPositive) (M : Model) (ρ : String → M.Dom) :
    r.base.interpretation.selected.denote M ρ ↔ r.base.candidate.claim.denote M ρ :=
  decideV2_certified_preserves_denotation (labelOf_positive h) M ρ

/-- A `VERIFIED_SEMANTIC_NEGATIVE` label carries a checked countermodel. -/
theorem label_negative_sound {A : Authority} {r : RequestV2}
    (h : labelOf (decideV2 A r) = .verifiedSemanticNegative) :
    ∃ w, checkCountermodel A.registry r.base.interpretation.selected r.base.candidate.claim w = true := by
  obtain ⟨w, _, hw, _⟩ := decideV2_counterexample_sound (labelOf_negative h)
  exact ⟨w, hw⟩

/-- Version of the checker recorded in every training record. -/
def checkerVersion : String := "pcs-semantic-check/v2.0 (Lean 4.28.0)"

def digestOf (v : JVal) : String := PCS.V2.SHA256.sha256Hex (jcsBytes v)

/-- Deterministic train/evaluation partition from the interpretation digest (first hex
    digit `0`–`1` ⇒ evaluation, i.e. 12.5%). -/
def partitionOf (interpDigest : String) : String :=
  match interpDigest.toList.head? with
  | some '0' | some '1' => "evaluation"
  | _ => "train"

/-- Encode a repair obligation. -/
def encObligation (o : RepairObligation) : JVal :=
  .obj [("code", .str o.code), ("component", .str o.component),
    ("expected_invariant", .str o.expectedInvariant),
    ("mechanically_repairable", .bool o.mechanicallyRepairable), ("observed", .str o.observed),
    ("requires_human_clarification", .bool o.requiresHumanClarification)]

/-- The `pcs-verifier-feedback-v1` training record of one checker run. -/
def trainingRecord (cfg : AuthorityConfig) (r : RequestV2) (d : DecisionV2)
    (provenance sourceRevision : String) : JVal :=
  let iDig := digestOf (encClaim r.base.interpretation.selected)
  .obj [
    ("candidate", encClaim r.base.candidate.claim),
    ("candidate_digest", .str (digestOf (encClaim r.base.candidate.claim))),
    ("certificate", match d.semantic with
      | .certified c => encCert c
      | _ => .null),
    ("checker_version", .str checkerVersion),
    ("confirmation_authority", match r.base.confirmation with
      | some rc => .str rc.authority
      | none => .null),
    ("countermodel", match d.semantic with
      | .counterexample w => encCountermodel w
      | _ => .null),
    ("diagnostics", .arr (d.diagnostics.map encDiagnostic)),
    ("feedback_available_before_choice", .arr []),
    ("interpretation", encClaim r.base.interpretation.selected),
    ("interpretation_digest", .str iDig),
    ("label", .str (labelOf d).name),
    ("model_confidence_ignored", encNat r.base.candidate.modelConfidence),
    ("obligations", .arr ((repairObligations d).map encObligation)),
    ("outcome", .str d.outcome.name),
    ("partition", .str (partitionOf iDig)),
    ("provenance", .str provenance),
    ("registry_digest", .str (digestOf (encRegistry cfg.registry))),
    ("repair_attempts", .arr []),
    ("schema", .str "pcs-verifier-feedback-v1"),
    ("semantic_status", encSemanticStatus d.semantic),
    ("source_revision", .str sourceRevision)]

/-! ## Decision output -/

/-- The literal PCS-CNL sentences of a claim (exact grammar; see `PCS.V2.CNL`).  `cnl_valid`
    is `true` exactly when every sentence is guaranteed to parse back to its formula
    (`controlled_language_print_parse`). -/
def encCNL (c : SemanticClaim) : JVal :=
  .obj [("assumptions", encStrs (c.assumptions.map CNL.renderCNL)),
    ("cnl_valid", .bool (c.assumptions.all Formula.cnlValid && c.conclusion.cnlValid)),
    ("conclusion", .str (CNL.renderCNL c.conclusion)),
    ("grammar", .str "pcs-cnl-v1"),
    ("parameters", encStrs (c.params.map (fun b => b.name ++ " of-sort " ++ b.sort)))]

def encViews (v : ExplanationViews) : JVal :=
  .obj [("beginner", .str v.beginner), ("technical", .str v.technical), ("trust", encStrs v.trust)]

/-- Canonical JSON output of the v2 front end. -/
def encCliResultV2 (cfg : Option AuthorityConfig) (res : CliResultV2) : JVal :=
  .obj [
    ("certificate", encOpt encCert res.decision.certificate),
    ("controlled_language", encOpt (fun e => encCNL e.toClaim) res.explanation),
    ("diagnostics", .arr (res.decision.diagnostics.map encDiagnostic)),
    ("expected_lean_source", .str res.expectedLeanSource),
    ("explanation", encOpt encExplanation res.explanation),
    ("explanation_views", match res.explanation, cfg with
      | some e, some c => encViews (explanationViews c.registry e.toClaim res.decision.semantic)
      | _, _ => .null),
    ("label", .str (labelOf res.decision).name),
    ("outcome", .str res.decision.outcome.name),
    ("repair_obligations", .arr ((repairObligations res.decision).map encObligation)),
    ("schema", .str "pcs-semantic-decision-v2"),
    ("semantic_status", encSemanticStatus res.decision.semantic)]

end PCS.V2.Semantic
