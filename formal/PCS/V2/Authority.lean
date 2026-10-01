import PCS.V2.Archive
import PCS.V2.Chemistry
import PCS.V2.TCB

/-!
# Lean-authoritative production acceptance

Production supplies a canonical observation transcript containing only results of
external stages that Lean intentionally models as oracles: static environment
capture, static workflow replay, and non-Lean replay observations. The transcript
is bound to the verified certificate semantic hash and checker version.

Lean still reconstructs and verifies the package, certificate, artifact table,
signatures, hashes, normalized decisions, and normalized set itself. The
`reaction_balance` check ignores the transcript result and is independently
replayed by the proved Lean chemistry executor.

`gatedProduction_refinesLean` captures the architectural point: once production
acceptance is the conjunction of a precheck and Lean acceptance,
`ProductionRefinesLean` follows without a Python-semantics refinement proof.
-/

namespace PCS.V2.Authority

open PCS PCS.Decision PCS.V2.Json PCS.V2.Hex PCS.V2.Canonical PCS.V2.Common
open PCS.V2.Package PCS.V2.Replay PCS.V2.CertificateModel PCS.V2.EndToEnd
open PCS.V2.Archive PCS.V2.TCB

def authorityTranscriptFormat : String := "pcs-lean-authority-observations-v1"
def maxAuthorityTranscriptBytes : Nat := 16 * 1024 * 1024

structure ReplayObservation where
  evidenceId : String
  kind : EvidenceKind
  outcome : Outcome
  deriving DecidableEq

structure AuthorityTranscript where
  certificateSemanticHash : List UInt8
  checkerVersion : String
  workflowOk : Bool
  environmentCapture : JVal
  replay : List ReplayObservation

def decodeReplayObservation (v : JVal) : Option ReplayObservation := do
  let ms ← objOf v
  let evidenceId ← strField ms "evidence_id"
  let kind ← (strField ms "kind").bind (decodeEnum allEvidenceKinds evidenceKindName)
  let outcome ← (strField ms "outcome").bind (decodeEnum allOutcomes outcomeName)
  if isSafeId evidenceId = true then
    pure { evidenceId, kind, outcome }
  else none

def decodeAuthorityTranscript (v : JVal) : Option AuthorityTranscript := do
  let ms ← objOf v
  let fmt ← strField ms "format"
  let certificateSemanticHash ← digestField ms "certificate_semantic_hash"
  let checkerVersion ← strField ms "checker_version"
  let workflowOk ← PCS.V2.Replay.boolField ms "workflow_ok"
  let environmentCapture ← field ms "environment_capture"
  let replayVals ← (field ms "replay").bind arrOf
  let replay ← mapOpt decodeReplayObservation replayVals
  if fmt = authorityTranscriptFormat ∧ isCheckerVersion checkerVersion = true ∧
      (replay.map (·.evidenceId)).Nodup then
    pure { certificateSemanticHash, checkerVersion, workflowOk, environmentCapture, replay }
  else none

def decodeAuthorityTranscriptBytes (raw : ByteArray) : Option AuthorityTranscript := do
  let v ← parseCanonicalBytes maxAuthorityTranscriptBytes raw
  decodeAuthorityTranscript v

def transcriptExecutor (t : AuthorityTranscript) : Executor := fun req =>
  match decodeCertEvidence req.evidence with
  | none => ⟨.provenance, .unverified⟩
  | some evidence =>
    match t.replay.find? (·.evidenceId == evidence.id) with
    | none => ⟨.provenance, .unverified⟩
    | some obs => ⟨obs.kind, obs.outcome⟩

/-- ASCII-compatible portability operations used by the production Lean authority.
    This matches the existing v0.6 golden/differential corpus. Full Unicode NFC and
    case-fold table correspondence remains an explicit portability boundary. -/
def authorityUnicode : UnicodeOps :=
  { nfc := id, casefold := fun s => String.map Char.toLower s }

def transcriptOracles (t : AuthorityTranscript) : Oracles :=
  { unicode := authorityUnicode,
    ed25519 := PCS.V2.Ed25519.verify,
    capture := fun _ => t.environmentCapture,
    workflow := fun _ _ => t.workflowOk,
    exec := PCS.V2.Chemistry.chemExecWith (transcriptExecutor t) }

def transcriptCovers (t : AuthorityTranscript) (r : AcceptedResult) : Bool :=
  t.certificateSemanticHash == r.pkg.cert.semanticHash &&
  t.checkerVersion == r.model.checkerVersion &&
  decide (t.replay.map (·.evidenceId) = r.model.evidence.map (·.id))

def acceptPCSWithTranscript (t : AuthorityTranscript) (T : TrustAnchor)
    (inp : PackageInput) : Option AcceptedResult :=
  match acceptPCS (transcriptOracles t) T inp with
  | none => none
  | some r => if transcriptCovers t r then some r else none

theorem acceptPCSWithTranscript_implies_acceptPCS {t : AuthorityTranscript} {T : TrustAnchor}
    {inp : PackageInput} {r : AcceptedResult}
    (h : acceptPCSWithTranscript t T inp = some r) :
    acceptPCS (transcriptOracles t) T inp = some r := by
  unfold acceptPCSWithTranscript at h
  split at h
  · cases h
  · rename_i r' hr
    split at h
    · cases h
      exact hr
    · cases h

def gatedProduction (precheck : ByteArray → Bool) (O : Oracles) (zip : ZipDecoder)
    (T : TrustAnchor) (raw : ByteArray) : Bool :=
  precheck raw && (acceptArchive O zip T raw).isSome

theorem gatedProduction_refinesLean (precheck : ByteArray → Bool) (O : Oracles)
    (zip : ZipDecoder) (T : TrustAnchor) :
    ProductionRefinesLean (gatedProduction precheck O zip T) O zip T := by
  intro raw h
  unfold gatedProduction at h
  have hh : precheck raw = true ∧ (acceptArchive O zip T raw).isSome = true := by
    simpa only [Bool.and_eq_true] using h
  exact hh.2

end PCS.V2.Authority
