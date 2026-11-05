import PCS.V2.SemanticFeedback

/-!
# Compositional translation, certified repair and sound caching (Semantic Intelligence v2)

* **Congruence** (`SemEquiv.not_congr`, …, `SemEquiv.quant_congr`): semantic equivalence of
  nameless formulas is a congruence for every connective and both quantifiers.
* **Compositional translation** (`compositional_translation_sound`): two independently
  certified sub-translations sharing parameters and assumptions combine into a certified
  translation of the conjunction.
* **Certified repair** (`certified_repair_preserves_meaning`,
  `certified_rewriting_cannot_repair_mistranslation`): a repair derivation consisting only of
  certified rewrite steps preserves meaning — hence it keeps a correct translation correct,
  and it can never turn an incorrect translation into a correct one (a real repair must change
  meaning and be re-checked).
* **Sound caching / invalidation** (`cachedCheck_sound`, `stale_cache_cannot_be_reused`): a
  decision cache keyed by the *exact input bytes* (authority configuration and request) always
  returns the fresh decision.  Any change to the registry, interpretation, candidate,
  certificate, receipt or bounds changes the key, so no dependent guarantee survives a change.
  Using the raw bytes as the key avoids any hash-collision assumption.
* **Proof-obligation graph** (`semantic_obligation_graph_acceptance_sound`,
  `wire_obligation_graph_acceptance_sound`): a certified v2 translation combined with an
  obligation graph accepted by the existing memoised PCS graph checker establishes the
  selected interpretation in the intended model, under the explicit receipt contracts and
  elaboration bridge only.
-/

set_option autoImplicit false

namespace PCS.V2.Semantic

/-! ## Congruence -/

theorem SemEquiv.not_congr {φ ψ : NFormula} (h : NFormula.SemEquiv φ ψ) :
    NFormula.SemEquiv (.not φ) (.not ψ) := fun M ρ env => _root_.not_congr (h M ρ env)

theorem SemEquiv.and_congr {φ φ' ψ ψ' : NFormula} (h₁ : NFormula.SemEquiv φ φ')
    (h₂ : NFormula.SemEquiv ψ ψ') : NFormula.SemEquiv (.and φ ψ) (.and φ' ψ') :=
  fun M ρ env => _root_.and_congr (h₁ M ρ env) (h₂ M ρ env)

theorem SemEquiv.or_congr {φ φ' ψ ψ' : NFormula} (h₁ : NFormula.SemEquiv φ φ')
    (h₂ : NFormula.SemEquiv ψ ψ') : NFormula.SemEquiv (.or φ ψ) (.or φ' ψ') :=
  fun M ρ env => _root_.or_congr (h₁ M ρ env) (h₂ M ρ env)

theorem SemEquiv.imp_congr {φ φ' ψ ψ' : NFormula} (h₁ : NFormula.SemEquiv φ φ')
    (h₂ : NFormula.SemEquiv ψ ψ') : NFormula.SemEquiv (.imp φ ψ) (.imp φ' ψ') :=
  fun M ρ env => _root_.imp_congr (h₁ M ρ env) (h₂ M ρ env)

theorem SemEquiv.quant_congr {φ ψ : NFormula} (q : Quant) (s : SortId)
    (h : NFormula.SemEquiv φ ψ) : NFormula.SemEquiv (.quant q s φ) (.quant q s ψ) := by
  intro M ρ env
  cases q with
  | all => exact forall_congr' (fun d => _root_.imp_congr Iff.rfl (h M ρ _))
  | ex => exact exists_congr (fun d => _root_.and_congr Iff.rfl (h M ρ _))

/-! ## Compositional translation -/

/-- Conjunction of two claims over the same parameters and assumptions. -/
def NClaim.conj (n m : NClaim) : NClaim := { n with conclusion := .and n.conclusion m.conclusion }

theorem ndenoteParams_and (M : Model) (ρ : String → M.Dom) :
    ∀ (ss : List SortId) (env : Nat → M.Dom) (K₁ K₂ : (Nat → M.Dom) → Prop),
    ndenoteParams M ρ ss env (fun e => K₁ e ∧ K₂ e) ↔
      ndenoteParams M ρ ss env K₁ ∧ ndenoteParams M ρ ss env K₂
  | [], _, _, _ => Iff.rfl
  | s :: ss, env, K₁, K₂ => by
    simp only [ndenoteParams]
    constructor
    · intro h
      exact ⟨fun d hd => ((ndenoteParams_and M ρ ss _ K₁ K₂).mp (h d hd)).1,
        fun d hd => ((ndenoteParams_and M ρ ss _ K₁ K₂).mp (h d hd)).2⟩
    · intro h d hd
      exact (ndenoteParams_and M ρ ss _ K₁ K₂).mpr ⟨h.1 d hd, h.2 d hd⟩

theorem NClaim.conj_denote (n m : NClaim) (hp : n.paramSorts = m.paramSorts)
    (ha : n.assumptions = m.assumptions) (M : Model) (ρ : String → M.Dom) (env : Nat → M.Dom) :
    (n.conj m).denote M ρ env ↔ n.denote M ρ env ∧ m.denote M ρ env := by
  unfold NClaim.conj NClaim.denote
  simp only [NFormula.denote]
  rw [← hp, ← ha, ← ndenoteParams_and]
  apply ndenoteParams_congr
  intro e
  exact ⟨fun h => ⟨fun hA => (h hA).1, fun hA => (h hA).2⟩, fun h hA => ⟨h.1 hA, h.2 hA⟩⟩

/-- **Compositional translation soundness.**  If `n ≡ n'` and `m ≡ m'` were certified
    independently, and each pair shares its parameters and assumptions, then the conjunction
    claims are equivalent.  Combined with `checkCert_sound` this composes certificates. -/
theorem compositional_translation_sound {n n' m m' : NClaim}
    (hp : n.paramSorts = m.paramSorts) (ha : n.assumptions = m.assumptions)
    (hp' : n'.paramSorts = m'.paramSorts) (ha' : n'.assumptions = m'.assumptions)
    (h₁ : NClaim.SemEquiv n n') (h₂ : NClaim.SemEquiv m m') :
    NClaim.SemEquiv (n.conj m) (n'.conj m') := by
  intro M ρ env
  rw [NClaim.conj_denote n m hp ha, NClaim.conj_denote n' m' hp' ha']
  exact _root_.and_congr (h₁ M ρ env) (h₂ M ρ env)

/-- Certificate-level composition. -/
theorem compositional_certificates_sound {n n' m m' : NClaim} {c₁ c₂ : EquivCert}
    (hp : n.paramSorts = m.paramSorts) (ha : n.assumptions = m.assumptions)
    (hp' : n'.paramSorts = m'.paramSorts) (ha' : n'.assumptions = m'.assumptions)
    (h₁ : checkCert c₁ n n' = true) (h₂ : checkCert c₂ m m' = true) :
    NClaim.SemEquiv (n.conj m) (n'.conj m') :=
  compositional_translation_sound hp ha hp' ha' (checkCert_sound h₁) (checkCert_sound h₂)

/-! ## Certified repair -/

/-- **Certified repair preserves the selected meaning**: if a candidate is certified against
    the interpretation and is then rewritten by certified steps, the result is still
    equivalent to the interpretation. -/
theorem certified_repair_preserves_meaning {I C C' : NClaim} {cert : EquivCert}
    {steps : List Step} (hc : checkCert cert I C = true) (hr : C.applySteps steps = some C') :
    NClaim.SemEquiv I C' :=
  (checkCert_sound hc).trans (NClaim.applySteps_sound steps C C' hr)

/-- **Certified rewriting cannot repair a mistranslation**: if the original candidate differs
    from the interpretation in some model, so does every candidate obtained from it by
    certified rewrite steps.  Genuine repairs must change meaning and are re-checked from
    scratch. -/
theorem certified_rewriting_cannot_repair_mistranslation {I C C' : NClaim} {steps : List Step}
    {M : Model} {ρ : String → M.Dom} {env : Nat → M.Dom}
    (hbad : ¬ (I.denote M ρ env ↔ C.denote M ρ env)) (hr : C.applySteps steps = some C') :
    ¬ (I.denote M ρ env ↔ C'.denote M ρ env) :=
  fun h => hbad (h.trans (NClaim.applySteps_sound steps C C' hr M ρ env).symm)

/-! ## Sound decision caching -/

/-- A decision cache keyed by the exact input bytes. -/
structure SemCache where
  entries : List ((ByteArray × ByteArray) × DecisionV2)

/-- Cache validity: every entry is the fresh decision for its key. -/
def SemCache.Valid (c : SemCache) : Prop :=
  ∀ k d, (k, d) ∈ c.entries → d = (semanticCheckV2 k.1 k.2).decision

/-- Cached checking: reuse an entry only for byte-identical inputs. -/
def cachedCheck (c : SemCache) (aRaw rRaw : ByteArray) : DecisionV2 × SemCache :=
  match c.entries.find? (fun e => decide (e.1 = (aRaw, rRaw))) with
  | some e => (e.2, c)
  | none =>
    let d := (semanticCheckV2 aRaw rRaw).decision
    (d, ⟨((aRaw, rRaw), d) :: c.entries⟩)

/-- **Cache soundness**: on a valid cache, cached checking returns exactly the fresh decision
    and leaves a valid cache. -/
theorem cachedCheck_sound {c : SemCache} (hv : c.Valid) (aRaw rRaw : ByteArray) :
    (cachedCheck c aRaw rRaw).1 = (semanticCheckV2 aRaw rRaw).decision ∧
    (cachedCheck c aRaw rRaw).2.Valid := by
  unfold cachedCheck
  split
  · rename_i e he
    have hk : e.1 = (aRaw, rRaw) := of_decide_eq_true (List.find?_some (p := fun (x : (ByteArray × ByteArray) × DecisionV2) => decide (x.1 = (aRaw, rRaw))) he)
    have hm := List.mem_of_find?_eq_some he
    refine ⟨?_, hv⟩
    have := hv e.1 e.2 hm
    rw [hk] at this
    exact this
  · refine ⟨rfl, ?_⟩
    intro k d hm
    rcases List.mem_cons.mp hm with h | h
    · cases h; rfl
    · exact hv k d h

/-- **No stale reuse**: after any change to any input byte (registry, interpretation,
    candidate, certificate, receipt, bounds), the cache cannot return a decision computed for
    the old inputs — it returns the decision for the new inputs. -/
theorem stale_cache_cannot_be_reused {c : SemCache} (hv : c.Valid) (a' r' : ByteArray) :
    (cachedCheck c a' r').1 = (semanticCheckV2 a' r').decision :=
  (cachedCheck_sound hv a' r').1

/-! ## Proof-obligation graph integration (reuse of `PCS.V2.ClaimGraph`) -/

open PCS.V2.ClaimGraph in
/-- **`semantic_obligation_graph_acceptance_sound`.**  If the v2 classifier certifies a
    translation request and the existing PCS memoised graph checker accepts a proof-obligation
    graph for the accepted candidate (decomposition rules proved semantics-preserving, leaves
    discharged by authorized proof receipts), then the **selected interpretation** holds in the
    intended model `M` — assuming exactly the explicit receipt contracts `ExternalContracts`
    and the elaboration bridge for `M`. -/
theorem semantic_obligation_graph_acceptance_sound {A : Authority} {r : RequestV2}
    {W : ExternalWorld} {M : Model} (h : (decideV2 A r).outcome = .certifiedTranslation)
    (hX : ExternalContracts A W) (hB : ElaborationBridge A.registry W M)
    {g : Graph ProofReceipt SemanticClaim}
    (hg : checkGraphMemo (semanticChecker A) g r.base.candidate.claim = true)
    (ρ : String → M.Dom) : r.base.interpretation.selected.denote M ρ :=
  (decideV2_certified_preserves_denotation h M ρ).mpr
    (root_assurance_sound (semanticChecker_sound hX hB)
      (by rw [← checkGraphMemo_eq]; exact hg) ρ)

open PCS.V2.ClaimGraph PCS.V2.Canonical PCS.V2.Json in
/-- Wire-level form: certified raw request bytes plus an accepted obligation graph for the
    decoded candidate give the selected interpretation in `M` (same explicit assumptions). -/
theorem wire_obligation_graph_acceptance_sound {aRaw rRaw : ByteArray} {W : ExternalWorld}
    {M : Model} (h : (semanticCheckV2 aRaw rRaw).decision.outcome = .certifiedTranslation) :
    ∃ cfg r, (parseCanonicalBytes maxInputBytes aRaw).bind decAuthorityConfig = some cfg ∧
      (parseCanonicalBytes maxInputBytes rRaw).bind decRequestV2 = some r ∧
      (ExternalContracts cfg.toAuthority W → ElaborationBridge cfg.toAuthority.registry W M →
        ∀ g : Graph ProofReceipt SemanticClaim,
          checkGraphMemo (semanticChecker cfg.toAuthority) g r.base.candidate.claim = true →
          ∀ ρ, r.base.interpretation.selected.denote M ρ) := by
  obtain ⟨cfg, r, h1, h2, hc⟩ := semanticCheckV2_certified_sound h
  refine ⟨cfg, r, h1, h2, fun hX hB g hg ρ => ?_⟩
  exact (accepted_translation_preserves_denotation_v2 hc M ρ).mpr
    (root_assurance_sound (semanticChecker_sound hX hB)
      (by rw [← checkGraphMemo_eq]; exact hg) ρ)

end PCS.V2.Semantic
