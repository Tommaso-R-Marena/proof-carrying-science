import PCS.V2.TranslationV3

/-!
# PCS v3 — adversarial rejection theorems and the receipt threat model

Every theorem here is about the **executable** state-aware decision `decideV3`.

Rejection (no cryptographic assumption needed):

* `replayed_receipt_rejected`, `expired_receipt_rejected`, `revoked_key_rejected`,
  `inactive_key_rejected`, `pre_genesis_receipt_rejected`, `unknown_version_receipt_rejected`,
  `forged_signature_rejected`, `duplicate_nonce_in_request_rejected`.
* `role_substitution_rejected` — with role-separated keys, a key registered for one role can
  never authorize an envelope of another role (e.g. a confirmation key cannot attest a kernel
  check), independently of any signature property.
* `cross_context_receipt_rejected` — a receipt whose statement was made for another authority
  context (scope, environment fingerprint, toolchain) is rejected.
* `statement_replacement_rejected` — a proof/elaboration receipt for another Lean source or
  declaration is rejected.
* `legacy_receipt_rejected` — any stateless v1 receipt makes v3 reject.
* `missing_confirmation_needs_clarification` / `missing_proof_unresolved`.
* `decideV3_ignores_proposer_metadata`.
* `decideV3_consumed_congr` — the decision depends on the ledger's consumed set only through
  the request's own nonces (the basis of the persistent store's atomic check-and-consume).

Threat model:

* `KeyHonest W verify k` — *every* envelope whose signed bytes verify under `k` asserts a fact
  that is true in the world `W`.  This single predicate covers forgery (Ed25519 broken), key
  compromise and a dishonest key holder: each of those makes the key dishonest.  PCS does **not**
  assume all keys honest.
* `certified_receipt_assurance` — certification implies, per role, a duplicate-free list of
  ≥ quorum distinct, active, unrevoked issuers that each signed exactly the expected statement;
  if any one of them is honest, the attested fact holds.
* `certified_receipt_quorum_assurance` — if fewer than `quorum` active keys of the role are
  dishonest, the attested fact holds.  With quorum 1 this is "the issuer is honest"; with quorum
  `q` it tolerates `q - 1` malicious or compromised issuers.
-/

set_option autoImplicit false

namespace PCS.V2.Semantic.V3

open PCS.V2.Json PCS.V2.Semantic PCS.V2.Semantic.Ledger

variable {A : AuthorityV3} {now : Nat} {S : LedgerV3} {r : RequestV3}

/-! ## Ledger locality -/

/-- **`decideV3_consumed_congr`.** -/
theorem decideV3_consumed_congr {T : LedgerV3} (hrev : S.revoked = T.revoked)
    (hgen : S.genesis = T.genesis)
    (h : ∀ n ∈ r.receipts.map (·.nonce), n ∈ S.consumed ↔ n ∈ T.consumed) :
    decideV3 A now S r = decideV3 A now T r := by
  exact congrArg (decideV3Core A r) (receiptPhase_consumed_congr hrev hgen h)

/-- Consequently the decision against the full ledger equals the decision against the ledger
    restricted to the request's nonces (what the persistent store passes to the checker). -/
theorem decideV3_restrict :
    decideV3 A now S r =
      decideV3 A now { S with consumed := S.consumed.filter (fun n => (r.receipts.map (·.nonce)).contains n) } r := by
  refine decideV3_consumed_congr
    (T := { S with consumed := S.consumed.filter (fun n => (r.receipts.map (·.nonce)).contains n) })
    rfl rfl ?_
  intro n hn
  simp only [List.mem_filter, List.contains_iff_mem]
  exact ⟨fun h => ⟨h, hn⟩, fun h => h.1⟩

/-! ## Per-envelope rejection -/

private theorem envelope_valid_of_certified (h : (decideV3 A now S r).outcome = .certifiedTranslation)
    {e : ReceiptEnvelope} (he : e ∈ r.receipts) : EnvelopeValid A now S r e :=
  (decideV3_certified_sound h).receipts.each e he

theorem replayed_receipt_rejected {e : ReceiptEnvelope} (he : e ∈ r.receipts)
    (hn : e.nonce ∈ S.consumed) : (decideV3 A now S r).outcome ≠ .certifiedTranslation :=
  fun h => (envelope_valid_of_certified h he).fresh hn

theorem expired_receipt_rejected {e : ReceiptEnvelope} (he : e ∈ r.receipts)
    (hx : e.expiresAt ≤ now) : (decideV3 A now S r).outcome ≠ .certifiedTranslation := by
  intro h
  have := (envelope_valid_of_certified h he).notExpired
  omega

theorem future_receipt_rejected {e : ReceiptEnvelope} (he : e ∈ r.receipts)
    (hx : now < e.issuedAt) : (decideV3 A now S r).outcome ≠ .certifiedTranslation := by
  intro h
  have := (envelope_valid_of_certified h he).issuedBeforeNow
  omega

theorem revoked_key_rejected {e : ReceiptEnvelope} (he : e ∈ r.receipts)
    (hr : e.issuer ∈ A.revoked ∨ e.issuer ∈ S.revoked) :
    (decideV3 A now S r).outcome ≠ .certifiedTranslation :=
  fun h => (envelope_valid_of_certified h he).notRevoked (List.mem_append.mpr hr)

theorem inactive_key_rejected {e : ReceiptEnvelope} (he : e ∈ r.receipts)
    (hk : ∀ k ∈ A.keys, k.key = e.issuer → k.role = e.role → ¬ (k.notBefore ≤ now ∧ now < k.notAfter)) :
    (decideV3 A now S r).outcome ≠ .certifiedTranslation := by
  intro h
  have hact := (envelope_valid_of_certified h he).activeKey
  unfold activeKeys at hact
  obtain ⟨k, hk', hkey⟩ := List.mem_map.mp hact
  simp only [List.mem_filter, Bool.and_eq_true, beq_iff_eq, decide_eq_true_eq] at hk'
  exact hk k hk'.1 hkey hk'.2.1.1 ⟨hk'.2.1.2, hk'.2.2⟩

theorem pre_genesis_receipt_rejected {e : ReceiptEnvelope} (he : e ∈ r.receipts)
    (hg : e.issuedAt < S.genesis) : (decideV3 A now S r).outcome ≠ .certifiedTranslation := by
  intro h
  have := (envelope_valid_of_certified h he).afterGenesis
  omega

theorem unknown_version_receipt_rejected {e : ReceiptEnvelope} (he : e ∈ r.receipts)
    (hv : e.version ≠ protocolVersion) : (decideV3 A now S r).outcome ≠ .certifiedTranslation :=
  fun h => hv (envelope_valid_of_certified h he).version

theorem forged_signature_rejected {e : ReceiptEnvelope} (he : e ∈ r.receipts)
    (hs : A.verify e.issuer (envelopeBytes e) e.signature = false) :
    (decideV3 A now S r).outcome ≠ .certifiedTranslation := by
  intro h
  have := (envelope_valid_of_certified h he).signature
  rw [hs] at this; cases this

theorem duplicate_nonce_in_request_rejected (hd : ¬ (r.receipts.map (·.nonce)).Nodup) :
    (decideV3 A now S r).outcome ≠ .certifiedTranslation :=
  fun h => hd (decideV3_certified_sound h).receipts.noncesDistinct

/-! ## Role separation and domain separation -/

/-- **`role_substitution_rejected`.** -/
theorem role_substitution_rejected (hwf : A.wellFormedB = true) {e : ReceiptEnvelope}
    (he : e ∈ r.receipts) {k : KeyEntry} (hk : k ∈ A.keys) (hkey : k.key = e.issuer)
    (hrole : k.role ≠ e.role) : (decideV3 A now S r).outcome ≠ .certifiedTranslation := by
  intro h
  have hact := (envelope_valid_of_certified h he).activeKey
  unfold activeKeys at hact
  obtain ⟨k', hk', hkey'⟩ := List.mem_map.mp hact
  simp only [List.mem_filter, Bool.and_eq_true, beq_iff_eq, decide_eq_true_eq] at hk'
  unfold AuthorityV3.wellFormedB at hwf
  simp only [Bool.and_eq_true, List.all_eq_true, Bool.or_eq_true, bne_iff_ne, ne_eq,
    beq_iff_eq] at hwf
  rcases hwf.1 k hk k' hk'.1 with hne | heq
  · exact hne (hkey.trans hkey'.symm)
  · exact hrole (heq.trans hk'.2.1.1)

theorem encContext_inj {A A' : AuthorityV3} (h : encContext A = encContext A') :
    A.context = A'.context := by
  unfold encContext at h
  simp only [JVal.obj.injEq, List.cons.injEq, Prod.mk.injEq, JVal.str.injEq, true_and,
    and_true] at h
  obtain ⟨h1, -, h3, h4⟩ := h
  cases hA : A.context; cases hA' : A'.context
  rw [hA, hA'] at h1 h3 h4
  simp_all

theorem proofStatement_inj {A A' : AuthorityV3} {c c' : Candidate} {axs axs' : List String}
    (h : proofStatement A c axs = proofStatement A' c' axs') :
    A.context = A'.context ∧ c.leanSource = c'.leanSource ∧ c.declName = c'.declName ∧
      encStrs axs = encStrs axs' := by
  unfold proofStatement at h
  simp only [JVal.obj.injEq, List.cons.injEq, Prod.mk.injEq, JVal.str.injEq, true_and,
    and_true] at h
  obtain ⟨h1, h2, h3, h4⟩ := h
  exact ⟨encContext_inj h2, h4, h3, h1⟩

theorem elaborationStatement_inj {A A' : AuthorityV3} {c c' : Candidate}
    (h : elaborationStatement A c = elaborationStatement A' c') :
    A.context = A'.context ∧ c.leanSource = c'.leanSource ∧ c.declName = c'.declName := by
  unfold elaborationStatement at h
  simp only [JVal.obj.injEq, List.cons.injEq, Prod.mk.injEq, JVal.str.injEq, true_and,
    and_true] at h
  obtain ⟨h1, h2, h3⟩ := h
  exact ⟨encContext_inj h1, h3, h2⟩

theorem confirmationStatement_inj {A A' : AuthorityV3} {I I' : Interpretation}
    (h : confirmationStatement A I = confirmationStatement A' I') :
    A.context = A'.context ∧ I.sourceText = I'.sourceText ∧ encClaim I.selected = encClaim I'.selected ∧
      encAmbiguities I.ambiguities = encAmbiguities I'.ambiguities := by
  unfold confirmationStatement at h
  simp only [JVal.obj.injEq, List.cons.injEq, Prod.mk.injEq, JVal.str.injEq, true_and,
    and_true] at h
  obtain ⟨h1, h2, h3, h4⟩ := h
  exact ⟨encContext_inj h2, h4, h3, h1⟩

/-- The three statement kinds are pairwise distinct (purpose domain separation). -/
theorem statements_domain_separated (A A' A'' : AuthorityV3) (I : Interpretation)
    (c c' : Candidate) (axs : List String) :
    confirmationStatement A I ≠ elaborationStatement A' c ∧
    confirmationStatement A I ≠ proofStatement A' c axs ∧
    elaborationStatement A' c ≠ proofStatement A'' c' axs := by
  refine ⟨?_, ?_, ?_⟩ <;>
  · intro h
    simp [confirmationStatement, elaborationStatement, proofStatement] at h

/-- **`cross_context_receipt_rejected`**: an envelope whose statement was produced for a
    different authority context (another scope, environment fingerprint or toolchain) is
    rejected, whichever role it claims. -/
theorem cross_context_receipt_rejected {e : ReceiptEnvelope} (he : e ∈ r.receipts)
    {A' : AuthorityV3} (hctx : A'.context ≠ A.context)
    (hs : e.statement = confirmationStatement A' r.core.base.interpretation ∨
      e.statement = elaborationStatement A' r.core.base.candidate ∨
      e.statement = proofStatement A' r.core.base.candidate r.proofAxioms) :
    (decideV3 A now S r).outcome ≠ .certifiedTranslation := by
  intro h
  have hst := (envelope_valid_of_certified h he).statement
  rcases hs with hs | hs | hs <;> rw [hs] at hst <;>
    cases hrole : e.role <;> rw [hrole] at hst <;> simp only [expectedStatement] at hst
  · exact hctx (confirmationStatement_inj hst).1
  · exact (statements_domain_separated A' A A r.core.base.interpretation r.core.base.candidate
      r.core.base.candidate r.proofAxioms).1 hst
  · exact (statements_domain_separated A' A A r.core.base.interpretation r.core.base.candidate
      r.core.base.candidate r.proofAxioms).2.1 hst
  · exact (statements_domain_separated A A' A r.core.base.interpretation r.core.base.candidate
      r.core.base.candidate r.proofAxioms).1 hst.symm
  · exact hctx (elaborationStatement_inj hst).1
  · exact (statements_domain_separated A A' A r.core.base.interpretation r.core.base.candidate
      r.core.base.candidate r.proofAxioms).2.2 hst
  · exact (statements_domain_separated A A' A r.core.base.interpretation r.core.base.candidate
      r.core.base.candidate r.proofAxioms).2.1 hst.symm
  · exact (statements_domain_separated A A A' r.core.base.interpretation r.core.base.candidate
      r.core.base.candidate r.proofAxioms).2.2 hst.symm
  · exact hctx (proofStatement_inj hst).1

/-- **`statement_replacement_rejected`**: a proof receipt attesting a kernel check of another
    Lean source or declaration (in any context) is rejected. -/
theorem statement_replacement_rejected {e : ReceiptEnvelope} (he : e ∈ r.receipts)
    (hrole : e.role = .proof) {A' : AuthorityV3} {c : Candidate} {axs : List String}
    (hs : e.statement = proofStatement A' c axs)
    (hdiff : c.leanSource ≠ r.core.base.candidate.leanSource ∨
      c.declName ≠ r.core.base.candidate.declName) :
    (decideV3 A now S r).outcome ≠ .certifiedTranslation := by
  intro h
  have hst := (envelope_valid_of_certified h he).statement
  rw [hs, hrole] at hst
  simp only [expectedStatement] at hst
  obtain ⟨-, h2, h3, -⟩ := proofStatement_inj hst
  rcases hdiff with hd | hd
  · exact hd h2
  · exact hd h3

/-- **`legacy_receipt_rejected`**: v3 never accepts with a stateless v1 receipt present. -/
theorem legacy_receipt_rejected
    (h : r.core.base.confirmation.isSome ∨ r.core.base.elaboration.isSome ∨ r.core.base.proof.isSome) :
    (decideV3 A now S r).outcome ≠ .certifiedTranslation := by
  intro hc
  obtain ⟨h1, h2, h3⟩ := (decideV3_certified_sound hc).noLegacyReceipts
  rw [h1, h2, h3] at h
  simp at h

/-! ## Missing receipts -/

theorem quorum_not_met_rejected {role : ReceiptRole}
    (hq : (issuersOf role r.receipts).length < A.quorum role) :
    (decideV3 A now S r).outcome ≠ .certifiedTranslation := by
  intro h
  have := (decideV3_certified_sound h).receipts.quorum role
  omega

/-- No confirmation envelope ⇒ not certified (the model's own "confirmed" flag is irrelevant). -/
theorem missing_confirmation_rejected (h0 : ∀ e ∈ r.receipts, e.role ≠ .confirmation) :
    (decideV3 A now S r).outcome ≠ .certifiedTranslation := by
  apply quorum_not_met_rejected (role := .confirmation)
  have : issuersOf .confirmation r.receipts = [] := by
    cases hl : issuersOf .confirmation r.receipts with
    | nil => rfl
    | cons k ks =>
      have : k ∈ issuersOf .confirmation r.receipts := by rw [hl]; exact List.mem_cons_self
      obtain ⟨e, he, hr, -⟩ := mem_issuersOf.mp this
      exact absurd hr (h0 e he)
  rw [this]
  simp only [AuthorityV3.quorum, List.length_nil]
  omega

/-- A required proof with no proof envelope ⇒ not certified. -/
theorem missing_proof_rejected (hreq : A.requireProof = true)
    (h0 : ∀ e ∈ r.receipts, e.role ≠ .proof) :
    (decideV3 A now S r).outcome ≠ .certifiedTranslation := by
  apply quorum_not_met_rejected (role := .proof)
  have : issuersOf .proof r.receipts = [] := by
    cases hl : issuersOf .proof r.receipts with
    | nil => rfl
    | cons k ks =>
      have : k ∈ issuersOf .proof r.receipts := by rw [hl]; exact List.mem_cons_self
      obtain ⟨e, he, hr, -⟩ := mem_issuersOf.mp this
      exact absurd hr (h0 e he)
  rw [this]
  simp only [AuthorityV3.quorum, hreq, if_true, List.length_nil]
  omega

/-! ## Metadata independence -/

/-- **The v3 authority does not trust proposer metadata**: proposer identities, self-reported
    confidence and a model's own "confirmed" flag never influence the decision (or the ledger). -/
theorem decideV3_ignores_proposer_metadata (conf : Nat) (p₁ p₂ : String) (asserted : Bool) :
    decideV3 A now S { r with core := { r.core with base := { r.core.base with
      interpretation := { r.core.base.interpretation with proposer := p₁, modelAssertsConfirmed := asserted },
      candidate := { r.core.base.candidate with proposer := p₂, modelConfidence := conf } } } } =
    decideV3 A now S r := by
  obtain ⟨⟨⟨I, cf, c, el, pr⟩, cert, b⟩, axs, es⟩ := r
  cases I; cases c; rfl

/-! ## Threat model: honest keys and quorums -/

/-- What receipt statements assert about the world (e.g. that the named kernel checker accepted
    the declaration in the fingerprinted environment). -/
structure ReceiptWorld where
  Holds : ReceiptRole → JVal → Prop

/-- **Honest key** (explicit trust predicate): every envelope whose signed bytes verify under
    `k` asserts a true fact.  Forgery, key compromise and a lying key holder each make a key
    dishonest; no key is assumed honest by PCS. -/
def KeyHonest (W : ReceiptWorld) (verify : String → List UInt8 → String → Bool) (k : String) : Prop :=
  ∀ e : ReceiptEnvelope, verify k (envelopeBytes e) e.signature = true → W.Holds e.role e.statement

/-- **`certified_receipt_assurance`.** -/
theorem certified_receipt_assurance (W : ReceiptWorld)
    (h : (decideV3 A now S r).outcome = .certifiedTranslation) (role : ReceiptRole) :
    (issuersOf role r.receipts).Nodup ∧
    A.quorum role ≤ (issuersOf role r.receipts).length ∧
    (∀ k ∈ issuersOf role r.receipts, k ∈ activeKeys A now role ∧ k ∉ A.revoked ++ S.revoked ∧
      ∃ e ∈ r.receipts, e.role = role ∧ e.issuer = k ∧
        e.statement = expectedStatement A r role ∧
        A.verify k (envelopeBytes e) e.signature = true) ∧
    ((∃ k ∈ issuersOf role r.receipts, KeyHonest W A.verify k) →
      W.Holds role (expectedStatement A r role)) := by
  have hv := (decideV3_certified_sound h).receipts
  have hk : ∀ k ∈ issuersOf role r.receipts, k ∈ activeKeys A now role ∧ k ∉ A.revoked ++ S.revoked ∧
      ∃ e ∈ r.receipts, e.role = role ∧ e.issuer = k ∧
        e.statement = expectedStatement A r role ∧
        A.verify k (envelopeBytes e) e.signature = true := by
    intro k hk
    obtain ⟨e, he, hr, hi⟩ := mem_issuersOf.mp hk
    have v := hv.each e he
    subst hr hi
    exact ⟨v.activeKey, v.notRevoked, e, he, rfl, rfl, v.statement, v.signature⟩
  refine ⟨dedup_nodup _, hv.quorum role, hk, ?_⟩
  rintro ⟨k, hmem, hhon⟩
  obtain ⟨-, -, e, -, hr, -, hs, hsig⟩ := hk k hmem
  have := hhon e hsig
  rw [hr, hs] at this
  exact this

/-- Fewer than `q` active keys of the role are dishonest. -/
def DishonestBelow (W : ReceiptWorld) (A : AuthorityV3) (now : Nat) (role : ReceiptRole) (q : Nat) :
    Prop :=
  ∀ ks : List String, ks.Nodup → (∀ k ∈ ks, k ∈ activeKeys A now role ∧ ¬ KeyHonest W A.verify k) →
    ks.length < q

/-- **`certified_receipt_quorum_assurance`.** -/
theorem certified_receipt_quorum_assurance (W : ReceiptWorld)
    (h : (decideV3 A now S r).outcome = .certifiedTranslation) (role : ReceiptRole)
    (hq : DishonestBelow W A now role (A.quorum role)) :
    W.Holds role (expectedStatement A r role) := by
  obtain ⟨hnd, hlen, hk, hhon⟩ := certified_receipt_assurance W h role
  apply hhon
  apply Classical.byContradiction
  intro hno
  have hall : ∀ k ∈ issuersOf role r.receipts, k ∈ activeKeys A now role ∧ ¬ KeyHonest W A.verify k :=
    fun k hm => ⟨(hk k hm).1, fun hh => hno ⟨k, hm, hh⟩⟩
  have := hq _ hnd hall
  omega

/-- With quorum `q`, a single honest issuer of the role suffices, and `q - 1` malicious or
    compromised issuers cannot make a false kernel-check record certify. -/
theorem certified_kernel_check_record (W : ReceiptWorld)
    (h : (decideV3 A now S r).outcome = .certifiedTranslation) (hreq : A.requireProof = true)
    (hq : DishonestBelow W A now .proof (A.quorum .proof)) :
    W.Holds .proof (proofStatement A r.core.base.candidate r.proofAxioms) ∧
    ∀ ax ∈ r.proofAxioms, ax ∈ A.allowedAxioms := by
  have _ := hreq
  exact ⟨certified_receipt_quorum_assurance W h .proof hq,
    (decideV3_certified_sound h).receipts.axiomsAllowed⟩

end PCS.V2.Semantic.V3
