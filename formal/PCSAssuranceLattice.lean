import Std

/-!
# Proof-Carrying Epistemic Composition — Assurance Lattice Kernel

First-party research continuation. This module formalizes a finite typed
assurance lattice for scientific certificates:

* Evidence classes are **strata**, not interchangeable PASS tokens.
* Composition of certificates is a **typed morphism** in that lattice.
* Silent cross-stratum promotion is rejected without an explicit bridge.
* Invalidation is the dual of composition: changed artifacts reopen the
  reachable dependency cone.

`Stratum.le e r` means evidence stratum `e` is strong enough to discharge
requirement `r`. Formal may discharge computational/provenance (strengthening).
Computational may never silently discharge formal. Empirical is observational
and incomparable with the integrity/math chain except via an explicit bridge.

These theorems concern the exact finite graph presented to the checker.
They do not establish empirical truth, continuum accuracy, cryptographic
unforgeability, or production package authority. Scientific acceptance
remains a separate OPEN obligation outside this lattice kernel.
-/
set_option autoImplicit false

namespace PCSAssuranceLattice

/-- Epistemic strata. -/
inductive Stratum where
  | unverified
  | provenance
  | computational
  | formal
  | empirical
  deriving DecidableEq, Repr

namespace Stratum

/-- Strength order for discharge. Formal may strengthen weaker integrity/math
    requirements. Computational cannot discharge formal. Empirical cannot
    discharge formal/computational/provenance without a bridge. -/
def le : Stratum → Stratum → Bool
  | unverified, unverified => true
  | provenance, provenance => true
  | computational, provenance => true
  | computational, computational => true
  | formal, provenance => true
  | formal, computational => true
  | formal, formal => true
  | empirical, empirical => true
  | _, _ => false

theorem le_refl (a : Stratum) : le a a = true := by
  cases a <;> rfl

theorem computational_not_le_formal :
    le .computational .formal = false := rfl

theorem empirical_not_le_formal :
    le .empirical .formal = false := rfl

theorem computational_not_le_empirical :
    le .computational .empirical = false := rfl

theorem formal_le_computational :
    le .formal .computational = true := rfl

theorem formal_le_formal :
    le .formal .formal = true := rfl

theorem provenance_le_provenance :
    le .provenance .provenance = true := rfl

theorem computational_le_computational :
    le .computational .computational = true := rfl

end Stratum

/-- A scoped claim node in a finite assurance graph. -/
structure ClaimNode where
  id : Nat
  required : Stratum
  artifactDeps : List Nat
  premiseClaims : List Nat
  deriving DecidableEq, Repr

/-- Leaf evidence proposing support for a claim at an explicit stratum. -/
structure EvidenceAtom where
  claimId : Nat
  stratum : Stratum
  accepted : Bool
  deriving DecidableEq, Repr

/-- Explicit cross-stratum bridge. Without it, `le` alone decides discharge. -/
structure Bridge where
  claimId : Nat
  fromStratum : Stratum
  toStratum : Stratum
  accepted : Bool
  deriving DecidableEq, Repr

/-- Finite assurance lattice package. -/
structure Package where
  claims : List ClaimNode
  evidence : List EvidenceAtom
  bridges : List Bridge
  changedArtifacts : List Nat
  deriving DecidableEq, Repr

/-- Direct evidence discharge: same claim, accepted, and stratum dominates. -/
def discharges (e : EvidenceAtom) (c : ClaimNode) : Bool :=
  (e.accepted && decide (e.claimId = c.id)) && Stratum.le e.stratum c.required

/-- Accepted bridge that upgrades evidence stratum for a claim. -/
def bridgeUpgrades (b : Bridge) (e : EvidenceAtom) (c : ClaimNode) : Bool :=
  (b.accepted && e.accepted && decide (b.claimId = c.id) && decide (e.claimId = c.id) &&
    decide (e.stratum = b.fromStratum)) && Stratum.le b.toStratum c.required

/-- Evidence supports a claim either by lattice order or by an accepted bridge. -/
def supports (p : Package) (c : ClaimNode) : Bool :=
  p.evidence.any (fun e =>
    discharges e c || p.bridges.any (fun b => bridgeUpgrades b e c))

/-- Premise claim identifiers that appear in the package. -/
def findClaim (p : Package) (id : Nat) : Option ClaimNode :=
  p.claims.find? (fun c => decide (c.id = id))

/-- A premise is usable when it is itself supported at its declared required stratum. -/
def premiseSupported (p : Package) (premiseId : Nat) : Bool :=
  match findClaim p premiseId with
  | some c => supports p c
  | none => false

/-- Composition gate: every declared premise claim is present and supported. -/
def premisesOk (p : Package) (c : ClaimNode) : Bool :=
  c.premiseClaims.all (fun id => premiseSupported p id)

/-- Reachability of a changed artifact through direct claim dependencies. -/
def dependsOnChanged (p : Package) (c : ClaimNode) : Bool :=
  c.artifactDeps.any (fun a => p.changedArtifacts.contains a)

/-- A claim is compositionally certified when supported, premises hold, and it is
    not invalidated by a changed artifact. -/
def claimCertified (p : Package) (c : ClaimNode) : Bool :=
  supports p c && premisesOk p c && !dependsOnChanged p c

/-- True when the claim has at least one accepted evidence atom. -/
def hasAcceptedEvidence (p : Package) (c : ClaimNode) : Bool :=
  p.evidence.any (fun e => e.accepted && decide (e.claimId = c.id))

/-- Unique claim identifiers. -/
def uniqueClaimIds (p : Package) : Bool :=
  decide ((p.claims.map (·.id)).eraseDups.length = p.claims.length)

/-- Whole-package executable certificate. -/
def check (p : Package) : Bool :=
  uniqueClaimIds p &&
  p.claims.all (fun c => !hasAcceptedEvidence p c || claimCertified p c) &&
  p.evidence.all (fun e => !e.accepted || (findClaim p e.claimId).isSome) &&
  p.bridges.all (fun b => !b.accepted || (findClaim p b.claimId).isSome)

/-- Semantic certificate matching the executable checker. -/
def Certified (p : Package) : Prop :=
  uniqueClaimIds p = true ∧
  (∀ c ∈ p.claims, hasAcceptedEvidence p c = true → claimCertified p c = true) ∧
  (∀ e ∈ p.evidence, e.accepted = true → (findClaim p e.claimId).isSome = true) ∧
  (∀ b ∈ p.bridges, b.accepted = true → (findClaim p b.claimId).isSome = true)

theorem check_iff_certified (p : Package) : check p = true ↔ Certified p := by
  simp only [check, Certified, Bool.and_eq_true, List.all_eq_true,
    Bool.or_eq_true, Bool.not_eq_eq_eq_not, Bool.not_true]
  constructor
  · intro h
    refine ⟨h.1.1.1, ?_, ?_, ?_⟩
    · intro c hc hex
      have := h.1.1.2 c hc
      simp [hex] at this
      exact this
    · intro e he ha
      have := h.1.2 e he
      simp [ha] at this
      exact this
    · intro b hb ha
      have := h.2 b hb
      simp [ha] at this
      exact this
  · intro h
    refine ⟨⟨⟨h.1, ?_⟩, ?_⟩, ?_⟩
    · intro c hc
      cases hAcc : hasAcceptedEvidence p c with
      | false => simp
      | true => exact Or.inr (h.2.1 c hc hAcc)
    · intro e he
      cases hAcc : e.accepted with
      | false => simp
      | true => exact Or.inr (h.2.2.1 e he hAcc)
    · intro b hb
      cases hAcc : b.accepted with
      | false => simp
      | true => exact Or.inr (h.2.2.2 b hb hAcc)

/-- Direct computational evidence cannot discharge a formal obligation. -/
theorem silent_computational_to_formal_rejected
    (e : EvidenceAtom) (c : ClaimNode)
    (hid : e.claimId = c.id) (hs : e.stratum = .computational)
    (hr : c.required = .formal) (ha : e.accepted = true) :
    discharges e c = false := by
  simp [discharges, hid, hs, hr, ha, Stratum.le]

/-- Empirical evidence cannot silently discharge a formal obligation. -/
theorem silent_empirical_to_formal_rejected
    (e : EvidenceAtom) (c : ClaimNode)
    (hid : e.claimId = c.id) (hs : e.stratum = .empirical)
    (hr : c.required = .formal) (ha : e.accepted = true) :
    discharges e c = false := by
  simp [discharges, hid, hs, hr, ha, Stratum.le]

/-- Computational evidence discharges computational obligations. -/
theorem computational_discharges_computational
    (e : EvidenceAtom) (c : ClaimNode)
    (hid : e.claimId = c.id) (hs : e.stratum = .computational)
    (hr : c.required = .computational) (ha : e.accepted = true) :
    discharges e c = true := by
  simp [discharges, hid, hs, hr, ha, Stratum.le]

/-- Formal evidence discharges formal obligations. -/
theorem formal_discharges_formal
    (e : EvidenceAtom) (c : ClaimNode)
    (hid : e.claimId = c.id) (hs : e.stratum = .formal)
    (hr : c.required = .formal) (ha : e.accepted = true) :
    discharges e c = true := by
  simp [discharges, hid, hs, hr, ha, Stratum.le]

/-- Formal evidence may strengthen a computational requirement. -/
theorem formal_strengthens_computational
    (e : EvidenceAtom) (c : ClaimNode)
    (hid : e.claimId = c.id) (hs : e.stratum = .formal)
    (hr : c.required = .computational) (ha : e.accepted = true) :
    discharges e c = true := by
  simp [discharges, hid, hs, hr, ha, Stratum.le]

/-- An accepted bridge can upgrade computational evidence for a formal claim. -/
theorem bridge_enables_formal_from_computational
    (b : Bridge) (e : EvidenceAtom) (c : ClaimNode)
    (hbid : b.claimId = c.id) (heid : e.claimId = c.id)
    (hfrom : b.fromStratum = .computational) (hto : b.toStratum = .formal)
    (hes : e.stratum = .computational) (hr : c.required = .formal)
    (hba : b.accepted = true) (hea : e.accepted = true) :
    bridgeUpgrades b e c = true := by
  simp [bridgeUpgrades, hbid, heid, hfrom, hto, hes, hr, hba, hea, Stratum.le]

/-- Changed artifacts force reopen: a claim depending on a changed artifact is
    not compositionally certified, even if leaf evidence still looks accepted. -/
theorem changed_artifact_blocks_certification
    (p : Package) (c : ClaimNode)
    (hdep : dependsOnChanged p c = true) :
    claimCertified p c = false := by
  simp [claimCertified, hdep]

/-- Composition: if every premise is supported and the claim itself is supported
    without invalidation, the claim is certified. -/
theorem composition_intro (p : Package) (c : ClaimNode)
    (hs : supports p c = true) (hp : premisesOk p c = true)
    (hi : dependsOnChanged p c = false) :
    claimCertified p c = true := by
  simp [claimCertified, hs, hp, hi]

/-- Unsupported missing premise blocks the premises gate. -/
theorem missing_premise_blocks (p : Package) (c : ClaimNode) (pid : Nat)
    (hin : pid ∈ c.premiseClaims) (hmiss : premiseSupported p pid = false) :
    premisesOk p c = false := by
  unfold premisesOk
  apply Eq.symm
  -- `all` is false iff some element fails the predicate.
  have : ¬ c.premiseClaims.all (fun id => premiseSupported p id) = true := by
    intro happ
    have := (List.all_eq_true.mp happ) pid hin
    simp [hmiss] at this
  cases h : c.premiseClaims.all (fun id => premiseSupported p id) with
  | false => rfl
  | true => exact (this h).elim

end PCSAssuranceLattice
