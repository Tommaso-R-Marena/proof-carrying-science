import PCS.V2.Flagship

/-!
# Reproducibility, freshness and anti-substitution

* Commitments determine the replay requests: two accepted packages whose
  certificates have the same semantic hash have the same typed certificate model,
  and (unless SHA-256 collides) the same artifact bytes, hence identical replay
  requests (`same_commitment_same_requests`).
* Determinism modulo an explicit runtime-equivalence relation makes the replay stage
  — and therefore the whole verdict — reproducible (`acceptance_reproducible`).
* Reproducibility notions are separated: raw-output (byte) reproducibility implies
  normalized-observation reproducibility, never conversely
  (`byte_repro_implies_normalized`, `normalized_not_byte`).
* Anti-substitution: a normalized decision accepted in one package can be accepted in
  another only if both certificates have identical hashes (`wire_reuse_same_certificate`);
  replay requests are injective in (certificate, evidence object, artifact bytes).
-/

namespace PCS.V2.Reproducibility

open PCS PCS.Decision PCS.V2.Json PCS.V2.Hex PCS.V2.SHA256 PCS.V2.Domains PCS.V2.Canonical
open PCS.V2.Common PCS.V2.NormalizedWire PCS.V2.Index PCS.V2.Package PCS.V2.CertificateModel
open PCS.V2.Signature PCS.V2.Replay PCS.V2.EndToEnd PCS.V2.Flagship

/-! ## Field access through projections -/

theorem field_filter {ms : List (String × JVal)} {keep : String → Bool} {k : String}
    (hk : keep k = true) : field (ms.filter (fun kv => keep kv.1)) k = field ms k := by
  induction ms with
  | nil => rfl
  | cons x xs ih =>
    obtain ⟨k', v⟩ := x
    unfold field at ih ⊢
    by_cases hkk : k' = k
    · subst hkk
      rw [List.filter_cons]
      simp only [hk, if_true, List.find?_cons, beq_self_eq_true]
    · have hb : (k' == k) = false := by simpa using hkk
      rw [List.filter_cons]
      cases hkeep : keep k'
      · simp only [Bool.false_eq_true, if_false]
        rw [ih, List.find?_cons, hb]
      · simp only [if_true]
        rw [List.find?_cons, List.find?_cons, hb]
        exact ih

def semanticKeep (k : String) : Bool := !(["generated_at", "semantic_hash", "integrity_hash"].contains k)

theorem semanticProjection_eq (ms : List (String × JVal)) :
    semanticProjection ms = .obj (ms.filter (fun kv => semanticKeep kv.1)) := rfl

theorem field_of_semantic_eq {ms₁ ms₂ : List (String × JVal)}
    (h : semanticProjection ms₁ = semanticProjection ms₂) {k : String} (hk : semanticKeep k = true) :
    field ms₁ k = field ms₂ k := by
  rw [semanticProjection_eq, semanticProjection_eq] at h
  simp only [JVal.obj.injEq] at h
  rw [← field_filter (ms := ms₁) hk, ← field_filter (ms := ms₂) hk, h]

theorem strField_congr {ms₁ ms₂ : List (String × JVal)} {k : String} (h : field ms₁ k = field ms₂ k) :
    strField ms₁ k = strField ms₂ k := by
  unfold strField; rw [h]

/-- The typed certificate model only reads semantically hashed fields. -/
theorem decodeCertModel_congr {c₁ c₂ : CertV2}
    (h : semanticProjection c₁.members = semanticProjection c₂.members) :
    decodeCertModel c₁ = decodeCertModel c₂ := by
  have f : ∀ k, semanticKeep k = true → field c₁.members k = field c₂.members k :=
    fun k hk => field_of_semantic_eq h hk
  unfold decodeCertModel
  rw [strField_congr (f "checker_version" rfl), f "claims" rfl, f "evidence" rfl,
    f "assumptions" rfl, f "artifacts" rfl]

/-! ## Commitments determine replay requests -/

theorem artifactEntries_binding {f₁ f₂ : FileMap} :
    ∀ {as : List CertArtifact} {t₁ t₂ : List (String × ByteArray)},
    mapOpt (artifactEntry f₁) as = some t₁ → mapOpt (artifactEntry f₂) as = some t₂ →
    t₁ = t₂ ∨ Sha256Collision
  | [], t₁, t₂, h₁, h₂ => by simp [mapOpt] at h₁ h₂; subst h₁ h₂; exact Or.inl rfl
  | a :: as, t₁, t₂, h₁, h₂ => by
    simp only [mapOpt] at h₁ h₂
    split at h₁
    · rename_i y₁ ys₁ hy₁ hys₁
      split at h₂
      · rename_i y₂ ys₂ hy₂ hys₂
        cases h₁; cases h₂
        rcases artifactEntries_binding hys₁ hys₂ with e | c
        · subst e
          unfold artifactEntry at hy₁ hy₂
          split at hy₁
          · split at hy₁
            · rename_i b₁ _ hc₁
              cases hy₁
              split at hy₂
              · split at hy₂
                · rename_i b₂ _ hc₂
                  cases hy₂
                  by_cases hb : b₁.data.toList = b₂.data.toList
                  · rw [bytes_injective hb]; exact Or.inl rfl
                  · exact Or.inr ⟨_, _, hb, hc₁.1.trans hc₂.1.symm⟩
                · cases hy₂
              · cases hy₂
            · cases hy₁
          · cases hy₁
        · exact Or.inr c
      · cases h₂
    · cases h₁

theorem artifactTable_binding {m : CertModel} {f₁ f₂ : FileMap} {t₁ t₂ : List (String × ByteArray)}
    (h₁ : artifactTable m f₁ = some t₁) (h₂ : artifactTable m f₂ = some t₂) :
    t₁ = t₂ ∨ Sha256Collision :=
  artifactEntries_binding h₁ h₂

theorem semantic_binding_of_accepted {r₁ r₂ : ByteArray} {c₁ c₂ : CertV2}
    (a : CertAccepted r₁ c₁) (b : CertAccepted r₂ c₂) (he : c₁.semanticHash = c₂.semanticHash) :
    semanticProjection c₁.members = semanticProjection c₂.members ∨ Sha256Collision := by
  rw [a.semanticHash, b.semanticHash] at he
  rcases digest_binding he with ⟨_, hp⟩ | hc
  · exact Or.inl hp
  · exact Or.inr hc

theorem integrity_binding_of_accepted {r₁ r₂ : ByteArray} {c₁ c₂ : CertV2}
    (a : CertAccepted r₁ c₁) (b : CertAccepted r₂ c₂) (he : c₁.integrityHash = c₂.integrityHash) :
    integrityProjection c₁.members = integrityProjection c₂.members ∨ Sha256Collision := by
  rw [a.integrityHash, b.integrityHash] at he
  rcases digest_binding he with ⟨_, hp⟩ | hc
  · exact Or.inl hp
  · exact Or.inr hc

/-- Same certificate semantic hash ⇒ same typed model and (absent a SHA-256 collision)
    identical replay requests for every evidence item. -/
theorem same_commitment_same_requests {O₁ O₂ : Oracles} {T₁ T₂ : TrustAnchor}
    {inp₁ inp₂ : PackageInput} {r₁ r₂ : AcceptedResult}
    (h₁ : acceptPCS O₁ T₁ inp₁ = some r₁) (h₂ : acceptPCS O₂ T₂ inp₂ = some r₂)
    (hs : r₁.pkg.cert.semanticHash = r₂.pkg.cert.semanticHash) :
    (r₁.model = r₂.model ∧ r₁.table = r₂.table ∧
      ∀ e ∈ r₁.model.evidence, requestFor r₁.pkg.cert r₁.model r₁.table e =
        requestFor r₂.pkg.cert r₂.model r₂.table e) ∨ Sha256Collision := by
  have a := acceptPCS_sound h₁
  have b := acceptPCS_sound h₂
  rcases semantic_binding_of_accepted a.package.cert b.package.cert hs with hp | c
  · have hm : r₁.model = r₂.model := by
      have := decodeCertModel_congr hp
      rw [a.model, b.model] at this
      exact Option.some.inj this
    have ht₂ := b.table
    rw [← hm] at ht₂
    rcases artifactTable_binding a.table ht₂ with ht | c
    · refine Or.inl ⟨hm, ht, fun e _ => ?_⟩
      simp only [requestFor, hs, hm, ht]
    · exact Or.inr c
  · exact Or.inr c

/-! ## Determinism modulo an explicit runtime equivalence -/

/-- A replay executor that may depend on an uncontrolled runtime `ρ`
    (OS, interpreter, container engine, clock, locale, RNG state, ...). -/
abbrev RuntimeExecutor (ρ : Type) := ReplayRequest → ρ → Observation

/-- Determinism modulo `Equiv`: equivalent runtimes give identical observations. -/
def DeterministicModulo {ρ : Type} (run : RuntimeExecutor ρ) (Equiv : ρ → ρ → Prop) : Prop :=
  ∀ req x y, Equiv x y → run req x = run req y

/-- Reproducibility of the verdict: if the executor is deterministic modulo `Equiv`, then
    re-verifying under any equivalent runtime yields exactly the same result. -/
theorem acceptance_reproducible {ρ : Type} {run : RuntimeExecutor ρ} {Equiv : ρ → ρ → Prop}
    (hdet : DeterministicModulo run Equiv) {x y : ρ} (hxy : Equiv x y) (O : Oracles)
    (T : TrustAnchor) (inp : PackageInput) :
    acceptPCS { O with exec := fun req => run req x } T inp =
      acceptPCS { O with exec := fun req => run req y } T inp := by
  have : (fun req => run req x) = (fun req => run req y) := funext fun req => hdet req x y hxy
  rw [this]

/-- Same committed source/inputs/environment/request + deterministic semantics ⇒ same result. -/
theorem same_commitments_same_observation {ρ : Type} {run : RuntimeExecutor ρ}
    {Equiv : ρ → ρ → Prop} (hdet : DeterministicModulo run Equiv)
    {req₁ req₂ : ReplayRequest} (hreq : req₁ = req₂) {x y : ρ} (hxy : Equiv x y) :
    run req₁ x = run req₂ y := by
  subst hreq; exact hdet req₁ x y hxy

/-! ## Reproducibility notions -/

/-- Raw replay output (stdout/stderr/files/exit status, abstractly) and its PCS
    normalization to an observation (e.g. a tolerance test for statistical checks). -/
structure RawSemantics (ρ Raw : Type) where
  rawRun : ReplayRequest → ρ → Raw
  normalize : Raw → Observation

def ByteReproducible {ρ Raw : Type} (S : RawSemantics ρ Raw) (req : ReplayRequest) (x y : ρ) : Prop :=
  S.rawRun req x = S.rawRun req y

def NormalizedReproducible {ρ Raw : Type} (S : RawSemantics ρ Raw) (req : ReplayRequest)
    (x y : ρ) : Prop :=
  S.normalize (S.rawRun req x) = S.normalize (S.rawRun req y)

theorem byte_repro_implies_normalized {ρ Raw : Type} (S : RawSemantics ρ Raw) {req : ReplayRequest}
    {x y : ρ} (h : ByteReproducible S req x y) : NormalizedReproducible S req x y := by
  unfold NormalizedReproducible; rw [h]

/-- Statistical/tolerance checks: normalized reproducibility does not imply byte
    reproducibility (two different raw outputs within tolerance). -/
theorem normalized_not_byte :
    ∃ (S : RawSemantics Bool Nat) (req : ReplayRequest),
      NormalizedReproducible S req false true ∧ ¬ ByteReproducible S req false true := by
  refine ⟨{ rawRun := fun _ b => if b then 101 else 100,
            normalize := fun n => ⟨.statisticalValidation, if n ≤ 105 then .pass else .fail⟩ },
          { certificateSemanticHash := [], checkerVersion := "", evidence := .null, artifacts := [] },
          ?_, ?_⟩
  · rfl
  · unfold ByteReproducible; decide

/-- PCS v0.6 acceptance depends on the executor only through observations: two
    executors that agree on every request yield the same verdict. -/
theorem verdict_depends_only_on_observations (O : Oracles) (exec' : Executor)
    (hagree : ∀ req, O.exec req = exec' req) (T : TrustAnchor) (inp : PackageInput) :
    acceptPCS O T inp = acceptPCS { O with exec := exec' } T inp := by
  have : O.exec = exec' := funext hagree
  cases O; simp only at this; subst this; rfl

/-! ## Anti-substitution / freshness -/

/-- Replay requests are injective in (certificate semantic hash, checker version,
    evidence object, artifact bytes): an observation for one context is never the
    observation *for* another context. -/
theorem requestFor_injective {c₁ c₂ : CertV2} {m₁ m₂ : CertModel}
    {t₁ t₂ : List (String × ByteArray)} {e₁ e₂ : CertEvidence}
    (h : requestFor c₁ m₁ t₁ e₁ = requestFor c₂ m₂ t₂ e₂) :
    c₁.semanticHash = c₂.semanticHash ∧ m₁.checkerVersion = m₂.checkerVersion ∧
      e₁.json = e₂.json ∧ t₁ = t₂ := by
  simp only [requestFor, ReplayRequest.mk.injEq] at h
  exact h

/-- A normalized decision accepted in two packages pins both to the same certificate
    hashes; their integrity projections agree unless SHA-256 collides.  Stale or foreign
    decisions cannot be transplanted into a package for a different certificate. -/
theorem wire_reuse_same_certificate {O₁ O₂ : Oracles} {T₁ T₂ : TrustAnchor}
    {inp₁ inp₂ : PackageInput} {r₁ r₂ : AcceptedResult}
    (h₁ : acceptPCS O₁ T₁ inp₁ = some r₁) (h₂ : acceptPCS O₂ T₂ inp₂ = some r₂)
    {p₁ p₂ : EntryV2 × WireV2} (hp₁ : p₁ ∈ r₁.claims) (hp₂ : p₂ ∈ r₂.claims)
    (hw : p₁.2 = p₂.2) :
    r₁.pkg.cert.semanticHash = r₂.pkg.cert.semanticHash ∧
    r₁.pkg.cert.integrityHash = r₂.pkg.cert.integrityHash ∧
    (integrityProjection r₁.pkg.cert.members = integrityProjection r₂.pkg.cert.members ∨
      Sha256Collision) := by
  obtain ⟨s₁, i₁⟩ := (pcs_claims_assured h₁ p₁ hp₁).certificateBound
  obtain ⟨s₂, i₂⟩ := (pcs_claims_assured h₂ p₂ hp₂).certificateBound
  have hs : r₁.pkg.cert.semanticHash = r₂.pkg.cert.semanticHash := by rw [← s₁, ← s₂, hw]
  have hi : r₁.pkg.cert.integrityHash = r₂.pkg.cert.integrityHash := by rw [← i₁, ← i₂, hw]
  exact ⟨hs, hi, integrity_binding_of_accepted (acceptPCS_sound h₁).package.cert
    (acceptPCS_sound h₂).package.cert hi⟩

end PCS.V2.Reproducibility
