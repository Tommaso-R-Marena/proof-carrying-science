import PCS.V2.TranslationV3Json

/-!
# PCS v3 — the end-to-end assurance theorem

**`pcs_v3_certified_wire_assurance`** connects

* the raw input bytes (authority configuration, request, ledger snapshot with trusted clock),
* the certified semantic equivalence (normal forms or a re-checked rewrite certificate),
* the stateful receipt protocol (every envelope verified, bound, authorized, fresh, consumed),
* the generated Lean syntax and its general name-resolution semantics
  (`PCS.V2.Semantic.LeanSyntax.lean_reading_correspondence`),

to a precisely scoped final judgment.  Everything except three explicitly named trust conditions
is proved:

1. `DishonestBelow W A now .proof q` — fewer than `q` (the proof quorum) active proof keys are
   dishonest.  A malicious signer, a compromised key and an Ed25519 forgery are all "dishonest
   keys"; they are **not** excluded from the threat model, only bounded in number.
2. `KernelRecordSound` — a *true* kernel-check record for source `s` in the environment with
   fingerprint `fp` means the Lean kernel accepted a proof of the proposition `s` elaborates to in
   that environment, and that proposition holds (Lean kernel soundness).
3. `LeanFrontendFaithful` — in the environment with fingerprint `fp`, Lean's parser/elaborator
   reads every text printed from gate-passing syntax as the proposition `LDecl.denote` describes
   (checked executably by `tools/CheckElaborationV3.lean`, not proved).

Under these, the explicitly selected structured interpretation holds in the model induced by the
fingerprinted environment through the approved registry.  Nothing here says the interpretation is
what a human meant (`intent_gap`), or that the environment's definitions describe the world.
-/

set_option autoImplicit false

namespace PCS.V2.Semantic.V3

open PCS.V2.Json PCS.V2.Canonical PCS.V2.Semantic PCS.V2.Semantic.Ledger PCS.V2.Semantic.LeanSyntax

/-! ## Injectivity of the bound interpretation -/

theorem encClaim_injective {c c' : SemanticClaim} (h : encClaim c = encClaim c') : c = c' := by
  have := congrArg decClaim h
  rw [decClaim_encClaim, decClaim_encClaim] at this
  exact Option.some.inj this

theorem encAmbiguities_injective {l l' : List Ambiguity} (h : encAmbiguities l = encAmbiguities l') :
    l = l' := by
  have := congrArg decAmbiguities h
  rw [decAmbiguities_enc, decAmbiguities_enc] at this
  exact Option.some.inj this

/-- A confirmation statement identifies the interpretation (text, selected structure, ambiguity
    resolutions) uniquely. -/
theorem confirmationStatement_identifies {A A' : AuthorityV3} {I I' : Interpretation}
    (h : confirmationStatement A I = confirmationStatement A' I') :
    A.context = A'.context ∧ I.sourceText = I'.sourceText ∧ I.selected = I'.selected ∧
      I.ambiguities = I'.ambiguities := by
  obtain ⟨h1, h2, h3, h4⟩ := confirmationStatement_inj h
  exact ⟨h1, h2, encClaim_injective h3, encAmbiguities_injective h4⟩

/-! ## External semantics of the fingerprinted Lean environment -/

/-- The external world PCS reasons about: what receipt statements assert, a semantic model of the
    Lean environment, and the proposition (if any) a source text elaborates to in the environment
    with a given fingerprint. -/
structure LeanAuthorityWorld where
  W : ReceiptWorld
  env : LeanEnvModel
  Elab : String → String → Option Prop

/-- **Trust condition 2.**  A true kernel-check record (in authority context `A`) for a candidate
    means the source elaborated, in the environment with `A`'s fingerprint, to a proposition the
    kernel accepted a proof of — and (kernel soundness) that proposition holds. -/
def KernelRecordSound (L : LeanAuthorityWorld) : Prop :=
  ∀ (A : AuthorityV3) (c : Candidate) (axs : List String),
    L.W.Holds .proof (proofStatement A c axs) →
      ∃ P, L.Elab A.context.envFingerprint c.leanSource = some P ∧ P

/-- **Trust condition 3.**  In the environment with fingerprint `fp`, Lean reads the printing of
    every gate-passing closed claim's syntax as `LDecl.denote` in `L.env`. -/
def LeanFrontendFaithful (L : LeanAuthorityWorld) (fp : String) (R : Registry) : Prop :=
  ∀ c : SemanticClaim, leanSyntaxSafeB R c = true → c.freeVars = [] →
    L.Elab fp (readClaim R c).print = some (∀ ν, (readClaim R c).denote L.env ν)

/-- A successful elaboration record is not a proof: there is a world in which every elaboration
    record is true, no kernel-check record is, and the elaborated proposition is false. -/
theorem elaboration_record_is_not_proof :
    ∃ L : LeanAuthorityWorld, (∀ st, L.W.Holds .elaboration st) ∧ (∀ st, ¬ L.W.Holds .proof st) ∧
      ∀ fp s, L.Elab fp s = some False := by
  refine ⟨⟨⟨fun r _ => r = .elaboration⟩, ⟨Unit, fun _ _ => True, fun _ _ => (), fun _ _ => True⟩,
    fun _ _ => some False⟩, ?_, ?_, ?_⟩
  · intro _; rfl
  · intro _ h; cases h
  · intro _ _; rfl

/-! ## The decision-level assurance -/

/-- **Certified translations hold in the fingerprinted environment** (decision level).
    When the policy does not require proof receipts the proof quorum is `0`, the hypothesis
    `DishonestBelow … 0` is unsatisfiable, and the theorem says nothing. -/
theorem certified_translation_holds_in_environment {A : AuthorityV3} {now : Nat} {S : LedgerV3}
    {r : RequestV3} (h : (decideV3 A now S r).outcome = .certifiedTranslation)
    (L : LeanAuthorityWorld)
    (hq : DishonestBelow L.W A now .proof (A.quorum .proof))
    (hK : KernelRecordSound L) (hF : LeanFrontendFaithful L A.context.envFingerprint A.registry) :
    ∀ ν, r.core.base.interpretation.selected.denote (modelOf L.env A.registry) ν := by
  have c := decideV3_certified_sound h
  have hrec := certified_receipt_quorum_assurance L.W h .proof hq
  simp only [expectedStatement] at hrec
  obtain ⟨P, hP, hPt⟩ := hK A r.core.base.candidate r.proofAxioms hrec
  have hsrc : r.core.base.candidate.leanSource = (readClaim A.registry r.core.base.candidate.claim).print := by
    rw [c.core.leanRendering, renderClaimLean_eq_print]
  rw [hsrc, hF _ c.core.leanSyntaxSafe c.core.noUnexpectedFreeVariables.2] at hP
  cases hP
  intro ν
  have hc := (lean_reading_correspondence L.env A.registry _ c.core.leanSyntaxSafe
    c.core.noUnexpectedFreeVariables.2 ν).mp (hPt ν)
  exact (decideV3_certified_preserves_denotation h _ ν).mpr hc

/-! ## The centerpiece -/

/-- **`pcs_v3_certified_wire_assurance`** — the end-to-end assurance theorem of PCS v3.

If `pcs-semantic-check --v3` certifies on raw bytes `aRaw` (authority), `rRaw` (request) and
`sRaw` (ledger snapshot and trusted clock), then there are a decoded authority `cfg`, snapshot
`snap` and request `r` such that, writing `A := cfg.toAuthority`, `I` for the selected
interpretation and `C` for the candidate:

1. **wire**: the bytes are the canonical encodings of `cfg`, `snap`, `r`, and the printed decision
   is `decideV3 A snap.now snap.state r.clamp`;
2. **well-formed and grounded**: every core gate holds (no unresolved ambiguity, unique grounding
   in the approved registry, both claims well typed and closed, supported fragment, binder
   hygiene, faithful Lean rendering, Lean-syntax anti-capture gate), and no stateless v1 receipt
   was used;
3. **uniquely identified interpretation**: every accepted confirmation envelope attests exactly
   `I`'s source text, selected structure and ambiguity resolutions in `A`'s context; any
   interpretation it could attest equals `I` on all three;
4. **semantic equivalence**: `I` and `C` have the same denotation in **every** model and valuation;
5. **certificate validity**: the link is a normal-form equality or a rewrite certificate that the
   proved-sound checker `checkCert` accepted (whoever produced it);
6. **receipts**: `ReceiptsValid` — each envelope has the known protocol version, an active,
   unrevoked key of its own role, exactly the expected statement, a validity window containing the
   clock, issuance after the ledger genesis, a fresh nonce and a verifying Ed25519 signature;
   nonces are distinct; every role meets its quorum of distinct issuers; claimed axioms are allowed;
7. **state transition**: the returned ledger is the snapshot extended by exactly the request's
   nonces (they are consumed; a later presentation of any of them is rejected,
   `stepV3_replay_rejected`);
8. **threat model**: for every role and world `W`, if fewer than the role's quorum of active keys
   are dishonest, the fact the role's statement asserts holds;
9. **truth in the fingerprinted environment**: under the explicit
   trust conditions (proof-key quorum honesty, `KernelRecordSound`, `LeanFrontendFaithful` for the
   fingerprint bound into the receipts), `I` holds in the model induced by the environment through
   the registry, for every valuation.  (If the policy does not require proof receipts, the proof
   quorum is `0` and the honesty hypothesis `DishonestBelow … 0` is unsatisfiable, so item 9 then
   gives nothing — correctly: without a proof record PCS claims no truth.)

Proposer identity, model confidence and self-asserted confirmation cannot affect any of this
(`decideV3_ignores_proposer_metadata`); a certificate search can only supply certificates that are
re-checked (item 5); `SEARCH_EXHAUSTED` is never a certification. -/
theorem pcs_v3_certified_wire_assurance {aRaw rRaw sRaw : ByteArray}
    (h : (semanticCheckV3 aRaw rRaw sRaw).decision.outcome = .certifiedTranslation) :
    ∃ cfg snap r,
      -- 1. wire
      (parseCanonicalBytes maxInputBytes aRaw).bind decAuthorityConfigV3 = some cfg ∧
      (parseCanonicalBytes maxInputBytes sRaw).bind decLedgerSnapshot = some snap ∧
      (parseCanonicalBytes maxInputBytes rRaw).bind decRequestV3 = some r ∧
      (semanticCheckV3 aRaw rRaw sRaw).decision = decideV3 cfg.toAuthority snap.now snap.state r.clamp ∧
      -- 2. well-formed, grounded, no legacy receipt
      CoreGates cfg.registry r.core.base ∧ NoLegacyReceipts r.core.base ∧
      cfg.toAuthority.wellFormedB = true ∧
      -- 3. uniquely identified interpretation
      (∀ e ∈ r.receipts, e.role = .confirmation →
        e.statement = confirmationStatement cfg.toAuthority r.core.base.interpretation ∧
        ∀ I' : Interpretation, e.statement = confirmationStatement cfg.toAuthority I' →
          I'.sourceText = r.core.base.interpretation.sourceText ∧
          I'.selected = r.core.base.interpretation.selected ∧
          I'.ambiguities = r.core.base.interpretation.ambiguities) ∧
      -- 4. semantic equivalence
      (∀ (M : Model) (ρ : String → M.Dom),
        r.core.base.interpretation.selected.denote M ρ ↔ r.core.base.candidate.claim.denote M ρ) ∧
      -- 5. certificate validity
      SemanticallyLinked r.core.base.interpretation r.core.base.candidate
        (semanticCheckV3 aRaw rRaw sRaw).decision.certificate ∧
      -- 6. receipts
      ReceiptsValid cfg.toAuthority snap.now snap.state r.clamp ∧
      -- 7. state transition
      (semanticCheckV3 aRaw rRaw sRaw).newState =
        some { snap.state with consumed := r.receipts.map (·.nonce) ++ snap.state.consumed } ∧
      (semanticCheckV3 aRaw rRaw sRaw).decision.consumed = r.receipts.map (·.nonce) ∧
      -- 8. threat model
      (∀ (W : ReceiptWorld) (role : ReceiptRole),
        DishonestBelow W cfg.toAuthority snap.now role (cfg.toAuthority.quorum role) →
          W.Holds role (expectedStatement cfg.toAuthority r.clamp role)) ∧
      -- 9. truth in the fingerprinted environment
      (∀ L : LeanAuthorityWorld,
        DishonestBelow L.W cfg.toAuthority snap.now .proof (cfg.toAuthority.quorum .proof) →
        KernelRecordSound L → LeanFrontendFaithful L cfg.context.envFingerprint cfg.registry →
        ∀ ν, r.core.base.interpretation.selected.denote (modelOf L.env cfg.registry) ν) := by
  obtain ⟨cfg, snap, r, ha, hs, hr, hdec, hc, hns⟩ := semanticCheckV3_certified_sound h
  have hcert : (decideV3 cfg.toAuthority snap.now snap.state r.clamp).outcome = .certifiedTranslation := by
    rw [← hdec]; exact h
  refine ⟨cfg, snap, r, ha, hs, hr, hdec, hc.core, hc.noLegacyReceipts, hc.authorityWellFormed,
    ?_, ?_, hc.semanticLink, hc.receipts, hns, ?_, ?_, ?_⟩
  · intro e he hrole
    have hv := hc.receipts.each e he
    have hst : e.statement = confirmationStatement cfg.toAuthority r.core.base.interpretation := by
      rw [hv.statement, hrole]; rfl
    refine ⟨hst, fun I' hI' => ?_⟩
    obtain ⟨-, h2, h3, h4⟩ := confirmationStatement_identifies (hI'.symm.trans hst)
    exact ⟨h2, h3, h4⟩
  · intro M ρ
    rcases hc.semanticLink with hn | ⟨c, _, hck⟩
    · exact alphaEquiv_denote_iff hn M ρ
    · exact translation_certificate_sound hck M ρ
  · rw [hdec, decideV3_consumed, if_pos hcert]; rfl
  · intro W role hq
    exact certified_receipt_quorum_assurance W hcert role hq
  · intro L hq hK hF ν
    exact certified_translation_holds_in_environment hcert L hq hK hF ν

end PCS.V2.Semantic.V3
