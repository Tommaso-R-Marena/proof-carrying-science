import PCS.V2.DomainAuthority

/-!
# Untrusted proposer non-authority

PCS uses external (possibly AI) proposers to suggest claim translations, decompositions,
obligations and proof repairs.  This file proves that such a proposer has **no authority**:
whatever it proposes — honestly, incompetently, adversarially, adaptively after seeing
earlier verdicts, or stochastically — every proposal that PCS accepts has a true semantic
conclusion, under hypotheses about the *trusted checking layers only*.

A `Proposal` contains

* `claimId`     — which signed certificate claim the proposer wants to ground;
* `translation` — the proposer's suggested domain-native reading of that claim;
* `graph`       — the proposer's suggested decomposition into obligations (also the form of
  a proof *repair*: a repaired proposal is just another proposal).

`checkProposal` (deterministic, trusted) accepts a proposal only if domain acceptance of
the claim with the proposed graph succeeds and the proposer's translation **equals** the
claim obtained by the adapter's deterministic decoding of the signed predicate
(grounding).

A proposer is modelled as an arbitrary function from the feedback history to the next
proposal (`Strategy`); randomness is modelled by quantifying over all strategies (a
stochastic proposer is a distribution over strategies / seeds, and the theorems hold for
every seed).  `runLoop` is the propose → check → feedback → repair loop.

Theorems:

* `loop_output_checked` — (generic, any check) every output of the loop passed the check;
* `untrusted_proposer_cannot_forge_assurance` — PCS instance: any proposal output by the
  loop for any strategy denotes a true domain proposition, with PCS `Assures`;
* `no_strategy_forges` — the same, stated as non-existence of a forging strategy;
* `untrusted_proposer_archive_sound` — on top of the production raw-archive authority.

The hypotheses mention only the trusted layers (`acceptPCS`, the replay executor's
faithfulness, `AdapterSound`); there is **no** hypothesis on the strategy.
-/

set_option autoImplicit false

namespace PCS.V2.Proposer

open PCS PCS.V2.Json PCS.V2.Replay PCS.V2.CertificateModel PCS.V2.EndToEnd PCS.V2.Flagship
open PCS.V2.ClaimGraph PCS.V2.DomainAdapter PCS.V2.Package PCS.V2.Authority
open PCS.V2.CanonicalArchive PCS.V2.HighAssurance PCS.V2.Checkers PCS.V2.Zip PCS.V2.Archive
open PCS.V2.Frontier PCS.V2.TCB PCS.V2.DomainAuthority PCS.V2.Signature

/-! ## Generic propose–check–repair loop -/

/-- Feedback visible to the proposer: its earlier proposals and their verdicts. -/
abbrev History (α : Type) := List (α × Bool)

/-- An arbitrary proposer strategy (adaptive; may be adversarial or an AI system). -/
abbrev Strategy (α : Type) := History α → α

/-- Propose, check, and feed back the verdict, for at most `fuel` rounds; return the first
    accepted proposal. -/
def runLoop {α : Type} (check : α → Bool) (P : Strategy α) : Nat → History α → Option α
  | 0, _ => none
  | n + 1, h =>
    let p := P h
    if check p then some p else runLoop check P n (h ++ [(p, false)])

/-- **Generic non-authority**: whatever the strategy, every output of the loop passed the
    trusted check. -/
theorem loop_output_checked {α : Type} (check : α → Bool) (P : Strategy α) :
    ∀ (n : Nat) (h : History α) {p : α}, runLoop check P n h = some p → check p = true
  | 0, _, _, hp => by simp [runLoop] at hp
  | n + 1, h, p, hp => by
    simp only [runLoop] at hp
    split at hp
    · rename_i hc; cases hp; exact hc
    · exact loop_output_checked check P n _ hp

/-! ## PCS proposals -/

variable {D : Domain}

/-- What an untrusted proposer submits. -/
structure Proposal (A : DomainAdapter D) where
  claimId : String
  translation : D.Claim
  graph : Graph String A.IR

/-- Deterministic grounding + typed compilation + obligation-graph check. -/
def checkProposal (A : DomainAdapter D) (r : AcceptedResult) (p : Proposal A) : Bool :=
  match domainAccepts A r p.claimId p.graph with
  | some c => decide (c = p.translation)
  | none => false

theorem checkProposal_spec {A : DomainAdapter D} {r : AcceptedResult} {p : Proposal A}
    (h : checkProposal A r p = true) : domainAccepts A r p.claimId p.graph = some p.translation := by
  unfold checkProposal at h
  split at h
  · rename_i c hc
    simp only [decide_eq_true_eq] at h
    rw [hc, h]
  · cases h

/-- Single proposal form: an accepted proposal, whoever produced it, is sound. -/
theorem accepted_proposal_sound {O : Oracles} {T : TrustAnchor} {inp : PackageInput}
    {r : AcceptedResult} {Valid : ReplayRequest → Prop} (hacc : acceptPCS O T inp = some r)
    (hV : ReplayFaithful O.exec Valid) (A : DomainAdapter D) (hA : AdapterSound A Valid)
    (p : Proposal A) (h : checkProposal A r p = true) :
    DomainAssurance A r p.claimId p.graph p.translation :=
  domain_adapter_sound hacc hV A hA (checkProposal_spec h)

/-- **Untrusted proposer non-authority.**  For *every* proposer strategy `P` (no
    assumption whatsoever about it), every proposal that the propose–check–repair loop
    outputs denotes a true domain proposition — `D.Holds` of the proposer's translation in
    the world of the committed artifacts — which is moreover the deterministic decoding of
    the signed certificate claim it names, with PCS `Assures` for that claim.  The only
    hypotheses concern the trusted layers. -/
theorem untrusted_proposer_cannot_forge_assurance {O : Oracles} {T : TrustAnchor}
    {inp : PackageInput} {r : AcceptedResult} {Valid : ReplayRequest → Prop}
    (hacc : acceptPCS O T inp = some r) (hV : ReplayFaithful O.exec Valid)
    (A : DomainAdapter D) (hA : AdapterSound A Valid)
    (P : Strategy (Proposal A)) (fuel : Nat) (h₀ : History (Proposal A)) {p : Proposal A}
    (hrun : runLoop (checkProposal A r) P fuel h₀ = some p) :
    D.Holds (A.world r.table) p.translation ∧
      DomainAssurance A r p.claimId p.graph p.translation := by
  have hd := accepted_proposal_sound hacc hV A hA p (loop_output_checked _ P fuel h₀ hrun)
  exact ⟨hd.holds, hd⟩

/-- Equivalent negative form: no strategy, fuel and starting history make the loop output a
    proposal whose translation is false. -/
theorem no_strategy_forges {O : Oracles} {T : TrustAnchor} {inp : PackageInput}
    {r : AcceptedResult} {Valid : ReplayRequest → Prop} (hacc : acceptPCS O T inp = some r)
    (hV : ReplayFaithful O.exec Valid) (A : DomainAdapter D) (hA : AdapterSound A Valid) :
    ¬ ∃ (P : Strategy (Proposal A)) (fuel : Nat) (h₀ : History (Proposal A)) (p : Proposal A),
      runLoop (checkProposal A r) P fuel h₀ = some p ∧ ¬ D.Holds (A.world r.table) p.translation :=
  fun ⟨P, fuel, h₀, _, hrun, hfalse⟩ =>
    hfalse (untrusted_proposer_cannot_forge_assurance hacc hV A hA P fuel h₀ hrun).1

/-- Stochastic proposers: for any family of strategies indexed by seeds, every seed's
    accepted output is sound (so the event "accepted and false" is empty, whatever the
    distribution on seeds). -/
theorem stochastic_proposer_sound {O : Oracles} {T : TrustAnchor} {inp : PackageInput}
    {r : AcceptedResult} {Valid : ReplayRequest → Prop} (hacc : acceptPCS O T inp = some r)
    (hV : ReplayFaithful O.exec Valid) (A : DomainAdapter D) (hA : AdapterSound A Valid)
    {Seed : Type} (P : Seed → Strategy (Proposal A)) (fuel : Nat) (h₀ : History (Proposal A)) :
    ∀ s p, runLoop (checkProposal A r) (P s) fuel h₀ = some p →
      D.Holds (A.world r.table) p.translation :=
  fun s _ hrun => (untrusted_proposer_cannot_forge_assurance hacc hV A hA (P s) fuel h₀ hrun).1

/-- **Archive-level non-authority** on the production raw-archive authority: sole
    cryptographic hypothesis `NoForgery` (plus the explicit external-validator meaning
    `hExt`, discharged by `replayFaithful_reported` for built-in-only domains). -/
theorem untrusted_proposer_archive_sound {t : AuthorityTranscript} {T : TrustAnchor}
    {signed : List UInt8 → Prop} (hB : NoForgery PCS.V2.Ed25519.verify T.pk signed)
    {ExtHolds : ReplayRequest → Prop} (hExt : ReplayFaithful (transcriptExecutor t) ExtHolds)
    {raw : ByteArray} {inp : PackageInput} {r : AcceptedResult}
    (h : acceptArchiveWithTranscript t T raw = some (inp, r))
    (A : DomainAdapter D) (hA : AdapterSound A (BuiltinHolds ExtHolds))
    (P : Strategy (Proposal A)) (fuel : Nat) (h₀ : History (Proposal A)) {p : Proposal A}
    (hrun : runLoop (checkProposal A r) P fuel h₀ = some p) :
    (∃ es, CanonicalZip raw es ∧ ArchivePartition es inp ∧
      HighAssurance t T (verifiedContracts t T signed hB) inp r) ∧
    D.Holds (A.world r.table) p.translation :=
  have hd := pcs_generic_domain_archive_acceptance_sound hB hExt h A hA
    (checkProposal_spec (loop_output_checked _ P fuel h₀ hrun))
  ⟨hd.1, hd.2.holds⟩

end PCS.V2.Proposer
