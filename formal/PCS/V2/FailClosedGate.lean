import PCS.V2.Witnesses.Instances
import PCS.V2.CanonicalArchive

/-!
# Fail-closed gates of the authoritative verifier

Before this file, the authority executed by `pcs-lean-authority` dispatched every replay
request to the verified built-in checkers, then to the registered domain checkers, and
**fell back to the host transcript** for any request no certified checker handles.  An
evidence item whose `check_spec.type` is unregistered (or missing) therefore passed replay
whenever the transcript reported the recorded outcome — even `PASS` over data that violates
the declared property (`PCS.V2.GoldenCx`).  A second, related gap existed at the claim
level: a claim recorded as supported could cite `PASS` evidence whose certified check
concerns *other* parameters than the claim's own predicate (only the evidence's declared
`predicate` field is bound to the claim, not its `check_spec`).

This file defines the two gates the authoritative verifier now enforces, and the strict
acceptance function built from them.

* **Check-type gate** (`supportedEvidenceB`): every evidence item of the certificate —
  whatever its recorded outcome, and whether or not any claim requires it — must be handled
  by a certified Lean checker (one of the six verified built-ins or a registered,
  proof-carrying domain checker).  Otherwise the archive is rejected with stage
  `unsupported_check_type`, *before* replay.
* **Claim-binding gate** (`claimsBoundB`): every certificate claim recorded at an assurance
  level (`FORMALLY_PROVEN`, `COMPUTATIONALLY_SUPPORTED`, `EMPIRICALLY_SUPPORTED`,
  `MIXED_SUPPORTED`) whose predicate is decoded by a registered domain adapter must be
  domain-accepted by that adapter, from its own required evidence, through the deterministic
  canonical obligation graph of a `ClaimBinder`.  Otherwise: stage `claim_binding`.

`acceptPCSStrictWith fb` runs the existing acceptance pipeline with replay executor
`dispatch (builtinCheckers ++ cs) fb` and then both gates.  Because of the check-type gate the
fallback `fb` is never consulted on an accepted archive; `acceptPCSStrictWith_fallback_irrelevant`
proves that the result is **the same for every fallback executor**, in particular for the
transcript and for the constant-`FAIL` executor `failClosedExec` that the executable uses.
-/

set_option autoImplicit false

namespace PCS.V2.FailClosed

open PCS PCS.V2.Json PCS.V2.EndToEnd PCS.V2.Authority PCS.V2.Replay PCS.V2.Package
open PCS.V2.CertificateModel PCS.V2.Checkers PCS.V2.DomainAuthority PCS.V2.DomainAdapter
open PCS.V2.ClaimGraph PCS.V2.NormalizedWire PCS.V2.Index PCS.V2.Witnesses PCS.V2.PKPDCheck
open PCS.V2.Zip PCS.V2.CanonicalArchive

/-! ## Check-type gate -/

/-- Is the replay request handled by a certified checker (verified built-in or registered)? -/
def certifiedHandles (cs : List CertifiedChecker) (req : ReplayRequest) : Bool :=
  (builtinCheckers ++ cs).any (fun k => k.handles req)

/-- **Check-type gate**: every evidence item is handled by a certified checker. -/
def supportedEvidenceB (cs : List CertifiedChecker) (c : CertV2) (m : CertModel)
    (table : List (String × ByteArray)) : Bool :=
  m.evidence.all (fun e => certifiedHandles cs (requestFor c m table e))

/-- The fallback executor of the executable: a constant `FAIL` observation.  It is never
    reached on an accepted archive (`acceptPCSStrictWith_fallback_irrelevant`). -/
def failClosedExec : Executor := fun _ => ⟨.provenance, .fail⟩

/-- Oracles of the strict authority with fallback executor `fb`. -/
def strictOracles (cs : List CertifiedChecker) (t : AuthorityTranscript) (fb : Executor) :
    Oracles :=
  { transcriptOracles t with exec := dispatch (builtinCheckers ++ cs) fb }

theorem strictOracles_transcript (cs : List CertifiedChecker) (t : AuthorityTranscript) :
    strictOracles cs t (transcriptExecutor t) = authorityOraclesWith cs t := rfl

/-! ## Claim-binding gate -/

/-- A registered claim interpretation: a domain adapter together with a deterministic
    (untrusted) builder of the canonical obligation graph for a claim.  Soundness never
    depends on the builder: the graph is checked by `checkGraph`. -/
structure ClaimBinder where
  D : Domain
  A : DomainAdapter D
  graphFor : List CertEvidence → CertClaim → D.Claim → Graph String A.IR

/-- The binder accepts claim `cl` of the accepted result `r`: either its predicate is not in
    the binder's domain, or the decoded domain claim is domain-accepted with the canonical
    graph. -/
def binderOK (b : ClaimBinder) (r : AcceptedResult) (cl : CertClaim) : Bool :=
  match b.A.decode cl.predicate with
  | none => true
  | some c => decide (domainAccepts b.A r cl.id (b.graphFor r.model.evidence cl c) = some c)

/-- Is the recorded certificate status an assurance level (a *supported* claim)? -/
def supportive (s : PCS.Decision.DecisionStatus) : Bool := (levelOf s).isSome

/-- **Claim-binding gate**: every supported claim is bound by every registered binder. -/
def claimsBoundB (bs : List ClaimBinder) (r : AcceptedResult) : Bool :=
  r.model.claims.all (fun cl => !supportive cl.status || bs.all (fun b => binderOK b r cl))

/-- First required evidence id of `cl` that discharges IR node `n`. -/
def leafEvidence {D : Domain} (A : DomainAdapter D) (evs : List CertEvidence) (cl : CertClaim)
    (n : A.IR) : Option String :=
  cl.requiredEvidence.find? (fun eid => evidenceLeafIn A evs cl eid n)

/-- A leaf node discharged by the first matching required evidence (or an explicitly
    unsupported node, which is never accepted). -/
def leafNode {D : Domain} (A : DomainAdapter D) (evs : List CertEvidence) (cl : CertClaim)
    (id : String) (n : A.IR) : Node String A.IR :=
  ⟨id, n, match leafEvidence A evs cl n with
    | some eid => .leaf eid
    | none => .unsupported "uncovered"⟩

/-- Canonical AI-safety graph: rule `ai.episodes` with one leaf per trace. -/
def aiGraph (evs : List CertEvidence) (cl : CertClaim) (c : AISafety.TraceClaim) :
    Graph String AISafety.TraceIR :=
  ⟨⟨"root", .all c, .derive "ai.episodes" (c.traces.map (fun a => "trace:" ++ a))⟩ ::
    c.traces.map (fun a => leafNode AISafety.aiAdapter evs cl ("trace:" ++ a)
      (.safe a c.budget c.forbidden)), "root"⟩

/-- Canonical biology graph: rule `bio.split` into the range and score leaves. -/
def bioGraph (evs : List CertEvidence) (cl : CertClaim) (c : Biology.BioClaim) :
    Graph String Biology.BioIR :=
  ⟨[⟨"root", .sites c, .derive "bio.split" ["range", "score"]⟩,
    leafNode Biology.bioAdapter evs cl "range" (.inRange c.seqA c.sitesA),
    leafNode Biology.bioAdapter evs cl "score" (.score c.seqA c.sitesA c.threshold)], "root"⟩

def aiBinder : ClaimBinder := ⟨AISafety.aiDomain, AISafety.aiAdapter, aiGraph⟩
def bioBinder : ClaimBinder := ⟨Biology.bioDomain, Biology.bioAdapter, bioGraph⟩

/-- The claim interpretations enforced by `pcs-lean-authority`. -/
def productionBinders : List ClaimBinder := [aiBinder, bioBinder]

/-! ## Strict acceptance -/

/-- **Strict (fail-closed) acceptance of a materialised package**, for replay fallback `fb`. -/
def acceptPCSStrictWith (fb : Executor) (cs : List CertifiedChecker) (bs : List ClaimBinder)
    (t : AuthorityTranscript) (T : TrustAnchor) (inp : PackageInput) : Option AcceptedResult :=
  match acceptPCS (strictOracles cs t fb) T inp with
  | none => none
  | some r =>
    if transcriptCovers t r && supportedEvidenceB cs r.pkg.cert r.model r.table &&
        claimsBoundB bs r then some r else none

/-- Strict acceptance of raw canonical archive bytes. -/
def acceptArchiveStrictWith (fb : Executor) (cs : List CertifiedChecker) (bs : List ClaimBinder)
    (t : AuthorityTranscript) (T : TrustAnchor) (raw : ByteArray) :
    Option (PackageInput × AcceptedResult) :=
  match decodeZip raw with
  | none => none
  | some es =>
    match fromArchiveEntries es with
    | none => none
    | some inp => (acceptPCSStrictWith fb cs bs t T inp).map (inp, ·)

/-- Diagnostic mirror of `acceptPCSStrictWith`: `ACCEPT`, or the first rejecting stage.  The
    check-type gate runs **before** replay, so an unsupported check type is never replayed. -/
def diagnosePCSStrictWith (fb : Executor) (cs : List CertifiedChecker) (bs : List ClaimBinder)
    (t : AuthorityTranscript) (T : TrustAnchor) (inp : PackageInput) : String :=
  let O := strictOracles cs t fb
  match verifyPackage O.unicode O.ed25519 T.pk T.expected inp with
  | none => "package"
  | some pr =>
    match decodeCertModel pr.cert with
    | none => "certificate_model"
    | some m =>
      match envStage O.capture pr.cert m inp.files with
      | none => "environment"
      | some env =>
        if O.workflow (.obj pr.cert.members) inp.files then
          match artifactTable m inp.files with
          | none => "artifact_table"
          | some table =>
            if supportedEvidenceB cs pr.cert m table then
              if replayOK O.exec pr.cert m table then
                match verifyNormalizedSet inp.files with
                | none => "normalized_set"
                | some (i, ps) =>
                  if normalizedOK pr.cert m i ps then
                    let r : AcceptedResult :=
                      { pkg := pr, model := m, table := table, env := env, index := i,
                        claims := ps }
                    if claimsBoundB bs r then
                      if transcriptCovers t r then "ACCEPT" else "transcript_binding"
                    else "claim_binding"
                  else "normalized"
              else "replay"
            else "unsupported_check_type"
        else "workflow"

/-- Raw-archive diagnostic mirror. -/
def diagnoseArchiveStrictWith (fb : Executor) (cs : List CertifiedChecker)
    (bs : List ClaimBinder) (t : AuthorityTranscript) (T : TrustAnchor) (raw : ByteArray) :
    String :=
  match decodeZip raw with
  | none => "canonical_archive"
  | some es =>
    match fromArchiveEntries es with
    | none => "archive_partition"
    | some inp => diagnosePCSStrictWith fb cs bs t T inp

end PCS.V2.FailClosed
