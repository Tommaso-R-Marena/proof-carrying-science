import PCS.V2.Common

/-!
# PCS v0.6 normalized decision wire `pcs-normalized-decision-v2`

Typed representation, exact JSON encoding, structural decoder, the JSON-Schema
field checks of `schemas/normalized_decision_v06.schema.json`, the semantic checks
of `pcs/normalized_wire_v06.py::validate_normalized_wire_v06`, and the Lean
byte-level checker `verifyWireBytes` mirroring
`parse_normalized_wire_bytes_v06(raw)`.

The refinement map `toV1` sends an accepted v2 wire into the existing v1 typed
`PCS.Wire.DecisionWire`, so the already machine-checked chain
`wireCheck_sound → WellFormed → wire_*_sound → Assures` is reused unchanged.
-/

namespace PCS.V2.NormalizedWire

open PCS PCS.Decision PCS.V2.Json PCS.V2.Hex PCS.V2.Domains PCS.V2.Canonical PCS.V2.Common

def wireFormat : String := "pcs-normalized-decision-v2"
def jcsProfile : String := "pcs-jcs-rfc8785-v1"
def specVersion : String := "pcs-0.6"
def maxWireBytes : Nat := 10 * 1024 * 1024
def maxStatementChars : Nat := 16384

structure SourceV2 where
  checkerVersion : String
  certificateSemanticHash : List UInt8
  certificateIntegrityHash : List UInt8
  claimId : String
  deriving DecidableEq, Repr

structure AssumptionV2 where
  id : String
  statement : String
  deriving DecidableEq, Repr

structure ClaimV2 where
  id : String
  kind : ClaimKind
  predicateCommitment : List UInt8
  requiredEvidence : List String
  assumptions : List String
  deriving DecidableEq, Repr

structure EvidenceV2 where
  id : String
  kind : EvidenceKind
  outcome : Outcome
  predicateCommitment : List UInt8
  deriving DecidableEq, Repr

/-- A typed `pcs-normalized-decision-v2` object.  The constant fields
    (`wire_format`, `canonical_json_profile`, `wire_hash_format`,
    `predicate_hash_format`, `source.spec_version`) are fixed by the encoding. -/
structure WireV2 where
  source : SourceV2
  context : List AssumptionV2
  claim : ClaimV2
  evidence : List EvidenceV2
  decision : DecisionStatus
  wireSemanticHash : List UInt8
  deriving DecidableEq, Repr

/-! ## Exact JSON encoding (members in JCS key order) -/

def encodeSource (s : SourceV2) : JVal :=
  .obj [("certificate_integrity_hash", .str (hexEncode s.certificateIntegrityHash)),
        ("certificate_semantic_hash", .str (hexEncode s.certificateSemanticHash)),
        ("checker_version", .str s.checkerVersion),
        ("claim_id", .str s.claimId),
        ("spec_version", .str specVersion)]

def encodeAssumption (a : AssumptionV2) : JVal :=
  .obj [("id", .str a.id), ("statement", .str a.statement)]

def encodeClaim (c : ClaimV2) : JVal :=
  .obj [("assumptions", .arr (c.assumptions.map JVal.str)),
        ("id", .str c.id),
        ("kind", .str (claimKindName c.kind)),
        ("predicate_commitment", .str (commitmentStr c.predicateCommitment)),
        ("required_evidence", .arr (c.requiredEvidence.map JVal.str))]

def encodeEvidence (e : EvidenceV2) : JVal :=
  .obj [("id", .str e.id),
        ("kind", .str (evidenceKindName e.kind)),
        ("outcome", .str (outcomeName e.outcome)),
        ("predicate_commitment", .str (commitmentStr e.predicateCommitment))]

def coreMembers (w : WireV2) : List (String × JVal) :=
  [("canonical_json_profile", .str jcsProfile),
   ("claim", encodeClaim w.claim),
   ("context", .arr (w.context.map encodeAssumption)),
   ("decision", .str (decisionName w.decision)),
   ("evidence", .arr (w.evidence.map encodeEvidence)),
   ("predicate_hash_format", .str predicateCommitmentDomain),
   ("source", encodeSource w.source),
   ("wire_format", .str wireFormat),
   ("wire_hash_format", .str normalizedDecisionDomain)]

/-- `_wire_projection(wire)`: the wire without `wire_semantic_hash`. -/
def projection (w : WireV2) : JVal := .obj (coreMembers w)

def encodeWire (w : WireV2) : JVal :=
  .obj (coreMembers w ++ [("wire_semantic_hash", .str (hexEncode w.wireSemanticHash))])

/-- The exact canonical bytes of a typed wire. -/
def encodedBytes (w : WireV2) : ByteArray := jcsBytes (encodeWire w)

/-- `wire_semantic_hash_v06(wire)` as digest bytes. -/
def expectedHash (w : WireV2) : List UInt8 := domainDigest normalizedDecisionDomain (projection w)

/-! ## Structural decoder (types, exact key sets, constants, enums, hex) -/

def decodeSource : JVal → Option SourceV2
  | .obj [(k₁, .str ih), (k₂, .str sh), (k₃, .str cv), (k₄, .str cid), (k₅, .str sv)] =>
    if k₁ = "certificate_integrity_hash" ∧ k₂ = "certificate_semantic_hash" ∧
       k₃ = "checker_version" ∧ k₄ = "claim_id" ∧ k₅ = "spec_version" ∧ sv = specVersion then
      match hexDecode ih, hexDecode sh with
      | some ih', some sh' =>
        some { checkerVersion := cv, certificateSemanticHash := sh',
               certificateIntegrityHash := ih', claimId := cid }
      | _, _ => none
    else none
  | _ => none

def decodeAssumption : JVal → Option AssumptionV2
  | .obj [(k₁, .str i), (k₂, .str st)] =>
    if k₁ = "id" ∧ k₂ = "statement" then some { id := i, statement := st } else none
  | _ => none

def decodeClaim : JVal → Option ClaimV2
  | .obj [(k₁, as), (k₂, .str i), (k₃, .str kd), (k₄, .str pc), (k₅, re)] =>
    if k₁ = "assumptions" ∧ k₂ = "id" ∧ k₃ = "kind" ∧ k₄ = "predicate_commitment" ∧
       k₅ = "required_evidence" then
      match strArray as, decodeEnum allClaimKinds claimKindName kd, hexDecode' pc, strArray re with
      | some as', some kd', some pc', some re' =>
        some { id := i, kind := kd', predicateCommitment := pc', requiredEvidence := re',
               assumptions := as' }
      | _, _, _, _ => none
    else none
  | _ => none
where
  /-- prefix + lower-case hex (length is a schema check). -/
  hexDecode' (s : String) : Option (List UInt8) :=
    if s.toList.take predicatePrefix.length = predicatePrefix.toList then
      decodeChars (s.toList.drop predicatePrefix.length)
    else none

def decodeEvidence : JVal → Option EvidenceV2
  | .obj [(k₁, .str i), (k₂, .str kd), (k₃, .str oc), (k₄, .str pc)] =>
    if k₁ = "id" ∧ k₂ = "kind" ∧ k₃ = "outcome" ∧ k₄ = "predicate_commitment" then
      match decodeEnum allEvidenceKinds evidenceKindName kd,
            decodeEnum allOutcomes outcomeName oc, decodeClaim.hexDecode' pc with
      | some kd', some oc', some pc' =>
        some { id := i, kind := kd', outcome := oc', predicateCommitment := pc' }
      | _, _, _ => none
    else none
  | _ => none

def decodeStructure : JVal → Option WireV2
  | .obj [(k₁, .str prof), (k₂, cl), (k₃, .arr ctx), (k₄, .str dec), (k₅, .arr ev),
          (k₆, .str phf), (k₇, src), (k₈, .str wf), (k₉, .str whf), (k₁₀, .str wsh)] =>
    if k₁ = "canonical_json_profile" ∧ k₂ = "claim" ∧ k₃ = "context" ∧ k₄ = "decision" ∧
       k₅ = "evidence" ∧ k₆ = "predicate_hash_format" ∧ k₇ = "source" ∧ k₈ = "wire_format" ∧
       k₉ = "wire_hash_format" ∧ k₁₀ = "wire_semantic_hash" ∧
       prof = jcsProfile ∧ phf = predicateCommitmentDomain ∧ wf = wireFormat ∧
       whf = normalizedDecisionDomain then
      match decodeClaim cl, mapOpt decodeAssumption ctx,
            decodeEnum allDecisions decisionName dec, mapOpt decodeEvidence ev,
            decodeSource src, hexDecode wsh with
      | some cl', some ctx', some dec', some ev', some src', some wsh' =>
        some { source := src', context := ctx', claim := cl', evidence := ev',
               decision := dec', wireSemanticHash := wsh' }
      | _, _, _, _, _, _ => none
    else none
  | _ => none

/-! ## JSON-Schema field checks -/

def assumptionOK (a : AssumptionV2) : Bool :=
  isSafeId a.id && decide (1 ≤ a.statement.toList.length) &&
    decide (a.statement.toList.length ≤ maxStatementChars)

def evidenceOK (e : EvidenceV2) : Bool :=
  isSafeId e.id && e.predicateCommitment.length == 32

def schemaOK (w : WireV2) : Bool :=
  isCheckerVersion w.source.checkerVersion &&
  w.source.certificateSemanticHash.length == 32 &&
  w.source.certificateIntegrityHash.length == 32 &&
  isSafeId w.source.claimId &&
  decide (w.context.length ≤ maxItems) && w.context.all assumptionOK &&
  isSafeId w.claim.id && w.claim.predicateCommitment.length == 32 &&
  idArrayOK w.claim.requiredEvidence && idArrayOK w.claim.assumptions &&
  decide (w.evidence.length ≤ maxItems) && w.evidence.all evidenceOK &&
  w.wireSemanticHash.length == 32

def decodeWire (v : JVal) : Option WireV2 :=
  match decodeStructure v with
  | some w => if schemaOK w then some w else none
  | none => none

/-! ## Refinement into the existing v1 typed wire -/

def toV1Assumption (a : AssumptionV2) : PCS.Wire.WireAssumption :=
  { id := a.id, statement := a.statement }

def toV1Evidence (e : EvidenceV2) : PCS.Wire.WireEvidence :=
  { id := e.id, kind := e.kind, outcome := e.outcome,
    predicateCommitment := some (commitmentStr e.predicateCommitment) }

def toV1Claim (c : ClaimV2) : PCS.Wire.WireClaim :=
  { id := c.id, kind := c.kind, predicateCommitment := some (commitmentStr c.predicateCommitment),
    requiredEvidence := c.requiredEvidence, assumptions := c.assumptions }

/-- The refinement map v2 → v1. The full `pcs-predicate-sha256-v2:` commitment
    string becomes the v1 opaque predicate tag. -/
def toV1 (w : WireV2) : PCS.Wire.DecisionWire :=
  { version := .v1
    source := { certificateSemanticHash := hexEncode w.source.certificateSemanticHash,
                claimId := w.source.claimId }
    context := w.context.map toV1Assumption
    claim := toV1Claim w.claim
    evidence := w.evidence.map toV1Evidence
    recordedDecision := w.decision }

/-! ## Semantic checks (`validate_normalized_wire_v06`) -/

def hashOK (w : WireV2) : Bool := w.wireSemanticHash == expectedHash w

def contextIdsUnique (w : WireV2) : Bool := decide (w.context.map (·.id)).Nodup

def semanticOK (w : WireV2) : Bool :=
  hashOK w && PCS.WireCheck.wireCheck (toV1 w) && contextIdsUnique w

/-- The Lean checker for raw normalized-decision bytes
    (`parse_normalized_wire_bytes_v06`). -/
def verifyWireBytes (raw : ByteArray) : Option WireV2 :=
  match parseCanonicalBytes maxWireBytes raw with
  | none => none
  | some v =>
    match decodeWire v with
    | none => none
    | some w => if semanticOK w then some w else none

/-! ## Semantic projection -/

/-- The explicit assumption context Γ carried by the wire. -/
def gamma (w : WireV2) : List Assumption := PCS.Wire.decodedContext (toV1 w)
/-- The claim as seen by the logical kernel. -/
def kernelClaim (w : WireV2) : Claim := PCS.Wire.decodeClaim (toV1 w).claim
/-- The evidence as seen by the logical kernel. -/
def kernelEvidence (w : WireV2) : List Evidence := PCS.Wire.decodedEvidence (toV1 w)

/-- The assurance level an accepted decision status denotes (`none` for OPEN/FAILED). -/
def levelOf : DecisionStatus → Option AssuranceLevel
  | .formal => some .formal
  | .computational => some .computational
  | .empirical => some .empirical
  | .mixed => some .mixed
  | .open_ => none
  | .failed => none

end PCS.V2.NormalizedWire
