import PCS.V2.Archive
import PCS.V2.Chemistry
import PCS.V2.Checkers
import PCS.V2.Workflow
import PCS.V2.EnvFacts
import PCS.V2.TCB

/-!
# Lean-authoritative production acceptance

Production supplies a canonical observation transcript containing only results of
external stages that Lean intentionally models as oracles: static environment
capture, static workflow replay, and non-Lean replay observations. The transcript
is bound to the verified certificate semantic hash and checker version.

Lean still reconstructs and verifies the package, certificate, artifact table,
signatures, hashes, normalized decisions, and normalized set itself. The verified
built-in checks `reaction_balance`, `unit_compatible`, `csv_disjoint`, `pkpd_contract`,
`pkpd_reference_match`, and `pkpd_peak_concentration_threshold` ignore the
transcript result and are independently replayed by the proved Lean checkers
(`PCS.V2.Checkers.builtinExecWith`); unregistered evidence kinds are rejected; no producer-supplied transcript PASS
can substitute for a certified checker.

`gatedProduction_refinesLean` captures the architectural point: once production
acceptance is the conjunction of a precheck and Lean acceptance,
`ProductionRefinesLean` follows without a Python-semantics refinement proof.
-/

namespace PCS.V2.Authority

open PCS PCS.Decision PCS.V2.Json PCS.V2.Hex PCS.V2.Canonical PCS.V2.Common
open PCS.V2.Package PCS.V2.Replay PCS.V2.CertificateModel PCS.V2.EndToEnd
open PCS.V2.Index PCS.V2.Archive PCS.V2.TCB

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
  /-- normalized fresh static analysis of the committed workflow sources (the only
      workflow input not checked by Lean itself; see `PCS.V2.Workflow`) -/
  workflowAnalysis : List PCS.V2.Workflow.FreshSource := []

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
  let workflowAnalysis ← match field ms "workflow_analysis" with
    | none => some []
    | some v => (arrOf v).bind (mapOpt PCS.V2.Workflow.decodeFreshSource)
  if fmt = authorityTranscriptFormat ∧ isCheckerVersion checkerVersion = true ∧
      (replay.map (·.evidenceId)).Nodup ∧
      (workflowAnalysis.map (·.inferenceId)).Nodup then
    pure { certificateSemanticHash, checkerVersion, workflowOk, environmentCapture, replay,
           workflowAnalysis }
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
    capture := fun inv =>
      if PCS.V2.EnvFacts.envFactsB inv t.environmentCapture then t.environmentCapture else .null,
    workflow := fun c _ =>
      t.workflowOk && (match c with
        | .obj ms => PCS.V2.Workflow.workflowCheckB t.workflowAnalysis ms
        | _ => false),
    -- Important P0 boundary: a producer transcript is NEVER evidence that an
    -- unregistered check has semantically passed. Unrecognized types fail closed.
    exec := PCS.V2.Checkers.certifiedOnlyExec }

/-- Every evidence record, including records with UNVERIFIED outcomes, must have
an independently certified handler in the live Lean registry. A signer cannot
register a checker by choosing a new check_spec.type in an archive. -/
def allEvidenceRegistered (r : AcceptedResult) : Bool :=
  r.model.evidence.all (fun e =>
    PCS.V2.Checkers.registeredBuiltin (requestFor r.pkg.cert r.model r.table e))

def transcriptCovers (t : AuthorityTranscript) (r : AcceptedResult) : Bool :=
  (t.certificateSemanticHash == r.pkg.cert.semanticHash &&
   t.checkerVersion == r.model.checkerVersion &&
   decide (t.replay.map (·.evidenceId) = r.model.evidence.map (·.id))) &&
  allEvidenceRegistered r

def acceptPCSWithTranscript (t : AuthorityTranscript) (T : TrustAnchor)
    (inp : PackageInput) : Option AcceptedResult :=
  match acceptPCS (transcriptOracles t) T inp with
  | none => none
  | some r => if transcriptCovers t r then some r else none

/-- Fail-closed diagnostic mirror of `acceptPCSWithTranscript`.  This is not an
    alternate verifier: `ACCEPT` is returned exactly when the same stage predicates
    used by the authority succeed; every other result names the first rejecting stage. -/
def diagnosePCSWithTranscript (t : AuthorityTranscript) (T : TrustAnchor)
    (inp : PackageInput) : String :=
  let O := transcriptOracles t
  match verifyPackage O.unicode O.ed25519 T.pk T.expected inp with
  | none => "package"
  | some pr =>
    match decodeCertModel pr.cert with
    | none => "certificate_model"
    | some m =>
      match envStage O.capture pr.cert m inp.files with
      | none => "environment"
      | some _ =>
        if O.workflow (.obj pr.cert.members) inp.files then
          match artifactTable m inp.files with
          | none => "artifact_table"
          | some table =>
            if replayOK O.exec pr.cert m table then
              match verifyNormalizedSet inp.files with
              | none => "normalized_set"
              | some (i, ps) =>
                if normalizedOK pr.cert m i ps then
                  let r : AcceptedResult :=
                    { pkg := pr, model := m, table := table, env := (envStage O.capture pr.cert m inp.files).getD none,
                      index := i, claims := ps }
                  if transcriptCovers t r then "ACCEPT" else "transcript_binding"
                else "normalized"
            else "replay"
        else "workflow"

/-- A positive transcript binding includes independent checker registration. -/
theorem transcriptCovers_requires_registered {t : AuthorityTranscript} {r : AcceptedResult}
    (h : transcriptCovers t r = true) : allEvidenceRegistered r = true := by
  cases hreg : allEvidenceRegistered r with
  | false =>
      simp [transcriptCovers, hreg] at h
  | true =>
      simp [hreg]

/-- The ACTUAL pure acceptance function rejects every signed archive for which
the decoded evidence includes an unregistered check type, even if the earlier
package/cryptographic stages happened to pass. -/
theorem acceptPCSWithTranscript_rejects_unregistered
    {t : AuthorityTranscript} {T : TrustAnchor} {inp : PackageInput}
    {r : AcceptedResult}
    (hbase : acceptPCS (transcriptOracles t) T inp = some r)
    (hbad : allEvidenceRegistered r = false) :
    acceptPCSWithTranscript t T inp = none := by
  simp [acceptPCSWithTranscript, hbase, transcriptCovers, hbad]

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

/-- The compiled authority's verdict is exactly `acceptPCSWithTranscript`: the
    diagnostic mirror prints `ACCEPT` only when the proved checker accepts. -/
theorem diagnose_accept_implies_accept {t : AuthorityTranscript} {T : TrustAnchor}
    {inp : PackageInput} (h : diagnosePCSWithTranscript t T inp = "ACCEPT") :
    ∃ r, acceptPCSWithTranscript t T inp = some r := by
  unfold diagnosePCSWithTranscript at h
  unfold acceptPCSWithTranscript acceptPCS
  dsimp only at h
  cases hpr : verifyPackage (transcriptOracles t).unicode (transcriptOracles t).ed25519 T.pk
      T.expected inp with
  | none => rw [hpr] at h; simp at h
  | some pr =>
    rw [hpr] at h
    simp only at h ⊢
    cases hm : decodeCertModel pr.cert with
    | none => rw [hm] at h; simp at h
    | some m =>
      rw [hm] at h
      simp only at h ⊢
      cases henv : envStage (transcriptOracles t).capture pr.cert m inp.files with
      | none => rw [henv] at h; simp at h
      | some env =>
        rw [henv] at h
        simp only [Option.getD_some] at h ⊢
        by_cases hw : (transcriptOracles t).workflow (.obj pr.cert.members) inp.files = true
        · rw [if_pos hw] at h ⊢
          cases htab : artifactTable m inp.files with
          | none => rw [htab] at h; simp at h
          | some table =>
            rw [htab] at h
            simp only at h ⊢
            by_cases hrep : replayOK (transcriptOracles t).exec pr.cert m table = true
            · rw [if_pos hrep] at h ⊢
              cases hset : verifyNormalizedSet inp.files with
              | none => rw [hset] at h; simp at h
              | some ip =>
                obtain ⟨i, ps⟩ := ip
                rw [hset] at h
                simp only at h ⊢
                by_cases hn : normalizedOK pr.cert m i ps = true
                · rw [if_pos hn] at h ⊢
                  simp only at h ⊢
                  by_cases hcov : transcriptCovers t
                      { pkg := pr, model := m, table := table, env := env, index := i,
                        claims := ps } = true
                  · exact ⟨_, by rw [if_pos hcov]⟩
                  · rw [if_neg hcov] at h; simp at h
                · rw [if_neg hn] at h; simp at h
            · rw [if_neg hrep] at h; simp at h
        · rw [if_neg hw] at h; simp at h

/-- Conversely, every transcript-gated acceptance is reported as `ACCEPT`. -/
theorem accept_implies_diagnose_accept {t : AuthorityTranscript} {T : TrustAnchor}
    {inp : PackageInput} {r : AcceptedResult} (h : acceptPCSWithTranscript t T inp = some r) :
    diagnosePCSWithTranscript t T inp = "ACCEPT" := by
  unfold acceptPCSWithTranscript acceptPCS at h
  unfold diagnosePCSWithTranscript
  dsimp only
  cases hpr : verifyPackage (transcriptOracles t).unicode (transcriptOracles t).ed25519 T.pk
      T.expected inp with
  | none => rw [hpr] at h; simp at h
  | some pr =>
    rw [hpr] at h
    simp only at h ⊢
    cases hm : decodeCertModel pr.cert with
    | none => rw [hm] at h; simp at h
    | some m =>
      rw [hm] at h
      simp only at h ⊢
      cases henv : envStage (transcriptOracles t).capture pr.cert m inp.files with
      | none => rw [henv] at h; simp at h
      | some env =>
        rw [henv] at h
        simp only [Option.getD_some] at h ⊢
        by_cases hw : (transcriptOracles t).workflow (.obj pr.cert.members) inp.files = true
        · rw [if_pos hw] at h ⊢
          cases htab : artifactTable m inp.files with
          | none => rw [htab] at h; simp at h
          | some table =>
            rw [htab] at h
            simp only at h ⊢
            by_cases hrep : replayOK (transcriptOracles t).exec pr.cert m table = true
            · rw [if_pos hrep] at h ⊢
              cases hset : verifyNormalizedSet inp.files with
              | none => rw [hset] at h; simp at h
              | some ip =>
                obtain ⟨i, ps⟩ := ip
                rw [hset] at h
                simp only at h ⊢
                by_cases hn : normalizedOK pr.cert m i ps = true
                · rw [if_pos hn] at h ⊢
                  simp only at h ⊢
                  by_cases hcov : transcriptCovers t
                      { pkg := pr, model := m, table := table, env := env, index := i,
                        claims := ps } = true
                  · rw [if_pos hcov]
                  · rw [if_neg hcov] at h; simp at h
                · rw [if_neg hn] at h; simp at h
            · rw [if_neg hrep] at h; simp at h
        · rw [if_neg hw] at h; simp at h

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
