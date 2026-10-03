import PCS.V2.Authority
import PCS.V2.SHA256Spec

/-!
# High-assurance flagship: the Lean-authoritative path with a smaller trusted base

`PCS.V2.Flagship.pcs_accept_implies_scientific_assurance` is stated for an arbitrary
oracle bundle and needs all four `ExternalContracts`:

1. `Ed25519ImplCorrect` — the Ed25519 primitive meets a specification;
2. `NoForgery` — unforgeability for the trust-anchor key;
3. `CaptureSound` — the environment capture means what `describes` says;
4. `ReplayFaithful` — every replay `PASS` means the scientific predicate holds.

For the production authority (`PCS.V2.Authority.acceptPCSWithTranscript`, the function
whose verdict the compiled `pcs-lean-authority` prints, see
`diagnose_accept_implies_accept`) this file proves strictly stronger statements:

* `pcs_verified_builtin_acceptance_sound` — **no hypothesis at all**: acceptance implies
  structural assurance, per-claim `Assures`, and that every passing `reaction_balance`,
  `unit_compatible`, `csv_disjoint`, `pkpd_contract` and `pkpd_reference_match` evidence
  item denotes its declarative scientific proposition (balanced reaction / equal physical
  dimension / disjoint strict-CSV key sets / restricted PK/PD positivity-and-dimension
  contract / certified-interval agreement of every reported row with the analytic PK/PD
  model; the real-valued form is `PCSReal.PKPD.pcs_pkpd_reference_match_real`) on the
  exact committed request.  The transcript's PASS bit is never trusted for
  these kinds.
* `pcs_high_assurance_acceptance_sound` — hypotheses: only `NoForgery` (2) for the Lean
  RFC 8032 implementation and `CaptureSound` (3) **of the transcript's environment
  capture**.  (1) is discharged because the authority uses the Lean Ed25519
  implementation; (4) is discharged by the certified-checker dispatcher; and every
  digest is additionally proved to be FIPS 180-4 SHA-256 (`sha256_eq_spec`) rather than
  merely a KAT-validated transcription.
* `pcs_authority_binary_sound` — the same, from the compiled authority's `ACCEPT`.
-/

namespace PCS.V2.HighAssurance

open PCS PCS.Decision PCS.V2.Json PCS.V2.Hex PCS.V2.SHA256 PCS.V2.Canonical PCS.V2.Common
open PCS.V2.Package PCS.V2.Replay PCS.V2.CertificateModel PCS.V2.EndToEnd PCS.V2.Index
open PCS.V2.Signature PCS.V2.Flagship PCS.V2.TCB PCS.V2.Authority PCS.V2.Checkers PCS.V2.Domains

/-! ## Zero-assumption layer -/

/-- What authoritative acceptance establishes with **no** external assumption. -/
structure VerifiedBuiltinAssurance (t : AuthorityTranscript) (T : TrustAnchor)
    (inp : PackageInput) (r : AcceptedResult) : Prop where
  structural : StructuralAssurance (transcriptOracles t) T inp r
  claims : ∀ p ∈ r.claims, ClaimAssurance (transcriptOracles t) inp r p
  claimScope : r.claims.map (·.1.claimId) = claimIds r.model
  /-- the observation transcript is bound to this certificate and evidence list -/
  transcriptBound : t.certificateSemanticHash = r.pkg.cert.semanticHash ∧
    t.checkerVersion = r.model.checkerVersion ∧
    t.replay.map (·.evidenceId) = r.model.evidence.map (·.id)
  /-- every passing built-in evidence item denotes its scientific proposition -/
  builtinEvidence : ∀ p ∈ r.claims, ∀ ev ∈ p.2.evidence, ev.outcome = .pass →
    ∃ e ∈ r.model.evidence, e.id = ev.id ∧
      BuiltinSemantics (requestFor r.pkg.cert r.model r.table e)
  /-- every signed static-workflow claim is checked by Lean against the transcript's
      normalized static analysis (`PCS.V2.Workflow.WorkflowDescribes`) -/
  workflow : PCS.V2.Workflow.WorkflowDescribes t.workflowAnalysis r.pkg.cert.members
  /-- the signed environment declaration is the transcript capture, and its verified
      facts (`PCS.V2.EnvFacts.EnvFacts`: bound sources, exact/hash pins, interpreter
      versions, digest-pinned container bases) hold of the committed source bytes -/
  envFacts : ∀ eb inv, r.env = some (eb, inv) →
    envProjection eb.signed = t.environmentCapture ∧
    PCS.V2.EnvFacts.EnvFacts inv (envProjection eb.signed)
  /-- every replayed artifact is the exact delivered, manifest-signed byte string -/
  artifactsBound : ∀ x ∈ r.table, ∃ a ∈ r.model.artifacts, ∃ fm, a.id = x.1 ∧
    lookup inp.files a.path = some x.2 ∧ sha256 x.2.data.toList = a.sha256 ∧
    (a.path, fm) ∈ r.pkg.manifest.files ∧ sha256 x.2.data.toList = fm.sha256

theorem transcriptCovers_spec {t : AuthorityTranscript} {r : AcceptedResult}
    (h : transcriptCovers t r = true) :
    t.certificateSemanticHash = r.pkg.cert.semanticHash ∧
    t.checkerVersion = r.model.checkerVersion ∧
    t.replay.map (·.evidenceId) = r.model.evidence.map (·.id) := by
  unfold transcriptCovers at h
  simp only [Bool.and_eq_true, beq_iff_eq, decide_eq_true_eq] at h
  exact ⟨h.1.1, h.1.2, h.2⟩

theorem acceptPCSWithTranscript_covers {t : AuthorityTranscript} {T : TrustAnchor}
    {inp : PackageInput} {r : AcceptedResult} (h : acceptPCSWithTranscript t T inp = some r) :
    transcriptCovers t r = true := by
  unfold acceptPCSWithTranscript at h
  split at h
  · cases h
  · split at h
    · rename_i hc; cases h; exact hc
    · cases h

/-- The authority's workflow oracle is the Lean workflow check (conjoined with the
    production Boolean). -/
theorem authority_workflow_describes {t : AuthorityTranscript} {ms : List (String × JVal)}
    {files : FileMap} (h : (transcriptOracles t).workflow (.obj ms) files = true) :
    PCS.V2.Workflow.WorkflowDescribes t.workflowAnalysis ms ∧ t.workflowOk = true := by
  simp only [transcriptOracles, Bool.and_eq_true] at h
  exact ⟨PCS.V2.Workflow.workflowCheckB_sound h.2, h.1⟩

/-- The authority's capture is the transcript capture *only if* Lean's `envFactsB`
    accepts it; otherwise it is `null`, which can never equal a signed declaration. -/
theorem authority_capture_sound (t : AuthorityTranscript) :
    CaptureSound (transcriptOracles t).capture
      (fun inv v => v = .null ∨ (v = t.environmentCapture ∧ PCS.V2.EnvFacts.EnvFacts inv v)) := by
  intro inv
  simp only [transcriptOracles]
  split
  · rename_i hb
    exact Or.inr ⟨rfl, PCS.V2.EnvFacts.envFactsB_sound hb⟩
  · exact Or.inl rfl

theorem envProjection_ne_null (sv : List (String × JVal)) : envProjection sv ≠ .null := by
  simp [envProjection]

theorem authority_env_facts {t : AuthorityTranscript} {T : TrustAnchor} {inp : PackageInput}
    {r : AcceptedResult} (ha : acceptPCS (transcriptOracles t) T inp = some r)
    {eb : EnvBinding} {inv : List InventoryItem} (he : r.env = some (eb, inv)) :
    envProjection eb.signed = t.environmentCapture ∧
    PCS.V2.EnvFacts.EnvFacts inv (envProjection eb.signed) := by
  rcases pcs_environment_described ha (authority_capture_sound t) he with h | h
  · exact absurd h (envProjection_ne_null _)
  · exact ⟨h.1, h.2⟩

/-- **Verified built-in acceptance soundness (no assumptions).** -/
theorem pcs_verified_builtin_acceptance_sound {t : AuthorityTranscript} {T : TrustAnchor}
    {inp : PackageInput} {r : AcceptedResult} (h : acceptPCSWithTranscript t T inp = some r) :
    VerifiedBuiltinAssurance t T inp r := by
  have ha := acceptPCSWithTranscript_implies_acceptPCS h
  refine ⟨acceptPCS_sound ha, pcs_claims_assured ha, pcs_claim_scope ha,
    transcriptCovers_spec (acceptPCSWithTranscript_covers h), ?_,
    (authority_workflow_describes (acceptPCS_sound ha).workflow).1,
    fun _ _ he => authority_env_facts ha he, pcs_artifacts_bound ha⟩
  intro p hp ev hev hpass
  obtain ⟨e, he, hid, hholds⟩ :=
    pcs_evidence_holds ha (builtinExecWith_faithful (replayFaithful_reported _)) p hp ev hev hpass
  exact ⟨e, he, hid, builtinHolds_semantics hholds⟩

/-! ## High-assurance layer: only unforgeability and capture soundness remain -/

theorem transcriptOracles_ed25519 (t : AuthorityTranscript) :
    (transcriptOracles t).ed25519 = PCS.V2.Ed25519.verify := rfl

/-- (A) is a theorem for the authority: it runs the Lean RFC 8032 implementation. -/
theorem authority_ed25519ImplCorrect (t : AuthorityTranscript) :
    Ed25519ImplCorrect (transcriptOracles t).ed25519 PCS.V2.Ed25519.verify := by
  rw [transcriptOracles_ed25519]; exact fun _ _ _ => rfl

/-- The remaining assumptions of the authoritative path. -/
structure AuthorityContracts (t : AuthorityTranscript) (T : TrustAnchor) where
  /-- messages the trust-anchor key holder actually signed -/
  signed : List UInt8 → Prop
  /-- (B) unforgeability of the Lean RFC 8032 Ed25519 verifier for the trust-anchor key -/
  noForgery : NoForgery PCS.V2.Ed25519.verify T.pk signed
  /-- meaning of the transcript's environment capture -/
  describes : List InventoryItem → JVal → Prop
  /-- (C) the transcript's environment capture means what `describes` says -/
  captureSound : CaptureSound (transcriptOracles t).capture describes

/-- The full `ExternalContracts` for the authority oracles, built from the two remaining
    assumptions: Ed25519 implementation correctness and replay faithfulness are theorems. -/
def AuthorityContracts.toExternal {t : AuthorityTranscript} {T : TrustAnchor}
    (K : AuthorityContracts t T) : ExternalContracts (transcriptOracles t) T :=
  contractsWithLeanEd25519 rfl K.signed K.noForgery K.describes K.captureSound
    (BuiltinHolds (fun req => (transcriptExecutor t req).outcome = .pass))
    (builtinExecWith_faithful (replayFaithful_reported _))

/-- The high-assurance conclusion. -/
structure HighAssurance (t : AuthorityTranscript) (T : TrustAnchor) (K : AuthorityContracts t T)
    (inp : PackageInput) (r : AcceptedResult) : Prop where
  /-- everything the generic flagship gives, for the authority oracles -/
  scientific : ScientificAssurance (transcriptOracles t) T K.toExternal inp r
  /-- the zero-assumption built-in layer -/
  verified : VerifiedBuiltinAssurance t T inp r
  /-- authenticity, stated against the trust anchor's actual signing record -/
  authentic : K.signed (signedMessage packageSignatureDomain (encodeManifest r.pkg.manifest)) ∧
    ∃ csp, certSigPayload r.pkg.cert = some csp ∧
      K.signed (signedMessage certificateSignatureDomain csp)
  /-- every delivered member's digest is the FIPS 180-4 SHA-256 of its exact bytes -/
  memberDigestsFIPS : ∀ n b, (n, b) ∈ inp.files → ∃ fm, (n, fm) ∈ r.pkg.manifest.files ∧
    b.size = fm.size ∧ PCS.V2.FIPS1804Spec.sha256 b.data.toList = fm.sha256
  /-- every replayed artifact is bound by its FIPS 180-4 SHA-256 digest -/
  artifactDigestsFIPS : ∀ x ∈ r.table, ∃ a ∈ r.model.artifacts,
    a.id = x.1 ∧ PCS.V2.FIPS1804Spec.sha256 x.2.data.toList = a.sha256
  /-- environment declaration = transcript capture, with its declared meaning -/
  environment : ∀ eb inv, r.env = some (eb, inv) →
    envProjection eb.signed = t.environmentCapture ∧ K.describes inv (envProjection eb.signed)

/-- **High-assurance acceptance soundness.**  Hypotheses: Ed25519 unforgeability for
    the trust anchor and soundness of the transcript's environment capture — nothing
    else.  No replay-faithfulness, no Ed25519-implementation, no SHA-256-specification
    assumption. -/
theorem pcs_high_assurance_acceptance_sound {t : AuthorityTranscript} {T : TrustAnchor}
    (K : AuthorityContracts t T) {inp : PackageInput} {r : AcceptedResult}
    (h : acceptPCSWithTranscript t T inp = some r) : HighAssurance t T K inp r := by
  have ha := acceptPCSWithTranscript_implies_acceptPCS h
  have hs := pcs_accept_implies_scientific_assurance K.toExternal ha
  have hv := pcs_verified_builtin_acceptance_sound h
  obtain ⟨hp, csp, _, hcsp, _, _, _, hc⟩ :=
    pcs_authentic ha (authority_ed25519ImplCorrect t) K.noForgery
  refine ⟨hs, hv, ⟨hp, csp, hcsp, hc⟩, ?_, ?_, ?_⟩
  · intro n b hb
    obtain ⟨fm, hfm, hsz, hd⟩ := hs.memberDigests n b hb
    exact ⟨fm, hfm, hsz, by rw [← PCS.V2.SHA256Spec.sha256_eq_spec]; exact hd⟩
  · intro x hx
    obtain ⟨a, ha', _, hid, _, hd, _, _⟩ := hv.artifactsBound x hx
    exact ⟨a, ha', hid, by rw [← PCS.V2.SHA256Spec.sha256_eq_spec]; exact hd⟩
  · intro eb inv he
    exact ⟨(authority_env_facts ha he).1,
      pcs_environment_described (Describes := K.describes) ha K.captureSound he⟩

/-- **The compiled authority's `ACCEPT` is sound** under the same two assumptions. -/
theorem pcs_authority_binary_sound {t : AuthorityTranscript} {T : TrustAnchor}
    (K : AuthorityContracts t T) {inp : PackageInput}
    (h : diagnosePCSWithTranscript t T inp = "ACCEPT") :
    ∃ r, acceptPCSWithTranscript t T inp = some r ∧ HighAssurance t T K inp r := by
  obtain ⟨r, hr⟩ := diagnose_accept_implies_accept h
  exact ⟨r, hr, pcs_high_assurance_acceptance_sound K hr⟩

/-- Zero-assumption version from the compiled authority's `ACCEPT`. -/
theorem pcs_authority_binary_builtin_sound {t : AuthorityTranscript} {T : TrustAnchor}
    {inp : PackageInput} (h : diagnosePCSWithTranscript t T inp = "ACCEPT") :
    ∃ r, acceptPCSWithTranscript t T inp = some r ∧ VerifiedBuiltinAssurance t T inp r := by
  obtain ⟨r, hr⟩ := diagnose_accept_implies_accept h
  exact ⟨r, hr, pcs_verified_builtin_acceptance_sound hr⟩

/-- **Workflow semantics of authoritative acceptance.**  The only hypothesis is the
    narrow front-end contract `hA`: each normalized analysis record handed to the authority
    satisfies the front-end meaning `A`.  The comparison of signed claims against the
    analysis (`static_only`, `user_code_executed`, human confirmation, inference identity,
    source path/kind, source-artifact inclusion, exact/subset input-output relation,
    rediscovered references, operation/kind consistency, source binding to a committed
    artifact) is proved, not assumed. -/
theorem pcs_workflow_acceptance_sound {t : AuthorityTranscript} {T : TrustAnchor}
    {inp : PackageInput} {r : AcceptedResult} (h : acceptPCSWithTranscript t T inp = some r)
    (A : PCS.V2.Workflow.FreshSource → Prop) (hA : ∀ f ∈ t.workflowAnalysis, A f) :
    PCS.V2.Workflow.WorkflowSemantics A r.pkg.cert.members :=
  PCS.V2.Workflow.workflowDescribes_semantics (pcs_verified_builtin_acceptance_sound h).workflow hA

/-- For a certificate without an environment contract, `CaptureSound` is irrelevant:
    the only remaining assumption is Ed25519 unforgeability. -/
theorem pcs_no_environment_authentic {t : AuthorityTranscript} {T : TrustAnchor}
    {signed : List UInt8 → Prop} (hB : NoForgery PCS.V2.Ed25519.verify T.pk signed)
    {inp : PackageInput} {r : AcceptedResult} (h : acceptPCSWithTranscript t T inp = some r) :
    VerifiedBuiltinAssurance t T inp r ∧
    signed (signedMessage packageSignatureDomain (encodeManifest r.pkg.manifest)) ∧
    ∃ csp, certSigPayload r.pkg.cert = some csp ∧
      signed (signedMessage certificateSignatureDomain csp) := by
  have ha := acceptPCSWithTranscript_implies_acceptPCS h
  obtain ⟨hp, csp, _, hcsp, _, _, _, hc⟩ :=
    pcs_authentic ha (authority_ed25519ImplCorrect t) hB
  exact ⟨pcs_verified_builtin_acceptance_sound h, hp, csp, hcsp, hc⟩

end PCS.V2.HighAssurance
