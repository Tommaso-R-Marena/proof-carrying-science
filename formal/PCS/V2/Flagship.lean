import PCS.V2.EndToEnd

/-!
# Flagship: from accepted v0.6 bytes to scientific assurance

Layering (each layer adds exactly one named external contract):

1. `acceptPCS_sound`               — no assumptions: `StructuralAssurance`;
2. `pcs_claims_assured`            — no assumptions: every accepted claim's
   decision is a v1 kernel `Assures` judgement, the claim/predicate/decision are the
   certificate's, and every evidence outcome is the *fresh* executor observation on a
   request built from the verified certificate and digest-checked artifact bytes;
3. `pcs_authentic`                 — + Ed25519 implementation correctness (A) and
   unforgeability for the trust-anchor key (B);
4. `pcs_environment_described`     — + capture soundness;
5. `pcs_evidence_holds`            — + replay faithfulness;
6. `pcs_accept_implies_scientific_assurance` — all of the above, bundled in
   `ExternalContracts`, concluding `ScientificAssurance`.
-/

namespace PCS.V2.Flagship

open PCS PCS.Decision PCS.V2.Json PCS.V2.Hex PCS.V2.SHA256 PCS.V2.Domains PCS.V2.Canonical
open PCS.V2.Common PCS.V2.NormalizedWire PCS.V2.Index PCS.V2.Package PCS.V2.CertificateModel
open PCS.V2.Signature PCS.V2.Replay PCS.V2.EndToEnd

/-! ## Generic helpers -/

theorem mapOpt_complete {α β : Type} {f : α → Option β} :
    ∀ {xs : List α} {ys : List β}, mapOpt f xs = some ys → ∀ x ∈ xs, ∃ y ∈ ys, f x = some y
  | [], _, _, _, hx => by cases hx
  | x :: xs, ys, h, x', hx' => by
    simp only [mapOpt] at h
    split at h
    · rename_i y ys' hy hys
      cases h
      simp only [List.mem_cons] at hx'
      rcases hx' with rfl | hx'
      · exact ⟨y, List.mem_cons_self, hy⟩
      · obtain ⟨y', hy', hf⟩ := mapOpt_complete hys x' hx'
        exact ⟨y', List.mem_cons_of_mem _ hy', hf⟩
    · cases h

/-- The certificate signature payload carries the certificate's semantic and
    integrity hashes verbatim. -/
theorem certSigPayload_binds {raw : ByteArray} {c : CertV2} (hc : CertAccepted raw c)
    {csp : JVal} (h : certSigPayload c = some csp) :
    ∃ ms, csp = .obj ms ∧ ("semantic_hash", .str (hexEncode c.semanticHash)) ∈ ms ∧
      ("integrity_hash", .str (hexEncode c.integrityHash)) ∈ ms := by
  unfold certSigPayload at h
  cases hm : mapOpt (fun k => (field c.members k).map (fun v => (k, v))) certSigKeys with
  | none => rw [hm] at h; cases h
  | some ms =>
    rw [hm] at h
    cases h
    refine ⟨ms, rfl, ?_, ?_⟩
    · obtain ⟨y, hy, hf⟩ := mapOpt_complete hm "semantic_hash" (by decide)
      rw [hc.semanticField] at hf
      cases hf
      exact hy
    · obtain ⟨y, hy, hf⟩ := mapOpt_complete hm "integrity_hash" (by decide)
      rw [hc.integrityField] at hf
      cases hf
      exact hy

/-! ## Layer 2: claim-level assurance (unconditional) -/

/-- What PCS acceptance establishes about one accepted claim. -/
structure ClaimAssurance (O : Oracles) (inp : PackageInput) (r : AcceptedResult)
    (p : EntryV2 × WireV2) : Prop where
  /-- the decision object is the canonical wire delivered at the claim's storage path -/
  delivered : ∃ raw, lookup inp.files (keyPath p.1.storageKey) = some raw ∧
    verifyWireBytes raw = some p.2 ∧ p.1.storageKey = storageKey p.1.claimId
  /-- exact claim, committed predicate, scope and decision from the certificate -/
  certificateClaim : ∃ cl ∈ r.model.claims,
    cl.id = p.1.claimId ∧ p.2.claim.id = cl.id ∧ p.2.claim.kind = cl.kind ∧
    p.2.claim.predicateCommitment = commitmentOf cl.predicate ∧
    p.2.claim.requiredEvidence = cl.requiredEvidence ∧
    p.2.claim.assumptions = cl.assumptions ∧ p.2.decision = cl.status ∧ p.1.decision = cl.status
  /-- the wire is bound to this certificate -/
  certificateBound : p.2.source.certificateSemanticHash = r.pkg.cert.semanticHash ∧
    p.2.source.certificateIntegrityHash = r.pkg.cert.integrityHash
  /-- semantic decision soundness (v1 kernel theorem stack) -/
  assures : ∀ L, levelOf p.2.decision = some L →
    Assures (gamma p.2) L (kernelClaim p.2) (kernelEvidence p.2)
  /-- required-evidence coverage: the wire carries exactly the required evidence ids -/
  evidenceScope : p.2.evidence.map (·.id) = p.2.claim.requiredEvidence
  /-- every evidence item is a certificate evidence item over the same predicate whose
      outcome is the fresh executor observation on the digest-bound request -/
  evidenceReplayed : ∀ ev ∈ p.2.evidence, ∃ e ∈ r.model.evidence,
    e.id = ev.id ∧ commitmentOf e.predicate = p.2.claim.predicateCommitment ∧
    ev.predicateCommitment = p.2.claim.predicateCommitment ∧
    O.exec (requestFor r.pkg.cert r.model r.table e) = ⟨ev.kind, ev.outcome⟩

theorem pcs_claims_assured {O : Oracles} {T : TrustAnchor} {inp : PackageInput}
    {r : AcceptedResult} (h : acceptPCS O T inp = some r) :
    ∀ p ∈ r.claims, ClaimAssurance O inp r p := by
  have hs := acceptPCS_sound h
  have hset := verifyNormalizedSet_sound hs.normalizedSet
  obtain ⟨_, _, _, hder⟩ := normalizedOK_spec hs.normalized
  have hrep := replayOK_spec hs.replay
  intro p hp
  obtain ⟨cl, hcl, hid, hw⟩ := hder p hp
  obtain ⟨hsh, hih, hsrc, _, hcid, hkind, hpc, hreq, hasm, hdec, hevids, hev, _⟩ :=
    deriveWire_spec hw
  obtain ⟨raw, hlk, hraw⟩ := hset.wires p hp
  have hpath : p.1.storageKey = storageKey p.1.claimId :=
    hset.pathDerived p.1 (by rw [← hset.entries]; exact List.mem_map_of_mem hp)
  refine ⟨⟨raw, hlk, hraw, hpath⟩, ⟨cl, hcl, hid, hcid, hkind, hpc, hreq, hasm, hdec, ?_⟩,
    ⟨hsh, hih⟩, fun L hL => verifyWireBytes_assures hraw hL, by rw [hevids, hreq], ?_⟩
  · rw [← hset.decisionBound p hp, hdec]
  · intro ev hev'
    obtain ⟨e, he, heid, hek, heo, hep, hevp⟩ := hev ev hev'
    refine ⟨e, he, heid, by rw [hep, hpc], by rw [hevp, hpc], ?_⟩
    rw [hrep e he, hek, heo]

/-- Exact claim scope: one normalized decision per certificate claim, in order. -/
theorem pcs_claim_scope {O : Oracles} {T : TrustAnchor} {inp : PackageInput}
    {r : AcceptedResult} (h : acceptPCS O T inp = some r) :
    r.claims.map (·.1.claimId) = claimIds r.model := by
  have hs := acceptPCS_sound h
  have hset := verifyNormalizedSet_sound hs.normalizedSet
  obtain ⟨_, _, hids, _⟩ := normalizedOK_spec hs.normalized
  rw [← hids, ← hset.entries]
  simp [Function.comp_def]

/-- Every replayed artifact is the exact delivered, manifest-signed byte string. -/
theorem pcs_artifacts_bound {O : Oracles} {T : TrustAnchor} {inp : PackageInput}
    {r : AcceptedResult} (h : acceptPCS O T inp = some r) :
    ∀ x ∈ r.table, ∃ a ∈ r.model.artifacts, ∃ fm, a.id = x.1 ∧ lookup inp.files a.path = some x.2 ∧
      sha256 x.2.data.toList = a.sha256 ∧ (a.path, fm) ∈ r.pkg.manifest.files ∧
      sha256 x.2.data.toList = fm.sha256 := by
  have hs := acceptPCS_sound h
  intro x hx
  obtain ⟨a, ha, hid, hl, hd⟩ := artifactTable_spec hs.table x hx
  obtain ⟨fm, hfm, _, hfd⟩ := fileMap_member_digest hs.package.fileMapOK (lookup_mem hl)
  exact ⟨a, ha, fm, hid, hl, hd, hfm, hfd⟩

/-! ## Layer 3: authenticity (Ed25519 (A) + (B)) -/

theorem pcs_authentic {O : Oracles} {T : TrustAnchor} {inp : PackageInput} {r : AcceptedResult}
    {Spec : Ed25519Verify} {Signed : List UInt8 → Prop}
    (h : acceptPCS O T inp = some r)
    (hA : Ed25519ImplCorrect O.ed25519 Spec) (hB : NoForgery Spec T.pk Signed) :
    Signed (signedMessage packageSignatureDomain (encodeManifest r.pkg.manifest)) ∧
    ∃ csp ms, certSigPayload r.pkg.cert = some csp ∧ csp = .obj ms ∧
      ("semantic_hash", .str (hexEncode r.pkg.cert.semanticHash)) ∈ ms ∧
      ("integrity_hash", .str (hexEncode r.pkg.cert.integrityHash)) ∈ ms ∧
      Signed (signedMessage certificateSignatureDomain csp) := by
  have hs := (acceptPCS_sound h).package
  obtain ⟨csp, hcsp, hcs⟩ := hs.certSig
  obtain ⟨ms, hms, h1, h2⟩ := certSigPayload_binds hs.cert hcsp
  exact ⟨hB _ _ ((hA _ _ _).symm.trans hs.packageSig.verified),
    csp, ms, hcsp, hms, h1, h2, hB _ _ ((hA _ _ _).symm.trans hcs.verified)⟩

/-- Under the key-holder discipline the signer intended exactly this manifest as a
    package and this certificate payload as a certificate (no domain confusion). -/
theorem pcs_intended {O : Oracles} {T : TrustAnchor} {inp : PackageInput} {r : AcceptedResult}
    {Spec : Ed25519Verify} {Signed : List UInt8 → Prop} {Intended : String → JVal → Prop}
    (h : acceptPCS O T inp = some r)
    (hA : Ed25519ImplCorrect O.ed25519 Spec) (hB : NoForgery Spec T.pk Signed)
    (hK : SignsOnlyEnvelopes Signed Intended) :
    Intended packageSignatureDomain (encodeManifest r.pkg.manifest) ∧
    ∃ csp, certSigPayload r.pkg.cert = some csp ∧ Intended certificateSignatureDomain csp := by
  obtain ⟨hp, csp, _, hcsp, _, _, _, hc⟩ := pcs_authentic h hA hB
  have open1 : ∀ d p, Signed (signedMessage d p) → Intended d p := by
    intro d p hsg
    obtain ⟨d', p', hm, hi⟩ := hK _ hsg
    obtain ⟨rfl, rfl⟩ := signaturePayloadBytes_injective (bytes_injective hm)
    exact hi
  exact ⟨open1 _ _ hp, csp, hcsp, open1 _ _ hc⟩

/-! ## Layer 4: environment (capture soundness) -/

theorem inventory_spec {m : CertModel} {files : FileMap} {inv : List InventoryItem}
    (h : inventory m files = some inv) :
    ∀ it ∈ inv, ∃ a ∈ m.artifacts, a.id = it.artifactId ∧ a.sourcePath = some it.path ∧
      lookup files a.path = some it.bytes ∧ sha256 it.bytes.data.toList = a.sha256 ∧
      it.sha256 = a.sha256 := by
  unfold inventory at h
  dsimp only at h
  split at h
  · intro it hit
    obtain ⟨asp, hasp, hit'⟩ := mapOpt_mem h it hit
    unfold inventoryItem at hit'
    split at hit'
    · rename_i b hb
      split at hit'
      · rename_i hd
        cases hit'
        unfold sourceArtifacts at hasp
        rw [List.mem_filterMap] at hasp
        obtain ⟨a, ha, hsa⟩ := hasp
        cases hsp : a.sourcePath with
        | none => rw [hsp] at hsa; cases hsa
        | some sp =>
          rw [hsp] at hsa
          cases hsa
          exact ⟨a, ha, rfl, hsp, hb, hd, rfl⟩
      · cases hit'
    · cases hit'
  · cases h

/-- Environment binding: when the certificate carries an environment contract, the
    signed declaration (minus confirmation fields) *is* the capture of the exact
    delivered, digest-checked source bytes. -/
theorem pcs_environment_bound {O : Oracles} {T : TrustAnchor} {inp : PackageInput}
    {r : AcceptedResult} (h : acceptPCS O T inp = some r) {eb : EnvBinding}
    {inv : List InventoryItem} (he : r.env = some (eb, inv)) :
    envProjection eb.signed = O.capture inv ∧
    boolField eb.signed "human_confirmed" = some true ∧
    boolField eb.signed "static_only" = some true ∧
    boolField eb.signed "network_accessed" = some false ∧
    boolField eb.signed "user_code_executed" = some false ∧
    (∀ it ∈ inv, ∃ a ∈ r.model.artifacts, a.id = it.artifactId ∧ a.sourcePath = some it.path ∧
      lookup inp.files a.path = some it.bytes ∧ sha256 it.bytes.data.toList = a.sha256) := by
  have hs := acceptPCS_sound h
  have henv := hs.env
  rw [he] at henv
  unfold envStage at henv
  split at henv
  · cases henv
  · cases henv
  · rename_i b _
    split at henv
    · rename_i eb' inv' heb hinv
      split at henv
      · rename_i hc
        cases henv
        unfold decodeEnvBinding at heb
        simp only [bind, Option.bind_eq_some_iff, pure] at heb
        obtain ⟨ct, _, prop, _, sv, _, ids, _, sids, _, heb⟩ := heb
        split at heb
        · rename_i hflags
          cases heb
          refine ⟨ser_injective hc.2.1, hflags.2.2.2.2.1, hflags.2.2.2.2.2.1,
            hflags.2.2.2.2.2.2.1, hflags.2.2.2.2.2.2.2.1, ?_⟩
          intro it hit
          obtain ⟨a, ha, h1, h2, h3, h4, _⟩ := inventory_spec hinv it hit
          exact ⟨a, ha, h1, h2, h3, h4⟩
        · cases heb
      · cases henv
    · cases henv
  · cases henv

/-- External meaning of a static environment description (e.g. "these sources declare
    exactly these dependency pins / interpreter constraints / container base image"). -/
def CaptureSound (capture : CaptureFn) (Describes : List InventoryItem → JVal → Prop) : Prop :=
  ∀ inv, Describes inv (capture inv)

theorem pcs_environment_described {O : Oracles} {T : TrustAnchor} {inp : PackageInput}
    {r : AcceptedResult} {Describes : List InventoryItem → JVal → Prop}
    (h : acceptPCS O T inp = some r) (hC : CaptureSound O.capture Describes)
    {eb : EnvBinding} {inv : List InventoryItem} (he : r.env = some (eb, inv)) :
    Describes inv (envProjection eb.signed) := by
  rw [(pcs_environment_bound h he).1]
  exact hC inv

/-! ## Layer 5: replay faithfulness -/

/-- The executor never reports PASS unless the check's scientific predicate `Holds`
    on the exact request (evidence object + artifact bytes). -/
def ReplayFaithful (exec : Executor) (Holds : ReplayRequest → Prop) : Prop :=
  ∀ req, (exec req).outcome = .pass → Holds req

theorem pcs_evidence_holds {O : Oracles} {T : TrustAnchor} {inp : PackageInput}
    {r : AcceptedResult} {Holds : ReplayRequest → Prop}
    (h : acceptPCS O T inp = some r) (hR : ReplayFaithful O.exec Holds) :
    ∀ p ∈ r.claims, ∀ ev ∈ p.2.evidence, ev.outcome = .pass →
      ∃ e ∈ r.model.evidence, e.id = ev.id ∧ Holds (requestFor r.pkg.cert r.model r.table e) := by
  intro p hp ev hev hpass
  obtain ⟨e, he, hid, _, _, hobs⟩ := (pcs_claims_assured h p hp).evidenceReplayed ev hev
  refine ⟨e, he, hid, hR _ ?_⟩
  rw [hobs, hpass]

/-! ## Layer 6: the flagship theorem -/

/-- Every external contract, each narrow and named. -/
structure ExternalContracts (O : Oracles) (T : TrustAnchor) where
  ed25519Spec : Ed25519Verify
  signed : List UInt8 → Prop
  ed25519ImplCorrect : Ed25519ImplCorrect O.ed25519 ed25519Spec
  noForgery : NoForgery ed25519Spec T.pk signed
  describes : List InventoryItem → JVal → Prop
  captureSound : CaptureSound O.capture describes
  holds : ReplayRequest → Prop
  replayFaithful : ReplayFaithful O.exec holds

/-- The substantive content of PCS acceptance. -/
structure ScientificAssurance (O : Oracles) (T : TrustAnchor) (K : ExternalContracts O T)
    (inp : PackageInput) (r : AcceptedResult) : Prop where
  structural : StructuralAssurance O T inp r
  /-- canonical, non-malleable control records -/
  certificateCanonical : inp.certificateBytes = jcsBytes (.obj r.pkg.cert.members)
  manifestCanonical : inp.manifestBytes = jcsBytes (encodeManifest r.pkg.manifest)
  /-- exact signed member set with exact digests -/
  memberSetExact : ∀ n, n ∈ fileNames inp.files ↔ n ∈ manifestNames r.pkg.manifest
  memberDigests : ∀ n b, (n, b) ∈ inp.files → ∃ fm, (n, fm) ∈ r.pkg.manifest.files ∧
    b.size = fm.size ∧ sha256 b.data.toList = fm.sha256
  manifestBindsCertificate : r.pkg.manifest.certSemanticHash = r.pkg.cert.semanticHash ∧
    r.pkg.manifest.certIntegrityHash = r.pkg.cert.integrityHash
  /-- exact claim scope -/
  claimScope : r.claims.map (·.1.claimId) = claimIds r.model
  /-- per-claim assurance -/
  claims : ∀ p ∈ r.claims, ClaimAssurance O inp r p
  /-- authenticity (A)+(B) -/
  authentic : K.signed (signedMessage packageSignatureDomain (encodeManifest r.pkg.manifest)) ∧
    ∃ csp, certSigPayload r.pkg.cert = some csp ∧
      K.signed (signedMessage certificateSignatureDomain csp)
  /-- environment declaration = capture of delivered sources, and its meaning -/
  environment : ∀ eb inv, r.env = some (eb, inv) →
    envProjection eb.signed = O.capture inv ∧ K.describes inv (envProjection eb.signed)
  /-- every passing evidence item's scientific check holds on the committed bytes -/
  evidenceHolds : ∀ p ∈ r.claims, ∀ ev ∈ p.2.evidence, ev.outcome = .pass →
    ∃ e ∈ r.model.evidence, e.id = ev.id ∧ K.holds (requestFor r.pkg.cert r.model r.table e)

theorem pcs_accept_implies_scientific_assurance {O : Oracles} {T : TrustAnchor}
    (K : ExternalContracts O T) {inp : PackageInput} {r : AcceptedResult}
    (h : acceptPCS O T inp = some r) : ScientificAssurance O T K inp r := by
  have hs := acceptPCS_sound h
  obtain ⟨ha, csp, _, hcsp, _, _, _, hc⟩ := pcs_authentic h K.ed25519ImplCorrect K.noForgery
  refine ⟨hs, hs.package.cert.bytes, hs.package.manifest.bytes,
    fileMap_exact_names hs.package.fileMapOK, ?_, ⟨hs.package.fileMap.certSemantic,
    hs.package.fileMap.certIntegrity⟩, pcs_claim_scope h, pcs_claims_assured h, ⟨ha, csp, hcsp, hc⟩,
    ?_, pcs_evidence_holds h K.replayFaithful⟩
  · intro n b hb
    exact fileMap_member_digest hs.package.fileMapOK hb
  · intro eb inv he
    exact ⟨(pcs_environment_bound h he).1, pcs_environment_described h K.captureSound he⟩

/-- The flagship from the raw archive bytes, with the ZIP decoder as the only additional
    oracle. -/
theorem pcs_archive_accept_implies_scientific_assurance {O : Oracles} {zip : ZipDecoder}
    {T : TrustAnchor} (K : ExternalContracts O T) {raw : ByteArray} {inp : PackageInput}
    {r : AcceptedResult} (h : acceptArchive O zip T raw = some (inp, r)) :
    (∃ entries, zip raw = some entries ∧ fromArchiveEntries entries = some inp) ∧
    ScientificAssurance O T K inp r := by
  unfold acceptArchive at h
  split at h
  · cases h
  · rename_i entries he
    split at h
    · cases h
    · rename_i inp' hinp
      cases hr : acceptPCS O T inp' with
      | none => rw [hr] at h; cases h
      | some r' =>
        rw [hr] at h
        simp only [Option.map_some, Option.some.injEq, Prod.mk.injEq] at h
        obtain ⟨rfl, rfl⟩ := h
        exact ⟨⟨entries, he, hinp⟩, pcs_accept_implies_scientific_assurance K hr⟩

end PCS.V2.Flagship
