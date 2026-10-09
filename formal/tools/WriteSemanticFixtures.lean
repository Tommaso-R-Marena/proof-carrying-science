import PCS.V2.TranslationFixtures
import PCS.V2.TranslationJson
import PCS.V2.Ed25519Sign

/-! Writes the signed JSON fixtures of PCS Semantic Translation Contract v1 for the
    `pcs-semantic-check` binary, derived from the kernel-checked fixtures of
    `PCS.V2.TranslationFixtures`.

    Usage (from the project root): `lake env lean --run tools/WriteSemanticFixtures.lean`

    The stand-in fixture receipts are replaced by real Ed25519 signatures:
    * a receipt that the stand-in verifier accepts is re-signed with the authorized key of
      its role (confirmation / elaboration / proof);
    * every other (forged) receipt is re-signed with an **attacker** key that is a valid
      Ed25519 key but not authorized, so the binary must reject it on key authorization.

    The seeds below are PUBLIC TEST SEEDS for fixtures only; never use them for anything else. -/

open PCS.V2.Semantic PCS.V2.Semantic.Fixtures PCS.V2.Json

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

def signConfirmation (r : ConfirmationReceipt) : ConfirmationReceipt :=
  let seed := if genuine r.authority r.signature then confSeed else attackerSeed
  { r with authority := pkOf seed, signature := sigOf seed (confirmationMessage r) }

def signElaboration (r : ElaborationReceipt) : ElaborationReceipt :=
  let seed := if genuine r.authority r.signature then elabSeed else attackerSeed
  { r with authority := pkOf seed, signature := sigOf seed (elaborationMessage r) }

def signProof (r : ProofReceipt) : ProofReceipt :=
  let seed := if genuine r.authority r.signature then proofSeed else attackerSeed
  { r with authority := pkOf seed, signature := sigOf seed (proofMessage r) }

def signRequest (req : Request) : Request :=
  { req with confirmation := req.confirmation.map signConfirmation,
             elaboration := req.elaboration.map signElaboration,
             proof := req.proof.map signProof }

def configOf (A : Authority) : AuthorityConfig :=
  { registry := A.registry, requireElaboration := A.requireElaboration,
    requireProof := A.requireProof, allowedAxioms := A.allowedAxioms,
    confirmationKeys := [pkOf confSeed], elaborationKeys := [pkOf elabSeed],
    proofKeys := [pkOf proofSeed] }

/-- name, authority file, request, expected verdict, failure codes that must be present -/
def fixtures : List (String × String × Request × Verdict × List FailureCode) :=
  [ ("pos_safety", "authority.json", safetyReq, .accepted, []),
    ("pos_liveness", "authority.json", livenessReq, .accepted, []),
    ("pos_arith", "authority.json", arithReq, .accepted, []),
    ("pos_unbounded_ne_normalization", "authority.json", unboundedReq, .accepted, []),
    ("neg_forall_to_exists", "authority.json", qAllToEx, .rejected, [.quantifierMismatch]),
    ("neg_exists_to_forall", "authority.json", qExToAll, .rejected, [.quantifierMismatch]),
    ("neg_quantifier_order", "authority.json", qOrder, .rejected, [.quantifierMismatch]),
    ("neg_negation_dropped", "authority.json", negDropped, .rejected, [.negationMismatch, .polarityMismatch]),
    ("neg_negation_inserted", "authority.json", negInserted, .rejected, [.negationMismatch]),
    ("neg_implication_reversed", "authority.json", impReversed, .rejected, [.polarityMismatch]),
    ("neg_assumption_dropped", "authority.json", asmDropped, .rejected, [.assumptionDropped]),
    ("neg_assumption_added", "authority.json", asmAdded, .rejected, [.assumptionAdded]),
    ("neg_assumption_weakened", "authority.json", asmWeakened, .rejected,
      [.assumptionDropped, .assumptionAdded]),
    ("neg_free_variable", "authority.json", freeVar, .rejected, [.unexpectedFreeVariable]),
    ("neg_variable_rebound", "authority.json", rebound, .rejected, [.bindingMismatch]),
    ("neg_variable_capture", "authority.json", capture, .rejected, [.bindingMismatch, .binderShadowing]),
    ("neg_and_to_or", "authority.json", andToOr, .rejected, [.connectiveMismatch]),
    ("neg_unknown_definition", "authority.json", unknownDef, .rejected,
      [.unresolvedSymbol, .unknownDefinition]),
    ("neg_similar_name_substituted", "authority.json", similarName, .rejected, [.semanticMismatch]),
    ("neg_wrong_symbol_identity", "authority.json", wrongIdentity, .rejected, [.incorrectSymbolIdentity]),
    ("neg_shadowed_grounding", "authority.json", shadowGrounding, .rejected,
      [.duplicateOrShadowedGrounding]),
    ("neg_binder_shadows_symbol", "authority.json", binderShadow, .rejected, [.binderShadowing]),
    ("neg_duplicate_registry_entry", "authority_duplicate_registry.json", safetyReq, .rejected,
      [.registryMalformed]),
    ("neg_unresolved_ambiguity", "authority.json", ambiguousReq, .needsClarification,
      [.ambiguousScope]),
    ("neg_forged_confirmation", "authority.json", forgedConfirmation, .rejected,
      [.confirmationNotVerified]),
    ("neg_misbound_confirmation", "authority.json", misboundConfirmation, .rejected,
      [.confirmationNotVerified]),
    ("neg_model_asserted_confirmation_only", "authority.json", modelOnlyConfirmation,
      .needsClarification, [.confirmationMissing]),
    ("neg_forged_elaboration_receipt", "authority.json", forgedElaboration, .rejected,
      [.elaborationNotVerified]),
    ("neg_stale_elaboration_receipt", "authority.json", staleElaboration, .rejected,
      [.elaborationNotVerified]),
    ("neg_forged_proof_receipt", "authority.json", forgedProof, .rejected, [.proofNotVerified]),
    ("neg_sorry_proof_receipt", "authority.json", sorryProof, .rejected, [.proofNotVerified]),
    ("neg_lean_source_mismatch", "authority.json", sourceMismatch, .rejected, [.leanRenderingMismatch]),
    ("neg_roundtrip_explanation_mismatch", "authority.json", explanationMismatch, .rejected,
      [.roundtripMismatch]),
    ("neg_unsupported_construct", "authority.json", unsupportedReq, .rejected, [.unsupportedConstruct]),
    ("neg_ill_typed_candidate", "authority.json", illTypedReq, .rejected, [.illTyped]),
    ("neg_high_confidence_failing", "authority.json", highConfidence, .rejected,
      [.negationMismatch]) ]

def canonicalStr (v : JVal) : String := String.ofList (ser v)

def main : IO Unit := do
  let dir : System.FilePath := "fixtures/semantic_translation_v1"
  IO.FS.createDirAll (dir / "requests")
  let cfg := configOf authority
  IO.FS.writeFile (dir / "authority.json") (canonicalStr (encAuthorityConfig cfg))
  IO.FS.writeFile (dir / "authority_duplicate_registry.json")
    (canonicalStr (encAuthorityConfig (configOf dupAuthority)))
  IO.FS.writeFile (dir / "claim_safety.json") (canonicalStr (encClaim safetyCandClaim))
  let mut entries : List JVal := []
  for (name, auth, req, verdict, codes) in fixtures do
    let signed := signRequest req
    IO.FS.writeFile (dir / "requests" / (name ++ ".json")) (canonicalStr (encRequest signed))
    -- consistency check against the pure front end (same function the binary runs)
    let aRaw := (canonicalStr (encAuthorityConfig (if auth == "authority.json" then cfg
      else configOf dupAuthority))).toUTF8
    let res := semanticCheck aRaw (canonicalStr (encRequest signed)).toUTF8
    if res.decision.verdict != verdict then
      throw (IO.userError s!"fixture {name}: expected {verdict.name}, got {res.decision.verdict.name}")
    entries := entries ++ [.obj [("authority", .str auth), ("codes", encStrs (codes.map (·.name))),
      ("name", .str name), ("request", .str ("requests/" ++ name ++ ".json")),
      ("verdict", .str verdict.name)]]
    IO.println s!"wrote {name}: {verdict.name}"
  IO.FS.writeFile (dir / "expected.json")
    (canonicalStr (.obj [("fixtures", .arr entries), ("schema", .str "pcs-semantic-fixtures-v1")]))
