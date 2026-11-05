import PCS.V2.PackageProofs

/-!
# Typed view of a v0.6 certificate and Lean normalization

`decodeCertModel` extracts, from the verified canonical certificate object, exactly
the parts the end-to-end verifier consumes: claims (with committed predicate and
recorded assessment), typed evidence items (with their verbatim JSON, which is what
fresh replay executes), assumptions and artifacts.

`deriveWire` is the Lean transcription of
`pcs/normalized_wire_v06.py::normalize_claim_after_replay_v06`: it rebuilds the
normalized decision wire of a claim from the certificate alone.  The production
verifier requires the delivered normalized bytes to equal the replay-derived bytes;
the Lean checker requires the delivered typed wire to equal `deriveWire`, which is
the same condition because accepted wire bytes are exactly the canonical encoding
of the typed wire (`verifyWireBytes_canonical`).
-/

namespace PCS.V2.CertificateModel

open PCS PCS.Decision PCS.V2.Json PCS.V2.Hex PCS.V2.Domains PCS.V2.Canonical PCS.V2.Common
open PCS.V2.NormalizedWire PCS.V2.Package

structure CertClaim where
  id : String
  kind : ClaimKind
  predicate : JVal
  requiredEvidence : List String
  assumptions : List String
  status : DecisionStatus

structure CertEvidence where
  id : String
  kind : EvidenceKind
  outcome : Outcome
  predicate : JVal
  /-- the complete evidence object (incl. `check_spec`, `artifact_ids`, `checker`) -/
  json : JVal

structure CertAssumption where
  id : String
  statement : String

structure CertArtifact where
  id : String
  path : String
  sha256 : List UInt8
  sourcePath : Option String

structure CertModel where
  checkerVersion : String
  claims : List CertClaim
  evidence : List CertEvidence
  assumptions : List CertAssumption
  artifacts : List CertArtifact

def objOf : JVal → Option (List (String × JVal))
  | .obj ms => some ms
  | _ => none

def arrOf : JVal → Option (List JVal)
  | .arr xs => some xs
  | _ => none

def decodeCertClaim (v : JVal) : Option CertClaim := do
  let ms ← objOf v
  let id ← strField ms "id"
  let kind ← (strField ms "kind").bind (decodeEnum allClaimKinds claimKindName)
  let predicate ← field ms "predicate"
  let req ← (field ms "required_evidence").bind strArray
  let asm ← (field ms "assumptions").bind strArray
  let a ← (field ms "assessment").bind objOf
  let status ← (strField a "status").bind (decodeEnum allDecisions decisionName)
  pure { id, kind, predicate, requiredEvidence := req, assumptions := asm, status }

def decodeCertEvidence (v : JVal) : Option CertEvidence := do
  let ms ← objOf v
  let id ← strField ms "id"
  let kind ← (strField ms "kind").bind (decodeEnum allEvidenceKinds evidenceKindName)
  let outcome ← (strField ms "outcome").bind (decodeEnum allOutcomes outcomeName)
  let predicate ← field ms "predicate"
  pure { id, kind, outcome, predicate, json := v }

def decodeCertAssumption (v : JVal) : Option CertAssumption := do
  let ms ← objOf v
  let id ← strField ms "id"
  let statement ← strField ms "statement"
  pure { id, statement }

def decodeCertArtifact (v : JVal) : Option CertArtifact := do
  let ms ← objOf v
  let id ← strField ms "id"
  let path ← strField ms "path"
  let sha ← digestField ms "sha256"
  pure { id, path, sha256 := sha, sourcePath := strField ms "source_path" }

def decodeCertModel (c : CertV2) : Option CertModel := do
  let cv ← strField c.members "checker_version"
  let claims ← (field c.members "claims").bind arrOf >>= mapOpt decodeCertClaim
  let evidence ← (field c.members "evidence").bind arrOf >>= mapOpt decodeCertEvidence
  let assumptions ← (field c.members "assumptions").bind arrOf >>= mapOpt decodeCertAssumption
  let artifacts ← (field c.members "artifacts").bind arrOf >>= mapOpt decodeCertArtifact
  if (claims.map (·.id)).Nodup ∧ (evidence.map (·.id)).Nodup ∧
     (assumptions.map (·.id)).Nodup ∧ (artifacts.map (·.id)).Nodup then
    pure { checkerVersion := cv, claims, evidence, assumptions, artifacts }
  else none

def claimIds (m : CertModel) : List String := m.claims.map (·.id)

/-! ## Lean normalization (`normalize_claim_after_replay_v06`) -/

def commitmentOf (p : JVal) : List UInt8 := domainDigest predicateCommitmentDomain p

def contextItem (m : CertModel) (aid : String) : Option AssumptionV2 :=
  (m.assumptions.find? (·.id == aid)).map (fun a => { id := a.id, statement := a.statement })

def wireEvidenceItem (m : CertModel) (commit : List UInt8) (eid : String) : Option EvidenceV2 :=
  match m.evidence.find? (·.id == eid) with
  | none => none
  | some e =>
    if commitmentOf e.predicate = commit then
      some { id := e.id, kind := e.kind, outcome := e.outcome, predicateCommitment := commit }
    else none

def deriveWire (c : CertV2) (m : CertModel) (cl : CertClaim) : Option WireV2 := do
  let ctx ← mapOpt (contextItem m) cl.assumptions
  let commit := commitmentOf cl.predicate
  let ev ← mapOpt (wireEvidenceItem m commit) cl.requiredEvidence
  let w0 : WireV2 :=
    { source := { checkerVersion := m.checkerVersion, certificateSemanticHash := c.semanticHash,
                  certificateIntegrityHash := c.integrityHash, claimId := cl.id },
      context := ctx,
      claim := { id := cl.id, kind := cl.kind, predicateCommitment := commit,
                 requiredEvidence := cl.requiredEvidence, assumptions := cl.assumptions },
      evidence := ev, decision := cl.status, wireSemanticHash := [] }
  pure { w0 with wireSemanticHash := expectedHash w0 }

/-! ## Generic lemmas -/

theorem mapOpt_mem {α β : Type} {f : α → Option β} :
    ∀ {xs : List α} {ys : List β}, mapOpt f xs = some ys → ∀ y ∈ ys, ∃ x ∈ xs, f x = some y
  | [], ys, h => by simp [mapOpt] at h; subst h; intro _ h; cases h
  | x :: xs, ys, h => by
    simp only [mapOpt] at h
    split at h
    · rename_i y' ys' hy hys
      cases h
      intro y hy'
      simp only [List.mem_cons] at hy'
      rcases hy' with rfl | hy'
      · exact ⟨x, List.mem_cons_self, hy⟩
      · obtain ⟨x', hx', hfx⟩ := mapOpt_mem hys y hy'
        exact ⟨x', List.mem_cons_of_mem _ hx', hfx⟩
    · cases h

theorem mapOpt_map_eq {α β γ : Type} {f : α → Option β} {g : β → γ} {h : α → γ}
    (hfg : ∀ x y, f x = some y → g y = h x) :
    ∀ {xs : List α} {ys : List β}, mapOpt f xs = some ys → ys.map g = xs.map h
  | [], ys, hm => by simp [mapOpt] at hm; subst hm; rfl
  | x :: xs, ys, hm => by
    simp only [mapOpt] at hm
    split at hm
    · rename_i y ys' hy hys
      cases hm
      simp [hfg x y hy, mapOpt_map_eq hfg hys]
    · cases hm

theorem find?_mem_id {α : Type} {l : List α} {key : α → String} {k : String} {a : α}
    (h : l.find? (fun x => key x == k) = some a) : a ∈ l ∧ key a = k := by
  refine ⟨List.mem_of_find?_eq_some h, ?_⟩
  have := List.find?_some h
  simpa using this

/-! ## Facts about derived wires -/

theorem deriveWire_spec {c : CertV2} {m : CertModel} {cl : CertClaim} {w : WireV2}
    (h : deriveWire c m cl = some w) :
    w.source.certificateSemanticHash = c.semanticHash ∧
    w.source.certificateIntegrityHash = c.integrityHash ∧
    w.source.claimId = cl.id ∧ w.source.checkerVersion = m.checkerVersion ∧
    w.claim.id = cl.id ∧ w.claim.kind = cl.kind ∧
    w.claim.predicateCommitment = commitmentOf cl.predicate ∧
    w.claim.requiredEvidence = cl.requiredEvidence ∧ w.claim.assumptions = cl.assumptions ∧
    w.decision = cl.status ∧
    w.evidence.map (·.id) = cl.requiredEvidence ∧
    (∀ ev ∈ w.evidence, ∃ e ∈ m.evidence, e.id = ev.id ∧ e.kind = ev.kind ∧
        e.outcome = ev.outcome ∧ commitmentOf e.predicate = commitmentOf cl.predicate ∧
        ev.predicateCommitment = commitmentOf cl.predicate) ∧
    (∀ a ∈ w.context, ∃ a' ∈ m.assumptions, a'.id = a.id ∧ a'.statement = a.statement) := by
  unfold deriveWire at h
  simp only [bind, Option.bind_eq_some_iff, pure, Option.some.injEq] at h
  obtain ⟨ctx, hctx, ev, hev, rfl⟩ := h
  have hevid : ev.map (·.id) = cl.requiredEvidence.map id := by
    refine mapOpt_map_eq (fun eid y hy => ?_) hev
    unfold wireEvidenceItem at hy
    split at hy
    · cases hy
    · rename_i e he
      split at hy
      · cases hy; exact (find?_mem_id he).2
      · cases hy
  refine ⟨rfl, rfl, rfl, rfl, rfl, rfl, rfl, rfl, rfl, rfl, by simpa using hevid, ?_, ?_⟩
  · intro y hy
    obtain ⟨eid, _, hy⟩ := mapOpt_mem hev y hy
    unfold wireEvidenceItem at hy
    split at hy
    · cases hy
    · rename_i e he
      split at hy
      · rename_i hc
        cases hy
        exact ⟨e, (find?_mem_id he).1, rfl, rfl, rfl, hc, rfl⟩
      · cases hy
  · intro a ha
    obtain ⟨aid, _, ha⟩ := mapOpt_mem hctx a ha
    unfold contextItem at ha
    cases hf : m.assumptions.find? (·.id == aid) with
    | none => rw [hf] at ha; cases ha
    | some a' =>
      rw [hf] at ha
      cases ha
      exact ⟨a', (find?_mem_id hf).1, rfl, rfl⟩

theorem decodeCertModel_spec {c : CertV2} {m : CertModel} (h : decodeCertModel c = some m) :
    strField c.members "checker_version" = some m.checkerVersion ∧
    (∃ xs, field c.members "claims" = some (.arr xs) ∧ mapOpt decodeCertClaim xs = some m.claims) ∧
    (∃ xs, field c.members "evidence" = some (.arr xs) ∧
      mapOpt decodeCertEvidence xs = some m.evidence) ∧
    (∃ xs, field c.members "artifacts" = some (.arr xs) ∧
      mapOpt decodeCertArtifact xs = some m.artifacts) ∧
    (m.claims.map (·.id)).Nodup ∧ (m.evidence.map (·.id)).Nodup ∧
    (m.assumptions.map (·.id)).Nodup ∧ (m.artifacts.map (·.id)).Nodup := by
  unfold decodeCertModel at h
  simp only [bind, Option.bind_eq_some_iff, pure] at h
  obtain ⟨cv, hcv, cls, ⟨xs1, ⟨v1, hv1, ha1⟩, hcls⟩, evs, ⟨xs2, ⟨v2, hv2, ha2⟩, hevs⟩,
    asms, ⟨xs3, ⟨v3, hv3, ha3⟩, hasms⟩, arts, ⟨xs4, ⟨v4, hv4, ha4⟩, harts⟩, h⟩ := h
  split at h
  · rename_i hnd
    cases h
    cases v1 <;> simp [arrOf] at ha1
    cases v2 <;> simp [arrOf] at ha2
    cases v4 <;> simp [arrOf] at ha4
    subst ha1 ha2 ha4
    exact ⟨hcv, ⟨_, hv1, hcls⟩, ⟨_, hv2, hevs⟩, ⟨_, hv4, harts⟩, hnd.1, hnd.2.1, hnd.2.2.1,
      hnd.2.2.2⟩
  · cases h

end PCS.V2.CertificateModel
