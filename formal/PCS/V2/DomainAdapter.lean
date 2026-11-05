import PCS.V2.ClaimGraph
import PCS.V2.Flagship

/-!
# Generic domain adapters: from PCS acceptance to a domain-native semantic proposition

A **domain** `D` is anything with a type of native claims, a semantic world, and a truth
relation `D.Holds : D.World → D.Claim → Prop` (computational biology, chemistry, ML
evaluation, AI-safety trace audits, simulation, …).  Nothing about `D` is assumed.

A **domain adapter** `A : DomainAdapter D` connects `D` to PCS:

* `decode`   — typed decoding of a signed certificate claim predicate (JSON) into a
  domain claim (the *claim binding*);
* `compile`  — typed compilation of a domain claim into the adapter's claim IR (the root
  obligation of an obligation graph);
* `world`    — the domain world determined by the committed, digest-bound artifact bytes;
* `sem`      — the semantics of claim-IR nodes in a world;
* `leafCheck` — does a certificate evidence object (whose replay has passed) discharge an
  IR node?
* `ruleCheck` — is a decomposition step valid?

`AdapterSound A Valid` is the **local** contract a new domain must discharge.  It never
mentions a particular claim's truth:

* `compile_sound` — compilation reflects semantics: `sem w (compile c) → Holds w c`;
* `rule_sound`    — every accepted decomposition rule is semantics-preserving;
* `leaf_sound`    — an evidence object accepted by `leafCheck`, whose replay request is
  `Valid` (i.e. whose replay validator's PASS-meaning holds), denotes the IR node in the
  world of the request's artifacts.

`Valid` is the meaning of a replay `PASS`; it is linked to the actual executor only by the
standard `ReplayFaithful O.exec Valid` (for the Lean authority this is a *theorem* for every
certified checker, see `PCS.V2.DomainAuthority`).

The obligation graph is **untrusted input** (`PCS.V2.ClaimGraph`); leaves name certificate
evidence ids, and are discharged only by evidence that (i) is required by the bound
certificate claim, (ii) was freshly replayed with outcome `PASS`, and (iii) is accepted by
the adapter's `leafCheck` for the leaf's own IR claim.

Main theorem: `domain_adapter_sound`.
-/

set_option autoImplicit false

namespace PCS.V2.DomainAdapter

open PCS PCS.V2.Json PCS.V2.Replay PCS.V2.CertificateModel PCS.V2.EndToEnd PCS.V2.Flagship
open PCS.V2.ClaimGraph PCS.V2.NormalizedWire PCS.V2.Package

/-- Artifact id ↦ exact delivered bytes (the replay table). -/
abbrev ArtifactTable := List (String × ByteArray)

/-- An arbitrary external scientific/computational domain. -/
structure Domain where
  World : Type
  Claim : Type
  [decEq : DecidableEq Claim]
  Holds : World → Claim → Prop

attribute [instance] Domain.decEq

/-- How a domain is connected to PCS (all components are deterministic code). -/
structure DomainAdapter (D : Domain) where
  /-- claim-IR (obligation-node) type -/
  IR : Type
  [decEqIR : DecidableEq IR]
  /-- typed decoding of a certificate claim predicate -/
  decode : JVal → Option D.Claim
  /-- typed compilation of a domain claim to its root IR obligation -/
  compile : D.Claim → Option IR
  /-- domain world determined by the committed artifact bytes -/
  world : ArtifactTable → D.World
  /-- semantics of IR nodes -/
  sem : D.World → IR → Prop
  /-- does a (passing, replayed) evidence object discharge an IR node? -/
  leafCheck : JVal → IR → Bool
  /-- is a decomposition step valid? -/
  ruleCheck : String → IR → List IR → Bool

attribute [instance] DomainAdapter.decEqIR

/-- **The adapter-soundness contract**: local refinement obligations, relative to the
    meaning `Valid` of a replay `PASS`. -/
structure AdapterSound {D : Domain} (A : DomainAdapter D) (Valid : ReplayRequest → Prop) :
    Prop where
  compile_sound : ∀ w c ir, A.compile c = some ir → A.sem w ir → D.Holds w c
  rule_sound : ∀ w r p cs, A.ruleCheck r p cs = true → (∀ q ∈ cs, A.sem w q) → A.sem w p
  leaf_sound : ∀ req n, A.leafCheck req.evidence n = true → Valid req →
    A.sem (A.world req.artifacts) n

variable {D : Domain}

/-- Leaf discharge against a certificate evidence list: the evidence id is required by the
    bound certificate claim, the certificate evidence with that id has (replayed) outcome
    PASS, and the adapter accepts its evidence object for the leaf's claim. -/
def evidenceLeafIn (A : DomainAdapter D) (evs : List CertEvidence) (cl : CertClaim)
    (eid : String) (n : A.IR) : Bool :=
  cl.requiredEvidence.contains eid &&
    match evs.find? (fun e => e.id == eid) with
    | some e => decide (e.outcome = .pass) && A.leafCheck e.json n
    | none => false

/-- The trusted obligation checker induced by an adapter, a certificate evidence list and
    a certificate claim. -/
def pcsCheckerIn (A : DomainAdapter D) (evs : List CertEvidence) (cl : CertClaim) :
    Checker String A.IR :=
  { leaf := evidenceLeafIn A evs cl, rule := A.ruleCheck }

/-- The checker for an accepted package. -/
def pcsChecker (A : DomainAdapter D) (r : AcceptedResult) (cl : CertClaim) :
    Checker String A.IR :=
  pcsCheckerIn A r.model.evidence cl

/-- **Domain acceptance** of certificate claim `cid` with (untrusted) obligation graph `g`:
    the claim exists in the certificate and has an accepted normalized decision at an
    assurance level, its predicate decodes to a domain claim `c`, `c` compiles to IR root
    `ir`, and `g` is accepted for `ir`.  Returns the bound domain claim. -/
def domainAccepts (A : DomainAdapter D) (r : AcceptedResult) (cid : String)
    (g : Graph String A.IR) : Option D.Claim :=
  match r.model.claims.find? (fun cl => cl.id == cid) with
  | none => none
  | some cl =>
    match r.claims.find? (fun p => p.1.claimId == cid) with
    | none => none
    | some p =>
      if (levelOf p.2.decision).isSome then
        match A.decode cl.predicate with
        | none => none
        | some c =>
          match A.compile c with
          | none => none
          | some ir => if checkGraph (pcsChecker A r cl) g ir then some c else none
      else none

/-- What domain acceptance establishes. -/
structure DomainAssurance (A : DomainAdapter D) (r : AcceptedResult) (cid : String)
    (g : Graph String A.IR) (c : D.Claim) : Prop where
  /-- **the original domain-level semantic proposition**, in the world of the committed
      artifact bytes -/
  holds : D.Holds (A.world r.table) c
  /-- the claim is the signed certificate's claim `cid`, decoded -/
  bound : ∃ cl ∈ r.model.claims, cl.id = cid ∧ A.decode cl.predicate = some c
  /-- PCS's kernel judgement for the same claim -/
  pcsAssures : ∃ p ∈ r.claims, p.1.claimId = cid ∧ ∃ L, levelOf p.2.decision = some L ∧
    Assures (gamma p.2) L (kernelClaim p.2) (kernelEvidence p.2)
  /-- the obligation graph's structural guarantees (no cycles, no missing or unsupported
      nodes, no duplicate ids, root bound to the compiled claim) -/
  graph : ∃ cl ∈ r.model.claims, ∃ ir, cl.id = cid ∧ A.compile c = some ir ∧
    AcceptedGraph (pcsChecker A r cl) g ir

/-- The induced checker is sound for the adapter's semantics in the world of the committed
    artifacts, as soon as the adapter is sound and the executor is faithful to `Valid`. -/
theorem pcsChecker_sound {O : Oracles} {T : TrustAnchor} {inp : PackageInput}
    {r : AcceptedResult} {Valid : ReplayRequest → Prop} (hacc : acceptPCS O T inp = some r)
    (hV : ReplayFaithful O.exec Valid) {A : DomainAdapter D} (hA : AdapterSound A Valid)
    (cl : CertClaim) : CheckerSound (pcsChecker A r cl) (A.sem (A.world r.table)) := by
  refine ⟨?_, fun r' p cs h hcs => hA.rule_sound _ r' p cs h hcs⟩
  intro eid n h
  simp only [pcsChecker, pcsCheckerIn, evidenceLeafIn, Bool.and_eq_true] at h
  obtain ⟨_, h⟩ := h
  split at h
  · rename_i e he
    simp only [Bool.and_eq_true, decide_eq_true_eq] at h
    have hmem := List.mem_of_find?_eq_some he
    have hobs := replayOK_spec (acceptPCS_sound hacc).replay e hmem
    have hvalid : Valid (requestFor r.pkg.cert r.model r.table e) :=
      hV _ (by rw [hobs, h.1])
    exact hA.leaf_sound (requestFor r.pkg.cert r.model r.table e) n h.2 hvalid
  · cases h

/-- **Generic Domain Adapter Soundness.**

    For any domain `D`, any adapter `A`, any executor semantics `Valid`:
    if the PCS checker accepts the package (`acceptPCS`, for arbitrary oracles), the
    executor is faithful to `Valid`, and `A` satisfies the local adapter contract, then
    domain acceptance of certificate claim `cid` with **any** obligation graph `g` yields
    the domain claim `c` bound to the signed certificate claim, and `D.Holds` of `c` in the
    world of the committed artifacts — together with PCS's kernel `Assures` judgement for
    that claim and the graph's structural guarantees. -/
theorem domain_adapter_sound {O : Oracles} {T : TrustAnchor} {inp : PackageInput}
    {r : AcceptedResult} {Valid : ReplayRequest → Prop} (hacc : acceptPCS O T inp = some r)
    (hV : ReplayFaithful O.exec Valid) (A : DomainAdapter D) (hA : AdapterSound A Valid)
    {cid : String} {g : Graph String A.IR} {c : D.Claim}
    (h : domainAccepts A r cid g = some c) : DomainAssurance A r cid g c := by
  unfold domainAccepts at h
  split at h
  · cases h
  · rename_i cl hcl
    obtain ⟨hclm, hclid⟩ := find?_mem_id hcl
    split at h
    · cases h
    · rename_i p hp
      have hpm := List.mem_of_find?_eq_some hp
      have hpid : p.1.claimId = cid := by simpa using List.find?_some hp
      split at h
      · rename_i hlev
        split at h
        · cases h
        · rename_i c' hdec
          split at h
          · cases h
          · rename_i ir hir
            split at h
            · rename_i hg
              cases h
              obtain ⟨L, hL⟩ := Option.isSome_iff_exists.mp hlev
              refine ⟨?_, ⟨cl, hclm, hclid, hdec⟩,
                ⟨p, hpm, hpid, L, hL, (pcs_claims_assured hacc p hpm).assures L hL⟩,
                ⟨cl, hclm, ir, hclid, hir, accepted_graph_facts hg⟩⟩
              exact hA.compile_sound _ _ ir hir
                (root_assurance_sound (pcsChecker_sound hacc hV hA cl) hg)
            · cases h
      · cases h

end PCS.V2.DomainAdapter
