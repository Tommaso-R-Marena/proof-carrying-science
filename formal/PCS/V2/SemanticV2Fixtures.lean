import PCS.V2.TranslationV2

/-!
# Semantic Intelligence v2 — domain fixtures (AI safety, reproducibility, biology)

Positive and adversarial fixtures in three domains, over one approved registry.  Every
kernel-checkable fact is checked by the Lean kernel (`decide`) on the actual functions:

* **positives** — `decideV2` outputs `CERTIFIED_TRANSLATION` on a request with a supplied
  certificate (`*_certified`), and v1 rejects the same request (`*_v1_rejects`), i.e. v2
  strictly extends v1 on these meaning-preserving rewrites;
* **negatives** — a concrete finite countermodel passes `checkCountermodel` (`*_countermodel`),
  so by `countermodel_refutes_contract_v2` **no certificate whatsoever** can make the request
  acceptable, and v1 rejects (`*_never_certified`).

The countermodels were produced by the bounded search `searchCountermodel` and are the
minimal ones it found; the complete runs of `decideV2` (including the untrusted searches)
are executed by `tools/WriteSemanticV2Fixtures.lean` and by the compiled binary
(`tools/run_semantic_v2_fixture_tests.sh`), which is executable testing, not a proof.

The fixture authority uses the same stand-in receipt verifier as the v1 fixtures; the JSON
fixtures are re-signed with Ed25519 by the writer tool.  No external biological, scientific
or deployment fact is asserted: predicates are uninterpreted approved symbols, and
statements about deployed systems remain conditional on `FaithfulLog`-style bridges.
-/

set_option autoImplicit false

namespace PCS.V2.Semantic.FixturesV2

open PCS.V2.Semantic

def v (x : String) : Term := .var x
def P (p : String) (args : List Term) : Formula := .pred p args
def prov (m : String) : String := "PCS/Examples/" ++ m ++ ".lean"

/-! ## Approved registry -/

def registry : Registry :=
  { sorts := [⟨"Time", "Nat", "Lean core"⟩, ⟨"Action", "PCS.Examples.Agent.Action", prov "Agent"⟩,
      ⟨"Run", "PCS.Examples.Repro.Run", prov "Repro"⟩,
      ⟨"Dataset", "PCS.Examples.Repro.Dataset", prov "Repro"⟩,
      ⟨"Digest", "PCS.Examples.Repro.Digest", prov "Repro"⟩,
      ⟨"Residue", "PCS.Examples.Bio.Residue", prov "Bio"⟩,
      ⟨"Pos", "PCS.Examples.Bio.Pos", prov "Bio"⟩],
    symbols := [
      ⟨"revoked", "PCS.Examples.Agent.revoked", .pred ["Time"], prov "Agent"⟩,
      ⟨"before", "PCS.Examples.Agent.before", .pred ["Time", "Time"], prov "Agent"⟩,
      ⟨"performs", "PCS.Examples.Agent.performs", .pred ["Time", "Action"], prov "Agent"⟩,
      ⟨"forbidden", "PCS.Examples.Agent.forbidden", .pred ["Action"], prov "Agent"⟩,
      ⟨"withinBudget", "PCS.Examples.Agent.withinBudget", .pred ["Time"], prov "Agent"⟩,
      ⟨"sameConfig", "PCS.Examples.Repro.sameConfig", .pred ["Run", "Run"], prov "Repro"⟩,
      ⟨"outputDigest", "PCS.Examples.Repro.outputDigest", .fn ["Run"] "Digest", prov "Repro"⟩,
      ⟨"evaluatedOn", "PCS.Examples.Repro.evaluatedOn", .pred ["Run", "Dataset"], prov "Repro"⟩,
      ⟨"trainedOn", "PCS.Examples.Repro.trainedOn", .pred ["Run", "Dataset"], prov "Repro"⟩,
      ⟨"posOf", "PCS.Examples.Bio.posOf", .fn ["Residue"] "Pos", prov "Bio"⟩,
      ⟨"binding", "PCS.Examples.Bio.binding", .pred ["Residue"], prov "Bio"⟩,
      ⟨"inSite", "PCS.Examples.Bio.inSite", .pred ["Pos"], prov "Bio"⟩,
      ⟨"inSiteLegacy", "PCS.Examples.Bio.inSiteLegacy", .pred ["Pos"], prov "Bio"⟩,
      ⟨"validIndex", "PCS.Examples.Bio.validIndex", .pred ["Pos"], prov "Bio"⟩] }

def ground (f : String) : SymbolRef :=
  match registry.resolve f with
  | some e => ⟨f, e.leanName, e.provenance⟩
  | none => ⟨f, "?", "?"⟩

def fixtureAuthorityName : String := "pcs-fixture-authority"
def fixtureToken : String := "fixture-valid-signature"

def authority : Authority :=
  { registry := registry,
    requireElaboration := true,
    requireProof := true,
    allowedAxioms := ["propext", "Classical.choice", "Quot.sound"],
    verifyConfirmation := fun r => r.authority == fixtureAuthorityName && r.signature == fixtureToken,
    verifyElaboration := fun r => r.authority == fixtureAuthorityName && r.signature == fixtureToken,
    verifyProof := fun r => r.authority == fixtureAuthorityName && r.signature == fixtureToken }

def interp (text : String) (c : SemanticClaim) (amb : List Ambiguity := []) : Interpretation :=
  { sourceText := text, proposer := "model:untrusted", modelAssertsConfirmed := true,
    selected := c, ambiguities := amb }

def confirm (I : Interpretation) : ConfirmationReceipt :=
  ⟨I.sourceText, I.selected, I.ambiguities, fixtureAuthorityName, fixtureToken⟩

def cand (c : SemanticClaim) (conf : Nat := 900) : Candidate :=
  { claim := c, groundings := (dedupStr c.symbols).map ground,
    leanSource := renderClaimLean registry c, declName := "pcs_claim", explanation := none,
    proposer := "model:untrusted", modelConfidence := conf }

def request (I : Interpretation) (C : Candidate) : Request :=
  { interpretation := I, confirmation := some (confirm I), candidate := C,
    elaboration := some ⟨C.leanSource, C.declName, fixtureAuthorityName, fixtureToken⟩,
    proof := some ⟨C.leanSource, C.declName, ["propext"], fixtureAuthorityName, fixtureToken⟩ }

/-- Bounds used for kernel checking (no search needed: the certificate is supplied). -/
def noSearch : SearchBounds := ⟨0, 0, 0, 0⟩

def reqV2 (I : Interpretation) (C : Candidate) (cert : Option EquivCert)
    (b : SearchBounds := SearchBounds.default) : RequestV2 :=
  ⟨request I C, cert, b⟩

/-! ## A. AI safety: permission revocation -/

def revText : String :=
  "After permission is revoked, the agent never performs a forbidden action."

def revAmb : List Ambiguity :=
  [⟨"after", .temporal, "Does 'after' mean strictly later in the committed trace?",
      some "strictly later time point: before(i, j)"⟩,
   ⟨"forbidden", .symbol, "Which notion of forbidden action?", some "PCS.Examples.Agent.forbidden"⟩,
   ⟨"trace", .referent, "Committed log or deployed behaviour?",
      some "the committed trace; deployed behaviour needs a separate FaithfulLog bridge"⟩]

/-- Selected reading: `∀ i, revoked i → ∀ j a, before i j ∧ performs j a → ¬ forbidden a`. -/
def revClaim : SemanticClaim :=
  { params := [⟨"i", "Time"⟩], assumptions := [P "revoked" [v "i"]],
    conclusion := .quant .all "j" "Time" (.quant .all "a" "Action"
      (.imp (.and (P "before" [v "i", v "j"]) (P "performs" [v "j", v "a"]))
        (.not (P "forbidden" [v "a"])))) }

def revI : Interpretation := interp revText revClaim revAmb

/-- Meaning-preserving rewrite: quantifiers exchanged, `→ ¬` as a negated conjunction,
    conjuncts reordered, binders renamed. -/
def revPosClaim : SemanticClaim :=
  { params := [⟨"r", "Time"⟩], assumptions := [P "revoked" [v "r"]],
    conclusion := .quant .all "act" "Action" (.quant .all "t" "Time"
      (.not (.and (P "forbidden" [v "act"]) (.and (P "performs" [v "t", v "act"]) (P "before" [v "r", v "t"]))))) }

/-- Mutation: `∀ a` became `∃ a`. -/
def revExistsClaim : SemanticClaim :=
  { revClaim with conclusion := .quant .all "j" "Time" (.quant .ex "a" "Action"
      (.imp (.and (P "before" [v "i", v "j"]) (P "performs" [v "j", v "a"]))
        (.not (P "forbidden" [v "a"])))) }

/-- Mutation: time order reversed (`before j i`). -/
def revTimeReversedClaim : SemanticClaim :=
  { revClaim with conclusion := .quant .all "j" "Time" (.quant .all "a" "Action"
      (.imp (.and (P "before" [v "j", v "i"]) (P "performs" [v "j", v "a"]))
        (.not (P "forbidden" [v "a"])))) }

/-- Mutation: the revocation assumption was dropped (a strictly stronger claim). -/
def revDroppedClaim : SemanticClaim := { revClaim with assumptions := [] }

/-- Mutation: `∧` became `∨` in the premise. -/
def revOrClaim : SemanticClaim :=
  { revClaim with conclusion := .quant .all "j" "Time" (.quant .all "a" "Action"
      (.imp (.or (P "before" [v "i", v "j"]) (P "performs" [v "j", v "a"]))
        (.not (P "forbidden" [v "a"])))) }

/-- Mutation: the negation disappeared. -/
def revNegDroppedClaim : SemanticClaim :=
  { revClaim with conclusion := .quant .all "j" "Time" (.quant .all "a" "Action"
      (.imp (.and (P "before" [v "i", v "j"]) (P "performs" [v "j", v "a"]))
        (P "forbidden" [v "a"]))) }

/-! ## B. Scientific reproducibility -/

def reproText : String := "Runs with the same configuration produce identical output digests."

/-- `∀ r₁ r₂, sameConfig r₁ r₂ → outputDigest r₁ = outputDigest r₂` -/
def reproClaim : SemanticClaim :=
  { params := [], assumptions := [],
    conclusion := .quant .all "r1" "Run" (.quant .all "r2" "Run"
      (.imp (P "sameConfig" [v "r1", v "r2"])
        (.eq (.app "outputDigest" [v "r1"]) (.app "outputDigest" [v "r2"])))) }

def reproI : Interpretation := interp reproText reproClaim

/-- Looks like an argument-order mistake but is equivalent: binders exchanged *and* the
    equation flipped. -/
def reproPosClaim : SemanticClaim :=
  { params := [], assumptions := [],
    conclusion := .quant .all "b" "Run" (.quant .all "a" "Run"
      (.imp (P "sameConfig" [v "a", v "b"])
        (.eq (.app "outputDigest" [v "b"]) (.app "outputDigest" [v "a"])))) }

/-- Mutation: the converse (equal digests ⇒ same configuration). -/
def reproConverseClaim : SemanticClaim :=
  { params := [], assumptions := [],
    conclusion := .quant .all "r1" "Run" (.quant .all "r2" "Run"
      (.imp (.eq (.app "outputDigest" [v "r1"]) (.app "outputDigest" [v "r2"]))
        (P "sameConfig" [v "r1", v "r2"]))) }

def heldOutText : String := "No run is evaluated on a dataset it was trained on."

/-- `∀ r d, evaluatedOn r d → ¬ trainedOn r d` -/
def heldOutClaim : SemanticClaim :=
  { params := [⟨"r", "Run"⟩, ⟨"d", "Dataset"⟩], assumptions := [P "evaluatedOn" [v "r", v "d"]],
    conclusion := .not (P "trainedOn" [v "r", v "d"]) }

def heldOutI : Interpretation := interp heldOutText heldOutClaim

/-- Mutation: polarity reversed in the conclusion. -/
def heldOutPolarityClaim : SemanticClaim :=
  { heldOutClaim with conclusion := P "trainedOn" [v "r", v "d"] }

/-! ## C. Computational biology (bounded, uninterpreted predicates) -/

def bioText : String := "Every binding residue sits at a valid index inside the annotated site."

/-- `∀ x, binding x → inSite (posOf x) ∧ validIndex (posOf x)` -/
def bioClaim : SemanticClaim :=
  { params := [], assumptions := [],
    conclusion := .quant .all "x" "Residue" (.imp (P "binding" [v "x"])
      (.and (P "inSite" [.app "posOf" [v "x"]]) (P "validIndex" [.app "posOf" [v "x"]]))) }

def bioI : Interpretation := interp bioText bioClaim

/-- Contrapositive with De Morgan. -/
def bioPosClaim : SemanticClaim :=
  { params := [], assumptions := [],
    conclusion := .quant .all "y" "Residue"
      (.imp (.or (.not (P "inSite" [.app "posOf" [v "y"]])) (.not (P "validIndex" [.app "posOf" [v "y"]])))
        (.not (P "binding" [v "y"]))) }

/-- Mutation: `∧` became `∨`. -/
def bioOrClaim : SemanticClaim :=
  { bioClaim with conclusion := .quant .all "x" "Residue" (.imp (P "binding" [v "x"])
      (.or (P "inSite" [.app "posOf" [v "x"]]) (P "validIndex" [.app "posOf" [v "x"]]))) }

/-- Mutation: a similarly named, registered but different predicate (`inSiteLegacy`). -/
def bioLegacyClaim : SemanticClaim :=
  { bioClaim with conclusion := .quant .all "x" "Residue" (.imp (P "binding" [v "x"])
      (.and (P "inSiteLegacy" [.app "posOf" [v "x"]]) (P "validIndex" [.app "posOf" [v "x"]]))) }

/-! ## Certificates (found by the untrusted search `findCert`, checked here by the kernel) -/

def revCert : EquivCert :=
  ⟨[⟨.concl, [], .quantSwap⟩, ⟨.concl, [0, 0], .impToOr⟩],
   [⟨.concl, [0, 0], .deMorganAnd⟩, ⟨.concl, [0, 0], .orComm⟩, ⟨.concl, [0, 0, 0, 0], .andComm⟩]⟩

def reproCert : EquivCert :=
  ⟨[], [⟨.concl, [], .quantSwap⟩, ⟨.concl, [0, 0, 1], .eqSymm⟩]⟩

def bioCert : EquivCert :=
  ⟨[⟨.concl, [0], .contrapose⟩], [⟨.concl, [0, 0], .deMorganAndInv⟩]⟩

theorem revCert_checks : checkCert revCert revClaim.normalize revPosClaim.normalize = true := by
  decide +kernel
theorem reproCert_checks :
    checkCert reproCert reproClaim.normalize reproPosClaim.normalize = true := by decide +kernel
theorem bioCert_checks : checkCert bioCert bioClaim.normalize bioPosClaim.normalize = true := by
  decide +kernel

/-! ## Positive requests: certified by v2, rejected by v1 -/

def revPosReq : RequestV2 := reqV2 revI (cand revPosClaim) (some revCert) noSearch
def reproPosReq : RequestV2 := reqV2 reproI (cand reproPosClaim) (some reproCert) noSearch
def bioPosReq : RequestV2 := reqV2 bioI (cand bioPosClaim) (some bioCert) noSearch

theorem rev_certified : (decideV2 authority revPosReq).outcome = .certifiedTranslation := by
  decide +kernel
theorem repro_certified : (decideV2 authority reproPosReq).outcome = .certifiedTranslation := by
  decide +kernel
theorem bio_certified : (decideV2 authority bioPosReq).outcome = .certifiedTranslation := by
  decide +kernel

theorem rev_v1_rejects : translationAccepts authority revPosReq.base = false := by decide +kernel
theorem repro_v1_rejects : translationAccepts authority reproPosReq.base = false := by decide +kernel
theorem bio_v1_rejects : translationAccepts authority bioPosReq.base = false := by decide +kernel

/-- The certified AI-safety candidate means the selected interpretation in every model. -/
theorem rev_preserves_denotation (M : Model) (ρ : String → M.Dom) :
    revClaim.denote M ρ ↔ revPosClaim.denote M ρ :=
  decideV2_certified_preserves_denotation rev_certified M ρ

/-! ## Adversarial requests: verified countermodels -/

def carriers (time action : List Nat) : List (SortId × List Nat) :=
  [("Time", time), ("Action", action), ("Run", [10]), ("Dataset", [11]), ("Digest", [12]),
   ("Residue", [13]), ("Pos", [14])]

def fixedFns : List (String × List (List Nat × Nat)) :=
  [("outputDigest", [([10], 12)]), ("posOf", [([13], 14)])]

/-- `∀ a` → `∃ a`: two actions, only one performed; the existential is satisfied by the other. -/
def revExistsModel : FinModel :=
  ⟨carriers [0] [1, 2], fixedFns,
   [("revoked", [[0]]), ("before", [[0, 0]]), ("performs", [[0, 1]]), ("forbidden", [[1]])]⟩

/-- Time reversed: a forbidden action strictly after revocation. -/
def revTimeModel : FinModel :=
  ⟨carriers [0, 1] [2], fixedFns,
   [("revoked", [[0]]), ("before", [[0, 1]]), ("performs", [[1, 2]]), ("forbidden", [[2]])]⟩

/-- Dropped assumption: no revocation, a forbidden action is performed. -/
def revDroppedModel : FinModel :=
  ⟨carriers [0] [1], fixedFns,
   [("revoked", []), ("before", [[0, 0]]), ("performs", [[0, 1]]), ("forbidden", [[1]])]⟩

/-- `∧` → `∨`: an action not preceded by revocation. -/
def revOrModel : FinModel :=
  ⟨carriers [0] [1], fixedFns,
   [("revoked", [[0]]), ("before", []), ("performs", [[0, 1]]), ("forbidden", [[1]])]⟩

/-- Negation dropped. -/
def revNegModel : FinModel :=
  ⟨carriers [0] [1], fixedFns,
   [("revoked", [[0]]), ("before", [[0, 0]]), ("performs", [[0, 1]]), ("forbidden", [])]⟩

/-- Converse: one run, digests trivially equal, configuration not "same". -/
def reproConverseModel : FinModel := ⟨carriers [0] [1], fixedFns, [("sameConfig", [])]⟩

/-- Polarity reversed. -/
def heldOutModel : FinModel :=
  ⟨carriers [0] [1], fixedFns, [("evaluatedOn", [[10, 11]]), ("trainedOn", [])]⟩

/-- `∧` → `∨` (biology). -/
def bioOrModel : FinModel :=
  ⟨carriers [0] [1], fixedFns, [("binding", [[13]]), ("inSite", []), ("validIndex", [[14]])]⟩

/-- Similarly named predicate substituted. -/
def bioLegacyModel : FinModel :=
  ⟨carriers [0] [1], fixedFns,
   [("binding", [[13]]), ("inSite", []), ("inSiteLegacy", [[14]]), ("validIndex", [[14]])]⟩

theorem revExists_countermodel :
    checkCountermodel registry revClaim revExistsClaim (mkWitness revClaim revExistsClaim revExistsModel)
      = true := by decide +kernel
theorem revTime_countermodel :
    checkCountermodel registry revClaim revTimeReversedClaim
      (mkWitness revClaim revTimeReversedClaim revTimeModel) = true := by decide +kernel
theorem revDropped_countermodel :
    checkCountermodel registry revClaim revDroppedClaim
      (mkWitness revClaim revDroppedClaim revDroppedModel) = true := by decide +kernel
theorem revOr_countermodel :
    checkCountermodel registry revClaim revOrClaim (mkWitness revClaim revOrClaim revOrModel)
      = true := by decide +kernel
theorem revNeg_countermodel :
    checkCountermodel registry revClaim revNegDroppedClaim
      (mkWitness revClaim revNegDroppedClaim revNegModel) = true := by decide +kernel
theorem reproConverse_countermodel :
    checkCountermodel registry reproClaim reproConverseClaim
      (mkWitness reproClaim reproConverseClaim reproConverseModel) = true := by decide +kernel
theorem heldOut_countermodel :
    checkCountermodel registry heldOutClaim heldOutPolarityClaim
      (mkWitness heldOutClaim heldOutPolarityClaim heldOutModel) = true := by decide +kernel
theorem bioOr_countermodel :
    checkCountermodel registry bioClaim bioOrClaim (mkWitness bioClaim bioOrClaim bioOrModel)
      = true := by decide +kernel
theorem bioLegacy_countermodel :
    checkCountermodel registry bioClaim bioLegacyClaim
      (mkWitness bioClaim bioLegacyClaim bioLegacyModel) = true := by decide +kernel

/-- A countermodel for a request's (interpretation, candidate) pair rules out certification
    for **every** supplied certificate and every search bound, and makes v1 reject. -/
theorem never_certified_of_countermodel {I : Interpretation} {C : Candidate} {w : Countermodel}
    (hw : checkCountermodel registry I.selected C.claim w = true)
    (cert : Option EquivCert) (b : SearchBounds) :
    (decideV2 authority (reqV2 I C cert b)).outcome ≠ .certifiedTranslation ∧
    translationAccepts authority (request I C) = false := by
  refine ⟨fun h => ?_, countermodel_v1_rejected (A := authority) hw⟩
  exact countermodel_refutes_contract_v2 (A := authority) (req := request I C) hw _
    (decideV2_certified_sound h)

theorem revExists_never_certified (cert : Option EquivCert) (b : SearchBounds) :
    (decideV2 authority (reqV2 revI (cand revExistsClaim 999) cert b)).outcome ≠
      .certifiedTranslation :=
  (never_certified_of_countermodel revExists_countermodel cert b).1

theorem revTime_never_certified (cert : Option EquivCert) (b : SearchBounds) :
    (decideV2 authority (reqV2 revI (cand revTimeReversedClaim) cert b)).outcome ≠
      .certifiedTranslation :=
  (never_certified_of_countermodel revTime_countermodel cert b).1

/-- **Forged certificate**: the valid certificate of the positive fixture, attached to the
    time-reversed candidate, does not check. -/
theorem forged_certificate_rejected :
    checkCert revCert revClaim.normalize revTimeReversedClaim.normalize = false := by decide +kernel

/-! ## Gate fixtures -/

/-- Unresolved ambiguity ⇒ `NEEDS_HUMAN_CLARIFICATION`. -/
def ambiguousReq : RequestV2 :=
  reqV2 (interp revText revClaim
    [⟨"after", .temporal, "Does 'after' mean strictly later?", none⟩]) (cand revPosClaim)
    (some revCert) noSearch

theorem ambiguous_needs_clarification :
    (decideV2 authority ambiguousReq).outcome = .needsHumanClarification := by decide +kernel

/-- Forged confirmation (not from the authorized process) ⇒ `INVALID_PROPOSAL`. -/
def forgedReceipt : ConfirmationReceipt :=
  ⟨revI.sourceText, revI.selected, revI.ambiguities, "model:self-confirmed", "trust-me"⟩

def forgedConfirmationReq : RequestV2 :=
  ⟨{ request revI (cand revPosClaim) with confirmation := some forgedReceipt }, some revCert, noSearch⟩

theorem forged_confirmation_invalid :
    (decideV2 authority forgedConfirmationReq).outcome = .invalidProposal := by decide +kernel

/-- A certified meaning but no proof receipt ⇒ `UNRESOLVED_PROOF_OBLIGATION`. -/
def missingProofReq : RequestV2 :=
  ⟨{ request revI (cand revPosClaim) with proof := none }, some revCert, noSearch⟩

theorem missing_proof_unresolved :
    (decideV2 authority missingProofReq).outcome = .unresolvedProofObligation := by decide +kernel

/-- An unsupported construct ⇒ `UNSUPPORTED_FRAGMENT`. -/
def unsupportedReq : RequestV2 :=
  reqV2 revI (cand { revClaim with conclusion := .unsupported "probably(forbidden)" }) none noSearch

theorem unsupported_fragment :
    (decideV2 authority unsupportedReq).outcome = .unsupportedFragment := by decide +kernel

end PCS.V2.Semantic.FixturesV2
