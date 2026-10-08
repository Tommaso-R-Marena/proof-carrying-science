import PCS.V2.DomainAuthority

/-!
# The external-world boundary as a theorem-level object

PCS establishes domain propositions about the **committed computational world**
`A.world r.table` — the world determined by the delivered, digest-bound, signed artifact
bytes.  It cannot, by itself, establish anything about an external / deployed / physical
world: acceptance is a function of the archive bytes, so two external worlds that agree on
the committed bytes receive the same verdict (see `false_external_world_not_corresponding` and the
AI-safety counter-model in `PCS.V2.Witnesses.AISafetyDeployment`).

`ExternalWorldBridge D` makes the boundary explicit:

* `ExternalWorld`  — the external semantic domain (deployed executions, physical samples, …);
* `ExternalHolds`  — the external reading of a domain claim;
* `Corresponds w ew` — the domain-specific **data-adequacy relation** between a committed
  world and an external world (e.g. "the committed trace is a faithful log of the deployed
  run").  PCS never proves it; it is an explicit premise of every transfer theorem;
* `transport` — the domain lemma: correspondence plus committed truth gives external truth.
  This is an obligation of the bridge's author, proved once per domain.

`external_world_transfer_sound`:
PCS acceptance + `AdapterSound` + an explicit `Corresponds (A.world r.table) ew` premise
⇒ `ExternalHolds ew c`.
-/

set_option autoImplicit false

namespace PCS.V2.DomainAdapter

open PCS PCS.V2.Json PCS.V2.Replay PCS.V2.CertificateModel PCS.V2.EndToEnd PCS.V2.Flagship
open PCS.V2.ClaimGraph

/-- An explicit bridge from the committed computational world of a domain to an external
    world. -/
structure ExternalWorldBridge (D : Domain) where
  ExternalWorld : Type
  ExternalHolds : ExternalWorld → D.Claim → Prop
  /-- data adequacy: the committed world faithfully represents the external one -/
  Corresponds : D.World → ExternalWorld → Prop
  /-- the domain's transport lemma (proved by the bridge author) -/
  transport : ∀ w ew c, Corresponds w ew → D.Holds w c → ExternalHolds ew c

variable {D : Domain}

/-- **External-world transfer.**  PCS acceptance, the adapter contract, and an explicit
    correspondence premise between the committed world of the accepted package and an
    external world `ew` yield the external reading of the domain claim.  The
    correspondence premise `hcorr` is the *only* link to `ew`; nothing in the PCS
    hypotheses mentions `ew`. -/
theorem external_world_transfer_sound {O : Oracles} {T : TrustAnchor}
    {inp : PCS.V2.Package.PackageInput} {r : AcceptedResult} {Valid : ReplayRequest → Prop}
    (hacc : acceptPCS O T inp = some r) (hV : ReplayFaithful O.exec Valid)
    (A : DomainAdapter D) (hA : AdapterSound A Valid) (B : ExternalWorldBridge D)
    {cid : String} {g : Graph String A.IR} {c : D.Claim}
    (hd : domainAccepts A r cid g = some c)
    {ew : B.ExternalWorld} (hcorr : B.Corresponds (A.world r.table) ew) :
    B.ExternalHolds ew c ∧ D.Holds (A.world r.table) c :=
  have h := (domain_adapter_sound hacc hV A hA hd).holds
  ⟨B.transport _ ew c hcorr h, h⟩

/-- The correspondence premise cannot be dropped: if an accepted package admits an
    external world in which the claim is externally false, then that world does **not**
    correspond to the committed world (whenever the adapter contract holds). -/
theorem false_external_world_not_corresponding {O : Oracles} {T : TrustAnchor}
    {inp : PCS.V2.Package.PackageInput} {r : AcceptedResult} {Valid : ReplayRequest → Prop}
    (hacc : acceptPCS O T inp = some r) (hV : ReplayFaithful O.exec Valid)
    (A : DomainAdapter D) (hA : AdapterSound A Valid) (B : ExternalWorldBridge D)
    {cid : String} {g : Graph String A.IR} {c : D.Claim}
    (hd : domainAccepts A r cid g = some c) {ew : B.ExternalWorld}
    (hbad : ¬ B.ExternalHolds ew c) : ¬ B.Corresponds (A.world r.table) ew :=
  fun hcorr => hbad (external_world_transfer_sound hacc hV A hA B hd hcorr).1

end PCS.V2.DomainAdapter

namespace PCS.V2.DomainAuthority

open PCS PCS.V2.EndToEnd PCS.V2.Authority PCS.V2.Signature PCS.V2.Checkers
open PCS.V2.DomainAdapter PCS.V2.ClaimGraph

variable {D : Domain}

/-- **External-world transfer from raw signed archive bytes** (extended certified
    authority).  Hypotheses: `NoForgery`, `AdapterSound`, and the explicit correspondence
    premise. -/
theorem archive_external_world_transfer_sound (cs : List CertifiedChecker)
    {t : AuthorityTranscript} {T : TrustAnchor} {signed : List UInt8 → Prop}
    (hB : NoForgery PCS.V2.Ed25519.verify T.pk signed)
    {raw : ByteArray} {inp : PCS.V2.Package.PackageInput} {r : AcceptedResult}
    (h : acceptArchiveWithCheckers cs t T raw = some (inp, r)) (A : DomainAdapter D)
    (hA : AdapterSound A (AuthorityValid cs (fun req => (transcriptExecutor t req).outcome = .pass)))
    (Bw : ExternalWorldBridge D) {cid : String} {g : Graph String A.IR} {c : D.Claim}
    (hd : domainAccepts A r cid g = some c) {ew : Bw.ExternalWorld}
    (hcorr : Bw.Corresponds (A.world r.table) ew) : Bw.ExternalHolds ew c :=
  Bw.transport _ ew c hcorr
    (pcs_generic_domain_archive_acceptance_sound_certified cs hB h A hA hd).2.holds

end PCS.V2.DomainAuthority
