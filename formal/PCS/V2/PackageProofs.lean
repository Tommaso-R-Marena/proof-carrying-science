import PCS.V2.Package
import PCS.V2.IndexProofs

/-!
# Soundness of the v0.6 package checkers

* `verifyCertBytes_sound`      : canonical certificate bytes with recomputed
  semantic/integrity hashes over the exact production projections;
* `verifyManifestBytes_sound`  : canonical manifest bytes, typed decoding, portable namespace;
* `fileMapOK_sound`            : exact member set, exact sizes, exact SHA-256 digests,
  certificate member byte-identical, manifest ↔ certificate hash binding;
* `verifyPackage_sound`        : the conjunction, plus both signature records;
* `member_bytes_binding`       : two deliveries accepted for the same manifest entry
  carry identical bytes or exhibit a SHA-256 collision;
* `package_authentic`          : under (A)+(B) only, the key holder signed exactly
  this manifest (hence every member digest) and exactly this certificate payload.
-/

namespace PCS.V2.Package

open PCS.V2.Json PCS.V2.Hex PCS.V2.SHA256 PCS.V2.Domains PCS.V2.Canonical PCS.V2.Common
open PCS.V2.Signature PCS.V2.Index

/-! ## Certificate -/

theorem digestField_sound {ms : List (String × JVal)} {k : String} {d : List UInt8}
    (h : digestField ms k = some d) : field ms k = some (.str (hexEncode d)) ∧ d.length = 32 := by
  unfold digestField at h
  split at h
  · rename_i s hs
    obtain ⟨he, hl⟩ := decDigest_sound h
    exact ⟨he ▸ hs, hl⟩
  · cases h

structure CertAccepted (raw : ByteArray) (c : CertV2) : Prop where
  bytes : raw = jcsBytes (.obj c.members)
  canonical : canonical (.obj c.members) = true
  size : raw.size ≤ maxCertificateBytes
  semanticField : field c.members "semantic_hash" = some (.str (hexEncode c.semanticHash))
  integrityField : field c.members "integrity_hash" = some (.str (hexEncode c.integrityHash))
  semanticHash : c.semanticHash = domainDigest certificateSemanticDomain (semanticProjection c.members)
  integrityHash : c.integrityHash = domainDigest certificateIntegrityDomain (integrityProjection c.members)
  specVersion : strField c.members "spec_version" = some certSpecVersion
  semanticFormat : strField c.members "semantic_hash_format" = some certificateSemanticDomain
  integrityFormat : strField c.members "integrity_hash_format" = some certificateIntegrityDomain

theorem verifyCertBytes_sound {raw : ByteArray} {c : CertV2} (h : verifyCertBytes raw = some c) :
    CertAccepted raw c := by
  unfold verifyCertBytes at h
  split at h
  · rename_i ms hms
    split at h
    · rename_i sh ih hsh hih
      dsimp only at h
      split at h
      · rename_i hok
        cases h
        obtain ⟨hraw, hcan, hsz⟩ := parseCanonicalBytes_sound hms
        simp only [certHashesOK, Bool.and_eq_true, beq_iff_eq] at hok
        obtain ⟨⟨⟨⟨⟨h1, _⟩, h3⟩, h4⟩, h5⟩, h6⟩ := hok
        exact ⟨hraw, hcan, hsz, (digestField_sound hsh).1, (digestField_sound hih).1, h5, h6,
          h1, h3, h4⟩
      · cases h
    · cases h
  · cases h

/-- The certificate semantic hash binds the semantic projection (up to collision). -/
theorem cert_semantic_binding {r₁ r₂ : ByteArray} {c₁ c₂ : CertV2}
    (h₁ : verifyCertBytes r₁ = some c₁) (h₂ : verifyCertBytes r₂ = some c₂)
    (he : c₁.semanticHash = c₂.semanticHash) :
    semanticProjection c₁.members = semanticProjection c₂.members ∨ Sha256Collision := by
  have a := verifyCertBytes_sound h₁
  have b := verifyCertBytes_sound h₂
  rw [a.semanticHash, b.semanticHash] at he
  rcases digest_binding he with ⟨_, hp⟩ | hc
  · exact Or.inl hp
  · exact Or.inr hc

/-- The certificate integrity hash binds everything except itself (up to collision). -/
theorem cert_integrity_binding {r₁ r₂ : ByteArray} {c₁ c₂ : CertV2}
    (h₁ : verifyCertBytes r₁ = some c₁) (h₂ : verifyCertBytes r₂ = some c₂)
    (he : c₁.integrityHash = c₂.integrityHash) :
    integrityProjection c₁.members = integrityProjection c₂.members ∨ Sha256Collision := by
  have a := verifyCertBytes_sound h₁
  have b := verifyCertBytes_sound h₂
  rw [a.integrityHash, b.integrityHash] at he
  rcases digest_binding he with ⟨_, hp⟩ | hc
  · exact Or.inl hp
  · exact Or.inr hc

/-- Certificate semantic and integrity digests live in different domains: one can
    stand in for the other only through a SHA-256 collision. -/
theorem cert_semantic_not_integrity {r₁ r₂ : ByteArray} {c₁ c₂ : CertV2}
    (h₁ : verifyCertBytes r₁ = some c₁) (h₂ : verifyCertBytes r₂ = some c₂)
    (he : c₁.semanticHash = c₂.integrityHash) : Sha256Collision := by
  have a := verifyCertBytes_sound h₁
  have b := verifyCertBytes_sound h₂
  rw [a.semanticHash, b.integrityHash] at he
  exact cross_domain_digest_collision (by decide) he

/-! ## Manifest -/

theorem decodeMeta_sound {v : JVal} {m : FileMeta} (h : decodeMeta v = some m) :
    encodeMeta m = v ∧ m.sha256.length = 32 := by
  unfold decodeMeta at h
  split at h
  · split at h
    · rename_i hk
      obtain ⟨rfl, rfl, hn⟩ := hk
      cases hd : decDigest _ with
      | none => rw [hd] at h; cases h
      | some d =>
        rw [hd] at h
        cases h
        obtain ⟨he, hl⟩ := decDigest_sound hd
        refine ⟨?_, hl⟩
        simp [encodeMeta, he, Int.toNat_of_nonneg hn]
    · cases h
  · cases h

theorem decodeFile_sound {kv : String × JVal} {nf : String × FileMeta} (h : decodeFile kv = some nf) :
    (nf.1, encodeMeta nf.2) = kv ∧ nf.2.sha256.length = 32 := by
  unfold decodeFile at h
  cases hm : decodeMeta kv.2 with
  | none => rw [hm] at h; cases h
  | some m =>
    rw [hm] at h
    cases h
    obtain ⟨he, hl⟩ := decodeMeta_sound hm
    exact ⟨by rw [he], hl⟩

theorem mapOpt_decodeFile_lengths :
    ∀ {fs : List (String × JVal)} {fs' : List (String × FileMeta)},
    mapOpt decodeFile fs = some fs' → ∀ nf ∈ fs', nf.2.sha256.length = 32
  | [], fs', h => by simp [mapOpt] at h; subst h; intro _ h; cases h
  | x :: xs, fs', h => by
    simp only [mapOpt] at h
    split at h
    · rename_i y ys hy hys
      cases h
      intro nf hnf
      simp only [List.mem_cons] at hnf
      rcases hnf with rfl | hnf
      · exact (decodeFile_sound hy).2
      · exact mapOpt_decodeFile_lengths hys nf hnf
    · cases h

theorem decodeManifest_sound {v : JVal} {m : ManifestV2} (h : decodeManifest v = some m) :
    encodeManifest m = v ∧ m.certSemanticHash.length = 32 ∧ m.certIntegrityHash.length = 32 ∧
      ∀ nf ∈ m.files, nf.2.sha256.length = 32 := by
  unfold decodeManifest at h
  split at h
  · split at h
    · rename_i hk
      obtain ⟨rfl, rfl, rfl, rfl, rfl, rfl, rfl, rfl, rfl, rfl, rfl, rfl, rfl⟩ := hk
      split at h
      · rename_i ih' sh' fs' hih hsh hfs
        cases h
        obtain ⟨h1, h1l⟩ := decDigest_sound hih
        obtain ⟨h2, h2l⟩ := decDigest_sound hsh
        have hf := mapOpt_inv (g := fun nf => (nf.1, encodeMeta nf.2))
          (fun x y hxy => (decodeFile_sound hxy).1) hfs
        refine ⟨?_, h2l, h1l, mapOpt_decodeFile_lengths hfs⟩
        simp [encodeManifest, h1, h2, hf]
      · cases h
    · cases h
  · cases h

structure ManifestAccepted (U : UnicodeOps) (raw : ByteArray) (m : ManifestV2) : Prop where
  bytes : raw = jcsBytes (encodeManifest m)
  canonical : canonical (encodeManifest m) = true
  size : raw.size ≤ maxManifestBytes
  hashLengths : m.certSemanticHash.length = 32 ∧ m.certIntegrityHash.length = 32
  digestLengths : ∀ nf ∈ m.files, nf.2.sha256.length = 32
  namespace_ : namespaceOK U (manifestNames m) = true
  bindsCertificate : certificateMember ∈ manifestNames m

theorem verifyManifestBytes_sound {U : UnicodeOps} {raw : ByteArray} {m : ManifestV2}
    (h : verifyManifestBytes U raw = some m) : ManifestAccepted U raw m := by
  unfold verifyManifestBytes at h
  split at h
  · cases h
  · rename_i v hv
    split at h
    · rename_i m' hm
      split at h
      · rename_i hok
        cases h
        obtain ⟨hraw, hcan, hsz⟩ := parseCanonicalBytes_sound hv
        obtain ⟨henc, hl1, hl2, hl3⟩ := decodeManifest_sound hm
        subst henc
        simp only [manifestOK, Bool.and_eq_true] at hok
        exact ⟨hraw, hcan, hsz, ⟨hl1, hl2⟩, hl3, hok.1, List.contains_iff_mem.mp hok.2⟩
      · cases h
    · cases h

/-- One typed manifest has one accepted byte string. -/
theorem verifyManifestBytes_nonmalleable {U : UnicodeOps} {r₁ r₂ : ByteArray} {m : ManifestV2}
    (h₁ : verifyManifestBytes U r₁ = some m) (h₂ : verifyManifestBytes U r₂ = some m) : r₁ = r₂ :=
  (verifyManifestBytes_sound h₁).bytes.trans (verifyManifestBytes_sound h₂).bytes.symm

/-! ## Exact file-map binding -/

structure FileMapAccepted (U : UnicodeOps) (m : ManifestV2) (c : CertV2) (certBytes : ByteArray)
    (files : FileMap) : Prop where
  namespace_ : namespaceOK U (fileNames files) = true
  noUnsigned : ∀ n ∈ fileNames files, n ∈ manifestNames m
  members : ∀ nf ∈ m.files, ∃ b, lookup files nf.1 = some b ∧ b.size = nf.2.size ∧
    sha256 b.data.toList = nf.2.sha256 ∧ b.size ≤ maxSingleFile
  count : files.length ≤ maxPackageFiles
  total : totalBytes files ≤ maxTotalBytes
  certificateMember : lookup files certificateMember = some certBytes
  certSemantic : m.certSemanticHash = c.semanticHash
  certIntegrity : m.certIntegrityHash = c.integrityHash

theorem memberOK_sound {files : FileMap} {nf : String × FileMeta} (h : memberOK files nf = true) :
    ∃ b, lookup files nf.1 = some b ∧ b.size = nf.2.size ∧ sha256 b.data.toList = nf.2.sha256 ∧
      b.size ≤ maxSingleFile := by
  unfold memberOK at h
  split at h
  · rename_i b hb
    simp only [Bool.and_eq_true, beq_iff_eq, decide_eq_true_eq] at h
    exact ⟨b, hb, h.1.1, h.1.2, h.2⟩
  · cases h

theorem fileMapOK_sound {U : UnicodeOps} {m : ManifestV2} {c : CertV2} {certBytes : ByteArray}
    {files : FileMap} (h : fileMapOK U m c certBytes files = true) :
    FileMapAccepted U m c certBytes files := by
  simp only [fileMapOK, Bool.and_eq_true, List.all_eq_true, decide_eq_true_eq, beq_iff_eq] at h
  obtain ⟨⟨⟨⟨⟨⟨⟨h1, h2⟩, h3⟩, h4⟩, h5⟩, h6⟩, h7⟩, h8⟩ := h
  exact ⟨h1, fun n hn => List.contains_iff_mem.mp (h2 n hn), fun nf hnf => memberOK_sound (h3 nf hnf),
    h4, h5, h6, h7, h8⟩

/-- The delivered member set is exactly the signed member set. -/
theorem fileMap_exact_names {U : UnicodeOps} {m : ManifestV2} {c : CertV2} {certBytes : ByteArray}
    {files : FileMap} (h : fileMapOK U m c certBytes files = true) (n : String) :
    n ∈ fileNames files ↔ n ∈ manifestNames m := by
  have hs := fileMapOK_sound h
  constructor
  · exact hs.noUnsigned n
  · intro hn
    simp only [manifestNames, List.mem_map] at hn
    obtain ⟨nf, hnf, rfl⟩ := hn
    obtain ⟨b, hb, _⟩ := hs.members nf hnf
    simp only [fileNames, List.mem_map]
    exact ⟨_, lookup_mem hb, rfl⟩

/-- Every delivered member is the unique byte string under its (unique) name, with the
    signed size and SHA-256 digest. -/
theorem fileMap_member_digest {U : UnicodeOps} {m : ManifestV2} {c : CertV2}
    {certBytes : ByteArray} {files : FileMap} (h : fileMapOK U m c certBytes files = true)
    {n : String} {b : ByteArray} (hb : (n, b) ∈ files) :
    ∃ fm, (n, fm) ∈ m.files ∧ b.size = fm.size ∧ sha256 b.data.toList = fm.sha256 := by
  have hs := fileMapOK_sound h
  have hn : n ∈ manifestNames m := hs.noUnsigned n (by simp only [fileNames, List.mem_map]; exact ⟨_, hb, rfl⟩)
  simp only [manifestNames, List.mem_map] at hn
  obtain ⟨nf, hnf, hname⟩ := hn
  obtain ⟨b', hb', hsz, hdig, _⟩ := hs.members nf hnf
  have hnd := namespaceOK_nodup hs.namespace_
  rw [hname] at hb'
  have := lookup_unique hnd hb' hb
  subst this
  exact ⟨nf.2, by rw [← hname]; exact hnf, hsz, hdig⟩

/-- Member binding: two file maps accepted against manifests that agree on a member's
    digest deliver identical bytes for that member, or a SHA-256 collision exists. -/
theorem member_bytes_binding {U₁ U₂ : UnicodeOps} {m₁ m₂ : ManifestV2} {c₁ c₂ : CertV2}
    {cb₁ cb₂ : ByteArray} {f₁ f₂ : FileMap}
    (h₁ : fileMapOK U₁ m₁ c₁ cb₁ f₁ = true) (h₂ : fileMapOK U₂ m₂ c₂ cb₂ f₂ = true)
    {n : String} {b₁ b₂ : ByteArray} (hb₁ : (n, b₁) ∈ f₁) (hb₂ : (n, b₂) ∈ f₂)
    (hagree : ∀ fm₁ fm₂, (n, fm₁) ∈ m₁.files → (n, fm₂) ∈ m₂.files →
      fm₁.sha256 = fm₂.sha256) :
    b₁ = b₂ ∨ Sha256Collision := by
  obtain ⟨mt₁, hm₁, _, hd₁⟩ := fileMap_member_digest h₁ hb₁
  obtain ⟨mt₂, hm₂, _, hd₂⟩ := fileMap_member_digest h₂ hb₂
  have he : sha256 b₁.data.toList = sha256 b₂.data.toList := by
    rw [hd₁, hd₂]; exact hagree _ _ hm₁ hm₂
  by_cases hl : b₁.data.toList = b₂.data.toList
  · exact Or.inl (bytes_injective hl)
  · exact Or.inr ⟨_, _, hl, he⟩

/-- The certificate member is byte-identical to the verified certificate bytes and its
    SHA-256 is the digest recorded in the manifest. -/
theorem certificate_member_bound {U : UnicodeOps} {m : ManifestV2} {c : CertV2}
    {certBytes : ByteArray} {files : FileMap} (h : fileMapOK U m c certBytes files = true) :
    ∃ fm, (certificateMember, fm) ∈ m.files ∧ certBytes.size = fm.size ∧
      sha256 certBytes.data.toList = fm.sha256 :=
  fileMap_member_digest h (lookup_mem (fileMapOK_sound h).certificateMember)

/-! ## The signed package -/

structure PackageAccepted (U : UnicodeOps) (V : Ed25519Verify) (pk : List UInt8)
    (expected : Option (List UInt8)) (inp : PackageInput) (r : PackageResult) : Prop where
  cert : CertAccepted inp.certificateBytes r.cert
  certSig : ∃ csp, PCS.V2.Package.certSigPayload r.cert = some csp ∧
    SigAccepted V pk expected certificateSignatureDomain csp inp.certificateSignatureBytes
      r.certSignature
  manifest : ManifestAccepted U inp.manifestBytes r.manifest
  fileMap : FileMapAccepted U r.manifest r.cert inp.certificateBytes inp.files
  fileMapOK : fileMapOK U r.manifest r.cert inp.certificateBytes inp.files = true
  packageSig : SigAccepted V pk expected packageSignatureDomain (encodeManifest r.manifest)
    inp.packageSignatureBytes r.packageSignature

theorem verifyPackage_sound {U : UnicodeOps} {V : Ed25519Verify} {pk : List UInt8}
    {expected : Option (List UInt8)} {inp : PackageInput} {r : PackageResult}
    (h : verifyPackage U V pk expected inp = some r) : PackageAccepted U V pk expected inp r := by
  unfold verifyPackage at h
  split at h
  · cases h
  · rename_i c hc
    split at h
    · cases h
    · rename_i csp hcsp
      split at h
      · cases h
      · rename_i cs hcs
        split at h
        · cases h
        · rename_i m hm
          split at h
          · rename_i hf
            split at h
            · cases h
            · rename_i ps hps
              cases h
              exact ⟨verifyCertBytes_sound hc, ⟨csp, hcsp, verifySigRecordBytes_sound hcs⟩,
                verifyManifestBytes_sound hm, fileMapOK_sound hf, hf, verifySigRecordBytes_sound hps⟩
          · cases h

/-- Authenticity of the package under (A)+(B): the key holder signed exactly the
    manifest (which carries every member digest and the certificate hashes) and
    exactly the certificate signature payload. -/
theorem package_authentic {U : UnicodeOps} {V Spec : Ed25519Verify} {pk : List UInt8}
    {expected : Option (List UInt8)} {inp : PackageInput} {r : PackageResult}
    {Signed : List UInt8 → Prop}
    (h : verifyPackage U V pk expected inp = some r)
    (hA : Ed25519ImplCorrect V Spec) (hB : NoForgery Spec pk Signed) :
    Signed (signedMessage packageSignatureDomain (encodeManifest r.manifest)) ∧
    ∃ csp, certSigPayload r.cert = some csp ∧ Signed (signedMessage certificateSignatureDomain csp) := by
  have hs := verifyPackage_sound h
  obtain ⟨csp, hcsp, hcs⟩ := hs.certSig
  refine ⟨hB _ r.packageSignature.signature ((hA _ _ _).symm.trans hs.packageSig.verified),
    csp, hcsp, hB _ r.certSignature.signature ((hA _ _ _).symm.trans hcs.verified)⟩

/-- Intent under (A)+(B)+key discipline: the signer intended this exact manifest as a
    package and this exact certificate payload as a certificate. -/
theorem package_intended {U : UnicodeOps} {V Spec : Ed25519Verify} {pk : List UInt8}
    {expected : Option (List UInt8)} {inp : PackageInput} {r : PackageResult}
    {Signed : List UInt8 → Prop} {Intended : String → JVal → Prop}
    (h : verifyPackage U V pk expected inp = some r)
    (hA : Ed25519ImplCorrect V Spec) (hB : NoForgery Spec pk Signed)
    (hK : SignsOnlyEnvelopes Signed Intended) :
    Intended packageSignatureDomain (encodeManifest r.manifest) ∧
    ∃ csp, certSigPayload r.cert = some csp ∧ Intended certificateSignatureDomain csp := by
  have hs := verifyPackage_sound h
  obtain ⟨csp, hcsp, hcs⟩ := hs.certSig
  have i1 : Intended packageSignatureDomain (encodeManifest r.manifest) := by
    obtain ⟨d', p', hm, hi⟩ := hK _ (hB _ _ ((hA _ _ _).symm.trans hs.packageSig.verified))
    obtain ⟨rfl, rfl⟩ := signaturePayloadBytes_injective (bytes_injective hm)
    exact hi
  exact ⟨i1, csp, hcsp, by
    obtain ⟨d', p', hm, hi⟩ := hK _ (hB _ _ ((hA _ _ _).symm.trans hcs.verified))
    obtain ⟨rfl, rfl⟩ := signaturePayloadBytes_injective (bytes_injective hm)
    exact hi⟩

end PCS.V2.Package
