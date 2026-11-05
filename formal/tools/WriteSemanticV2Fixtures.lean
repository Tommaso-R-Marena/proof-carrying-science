import PCS.V2.SemanticV2Fixtures
import PCS.V2.SemanticFeedback
import PCS.V2.Ed25519Sign

/-! Writes the signed JSON fixtures of PCS Proof-Carrying Semantic Intelligence v2 for
    `pcs-semantic-check --v2` and `--check-countermodel`, derived from the kernel-checked
    fixtures of `PCS.V2.SemanticV2Fixtures`.

    Usage (from the project root): `lake env lean --run tools/WriteSemanticV2Fixtures.lean`

    Every request is re-signed with real Ed25519 signatures (authorized key of the right role
    for genuine receipts, an unauthorized attacker key otherwise, or a deliberately wrong role
    key for the role-confusion fixture) and every fixture is run through the pure front end
    `semanticCheckV2` (the same function the binary runs, including the untrusted searches);
    the writer aborts if an outcome differs from the expectation.  Countermodel bundles are
    re-checked with `checkCountermodelBundle`.

    The seeds below are PUBLIC TEST SEEDS for fixtures only; never use them for anything else. -/

open PCS.V2.Semantic PCS.V2.Semantic.FixturesV2 PCS.V2.Json

def seedOf (tag : String) : List UInt8 :=
  ((tag.toList.map (fun (c : Char) => c.toNat.toUInt8)) ++ List.replicate 32 0).take 32

def confSeed : List UInt8 := seedOf "pcs-test-confirmation-seed"
def elabSeed : List UInt8 := seedOf "pcs-test-elaboration-seed"
def proofSeed : List UInt8 := seedOf "pcs-test-proof-seed"
def attackerSeed : List UInt8 := seedOf "pcs-test-attacker-seed"

def pkOf (seed : List UInt8) : String :=
  PCS.V2.Base64.encodeStr (PCS.V2.Ed25519Sign.publicKey seed)

def sigOf (seed msg : List UInt8) : String :=
  PCS.V2.Base64.encodeStr (PCS.V2.Ed25519Sign.sign seed msg)

def genuine (authority signature : String) : Bool :=
  authority == fixtureAuthorityName && signature == fixtureToken

/-- `confRole` chooses the key used for a *genuine* confirmation receipt (normally the
    confirmation key; the role-confusion fixture uses the proof key instead). -/
def signConfirmation (confRole : List UInt8) (r : ConfirmationReceipt) : ConfirmationReceipt :=
  let seed := if genuine r.authority r.signature then confRole else attackerSeed
  { r with authority := pkOf seed, signature := sigOf seed (confirmationMessage r) }

def signElaboration (r : ElaborationReceipt) : ElaborationReceipt :=
  let seed := if genuine r.authority r.signature then elabSeed else attackerSeed
  { r with authority := pkOf seed, signature := sigOf seed (elaborationMessage r) }

def signProof (r : ProofReceipt) : ProofReceipt :=
  let seed := if genuine r.authority r.signature then proofSeed else attackerSeed
  { r with authority := pkOf seed, signature := sigOf seed (proofMessage r) }

def signRequestWith (confRole : List UInt8) (r : RequestV2) : RequestV2 :=
  { r with base := { r.base with
      confirmation := r.base.confirmation.map (signConfirmation confRole),
      elaboration := r.base.elaboration.map signElaboration,
      proof := r.base.proof.map signProof } }

def signRequest (r : RequestV2) : RequestV2 := signRequestWith confSeed r

def config : AuthorityConfig :=
  { registry := authority.registry, requireElaboration := authority.requireElaboration,
    requireProof := authority.requireProof, allowedAxioms := authority.allowedAxioms,
    confirmationKeys := [pkOf confSeed], elaborationKeys := [pkOf elabSeed],
    proofKeys := [pkOf proofSeed] }

def dflt : SearchBounds := SearchBounds.default

/-! ## Additional adversarial requests (beyond the kernel-checked ones) -/

/-- The valid confirmation of the *safety* interpretation attached to a request about the
    reproducibility interpretation (valid signature, wrong claim). -/
def misboundConfirmationReq : RequestV2 :=
  ⟨{ request reproI (cand reproPosClaim) with confirmation := some (confirm revI) },
    some reproCert, noSearch⟩

/-- The safety conclusion with the final predicate application replaced. -/
def revConclWith (last : Formula) (freeJ : Bool := false) : Formula :=
  let body := Formula.imp (.and (P "before" [v "i", v "j"]) (P "performs" [v "j", v "a"]))
    (.not last)
  if freeJ then .quant .all "a" "Action" body
  else .quant .all "j" "Time" (.quant .all "a" "Action" body)

def revWith (last : Formula) (freeJ : Bool := false) : SemanticClaim :=
  { revClaim with conclusion := revConclWith last freeJ }

/-- A symbol that is not in the approved registry (hallucinated definition). -/
def unknownSymbolReq : RequestV2 :=
  reqV2 revI (cand (revWith (P "forbiddenAction" [v "a"]))) none dflt

/-- Wrong arity for a registered predicate. -/
def wrongArityReq : RequestV2 :=
  reqV2 revI (cand (revWith (P "forbidden" [v "a", v "a"]))) none dflt

/-- Wrong sort: a `Time` variable where `forbidden` expects an `Action`. -/
def wrongSortReq : RequestV2 :=
  reqV2 revI (cand (revWith (P "forbidden" [v "j"]))) none dflt

/-- A free variable in the candidate (the binder of `j` is dropped). -/
def freeVarReq : RequestV2 :=
  reqV2 revI (cand (revWith (P "forbidden" [v "a"]) true)) none dflt

/-- name, request, signing key for genuine confirmations, expected outcome, required codes -/
def fixtures : List (String × RequestV2 × List UInt8 × OutcomeV2 × List FailureCode) :=
  [ -- certified (proposer-supplied certificates; v1 rejects these)
    ("pos_ai_safety_supplied_certificate", revPosReq, confSeed, .certifiedTranslation, []),
    ("pos_repro_supplied_certificate", reproPosReq, confSeed, .certifiedTranslation, []),
    ("pos_bio_supplied_certificate", bioPosReq, confSeed, .certifiedTranslation, []),
    -- certified by the untrusted bounded search, re-checked by the certificate checker
    ("pos_repro_search_certificate", reqV2 reproI (cand reproPosClaim) none dflt, confSeed,
      .certifiedTranslation, []),
    ("pos_bio_search_certificate", reqV2 bioI (cand bioPosClaim) none dflt, confSeed,
      .certifiedTranslation, []),
    -- certified by identical canonical normal form (v1 path)
    ("pos_ai_safety_identical", reqV2 revI (cand revClaim) none dflt, confSeed,
      .certifiedTranslation, []),
    -- verified counterexamples (search finds a countermodel; re-checked)
    ("neg_forall_to_exists", reqV2 revI (cand revExistsClaim) none dflt, confSeed,
      .verifiedCounterexample, [.semanticMismatch]),
    ("neg_high_confidence_forall_to_exists", reqV2 revI (cand revExistsClaim 999) none dflt,
      confSeed, .verifiedCounterexample, [.semanticMismatch]),
    ("neg_time_order_reversed", reqV2 revI (cand revTimeReversedClaim) none dflt, confSeed,
      .verifiedCounterexample, [.semanticMismatch]),
    ("neg_assumption_dropped", reqV2 revI (cand revDroppedClaim) none dflt, confSeed,
      .verifiedCounterexample, [.semanticMismatch]),
    ("neg_and_to_or", reqV2 revI (cand revOrClaim) none dflt, confSeed,
      .verifiedCounterexample, [.semanticMismatch]),
    ("neg_negation_dropped", reqV2 revI (cand revNegDroppedClaim) none dflt, confSeed,
      .verifiedCounterexample, [.semanticMismatch]),
    ("neg_repro_converse", reqV2 reproI (cand reproConverseClaim) none dflt, confSeed,
      .verifiedCounterexample, [.semanticMismatch]),
    ("neg_heldout_polarity", reqV2 heldOutI (cand heldOutPolarityClaim) none dflt, confSeed,
      .verifiedCounterexample, [.semanticMismatch]),
    ("neg_bio_and_to_or", reqV2 bioI (cand bioOrClaim) none dflt, confSeed,
      .verifiedCounterexample, [.semanticMismatch]),
    ("neg_bio_similar_name_substituted", reqV2 bioI (cand bioLegacyClaim) none dflt, confSeed,
      .verifiedCounterexample, [.semanticMismatch]),
    ("neg_forged_certificate", reqV2 revI (cand revTimeReversedClaim) (some revCert) dflt,
      confSeed, .verifiedCounterexample, [.semanticMismatch]),
    -- bounded search: nothing established (NOT an equivalence proof)
    ("unresolved_search_disabled", reqV2 revI (cand revPosClaim) none noSearch, confSeed,
      .searchExhausted, [.semanticMismatch]),
    -- gates
    ("neg_unresolved_ambiguity", ambiguousReq, confSeed, .needsHumanClarification, [.unresolvedAmbiguity]),
    ("neg_forged_confirmation", forgedConfirmationReq, confSeed, .invalidProposal,
      [.confirmationNotVerified]),
    ("neg_confirmation_wrong_role_key", revPosReq, proofSeed, .invalidProposal,
      [.confirmationNotVerified]),
    ("neg_confirmation_bound_to_other_claim", misboundConfirmationReq, confSeed, .invalidProposal,
      [.confirmationNotVerified]),
    ("neg_missing_proof_receipt", missingProofReq, confSeed, .unresolvedProofObligation,
      [.proofNotVerified]),
    ("neg_unsupported_construct", unsupportedReq, confSeed, .unsupportedFragment,
      [.unsupportedConstruct]),
    ("neg_unknown_symbol", unknownSymbolReq, confSeed, .invalidProposal, [.unresolvedSymbol]),
    ("neg_wrong_arity", wrongArityReq, confSeed, .invalidProposal, [.illTyped]),
    ("neg_wrong_sort", wrongSortReq, confSeed, .invalidProposal, [.illTyped]),
    ("neg_free_variable", freeVarReq, confSeed, .invalidProposal, [.unexpectedFreeVariable]) ]

/-- Truth values recorded for one structure, then the structure edited. -/
def editedWitness : Countermodel :=
  let w := mkWitness revClaim revExistsClaim revExistsModel
  { w with model := { revExistsModel with preds := [] } }

/-- A function table leaving its declared result sort. -/
def badFnModel : FinModel :=
  { revExistsModel with fns := [("outputDigest", [([10], 99)]), ("posOf", [([13], 14)])] }

/-- An approved sort with an empty carrier. -/
def emptySortModel : FinModel :=
  { revExistsModel with
    sorts := revExistsModel.sorts.map (fun e => if e.1 == "Dataset" then (e.1, []) else e) }

/-- Countermodel bundles: name, interpretation, candidate, model, expected validity. -/
def bundles : List (String × SemanticClaim × SemanticClaim × Countermodel × Bool) :=
  [ ("cm_forall_to_exists", revClaim, revExistsClaim, mkWitness revClaim revExistsClaim revExistsModel, true),
    ("cm_time_order_reversed", revClaim, revTimeReversedClaim,
      mkWitness revClaim revTimeReversedClaim revTimeModel, true),
    ("cm_assumption_dropped", revClaim, revDroppedClaim, mkWitness revClaim revDroppedClaim revDroppedModel, true),
    ("cm_and_to_or", revClaim, revOrClaim, mkWitness revClaim revOrClaim revOrModel, true),
    ("cm_negation_dropped", revClaim, revNegDroppedClaim, mkWitness revClaim revNegDroppedClaim revNegModel, true),
    ("cm_repro_converse", reproClaim, reproConverseClaim,
      mkWitness reproClaim reproConverseClaim reproConverseModel, true),
    ("cm_heldout_polarity", heldOutClaim, heldOutPolarityClaim,
      mkWitness heldOutClaim heldOutPolarityClaim heldOutModel, true),
    ("cm_bio_and_to_or", bioClaim, bioOrClaim, mkWitness bioClaim bioOrClaim bioOrModel, true),
    ("cm_bio_similar_name", bioClaim, bioLegacyClaim, mkWitness bioClaim bioLegacyClaim bioLegacyModel, true),
    -- adversarial: recorded truth values flipped / model reused for an equivalent pair
    ("cm_invalid_flipped_values", revClaim, revExistsClaim,
      let w := mkWitness revClaim revExistsClaim revExistsModel
      { w with interpretationHolds := w.candidateHolds, candidateHolds := w.interpretationHolds }, false),
    ("cm_invalid_equivalent_pair", revClaim, revPosClaim,
      mkWitness revClaim revPosClaim revExistsModel, false),
    ("cm_invalid_model_edited_after_evaluation", revClaim, revExistsClaim, editedWitness, false),
    ("cm_invalid_nonconforming_function", revClaim, revExistsClaim,
      mkWitness revClaim revExistsClaim badFnModel, false),
    ("cm_invalid_empty_sort", revClaim, revExistsClaim,
      mkWitness revClaim revExistsClaim emptySortModel, false) ]

def canonicalStr (v : JVal) : String := String.ofList (ser v)

def main : IO Unit := do
  let dir : System.FilePath := "fixtures/semantic_intelligence_v2"
  IO.FS.createDirAll (dir / "requests")
  IO.FS.createDirAll (dir / "countermodels")
  let aStr := canonicalStr (encAuthorityConfig config)
  IO.FS.writeFile (dir / "authority.json") aStr
  let mut entries : List JVal := []
  for (name, req, role, outcome, codes) in fixtures do
    let signed := signRequestWith role req
    let rStr := canonicalStr (encRequestV2 signed)
    IO.FS.writeFile (dir / "requests" / (name ++ ".json")) rStr
    let res := semanticCheckV2 aStr.toUTF8 rStr.toUTF8
    if res.decision.outcome != outcome then
      throw (IO.userError s!"fixture {name}: expected {outcome.name}, got {res.decision.outcome.name}")
    let got := res.decision.diagnostics.map (·.code)
    for c in codes do
      if !(got.contains c) then
        throw (IO.userError s!"fixture {name}: missing code {c.name}; got {(got.map (·.name))}")
    entries := entries ++ [.obj [("codes", encStrs (codes.map (·.name))),
      ("label", .str (labelOf res.decision).name),
      ("name", .str name), ("outcome", .str outcome.name),
      ("request", .str ("requests/" ++ name ++ ".json")),
      ("semantic_status", .str res.decision.semantic.name)]]
    IO.println s!"wrote {name}: {outcome.name} [{res.decision.semantic.name}]"
  let mut bentries : List JVal := []
  for (name, i, c, w, valid) in bundles do
    let bStr := canonicalStr (encCountermodelBundle ⟨i, c, w⟩)
    IO.FS.writeFile (dir / "countermodels" / (name ++ ".json")) bStr
    if checkCountermodelBundle aStr.toUTF8 bStr.toUTF8 != some valid then
      throw (IO.userError s!"bundle {name}: expected validity {valid}")
    bentries := bentries ++ [.obj [("bundle", .str ("countermodels/" ++ name ++ ".json")),
      ("name", .str name), ("valid", .bool valid)]]
    IO.println s!"wrote {name}: valid={valid}"
  IO.FS.writeFile (dir / "expected.json")
    (canonicalStr (.obj [("countermodels", .arr bentries), ("fixtures", .arr entries),
      ("schema", .str "pcs-semantic-fixtures-v2")]))
