import PCS.V2.TranslationV2
import PCS.V2.TranslationJson

/-!
# Wire format and executable front end of Semantic Intelligence v2

* Canonical JSON codecs for certificates (`EquivCert`), finite structures (`FinModel`),
  countermodel witnesses, search bounds and v2 requests, each with a proved
  decode∘encode round trip (`decRequestV2_encRequestV2`, `decCountermodel_enc`, …).
* `semanticCheckV2` — the pure function run by `pcs-semantic-check --v2`: strict canonical
  decoding (the v1 byte gate `parseCanonicalBytes`), decoding of the authority configuration
  (v1 format, Ed25519 receipt verification), clamping of the untrusted search bounds, and the
  v2 classifier `decideV2`.
* `checkCountermodelBundle` — the pure function run by `pcs-semantic-check --check-countermodel`:
  independent re-verification of a serialized countermodel.

Refinement theorems (all kernel-checked):

* `semantic_wire_roundtrip` — the request decoder inverts the encoder.
* `semanticCheckV2_decision` / `semanticCheckV2_encRequestV2` — on decodable input (in
  particular on the canonical bytes of any request) the front end computes exactly
  `decideV2`.
* `accepted_wire_translation_preserves_semantics` — a `CERTIFIED_TRANSLATION` printed by the
  front end implies that the raw bytes decode to a request whose selected interpretation and
  candidate are denotationally equivalent in every model.
* `malformed_wire_request_rejected`, `semantic_authority_cannot_be_bypassed_by_unsigned_receipts`.
* `countermodel_bundle_sound` — an accepted serialized countermodel is a genuine semantic
  difference.

The compiler, runtime, file IO and the Ed25519 implementation's correspondence to the
standard remain trusted (as in v1).
-/

set_option autoImplicit false

namespace PCS.V2.Semantic

open PCS.V2.Json PCS.V2.Canonical

/-! ## Numbers and lists -/

def encNat (n : Nat) : JVal := .num (Int.ofNat n)

theorem decNat_encNat (n : Nat) : decNat (encNat n) = some n := rfl

def encNats (l : List Nat) : JVal := .arr (l.map encNat)

def decNats : JVal → Option (List Nat)
  | .arr vs => decList decNat vs
  | _ => none

theorem decNats_encNats (l : List Nat) : decNats (encNats l) = some l :=
  decList_map decNat encNat l (fun _ _ => rfl)

/-! ## Certificates -/

def encRule (r : Rule) : JVal := .str r.name

def decRule : JVal → Option Rule
  | .str s => Rule.ofName s
  | _ => none

theorem decRule_encRule (r : Rule) : decRule (encRule r) = some r := by
  cases r <;> rfl

def encTarget : Target → JVal
  | .concl => .str "conclusion"
  | .assm j => encNat j

def decTarget : JVal → Option Target
  | .str "conclusion" => some .concl
  | .num (.ofNat j) => some (.assm j)
  | _ => none

theorem decTarget_encTarget (t : Target) : decTarget (encTarget t) = some t := by
  cases t <;> rfl

def encStep (s : Step) : JVal :=
  .obj [("path", encNats s.path), ("rule", encRule s.rule), ("target", encTarget s.target)]

def decStep : JVal → Option Step
  | .obj [("path", p), ("rule", r), ("target", t)] =>
    match decNats p, decRule r, decTarget t with
    | some p', some r', some t' => some ⟨t', p', r'⟩
    | _, _, _ => none
  | _ => none

theorem decStep_encStep (s : Step) : decStep (encStep s) = some s := by
  obtain ⟨t, p, r⟩ := s
  simp [encStep, decStep, decNats_encNats, decRule_encRule, decTarget_encTarget]

def encSteps (l : List Step) : JVal := .arr (l.map encStep)

def decSteps : JVal → Option (List Step)
  | .arr vs => decList decStep vs
  | _ => none

theorem decSteps_encSteps (l : List Step) : decSteps (encSteps l) = some l :=
  decList_map decStep encStep l (fun s _ => decStep_encStep s)

def encCert (c : EquivCert) : JVal :=
  .obj [("left", encSteps c.left), ("right", encSteps c.right)]

def decCert : JVal → Option EquivCert
  | .obj [("left", l), ("right", r)] =>
    match decSteps l, decSteps r with
    | some l', some r' => some ⟨l', r'⟩
    | _, _ => none
  | _ => none

theorem decCert_encCert (c : EquivCert) : decCert (encCert c) = some c := by
  obtain ⟨l, r⟩ := c
  simp [encCert, decCert, decSteps_encSteps]

/-! ## Finite structures and countermodels -/

def encSortCarrier (e : SortId × List Nat) : JVal :=
  .obj [("carrier", encNats e.2), ("sort", .str e.1)]

def decSortCarrier : JVal → Option (SortId × List Nat)
  | .obj [("carrier", c), ("sort", .str s)] => (decNats c).map (fun c' => (s, c'))
  | _ => none

def encRow (r : List Nat × Nat) : JVal := .obj [("args", encNats r.1), ("value", encNat r.2)]

def decRow : JVal → Option (List Nat × Nat)
  | .obj [("args", a), ("value", v)] =>
    match decNats a, decNat v with
    | some a', some v' => some (a', v')
    | _, _ => none
  | _ => none

def encFnTable (e : String × List (List Nat × Nat)) : JVal :=
  .obj [("symbol", .str e.1), ("table", .arr (e.2.map encRow))]

def decFnTable : JVal → Option (String × List (List Nat × Nat))
  | .obj [("symbol", .str f), ("table", .arr rs)] => (decList decRow rs).map (fun t => (f, t))
  | _ => none

def encPredTable (e : String × List (List Nat)) : JVal :=
  .obj [("symbol", .str e.1), ("true_on", .arr (e.2.map encNats))]

def decPredTable : JVal → Option (String × List (List Nat))
  | .obj [("symbol", .str p), ("true_on", .arr ts)] => (decList decNats ts).map (fun t => (p, t))
  | _ => none

def encFinModel (F : FinModel) : JVal :=
  .obj [("functions", .arr (F.fns.map encFnTable)), ("predicates", .arr (F.preds.map encPredTable)),
    ("sorts", .arr (F.sorts.map encSortCarrier))]

def decFinModel : JVal → Option FinModel
  | .obj [("functions", .arr fs), ("predicates", .arr ps), ("sorts", .arr ss)] =>
    match decList decFnTable fs, decList decPredTable ps, decList decSortCarrier ss with
    | some fs', some ps', some ss' => some ⟨ss', fs', ps'⟩
    | _, _, _ => none
  | _ => none

theorem decFinModel_enc (F : FinModel) : decFinModel (encFinModel F) = some F := by
  obtain ⟨ss, fs, ps⟩ := F
  have h1 : decList decFnTable (fs.map encFnTable) = some fs := by
    apply decList_map
    intro e _
    obtain ⟨f, t⟩ := e
    have : decList decRow (t.map encRow) = some t := by
      apply decList_map; intro r _; obtain ⟨a, v⟩ := r
      simp [encRow, decRow, decNats_encNats, decNat_encNat]
    simp [encFnTable, decFnTable, this]
  have h2 : decList decPredTable (ps.map encPredTable) = some ps := by
    apply decList_map
    intro e _
    obtain ⟨p, t⟩ := e
    have : decList decNats (t.map encNats) = some t :=
      decList_map decNats encNats t (fun l _ => decNats_encNats l)
    simp [encPredTable, decPredTable, this]
  have h3 : decList decSortCarrier (ss.map encSortCarrier) = some ss := by
    apply decList_map
    intro e _
    obtain ⟨s, c⟩ := e
    simp [encSortCarrier, decSortCarrier, decNats_encNats]
  simp [encFinModel, decFinModel, h1, h2, h3]

def encCountermodel (w : Countermodel) : JVal :=
  .obj [("candidate_holds", .bool w.candidateHolds),
    ("interpretation_holds", .bool w.interpretationHolds), ("model", encFinModel w.model)]

def decCountermodel : JVal → Option Countermodel
  | .obj [("candidate_holds", .bool c), ("interpretation_holds", .bool i), ("model", m)] =>
    (decFinModel m).map (fun F => ⟨F, i, c⟩)
  | _ => none

/-- **Reproducible countermodel serialization.** -/
theorem decCountermodel_enc (w : Countermodel) : decCountermodel (encCountermodel w) = some w := by
  obtain ⟨F, i, c⟩ := w
  simp [encCountermodel, decCountermodel, decFinModel_enc]

/-! ## v2 requests -/

def encBounds (b : SearchBounds) : JVal :=
  .obj [("cert_cap", encNat b.certCap), ("cert_depth", encNat b.certDepth),
    ("model_bound", encNat b.modelBound), ("model_budget", encNat b.modelBudget)]

def decBounds : JVal → Option SearchBounds
  | .obj [("cert_cap", cc), ("cert_depth", cd), ("model_bound", mb), ("model_budget", mu)] =>
    match decNat cc, decNat cd, decNat mb, decNat mu with
    | some cc', some cd', some mb', some mu' => some ⟨cd', cc', mb', mu'⟩
    | _, _, _, _ => none
  | _ => none

theorem decBounds_encBounds (b : SearchBounds) : decBounds (encBounds b) = some b := by
  obtain ⟨a, b, c, d⟩ := b; rfl

def requestV2Schema : String := "pcs-semantic-translation-v2"

def encRequestV2 (r : RequestV2) : JVal :=
  .obj [("bounds", encBounds r.bounds), ("certificate", encOpt encCert r.certificate),
    ("request", encRequest r.base), ("schema", .str requestV2Schema)]

def decRequestV2 : JVal → Option RequestV2
  | .obj [("bounds", b), ("certificate", c), ("request", q),
      ("schema", .str "pcs-semantic-translation-v2")] =>
    match decBounds b, decOpt decCert c, decRequest q with
    | some b', some c', some q' => some ⟨q', c', b'⟩
    | _, _, _ => none
  | _ => none

/-- **`semantic_wire_roundtrip`**: the v2 request decoder inverts the canonical encoder. -/
theorem semantic_wire_roundtrip (r : RequestV2) : decRequestV2 (encRequestV2 r) = some r := by
  obtain ⟨q, c, b⟩ := r
  simp only [encRequestV2, requestV2Schema, decRequestV2, decBounds_encBounds,
    decOpt_encOpt decCert encCert (fun _ h => by cases h) decCert_encCert, decRequest_encRequest]

theorem decRequestV2_encRequestV2 (r : RequestV2) : decRequestV2 (encRequestV2 r) = some r :=
  semantic_wire_roundtrip r

/-! ## Decision output -/

def SemanticStatus.name : SemanticStatus → String
  | .normalFormEqual => "NORMAL_FORM_EQUAL"
  | .certified _ => "CERTIFIED_EQUIVALENCE"
  | .counterexample _ => "VERIFIED_COUNTERMODEL"
  | .unknown _ => "UNDETERMINED_WITHIN_BOUNDS"

def SearchOutcome.name : SearchOutcome → String
  | .found _ => "FOUND"
  | .exhausted => "EXHAUSTED_WITHIN_BOUND"
  | .budgetExceeded => "BUDGET_EXCEEDED"

/-- Hard caps on the untrusted search effort (denial-of-service protection only). -/
def SearchBounds.clamp (b : SearchBounds) : SearchBounds :=
  ⟨min b.certDepth 4, min b.certCap 2000, min b.modelBound 4, min b.modelBudget 200000⟩

/-- What the v2 front end computes. -/
structure CliResultV2 where
  decision : DecisionV2
  explanation : Option ExplanationIR
  expectedLeanSource : String
  deriving Repr, Inhabited

def malformedV2 (component : String) : CliResultV2 :=
  ⟨⟨.invalidProposal, [⟨.malformedInput, component, "input is not canonical JSON of the expected schema"⟩],
    .unknown .exhausted, none⟩, none, ""⟩

/-- **The pure v2 front end** run by `pcs-semantic-check --v2`. -/
def semanticCheckV2 (authorityRaw requestRaw : ByteArray) : CliResultV2 :=
  match (parseCanonicalBytes maxInputBytes authorityRaw).bind decAuthorityConfig with
  | none => malformedV2 "authority"
  | some cfg =>
    match (parseCanonicalBytes maxInputBytes requestRaw).bind decRequestV2 with
    | none => malformedV2 "request"
    | some r =>
      let A := cfg.toAuthority
      let d := decideV2 A { r with bounds := r.bounds.clamp }
      { decision := d,
        explanation := if d.outcome = .certifiedTranslation then
          some (toExplanation A.registry r.base.candidate.claim) else none,
        expectedLeanSource := renderClaimLean A.registry r.base.candidate.claim }

theorem semanticCheckV2_decision {aRaw rRaw : ByteArray} {cfg : AuthorityConfig} {r : RequestV2}
    (ha : (parseCanonicalBytes maxInputBytes aRaw).bind decAuthorityConfig = some cfg)
    (hr : (parseCanonicalBytes maxInputBytes rRaw).bind decRequestV2 = some r) :
    (semanticCheckV2 aRaw rRaw).decision = decideV2 cfg.toAuthority { r with bounds := r.bounds.clamp } := by
  unfold semanticCheckV2; rw [ha, hr]

/-- On the canonical bytes of any (canonical, size-bounded) v2 request, the front end computes
    exactly the v2 classifier's decision. -/
theorem semanticCheckV2_encRequestV2 {aRaw : ByteArray} {cfg : AuthorityConfig} (r : RequestV2)
    (ha : (parseCanonicalBytes maxInputBytes aRaw).bind decAuthorityConfig = some cfg)
    (hc : canonical (encRequestV2 r) = true) (hs : (jcsBytes (encRequestV2 r)).size ≤ maxInputBytes) :
    (semanticCheckV2 aRaw (jcsBytes (encRequestV2 r))).decision =
      decideV2 cfg.toAuthority { r with bounds := r.bounds.clamp } := by
  apply semanticCheckV2_decision ha
  rw [parseCanonicalBytes_complete hc hs]
  exact semantic_wire_roundtrip r

/-- **Wire-level soundness**: a `CERTIFIED_TRANSLATION` outcome means the raw bytes decode to
    an authority configuration and a request satisfying the v2 contract. -/
theorem semanticCheckV2_certified_sound {aRaw rRaw : ByteArray}
    (h : (semanticCheckV2 aRaw rRaw).decision.outcome = .certifiedTranslation) :
    ∃ cfg r, (parseCanonicalBytes maxInputBytes aRaw).bind decAuthorityConfig = some cfg ∧
      (parseCanonicalBytes maxInputBytes rRaw).bind decRequestV2 = some r ∧
      CertifiedContractV2 cfg.toAuthority r.base (semanticCheckV2 aRaw rRaw).decision.certificate := by
  unfold semanticCheckV2 at h ⊢
  split at h
  · cases h
  · rename_i cfg hcfg
    split at h
    · cases h
    · rename_i r hr
      refine ⟨cfg, r, hcfg, hr, ?_⟩
      exact decideV2_certified_sound (r := { r with bounds := r.bounds.clamp }) h

/-- **`accepted_wire_translation_preserves_semantics`.** -/
theorem accepted_wire_translation_preserves_semantics {aRaw rRaw : ByteArray}
    (h : (semanticCheckV2 aRaw rRaw).decision.outcome = .certifiedTranslation) :
    ∃ cfg r, (parseCanonicalBytes maxInputBytes aRaw).bind decAuthorityConfig = some cfg ∧
      (parseCanonicalBytes maxInputBytes rRaw).bind decRequestV2 = some r ∧
      ∀ (M : Model) (ρ : String → M.Dom),
        r.base.interpretation.selected.denote M ρ ↔ r.base.candidate.claim.denote M ρ := by
  obtain ⟨cfg, r, h1, h2, hc⟩ := semanticCheckV2_certified_sound h
  exact ⟨cfg, r, h1, h2, accepted_translation_preserves_denotation_v2 hc⟩

/-- **`malformed_wire_request_rejected`**: bytes that are not the canonical encoding of a v2
    request never yield acceptance. -/
theorem malformed_wire_request_rejected {aRaw rRaw : ByteArray}
    (h : (parseCanonicalBytes maxInputBytes rRaw).bind decRequestV2 = none) :
    (semanticCheckV2 aRaw rRaw).decision.outcome = .invalidProposal := by
  unfold semanticCheckV2
  split
  · rfl
  · rw [h]; rfl

/-- **`semantic_authority_cannot_be_bypassed_by_unsigned_receipts`**: a certified wire
    request carries a confirmation receipt bound to the exact interpretation whose Ed25519
    signature verifies under an authorized confirmation key, and — when required — proof and
    elaboration receipts bound to the exact Lean source whose signatures verify under
    authorized keys of the right role. -/
theorem semantic_authority_cannot_be_bypassed_by_unsigned_receipts {aRaw rRaw : ByteArray}
    (h : (semanticCheckV2 aRaw rRaw).decision.outcome = .certifiedTranslation) :
    ∃ cfg r, (parseCanonicalBytes maxInputBytes aRaw).bind decAuthorityConfig = some cfg ∧
      (parseCanonicalBytes maxInputBytes rRaw).bind decRequestV2 = some r ∧
      (∃ rc, r.base.confirmation = some rc ∧ rc.binds r.base.interpretation = true ∧
        sigOK cfg.confirmationKeys rc.authority (confirmationMessage rc) rc.signature = true) ∧
      (cfg.requireProof = true → ∃ rp, r.base.proof = some rp ∧
        rp.leanSource = r.base.candidate.leanSource ∧
        sigOK cfg.proofKeys rp.authority (proofMessage rp) rp.signature = true) ∧
      (cfg.requireElaboration = true → ∃ re, r.base.elaboration = some re ∧
        re.leanSource = r.base.candidate.leanSource ∧
        sigOK cfg.elaborationKeys re.authority (elaborationMessage re) re.signature = true) := by
  obtain ⟨cfg, r, h1, h2, hc⟩ := semanticCheckV2_certified_sound h
  refine ⟨cfg, r, h1, h2, hc.gates.confirmation, fun hp => ?_, fun he => ?_⟩
  · obtain ⟨rp, h3, h4, _, _, h5⟩ := hc.gates.proof hp
    exact ⟨rp, h3, h4, h5⟩
  · obtain ⟨re, h3, h4, _, h5⟩ := hc.gates.elaboration he
    exact ⟨re, h3, h4, h5⟩

/-! ## Independent countermodel re-verification -/

/-- A self-contained countermodel bundle. -/
structure CountermodelBundle where
  interpretation : SemanticClaim
  candidate : SemanticClaim
  countermodel : Countermodel
  deriving Repr, Inhabited

def encCountermodelBundle (b : CountermodelBundle) : JVal :=
  .obj [("candidate", encClaim b.candidate), ("countermodel", encCountermodel b.countermodel),
    ("interpretation", encClaim b.interpretation), ("schema", .str "pcs-countermodel-v1")]

def decCountermodelBundle : JVal → Option CountermodelBundle
  | .obj [("candidate", c), ("countermodel", w), ("interpretation", i),
      ("schema", .str "pcs-countermodel-v1")] =>
    match decClaim c, decCountermodel w, decClaim i with
    | some c', some w', some i' => some ⟨i', c', w'⟩
    | _, _, _ => none
  | _ => none

theorem decCountermodelBundle_enc (b : CountermodelBundle) :
    decCountermodelBundle (encCountermodelBundle b) = some b := by
  obtain ⟨i, c, w⟩ := b
  simp [encCountermodelBundle, decCountermodelBundle, decClaim_encClaim, decCountermodel_enc]

/-- The pure function run by `pcs-semantic-check --check-countermodel`. -/
def checkCountermodelBundle (authorityRaw bundleRaw : ByteArray) : Option Bool :=
  match (parseCanonicalBytes maxInputBytes authorityRaw).bind decAuthorityConfig,
    (parseCanonicalBytes maxInputBytes bundleRaw).bind decCountermodelBundle with
  | some cfg, some b => some (checkCountermodel cfg.registry b.interpretation b.candidate b.countermodel)
  | _, _ => none

/-- **`countermodel_bundle_sound`**: if the re-verifier accepts serialized bytes, they decode
    to two claims and a registry-conforming finite structure in which the claims differ. -/
theorem countermodel_bundle_sound {aRaw bRaw : ByteArray}
    (h : checkCountermodelBundle aRaw bRaw = some true) :
    ∃ cfg b, (parseCanonicalBytes maxInputBytes aRaw).bind decAuthorityConfig = some cfg ∧
      (parseCanonicalBytes maxInputBytes bRaw).bind decCountermodelBundle = some b ∧
      b.countermodel.model.toModel.Conforms cfg.registry ∧
      ¬ (b.interpretation.denote b.countermodel.model.toModel ρ0 ↔
          b.candidate.denote b.countermodel.model.toModel ρ0) := by
  unfold checkCountermodelBundle at h
  split at h
  · rename_i cfg b hcfg hb
    have hw : checkCountermodel cfg.registry b.interpretation b.candidate b.countermodel = true :=
      Option.some.inj h
    exact ⟨cfg, b, hcfg, hb, (countermodel_witness_sound hw).1, (countermodel_witness_sound hw).2.2.2⟩
  · cases h

/-! ## Output encoding -/

def encSemanticStatus (s : SemanticStatus) : JVal :=
  match s with
  | .normalFormEqual => .obj [("kind", .str s.name)]
  | .certified c => .obj [("certificate", encCert c), ("kind", .str s.name)]
  | .counterexample w => .obj [("countermodel", encCountermodel w), ("kind", .str s.name)]
  | .unknown o => .obj [("kind", .str s.name), ("search", .str o.name)]

end PCS.V2.Semantic
