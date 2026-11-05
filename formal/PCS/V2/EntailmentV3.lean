import PCS.V2.AssuranceV3

/-!
# PCS v3 — biconditional sugar and a separate, explicitly authorized strengthening mode

**Equivalence is not entailment.**  A candidate that is logically *stronger* than the selected
interpretation (it implies the interpretation but not conversely) is **not** a meaning-preserving
translation.  v3 keeps the equivalence-only acceptance (`decideV3`, `CERTIFIED_TRANSLATION`)
exactly as it was and adds a *separate* decision `decideStrengtheningV3` whose only accepting
outcome is `CERTIFIED_STRENGTHENING`:

* the semantic check is a sound syntactic entailment checker on nameless normal forms
  (`NFormula.entails`, `entails_sound`), lifted to claims (`NClaim.strengthensB`,
  `strengthens_sound`): **candidate ⊨ interpretation** in every model and valuation;
* explicit authorization is required: the confirmation-role receipts must attest a distinct
  statement, `strengtheningStatement` (purpose `"strengthening-authorization"`), binding the
  interpretation **and** the exact stronger candidate; it is domain separated from an ordinary
  confirmation (`strengthening_statement_ne_confirmation`) so neither can be replayed as the other;
* `decideStrengtheningV3` can never produce `CERTIFIED_TRANSLATION` (different result type), and
  a strengthening can be certified for a pair that is **not** equivalent
  (`strengthening_is_not_equivalence`).

`Formula.iff` is biconditional sugar desugared to `(φ → ψ) ∧ (ψ → φ)` before checking; its
meaning is exactly `↔` (`Formula.iff_denote`).
-/

set_option autoImplicit false

namespace PCS.V2.Semantic

/-! ## Biconditional sugar -/

/-- `φ ↔ ψ`, desugared. -/
def Formula.iff (φ ψ : Formula) : Formula := .and (.imp φ ψ) (.imp ψ φ)

/-- **`Formula.iff_denote`**: the desugaring means exactly `↔`. -/
theorem Formula.iff_denote (M : Model) (ρ : String → M.Dom) (φ ψ : Formula) :
    (Formula.iff φ ψ).denote M ρ ↔ (φ.denote M ρ ↔ ψ.denote M ρ) := by
  simp only [Formula.iff, Formula.denote]
  exact ⟨fun ⟨a, b⟩ => ⟨a, b⟩, fun h => ⟨h.mp, h.mpr⟩⟩

/-! ## Sound syntactic entailment on nameless formulas -/

/-- Entailment `φ ⊨ ψ`, with fuel (soundness holds for every fuel). -/
def entailsF : Nat → NFormula → NFormula → Bool
  | 0, φ, ψ => decide (φ = ψ)
  | n + 1, φ, ψ =>
    decide (φ = ψ) ||
    (match ψ with | .tt => true | _ => false) ||
    (match φ with | .ff => true | _ => false) ||
    (match ψ with | .and ψ₁ ψ₂ => entailsF n φ ψ₁ && entailsF n φ ψ₂ | _ => false) ||
    (match φ with | .or φ₁ φ₂ => entailsF n φ₁ ψ && entailsF n φ₂ ψ | _ => false) ||
    (match φ with | .and φ₁ φ₂ => entailsF n φ₁ ψ || entailsF n φ₂ ψ | _ => false) ||
    (match ψ with | .or ψ₁ ψ₂ => entailsF n φ ψ₁ || entailsF n φ ψ₂ | _ => false) ||
    (match φ, ψ with
      | .imp a b, .imp c d => entailsF n c a && entailsF n b d
      | .not a, .not b => entailsF n b a
      | .quant q s a, .quant q' s' b => decide (q = q') && decide (s = s') && entailsF n a b
      | _, _ => false)

/-- Size of a nameless formula (fuel bound). -/
def NFormula.size : NFormula → Nat
  | .not φ | .quant _ _ φ => NFormula.size φ + 1
  | .and φ ψ | .or φ ψ | .imp φ ψ => NFormula.size φ + NFormula.size ψ + 1
  | _ => 1

/-- **The entailment checker.** -/
def NFormula.entails (φ ψ : NFormula) : Bool := entailsF (φ.size + ψ.size) φ ψ

/-- **`entailsF_sound`**: the checker is sound for every model, valuation, environment and fuel. -/
theorem entailsF_sound (M : Model) (ρ : String → M.Dom) :
    ∀ (n : Nat) (φ ψ : NFormula), entailsF n φ ψ = true →
      ∀ env, NFormula.denote M ρ env φ → NFormula.denote M ρ env ψ
  | 0, φ, ψ, h, env, hφ => by
    simp only [entailsF, decide_eq_true_eq] at h
    subst h; exact hφ
  | n + 1, φ, ψ, h, env, hφ => by
    have ih := entailsF_sound M ρ n
    simp only [entailsF, Bool.or_eq_true, decide_eq_true_eq] at h
    rcases h with ((((((h | h) | h) | h) | h) | h) | h) | h
    · subst h; exact hφ
    · cases ψ <;> simp at h; trivial
    · cases φ <;> simp at h; exact hφ.elim
    · cases ψ <;> simp at h
      exact ⟨ih _ _ h.1 env hφ, ih _ _ h.2 env hφ⟩
    · cases φ <;> simp at h
      rcases hφ with hφ | hφ
      · exact ih _ _ h.1 env hφ
      · exact ih _ _ h.2 env hφ
    · cases φ <;> simp at h
      rcases h with h | h
      · exact ih _ _ h env hφ.1
      · exact ih _ _ h env hφ.2
    · cases ψ <;> simp at h
      rcases h with h | h
      · exact Or.inl (ih _ _ h env hφ)
      · exact Or.inr (ih _ _ h env hφ)
    · cases φ <;> cases ψ <;> simp at h
      · exact fun ha => hφ (ih _ _ h env ha)
      · exact fun hc => ih _ _ h.2 env (hφ (ih _ _ h.1 env hc))
      · rename_i q s a q' s' b
        obtain ⟨⟨rfl, rfl⟩, hab⟩ := h
        cases q
        · exact fun d hd => ih _ _ hab _ (hφ d hd)
        · obtain ⟨d, hd, ha⟩ := hφ
          exact ⟨d, hd, ih _ _ hab _ ha⟩

theorem entails_sound {φ ψ : NFormula} (h : φ.entails ψ = true) (M : Model) (ρ : String → M.Dom)
    (env : Nat → M.Dom) : NFormula.denote M ρ env φ → NFormula.denote M ρ env ψ :=
  entailsF_sound M ρ _ φ ψ h env

/-! ## Claim-level strengthening -/

/-- Conjunction of a list of formulas. -/
def conjAll : List NFormula → NFormula
  | [] => .tt
  | a :: as => .and a (conjAll as)

theorem conjAll_denote (M : Model) (ρ : String → M.Dom) (env : Nat → M.Dom) :
    ∀ (as : List NFormula), (∀ a ∈ as, NFormula.denote M ρ env a) →
      NFormula.denote M ρ env (conjAll as)
  | [], _ => trivial
  | a :: as, h => ⟨h a (List.mem_cons_self ..), conjAll_denote M ρ env as
      (fun b hb => h b (List.mem_cons_of_mem _ hb))⟩

/-- **`C` strengthens `I`** (`C ⊨ I`): the same parameter sorts, every assumption of `C` follows
    from the assumptions of `I`, and `I`'s conclusion follows from `I`'s assumptions together
    with `C`'s conclusion. -/
def NClaim.strengthensB (C I : NClaim) : Bool :=
  decide (C.paramSorts = I.paramSorts) &&
  C.assumptions.all (fun a => (conjAll I.assumptions).entails a) &&
  (NFormula.and (conjAll I.assumptions) C.conclusion).entails I.conclusion

theorem ndenoteParams_mono (M : Model) (ρ : String → M.Dom) :
    ∀ (ss : List SortId) (env : Nat → M.Dom) (K₁ K₂ : (Nat → M.Dom) → Prop),
      (∀ e, K₁ e → K₂ e) → ndenoteParams M ρ ss env K₁ → ndenoteParams M ρ ss env K₂
  | [], env, _, _, h, h₁ => h env h₁
  | _ :: ss, env, K₁, K₂, h, h₁ => fun d hd =>
      ndenoteParams_mono M ρ ss (consEnv d env) K₁ K₂ h (h₁ d hd)

theorem NClaim.strengthens_sound {C I : NClaim} (h : C.strengthensB I = true) (M : Model)
    (ρ : String → M.Dom) (env : Nat → M.Dom) : C.denote M ρ env → I.denote M ρ env := by
  simp only [NClaim.strengthensB, Bool.and_eq_true, decide_eq_true_eq, List.all_eq_true] at h
  obtain ⟨⟨hps, hass⟩, hcon⟩ := h
  unfold NClaim.denote
  rw [hps]
  apply ndenoteParams_mono
  intro e hC hIa
  have hconj := conjAll_denote M ρ e I.assumptions hIa
  have hCc := hC (fun a ha => entails_sound (hass a ha) M ρ e hconj)
  exact entails_sound hcon M ρ e ⟨hconj, hCc⟩

/-- **`strengthens_sound`**: if the checker accepts, the candidate implies the interpretation in
    every model and valuation. -/
theorem strengthens_sound {C I : SemanticClaim} (h : C.normalize.strengthensB I.normalize = true)
    (M : Model) (ρ : String → M.Dom) : C.denote M ρ → I.denote M ρ := by
  let env : Nat → M.Dom := fun _ => ρ ""
  rw [SemanticClaim.normalize_denote M ρ env C, SemanticClaim.normalize_denote M ρ env I]
  exact NClaim.strengthens_sound h M ρ env

end PCS.V2.Semantic

namespace PCS.V2.Semantic.V3

open PCS.V2.Json PCS.V2.Canonical PCS.V2.Semantic PCS.V2.Semantic.Ledger

/-! ## The strengthening decision -/

/-- What an authorization of a *deliberate strengthening* must attest: the interpretation, the
    exact stronger candidate claim, and the context — under a purpose distinct from
    `"confirmation"`. -/
def strengtheningStatement (A : AuthorityV3) (I : Interpretation) (c : Candidate) : JVal :=
  .obj [("ambiguities", encAmbiguities I.ambiguities), ("candidate", encClaim c.claim),
    ("context", encContext A), ("purpose", .str "strengthening-authorization"),
    ("selected", encClaim I.selected), ("source_text", .str I.sourceText)]

/-- Expected statement per role in strengthening mode. -/
def strengthStatement (A : AuthorityV3) (r : RequestV3) : ReceiptRole → JVal
  | .confirmation => strengtheningStatement A r.core.base.interpretation r.core.base.candidate
  | .elaboration => elaborationStatement A r.core.base.candidate
  | .proof => proofStatement A r.core.base.candidate r.proofAxioms

theorem strengthening_statement_ne_confirmation (A A' : AuthorityV3) (I I' : Interpretation)
    (c : Candidate) : strengtheningStatement A I c ≠ confirmationStatement A' I' := by
  intro h
  simp only [strengtheningStatement, confirmationStatement, JVal.obj.injEq, List.cons.injEq,
    Prod.mk.injEq] at h
  exact absurd h.2.1.1 (by decide)

/-- Receipt phase of strengthening mode (same ledger protocol, strengthening statements). -/
def strengthReceiptPhase (A : AuthorityV3) (now : Nat) (S : LedgerV3) (r : RequestV3) :
    Except ReceiptFailure (List String) :=
  match r.proofAxioms.find? (fun ax => !A.allowedAxioms.contains ax) with
  | some ax => .error (.axiomNotAllowed ax)
  | none =>
    match acceptAllV3 (policy A S now) (strengthStatement A r) S.genesis ⟨S.consumed⟩ r.receipts with
    | .error f => .error f
    | .ok ns =>
      match quorumFailure A r.receipts with
      | some f => .error f
      | none => .ok ns

/-- Strengthening-mode outcomes.  There is no `CERTIFIED_TRANSLATION` here. -/
inductive StrengthOutcome where
  | certifiedStrengthening
  | notAStrengthening
  | invalidProposal
  | receiptRejected (f : ReceiptFailure)
  | invalidAuthority
  deriving Repr, DecidableEq, Inhabited

def StrengthOutcome.name : StrengthOutcome → String
  | .certifiedStrengthening => "CERTIFIED_STRENGTHENING"
  | .notAStrengthening => "NOT_A_STRENGTHENING"
  | .invalidProposal => "INVALID_PROPOSAL"
  | .receiptRejected _ => "RECEIPT_REJECTED"
  | .invalidAuthority => "INVALID_AUTHORITY"

/-- **The strengthening decision** (separate from `decideV3`). -/
def decideStrengtheningV3 (A : AuthorityV3) (now : Nat) (S : LedgerV3) (r : RequestV3) :
    StrengthOutcome :=
  let req := r.core.base
  if !A.wellFormedB then .invalidAuthority
  else if !(coreDiagnostics A.registry req ++ legacyDiagnostics req).isEmpty then .invalidProposal
  else if !(req.candidate.claim.normalize.strengthensB req.interpretation.selected.normalize) then
    .notAStrengthening
  else match strengthReceiptPhase A now S r with
    | .error f => .receiptRejected f
    | .ok _ => .certifiedStrengthening

/-- Ledger transition of strengthening mode (consume only on certification). -/
def stepStrengtheningV3 (A : AuthorityV3) (now : Nat) (S : LedgerV3) (r : RequestV3) :
    StrengthOutcome × LedgerV3 :=
  let o := decideStrengtheningV3 A now S r
  (o, if o = .certifiedStrengthening then
        { S with consumed := r.receipts.map (·.nonce) ++ S.consumed } else S)

/-- **`decideStrengtheningV3_sound`**: a certified strengthening has a well-formed authority, all
    core gates, no legacy receipt, a candidate that **implies** the selected interpretation in
    every model and valuation, and every envelope accepted under the ledger protocol against the
    strengthening statements (so the confirmation-role issuers explicitly authorized *this*
    stronger candidate), with distinct fresh nonces and quorums met. -/
theorem decideStrengtheningV3_sound {A : AuthorityV3} {now : Nat} {S : LedgerV3} {r : RequestV3}
    (h : decideStrengtheningV3 A now S r = .certifiedStrengthening) :
    A.wellFormedB = true ∧ CoreGates A.registry r.core.base ∧ NoLegacyReceipts r.core.base ∧
    (∀ (M : Model) (ρ : String → M.Dom),
      r.core.base.candidate.claim.denote M ρ → r.core.base.interpretation.selected.denote M ρ) ∧
    (∀ ax ∈ r.proofAxioms, ax ∈ A.allowedAxioms) ∧
    (∀ e ∈ r.receipts, S.genesis ≤ e.issuedAt ∧
      EnvOK (policy A S now) e.role (strengthStatement A r e.role) e ∧ e.nonce ∉ S.consumed) ∧
    (r.receipts.map (·.nonce)).Nodup ∧
    (∀ role, A.quorum role ≤ (issuersOf role r.receipts).length) := by
  unfold decideStrengtheningV3 at h
  simp only at h
  split at h
  · cases h
  rename_i hwf
  split at h
  · cases h
  rename_i hcore
  split at h
  · cases h
  rename_i hstr
  split at h
  · cases h
  rename_i ns hrp
  simp only [Bool.not_eq_true', Bool.not_eq_false] at hwf hstr
  have hc : coreDiagnostics A.registry r.core.base ++ legacyDiagnostics r.core.base = [] := by
    revert hcore; cases (coreDiagnostics A.registry r.core.base ++ legacyDiagnostics r.core.base)
    · intro; rfl
    · simp
  have hc2 := List.append_eq_nil_iff.mp hc
  unfold strengthReceiptPhase at hrp
  split at hrp
  · cases hrp
  rename_i hfind
  split at hrp
  · cases hrp
  rename_i ns' hacc
  split at hrp
  · cases hrp
  rename_i hq
  obtain ⟨hall, hnd, _⟩ := acceptAllV3_ok_iff.mp hacc
  refine ⟨by simpa using hwf, (coreDiagnostics_nil _ _).mp hc2.1, (legacyDiagnostics_nil _).mp hc2.2,
    fun M ρ => strengthens_sound (by simpa using hstr) M ρ, ?_, hall, hnd,
    (quorumFailure_none_iff A r.receipts).mp hq⟩
  intro ax hax
  have := List.find?_eq_none.mp hfind ax hax
  simpa using this

/-- Strengthening mode consumes nonces only on certification. -/
theorem stepStrengtheningV3_rejected_no_consumption {A : AuthorityV3} {now : Nat} {S : LedgerV3}
    {r : RequestV3} (h : decideStrengtheningV3 A now S r ≠ .certifiedStrengthening) :
    (stepStrengtheningV3 A now S r).2 = S := by
  simp only [stepStrengtheningV3, if_neg h]

/-- An ordinary confirmation receipt never authorizes a strengthening: if any confirmation
    envelope attests an ordinary `confirmationStatement`, the strengthening is not certified. -/
theorem ordinary_confirmation_cannot_authorize_strengthening {A : AuthorityV3} {now : Nat}
    {S : LedgerV3} {r : RequestV3} {e : ReceiptEnvelope} (he : e ∈ r.receipts)
    (hrole : e.role = .confirmation) {A' : AuthorityV3} {I' : Interpretation}
    (hst : e.statement = confirmationStatement A' I') :
    decideStrengtheningV3 A now S r ≠ .certifiedStrengthening := by
  intro h
  obtain ⟨-, -, -, -, -, hall, -⟩ := decideStrengtheningV3_sound h
  have hs := (hall e he).2.1.statement
  rw [hrole] at hs
  exact strengthening_statement_ne_confirmation A A' r.core.base.interpretation I'
    r.core.base.candidate (hs.symm.trans hst)


/-! ## Wire front end of strengthening mode (`pcs-semantic-check --v3-strengthen`) -/

/-- The pure function run by `pcs-semantic-check --v3-strengthen`: outcome and new ledger
    (`none` on malformed input). -/
def strengthenCheckV3 (authorityRaw requestRaw stateRaw : ByteArray) :
    StrengthOutcome × Option LedgerV3 :=
  match (parseCanonicalBytes maxInputBytes authorityRaw).bind decAuthorityConfigV3,
    (parseCanonicalBytes maxInputBytes stateRaw).bind decLedgerSnapshot,
    (parseCanonicalBytes maxInputBytes requestRaw).bind decRequestV3 with
  | some cfg, some snap, some r =>
    let p := stepStrengtheningV3 cfg.toAuthority snap.now snap.state r
    (p.1, some p.2)
  | _, _, _ => (.invalidProposal, none)

/-- **`strengthenCheckV3_certified_sound`**: `CERTIFIED_STRENGTHENING` on raw bytes means the
    inputs decode and the decoded request is a certified strengthening (candidate ⊨ selected
    interpretation in every model; explicitly authorized; receipts valid and fresh), and the new
    ledger is the snapshot extended by exactly the request's nonces. -/
theorem strengthenCheckV3_certified_sound {aRaw rRaw sRaw : ByteArray}
    (h : (strengthenCheckV3 aRaw rRaw sRaw).1 = .certifiedStrengthening) :
    ∃ cfg snap r, (parseCanonicalBytes maxInputBytes aRaw).bind decAuthorityConfigV3 = some cfg ∧
      (parseCanonicalBytes maxInputBytes sRaw).bind decLedgerSnapshot = some snap ∧
      (parseCanonicalBytes maxInputBytes rRaw).bind decRequestV3 = some r ∧
      decideStrengtheningV3 cfg.toAuthority snap.now snap.state r = .certifiedStrengthening ∧
      (∀ (M : Model) (ρ : String → M.Dom),
        r.core.base.candidate.claim.denote M ρ → r.core.base.interpretation.selected.denote M ρ) ∧
      (strengthenCheckV3 aRaw rRaw sRaw).2 =
        some { snap.state with consumed := r.receipts.map (·.nonce) ++ snap.state.consumed } := by
  unfold strengthenCheckV3 at h ⊢
  split at h
  · rename_i cfg snap r ha hs hr
    have hd : decideStrengtheningV3 cfg.toAuthority snap.now snap.state r = .certifiedStrengthening := h
    refine ⟨cfg, snap, r, ha, hs, hr, hd, (decideStrengtheningV3_sound hd).2.2.2.1, ?_⟩
    simp only [stepStrengtheningV3, if_pos hd]
  · cases h

def encStrengthResult (p : StrengthOutcome × Option LedgerV3) : JVal :=
  .obj [("failure", match p.1 with
      | .receiptRejected f => encReceiptFailure f
      | _ => .null),
    ("new_ledger_consumed", match p.2 with
      | some s => encStrs s.consumed
      | none => .null),
    ("note", .str "CERTIFIED_STRENGTHENING means the candidate logically implies the selected interpretation and was explicitly authorized as a strengthening; it is NOT a meaning-preserving translation"),
    ("outcome", .str p.1.name),
    ("schema", .str "pcs-semantic-strengthening-decision-v3")]

/-! ## Strengthening is not equivalence -/

/-- A concrete pair: interpretation `p(x)`, candidate `p(x) ∧ q(x)` (with `x` a parameter). -/
def strengthExampleI : SemanticClaim :=
  { params := [⟨"x", "S"⟩], assumptions := [], conclusion := .pred "p" [.var "x"] }

def strengthExampleC : SemanticClaim :=
  { params := [⟨"x", "S"⟩], assumptions := [],
    conclusion := .and (.pred "p" [.var "x"]) (.pred "q" [.var "x"]) }

/-- A two-predicate model where `p` holds everywhere and `q` nowhere. -/
def strengthExampleModel : Model :=
  { Dom := Unit, HasSort := fun _ _ => True, fn := fun _ _ => (), pred := fun f _ => f = "p" }

/-- **`strengthening_is_not_equivalence`**: the checker certifies that the candidate strengthens
    the interpretation, yet the two are **not** equivalent (a model separates them).  Such a pair
    is rejected by the equivalence-only translation authority and can only ever be reported as
    `CERTIFIED_STRENGTHENING`. -/
theorem strengthening_is_not_equivalence :
    strengthExampleC.normalize.strengthensB strengthExampleI.normalize = true ∧
    strengthExampleI.denote strengthExampleModel (fun _ => ()) ∧
    ¬ strengthExampleC.denote strengthExampleModel (fun _ => ()) := by
  refine ⟨by decide, ?_, ?_⟩
  · simp [SemanticClaim.denote, denoteParams, strengthExampleI, strengthExampleModel,
      Formula.denote]
  · simp [SemanticClaim.denote, denoteParams, strengthExampleC, strengthExampleModel,
      Formula.denote]

end PCS.V2.Semantic.V3
