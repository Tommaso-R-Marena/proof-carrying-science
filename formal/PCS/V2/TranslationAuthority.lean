import PCS.V2.TranslationChecker
import PCS.V2.ClaimGraphMemo
import PCS.V2.Proposer

/-!
# Semantic translation authority: external receipts, obligation graphs, untrusted proposers

This file connects the certified translation checker to the existing PCS architecture and
makes every external trust assumption an explicit hypothesis.

## External world and its contracts (the TCB, stated, not proved)

`ExternalWorld` names three external facts PCS cannot establish internally:

* `Confirmed s c as` — an authorized external process (human or delegated authority)
  confirmed that the structured interpretation `c` with ambiguity resolutions `as` is the
  intended reading of text `s`.  *This is evidence about intent, not a mathematical fact.*
* `Elaborates src d` — the external Lean elaboration service elaborated `src` as the
  type of a declaration `d` against the approved environment.
* `KernelProved src d` — the Lean kernel accepted a proof of `src` as declaration `d`.

`ExternalContracts A W` says the authority's receipt verifiers are sound for `W` (e.g.
Ed25519 signatures under the authorized keys, issued only after the external process ran).
`ElaborationBridge R W M` is the remaining **semantic bridge**: a kernel-proved rendering of
a well-typed, closed, hygienic claim means that the claim holds in the intended model `M`
(i.e. the approved symbols denote, in Lean, what `M` says they denote).

## Results

* `translation_authority_sound` — acceptance plus the external contracts give:
  (1) **unconditionally**, the interpretation and candidate denotations coincide in every
  model and valuation; (2) authorized confirmation of the exact interpretation;
  (3) external elaboration and (4) kernel proof of the exact rendered source, when required;
  (5) with the elaboration bridge, the **selected interpretation's meaning holds** in the
  intended model.
* `semanticChecker`, `semanticChecker_sound`, `translated_claim_graph_sound` — reuse of the
  existing proof-obligation-graph checker (`PCS.V2.ClaimGraph.checkGraph`, and the memoised
  `checkGraphMemo`): semantic claims are the claim IR, decomposition rules
  (`and_intro`, `imp_intro`, `or_intro_left/right`, `true_intro`, `assumption`) are proved
  semantics-preserving, and leaves are verified proof receipts.
* `untrusted_proposer_cannot_bypass_translation_authority`, `no_strategy_forges_translation`
  — reuse of the existing propose → check → repair loop (`PCS.V2.Proposer.runLoop`): for
  *every* proposer strategy, every output satisfies the certified contract and preserves
  meaning.
-/

set_option autoImplicit false

namespace PCS.V2.Semantic

open PCS.V2.ClaimGraph PCS.V2.Proposer

/-! ## External world -/

/-- External facts that PCS cannot establish internally. -/
structure ExternalWorld where
  Confirmed : String → SemanticClaim → List Ambiguity → Prop
  Elaborates : String → String → Prop
  KernelProved : String → String → Prop

/-- Soundness of the authority's receipt verifiers (explicit trust assumption). -/
structure ExternalContracts (A : Authority) (W : ExternalWorld) : Prop where
  confirmation_sound : ∀ r, A.verifyConfirmation r = true →
    W.Confirmed r.sourceText r.selected r.ambiguities
  elaboration_sound : ∀ r, A.verifyElaboration r = true → W.Elaborates r.leanSource r.declName
  proof_sound : ∀ r, A.verifyProof r = true → W.KernelProved r.leanSource r.declName

/-- The semantic elaboration bridge for an intended model `M` (explicit trust assumption):
    a kernel-proved rendering of a well-typed, closed, hygienic claim means the claim. -/
def ElaborationBridge (R : Registry) (W : ExternalWorld) (M : Model) : Prop :=
  ∀ (c : SemanticClaim) (d : String), c.wellTypedB R = true → c.freeVars = [] →
    c.hygienicB R = true → W.KernelProved (renderClaimLean R c) d → ∀ ρ, c.denote M ρ

/-- **Translation authority soundness** with every external assumption explicit. -/
theorem translation_authority_sound {A : Authority} {req : Request} {W : ExternalWorld}
    (hacc : translationAccepts A req = true) (hX : ExternalContracts A W) :
    (∀ (M : Model) (ρ : String → M.Dom),
      req.interpretation.selected.denote M ρ ↔ req.candidate.claim.denote M ρ) ∧
    W.Confirmed req.interpretation.sourceText req.interpretation.selected
      req.interpretation.ambiguities ∧
    (A.requireElaboration = true → W.Elaborates req.candidate.leanSource req.candidate.declName) ∧
    (A.requireProof = true → W.KernelProved req.candidate.leanSource req.candidate.declName) ∧
    (A.requireProof = true → ∀ M, ElaborationBridge A.registry W M →
      ∀ ρ, req.interpretation.selected.denote M ρ) := by
  have c := (translationAccepts_iff A req).mp hacc
  have hproved : A.requireProof = true →
      W.KernelProved req.candidate.leanSource req.candidate.declName := by
    intro hp
    obtain ⟨r, _, hs, hd, _, hv⟩ := c.proof hp
    have := hX.proof_sound r hv
    rw [hs, hd] at this; exact this
  refine ⟨fun M ρ => accepted_translation_preserves_meaning hacc M ρ, ?_, ?_, hproved, ?_⟩
  · obtain ⟨r, _, hb, hv⟩ := c.confirmation
    have := hX.confirmation_sound r hv
    unfold ConfirmationReceipt.binds at hb
    simp only [Bool.and_eq_true, decide_eq_true_eq] at hb
    obtain ⟨⟨h1, h2⟩, h3⟩ := hb
    rw [h1, h2, h3] at this; exact this
  · intro he
    obtain ⟨r, _, hs, hd, hv⟩ := c.elaboration he
    have := hX.elaboration_sound r hv
    rw [hs, hd] at this; exact this
  · intro hp M hB ρ
    have hk := hproved hp
    rw [c.leanRendering] at hk
    have hc := hB req.candidate.claim req.candidate.declName c.wellTyped.2
      c.noUnexpectedFreeVariables.2 c.hygienic hk ρ
    exact (accepted_translation_preserves_meaning hacc M ρ).mpr hc

/-! ## Reuse of the proof-obligation graph (Claim IR) -/

/-- Decomposition rules over semantic claims (all proved semantics-preserving). -/
def semanticRule : String → SemanticClaim → List SemanticClaim → Bool
  | "and_intro", p, [c₁, c₂] =>
    match p.conclusion with
    | .and a b => decide (c₁ = { p with conclusion := a }) && decide (c₂ = { p with conclusion := b })
    | _ => false
  | "imp_intro", p, [c₁] =>
    match p.conclusion with
    | .imp a b => decide (c₁ = { p with assumptions := p.assumptions ++ [a], conclusion := b })
    | _ => false
  | "or_intro_left", p, [c₁] =>
    match p.conclusion with
    | .or a _ => decide (c₁ = { p with conclusion := a })
    | _ => false
  | "or_intro_right", p, [c₁] =>
    match p.conclusion with
    | .or _ b => decide (c₁ = { p with conclusion := b })
    | _ => false
  | "true_intro", p, [] => decide (p.conclusion = .tt)
  | "assumption", p, [] => p.assumptions.contains p.conclusion
  | _, _, _ => false

/-- Leaf check: a proof receipt for the exact rendering of a well-typed, closed, hygienic
    claim, with allowed axioms, verified by the authority. -/
def semanticLeaf (A : Authority) (r : ProofReceipt) (c : SemanticClaim) : Bool :=
  decide (r.leanSource = renderClaimLean A.registry c) && c.wellTypedB A.registry &&
    decide (c.freeVars = []) && c.hygienicB A.registry &&
    r.axioms.all (fun ax => A.allowedAxioms.contains ax) && A.verifyProof r

/-- The trusted obligation checker for semantic claims. -/
def semanticChecker (A : Authority) : Checker ProofReceipt SemanticClaim :=
  { leaf := semanticLeaf A, rule := semanticRule }

theorem denoteParams_mono (M : Model) :
    ∀ (bs : List Binder) (ρ : String → M.Dom) (k k' : (String → M.Dom) → Prop),
      (∀ ρ', k ρ' → k' ρ') → denoteParams M bs ρ k → denoteParams M bs ρ k'
  | [], ρ, _, _, h, hk => h ρ hk
  | _ :: bs, _, k, k', h, hk => fun d hd => denoteParams_mono M bs _ k k' h (hk d hd)

theorem denoteParams_and (M : Model) :
    ∀ (bs : List Binder) (ρ : String → M.Dom) (k k' : (String → M.Dom) → Prop),
      denoteParams M bs ρ k → denoteParams M bs ρ k' → denoteParams M bs ρ (fun ρ' => k ρ' ∧ k' ρ')
  | [], _, _, _, h1, h2 => ⟨h1, h2⟩
  | _ :: bs, _, k, k', h1, h2 => fun d hd => denoteParams_and M bs _ k k' (h1 d hd) (h2 d hd)

theorem denoteParams_intro (M : Model) :
    ∀ (bs : List Binder) (ρ : String → M.Dom) (k : (String → M.Dom) → Prop),
      (∀ ρ', k ρ') → denoteParams M bs ρ k
  | [], ρ, _, h => h ρ
  | _ :: bs, _, k, h => fun _ _ => denoteParams_intro M bs _ k h

/-- Every semantic decomposition rule is semantics-preserving. -/
theorem semanticRule_sound (M : Model) :
    ∀ r p cs, semanticRule r p cs = true → (∀ c ∈ cs, ∀ ρ, c.denote M ρ) → ∀ ρ, p.denote M ρ := by
  intro r p cs hr hcs ρ
  unfold semanticRule at hr
  split at hr
  · rename_i c₁ c₂
    split at hr
    · rename_i a b hpc
      simp only [Bool.and_eq_true, decide_eq_true_eq] at hr
      obtain ⟨rfl, rfl⟩ := hr
      have h1 := hcs _ (List.mem_cons_self) ρ
      have h2 := hcs _ (List.mem_cons_of_mem _ List.mem_cons_self) ρ
      unfold SemanticClaim.denote at h1 h2 ⊢
      rw [hpc]
      refine denoteParams_mono M _ _ _ _ ?_ (denoteParams_and M _ _ _ _ h1 h2)
      intro ρ' ⟨k1, k2⟩ hA
      exact ⟨k1 hA, k2 hA⟩
    · cases hr
  · rename_i c₁
    split at hr
    · rename_i a b hpc
      simp only [decide_eq_true_eq] at hr
      subst hr
      have h1 := hcs _ (List.mem_cons_self) ρ
      unfold SemanticClaim.denote at h1 ⊢
      rw [hpc]
      refine denoteParams_mono M _ _ _ _ ?_ h1
      intro ρ' k hA ha
      apply k
      intro x hx
      rcases List.mem_append.mp hx with hx | hx
      · exact hA x hx
      · simp only [List.mem_singleton] at hx; subst hx; exact ha
    · cases hr
  · rename_i c₁
    split at hr
    · rename_i a _ hpc
      simp only [decide_eq_true_eq] at hr
      subst hr
      have h1 := hcs _ (List.mem_cons_self) ρ
      unfold SemanticClaim.denote at h1 ⊢
      rw [hpc]
      exact denoteParams_mono M _ _ _ _ (fun ρ' k hA => Or.inl (k hA)) h1
    · cases hr
  · rename_i c₁
    split at hr
    · rename_i _ b hpc
      simp only [decide_eq_true_eq] at hr
      subst hr
      have h1 := hcs _ (List.mem_cons_self) ρ
      unfold SemanticClaim.denote at h1 ⊢
      rw [hpc]
      exact denoteParams_mono M _ _ _ _ (fun ρ' k hA => Or.inr (k hA)) h1
    · cases hr
  · simp only [decide_eq_true_eq] at hr
    unfold SemanticClaim.denote
    rw [hr]
    exact denoteParams_intro M _ _ _ (fun _ _ => trivial)
  · unfold SemanticClaim.denote
    have hm : p.conclusion ∈ p.assumptions := List.contains_iff_mem.mp hr
    exact denoteParams_intro M _ _ _ (fun ρ' hA => hA _ hm)
  · cases hr

/-- **The semantic obligation checker satisfies the local soundness obligations of the
    existing PCS graph checker**, relative to the explicit external contracts and the
    elaboration bridge for `M`. -/
theorem semanticChecker_sound {A : Authority} {W : ExternalWorld} {M : Model}
    (hX : ExternalContracts A W) (hB : ElaborationBridge A.registry W M) :
    CheckerSound (semanticChecker A) (fun c => ∀ ρ, c.denote M ρ) :=
  { leaf := fun r c h => by
      simp only [semanticChecker, semanticLeaf, Bool.and_eq_true, decide_eq_true_eq] at h
      obtain ⟨⟨⟨⟨⟨hs, hwt⟩, hfv⟩, hhy⟩, _⟩, hv⟩ := h
      have hk := hX.proof_sound r hv
      rw [hs] at hk
      exact hB c r.declName hwt hfv hhy hk,
    rule := fun r p cs h hcs => semanticRule_sound M r p cs h hcs }

/-- **Accepted translation + accepted obligation graph ⇒ the selected interpretation's
    meaning holds** in the intended model (graph checked by the existing PCS checker). -/
theorem translated_claim_graph_sound {A : Authority} {req : Request} {W : ExternalWorld}
    {M : Model} (hacc : translationAccepts A req = true) (hX : ExternalContracts A W)
    (hB : ElaborationBridge A.registry W M) {g : Graph ProofReceipt SemanticClaim}
    (hg : checkGraph (semanticChecker A) g req.candidate.claim = true) (ρ : String → M.Dom) :
    req.interpretation.selected.denote M ρ :=
  (accepted_translation_preserves_meaning hacc M ρ).mpr
    (root_assurance_sound (semanticChecker_sound hX hB) hg ρ)

/-- Same, with the production memoised graph checker. -/
theorem translated_claim_graph_sound_memo {A : Authority} {req : Request} {W : ExternalWorld}
    {M : Model} (hacc : translationAccepts A req = true) (hX : ExternalContracts A W)
    (hB : ElaborationBridge A.registry W M) {g : Graph ProofReceipt SemanticClaim}
    (hg : checkGraphMemo (semanticChecker A) g req.candidate.claim = true) (ρ : String → M.Dom) :
    req.interpretation.selected.denote M ρ :=
  translated_claim_graph_sound hacc hX hB (by rw [← checkGraphMemo_eq]; exact hg) ρ

/-! ## Untrusted proposers (reuse of the PCS propose–check–repair loop) -/

/-- **An untrusted proposer cannot bypass the translation authority.**  For every proposer
    strategy (adaptive, adversarial, stochastic seed, or a learned model — no assumption
    whatsoever), every request output by the propose → check → repair loop satisfies the
    full certified contract and preserves meaning in every model and valuation. -/
theorem untrusted_proposer_cannot_bypass_translation_authority (A : Authority)
    (P : Strategy Request) (fuel : Nat) (h₀ : History Request) {req : Request}
    (hrun : runLoop (translationAccepts A) P fuel h₀ = some req) :
    TranslationContract A req ∧
      ∀ (M : Model) (ρ : String → M.Dom),
        req.interpretation.selected.denote M ρ ↔ req.candidate.claim.denote M ρ :=
  have h := loop_output_checked (translationAccepts A) P fuel h₀ hrun
  ⟨(translationAccepts_iff A req).mp h, accepted_translation_preserves_meaning h⟩

/-- No strategy makes the loop output a candidate whose meaning differs from the selected
    interpretation's in any model. -/
theorem no_strategy_forges_translation (A : Authority) :
    ¬ ∃ (P : Strategy Request) (fuel : Nat) (h₀ : History Request) (req : Request)
      (M : Model) (ρ : String → M.Dom),
      runLoop (translationAccepts A) P fuel h₀ = some req ∧
        ¬ (req.interpretation.selected.denote M ρ ↔ req.candidate.claim.denote M ρ) :=
  fun ⟨P, fuel, h₀, _, M, ρ, hrun, hne⟩ =>
    hne ((untrusted_proposer_cannot_bypass_translation_authority A P fuel h₀ hrun).2 M ρ)

/-- With the external contracts, every loop output is also authorized-confirmed. -/
theorem untrusted_proposer_output_confirmed {A : Authority} {W : ExternalWorld}
    (hX : ExternalContracts A W) (P : Strategy Request) (fuel : Nat) (h₀ : History Request)
    {req : Request} (hrun : runLoop (translationAccepts A) P fuel h₀ = some req) :
    W.Confirmed req.interpretation.sourceText req.interpretation.selected
      req.interpretation.ambiguities :=
  (translation_authority_sound (loop_output_checked _ P fuel h₀ hrun) hX).2.1

end PCS.V2.Semantic
