import PCS.V2.DomainAdapter
import PCS.V2.Frontier

/-!
# Flagship: raw canonical signed archive ⟶ domain-native semantic proposition

Two authoritative paths are covered.

1. **The production Lean authority, unchanged** (`acceptArchiveWithTranscript`, the function
   whose verdict `pcs-lean-authority --zip` prints).  `pcs_generic_domain_archive_acceptance_sound`
   composes `PCS.V2.Frontier.pcs_frontier_archive_acceptance_sound` (sole cryptographic
   hypothesis: `NoForgery` for the trust anchor) with `domain_adapter_sound`.  A domain
   whose leaf obligations are discharged by the six verified built-in checkers needs no
   further hypothesis (`…_builtin`); a domain relying on transcript-reported external
   validators must state the meaning of those reports explicitly (`hExt`).

2. **The authority extended with domain checkers** (`acceptArchiveWithCheckers cs`): every
   domain registers proof-carrying `CertifiedChecker`s; the built-ins keep priority, so
   their semantics are preserved (`authorityValid_builtin`).  For `cs = []` this *is* the
   production authority (`acceptArchiveWithCheckers_nil`).  `ExtendedAssurance` re-derives
   the frontier conclusions for the extended executor under the same single hypothesis
   `NoForgery`.

Trusted / assumed (all visible in the theorem types): `NoForgery` for the Lean RFC 8032
verifier and the trust-anchor key; for path 1 or 2 with external validators, `hExt` (meaning
of transcript-reported PASS for kinds no certified checker handles); the adapter contract
`AdapterSound`, which every domain proves once.
-/

set_option autoImplicit false

namespace PCS.V2.DomainAuthority

open PCS PCS.V2.Json PCS.V2.EndToEnd PCS.V2.Archive PCS.V2.Authority PCS.V2.HighAssurance
open PCS.V2.Zip PCS.V2.TCB PCS.V2.Package PCS.V2.CanonicalArchive PCS.V2.Replay PCS.V2.Signature
open PCS.V2.Domains PCS.V2.Flagship PCS.V2.Checkers PCS.V2.Frontier PCS.V2.CertificateModel
open PCS.V2.DomainAdapter PCS.V2.ClaimGraph PCS.V2.Index PCS.V2.Common

variable {D : Domain}

/-! ## Path 1: the production authority -/

/-- **Generic domain soundness of the production raw-archive authority.**

    Hypotheses: Ed25519 unforgeability for the trust anchor (inherited unchanged from the
    frontier theorem), the meaning `ExtHolds` of transcript-reported PASS for evidence kinds
    that no verified built-in handles (`hExt`), and the adapter contract relative to the
    authority's PASS-meaning `BuiltinHolds ExtHolds`.

    Conclusion: everything `pcs_frontier_archive_acceptance_sound` gives, plus the domain
    claim bound to the signed certificate claim `cid` holds in the world of the committed
    artifact bytes, with PCS `Assures` for that claim and a structurally sound obligation
    graph. -/
theorem pcs_generic_domain_archive_acceptance_sound {t : AuthorityTranscript} {T : TrustAnchor}
    {signed : List UInt8 → Prop} (hB : NoForgery PCS.V2.Ed25519.verify T.pk signed)
    {ExtHolds : ReplayRequest → Prop} (hExt : ReplayFaithful (transcriptExecutor t) ExtHolds)
    {raw : ByteArray} {inp : PackageInput} {r : AcceptedResult}
    (h : acceptArchiveWithTranscript t T raw = some (inp, r))
    (A : DomainAdapter D) (hA : AdapterSound A (BuiltinHolds ExtHolds))
    {cid : String} {g : Graph String A.IR} {c : D.Claim}
    (hd : domainAccepts A r cid g = some c) :
    (∃ es, CanonicalZip raw es ∧ ArchivePartition es inp ∧
      HighAssurance t T (verifiedContracts t T signed hB) inp r) ∧
    DomainAssurance A r cid g c := by
  obtain ⟨_, _, _, ha⟩ := acceptArchiveWithTranscript_spec h
  exact ⟨pcs_frontier_archive_acceptance_sound hB h,
    domain_adapter_sound (acceptPCSWithTranscript_implies_acceptPCS ha)
      (builtinExecWith_faithful hExt) A hA hd⟩

/-- The same with **no hypothesis beyond `NoForgery`**: transcript reports are given only
    their literal meaning ("the transcript said PASS"), so the adapter contract must be
    discharged from the verified built-ins' semantics alone. -/
theorem pcs_generic_domain_archive_acceptance_sound_builtin {t : AuthorityTranscript}
    {T : TrustAnchor} {signed : List UInt8 → Prop}
    (hB : NoForgery PCS.V2.Ed25519.verify T.pk signed)
    {raw : ByteArray} {inp : PackageInput} {r : AcceptedResult}
    (h : acceptArchiveWithTranscript t T raw = some (inp, r)) (A : DomainAdapter D)
    (hA : AdapterSound A (BuiltinHolds (fun req => (transcriptExecutor t req).outcome = .pass)))
    {cid : String} {g : Graph String A.IR} {c : D.Claim}
    (hd : domainAccepts A r cid g = some c) :
    (∃ es, CanonicalZip raw es ∧ ArchivePartition es inp ∧
      HighAssurance t T (verifiedContracts t T signed hB) inp r) ∧
    DomainAssurance A r cid g c :=
  pcs_generic_domain_archive_acceptance_sound hB (replayFaithful_reported _) h A hA hd

/-! ## Path 2: the authority extended with registered domain checkers -/

/-- Authority oracles whose executor runs the verified built-ins first, then the registered
    domain checkers `cs`, then the transcript. -/
def authorityOraclesWith (cs : List CertifiedChecker) (t : AuthorityTranscript) : Oracles :=
  { transcriptOracles t with exec := dispatch (builtinCheckers ++ cs) (transcriptExecutor t) }

def acceptPCSWithCheckers (cs : List CertifiedChecker) (t : AuthorityTranscript)
    (T : TrustAnchor) (inp : PackageInput) : Option AcceptedResult :=
  match acceptPCS (authorityOraclesWith cs t) T inp with
  | none => none
  | some r => if transcriptCovers t r then some r else none

/-- The extended raw canonical-archive authority. -/
def acceptArchiveWithCheckers (cs : List CertifiedChecker) (t : AuthorityTranscript)
    (T : TrustAnchor) (raw : ByteArray) : Option (PackageInput × AcceptedResult) :=
  match decodeZip raw with
  | none => none
  | some es =>
    match fromArchiveEntries es with
    | none => none
    | some inp => (acceptPCSWithCheckers cs t T inp).map (inp, ·)

theorem authorityOraclesWith_nil (t : AuthorityTranscript) :
    authorityOraclesWith [] t = transcriptOracles t := by
  simp [authorityOraclesWith, transcriptOracles, builtinExecWith]

/-- With no registered domain checker the extended authority **is** the production one. -/
theorem acceptPCSWithCheckers_nil (t : AuthorityTranscript) (T : TrustAnchor)
    (inp : PackageInput) : acceptPCSWithCheckers [] t T inp = acceptPCSWithTranscript t T inp := by
  simp only [acceptPCSWithCheckers, acceptPCSWithTranscript, authorityOraclesWith_nil]
  rfl

theorem acceptArchiveWithCheckers_nil (t : AuthorityTranscript) (T : TrustAnchor)
    (raw : ByteArray) :
    acceptArchiveWithCheckers [] t T raw = acceptArchiveWithTranscript t T raw := by
  simp only [acceptArchiveWithCheckers, acceptArchiveWithTranscript, acceptPCSWithCheckers_nil]
  rfl

/-- Meaning of a PASS of the extended executor. -/
def AuthorityValid (cs : List CertifiedChecker) (ExtHolds : ReplayRequest → Prop) :
    ReplayRequest → Prop :=
  DispatchHolds (builtinCheckers ++ cs) ExtHolds

theorem authorityWith_faithful (cs : List CertifiedChecker) {t : AuthorityTranscript}
    {ExtHolds : ReplayRequest → Prop} (hExt : ReplayFaithful (transcriptExecutor t) ExtHolds) :
    ReplayFaithful (authorityOraclesWith cs t).exec (AuthorityValid cs ExtHolds) :=
  dispatch_faithful _ hExt

theorem dispatchHolds_append (cs₁ cs₂ : List CertifiedChecker) (fb : ReplayRequest → Prop)
    (req : ReplayRequest) :
    DispatchHolds (cs₁ ++ cs₂) fb req ↔ DispatchHolds cs₁ (DispatchHolds cs₂ fb) req := by
  unfold DispatchHolds
  rw [List.find?_append]
  cases cs₁.find? (·.handles req) <;> simp

/-- Registered domain checkers cannot change the meaning of the verified built-ins. -/
theorem authorityValid_builtin {cs : List CertifiedChecker} {ExtHolds : ReplayRequest → Prop}
    {req : ReplayRequest} (h : AuthorityValid cs ExtHolds req) : BuiltinSemantics req :=
  builtinHolds_semantics ((dispatchHolds_append _ _ _ _).mp h)

/-- `DispatchHolds` of a request that exactly one registered checker can handle is that
    checker's proposition — the lemma adapters use to discharge `leaf_sound`. -/
theorem dispatchHolds_of_unique {cs : List CertifiedChecker} {fb : ReplayRequest → Prop}
    {req : ReplayRequest} {k : CertifiedChecker}
    (huniq : ∀ k' ∈ cs, k'.handles req = true → k'.Holds req → k.Holds req)
    (hk : k ∈ cs) (hhk : k.handles req = true) (h : DispatchHolds cs fb req) : k.Holds req := by
  unfold DispatchHolds at h
  split at h
  · rename_i k' hk'
    exact huniq k' (List.mem_of_find?_eq_some hk') (by simpa using List.find?_some hk') h
  · rename_i hn
    exact absurd (List.find?_eq_none.mp hn k hk) (by simp [hhk])

/-- The extended contracts: only `NoForgery` and the external-validator meaning. -/
def extendedContracts (cs : List CertifiedChecker) (t : AuthorityTranscript) (T : TrustAnchor)
    (signed : List UInt8 → Prop) (hB : NoForgery PCS.V2.Ed25519.verify T.pk signed)
    (ExtHolds : ReplayRequest → Prop) (hExt : ReplayFaithful (transcriptExecutor t) ExtHolds) :
    ExternalContracts (authorityOraclesWith cs t) T :=
  contractsWithLeanEd25519 rfl signed hB (VerifiedCapture t) (authority_capture_sound t)
    (AuthorityValid cs ExtHolds) (authorityWith_faithful cs hExt)

/-- Frontier-strength conclusions for the extended authority. -/
structure ExtendedAssurance (cs : List CertifiedChecker) (t : AuthorityTranscript)
    (T : TrustAnchor) (K : ExternalContracts (authorityOraclesWith cs t) T)
    (inp : PackageInput) (r : AcceptedResult) : Prop where
  /-- the generic flagship's conclusion (structure, canonical control records, exact member
      set and digests, claim scope, per-claim `Assures`, authenticity, environment, and the
      PASS-meaning of every passing evidence item) -/
  scientific : ScientificAssurance (authorityOraclesWith cs t) T K inp r
  /-- the transcript is bound to this certificate and evidence list -/
  transcriptBound : t.certificateSemanticHash = r.pkg.cert.semanticHash ∧
    t.checkerVersion = r.model.checkerVersion ∧
    t.replay.map (·.evidenceId) = r.model.evidence.map (·.id)
  /-- every passing built-in evidence item keeps its verified scientific meaning -/
  builtinEvidence : ∀ e ∈ r.model.evidence, e.outcome = .pass →
    BuiltinSemantics (requestFor r.pkg.cert r.model r.table e)
  /-- every member digest is FIPS 180-4 SHA-256 of the exact bytes -/
  memberDigestsFIPS : ∀ n b, (n, b) ∈ inp.files → ∃ fm, (n, fm) ∈ r.pkg.manifest.files ∧
    b.size = fm.size ∧ PCS.V2.FIPS1804Spec.sha256 b.data.toList = fm.sha256
  /-- every replayed artifact is the delivered, manifest-signed byte string -/
  artifactsBound : ∀ x ∈ r.table, ∃ a ∈ r.model.artifacts, ∃ fm, a.id = x.1 ∧
    lookup inp.files a.path = some x.2 ∧
    PCS.V2.FIPS1804Spec.sha256 x.2.data.toList = a.sha256 ∧
    (a.path, fm) ∈ r.pkg.manifest.files
  /-- verified environment facts -/
  envFacts : ∀ eb inv, r.env = some (eb, inv) →
    envProjection eb.signed = t.environmentCapture ∧
    PCS.V2.EnvFacts.EnvFacts inv (envProjection eb.signed)
  /-- signed static-workflow claims checked against the normalized static analysis -/
  workflow : PCS.V2.Workflow.WorkflowDescribes t.workflowAnalysis r.pkg.cert.members

theorem acceptPCSWithCheckers_spec {cs : List CertifiedChecker} {t : AuthorityTranscript}
    {T : TrustAnchor} {inp : PackageInput} {r : AcceptedResult}
    (h : acceptPCSWithCheckers cs t T inp = some r) :
    acceptPCS (authorityOraclesWith cs t) T inp = some r ∧ transcriptCovers t r = true := by
  unfold acceptPCSWithCheckers at h
  split at h
  · cases h
  · rename_i r' hr
    split at h
    · rename_i hc; cases h; exact ⟨hr, hc⟩
    · cases h

theorem acceptArchiveWithCheckers_spec {cs : List CertifiedChecker} {t : AuthorityTranscript}
    {T : TrustAnchor} {raw : ByteArray} {inp : PackageInput} {r : AcceptedResult}
    (h : acceptArchiveWithCheckers cs t T raw = some (inp, r)) :
    ∃ es, decodeZip raw = some es ∧ ArchivePartition es inp ∧
      acceptPCSWithCheckers cs t T inp = some r := by
  unfold acceptArchiveWithCheckers at h
  split at h
  · cases h
  · rename_i es hes
    split at h
    · cases h
    · rename_i inp' hinp
      cases hr : acceptPCSWithCheckers cs t T inp' with
      | none => rw [hr] at h; cases h
      | some r' =>
        rw [hr] at h
        simp only [Option.map_some, Option.some.injEq, Prod.mk.injEq] at h
        obtain ⟨rfl, rfl⟩ := h
        exact ⟨es, hes, fromArchiveEntries_sound hinp, hr⟩

/-- **Frontier theorem for the extended authority.**  Hypotheses: `NoForgery` and the
    external-validator meaning `hExt` (take `ExtHolds := reported PASS` to discharge it). -/
theorem pcs_extended_acceptance_sound (cs : List CertifiedChecker) {t : AuthorityTranscript}
    {T : TrustAnchor} {signed : List UInt8 → Prop}
    (hB : NoForgery PCS.V2.Ed25519.verify T.pk signed)
    {ExtHolds : ReplayRequest → Prop} (hExt : ReplayFaithful (transcriptExecutor t) ExtHolds)
    {inp : PackageInput} {r : AcceptedResult} (h : acceptPCSWithCheckers cs t T inp = some r) :
    ExtendedAssurance cs t T (extendedContracts cs t T signed hB ExtHolds hExt) inp r := by
  obtain ⟨ha, hcov⟩ := acceptPCSWithCheckers_spec h
  have hs := pcs_accept_implies_scientific_assurance
    (extendedContracts cs t T signed hB ExtHolds hExt) ha
  refine ⟨hs, transcriptCovers_spec hcov, ?_, ?_, ?_, ?_, ?_⟩
  · intro e he hpass
    have hobs := replayOK_spec (acceptPCS_sound ha).replay e he
    exact authorityValid_builtin (authorityWith_faithful cs hExt _ (by rw [hobs, hpass]))
  · intro n b hb
    obtain ⟨fm, hfm, hsz, hd⟩ := hs.memberDigests n b hb
    exact ⟨fm, hfm, hsz, by rw [← PCS.V2.SHA256Spec.sha256_eq_spec]; exact hd⟩
  · intro x hx
    obtain ⟨a, ha', fm, hid, hl, hd, hfm, _⟩ := pcs_artifacts_bound ha x hx
    exact ⟨a, ha', fm, hid, hl, by rw [← PCS.V2.SHA256Spec.sha256_eq_spec]; exact hd, hfm⟩
  · intro eb inv he
    rcases pcs_environment_described (Describes := VerifiedCapture t) ha
        (authority_capture_sound t) he with h0 | h1
    · exact absurd h0 (envProjection_ne_null _)
    · exact h1
  · exact (authority_workflow_describes (files := inp.files) (acceptPCS_sound ha).workflow).1

/-- **Flagship: generic domain soundness of the extended raw-archive authority.**

    raw canonical signed archive → canonical ZIP decoding → package/signature/digest
    verification → typed certificate claim → domain adapter (`decode`, `compile`) →
    obligation graph → certified validators / replay → PCS `Assures` → `D.Holds`.

    Hypotheses: `NoForgery` (trust anchor), `hExt` (meaning of transcript-reported PASS
    for kinds no certified checker handles), `AdapterSound` for the extended executor's
    PASS-meaning.  No hypothesis about the obligation graph or its producer. -/
theorem pcs_generic_domain_archive_acceptance_sound_with (cs : List CertifiedChecker)
    {t : AuthorityTranscript} {T : TrustAnchor} {signed : List UInt8 → Prop}
    (hB : NoForgery PCS.V2.Ed25519.verify T.pk signed)
    {ExtHolds : ReplayRequest → Prop} (hExt : ReplayFaithful (transcriptExecutor t) ExtHolds)
    {raw : ByteArray} {inp : PackageInput} {r : AcceptedResult}
    (h : acceptArchiveWithCheckers cs t T raw = some (inp, r))
    (A : DomainAdapter D) (hA : AdapterSound A (AuthorityValid cs ExtHolds))
    {cid : String} {g : Graph String A.IR} {c : D.Claim}
    (hd : domainAccepts A r cid g = some c) :
    (∃ es, CanonicalZip raw es ∧ ArchivePartition es inp ∧
      ExtendedAssurance cs t T (extendedContracts cs t T signed hB ExtHolds hExt) inp r) ∧
    DomainAssurance A r cid g c := by
  obtain ⟨es, hes, hp, ha⟩ := acceptArchiveWithCheckers_spec h
  exact ⟨⟨es, decodeZip_sound hes, hp, pcs_extended_acceptance_sound cs hB hExt ha⟩,
    domain_adapter_sound (acceptPCSWithCheckers_spec ha).1 (authorityWith_faithful cs hExt)
      A hA hd⟩

/-- The extended flagship with **`NoForgery` as the only hypothesis** (transcript reports
    get only their literal meaning). -/
theorem pcs_generic_domain_archive_acceptance_sound_certified (cs : List CertifiedChecker)
    {t : AuthorityTranscript} {T : TrustAnchor} {signed : List UInt8 → Prop}
    (hB : NoForgery PCS.V2.Ed25519.verify T.pk signed)
    {raw : ByteArray} {inp : PackageInput} {r : AcceptedResult}
    (h : acceptArchiveWithCheckers cs t T raw = some (inp, r)) (A : DomainAdapter D)
    (hA : AdapterSound A (AuthorityValid cs (fun req => (transcriptExecutor t req).outcome = .pass)))
    {cid : String} {g : Graph String A.IR} {c : D.Claim}
    (hd : domainAccepts A r cid g = some c) :
    (∃ es, CanonicalZip raw es ∧ ArchivePartition es inp ∧
      ExtendedAssurance cs t T
        (extendedContracts cs t T signed hB _ (replayFaithful_reported _)) inp r) ∧
    DomainAssurance A r cid g c :=
  pcs_generic_domain_archive_acceptance_sound_with cs hB (replayFaithful_reported _) h A hA hd

end PCS.V2.DomainAuthority
